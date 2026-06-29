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
