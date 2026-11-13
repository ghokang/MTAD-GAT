## 변경 이력 (2026-11-13)

### 새 기능
- **V5 무작위 분할 대조군** (`full_pipeline_v5.py`) — MTAD-GAT 분할이 무작위 분할보다 나은지 permutation 1000회로 검정 (세그먼트 개수·길이 분포 보존)
- **V6** (`full_pipeline_v6.py`) — State별 세그먼트 concat → 균일 64 TP 윈도우 분할 → State별 BrainLM 독립 학습 → latent 비교 (교수님 요청 방식, K=2/3/4 및 stride 64)
- **V7** (`full_pipeline_v7.py`) — 공유 BrainLM 하나로 학습해 모든 latent를 같은 좌표공간에서 비교
- `find_optimal_k.py` — leakage 방지 optimal K 탐색 (elbow + silhouette), 결과 `result/optimal_k/`
- `v6_heldout_recon.py` — 교차 재구성 손실을 **미학습(val+test) 윈도우만으로** 재계산
- `recon_double_center.py` — 손실 행렬 이중 중심화로 행(모델) 효과와 열(데이터 난이도) 효과 분리
- `v6_rsa_cka_repeat.py` — 공통 입력 RSA/CKA 재계산 + 같은 데이터·다른 seed 기준선
- `v6_tsne_control.py` / `v6_tsne_figures.py` — t-SNE 분리가 State 차이인지 모델 정체성인지 가리는 대조군
- `v6_window_loss.py`, `v6_control_summary.py`, `v6_fig3_fix.py`, `k_crosstab.py`, `v4_cross_recon.py`
- `thesis/` — 학위논문 본문·그림 빌드 파이프라인 (`build_thesis.py`, `make_figures.py`, `docx_builder.py`)
- `scripts/deck/` — 발표 덱 빌드 및 QA 스크립트
- `md_to_docx.py` / `build_report_docx.py` — Markdown 리포트 → Word 변환 (표·그림 포함)
- `data/atlas/` — Schaefer2018 100Parcels 7Networks 레이블

### 버그 수정
- **교차 재구성 손실의 train/test 누수 수정 (핵심)** — 자기 데이터 칸에 해당 모델의 학습 윈도우가 약 75% 섞여 있어, 비교가 사실상 '학습한 것 vs 처음 보는 것'이 되어 암기를 측정하고 있었다. 미학습 윈도우만으로 재계산한 결과:
  - V6 K=2 (stride 64): **+11.0% → −0.4%**
  - V6 K=4: State 0 +8.7%, State 1 +7.3% / State 2 −0.9%, State 3 −21.8%
  - V4 패딩 방식: **+11.0% → +0.5%**
  - → "독립 학습 모델이 자기 State 데이터를 더 잘 복원한다"는 기존 결론 폐기
- **RSA / CKA 계산 오류 수정** — 모델 0에는 State 0 데이터를, 모델 1에는 State 1 데이터를 넣어 '모델 차이'와 '입력 차이'가 섞여 있었다. 두 모델에 **같은 505개 윈도우**를 통과시켜 재계산하고, 같은 데이터로 seed만 바꾼 쌍을 기준선으로 삼았다. 기준선 최솟값 0.8828 > 관심 최댓값 0.8154 로 3회 모두 비겹침. 기존 **RSA 0.0037 / CKA 0.0260 은 폐기**
- **t-SNE State 분리가 모델 정체성 artifact임을 확인** — 같은 State 0 데이터로 seed만 바꿔 학습한 대조군에서 2D 실루엣 0.765 / kNN 1.000 이 나왔다. 실제 State 비교(0.758 / 1.000)와 동등하거나 더 높아, 분리는 State 차이의 증거가 아니다
- `fig3_latent_comparison.png` 를 잘못된 RSA·CKA를 담은 원본에서 `_fixed` 버전으로 대체

### 변경사항
- V5 대조군 결과 반영 — 7개 지표 중 **dwell time 2개만 유의**: 총 점유 시간 z=+2.10, p=0.0300 / 방문당 체류 시간 z=+3.27, p=0.0030. 세그먼트 내부 동질성(p=0.6084), 경계 대비(p=0.4176), 클러스터링 품질 K=2/3/4 는 무작위와 구별되지 않았다
- K=2/3/4 클러스터 레이블 교차표로 희소 state 흡수 양상 확인 — K를 낮춰도 데이터 부족은 해소되지 않음 (`k_crosstab.py`)
- 리포트 추가 (md + docx): V4 K=2/K=3/K=4 degree centrality 해석, V5 대조군, V6 K=2/K=3/K=4/stride64
- 시각화 결과 디렉토리 추가: `visualization_ver4_add`, `_k2`, `_k3`, `_crossrecon`, `visualization_ver5`, `visualization_ver6_k2`/`_k3`/`_k4`/`_k2_stride64`, `visualization_ver7_k2`
- 산출물 추가 — KHBM 초록, 연구 정리 PPT, 발표자료·PPT 해설 보고서, 참고문헌 PDF(`paper/`)
- `.gitignore` 보강 — `PostFAB/`(별개 저장소 PostFAB_Trace 혼입 방지), `node_modules/`, 재생성 가능한 대용량 중간 캐시 제외

---

## 변경 이력 (2026-06-29)

### 새 기능
- MTAD-GAT embedding 변화점 기반 BOLD 신호 세그먼테이션 파이프라인 구현 (V1~V4)
- CM(Connectivity Matrix) + K-means K=4 Brain State 정의 및 클러스터링
- V2: 클러스터별 독립 BrainLM (CM 시퀀스 입력) — latent 직교성 확인
- V4: 클러스터별 독립 BrainLM (Raw Timeseries 입력) — 교수님 피드백 반영
- ROI 번호 → Schaefer100 해부학적 뇌 영역 매핑 (`roi_mapping.py`)
- 시각화 8종 생성: PCA/t-SNE, cosine heatmap, CM centroid, 네트워크 레이더 차트 등
- `visualization_ver4/roi_mapping/` — 네트워크 수준 해부학적 해석 도표 6종
- `VISUALIZATION_REPORT_V4.md` — 그래프 해석 및 가설 검증 결과 보고서
- `RESEARCH_SUMMARY.md` — 전체 연구 개요 문서

### 변경사항
- 세그멘테이션 방법을 windowed 방식으로 변경 및 segmentation 모듈 추가 (2026-03-05)
- 코드 수정 및 리팩토링 (2026-03-13)
- paper code 초기 적용 (2026-03-05)
- `.gitignore` 추가 — `*.pt` 가중치, `__pycache__`, `.DS_Store` 제외

---

## 변경 이력 (2025-08-01)

### 새 기능
- 초기 커밋: 프로젝트 기반 구조 설정

---

## 변경 이력 (2024-06-30)

### 새 기능
- 프로젝트 초기 생성 및 데이터 업로드
- LICENSE 추가
- README.md 작성
- 데이터 디렉토리 구성
