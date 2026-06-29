# 연구 정리: MTAD-GAT 기반 BOLD Signal State 정의 및 BrainLM 표현 학습

## 1. 연구 가설 및 핵심 아이디어

### 핵심 가설
> MTAD-GAT가 탐지한 **Anomaly Point(이상 지점)**는 단순한 노이즈가 아니라, 뇌의 기능적 상태(Brain State)가 전환되는 의미 있는 경계점이다.

이 가설이 맞다면:
- Anomaly Point로 분할된 **Segment 단위 CM(Connectivity Matrix)**이 뇌 기능 상태를 잘 포착한다.
- 이렇게 정의된 State로 학습된 **BrainLM의 표현(Latent)**이, 무작위 분할 기반 BrainLM보다 **더 낮은 reconstruction loss**를 달성한다.
- Latent Space에서 **CM Cluster별로 명확하게 분리**된다 → 각 클러스터 = 뇌 기능 상태

### 3개 Sub-Module의 역할
```
BOLD Signal (100 ROI × T timesteps)
    │
    ▼
┌───────────────────────────────────┐
│ MTAD-GAT (3 Sub-Modules)          │
│  1. Conv Layer  → 시간적 평활화    │
│  2. Feature-GAT → ROI 간 공간 관계 │
│  3. Temporal-GAT → 시간적 의존성   │
│          ↓ Concat → GRU           │
│  → Reconstruction + Forecast Loss │
└───────────────────────────────────┘
    │
    ▼ Anomaly Score (재구성 오차 높은 지점 = 이상 지점)
    │
    ▼ State Boundary
```

---

## 2. 전체 파이프라인 (5단계)

### Stage 1: MTAD-GAT 이상 탐지 (`model/`, `result/`)

| 항목 | 내용 |
|------|------|
| 입력 | 27명 피험자, 각 100개 ROI의 fMRI BOLD 시계열 |
| 모델 | MTAD-GAT (Conv + Feature-GAT + Temporal-GAT + GRU) |
| 출력 | 각 time point별 `Pred_Global` (0: 정상, 1: 이상) |
| 저장 위치 | `result/{subject_id}_iter_0_testresult.csv` |

**구조 세부:**
- `ConvLayer`: 1D conv로 시계열 평활화
- `FeatureAttentionLayer`: 100개 ROI 간 그래프 어텐션 (공간 축)
- `TemporalAttentionLayer`: 시간축 그래프 어텐션
- `GRULayer`: [원본 + Feature-GAT + Temporal-GAT] 3개 concat → 시퀀스 인코딩
- 출력: Reconstruct + Forecast 두 헤드

---

### Stage 2: 세그멘테이션 (`pipeline/segmentation.py`, `pipeline/segmentation_evaluation.py`)

**두 가지 방법 중 현재 채택: Embedding Change-based**

```
방법 1 (구버전): pred_global==1인 지점에서 분할
방법 2 (현재):  ||z_t - z_{t-1}||²를 계산 → 변화량 top-K 지점 = 경계
```

- MTAD-GAT GRU의 hidden state `z_t`를 각 윈도우에서 추출
- 연속 윈도우 간 embedding 변화량으로 state 전환 감지
- `smooth_window=5`, `top_k=20`, `min_segment_len=30`

**결과:** 27명 × 평균 11.4 세그먼트 = **총 308개 세그먼트**
- 평균 길이: 105.2 timesteps, 범위: 31 ~ 549

---

### Stage 3: CM 계산 (`pipeline/connectivity.py`)

각 Segment에 대해 **기능적 연결성 행렬(Functional Connectivity Matrix)** 계산:

```
CM[i,j] = Pearson 상관계수(ROI_i 시계열, ROI_j 시계열)
         → Fisher-Z 변환: arctanh(CM) [현재 USE_FISHER_Z=True]
```

- CM shape: (100, 100) → 상삼각 추출 → **4,950차원 벡터**
- Fisher-Z 사용 이유: 상관계수 분포 정규화, 클러스터링 품질 향상
- 총 **308개 CM** (피험자당 평균 11.4개)

---

### Stage 4: CM 클러스터링 (`pipeline/clustering.py`)

```
X shape: (308, 4950)  ← 308개 CM × 4950 features
    │
    ▼ StandardScaler 정규화
    │
    ▼ MiniBatchKMeans (K=4, Elbow Method 기반 결정)
    │
    ▼ 4개 Brain State 클러스터
```

**클러스터 크기 (v1/v2 기준):**
| Cluster | 크기 | 해석 (추정) |
|---------|------|-------------|
| 0 | 99개 | 우세한 State |
| 1 | 121개 | 가장 흔한 State |
| 2 | 72개 | 중간 빈도 State |
| 3 | 16개 | 드문/특수 State |

**v3에서 sliding window 후:**
| Cluster | Window 수 |
|---------|-----------|
| 0 | 1 (거의 소멸) |
| 1 | 54 |
| 3 | 28 |

---

### Stage 5: BrainLM 학습 및 Latent 분석 (`brainlm/`)

**BrainLM 아키텍처 (Transformer Masked Autoencoder):**
```
입력 시퀀스 → Input Projection (→ d_model=256)
    + CLS Token [학습 가능]
    + Positional Encoding (Sinusoidal)
    ↓
Transformer Encoder (4 layers, 8 heads, FFN=1024)
    ↓
CLS Representation (256-dim) ← 이것이 State의 Latent
    ↓
Transformer Decoder (2 layers) → Reconstruction
    ↓
MSE Loss on masked positions (mask_ratio=15%)
```

---

## 3. 버전별 BrainLM 전략

### v1 (`full_pipeline.ipynb`) — CM 시퀀스, 단일 모델
- **입력**: 4,950-dim CM 벡터를 seq_len 개 이어붙인 시퀀스
- **단일 BrainLM** 하나로 모든 클러스터 학습
- **결과**: train_loss=0.109, val_loss=0.084, latent_dim=256, 308개 latent

### v2 (`full_pipeline_v2.ipynb`) — CM 시퀀스, 클러스터별 모델
- **입력**: CM 시퀀스 (per-cluster 분리)
- **클러스터별 별도 BrainLM** (각 State에 특화된 표현)
- Grid Search로 최적 (SEQ_LEN, STRIDE) 탐색
  - **최적 조합: seq6_st1_z** (mean_val_loss=0.333, 4개 클러스터 모두 valid)
- **한계**: 클러스터마다 다른 latent space → 직접 비교 불가

### v3 (`full_pipeline_v3.ipynb`) — Raw BOLD 시계열, 단일 공유 모델
- **입력**: 같은 CM 클러스터 내 연속 4개 Segment의 **raw BOLD 시계열을 concat**
  - shape: (T_total, 100 ROI)
- **단일 공유 BrainLM** → 모든 클러스터가 **동일한 latent space** → 직접 비교 가능
- SEQ_LEN=4 (segment 개수), MAX_TIME_STEPS=670 (padding 기준)
- train=69, val=8, test=6 examples
- **21 epoch 학습** (early stopping, patience=8)

---

## 4. 현재 결과 및 해석

### v1 결과
| 지표 | 값 |
|------|-----|
| Final Train Loss | 0.109 |
| Final Val Loss | 0.084 |
| Silhouette Score | 0.072 (낮음) |
| Latent 시각화 | PCA/t-SNE로 308개 latent → 4클러스터 색상 |

### v3 결과 (최신)

**Cross-cluster Cosine Similarity:**
```
       CM0    CM1    CM3
CM0   1.000  0.960  0.989   ← 오프-대각선이 높음 (0.96~0.99)
CM1   0.960  1.000  0.974   → 클러스터 간 latent 방향이 거의 동일
CM3   0.989  0.974  1.000   → 현재 클러스터 분리가 부족함
```

**Training Curve (v3):**
- Epoch 1: loss 192.9 → Epoch 21: loss 90.9 (early stopping)
- 수렴은 되었으나 loss가 높음 → 데이터 부족 영향

---

## 5. 시각화 해석 가이드

### 5-1. CM 클러스터 센트로이드 (`cluster_centroids_z.png`)
- **해석 포인트**: 각 클러스터(Brain State)의 평균 연결성 패턴
- **가설 부합 신호**: 클러스터마다 **뚜렷하게 다른 패턴** (일부 ROI 쌍 강조, 다른 클러스터에서는 약함)
- **해석 방법**: 
  - 밝은 영역 = 강한 양의 연결 → 두 ROI가 함께 활성화
  - 어두운 영역 = 강한 음의 연결 → 반-상관 패턴
  - 클러스터 0과 클러스터 1이 대각 블록 구조에서 차이 → 서로 다른 네트워크 조합 활성

### 5-2. Subject-Cluster Similarity Matrix (`subject_cluster_similarity_z.png`)
- **해석 포인트**: 각 피험자가 어떤 State에 주로 속하는지
- **가설 부합 신호**: 피험자마다 **주도적 클러스터가 다름** (특정 State에 집중)
- **해석 방법**:
  - 행=피험자, 열=클러스터, 값=Pearson 유사도
  - 피험자 A가 클러스터 1과 높은 유사도 → "피험자 A의 뇌는 State 1에 주로 있었다"

### 5-3. Latent PCA/t-SNE (`latent_pca_z.png`, `latent_tsne_z.png`)
- **해석 포인트**: BrainLM latent space에서 CM 클러스터 분리 여부
- **가설 부합 신호**: **색상별 점군이 공간적으로 분리**
- **현재 상태 (v3)**: 코사인 유사도 0.96~0.99 → 분리 부족 예상
- **개선 방향**: 더 많은 데이터, 더 긴 학습, 클러스터 수 재조정

### 5-4. Cross-cluster Mean Cosine Heatmap (`cross_cluster_mean_cosine_*.png`)
- **해석 포인트**: 클러스터 평균 latent 벡터 간의 방향 차이
- **가설 부합 신호**: **오프-대각선 값이 낮을수록** (0에 가까울수록) 클러스터 구분 명확
- **현재 v3 문제**: 오프-대각선이 0.96~0.99 → 클러스터가 latent space에서 구분되지 않음
- **원인 추정**: 데이터 부족 (83 examples), 클러스터 불균형 (Cluster 0 = 1개만)

### 5-5. Per-cluster L2 Norm Violin (`latent_l2_norms_*.png`)
- **해석 포인트**: 클러스터별 latent 크기 분포
- **가설 부합 신호**: 클러스터마다 **L2 norm 분포가 다름** (다른 강도의 State)
- 현재 v3: CM1(54개)=54.02, CM3(28개)=52.87 → 비슷한 수준

### 5-6. Training Curve (`training_curve_*.png`)
- **해석 포인트**: BrainLM이 BOLD 패턴을 학습했는지
- **가설 부합 신호**: val_loss가 train_loss보다 낮거나 비슷하게 수렴 (과적합 없음)
- **BrainLM base 대비 성능 비교**가 핵심 지표

---

## 6. 가설 부합 여부 판단 기준

### "의미 있는 State 정의" = 아래 조건들이 만족될 때

| 검증 기준 | 기대 결과 | 현재 상태 |
|-----------|-----------|-----------|
| CM 클러스터 센트로이드 차이 | 클러스터마다 다른 FC 패턴 | 확인 필요 (시각적 검증) |
| Latent 클러스터 분리 | PCA/t-SNE에서 색상 분리 | 현재 분리 부족 (코사인 0.96~0.99) |
| BrainLM loss < Baseline | 더 낮은 reconstruction loss | 비교 데이터 필요 |
| Silhouette Score > 0 | 클러스터링 품질 양호 | v1 = 0.072 (낮음), v3 = skip |
| Subject-State 패턴 | 피험자 간 State 사용 패턴 다양 | 시각적 확인 필요 |

### "Baseline보다 높은 성능" = State 정의가 유효함
- **Baseline**: 임의 분할 기반 BrainLM (anomaly point 사용 안 함)
- **Our method**: Anomaly Point 기반 segmentation → CM clustering → BrainLM
- **판단 기준**: Our BrainLM val_loss < Baseline val_loss

---

## 7. 현재 파이프라인의 문제점 및 개선 방향

### 문제점

1. **데이터 부족 (v3 특히 심각)**
   - 27명 × 308세그먼트 → SEQ_LEN=4 sliding window → 83개 example
   - Cluster 0은 window 1개뿐 (거의 사라진 클러스터)
   - Train/Val/Test = 69/8/6 → 검증 신뢰도 낮음

2. **클러스터 불균형**
   - K=4이지만 실질적 클러스터가 2~3개 (cluster 0이 degenerate)
   - Silhouette Score 0.072 → 클러스터링 자체가 불명확

3. **v3 Cross-cluster Latent 유사도 과도**
   - CM1 vs CM3 cosine = 0.974 → 사실상 같은 방향
   - Shared BrainLM이 CM-cluster 구분을 학습하지 못함

4. **Base model 비교 부재**
   - 현재 BrainLM이 "의미있는 State 정의" 없이 학습된 BrainLM보다 나은지 수치 비교 없음

### 개선 방향

1. **피험자 수 확대** (HCP 데이터 더 활용) → 안정적 클러스터링
2. **K 재조정** → K=3 또는 silhouette 최대화로 결정
3. **Cluster-conditional BrainLM** → cluster id를 conditioning으로 입력
4. **Baseline 비교 실험** → 동일 아키텍처, 무작위 segmentation으로 학습
5. **v2 접근 재검토** → per-cluster 모델이 shared 모델보다 나을 수 있음 (v2 best: val_loss=0.333)

---

## 8. 파일 구조 요약

```
MTAD-GAT/
├── model/
│   ├── mtad_gat.py        ← MTAD-GAT 전체 모델
│   ├── gat.py             ← Feature/Temporal GAT 레이어
│   ├── gru.py             ← GRU 레이어
│   ├── conv.py            ← 1D Conv 레이어
│   ├── forecast.py        ← Forecast 헤드
│   └── reconstruct.py     ← Reconstruction 헤드
│
├── pipeline/
│   ├── segmentation.py          ← Anomaly 기반 세그멘테이션
│   ├── segmentation_evaluation.py ← Embedding 변화 기반 세그멘테이션
│   ├── connectivity.py          ← CM 계산 (Pearson + Fisher-Z)
│   ├── clustering.py            ← K-means (Elbow method)
│   ├── v3_sequences.py          ← v3용 concat TS 시퀀스 생성
│   └── visualization.py         ← 시각화 유틸
│
├── brainlm/
│   ├── model.py           ← BrainLM (CM 시퀀스용 Transformer MAE)
│   ├── ts_model.py        ← BrainLM TS (raw 시계열용)
│   ├── dataset.py         ← CM 데이터셋
│   ├── ts_dataset.py      ← 시계열 데이터셋
│   ├── train.py           ← CM BrainLM 학습 루프
│   └── ts_train.py        ← TS BrainLM 학습 루프
│
├── notebooks/
│   ├── full_pipeline.ipynb   ← v1: 단일 BrainLM on CM
│   ├── full_pipeline_v2.ipynb ← v2: per-cluster BrainLM on CM
│   └── full_pipeline_v3.ipynb ← v3: 단일 shared BrainLM on raw TS
│
├── result/                    ← MTAD-GAT 이상 탐지 결과 (27명)
├── visualization_ver1/        ← v1 시각화 결과
├── visualization_ver2/        ← v2 시각화 결과 (grid search 포함)
└── visualization_ver3/        ← v3 시각화 결과 (현재 최신)
```

---

## 9. 데이터 사양

| 항목 | 값 |
|------|-----|
| 데이터셋 | HCP (Human Connectome Project) |
| 피험자 수 | 27명 |
| ROI 수 | 100 (Parcellation) |
| Fisher-Z 적용 | YES (현재 기본) |
| CM 차원 | 4,950 (상삼각 행렬) |
| 총 세그먼트 | 308개 |
| 클러스터 수 K | 4 |
| BrainLM d_model | 256 |
| BrainLM Encoder | 4 layers, 8 heads |
| Mask Ratio | 15% |

---

## 10. 구현 계획 (최종 정리)

사용자가 제시한 3단계 구현 계획 및 현재 코드와의 대응 관계:

### Step 1: Subject별 GAT → CM 생성

```
각 Subject의 BOLD 시계열
    ↓
MTAD-GAT (3 Sub-Modules: Conv + Feature-GAT + Temporal-GAT + GRU)
    ↓ Anomaly/Embedding Change 기반 Segmentation
Sub-timeseries (Segment) 생성
    ↓
각 Segment에 대해 Pearson CM 계산 (+ Fisher-Z 변환)
    ↓
CM의 목적: 클러스터링을 위한 Feature
```

**현재 코드**: `pipeline/segmentation_evaluation.py` + `pipeline/connectivity.py`  
**핵심**: CM은 BrainLM 입력이 아닌, **State 분류를 위한 클러스터링 feature**

---

### Step 2: 전체 CM 클러스터링 + 유사도 확인

```
모든 Subject의 CM (308개, 각 4,950-dim)
    ↓
K-means Clustering (K=4)
    ↓
4개 Brain State Cluster 정의
    ↓
Individual CM ↔ Cluster Centroid 유사도 계산 (Pearson 상관)
    → 각 피험자별 "어떤 State에 얼마나 속하는가" 시각화
```

**현재 코드**: `pipeline/clustering.py`, `clustering.compute_cluster_similarity()`  
**출력**: `visualization_ver*/subject_cluster_similarity_z.png`

---

### Step 3: 클러스터별 CM 이어붙임 → BrainLM 학습 → Latent 뇌영역 시각화

```
Cluster별 CM 시퀀스 구성 (전체 Subject에서 같은 Cluster CM 모음)
    ↓
Train / Val / Test 분할 (Subject 단위)
    ↓
동일 길이로 토큰화 (seq_len 개 CM → padding)
    ↓
BrainLM 학습 (Masked Autoencoder)
    ↓
Latent 추출 (CLS token: 256-dim)
    ↓
C1 vs C2 vs C3 Latent 비교 (PCA, t-SNE, cosine)
    ↓ ← 핵심 추가 단계
Latent → 100 ROI 뇌영역 시각화
```

**현재 코드**: v2 파이프라인이 가장 유사 (`full_pipeline_v2.ipynb`)

#### Latent (100 × 1 or N) → 뇌 영역 시각화 구현 방향

현재 BrainLM CLS latent는 **256-dim**이며, 이를 **100개 ROI**에 대응시키는 방법:

| 방법 | 설명 | 구현 복잡도 |
|------|------|-------------|
| **Linear Projection** | 256→100 선형 투영, 각 ROI별 중요도 스칼라 | 낮음 |
| **Encoder Token Latent** | 시퀀스 내 각 CM 토큰의 encoder output (seq_len, 256) → 100-dim CM과 연결 | 중간 |
| **Attention Weight** | 각 ROI pair의 어텐션 가중치 집계 → 100 ROI 중요도 | 높음 |
| **d_model=100 설정** | BrainLM d_model을 100으로 설정 → latent 차원 = ROI 수 | 중간 (재학습 필요) |

**권장 방법 (단기):**
```python
# BrainLM latent (256-dim) → 100 ROI projection
roi_projection = nn.Linear(256, 100)  # 학습 가능한 투영
roi_importance = roi_projection(cls_latent)  # (batch, 100)

# 클러스터별 평균 ROI 중요도
cluster_roi_map = {}
for cid in [0, 1, 2, 3]:
    cluster_roi_map[cid] = roi_importance[cluster_mask == cid].mean(axis=0)
    # → (100,) 벡터를 뇌 지도에 매핑
```

**시각화 구현 (nilearn 사용):**
```python
import nilearn.plotting as plotting
from nilearn import datasets

atlas = datasets.fetch_atlas_schaefer_2018(n_rois=100)
# cluster_roi_map[cid] (100-dim) → 100개 ROI의 중요도 컬러맵
plotting.plot_roi(atlas.maps, title=f'Brain State {cid}', 
                  display_mode='z', colorbar=True)
```

---

### 비교 분석: C1 vs C2 vs C3 Latent 해석

| 분석 | 기대 결과 (가설 부합) | 현재 상태 |
|------|----------------------|-----------|
| PCA/t-SNE 시각화 | 클러스터별 점군 분리 | v3에서 분리 부족 |
| 평균 코사인 유사도 | 오프-대각선 < 0.5 | 현재 0.96~0.99 (문제) |
| 뇌영역 ROI 패턴 | 클러스터마다 다른 활성 영역 | 미구현 (다음 단계) |
| Reconstruction Loss | < Baseline (무작위 분할) | 비교 미완성 |

---

## 11. PPT 파일 활용 방법

Claude Code에서 PPT 파일을 직접 읽을 수는 없습니다. 다음 방법 중 하나를 사용하세요:

### 방법 1: PDF로 변환 후 공유 (권장)
```
PowerPoint → 파일 → PDF로 저장
→ Claude Code에서 Read 도구로 읽기 가능 (최대 20페이지)
```

### 방법 2: 이미지로 저장 후 공유
```
PPT 각 슬라이드를 PNG/JPG로 내보내기
→ "파일 경로를 알려줘" 형식으로 공유
```

### 방법 3: 맥에서 터미널로 PDF 변환
```bash
# LibreOffice가 있는 경우:
libreoffice --headless --convert-to pdf 파일명.pptx

# 또는 Python:
! python3 -c "import subprocess; subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', 'your_file.pptx'])"
```
