"""검토 피드백 2차까지 반영 — Downloads 의 초록 docx 를 제자리에서 수정한다.

사용자가 손으로 고친 부분(소속, Yeo 참고문헌 추가)을 보존해야 하므로
build_khbm.py 로 새로 생성하지 않고 기존 파일의 문단 텍스트만 교체한다.
"""
import copy
import shutil
from pathlib import Path

from docx import Document
from docx.text.run import Run

SRC = Path("/Users/mac/Downloads/abstract_GihoKang.docx")
BAK = SRC.with_name(SRC.stem + "_수정전백업.docx")
shutil.copy(SRC, BAK)
d = Document(SRC)
P = d.paragraphs


def set_text(idx, text):
    """첫 run 의 서식을 유지한 채 문단 내용만 교체."""
    p = P[idx]
    assert p.runs, f"para {idx} 에 run 이 없음"
    p.runs[0].text = text
    for r in p.runs[1:]:
        r._element.getparent().remove(r._element)


def clone_runs_from(src_idx, dst_idx, parts):
    """src 문단의 run 서식을 복제해 dst 문단을 (텍스트, 위첨자) 목록으로 채운다."""
    src, dst = P[src_idx], P[dst_idx]
    for r in list(dst.runs):
        r._element.getparent().remove(r._element)
    for text, sup in parts:
        tmpl = copy.deepcopy(src.runs[0 if sup else -1]._element)
        dst._p.append(tmpl)
        run = Run(tmpl, dst)
        run.text = text
        run.font.superscript = True if sup else None


# ── 소속 통일 ───────────────────────────────────────────────────────────────
P[4].runs[1].text = ("Department of Artificial Intelligence Convergence, Korea University, "
                     "Seoul, Republic of Korea")
clone_runs_from(4, 5, [("2", True),
                       ("Center for Neuroscience Imaging Research, Institute for Basic "
                        "Science, Suwon, Republic of Korea", False)])
P[33].runs[1].text = "고려대학교 인공지능융합학과"
for r in P[33].runs[2:]:
    pass  # ", 서울, 대한민국" 유지

# ── 영문 Objective ──────────────────────────────────────────────────────────
set_text(9,
    "Resting-state functional magnetic resonance imaging (fMRI) signals are thought to "
    "transition among recurring connectivity configurations, commonly termed brain states "
    "[1]. These are usually delineated with fixed sliding windows, which impose an "
    "arbitrary temporal scale. Here, state boundaries were placed at change points in the "
    "latent space of a multivariate time-series anomaly detection model (MTAD-GAT) [2], "
    "and the resulting segments were grouped into states by clustering their functional "
    "connectivity. We asked whether these states differ in the strength of functional "
    "connectivity, quantified by degree centrality (DC), and in their temporal "
    "persistence, quantified by dwell time, and we tested both against an explicit "
    "random-segmentation null model rather than against chance alone.")

# ── 영문 Methods ────────────────────────────────────────────────────────────
set_text(12,
    "Resting-state fMRI from 27 unrelated Human Connectome Project participants [4] "
    "(1,200 volumes; repetition time = 0.72 s) was parcellated into 100 cortical regions "
    "using the Schaefer atlas [3] and grouped into seven Yeo networks [5]. Segment "
    "boundaries were placed at the largest changes in the gated recurrent unit hidden "
    "state of an MTAD-GAT model trained on a disjoint set of 70 participants, yielding "
    "308 segments. For each segment a Pearson functional connectivity matrix was computed, "
    "Fisher-z transformed, and clustered by k-means to assign state labels. DC was defined "
    "by retaining, in each row, the strongest 10% of the signed Fisher-z values and "
    "summing them, giving a weighted degree (node strength) rather than an edge count; the "
    "retained decile was positive throughout, so negative correlations were not rectified. "
    "Dwell time was computed per participant as the number of volumes assigned to a state "
    "multiplied by the repetition time, both as total occupancy and as mean duration per "
    "continuous visit. Statistical units were (participant × state) pairs, of which 75 "
    "of the 108 possible pairs were available because not every participant visited every "
    "state; these were compared using one-way analysis of variance and pairwise two-sample "
    "t-tests. Because state labels are derived from the same time series that produced the "
    "segmentation, the observed effect sizes were compared with a random-segmentation null "
    "in which each participant's segment lengths were reordered 1,000 times, preserving "
    "the number and the length distribution of segments while destroying their placement; "
    "connectivity estimation and k-means clustering were repeated in full for every "
    "reordering. All analyses used K = 4.")

# ── 영문 Results ────────────────────────────────────────────────────────────
set_text(15,
    "DC differed strongly across states (K = 4: F(3,71) = 218.56, p < 0.001, eta-squared = "
    "0.90), with all six state pairs significant, all 100 regions surviving false "
    "discovery rate correction, and all seven Yeo networks differing. Dwell time also "
    "differed across states (mean duration per visit: F(3,71) = 10.78, p < 0.001, "
    "eta-squared = 0.31; total occupancy: F(3,71) = 6.39, p < 0.001), with the lowest-DC "
    "state persisting the longest and the highest-DC state being the briefest (mean "
    "duration per visit 340.8 +/- 298.4 s and 66.3 +/- 53.0 s, respectively). These "
    "effects exceeded the random-segmentation null (mean duration per visit, observed "
    "eta-squared 0.32 vs. null 0.15 +/- 0.05, p = 0.003; total occupancy, 0.21 vs. "
    "0.12 +/- 0.04, p = 0.030; observed values were re-estimated under the null pipeline, "
    "which accounts for the small difference from the eta-squared reported above). Of the "
    "seven measures tested against this null, only mean duration per visit survived "
    "Bonferroni correction (alpha = 0.05/7 = 0.0071). By contrast, five measures of "
    "connectivity structure - within-segment homogeneity, boundary contrast, and "
    "clustering silhouette at K = 2, 3 and 4 - did not exceed the same null (all "
    "p > 0.1), indicating that the change points capture differences in state persistence "
    "rather than greater within-state connectivity coherence.")

# ── 영문 Conclusion (검토자 제안문 그대로) ──────────────────────────────────
set_text(18,
    "Brain states identified from MTAD-GAT-derived change points exhibited significant "
    "differences in degree centrality and dwell time, with lower-centrality states tending "
    "to persist longer. Importantly, the difference in mean dwell time per visit remained "
    "significant against a random-segmentation null model after correction for multiple "
    "comparisons, whereas the connectivity-structure measures did not show significant "
    "improvements over the null. These findings suggest that temporal persistence may be a "
    "more robust feature of the identified states than within-state connectivity "
    "coherence. Our results highlight the importance of explicit null-model validation "
    "when evaluating data-driven brain-state segmentation methods.")

# ── 국문 연구 목적 ──────────────────────────────────────────────────────────
set_text(37,
    "휴지기 기능적 자기공명영상(fMRI) 신호는 반복적으로 나타나는 연결성 구성 사이를 "
    "전환하며, 이를 뇌 상태(brain state)라 한다[1]. 기존 연구는 대개 고정 길이 슬라이딩 "
    "윈도우로 상태를 구분하는데, 이는 시간 척도를 임의로 정하는 한계가 있다. 본 연구는 "
    "다변량 시계열 이상탐지 모델(MTAD-GAT)의 잠재 공간에서 나타나는 변화점으로 상태 "
    "경계를 정의하고[2], 산출된 세그먼트의 기능적 연결성을 군집화하여 상태를 부여하였다. "
    "이 상태들이 연결 중심성(degree centrality, DC)으로 본 기능적 연결 강도와 체류 "
    "시간(dwell time)에서 서로 다른지, 그리고 그 차이가 우연 수준이 아니라 명시적 무작위 "
    "분할 귀무 모형을 넘어서는지 검정하였다.")

# ── 국문 연구 방법 ──────────────────────────────────────────────────────────
set_text(40,
    "Human Connectome Project[4]의 비혈연 피험자 27명의 휴지기 fMRI(1,200 volume, "
    "반복시간 0.72초)를 Schaefer 아틀라스[3]로 100개 피질 영역으로 분할하고 Yeo 7개 "
    "네트워크[5]로 묶었다. 독립된 70명으로 학습한 MTAD-GAT의 GRU 은닉상태 변화량이 가장 "
    "큰 지점을 경계로 삼아 총 308개 세그먼트를 얻었다. 각 세그먼트에서 Pearson 기능적 "
    "연결성 행렬을 구해 Fisher-z 변환한 뒤 k-means 군집화로 상태를 부여하였다. DC는 각 "
    "행에서 부호를 유지한 Fisher-z 값 가운데 상위 10%만 남겨 합산한 값으로, 연결 개수가 "
    "아니라 연결 강도의 합(weighted degree, node strength)이다. 남은 상위 10%는 모두 "
    "양수였으므로 음의 상관에 대한 별도 처리는 적용하지 않았다. 체류 시간은 피험자별로 "
    "해당 상태에 배정된 volume 수에 반복시간을 곱해 총 점유 시간과 방문당 평균 체류 시간 "
    "두 가지로 계산하였다. 분석 단위는 (피험자 × 상태) 쌍으로 설정하였으며, 모든 피험자가 "
    "모든 상태를 방문한 것은 아니어서 가능한 108쌍 중 75쌍을 분석에 사용하였고, "
    "일원분산분석과 쌍별 이표본 t-검정을 수행하였다. 상태 레이블은 분할에 쓰인 것과 같은 "
    "시계열에서 유도되므로, 관측된 효과크기를 무작위 분할 귀무 모형과도 비교하였다. "
    "피험자마다 세그먼트 길이의 순서만 1,000회 섞어 세그먼트 개수와 길이 분포는 보존하되 "
    "위치만 무너뜨린 분할을 만들고, 각 반복마다 연결성 행렬 산출부터 k-means 군집화까지 "
    "전 과정을 다시 수행하였다. 모든 분석은 K = 4를 사용하였다.")

# ── 국문 연구 결과 ──────────────────────────────────────────────────────────
set_text(43,
    "DC는 상태 간에 뚜렷하게 달랐다(K = 4: F(3,71) = 218.56, p < 0.001, η² = 0.90). "
    "6개 상태 쌍 모두 유의하였고, 100개 영역 전부와 Yeo 7개 네트워크 전부가 FDR 보정 "
    "후에도 유의하였다. 체류 시간 역시 상태 간에 달랐고(방문당 평균: F(3,71) = 10.78, "
    "p < 0.001, η² = 0.31; 총 점유: F(3,71) = 6.39, p < 0.001), DC가 가장 낮은 상태가 "
    "가장 오래, 가장 높은 상태가 가장 짧게 유지되었다(방문당 평균 체류 시간 각각 "
    "340.8 ± 298.4초, 66.3 ± 53.0초). 이 효과는 무작위 분할 귀무분포를 초과하였다"
    "(방문당 평균: 관측 η² 0.32 대 귀무 0.15 ± 0.05, p = 0.003; 총 점유: 0.21 대 "
    "0.12 ± 0.04, p = 0.030. 관측값은 귀무 모형과 동일한 절차로 다시 산출한 것이어서 "
    "위에 보고한 η²와 미세한 차이가 있다). 이 귀무 모형으로 검정한 7개 지표 가운데 "
    "Bonferroni 보정(α = 0.05/7 = 0.0071)을 통과한 것은 방문당 평균 체류 시간 하나였다. "
    "반면 연결성 구조를 재는 다섯 지표, 즉 세그먼트 내부 동질성, 경계 대비, "
    "K = 2·3·4에서의 군집 실루엣은 같은 귀무분포를 넘지 못하였다(모두 p > 0.1). 즉 "
    "변화점은 상태의 지속 시간 차이를 포착하였을 뿐, 상태 내부 연결성에서 무작위 분할 "
    "대비 우월한 일관성을 보이지는 않았다.")

# ── 국문 결론 ───────────────────────────────────────────────────────────────
set_text(46,
    "MTAD-GAT의 변화점으로 정의한 뇌 상태는 연결 중심성과 체류 시간에서 유의한 차이를 "
    "보였으며, 연결 중심성이 낮은 상태일수록 더 오래 유지되는 경향이 있었다. 특히 방문당 "
    "평균 체류 시간의 차이는 다중비교 보정 후에도 무작위 분할 귀무 모형에 대해 유의하게 "
    "유지된 반면, 연결성 구조 지표들은 귀무 모형 대비 유의한 개선을 보이지 않았다. 이는 "
    "시간적 지속성이 상태 내부 연결성의 일관성보다 더 견고한 특성일 수 있음을 시사한다. "
    "본 결과는 데이터 기반 뇌 상태 분할 방법을 평가할 때 명시적 귀무 모형 검증이 "
    "중요함을 보여준다.")

d.save(SRC)
print(f"수정 완료: {SRC}")
print(f"수정 전 백업: {BAK}")
