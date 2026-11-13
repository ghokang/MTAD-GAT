"""V4 K=3 리포트 / K=2 vs K=3 비교 리포트 → Word(.docx) 변환.

마크다운 리포트(REPORT_V4_K3.md, REPORT_K2_VS_K3.md)의 내용을 그대로 유지하되
- 헤딩 계층 → Word 제목
- 파이프 테이블 → 진짜 Word 표
- "그림 파일 경로" 언급 → 실제 PNG 삽입
로 재구성한다.

재실행: python3 build_report_docx.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "thesis"))
from docx_builder import Docx  # noqa: E402

K3 = ROOT / "visualization_ver4_k3"
K2 = ROOT / "visualization_ver4_k2"
K4 = ROOT / "visualization_ver4"
OPT = ROOT / "result" / "optimal_k"


# ── 헬퍼 ────────────────────────────────────────────────────────────────────
def bullet(d, text, sub=False):
    d.para(("    ◦ " if sub else "• ") + text, indent=0, align="left", after=60)


def note(d, text):
    """마크다운 인용구(> …) 스타일 — 회색 이탤릭."""
    d.para(text, indent=0, align="left", after=100, italic=True, color="595959")


def code(d, lines):
    for ln in lines:
        d.para(ln if ln else " ", indent=0, align="left", after=0, size=18, color="404040")
    d.spacer(120)


def meta(d, pairs):
    for k, v in pairs:
        d.para(f"{k}: {v}", indent=0, align="left", after=40, size=21)
    d.spacer(160)


# =============================================================================
# 리포트 1 — V4 파이프라인 (K=3)
# =============================================================================
def build_k3():
    d = Docx()
    d.title("V4 파이프라인 (K=3) 시각화 해석 보고서",
            "— per-cluster BrainLM + Raw Timeseries 입력, K=3 재클러스터링 —")
    meta(d, [
        ("버전", "V4 — per-cluster BrainLM + Raw Timeseries 입력, K=3 재클러스터링"),
        ("날짜", "2026-09-07"),
        ("핵심 변경점 (V4 K=4 → V4 K=3)",
         "K-means 클러스터 수를 4에서 3으로 변경. 나머지 파이프라인·하이퍼파라미터는 동일"),
        ("실행 스크립트", "full_pipeline_v4_k3.py (full_pipeline_v4.py에서 K = 3만 변경)"),
        ("결과 경로", "visualization_ver4_k3/, checkpoint/brainlm_v4_k3/"),
    ])

    # ── 1 ──
    d.heading("1. 왜 K=3을 다시 돌렸는가", 1)
    d.para("기존 V4 리포트는 K=4를 사용했다. 그러나 코드를 다시 추적한 결과, K=4는 elbow/실루엣 "
           "탐색으로 선정된 값이 아니라 하드코딩된 값이었다.")
    bullet(d, "원본 노트북에서 실루엣 계산 셀은 macOS OpenMP/BLAS 충돌(커널 크래시) 우려로 "
              "주석 처리되어 있었고, optimal_k = 4가 직접 대입되어 있었다.")
    bullet(d, "파이프라인 클러스터링 함수도 skip_silhouette=True로 호출된다.")
    bullet(d, "논문 초안(thesis/build_thesis.py)에도 이 문제가 이미 Limitations로 기록되어 있다: "
              "\"본 연구는 K=4를 채택하였으나 상태 3의 소멸에 가까운 크기는 이 선택이 최적이 아닐 수 "
              "있음을 시사한다. 실루엣 계수 등 내부 평가 지표를 이용한 체계적 탐색과 K=3 조건에서의 "
              "재분석이 요구된다.\"")
    d.para("이에 따라 torch를 로드하지 않는 독립 프로세스(find_optimal_k.py)로 실루엣을 실제로 "
           "계산했다. 계산량은 최대 308×4,950 규모로 가벼웠고 크래시 없이 완료됐다.")

    d.heading("1.1 실루엣 스코어 (K=2~10, StandardScaler 적용 Fisher-Z CM)", 2)
    d.table([
        ["K", "Silhouette (train 19명 / 212세그먼트)", "Silhouette (전체 27명 / 308세그먼트)",
         "최소 클러스터 크기 (전체 기준)"],
        ["2", "0.241 (1위)", "0.227 (1위)", "132"],
        ["3", "0.185 (2위)", "0.170 (2위)", "30"],
        ["4", "0.134 (3위)", "0.094", "28"],
        ["5", "0.111", "0.079", "16"],
        ["6", "0.084", "0.079", "7"],
        ["7", "0.089", "0.057", "12"],
        ["8", "0.055", "0.043", "11"],
        ["9", "0.066", "0.058", "5"],
        ["10", "0.038", "0.035", "6"],
    ], caption="표 1. K별 실루엣 스코어 (K=2가 1위, K=3이 2위, K=4는 하위권)",
        widths=[0.6, 2.2, 2.2, 1.8])

    bullet(d, "train subject만 사용한 계산은 val/test 피험자가 클러스터 정의에 관여하지 않도록 "
              "leakage를 차단한 조건이다. 두 조건 모두에서 순위(K=2 > K=3 > K=4)가 동일했다.")
    bullet(d, "MiniBatchKMeans로 계산해도 순위는 유지된다 (전체 기준 K=2: 0.224, K=3: 0.193, "
              "K=4: 0.109). 실제 파이프라인이 MiniBatchKMeans를 쓰기 때문에 이 확인이 필요했다.")
    bullet(d, "즉 K=4는 실루엣 기준으로 명확한 하위권이며, K=3은 K=2에 이은 2위다.")

    note(d, "정직한 주의: 절대값 자체는 낮다. Kaufman & Rousseeuw 관례상 실루엣 0.25 이하는 "
            "\"실질적인 군집 구조를 찾지 못함\" 구간이며, 최상위인 K=2(0.227~0.241)조차 그 경계에 "
            "걸쳐 있다. K=3(0.170~0.185)은 그보다 더 아래다. 따라서 이 결과는 \"K=3이 좋은 "
            "클러스터링\"이라는 근거가 아니라, \"K=4보다는 덜 나쁜 선택\"이라는 근거로만 읽어야 한다.")

    d.figure(OPT / "elbow_silhouette_train.png",
             "그림 1. Elbow + 실루엣 곡선 (train 19명 / 212세그먼트 기준)")
    d.figure(OPT / "elbow_silhouette_full.png",
             "그림 2. Elbow + 실루엣 곡선 (전체 27명 / 308세그먼트 기준)")

    # ── 2 ──
    d.heading("2. 실험 설정", 1, page_break=True)
    d.table([
        ["파라미터", "값"],
        ["피험자 수", "27 (MTAD-GAT 학습용 70명과 완전 분리된 held-out)"],
        ["총 세그먼트", "308"],
        ["K (Brain State 수)", "3"],
        ["클러스터링 알고리즘", "MiniBatchKMeans (n_init=4, random_state=42)"],
        ["CM", "Pearson + Fisher-Z, 100×100 → 4,950-dim, StandardScaler"],
        ["SEQ_LEN", "1 (세그먼트 1개 = 1 예제)"],
        ["BrainLM d_model", "256"],
        ["Encoder layers / heads", "4 / 8"],
        ["Mask ratio", "15%"],
        ["Max epochs", "50"],
        ["Early stopping patience", "10"],
        ["Split", "subject-level, seed=42, val 0.15 / test 0.15"],
    ], caption="표 2. 실험 설정", widths=[1.2, 2.8])

    # ── 3 ──
    d.heading("3. 클러스터링 결과", 1)
    d.table([
        ["State", "세그먼트 수", "비율", "Train / Val / Test", "상태"],
        ["State 0", "169", "54.9%", "115 / 30 / 24", "학습 완료"],
        ["State 1", "122", "39.6%", "84 / 19 / 19", "학습 완료"],
        ["State 2", "17", "5.5%", "13 / 0 / 4", "데이터 부족으로 제외 (skipped)"],
    ], caption="표 3. K=3 클러스터링 결과 및 split 분포",
        widths=[1.0, 1.0, 0.8, 1.5, 2.0])

    note(d, "State 2 스킵 이유 — K=4의 문제가 그대로 반복됐다. 클러스터 크기 17개가 subject-level "
            "split에서 train 13 / val 0 / test 4로 쪼개지면서 validation set이 비었다. Early "
            "stopping이 성립하지 않으므로 학습 자체를 수행할 수 없어 파이프라인이 자동으로 스킵했다. "
            "K=4에서 State 3(16개 → 12/0/4)이 제외됐던 것과 원인·규모·결과가 사실상 동일하다. 즉 K를 "
            "4에서 3으로 줄여도 \"소수 상태 소멸\" 문제는 해결되지 않았다. 결과적으로 K=3으로 "
            "정의했지만 실제로 표현학습이 검증된 상태는 2개뿐이다.")

    d.para("클러스터 크기에 대한 부가 설명: 위 크기(169/122/17)는 파이프라인의 MiniBatchKMeans "
           "결과다. find_optimal_k.py가 full-batch KMeans로 같은 데이터를 나누면 152/126/30이 "
           "나온다. 알고리즘 차이만으로 최소 클러스터가 17↔30으로 흔들린다는 점 자체가 이 소수 "
           "상태가 안정적인 구조가 아니라 경계에 놓인 표본 집합임을 시사한다.")

    d.figure(K3 / "fig5_cm_centroids.png",
             "그림 3. State별 CM 중심값 + State-specific ROI — 학습에서 제외된 State 2도 포함되어 있다 "
             "(CM 중심은 학습 없이 계산 가능)")

    # ── 4 ──
    d.heading("4. 클러스터별 BrainLM 학습 결과", 1, page_break=True)
    d.table([
        ["State", "예제 수 (Train/Val/Test)", "Max TS length", "최종 Train Loss",
         "최종 Val Loss", "학습 에폭", "상태"],
        ["State 0", "115 / 30 / 24", "279", "84.23", "93.66", "49", "학습 완료"],
        ["State 1", "84 / 19 / 19", "242", "76.69", "91.89", "50", "학습 완료"],
        ["State 2", "13 / 0 / 4", "—", "—", "—", "—", "제외 (skip)"],
    ], caption="표 4. 클러스터별 BrainLM 학습 결과",
        widths=[0.9, 1.6, 1.1, 1.1, 1.0, 0.8, 1.1])

    d.para("관찰:", indent=0, bold=True, after=60)
    bullet(d, "두 State 모두 50 에폭 상한 근처(49, 50)까지 학습이 진행됐다. K=4에서 세 State가 각각 "
              "17 / 24 / 19 에폭에서 early stopping으로 조기 종료된 것과 대조된다. 클러스터당 학습 "
              "데이터가 늘어나면서 과적합 시점이 뒤로 밀린 것으로 보인다.")
    bullet(d, "Train–Val 간격은 State 0에서 9.43, State 1에서 15.20이다. State 1이 예제 수가 적은 "
              "만큼(84 vs 115) 일반화 격차가 더 크다.")
    bullet(d, "State 1이 State 0보다 train/val loss 모두 낮다. 예제 수는 더 적지만 세그먼트 길이가 "
              "짧고(242 vs 279) 내부 패턴이 더 균질할 가능성이 있다. 다만 이 해석을 뒷받침할 별도 "
              "지표는 아직 계산하지 않았다.")

    d.figure(K3 / "fig1_training_curves.png",
             "그림 4. 클러스터별 BrainLM 학습 곡선 — State 0, 1 두 개만 표시되며 둘 다 50 에폭 부근까지 진행")

    d.heading("4.1 매우 중요한 caveat — 보고된 Loss 절대값은 약 100배 부풀려져 있다", 2)
    d.para("brainlm/ts_model.py의 compute_loss()에 정규화 버그가 있다.")
    code(d, [
        'w = (m * attn).unsqueeze(-1)          # shape: (B, T, 1)',
        'denom = w.sum().clamp_min(1.0)        # timestep 개수만 셈',
        'loss = F.mse_loss(recon * w, labels * w, reduction="sum") / denom',
    ])
    bullet(d, "분자의 reduction=\"sum\"은 (B, T, 100) 전체 원소에 대해 제곱오차를 더한다.")
    bullet(d, "분모 w.sum()은 w의 마지막 축이 1이므로 (B, T) 개수, 즉 timestep 개수만 센다.")
    bullet(d, "따라서 ROI feature 차원(=100)으로 나뉘지 않아 보고된 loss가 실제 element-wise MSE의 "
              "약 100배다.")

    d.table([
        ["State", "보고된 Val Loss", "100으로 나눈 추정 실제 MSE"],
        ["State 0", "93.66", "약 0.94"],
        ["State 1", "91.89", "약 0.92"],
    ], caption="표 5. 스케일 보정 시 추정되는 실제 MSE", widths=[1.0, 1.4, 2.0])

    d.para("정규화된 입력에서 MSE 약 0.9라는 값은 \"분산을 거의 설명하지 못하는 수준(1.0)에 근접\""
           "한다는 의미로, 기존 리포트가 \"loss가 100 근처인 것은 raw BOLD 스케일 때문\"이라고 "
           "적었던 설명은 틀렸다.")
    bullet(d, "영향 있음: loss 절대값에 대한 모든 해석, \"잘 재구성했다\"는 서술.")
    bullet(d, "영향 없음: State 간 상대 비교(어느 State가 더 낮은 loss로 수렴했는지). 모든 State에 "
              "동일한 상수 배율이 적용되므로 순위와 비율은 보존된다.")
    bullet(d, "이 리포트의 모든 loss 표는 수정 전 원본 값 그대로 기재했다. 논문/발표에서 절대값을 "
              "인용할 경우 반드시 이 배율을 바로잡거나 caveat을 병기해야 한다.")

    # ── 5 ──
    d.heading("5. 핵심 결과: Cross-cluster Cosine Similarity", 1, page_break=True)
    d.table([
        ["", "State 0", "State 1"],
        ["State 0", "1.000", "0.068"],
        ["State 1", "0.068", "1.000"],
    ], caption="표 6. Cross-cluster cosine similarity (2×2)", widths=[1.2, 1.2, 1.2])
    d.para("오프-대각: 0.0681 (State 2는 학습 제외로 latent가 없어 계산 불가)", indent=0, bold=True)

    d.para("해석:", indent=0, bold=True, after=60)
    bullet(d, "0.068은 0에 가깝다. 두 State BrainLM의 평균 latent 방향이 거의 직교하며, 이는 \"각 "
              "State가 서로 다른 표현 공간을 학습했다\"는 기존 가설과 일관된다.")
    bullet(d, "다만 K=3에서는 학습된 클러스터가 2개뿐이므로 오프-대각 값이 단 하나다. \"평균 "
              "0.068\"은 분포의 평균이 아니라 단일 관측치이며, 산포·안정성을 논할 수 없다.")
    bullet(d, "K=4의 오프-대각 평균(-0.0056)이 더 0에 가까워 보이지만, 그것은 -0.059와 +0.048이 "
              "상쇄된 결과다. 절댓값 평균으로 보면 K=4는 0.037, K=3은 0.068이다. 어느 쪽이 \"더 "
              "직교하다\"고 주장하기에는 관측치가 너무 적고, 귀무분포(무작위 세그먼테이션 대조군) "
              "대비 유의성 검정을 아직 수행하지 않았다.")
    bullet(d, "즉 이 지표는 현재 \"직교성 가설과 모순되지 않는다\" 수준까지만 말할 수 있고, K 선택의 "
              "근거로 쓰기에는 약하다.")

    d.figure(K3 / "fig3_cosine_and_l2.png",
             "그림 5. Cross-cluster cosine heatmap + State별 latent L2 norm violin — 히트맵이 2×2로 축소됨")

    # ── 6 ──
    d.heading("6. 시각화 그래프", 1, page_break=True)
    d.para("이미지 파일은 visualization_ver4_k3/ 아래에 있다. 아래 표는 각 그림의 내용과 K=3에서의 "
           "유의사항을 정리한 것이며, 이어지는 6.1절에 실제 그림을 모두 삽입했다.")
    d.table([
        ["파일", "내용", "K=3에서의 유의사항"],
        ["fig1_training_curves.png", "클러스터별 BrainLM 학습 곡선",
         "State 0, 1 두 개만 표시. 둘 다 50 에폭 부근까지 진행"],
        ["fig2_pooled_latent.png", "Pooled PCA + t-SNE (L2 정규화 후)",
         "총 291개 latent (169+122). State 2는 없음"],
        ["fig3_cosine_and_l2.png", "Cross-cluster cosine heatmap + L2 norm violin",
         "히트맵이 2×2로 축소됨"],
        ["fig4_latent_profile.png", "평균 latent 프로파일 + PCA 누적 분산",
         "두 선만 비교되므로 K=4 대비 정보량이 적음"],
        ["fig5_cm_centroids.png", "State별 CM 중심값 + State-specific ROI",
         "State 2 포함 3개 모두 그려짐 (CM 중심은 학습 없이 계산 가능)"],
        ["fig6_subject_state.png", "피험자별 State 유사도 + 점유율",
         "3개 State 기준 점유율. State 2가 소수 피험자에 몰려 있는지 확인 가능"],
        ["fig7_v2_vs_v4.png", "V2(CM 입력) vs V4(Raw TS 입력) 비교",
         "주의: V2 쪽은 K=4 시절 결과(visualization_ver2/final_runs/seq6_st1_z_ep50)를 그대로 "
         "로드한다. K=3과의 직접 비교 그림이 아니므로 인용 시 주의"],
        ["fig8_summary_dashboard.png", "종합 요약 대시보드", "위 내용 통합"],
    ], caption="표 7. 시각화 파일 목록", widths=[1.5, 1.8, 2.7])

    d.heading("6.1 Figure별 읽는 법 (K=4 리포트와 동일한 관점)", 2, page_break=True)

    d.para("Figure 1 — 학습 곡선. 각 State BrainLM이 masked autoencoder로 raw BOLD를 재구성하는 "
           "학습 과정. K=3에서는 두 State 모두 early stopping 없이 상한까지 갔으므로, 더 "
           "학습시키면 val loss가 더 내려갈 여지가 남아 있다 — 즉 현재 loss는 수렴값이 아닐 수 있다.")
    d.figure(K3 / "fig1_training_curves.png", "그림 6. fig1_training_curves.png — 클러스터별 BrainLM 학습 곡선")

    d.para("Figure 2 — Pooled PCA / t-SNE. L2 정규화 후 방향만 비교. 두 State가 공간적으로 "
           "분리되어 보이는지 확인한다. 단, 클러스터가 2개뿐이면 어떤 투영에서도 \"둘로 갈라져 "
           "보이기\" 쉬우므로 이 그림은 K=4 때보다 증거력이 약하다.")
    d.figure(K3 / "fig2_pooled_latent.png", "그림 7. fig2_pooled_latent.png — Pooled PCA + t-SNE (L2 정규화 후)")

    d.para("Figure 3 — Cosine heatmap + L2 norm. 좌측 히트맵의 오프-대각이 0.068. 우측 violin은 "
           "State별 latent 크기 분포로, State 간 BOLD 진폭 차이 및 State 내부 variability를 "
           "반영한다.")
    d.figure(K3 / "fig3_cosine_and_l2.png", "그림 8. fig3_cosine_and_l2.png — Cosine heatmap + L2 norm violin")

    d.para("Figure 4 — Latent 프로파일 + PCA 누적 분산. 누적 분산 곡선이 빠르게 90%에 도달하는 "
           "State일수록 내부적으로 균질하다. State 0(n=169)과 State 1(n=122)의 곡선 차이를 "
           "비교하면 어느 쪽이 더 단일한 패턴인지 볼 수 있다.")
    d.figure(K3 / "fig4_latent_profile.png", "그림 9. fig4_latent_profile.png — 평균 latent 프로파일 + PCA 누적 분산")

    d.para("Figure 5 — CM centroid. 클러스터 레이블을 만든 근거인 FC 패턴 자체. State 2도 여기엔 "
           "나온다 — 학습에서만 빠졌을 뿐 클러스터 자체는 존재하기 때문이다. State 2 centroid가 "
           "State 0/1과 뚜렷이 다르다면 \"표본이 없어서 검증하지 못한 실재하는 상태\"일 가능성을 "
           "지지한다.")
    d.figure(K3 / "fig5_cm_centroids.png", "그림 10. fig5_cm_centroids.png — State별 CM 중심값 + State-specific ROI")

    d.para("Figure 6 — 피험자별 State 분포. State 2(n=17)가 소수 피험자에 집중되어 있다면 개인 "
           "특이적 패턴, 여러 피험자에 흩어져 있다면 드물지만 보편적인 상태라는 해석이 가능하다. "
           "K=3 결과 해석에서 가장 정보량이 큰 그림이다.")
    d.figure(K3 / "fig6_subject_state.png", "그림 11. fig6_subject_state.png — 피험자별 State 유사도 + 점유율")

    d.para("Figure 7 — V2 vs V4. 위 표의 주의사항대로 K 조건이 섞여 있다. K=3 리포트의 근거로 "
           "삼지 말 것.")
    d.figure(K3 / "fig7_v2_vs_v4.png",
             "그림 12. fig7_v2_vs_v4.png — V2(CM) vs V4(Raw TS) 비교 (V2 쪽은 K=4 시절 결과)")

    d.para("Figure 8 — 종합 대시보드. 발표용 한 장 요약.")
    d.figure(K3 / "fig8_summary_dashboard.png", "그림 13. fig8_summary_dashboard.png — 종합 요약 대시보드")

    # ── 7 ──
    d.heading("7. K=4 대비 무엇이 달라졌나", 1, page_break=True)
    d.table([
        ["항목", "K=4 (기존)", "K=3 (본 리포트)", "평가"],
        ["실루엣 (train / 전체)", "0.134 / 0.094", "0.185 / 0.170", "K=3 우세"],
        ["클러스터 크기", "99 / 121 / 72 / 16", "169 / 122 / 17", "소수 클러스터 문제 미해결"],
        ["학습된 State 수", "3 (State 3 제외)", "2 (State 2 제외)", "검증 가능한 상태가 오히려 줄어듦"],
        ["학습 에폭", "17 / 24 / 19 (조기 종료)", "49 / 50 (상한 도달)", "클러스터당 데이터 증가 효과"],
        ["최종 Train Loss", "92.81 / 92.20 / 92.97", "84.23 / 76.69", "낮아졌으나 에폭 수 교란 있음"],
        ["최종 Val Loss", "98.83 / 101.15 / 115.67", "93.66 / 91.89", "낮아졌고 State 간 편차도 감소"],
        ["오프-대각 코사인", "-0.059 / -0.005 / 0.048 (평균 -0.006)", "0.068 (단일 값)",
         "둘 다 0에 가까움, 우열 판단 불가"],
    ], caption="표 8. K=4와 K=3의 항목별 비교", widths=[1.3, 2.0, 1.5, 1.7])

    d.para("loss 감소에 대한 정직한 해석: K=3의 loss가 K=4보다 낮은 것은 사실이지만, 이를 곧바로 "
           "\"K=3의 상태 정의가 더 좋다\"로 읽으면 안 된다. 두 조건은 클러스터당 학습 예제 수와 실제 "
           "학습 에폭 수가 모두 다르다(K=4는 62~86예제로 17~24에폭, K=3은 84~115예제로 49~50에폭). "
           "loss 차이의 상당 부분이 데이터량·학습량 차이로 설명될 수 있으며, 이를 분리하려면 "
           "에폭·예제 수를 통제한 추가 실험이 필요하다.")

    # ── 8 ──
    d.heading("8. 종합 결론", 1)
    for i, t in enumerate([
        "K=4는 실루엣 근거가 없는 하드코딩 값이었고, 실제로 계산해보면 K=2 > K=3 > K=4 순이다. 이 "
        "점은 논문 Limitations에 이미 예고되어 있었으며, 본 재실행으로 확인됐다.",
        "K=3은 K=4보다 실루엣이 높고 State별 loss도 낮으며 학습이 조기 종료되지 않는다. 그 "
        "의미에서 K=4보다 나은 선택이다.",
        "그러나 K=3은 \"소수 상태가 validation set을 구성하지 못해 제외되는\" 구조적 문제를 해결하지 "
        "못했다. State 2(n=17, val=0)가 K=4의 State 3(n=16, val=0)과 동일한 방식으로 탈락했고, "
        "결과적으로 검증된 상태는 2개뿐이다. K=3이라고 부르지만 실질은 2-state 분석에 가깝다.",
        "State 간 latent는 여전히 거의 직교하다(cosine 0.068). 직교성 가설과 모순되지 않지만, "
        "관측치가 단 하나이고 무작위 세그먼테이션 대조군이 없어 이것만으로 가설을 강하게 "
        "지지한다고 말할 수 없다.",
        "loss 절대값은 약 100배 부풀려져 있다 (compute_loss() 분모 버그). State 간 상대 비교는 "
        "유효하지만 절대값 인용 시 반드시 정정이 필요하다.",
        "모든 K에서 실루엣이 낮다(최대 0.24). 이 데이터의 CM 공간에 강한 군집 구조가 존재하지 않을 "
        "가능성을 배제할 수 없다. K 선택은 \"가장 덜 나쁜 값 고르기\"에 가깝다는 점을 정직하게 "
        "기술해야 한다.",
    ], 1):
        d.para(f"{i}. {t}", indent=0, after=80)

    d.heading("8.1 다음 단계 제안", 2)
    for i, t in enumerate([
        "소수 상태 처리 방침 확정. (a) 피험자 수 확대, (b) subject-level split 대신 계층화"
        "(stratified) split으로 val 확보, (c) 소수 클러스터를 최근접 클러스터에 병합 — 중 하나를 "
        "선택하고 논문에 명시.",
        "compute_loss() 분모 수정 후 재학습. 절대 MSE 해석이 필요한 모든 서술의 전제 조건.",
        "무작위 세그먼테이션 baseline. MTAD-GAT 변화점 없이 같은 길이로 자른 세그먼트에 동일 "
        "파이프라인 적용 → cosine이 유의하게 다른지 검정. 이것이 없으면 직교성 결과는 해석이 아니라 "
        "관찰에 머문다.",
        "K 선택 근거 재기술. find_optimal_k.py 결과(실루엣 표 + elbow 그림 "
        "result/optimal_k/elbow_silhouette_train.png, elbow_silhouette_full.png)를 논문 Methods에 "
        "직접 포함.",
        "에폭·예제 수 통제 재실험. K 간 loss 비교를 유효하게 만들기 위해 필요.",
    ], 1):
        d.para(f"{i}. {t}", indent=0, after=80)

    # ── 9 ──
    d.heading("9. 파일 구조", 1)
    code(d, [
        "visualization_ver4_k3/",
        "├── fig1_training_curves.png     # 클러스터별 BrainLM 학습 곡선 (State 0, 1)",
        "├── fig2_pooled_latent.png       # Pooled PCA + t-SNE (L2 정규화)",
        "├── fig3_cosine_and_l2.png       # Cross-cluster cosine heatmap + L2 norm violin",
        "├── fig4_latent_profile.png      # 평균 latent 프로파일 + PCA 누적 분산",
        "├── fig5_cm_centroids.png        # State별 CM 중심값 + State-specific ROI (State 2 포함)",
        "├── fig6_subject_state.png       # 피험자별 State 유사도 + 점유율",
        "├── fig7_v2_vs_v4.png            # V2(CM) vs V4(Raw TS) 비교 — V2는 K=4 시절 결과",
        "├── fig8_summary_dashboard.png   # 종합 요약 대시보드",
        "├── latents_v4_cluster0.npy      # State 0 latent (169 x 256)",
        "├── latents_v4_cluster1.npy      # State 1 latent (122 x 256)",
        "├── v4_results.csv               # 클러스터별 학습 결과 수치",
        "├── v4_cross_cluster_cosine.csv  # 코사인 유사도 매트릭스 (2x2)",
        "└── v4_summary.json              # 전체 파이프라인 설정 + 결과 요약",
        "",
        "checkpoint/brainlm_v4_k3/",
        "├── cluster_0/  (best_model.pt, last_model.pt, config.pt, normalizer.pkl)",
        "└── cluster_1/  (같은 구조)",
        "                                 # cluster_2는 학습 제외로 생성되지 않음",
        "",
        "full_pipeline_v4_k3.py           # K=3 실행 스크립트",
        "find_optimal_k.py                # 실루엣/elbow 탐색 (torch 미로드, 크래시 회피)",
        "result/optimal_k/                # 실루엣 결과 CSV + elbow 그림",
    ])

    out = ROOT / "REPORT_V4_K3.docx"
    d.save(out)
    return out, len(d.images)


# =============================================================================
# 리포트 2 — K=2 vs K=3 비교
# =============================================================================
def build_cmp():
    d = Docx()
    d.title("K=2 vs K=3 비교 보고서", "— 참고: K=4 —")
    meta(d, [
        ("날짜", "2026-09-07"),
        ("대상", "V4 파이프라인 (per-cluster BrainLM + Raw BOLD Timeseries 입력)"),
        ("데이터", "held-out 피험자 27명, 308 세그먼트 (MTAD-GAT 학습에 쓰인 70명과 완전 분리)"),
        ("실행 스크립트", "full_pipeline_v4_k2.py, full_pipeline_v4_k3.py, full_pipeline_v4.py(K=4)"),
        ("결과 경로", "visualization_ver4_k2/, visualization_ver4_k3/, visualization_ver4/"),
    ])

    d.heading("이 비교를 하게 된 배경", 1)
    d.para("기존 파이프라인의 K=4는 탐색으로 결정된 값이 아니었다.")
    bullet(d, "원본 노트북에서 실루엣/elbow 계산 셀은 macOS OpenMP/BLAS 충돌(커널 크래시) 우려로 "
              "주석 처리되어 있었고, optimal_k = 4가 직접 대입되어 있었다.")
    bullet(d, "파이프라인 클러스터링도 skip_silhouette=True로 호출된다.")
    bullet(d, "논문 초안(thesis/build_thesis.py) Limitations에도 \"K=4를 채택하였으나 상태 3의 "
              "소멸에 가까운 크기는 이 선택이 최적이 아닐 수 있음을 시사한다\"고 이미 기록되어 있었다.")
    d.para("이에 torch를 로드하지 않는 독립 프로세스(find_optimal_k.py)로 실루엣을 실제 계산하고, "
           "상위 후보인 K=2와 K=3을 파이프라인 전체(클러스터링 → State별 BrainLM 학습 → latent "
           "코사인)로 재실행했다. 아래는 그 결과 비교다.")

    # ── 1 ──
    d.heading("1. 실루엣 스코어 비교", 1)
    d.para("두 가지 조건에서 각각 계산했다.")
    bullet(d, "train subject 기준 (19명 / 212세그먼트): val·test 피험자가 클러스터 정의에 관여하지 "
              "않도록 leakage를 차단한 조건")
    bullet(d, "전체 기준 (27명 / 308세그먼트): 실제 파이프라인이 클러스터링을 수행하는 방식")

    d.table([
        ["K", "Silhouette (train 19명)", "순위", "Silhouette (전체 27명)", "순위",
         "MiniBatchKMeans (전체)"],
        ["2", "0.241", "1위", "0.227", "1위", "0.224"],
        ["3", "0.185", "2위", "0.170", "2위", "0.193"],
        ["4", "0.134", "3위", "0.094", "4위", "0.109"],
        ["5", "0.111", "—", "0.079", "—", "0.074"],
        ["6", "0.084", "—", "0.079", "—", "0.083"],
        ["7", "0.089", "—", "0.057", "—", "0.076"],
        ["8", "0.055", "—", "0.043", "—", "0.050"],
        ["9", "0.066", "—", "0.058", "—", "0.038"],
        ["10", "0.038", "—", "0.035", "—", "0.045"],
    ], caption="표 1. K별 실루엣 스코어 — 세 조건 모두에서 K=2 > K=3 > K=4",
        widths=[0.5, 1.5, 0.6, 1.5, 0.6, 1.6])

    d.para("정리:", indent=0, bold=True, after=60)
    bullet(d, "순위는 세 조건 모두에서 동일하다: K=2 > K=3 > K=4. 서브셋(leakage 차단 여부)에도, "
              "알고리즘(full-batch KMeans vs MiniBatchKMeans)에도 뒤집히지 않는다.")
    bullet(d, "K=2와 K=3의 격차는 train 기준 0.056, 전체 기준 0.057이다. \"근소한 차이\"라기보다 "
              "일관되게 K=2가 앞선다.")
    bullet(d, "K=4는 K=3보다도 확실히 낮다. 기존 하드코딩 값이 실루엣 기준으로 정당화되지 않는다는 "
              "점은 명확하다.")

    note(d, "반드시 함께 기술해야 할 사실: 절대값이 모두 낮다. Kaufman & Rousseeuw 관례상 실루엣 "
            "0.25 이하는 \"실질적인 군집 구조를 찾지 못했다\"로 해석되는 구간이며, 최상위인 "
            "K=2(0.227~0.241)조차 그 경계에 걸쳐 있다. K=3(0.170~0.185)은 그보다 아래다. 즉 이 "
            "비교는 \"어느 K가 좋은가\"가 아니라 \"어느 K가 덜 나쁜가\"의 비교다. 이 데이터의 "
            "Fisher-Z CM 공간에 뚜렷한 이산적 상태 구조가 존재하지 않을 가능성을 배제할 수 없으며, "
            "이 점은 논문에 명시해야 한다.")

    d.figure(OPT / "elbow_silhouette_train.png",
             "그림 1. Elbow + 실루엣 곡선 (train 19명 / 212세그먼트 기준)")
    d.figure(OPT / "elbow_silhouette_full.png",
             "그림 2. Elbow + 실루엣 곡선 (전체 27명 / 308세그먼트 기준)")

    # ── 2 ──
    d.heading("2. 클러스터 크기와 균형 비교", 1, page_break=True)
    d.table([
        ["조건", "클러스터 크기", "최소/최대 비율", "학습 제외된 State", "학습에 실제 사용된 세그먼트"],
        ["K=2", "138 / 170", "0.81", "없음", "308 / 308 (100%)"],
        ["K=3", "169 / 122 / 17", "0.10", "State 2 (n=17)", "291 / 308 (94.5%)"],
        ["K=4", "99 / 121 / 72 / 16", "0.13", "State 3 (n=16)", "292 / 308 (94.8%)"],
    ], caption="표 2. 조건별 클러스터 크기와 균형", widths=[0.7, 1.6, 1.1, 1.3, 1.8])

    d.para("소수 State가 제외되는 메커니즘 (K=3, K=4 공통):", indent=0, bold=True, after=60)
    d.para("세그먼트가 subject-level split(seed=42, val 0.15 / test 0.15)으로 나뉘는데, 크기 "
           "16~17개 클러스터는 val split에 하나도 배정되지 않는다(K=3 State 2: 13/0/4, K=4 "
           "State 3: 12/0/4). Early stopping을 위한 validation set이 없으므로 파이프라인이 해당 "
           "클러스터의 학습을 자동으로 스킵한다.")
    bullet(d, "K를 4에서 3으로 줄여도 이 문제는 해결되지 않았다. 크기·원인·결과가 사실상 동일하게 "
              "반복됐다.")
    bullet(d, "그 결과 K=3은 \"3개 상태\"라고 부르지만 표현학습이 검증된 상태는 2개뿐이다. "
              "실질적으로 2-state 분석에 가깝다.")
    bullet(d, "K=2만이 유일하게 모든 클러스터가 학습되고 모든 세그먼트가 사용된 조건이다.")
    d.para("클러스터 크기의 불안정성: K=3의 크기 169/122/17은 파이프라인의 MiniBatchKMeans "
           "결과이고, full-batch KMeans로 같은 데이터를 나누면 152/126/30이 된다. 알고리즘 차이만"
           "으로 최소 클러스터가 17↔30으로 흔들린다는 것은 K=3의 세 번째 상태가 안정적 구조가 "
           "아니라 경계에 놓인 표본 집합임을 시사한다. 반면 K=2는 알고리즘 간 크기 차이가 "
           "작다(138/170 vs 132/176).")

    d.figure(K2 / "fig5_cm_centroids.png",
             "그림 3. [K=2] State별 CM 중심값 + State-specific ROI")
    d.figure(K3 / "fig5_cm_centroids.png",
             "그림 4. [K=3] State별 CM 중심값 + State-specific ROI — 학습에서 제외된 State 2도 포함")

    # ── 3 ──
    d.heading("3. State별 BrainLM 학습 결과 비교", 1, page_break=True)

    hdr = ["State", "Train/Val/Test", "Max TS len", "Train Loss", "Val Loss",
           "Train–Val gap", "에폭", "상태"]
    wid = [0.8, 1.3, 0.9, 0.9, 0.8, 1.1, 0.6, 1.0]

    d.heading("3.1 K=2 (checkpoint/brainlm_v4_k2/)", 2)
    d.table([hdr,
             ["State 0", "96 / 19 / 23", "246", "73.07", "88.66", "15.59", "50", "학습 완료"],
             ["State 1", "116 / 30 / 24", "277", "81.45", "94.65", "13.19", "49", "학습 완료"]],
            caption="표 3. K=2 State별 학습 결과", widths=wid)

    d.heading("3.2 K=3 (checkpoint/brainlm_v4_k3/)", 2)
    d.table([hdr,
             ["State 0", "115 / 30 / 24", "279", "84.23", "93.66", "9.43", "49", "학습 완료"],
             ["State 1", "84 / 19 / 19", "242", "76.69", "91.89", "15.20", "50", "학습 완료"],
             ["State 2", "13 / 0 / 4", "—", "—", "—", "—", "—", "제외 (skip)"]],
            caption="표 4. K=3 State별 학습 결과", widths=wid)

    d.heading("3.3 K=4 (참고, checkpoint/brainlm_v4/)", 2)
    d.table([hdr,
             ["State 0", "62 / 20 / 17", "252", "92.81", "98.83", "6.02", "17", "학습 완료"],
             ["State 1", "86 / 20 / 15", "292", "92.20", "101.15", "8.96", "24", "학습 완료"],
             ["State 2", "52 / 9 / 11", "237", "92.97", "115.67", "22.70", "19", "학습 완료"],
             ["State 3", "12 / 0 / 4", "—", "—", "—", "—", "—", "제외 (skip)"]],
            caption="표 5. K=4 State별 학습 결과 (참고)", widths=wid)

    d.heading("3.4 요약 비교", 2)
    d.table([
        ["지표", "K=2", "K=3", "K=4"],
        ["평균 Train Loss", "77.26", "80.46", "92.66"],
        ["평균 Val Loss", "91.66", "92.78", "105.22"],
        ["Val Loss 편차 (max−min)", "5.99", "1.77", "16.84"],
        ["평균 학습 에폭", "49.5", "49.5", "20.0"],
        ["Early stopping 발동", "없음", "없음", "3개 모두 발동"],
        ["클러스터당 평균 train 예제", "106", "100", "67"],
    ], caption="표 6. K별 학습 결과 요약 비교", widths=[2.0, 1.0, 1.0, 1.3])

    d.para("관찰:", indent=0, bold=True, after=60)
    bullet(d, "K=2와 K=3의 loss는 거의 비슷하고(평균 val 91.66 vs 92.78), 둘 다 K=4보다 확실히 낮다.")
    bullet(d, "K=4는 세 State 모두 early stopping이 발동해 17~24 에폭에서 멈췄다. K=2/K=3은 50 "
              "에폭 상한까지 갔다. 클러스터당 학습 데이터가 많아질수록 과적합 시점이 뒤로 밀린다는 "
              "일관된 경향이다.")
    bullet(d, "다만 이 loss 비교는 그대로 K 선택 근거로 쓸 수 없다. 세 조건은 클러스터당 예제 "
              "수(67 / 100 / 106)와 실제 학습 에폭 수(20 / 49.5 / 49.5)가 모두 다르다. loss 차이의 "
              "상당 부분이 \"데이터가 많고 오래 학습했다\"로 설명 가능하며, 상태 정의의 질과는 "
              "분리되지 않는다. 에폭·예제 수를 통제한 실험이 없으면 이 표는 참고용이다.")
    bullet(d, "K=2/K=3 모두 상한 에폭까지 갔으므로 loss가 수렴값이 아닐 수 있다 — 더 학습하면 더 "
              "내려갈 여지가 남아 있다.")

    d.figure(K2 / "fig1_training_curves.png", "그림 5. [K=2] 클러스터별 BrainLM 학습 곡선")
    d.figure(K3 / "fig1_training_curves.png", "그림 6. [K=3] 클러스터별 BrainLM 학습 곡선")
    d.figure(K4 / "fig1_training_curves.png",
             "그림 7. [K=4, 참고] 클러스터별 BrainLM 학습 곡선 — 세 State 모두 early stopping 발동")

    d.heading("3.5 Loss 절대값에 대한 필수 caveat (모든 조건 공통)", 2)
    d.para("brainlm/ts_model.py의 compute_loss()에 정규화 버그가 있다.")
    code(d, [
        'w = (m * attn).unsqueeze(-1)          # shape: (B, T, 1)',
        'denom = w.sum().clamp_min(1.0)        # timestep 개수만 셈',
        'loss = F.mse_loss(recon * w, labels * w, reduction="sum") / denom',
    ])
    d.para("분자는 (B, T, 100) 전체 원소의 제곱오차 합인데, 분모 w.sum()은 마지막 축이 1이므로 "
           "(B, T) 개수만 센다. ROI feature 차원(=100)으로 나뉘지 않아 보고된 loss가 실제 "
           "element-wise MSE의 약 100배다.")
    d.table([
        ["조건", "보고된 평균 Val Loss", "100으로 나눈 추정 실제 MSE"],
        ["K=2", "91.66", "약 0.92"],
        ["K=3", "92.78", "약 0.93"],
        ["K=4", "105.22", "약 1.05"],
    ], caption="표 7. 스케일 보정 시 추정되는 실제 MSE", widths=[0.8, 1.6, 2.0])
    d.para("정규화된 입력에서 MSE 약 0.9~1.05는 \"분산을 거의 설명하지 못하는 수준(1.0)\"에 "
           "근접한다는 뜻이다. 기존 K=4 리포트의 \"loss 절대값이 100 근처인 것은 raw BOLD 스케일 "
           "때문\"이라는 설명은 틀렸다.")
    bullet(d, "영향 있음: loss 절대값 해석, \"재구성을 잘했다\"는 서술 전체.")
    bullet(d, "영향 없음: State 간·K 간 상대 비교. 동일한 상수 배율이 모든 조건에 적용되므로 "
              "순위와 비율은 보존된다.")
    bullet(d, "위 표들은 수정 전 원본 값을 그대로 기재했다. 논문/발표에서 절대값을 인용하려면 반드시 "
              "정정하거나 caveat을 병기해야 한다.")

    # ── 4 ──
    d.heading("4. Cross-cluster Cosine Similarity (State 분리도) 비교", 1, page_break=True)
    d.table([
        ["조건", "오프-대각 값", "관측 쌍 수", "절댓값 평균"],
        ["K=2", "0.0431 (State0–State1)", "1", "0.043"],
        ["K=3", "0.0681 (State0–State1)", "1", "0.068"],
        ["K=4", "-0.0593 (0–1), -0.0053 (0–2), 0.0477 (1–2) → 평균 -0.0056", "3", "0.037"],
    ], caption="표 8. 조건별 cross-cluster cosine similarity", widths=[0.7, 3.4, 1.0, 1.0])

    d.para("해석 — 여기서는 과장하기 쉬우니 주의해야 한다.", indent=0, bold=True, after=60)
    bullet(d, "세 조건 모두 0에 가깝다. 0.043 / 0.068 / -0.006 어느 것도 \"State 표현이 겹친다\"고 "
              "볼 수 없는 값이며, 직교성 가설과 모순되지 않는다. (참고: V3의 단일 공유 BrainLM은 "
              "cosine 약 0.97로 완전히 실패했었다. 그것과 비교하면 세 조건 다 성공 범주다.)")
    bullet(d, "K=4의 평균 -0.0056이 가장 0에 가까워 보이지만 이는 착시에 가깝다. -0.059와 +0.048이 "
              "서로 상쇄된 결과이며, 절댓값 평균으로 보면 0.037이다. 부호 상쇄를 제거하면 "
              "K=4(0.037) < K=2(0.043) < K=3(0.068) 순이지만, 이 정도 차이를 근거로 우열을 "
              "논하기에는 관측 쌍이 1~3개뿐이고 귀무분포 대비 유의성 검정도 없다.")
    bullet(d, "K가 작을수록 이 지표의 증거력 자체가 약해진다는 구조적 문제가 있다. K=2와 K=3(학습 "
              "2개)은 오프-대각 값이 단 하나여서 산포나 안정성을 논할 수 없고, PCA/t-SNE에서도 "
              "클러스터가 2개면 어떤 투영에서든 둘로 갈라져 보이기 쉽다. K=4는 쌍이 3개라 그나마 "
              "\"여러 쌍이 모두 0 근처\"라는 패턴을 보여준다.")
    bullet(d, "따라서 코사인 지표는 K 선택 근거가 되지 못한다. 이 지표로 K를 고르려는 시도는 "
              "자제하고, \"선택한 K에서 직교성이 유지되는지 확인하는 용도\"로만 써야 한다.")

    d.figure(K2 / "fig3_cosine_and_l2.png", "그림 8. [K=2] Cosine heatmap + latent L2 norm violin")
    d.figure(K3 / "fig3_cosine_and_l2.png", "그림 9. [K=3] Cosine heatmap + latent L2 norm violin")
    d.figure(K4 / "fig3_cosine_and_l2.png",
             "그림 10. [K=4, 참고] Cosine heatmap + latent L2 norm violin — 오프-대각 쌍이 3개")
    d.figure(K2 / "fig2_pooled_latent.png", "그림 11. [K=2] Pooled PCA + t-SNE (L2 정규화 후)")
    d.figure(K3 / "fig2_pooled_latent.png", "그림 12. [K=3] Pooled PCA + t-SNE (L2 정규화 후)")

    # ── 5 ──
    d.heading("5. 조건별 장단점 정리", 1, page_break=True)

    d.heading("5.1 K=2", 2)
    d.para("장점", indent=0, bold=True, after=40)
    bullet(d, "실루엣이 세 조건 중 최고이며(0.241 / 0.227), 서브셋·알고리즘을 바꿔도 1위가 유지된다.")
    bullet(d, "클러스터 균형이 압도적으로 좋다(138 / 170, 비율 0.81).")
    bullet(d, "유일하게 제외된 State가 없고 308개 세그먼트를 100% 사용한다. 표본 부족으로 인한 상태 "
              "소멸 문제가 발생하지 않는다.")
    bullet(d, "클러스터당 학습 데이터가 가장 많고(평균 106 예제), 평균 val loss가 가장 낮다.")
    bullet(d, "클러스터 크기가 알고리즘 변경에 안정적이다.")
    d.para("단점", indent=0, bold=True, after=40)
    bullet(d, "상태 체계가 이분법적이라 해석이 단순해진다. \"State A / State B\"만으로는 dFC "
              "문헌에서 흔히 보고되는 다중 상태 구조(보통 3~7개)와 연결짓기 어렵고, 뇌 상태 전환 "
              "역학(Markov 전이 행렬 등) 분석의 여지도 줄어든다.")
    bullet(d, "오프-대각 코사인이 단 하나뿐이라 직교성 가설 검증의 증거력이 가장 약하다. 2개 "
              "클러스터의 분리는 저차원 투영에서 거의 자동으로 만족되는 관찰이다.")
    bullet(d, "실루엣 0.227~0.241 자체가 \"구조 있음\"을 주장하기에는 여전히 낮다. K=2가 1위인 것이 "
              "\"2개 상태가 실재한다\"는 증거는 아니다 — 데이터에 강한 군집 구조가 없을 때 실루엣은 "
              "대체로 K가 작을수록 높게 나오는 경향이 있다는 점도 함께 고려해야 한다.")
    d.figure(K2 / "fig8_summary_dashboard.png", "그림 13. [K=2] 종합 요약 대시보드")

    d.heading("5.2 K=3", 2)
    d.para("장점", indent=0, bold=True, after=40)
    bullet(d, "실루엣이 K=4보다 확실히 높다(0.185 / 0.170 vs 0.134 / 0.094).")
    bullet(d, "상태가 3개라 해석·서술의 여지가 K=2보다 넓다. 선행 dFC 연구의 상태 개수 범위와도 더 "
              "잘 맞고, 논문 스토리상 \"다중 상태 체계\"를 유지할 수 있다.")
    bullet(d, "학습된 두 State의 val loss 편차가 가장 작다(1.77). K=4의 16.84와 대조적이다.")
    bullet(d, "K=4와 동등 이상의 학습 안정성(early stopping 미발동, 상한까지 학습).")
    d.para("단점", indent=0, bold=True, after=40)
    bullet(d, "K=4의 핵심 문제가 그대로 반복된다. State 2(n=17, val=0)가 학습에서 제외되어, 실제로 "
              "검증된 상태는 2개뿐이다. \"3개 상태 체계\"라고 쓰지만 결과로 보여줄 수 있는 것은 2개다.")
    bullet(d, "세 번째 클러스터가 알고리즘에 따라 17↔30으로 흔들려 구조적으로 불안정하다.")
    bullet(d, "결국 학습·코사인 결과는 K=2와 거의 구별되지 않으면서(평균 val loss 92.78 vs 91.66, "
              "오프-대각 쌍 1개로 동일), 실루엣만 낮은 조건이 된다. 즉 K=2 대비 얻는 것이 \"명목상 "
              "상태 개수\"뿐일 수 있다.")
    d.figure(K3 / "fig8_summary_dashboard.png", "그림 14. [K=3] 종합 요약 대시보드")

    d.heading("5.3 K=4 (기존)", 2)
    d.para("장점", indent=0, bold=True, after=40)
    bullet(d, "학습된 State가 3개라 오프-대각 코사인 쌍이 3개 — 직교성 가설 검증에는 가장 정보량이 "
              "많다.")
    bullet(d, "상태 해석의 다양성이 가장 크다.")
    d.para("단점", indent=0, bold=True, after=40)
    bullet(d, "실루엣이 명확한 하위권이고 애초에 탐색 없이 하드코딩된 값이었다.")
    bullet(d, "State 3(n=16)이 제외되어 4개 중 3개만 검증됐다.")
    bullet(d, "세 State 모두 early stopping이 조기에 발동(17~24 에폭)했고 평균 val loss가 가장 "
              "높으며 State 간 편차도 가장 크다(State 2가 115.67로 이탈).")
    d.figure(K4 / "fig8_summary_dashboard.png", "그림 15. [K=4, 참고] 종합 요약 대시보드")

    # ── 6 ──
    d.heading("6. 추천", 1, page_break=True)
    d.para("주 분석은 K=2, 보조(robustness) 분석은 K=3으로 보고하는 것을 추천한다.",
           indent=0, bold=True)
    d.para("근거는 다음과 같다.")
    for i, t in enumerate([
        "데이터가 지지하는 유일한 정량 근거인 실루엣은 K=2를 가리킨다. train subset / 전체 / "
        "KMeans / MiniBatchKMeans 네 조건에서 모두 1위이고, K=3과의 격차(약 0.056)는 조건에 따라 "
        "뒤집히지 않는다.",
        "K=2만이 상태 소멸 문제를 겪지 않는다. K=3과 K=4는 소수 클러스터(n=16~17)가 validation "
        "set을 만들지 못해 제외되는 동일한 실패를 반복한다. \"3-state를 정의했지만 2개만 "
        "검증했다\"는 서술은 방어하기 어렵고, 이미 논문 Limitations에 지적된 약점을 그대로 남기는 "
        "셈이다.",
        "loss와 코사인은 K=2와 K=3을 실질적으로 구별하지 못한다. 평균 val loss 차이 1.1(스케일 "
        "보정 시 MSE 0.01 수준), 오프-대각 쌍은 양쪽 다 1개. 즉 K=3을 택해도 결과 품질에서 얻는 "
        "것이 없으면서 실루엣만 낮아진다.",
    ], 1):
        d.para(f"{i}. {t}", indent=0, after=80)

    d.para("단, K=3을 완전히 버리지 않고 함께 보고할 이유도 분명하다.", indent=0, bold=True)
    bullet(d, "해석가능성·선행연구 정합성 측면에서 3-state가 더 풍부하며, K=3의 State 2는 학습만 못 "
              "했을 뿐 CM centroid 자체는 존재한다(visualization_ver4_k3/fig5_cm_centroids.png에 "
              "3개 모두 그려져 있다). \"표본 부족으로 검증하지 못한 희소 상태\"로 정직하게 서술하면 "
              "향후 연구 방향으로 연결된다.")
    bullet(d, "실루엣이 전반적으로 낮은 상황에서 K 하나에만 결과를 걸면 취약하다. \"K=2와 K=3 "
              "양쪽에서 State 간 latent 직교성이 유지된다\"는 서술이 K 선택에 대한 민감도를 보여주는 "
              "강한 근거가 된다.")
    d.para("K=4는 주 분석에서 내리는 것이 맞다. 실루엣 하위권, 근거 없는 하드코딩, 상태 소멸, 가장 "
           "높은 loss와 가장 큰 State 간 편차 — 어느 축으로도 우위가 없다. 기존 결과와의 연속성을 "
           "보이기 위해 부록/비교 표에만 남기는 정도가 적절하다.")

    d.heading("6.1 함께 반드시 명시해야 할 한계", 2)
    d.para("이 추천은 \"주어진 선택지 중 무엇이 나은가\"에 대한 답이지, \"K=2가 옳은 상태 구조\"라는 "
           "주장이 아니다.")
    bullet(d, "모든 K에서 실루엣이 낮다. 최고값(0.241)조차 관례상 \"실질적 군집 구조를 찾지 못함\" "
              "경계에 있다. 이 데이터의 CM 공간이 이산적 상태로 잘 나뉘지 않을 가능성을 논문에서 "
              "배제하지 말아야 한다.")
    bullet(d, "표본이 근본 원인이다. 27명 / 308세그먼트로는 소수 상태에 validation을 배정할 수 없다. "
              "K를 줄이는 것은 이 문제를 회피하는 것이지 해결하는 것이 아니다.")
    bullet(d, "무작위 세그먼테이션 대조군이 아직 없다. 코사인이 0 근처라는 관찰은 대조군 없이는 "
              "\"MTAD-GAT 변화점이 의미 있다\"의 증거가 되지 못한다. 이 baseline이 K 선택보다 "
              "우선순위가 높다.")
    bullet(d, "loss 절대값은 약 100배 부풀려져 있다 (compute_loss() 분모 버그). 상대 비교는 유효하나 "
              "절대값 인용 전 수정이 필요하다.")

    # ── 7 ──
    d.heading("7. 권장 후속 작업 (우선순위 순)", 1)
    for i, t in enumerate([
        "무작위 세그먼테이션 baseline 실행. anomaly point 없이 동일 길이로 자른 세그먼트에 같은 "
        "파이프라인을 적용해 cosine 분포를 비교. 이것이 가설 검증의 핵심이며 K 선택보다 중요하다.",
        "compute_loss() 분모 수정 후 재학습. 절대 MSE를 인용하는 모든 서술의 전제.",
        "소수 상태 처리 방침 확정. (a) 피험자 수 확대, (b) subject-level split 대신 계층화"
        "(stratified) split으로 val 확보, (c) 소수 클러스터를 최근접 클러스터에 병합 — 중 하나를 "
        "택하고 논문에 명시. (b)를 쓰면 K=3의 State 2도 학습 가능해져 K=3이 다시 유력 후보가 된다.",
        "K 선택 근거를 Methods에 직접 기술. find_optimal_k.py 결과 표와 "
        "result/optimal_k/elbow_silhouette_train.png, elbow_silhouette_full.png를 포함하고, "
        "K=4가 하드코딩이었다는 점을 정정.",
        "에폭·예제 수를 통제한 K 간 재비교. 현재 loss 비교는 학습량 교란이 커서 근거로 쓸 수 없다.",
        "클러스터 안정성 정량화. bootstrap/재샘플링으로 클러스터 재현율(ARI 등)을 측정하면 "
        "실루엣보다 K 선택에 설득력 있는 근거가 된다.",
    ], 1):
        d.para(f"{i}. {t}", indent=0, after=80)

    # ── 8 ──
    d.heading("8. 산출물 경로", 1)
    code(d, [
        "result/optimal_k/",
        "├── optimal_k_train.csv           # 실루엣/inertia (train 19명 기준, K=2~10)",
        "├── optimal_k_full.csv            # 실루엣/inertia (전체 27명 기준, K=2~10)",
        "├── elbow_silhouette_train.png    # elbow + 실루엣 곡선 (train)",
        "└── elbow_silhouette_full.png     # elbow + 실루엣 곡선 (전체)",
        "",
        "visualization_ver4_k2/            # K=2 결과 (fig1~fig8, latents, csv, json)",
        "visualization_ver4_k3/            # K=3 결과 (fig1~fig8, latents, csv, json)",
        "visualization_ver4/               # K=4 결과 (기존)",
        "",
        "checkpoint/brainlm_v4_k2/         # cluster_0, cluster_1",
        "checkpoint/brainlm_v4_k3/         # cluster_0, cluster_1 (cluster_2는 학습 제외)",
        "checkpoint/brainlm_v4/            # cluster_0~2 (cluster_3는 학습 제외)",
    ])

    d.para("시각화 파일 (K=2 / K=3 동일 구성)", indent=0, bold=True, after=60)
    d.table([
        ["파일", "내용"],
        ["fig1_training_curves.png", "클러스터별 BrainLM 학습 곡선"],
        ["fig2_pooled_latent.png", "Pooled PCA + t-SNE (L2 정규화 후)"],
        ["fig3_cosine_and_l2.png", "Cross-cluster cosine heatmap + L2 norm violin"],
        ["fig4_latent_profile.png", "평균 latent 프로파일 + PCA 누적 분산"],
        ["fig5_cm_centroids.png", "State별 CM 중심값 + State-specific ROI (K=3은 제외된 State 2도 포함)"],
        ["fig6_subject_state.png", "피험자별 State 유사도 + 점유율"],
        ["fig7_v2_vs_v4.png",
         "V2(CM 입력) vs V4(Raw TS 입력) 비교 — 주의: V2 쪽은 K=4 시절 결과를 그대로 로드하므로 "
         "K=2/K=3과의 직접 비교가 아니다"],
        ["fig8_summary_dashboard.png", "종합 요약 대시보드"],
    ], caption="표 9. 시각화 파일 목록", widths=[1.5, 3.5])

    d.para("관련 리포트: REPORT_V4_K3.md (K=3 상세), VISUALIZATION_REPORT_V4.md (기존 K=4 상세)",
           indent=0)

    # 부록 — 나머지 그림
    d.heading("부록 A. K=2 / K=3 나머지 시각화", 1, page_break=True)
    d.figure(K2 / "fig4_latent_profile.png", "그림 A1. [K=2] 평균 latent 프로파일 + PCA 누적 분산")
    d.figure(K3 / "fig4_latent_profile.png", "그림 A2. [K=3] 평균 latent 프로파일 + PCA 누적 분산")
    d.figure(K2 / "fig6_subject_state.png", "그림 A3. [K=2] 피험자별 State 유사도 + 점유율")
    d.figure(K3 / "fig6_subject_state.png", "그림 A4. [K=3] 피험자별 State 유사도 + 점유율")
    d.figure(K2 / "fig7_v2_vs_v4.png",
             "그림 A5. [K=2] V2(CM) vs V4(Raw TS) 비교 — V2 쪽은 K=4 시절 결과")
    d.figure(K3 / "fig7_v2_vs_v4.png",
             "그림 A6. [K=3] V2(CM) vs V4(Raw TS) 비교 — V2 쪽은 K=4 시절 결과")

    out = ROOT / "REPORT_K2_VS_K3.docx"
    d.save(out)
    return out, len(d.images)


if __name__ == "__main__":
    for path, n in (build_k3(), build_cmp()):
        print(f"저장: {path}  ({path.stat().st_size / 1024:.0f} KB, 그림 {n}개)")
