"""KHBM 2025 초록 — 템플릿 서식을 그대로 두고 내용만 교체."""
import copy
import shutil
from pathlib import Path

from docx import Document

ROOT = Path("/Users/mac/Desktop/code/MTAD-GAT")
SRC = ROOT / "KHBM_fall_2025_final.docx"
OUT = ROOT / "KHBM_2025_abstract_GihoKang.docx"
shutil.copy(SRC, OUT)
d = Document(OUT)
P = d.paragraphs


def set_text(idx, text):
    """첫 run의 서식을 유지한 채 문단 내용만 교체."""
    p = P[idx]
    if not p.runs:
        p.add_run(text)
        return
    p.runs[0].text = text
    for r in p.runs[1:]:
        r._element.getparent().remove(r._element)


def set_runs(idx, parts):
    """(텍스트, 위첨자여부) 목록으로 문단 재구성. 첫 run 서식을 복제해 사용."""
    p = P[idx]
    base = p.runs[0]
    tmpl = copy.deepcopy(base._element)
    for r in list(p.runs):
        r._element.getparent().remove(r._element)
    from docx.text.run import Run
    for text, sup in parts:
        el = copy.deepcopy(tmpl)
        p._p.append(el)
        run = Run(el, p)
        run.text = text
        run.font.superscript = True if sup else None


# ── 제목 ────────────────────────────────────────────────────────────────────
set_text(0, "Brain states defined from anomaly-detection change points differ in "
            "degree centrality and dwell time")
set_text(1, "이상탐지 변화점으로 정의한 뇌 상태의 연결 중심성과 체류 시간 차이")

# ── 저자 / 소속 ─────────────────────────────────────────────────────────────
set_runs(3, [("Giho Kang", False), ("1", True), (", Bo-yong Park", False),
             ("1,2*", True)])
def set_affil(idx, num, body):
    """소속 줄: run0(위첨자 번호) + run1(이탤릭 본문) 구조를 그대로 유지."""
    p = P[idx]
    p.runs[0].text = num          # 원본 run0 = 위첨자
    p.runs[1].text = body         # 원본 run1 = 이탤릭 본문
    for r in p.runs[2:]:
        r._element.getparent().remove(r._element)


set_affil(4, "1", "Department of Brain and Cognitive Engineering, Korea University, "
                  "Seoul, Republic of Korea")
set_affil(5, "2", "Center for Neuroscience Imaging Research, Institute for Basic Science, "
                  "Suwon, Republic of Korea")
# 소속 3번째 줄 제거
P[6]._element.getparent().remove(P[6]._element)
P = d.paragraphs  # 인덱스 재계산


def find(label):
    for i, p in enumerate(P):
        if p.text.strip() == label:
            return i
    raise KeyError(label)


# ── 본문 ────────────────────────────────────────────────────────────────────
OBJ = (
    "Resting-state functional magnetic resonance imaging (fMRI) signals are thought to "
    "transition among recurring connectivity configurations, commonly termed brain states "
    "[1]. These are usually delineated with fixed sliding windows, which impose an "
    "arbitrary temporal scale. Here state boundaries were instead placed at change points "
    "in the embedding of a multivariate time-series anomaly detection model (MTAD-GAT) "
    "[2], and the resulting segments were grouped into states by clustering their "
    "functional connectivity. We asked whether these states differ in the strength of "
    "connectivity hubs, quantified by degree centrality (DC), and in temporal "
    "persistence, quantified by dwell time, and we tested both against an explicit null "
    "model rather than against chance alone."
)
MET = (
    "Resting-state fMRI from 27 unrelated Human Connectome Project participants [4] "
    "(1,200 "
    "volumes; repetition time = 0.72 s) was parcellated into 100 cortical regions using "
    "the Schaefer atlas and grouped into seven Yeo networks [3]. Segment boundaries were "
    "placed at the largest changes in the gated recurrent unit hidden state of an MTAD-GAT "
    "model trained on a disjoint set of 70 participants, yielding 308 segments. For each "
    "segment a Pearson functional connectivity matrix was computed, Fisher-z transformed, "
    "and clustered by k-means to assign state labels. DC was defined by retaining the "
    "strongest 10% of connections in each row and summing them. Dwell time was "
    "computed per participant as the number of volumes assigned to a state multiplied by "
    "the repetition time, both as total occupancy and as mean duration per continuous "
    "visit. Observations were (participant x state) pairs, compared using one-way analysis "
    "of variance and pairwise two-sample t-tests. Because state labels are derived from the "
    "same time series that produced the segmentation, the effects were also compared "
    "against a random-segmentation null in which each participant's segment lengths were "
    "reordered 1,000 times, preserving the number and the length distribution of segments "
    "while destroying their placement. All analyses used K = 4."
)
RES = (
    "DC differed strongly across states (K = 4: F(3,71) = 218.56, p < 0.001, eta-squared = "
    "0.90), with all six state pairs significant, all 100 regions surviving false "
    "discovery rate correction, and all seven Yeo networks differing. Dwell time also differed across "
    "states (mean duration per visit: F(3,71) = 10.78, p < 0.001, eta-squared = 0.31; "
    "total occupancy: F(3,71) = 6.39, p < 0.001), with the lowest-DC state persisting "
    "longest (340.8 +/- 298.4 s) and the highest-DC state briefest (66.3 +/- 53.0 s); this "
    "exceeded the random-segmentation null (eta-squared 0.32 vs. 0.15 +/- 0.05, p = 0.003 "
    "for mean duration per visit; 0.21 vs. 0.12 +/- 0.04, p = 0.030 for total occupancy; "
    "of the seven measures tested against this null, only mean duration per visit "
    "survives Bonferroni correction). "
    "By contrast, five measures of connectivity structure - within-segment homogeneity, "
    "boundary contrast, and clustering silhouette at K = 2, 3 and 4 - did not exceed the "
    "same null (all p > 0.1), indicating that the change points improve how long states "
    "persist rather than how internally coherent their connectivity is."
)
CON = (
    "Brain states delineated from anomaly-detection change points differ in degree "
    "centrality and in how long they persist, with lower-centrality states persisting "
    "longer, and the dwell-time difference survives a random-segmentation null that the "
    "connectivity-structure measures do not. Temporal persistence therefore appears to be "
    "the property these states capture most reliably, whereas the spatial organisation of "
    "connectivity within a state is no more coherent than a random segmentation would "
    "produce. Data-driven brain states should accordingly be judged against explicit null "
    "models rather than against chance."
)
ACK = ("[연구비 지원 문구를 여기에 기입하십시오.]")

set_text(find("Objective") + 1, OBJ)
set_text(find("Methods") + 1, MET)
set_text(find("Results") + 1, RES)
set_text(find("Conclusion") + 1, CON)
set_text(find("Acknowledgements") + 1, ACK)

# ── 참고문헌 ────────────────────────────────────────────────────────────────
REFS = [
    "1.\tAllen, E.A., et al., Tracking whole-brain connectivity dynamics in the resting "
    "state. Cerebral Cortex, 2014. 24(3): p. 663-676.",
    "2.\tZhao, H., et al., Multivariate time-series anomaly detection via graph attention "
    "network. IEEE International Conference on Data Mining (ICDM), 2020: p. 841-850.",
    "3.\tSchaefer, A., et al., Local-global parcellation of the human cerebral cortex from "
    "intrinsic functional connectivity MRI. Cerebral Cortex, 2018. 28(9): p. 3095-3114.",
    "4.\tVan Essen, D.C., et al., The WU-Minn Human Connectome Project: an overview. "
    "NeuroImage, 2013. 80: p. 62-79.",
]
ref_start = find("References") + 1
for i, txt in enumerate(REFS):
    set_text(ref_start + i, txt)
for extra in list(P[ref_start + len(REFS):ref_start + 5]):   # 템플릿의 남는 줄 제거
    if extra.text.strip():
        extra._element.getparent().remove(extra._element)

# ── 국문본 추가 ─────────────────────────────────────────────────────────────
from docx.enum.text import WD_BREAK

last = d.paragraphs[-1]
br = last.add_run()
br.add_break(WD_BREAK.PAGE)


def add_para(text, bold=False, size=None, italic=False):
    p = d.add_paragraph()
    p.alignment = P[10].alignment
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.bold = bold
    r.font.italic = italic
    if size:
        from docx.shared import Pt
        r.font.size = Pt(size)
    from docx.oxml.ns import qn
    rPr = r._element.get_or_add_rPr()
    rf = rPr.find(qn("w:rFonts"))
    if rf is None:
        from docx.oxml import OxmlElement
        rf = OxmlElement("w:rFonts")
        rPr.append(rf)
    rf.set(qn("w:eastAsia"), "바탕")
    return p


add_para("[국문본] 이상탐지 변화점으로 정의한 뇌 상태의 연결 중심성과 체류 시간 차이",
         bold=True, size=14)
add_para("강기호¹, 박보용¹²*")
add_para("¹고려대학교 뇌공학과, 서울, 대한민국", italic=True)
add_para("²기초과학연구원 뇌과학이미징연구단, 수원, 대한민국", italic=True)
add_para("")

add_para("연구 목적", bold=True)
add_para(
    "휴지기 기능적 자기공명영상(fMRI) 신호는 반복적으로 나타나는 연결성 구성 사이를 "
    "전환하며, 이를 뇌 상태(brain state)라 한다[1]. 기존 연구는 대개 고정 길이 슬라이딩 "
    "윈도우로 상태를 구분하는데, 이는 시간 척도를 임의로 정하는 한계가 있다. 본 연구는 "
    "다변량 시계열 이상탐지 모델(MTAD-GAT)의 임베딩 변화점에서 상태 경계를 정의하고[2], "
    "그렇게 얻은 세그먼트의 기능적 연결성을 군집화하여 상태를 부여하였다. 이 상태들이 "
    "연결 중심성(degree centrality, DC)으로 본 허브의 강도와 체류 시간(dwell time)에서 "
    "서로 다른지, 그리고 그 차이가 우연 수준이 아니라 명시적 귀무 모형을 넘어서는지 "
    "검정하였다.")
add_para("")

add_para("연구 방법", bold=True)
add_para(
    "Human Connectome Project[4]의 비혈연 피험자 27명의 휴지기 fMRI(1,200 volume, "
    "반복시간 0.72초)를 Schaefer 아틀라스로 100개 피질 영역으로 분할하고 Yeo 7개 "
    "네트워크로 묶었다[3]. 독립된 70명으로 학습한 MTAD-GAT의 GRU 은닉상태 변화량이 "
    "가장 큰 지점을 경계로 삼아 총 308개 세그먼트를 얻었다. 각 세그먼트에서 Pearson "
    "기능적 연결성 행렬을 구해 Fisher-z 변환한 뒤 k-means 군집화로 상태를 부여하였다. "
    "DC는 각 행에서 상위 10% 연결만 남겨 합산한 값으로 정의하였다. 체류 시간은 피험자별로 "
    "해당 상태에 배정된 volume 수에 반복시간을 곱해 총 점유 시간과 방문당 평균 체류 "
    "시간 두 가지로 계산하였다. 관측 단위는 (피험자 x 상태) 쌍으로 하여 일원분산분석과 "
    "쌍별 이표본 t-검정을 수행하였다. 상태 레이블은 분할에 쓰인 것과 같은 시계열에서 "
    "유도되므로, 효과를 무작위 분할 귀무 모형과도 비교하였다. 피험자마다 세그먼트 "
    "길이의 순서만 1,000회 섞어 세그먼트 개수와 길이 분포는 보존하되 위치만 무너뜨린 "
    "분할을 만들어 대조하였다. 모든 분석은 K = 4를 사용하였다.")
add_para("")

add_para("연구 결과", bold=True)
add_para(
    "DC는 상태 간에 뚜렷하게 달랐다(K = 4: F(3,71) = 218.56, p < 0.001, η² = 0.90). "
    "6개 상태 쌍 모두 유의하였고, 100개 영역 전부와 Yeo 7개 네트워크 전부가 FDR 보정 "
    "후에도 유의하였다. 체류 시간 역시 상태 간에 달랐고"
    "(방문당 평균: F(3,71) = 10.78, p < 0.001, η² = 0.31; 총 점유: F(3,71) = 6.39, "
    "p < 0.001), DC가 가장 낮은 상태가 가장 오래(340.8 ± 298.4초), 가장 높은 상태가 "
    "가장 짧게(66.3 ± 53.0초) 유지되었다. 이 효과는 무작위 분할 귀무분포를 초과하였다"
    "(방문당 평균 η² 0.32 대 0.15 ± 0.05, p = 0.003; 총 점유 η² 0.21 대 0.12 ± 0.04, "
    "p = 0.030. 이 귀무 모형으로 검정한 7개 지표 가운데 Bonferroni 보정을 통과하는 "
    "것은 방문당 평균 하나이다). 반면 연결성 구조를 재는 다섯 지표, 즉 세그먼트 내부 "
    "동질성, 경계 대비, "
    "K = 2·3·4에서의 군집 실루엣은 같은 귀무분포를 넘지 못하였다(모두 p > 0.1). 즉 "
    "변화점은 상태가 얼마나 오래 유지되는지를 개선하였을 뿐, 상태 내부 연결성이 얼마나 "
    "일관된지는 개선하지 못하였다.")
add_para("")

add_para("결론", bold=True)
add_para(
    "이상탐지 변화점으로 정의한 뇌 상태는 연결 중심성과 유지 시간에서 서로 달랐으며, "
    "연결 중심성이 낮은 상태일수록 더 오래 유지되었다. 체류 시간의 차이는 무작위 분할 "
    "귀무 모형을 넘어섰으나 연결성 구조 지표들은 그렇지 못하였다. 따라서 이 상태들이 "
    "가장 안정적으로 포착하는 성질은 시간적 지속성이며, 상태 내부 연결성의 공간적 "
    "구성은 무작위 분할로 얻은 것보다 더 일관되지 않았다. 데이터 기반 뇌 상태는 우연 "
    "수준이 아니라 명시적 귀무 모형에 대조해 판단해야 한다.")

d.save(OUT)
print("저장:", OUT)
