"""학위논문 Word 문서 생성 — 국문 전문 + 영문 전문, 그림/표 포함.

재실행: python3 thesis/build_thesis.py   (그림은 thesis/figures/{ko,en}/ 에 미리 생성)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from docx_builder import Docx

FIG = ROOT / "thesis" / "figures"
OUT = ROOT / "thesis" / "MTAD-GAT_BrainState_Thesis.docx"

TITLE_KO = "MTAD-GAT 임베딩 변화점 기반 뇌 기능 상태 정의와\nBrainLM 잠재표현을 이용한 검증"
TITLE_EN = ("Defining Functional Brain States from MTAD-GAT Embedding Change Points\n"
            "and Their Validation via BrainLM Latent Representations")


# =============================================================================
# 국문 본문
# =============================================================================
def korean(d: Docx):
    F = FIG / "ko"

    # ── 표지 ──
    d.title(TITLE_KO.replace("\n", " "), "— fMRI BOLD 신호의 비지도 상태 분할과 표현학습 기반 검증 —")
    d.spacer(600)

    # ── 국문초록 ──
    d.heading("국문초록", 1)
    for p in [
        "기능적 자기공명영상(fMRI)으로 측정되는 혈중산소농도의존(BOLD) 신호는 시간에 따라 서로 다른 기능적 상태(brain state) 사이를 전환하는 것으로 알려져 있으나, 그 전환 경계를 사전 지식이나 지도학습 레이블 없이 규정하는 방법은 아직 충분히 정립되지 않았다. 본 연구는 다변량 시계열 이상탐지 모델인 MTAD-GAT가 탐지하는 임베딩 변화점이 단순한 잡음이 아니라 뇌 기능 상태가 전환되는 의미 있는 경계라는 가설을 세우고, 이를 표현학습의 관점에서 정량적으로 검증하는 것을 목적으로 하였다.",
        "Human Connectome Project의 100개 관심영역(ROI)으로 분할된 BOLD 시계열을 사용하여, 70명의 피험자 데이터로 MTAD-GAT(Conv–Feature GAT–Temporal GAT–GRU)를 학습한 뒤 이와 중복되지 않는 27명에 적용하였다. GRU 은닉상태의 연속 시점 간 변화량을 기준으로 상태 전환 경계를 탐지하여 총 308개 세그먼트를 얻고, 각 세그먼트의 100×100 Pearson 기능적 연결성 행렬에 Fisher-Z 변환을 적용한 4,950차원 벡터를 K-평균(K=4)으로 군집화하여 상태 레이블을 부여하였다. 연결성 행렬은 상태 레이블 부여에만 사용하고, 표현학습에는 시간적 순서와 동역학 정보가 보존된 원시 BOLD 시계열을 입력하였다. 상태별로 독립적인 BrainLM(마스크 자기부호화 트랜스포머, d_model=256, 부호화기 4층·8헤드, 마스킹 비율 15%)을 학습한 뒤 CLS 토큰의 256차원 잠재표현을 추출하여, 상태 간 코사인 유사도로 표현의 분리 정도를 평가하였다.",
        "세 개 상태의 BrainLM은 모두 과적합 징후 없이 수렴하였으며(최적 검증 손실 98.83, 101.15, 115.67), 상태 간 잠재표현의 비대각 코사인 유사도 평균은 -0.006(범위 -0.059~0.048)으로 상호 거의 직교하였다. PCA 및 t-SNE 투영에서도 세 상태의 잠재표현이 공간적으로 분리된 군집을 형성하였다. 반면 군집을 구분하지 않고 단일 공유 모델을 학습한 경우 유사도가 0.96~0.99에 이르러 분리에 실패하였는데, 이는 상태별 독립 모델 구조가 원시 시계열의 시간적 동역학을 상태 구분에 활용하는 데 필수적임을 시사한다.",
        "본 연구는 이상탐지의 부산물로 간주되던 변화점이 신경생리학적으로 유의미한 상태 전환 신호일 수 있음을 보이고, 지도 레이블 없이 동적 뇌 상태를 정의하고 표현하는 파이프라인을 제시함으로써 동일 형식의 신규 피험자 데이터에 대한 상태 해석 도구로서의 확장 가능성을 확인하였다. 다만 분석 대상 피험자가 27명으로 제한되어 군집의 안정성과 일반화에는 제약이 있고, 표본이 부족한 한 개 상태(n=16)는 검증 세트 구성이 불가하여 분석에서 제외되었으며, 무작위 분할 기반 대조 조건과의 정량적 비교는 향후 과제로 남는다.",
    ]:
        d.para(p)
    d.para("주제어: 기능적 자기공명영상, 뇌 기능 상태, 그래프 어텐션 네트워크, 시계열 이상탐지, "
           "기능적 연결성, 표현학습", indent=0, after=200)

    # ── 1. 서론 ──
    d.heading("1. 서론", 1, page_break=True)
    d.heading("1.1 연구 배경", 2)
    for p in [
        "기능적 자기공명영상(functional Magnetic Resonance Imaging, fMRI)은 혈중산소농도의존(Blood-Oxygen-Level-Dependent, BOLD) 신호를 통해 뇌 활동을 비침습적으로 관찰하는 대표적 도구이다. 초기의 기능적 연결성(functional connectivity) 연구는 전체 측정 구간에 대해 하나의 상관 행렬을 산출하고 이를 개인의 고정된 특성으로 간주하였다. 그러나 지난 10여 년간의 연구는 휴지기(resting state)에서도 뇌의 연결 구조가 수십 초 단위로 변동하며, 이러한 변동이 측정 잡음이 아니라 인지 상태·각성 수준·주의 배분과 체계적으로 연관된다는 점을 반복적으로 보고해 왔다.",
        "이러한 관찰은 동적 기능적 연결성(dynamic functional connectivity, dFC)이라는 연구 분야를 형성하였고, 뇌를 유한한 수의 반복되는 '상태(state)' 사이를 전이하는 시스템으로 모형화하려는 시도로 이어졌다. 이때 핵심적인 기술적 난제는 연속적인 시계열을 어떤 기준으로 분할하여 상태의 경계를 정의할 것인가이다. 경계의 정의가 달라지면 이후의 모든 분석 — 상태의 개수, 각 상태의 연결성 패턴, 개인 간 비교 — 이 함께 달라지기 때문이다.",
        "가장 널리 사용되는 방법은 고정 길이 슬라이딩 윈도우이다. 이 방법은 구현이 단순하다는 장점이 있으나, 윈도우 길이라는 임의의 초매개변수에 결과가 민감하고, 실제 상태 전환이 윈도우 경계와 일치한다는 보장이 없으며, 짧은 지속 시간의 상태를 원리적으로 포착할 수 없다는 한계를 갖는다. 즉 슬라이딩 윈도우는 상태 경계를 데이터로부터 발견하는 것이 아니라 분석자가 미리 부과하는 방식에 가깝다.",
    ]:
        d.para(p)

    d.heading("1.2 문제 정의 및 연구 목적", 2)
    for p in [
        "본 연구는 상태 경계를 사전에 부과하지 않고 신호 자체로부터 도출하는 접근을 취한다. 구체적으로 다변량 시계열 이상탐지(multivariate time-series anomaly detection) 모델인 MTAD-GAT를 BOLD 신호에 적용하고, 이 모델이 학습한 내부 표현이 급격히 변화하는 시점을 상태 전환의 후보 경계로 삼는다. 이상탐지 모델은 본래 정상 패턴에서 벗어난 지점을 찾도록 설계되었으며, 그 출력은 통상 제거해야 할 잡음이나 오류로 취급된다. 본 연구는 이 통념을 뒤집어, fMRI 맥락에서는 그러한 '이상' 지점이 오히려 뇌가 하나의 기능적 구성에서 다른 구성으로 옮겨 가는 전환점에 대응할 수 있다고 본다.",
        "이 발상이 타당하려면 검증 가능한 형태로 진술되어야 한다. 만약 탐지된 경계가 실제 상태 전환을 반영한다면, 그 경계로 분할된 구간들은 내적으로 일관되고 서로 구별되는 신경 활동 패턴을 가져야 한다. 그리고 이러한 구별 가능성은 구간을 나눌 때 사용한 정보와는 독립적인 방식으로 확인될 때 비로소 설득력을 갖는다.",
        "본 연구는 이 검증을 표현학습의 문제로 환원한다. 즉 분할된 구간들을 연결성 패턴에 따라 군집화하여 상태 레이블을 부여한 뒤, 각 상태에 속하는 원시 BOLD 시계열만으로 별도의 표현학습 모델을 학습시키고, 그 결과로 얻어진 잠재표현이 상태 간에 서로 구별되는지를 정량적으로 측정한다.",
    ]:
        d.para(p)

    d.heading("1.3 연구 가설 및 기여", 2)
    d.para("본 연구의 핵심 가설은 다음과 같다.")
    d.para("가설: MTAD-GAT가 탐지하는 임베딩 변화점은 무작위적 잡음이 아니라 뇌 기능 상태가 전환되는 "
           "의미 있는 경계이며, 따라서 이 경계로 정의된 상태들은 표현학습 모델의 잠재공간에서 "
           "서로 구별되는 표현으로 나타난다.", indent=0, italic=True, after=160)
    d.para("본 연구의 기여는 다음 네 가지로 요약된다.")
    for p in [
        "첫째, 시계열 이상탐지 모델의 내부 임베딩 변화량을 fMRI 상태 분할의 기준으로 사용하는 파이프라인을 설계하고 구현하였다. 이는 고정 길이 윈도우에 의존하지 않는 데이터 주도적 분할 방식이다.",
        "둘째, 상태 레이블 부여와 표현학습의 정보원을 분리하는 설계 원칙을 제시하였다. 연결성 행렬은 군집화에만 사용하고, 표현학습에는 시간 정보가 보존된 원시 시계열을 입력함으로써, 검증이 순환 논증에 빠지지 않도록 하였다.",
        "셋째, 상태별 잠재표현의 코사인 유사도를 검증 지표로 도입하고, 세 상태에 대해 비대각 평균 -0.006이라는 결과를 얻었다.",
        "넷째, 단일 공유 모델과 상태별 독립 모델을 비교하여, 원시 시계열 입력이 효과를 발휘하기 위해서는 상태별 독립 모델 구조가 함께 요구된다는 설계적 함의를 실증하였다.",
    ]:
        d.para(p)

    # ── 2. 관련 연구 ──
    d.heading("2. 관련 연구", 1, page_break=True)
    d.heading("2.1 동적 기능적 연결성과 뇌 상태 분석", 2)
    for p in [
        "Hutchison 등[1]은 휴지기 fMRI에서 관찰되는 연결성의 시간적 변동을 종합적으로 검토하고, 이러한 변동이 방법론적 인공물만으로는 설명되지 않음을 논의하였다. Allen 등[2]은 슬라이딩 윈도우로 산출한 연결성 행렬을 K-평균으로 군집화하여 반복적으로 출현하는 연결성 상태를 정의하는 절차를 제시하였으며, 이는 이후 dFC 연구의 표준적 분석 틀이 되었다.",
        "한편 Vidaurre 등[3]은 은닉 마르코프 모형(Hidden Markov Model)을 이용하여 뇌 신경망 동역학이 시간적으로 위계적인 구조를 갖는다는 점을 보였다. 이러한 상태 공간 모형 계열의 접근은 상태 전환을 확률 모형의 잠재 변수로 다룬다는 점에서 본 연구와 문제의식을 공유하지만, 상태의 개수와 관측 모형의 형태를 사전에 가정해야 한다는 차이가 있다.",
        "Preti 등[4]은 동적 연결성 분석의 방법론적 쟁점을 정리하면서, 윈도우 길이 선택과 상태 개수 결정이 결과에 미치는 영향이 크다는 점을 지적하였다. 본 연구가 윈도우에 의존하지 않는 분할 기준을 모색한 배경에는 이러한 문제의식이 있다.",
    ]:
        d.para(p)

    d.heading("2.2 그래프 어텐션 네트워크와 다변량 시계열 이상탐지", 2)
    for p in [
        "Veličković 등[5]이 제안한 그래프 어텐션 네트워크(Graph Attention Network, GAT)는 그래프의 각 노드가 이웃 노드의 정보를 취합할 때, 고정된 가중치 대신 어텐션 계수를 학습하여 이웃별 중요도를 다르게 부여한다. 이는 노드 간 관계 구조가 사전에 알려져 있지 않거나 시점에 따라 변하는 상황에 적합하다.",
        "Zhao 등[6]의 MTAD-GAT는 이 아이디어를 다변량 시계열에 적용하여, 변수 간 관계를 다루는 특징 축 어텐션과 시점 간 관계를 다루는 시간 축 어텐션을 병렬로 구성하였다. 두 어텐션의 출력과 원 신호를 결합하여 GRU로 인코딩한 뒤, 재구성과 예측이라는 두 개의 목적함수로 학습한다.",
        "fMRI 데이터는 100개 ROI가 서로 시변하는 상호작용을 갖는 다변량 시계열이므로 이 구조와 자연스럽게 대응된다. ROI를 그래프의 노드로 볼 때 특징 축 어텐션은 영역 간 기능적 상호작용을, 시간 축 어텐션은 시점 간 의존 구조를 각각 모형화한다. 본 연구는 MTAD-GAT의 이상 점수 자체가 아니라 GRU 은닉상태의 시간적 변화량을 분할 기준으로 사용한다는 점에서 원 논문의 활용 방식과 구별된다.",
        "변화점 탐지(change point detection) 문헌[7]에서도 표현 공간에서의 거리 변화를 경계 신호로 사용하는 접근이 논의되어 왔다. 본 연구의 분할 기준은 이 관점에서 학습된 표현 공간 위에서의 변화점 탐지로 해석할 수 있다.",
    ]:
        d.para(p)

    d.heading("2.3 fMRI 파운데이션 모델과 표현학습", 2)
    for p in [
        "Vaswani 등[8]의 트랜스포머와 He 등[9]의 마스크 자기부호화기(Masked Autoencoder, MAE)는 대규모 비지도 표현학습의 표준적 구성 요소가 되었다. MAE는 입력의 일부를 가린 뒤 이를 복원하도록 학습함으로써, 별도의 레이블 없이도 데이터의 구조적 규칙성을 포착하는 표현을 얻는다.",
        "Ortega Caro 등[10]이 제안한 BrainLM은 이러한 마스크 자기부호화 방식을 fMRI 시계열에 적용한 파운데이션 모델로, 대규모 기록으로 사전학습된 표현이 하류 과제로 전이될 수 있음을 보였다. 본 연구는 BrainLM의 구조를 상태별 표현 추출기로 채택하되, 사전학습 가중치를 그대로 사용하는 대신 각 상태에 속한 데이터만으로 독립적으로 학습시켜 상태 특이적 표현을 얻는다.",
        "Bedel 등[11]의 BolT는 원시 fMRI 시계열에 융합 윈도우 트랜스포머를 직접 적용하여 시간적 문맥을 계층적으로 통합하는 대안적 접근을 제시하였다. BolT가 단일 모델로 전체 시계열을 처리하는 반면, 본 연구는 상태별로 분리된 모델을 학습한다는 점에서 설계 철학이 대비된다. 5.7절에서 보이듯 이 차이는 본 연구의 검증 결과에 결정적인 영향을 미친다.",
    ]:
        d.para(p)

    # ── 3. 연구 방법 ──
    d.heading("3. 연구 방법", 1, page_break=True)
    d.heading("3.1 전체 파이프라인 개요", 2)
    d.para("본 연구의 파이프라인은 그림 1과 같이 다섯 단계로 구성된다. 원시 BOLD 신호에서 출발하여 "
           "MTAD-GAT로 상태 전환 경계를 탐지하고, 분할된 세그먼트마다 기능적 연결성 행렬을 산출한 뒤, "
           "이를 군집화하여 상태 레이블을 부여한다. 마지막으로 상태별로 독립적인 BrainLM을 학습하고 "
           "그 잠재표현의 직교성을 검증한다.")
    d.para("이 설계에서 가장 중요한 원칙은 상태 레이블을 부여하는 정보원과 표현학습에 사용하는 정보원을 "
           "분리한 점이다. 연결성 행렬은 군집화에만 쓰이고 표현학습 모델에는 입력되지 않는다. 만약 "
           "연결성 행렬로 군집을 나눈 뒤 같은 연결성 행렬로 표현을 학습한다면, 얻어진 표현이 구별되는 "
           "것은 당연한 귀결이므로 검증으로서의 가치가 없다. 표현학습의 입력을 원시 시계열로 두면 모델은 "
           "군집화에 사용되지 않은 시간적 동역학 정보로부터 상태를 재발견해야 하며, 이때 비로소 "
           "잠재표현의 분리가 상태 정의의 타당성에 대한 독립적 증거가 된다.")
    d.figure(F / "fig1_pipeline.png",
             "그림 1. 전체 연구 파이프라인. 연결성 행렬은 상태 레이블 부여에만 사용되며, "
             "표현학습 단계의 입력은 원시 BOLD 시계열이다.",
             "Figure 1. Overview of the proposed pipeline.", width_in=3.9)

    d.heading("3.2 MTAD-GAT 기반 상태 전환 경계 탐지", 2)
    for p in [
        "MTAD-GAT는 네 개의 구성 요소로 이루어진다. 첫째, 1차원 합성곱 계층은 각 ROI 시계열을 국소적으로 평활하여 고주파 잡음의 영향을 줄인다. 둘째, 특징 축 그래프 어텐션 계층은 100개 ROI를 노드로 간주하고 영역 간 상호작용의 강도를 어텐션 계수로 학습한다. 셋째, 시간 축 그래프 어텐션 계층은 윈도우 내 시점들을 노드로 간주하여 시점 간 의존 구조를 학습한다. 넷째, 두 어텐션의 출력과 원 신호를 결합한 표현을 GRU로 인코딩하여 시퀀스 수준의 은닉상태를 얻는다. 모델은 재구성 손실과 예측 손실의 합으로 학습된다.",
        "학습을 마친 모델에 대하여, 크기 64의 윈도우를 이동시키며 각 시점에서 GRU 은닉상태를 추출한다. 시점 t의 은닉상태를 z_t라 할 때, 연속한 두 시점 사이의 변화량을 제곱 유클리드 거리로 정의한다. 이 변화량 계열에 길이 5의 이동평균 평활을 적용한 뒤, 값이 큰 상위 20개 시점을 상태 전환 후보로 선택한다.",
        "선택된 경계는 최소 세그먼트 길이 30 TR의 제약 하에 정리된다. 이는 지나치게 짧은 구간에서 산출된 상관 행렬이 표본 부족으로 불안정해지는 문제를 방지하기 위한 조치이다. 이 절차의 근거는 다음과 같다. GRU 은닉상태는 최근 시점들의 다변량 패턴을 요약한 표현이므로, 은닉상태가 급격히 이동한다는 것은 신호를 지배하던 패턴이 다른 패턴으로 교체되었음을 의미한다.",
    ]:
        d.para(p)

    d.heading("3.3 기능적 연결성 행렬 산출", 2)
    for p in [
        "분할된 각 세그먼트에 대해 100개 ROI 시계열 간 Pearson 상관계수를 계산하여 100×100 대칭 행렬을 얻는다. 상관계수는 [-1, 1] 구간에 제한되어 분포가 양 끝에서 압축되므로, 역쌍곡탄젠트 함수를 이용한 Fisher-Z 변환을 적용하여 분포를 정규분포에 가깝게 만든다. 이 변환은 이후 K-평균 군집화가 유클리드 거리를 전제한다는 점에서 군집 품질에 유리하게 작용한다.",
        "행렬은 대칭이므로 상삼각 성분만을 추출하여 4,950차원 벡터로 평탄화한다. 이 벡터가 각 세그먼트를 대표하는 군집화용 특징이 된다.",
    ]:
        d.para(p)

    d.heading("3.4 K-평균 군집화를 통한 상태 레이블링", 2)
    for p in [
        "전체 피험자에서 얻은 308개의 연결성 벡터를 하나의 행렬로 모아 표준화한 뒤, 미니배치 K-평균 알고리즘으로 군집화한다. 군집 수는 K=4로 설정하였으며, 이는 선행 dFC 연구에서 보고된 상태 개수의 범위와 엘보 기준을 함께 고려한 결정이다. 재현성을 위해 난수 시드는 42로 고정하였다.",
        "군집화는 피험자 구분 없이 전체 세그먼트를 대상으로 수행된다. 이는 동일한 상태가 여러 피험자에게서 공통으로 출현한다는 가정을 반영한 것으로, 결과적으로 각 군집은 개인 특이적 패턴이 아니라 피험자 간에 공유되는 연결성 구성을 나타내게 된다.",
    ]:
        d.para(p)

    d.heading("3.5 상태별 독립 BrainLM 표현학습", 2)
    for p in [
        "각 상태에 대해 해당 상태로 레이블된 세그먼트의 원시 BOLD 시계열만을 모아 별도의 BrainLM을 학습한다. 모델은 트랜스포머 기반 마스크 자기부호화기로서, 100차원 입력을 256차원으로 사영한 뒤 학습 가능한 CLS 토큰과 정현파 위치 부호화를 더하고, 4층·8헤드 부호화기와 2층 복호화기를 거쳐 원 신호를 복원한다. 전체 시점의 15%를 무작위로 가린 뒤 가려진 위치에서의 평균제곱오차를 손실로 사용한다.",
        "한 세그먼트가 하나의 학습 예제에 대응하도록 구성하였다. 여러 세그먼트를 이어붙이는 방식도 가능하나, 그 경우 표본이 적은 상태에서 예제 수가 급감하는 문제가 있어 본 연구에서는 세그먼트 단위를 채택하였다. 세그먼트마다 길이가 다르므로 상태별 최대 길이에 맞추어 패딩하고, 패딩된 위치는 손실 계산에서 제외한다.",
        "학습이 완료된 각 모델에 대해 해당 상태의 모든 세그먼트를 통과시켜 CLS 토큰의 256차원 출력을 추출하며, 이를 그 세그먼트의 잠재표현으로 삼는다.",
    ]:
        d.para(p)

    d.heading("3.6 잠재표현 분리도 평가 지표", 2)
    d.para("상태 i에 속한 모든 잠재표현의 평균 벡터를 구한 뒤 L2 정규화하여 그 상태의 대표 방향으로 "
           "정의한다. 두 상태의 대표 방향 사이의 내적이 곧 코사인 유사도이며, 이 값이 1에 가까우면 두 "
           "상태의 표현이 사실상 같은 방향을, 0에 가까우면 서로 직교하는 방향을 가리킨다. 상태 정의가 "
           "타당하다면 비대각 성분이 0에 가까울 것으로 기대된다.")
    d.para("보조 지표로 PCA와 t-SNE 투영에서의 군집 분리 양상, 상태별 잠재벡터의 L2 노름 분포, "
           "상태 내부의 주성분 누적 설명 분산을 함께 확인한다.")

    # ── 4. 실험 설정 ──
    d.heading("4. 실험 설정", 1, page_break=True)
    d.heading("4.1 데이터", 2)
    d.para("Human Connectome Project에서 공개한 휴지기 fMRI 데이터를 사용하였다. 각 피험자의 신호는 "
           "100개 ROI로 분할되어 있으며, 전체 97명 중 70명은 MTAD-GAT의 학습에, 나머지 27명은 상태 "
           "분할과 이후 모든 분석에 사용하였다. 두 집합은 서로 겹치지 않으므로, 분석 대상 피험자의 "
           "신호는 MTAD-GAT 학습 과정에 관여하지 않았다.")
    d.table(
        [["항목", "값"],
         ["데이터셋", "Human Connectome Project (휴지기 fMRI)"],
         ["전체 피험자 수", "97명"],
         ["MTAD-GAT 학습", "70명"],
         ["상태 분할·분석 대상", "27명"],
         ["ROI 수", "100"],
         ["총 세그먼트 수", "308"],
         ["세그먼트 길이 (평균 / 범위)", "105.2 TR / 31 ~ 549 TR"]],
        caption="표 1. 데이터 사양", caption_en="Table 1. Data specification", widths=[2, 3])

    d.heading("4.2 하이퍼파라미터", 2)
    d.para("파이프라인 각 단계의 주요 설정은 표 2와 같다. 모든 난수 시드는 42로 고정하여 재현성을 "
           "확보하였다.")
    d.table(
        [["단계", "매개변수", "값"],
         ["세그멘테이션", "윈도우 크기", "64"],
         ["", "평활 윈도우", "5"],
         ["", "선택 변화점 수", "20"],
         ["", "최소 세그먼트 길이", "30 TR"],
         ["연결성", "상관 계수", "Pearson"],
         ["", "Fisher-Z 변환", "적용"],
         ["", "특징 차원", "4,950 (상삼각)"],
         ["군집화", "알고리즘", "미니배치 K-평균"],
         ["", "군집 수 K", "4"],
         ["", "표준화", "적용"],
         ["BrainLM", "d_model", "256"],
         ["", "부호화기 / 복호화기", "4층 / 2층"],
         ["", "어텐션 헤드", "8"],
         ["", "FFN 차원", "1,024"],
         ["", "마스킹 비율", "15%"],
         ["", "학습률 / 배치 크기", "1e-4 / 8"],
         ["", "최대 에폭 / 조기종료 인내", "50 / 10"]],
        caption="표 2. 주요 하이퍼파라미터", caption_en="Table 2. Key hyperparameters",
        widths=[2, 3, 2])

    d.heading("4.3 데이터 분할", 2)
    d.para("학습·검증·평가 집합은 피험자 단위로 분할하였다. 동일 피험자의 세그먼트가 서로 다른 집합에 "
           "나뉘어 들어가면 개인 고유의 신호 특성이 누출되어 검증 손실이 낙관적으로 편향되므로, "
           "피험자를 통째로 배정하는 방식을 택하였다. 전체 308개 예제는 212 / 49 / 47로 나뉘었다.")

    # ── 5. 결과 및 논의 ──
    d.heading("5. 결과 및 논의", 1, page_break=True)
    d.heading("5.1 세그멘테이션 결과", 2)
    d.para("27명의 피험자로부터 총 308개의 세그먼트가 얻어졌으며, 피험자당 평균 11.4개에 해당한다. "
           "세그먼트 길이의 평균은 105.2 TR이고 범위는 31 TR에서 549 TR에 이른다(그림 2).")
    d.para("주목할 점은 길이 분포가 특정 값에 몰려 있지 않고 넓게 퍼져 있다는 것이다. 고정 길이 윈도우를 "
           "사용했다면 모든 구간이 동일한 길이를 가졌을 것이므로, 이 분산은 분할 기준이 데이터에 반응하여 "
           "경계를 결정했음을 보여준다. 다만 최장 549 TR과 같은 긴 세그먼트가 존재한다는 것은 해당 구간에서 "
           "은닉상태 변화가 상위 20개 안에 들 만큼 두드러지지 않았음을 의미하며, 이는 변화점 개수를 "
           "고정한 설계의 결과이기도 하다.")
    d.figure(F / "fig2_segmentation.png",
             "그림 2. 세그멘테이션 결과. (a) 세그먼트 길이 분포, (b) 피험자별 세그먼트 수.",
             "Figure 2. Segmentation results.")

    d.heading("5.2 상태 군집화 결과", 2)
    d.para("308개의 연결성 벡터를 K=4로 군집화한 결과 각 상태의 크기는 99, 121, 72, 16개로 나타났다. "
           "상태 0부터 2까지는 충분한 표본을 확보한 반면, 상태 3은 16개에 그쳐 전체의 5.2%에 불과하다.")
    d.para("그림 3은 각 상태의 중심 연결성 행렬을 보여준다. 네 상태는 서로 구별되는 연결 구조를 보이며, "
           "특정 영역 집합 내부의 동기적 활동이 강조되는 정도와 영역 집합 간 반동기적 관계의 강도에서 "
           "차이가 관찰된다. 이는 군집화가 무의미한 분할이 아니라 실제로 상이한 연결성 구성을 포착하고 "
           "있음을 시사한다. 다만 각 상태를 특정 뇌 네트워크와 대응시키는 해부학적 해석은 ROI 번호를 "
           "표준 아틀라스에 매핑하는 후속 작업을 필요로 한다.")
    d.figure(F / "fig3_cm_centroids.png",
             "그림 3. 상태별 중심 기능적 연결성 행렬. 대각 성분은 0으로 처리하였다.",
             "Figure 3. Centroid functional connectivity matrix of each state.")

    d.heading("5.3 상태별 BrainLM 학습", 2)
    d.para("상태 0, 1, 2에 대해 각각 독립적인 BrainLM을 학습하였다. 상태 3은 학습 집합에 12개, 검증 "
           "집합에 0개가 배정되어 조기 종료 판단의 근거가 되는 검증 손실을 계산할 수 없었으므로 "
           "학습에서 제외하였다. 이는 임의적 배제가 아니라 피험자 단위 분할과 표본 부족이 결합하여 "
           "발생한 구조적 제약이다.")
    d.table(
        [["상태", "학습 / 검증 / 평가", "최대 길이", "최종 학습 손실", "최종 검증 손실", "학습 에폭"],
         ["상태 0", "62 / 20 / 17", "252", "92.81", "98.83", "17"],
         ["상태 1", "86 / 20 / 15", "292", "92.20", "101.15", "24"],
         ["상태 2", "52 / 9 / 11", "237", "92.97", "115.67", "19"],
         ["상태 3", "12 / 0 / 4", "—", "—", "—", "학습 제외"]],
        caption="표 3. 상태별 BrainLM 학습 결과",
        caption_en="Table 3. Per-state BrainLM training results", widths=[1.2, 2, 1.2, 1.5, 1.5, 1.2])
    d.para("세 모델 모두 조기 종료 조건에 따라 17~24 에폭에서 학습을 마쳤으며, 학습 손실과 검증 손실의 "
           "간격이 좁아 심각한 과적합은 관찰되지 않았다(그림 4). 상태 2의 검증 손실이 115.67로 다른 두 "
           "상태보다 높은데, 이는 학습 예제가 52개로 가장 적고 검증 예제도 9개에 불과하여 추정의 분산이 "
           "크기 때문으로 보인다. 손실의 절대값이 90~116 범위로 큰 것은 원시 BOLD 신호의 스케일에 기인하며, "
           "상태 간 비교에서 의미를 갖는 것은 절대값이 아니라 수렴 양상이다.")
    d.figure(F / "fig4_training.png",
             "그림 4. 상태별 BrainLM 학습 결과. (a) 최종 학습·검증 손실, (b) 조기 종료 시점의 에폭 수.",
             "Figure 4. Per-state BrainLM training outcomes.")

    d.heading("5.4 잠재표현의 직교성", 2)
    d.para("각 상태의 평균 잠재벡터를 L2 정규화한 뒤 상호 코사인 유사도를 계산한 결과가 그림 5(a)이다. "
           "비대각 성분은 상태 0–상태 1이 -0.059, 상태 0–상태 2가 -0.005, 상태 1–상태 2가 0.048로, "
           "평균 -0.006이며 범위는 -0.059에서 0.048 사이이다. 세 값 모두 절대값이 0.06 미만으로, 상태별 "
           "표현이 서로 거의 직교하는 방향을 가리킨다.")
    d.para("이는 본 연구의 검증 기준을 충족하는 결과이다. 각 BrainLM은 자신에게 할당된 상태의 원시 "
           "시계열만을 보고 학습하였으며, 연결성 행렬이나 상태 레이블을 입력으로 받지 않았다. 그럼에도 "
           "서로 다른 방향의 표현이 형성되었다는 것은, 상태 간에 시계열 수준에서 구별되는 규칙성이 "
           "존재함을 뜻한다.")
    d.para("그림 5(b)의 L2 노름 분포는 상태별로 다른 양상을 보인다. 상태 0의 노름이 상대적으로 크고 "
           "분포가 넓은 반면, 상태 2는 좁은 범위에 집중되어 있다. 노름의 크기는 표현의 강도에, 분포의 "
           "폭은 상태 내부의 이질성에 각각 대응하는 것으로 해석할 수 있다.")
    d.figure(F / "fig5_cosine_l2.png",
             "그림 5. (a) 상태 간 잠재표현 코사인 유사도, (b) 상태별 잠재벡터 L2 노름 분포.",
             "Figure 5. Cross-state cosine similarity and latent norm distributions.")

    d.heading("5.5 잠재공간의 시각적 분리", 2)
    d.para("코사인 유사도는 각 상태의 평균 방향만을 요약하므로, 개별 잠재표현 수준에서의 분리를 함께 "
           "확인할 필요가 있다. 292개 잠재벡터를 L2 정규화한 뒤 PCA와 t-SNE로 2차원에 투영한 결과가 "
           "그림 6이다. 선형 투영인 PCA와 비선형 투영인 t-SNE 모두에서 세 상태가 서로 구별되는 영역을 "
           "점유하는 경향이 관찰된다.")
    d.para("두 투영 방법에서 일관된 분리가 나타난다는 점은 결과가 특정 차원 축소 기법의 인공물이 아님을 "
           "뒷받침한다. 다만 군집 경계에서 일부 중첩이 존재하며, 이는 상태 간 전이 구간에 해당하는 "
           "세그먼트나 군집화 단계에서 경계에 가깝게 배정된 세그먼트를 반영하는 것으로 보인다.")
    d.figure(F / "fig6_pca_tsne.png",
             "그림 6. 상태별 잠재표현의 2차원 투영. (a) PCA, (b) t-SNE.",
             "Figure 6. Two-dimensional projections of state latents.")

    d.heading("5.6 상태 내부 구조", 2)
    d.para("그림 7(a)는 상태 간 분산이 큰 상위 30개 잠재 차원에서 각 상태의 평균 프로파일을 비교한 "
           "것이다. 세 곡선은 여러 차원에서 서로 교차하고 부호가 반전되는데, 이는 상태 간 차이가 단순한 "
           "크기 차이가 아니라 활성화되는 차원 자체가 다른 질적 차이임을 보여준다.")
    d.para("그림 7(b)는 각 상태 내부에서 주성분 누적 설명 분산이 증가하는 양상이다. 곡선이 빠르게 "
           "상승하는 상태일수록 내부 표현이 저차원 구조로 요약되며, 이는 그 상태가 비교적 일관된 단일 "
           "패턴으로 특징지어짐을 시사한다. 반대로 완만하게 상승하는 상태는 내부에 서로 다른 하위 패턴이 "
           "혼재할 가능성을 시사하며, 이는 군집 수 K의 재검토가 필요할 수 있다는 신호로도 읽을 수 있다.")
    d.figure(F / "fig7_latent_profile.png",
             "그림 7. (a) 상태별 평균 잠재 프로파일, (b) 상태 내 PCA 누적 설명 분산.",
             "Figure 7. Latent profiles and within-state cumulative explained variance.")

    d.heading("5.7 설계 요인 분석: 공유 모델과 상태별 모델", 2)
    d.para("원시 시계열 입력이라는 선택만으로 상태 분리가 달성되는지 확인하기 위해, 상태를 구분하지 않고 "
           "모든 세그먼트를 하나의 BrainLM으로 학습한 조건(V3)과 본 연구의 상태별 독립 모델 조건(V4)을 "
           "비교하였다. 두 조건은 입력 형식이 원시 시계열로 동일하며 모델 구조도 같고, 상태별로 모델을 "
           "분리했는지 여부에서만 차이가 있다.")
    d.para("그림 8에서 보듯 단일 공유 모델 조건의 비대각 코사인 유사도는 0.960에서 0.989 사이로, 세 "
           "상태의 표현이 사실상 같은 방향을 가리켰다. 즉 공유 모델은 상태 구분을 학습하지 못하고 전체 "
           "데이터에 공통된 평균적 표현으로 수렴하였다. 반면 상태별 독립 모델 조건에서는 같은 지표가 "
           "-0.059에서 0.048로 떨어졌다.")
    d.para("이 대비는 방법론적으로 중요한 함의를 갖는다. 원시 시계열을 입력으로 사용한다는 선택은 그 "
           "자체로 충분조건이 아니며, 상태별로 분리된 학습 구조와 결합될 때 비로소 상태 특이적 표현이 "
           "형성된다. 동시에 이 결과는 5.9절에서 논의할 해석상의 주의점과도 직결된다.")
    d.figure(F / "fig8_v3_vs_v4.png",
             "그림 8. 단일 공유 모델(V3)과 상태별 독립 모델(V4)의 잠재표현 코사인 유사도 비교.",
             "Figure 8. Cosine similarity under shared versus per-state model configurations.")

    d.heading("5.8 피험자별 상태 점유율", 2)
    d.para("그림 9는 각 피험자의 세그먼트가 네 상태에 배분된 비율을 보여준다. 모든 피험자가 동일한 구성을 "
           "보이지 않고 개인마다 주로 머무는 상태가 다르며, 여러 상태를 고루 오가는 피험자와 특정 상태에 "
           "집중되는 피험자가 함께 관찰된다.")
    d.para("이러한 개인차는 두 가지로 해석될 수 있다. 하나는 상태 점유율이 개인의 안정적 특성을 반영한다는 "
           "해석으로, 이 경우 점유율은 잠재적 생체지표로 활용될 여지가 있다. 다른 하나는 측정 시점의 "
           "각성 수준이나 과제 외적 요인이 반영되었다는 해석이다. 본 연구의 데이터만으로는 두 해석을 "
           "구분할 수 없으며, 인지 점수나 인구통계 변수와의 연계 분석이 필요하다.")
    d.figure(F / "fig9_occupancy.png",
             "그림 9. 피험자별 뇌 기능 상태 점유율.",
             "Figure 9. Brain state occupancy per subject.")

    d.heading("5.9 논의 및 한계", 2)
    d.para("본 연구의 결과는 가설과 부합하지만, 그 해석 범위를 명확히 할 필요가 있다. 다음 네 가지는 "
           "결론을 제한하는 요인이다.")
    for p in [
        "첫째, 독립 학습에서 비롯되는 해석상의 주의점이다. 상태별 BrainLM은 서로 다른 무작위 초기값에서 출발하여 각각 학습되었으므로, 세 모델의 잠재공간은 애초에 정렬되어 있지 않다. 정렬되지 않은 고차원 공간에서 임의의 두 벡터는 확률적으로 거의 직교하는 경향이 있으므로, 관측된 낮은 코사인 유사도의 일부는 상태 간 실질적 차이가 아니라 독립 초기화 자체에서 기인했을 가능성을 배제할 수 없다. 이 가능성을 제거하려면 동일한 절차를 무작위로 분할한 세그먼트에 적용하는 대조 실험이 필요하다. 무작위 분할에서도 유사한 직교성이 관측된다면 본 연구의 지표는 상태 정의의 타당성에 대한 증거로서 힘을 잃으며, 반대로 무작위 분할에서 유의하게 높은 유사도가 관측된다면 가설은 강하게 지지된다. 이 대조 실험은 본 연구에서 수행되지 않았으며 가장 우선적인 후속 과제이다.",
        "둘째, 표본 규모의 제약이다. 분석 대상 피험자가 27명, 세그먼트가 308개로 제한되어 군집 중심의 안정성과 상태 구조의 일반화 가능성을 확언하기 어렵다. 특히 상태 3은 16개 표본에 그쳐 검증 집합을 구성하지 못하고 분석에서 제외되었으며, 이는 K=4로 정의한 상태 체계가 온전히 검증되지 못했음을 뜻한다.",
        "셋째, 군집 수 K의 결정 근거이다. 본 연구는 K=4를 채택하였으나 상태 3의 소멸에 가까운 크기는 이 선택이 최적이 아닐 수 있음을 시사한다. 실루엣 계수 등 내부 평가 지표를 이용한 체계적 탐색과 K=3 조건에서의 재분석이 요구된다.",
        "넷째, 해부학적 해석의 부재이다. 각 상태의 연결성 패턴이 어떤 기능적 뇌 네트워크에 대응하는지는 ROI 번호를 표준 아틀라스에 매핑해야 규명할 수 있다. 이 작업이 수반되어야 본 연구가 정의한 상태가 신경과학적 의미를 갖는지 판단할 수 있다.",
    ]:
        d.para(p)

    # ── 6. 결론 ──
    d.heading("6. 결론", 1, page_break=True)
    d.para("본 연구는 다변량 시계열 이상탐지 모델이 탐지하는 임베딩 변화점을 fMRI BOLD 신호의 상태 전환 "
           "경계로 사용하는 파이프라인을 설계하고, 그 타당성을 표현학습의 관점에서 검증하였다. 상태 "
           "레이블은 기능적 연결성 행렬의 군집화로 부여하되 표현학습에는 원시 시계열만을 입력함으로써, "
           "검증이 순환 논증에 빠지지 않도록 정보원을 분리한 점이 설계상의 핵심이다.")
    d.para("세 개 상태에 대해 독립적으로 학습된 BrainLM의 잠재표현은 비대각 코사인 유사도 평균 -0.006으로 "
           "거의 직교하였으며, PCA와 t-SNE 투영에서도 분리되는 경향이 확인되었다. 또한 상태를 구분하지 "
           "않은 단일 공유 모델에서는 같은 지표가 0.96 이상으로 나타나, 상태별 독립 학습 구조가 상태 특이적 "
           "표현 형성에 필수적임을 보였다.")
    d.para("다만 상태별 모델이 서로 다른 초기값에서 독립적으로 학습된다는 점에서, 관측된 직교성이 상태 간 "
           "실질적 차이만을 반영한다고 단정하기는 이르다. 무작위 분할을 대조 조건으로 하는 실험이 "
           "수행되어야 본 연구의 지표가 상태 정의의 타당성을 가리키는 증거로 확립될 수 있다. 표본 확대, "
           "군집 수의 체계적 결정, 해부학적 아틀라스 매핑, 상태 간 전이 확률의 모형화가 함께 요구되는 "
           "후속 과제이다.")
    d.para("이러한 한계에도 불구하고 본 연구는 이상탐지의 부산물로 취급되던 변화점을 뇌 상태 분할의 기준으로 "
           "재해석하고, 그 결과를 파운데이션 모델의 표현 공간에서 검증하는 절차를 구체적인 형태로 제시하였다. "
           "이 파이프라인은 동일한 형식의 신규 데이터에 그대로 적용될 수 있으며, 지도 레이블 없이 개인의 뇌 "
           "상태 구성을 기술하는 도구로 확장될 여지를 갖는다.")

    d.page_break()


# =============================================================================
# 영문 본문
# =============================================================================
def english(d: Docx):
    F = FIG / "en"

    d.title(TITLE_EN.replace("\n", " "),
            "— Unsupervised state segmentation of fMRI BOLD signals and "
            "representation-based validation —")
    d.spacer(600)

    d.heading("Abstract", 1)
    for p in [
        "Blood-oxygen-level-dependent (BOLD) signals measured by functional magnetic resonance imaging (fMRI) are known to transition among distinct functional brain states over time, yet methods for delineating these transition boundaries without prior knowledge or supervised labels remain underdeveloped. This study examines the hypothesis that the embedding change points detected by MTAD-GAT, a multivariate time-series anomaly detection model, are not mere noise but meaningful boundaries at which brain states shift, and evaluates this hypothesis quantitatively from a representation-learning perspective.",
        "Using BOLD time series parcellated into 100 regions of interest from the Human Connectome Project, MTAD-GAT (Conv–Feature GAT–Temporal GAT–GRU) was trained on 70 subjects and applied to a disjoint set of 27 subjects. State transition boundaries were identified from the magnitude of change in consecutive GRU hidden states, yielding 308 segments. For each segment, a 100×100 Pearson functional connectivity matrix was computed, Fisher-Z transformed, and vectorized (4,950 dimensions), then clustered by K-means (K=4) to assign state labels. Connectivity matrices were used solely for labeling; representation learning took raw BOLD time series as input, thereby preserving temporal ordering and dynamics. An independent BrainLM (masked-autoencoding Transformer; d_model=256, 4-layer/8-head encoder, 15% mask ratio) was trained per state, and 256-dimensional CLS-token latents were extracted and compared by cosine similarity.",
        "All three state-specific models converged without evident overfitting (best validation losses of 98.83, 101.15, and 115.67). The mean off-diagonal cosine similarity between state latents was -0.006 (range -0.059 to 0.048), indicating near-orthogonal representations, and PCA and t-SNE projections likewise showed spatially separated clusters. In contrast, a single shared model trained without state separation yielded similarities of 0.96–0.99, indicating that per-state independent models are essential for exploiting temporal dynamics in state discrimination.",
        "These findings suggest that change points, often regarded as byproducts of anomaly detection, may reflect neurophysiologically meaningful state transitions, and present a label-free pipeline for defining and representing dynamic brain states. Limitations include the modest sample of 27 subjects, the exclusion of one sparsely populated state (n=16) for which no validation set could be formed, and the absence of a quantitative comparison against randomly segmented controls, which remains future work.",
    ]:
        d.para(p)
    d.para("Keywords: functional MRI, brain state, graph attention network, time-series anomaly "
           "detection, functional connectivity, representation learning", indent=0, after=200)

    # ── 1. Introduction ──
    d.heading("1. Introduction", 1, page_break=True)
    d.heading("1.1 Background", 2)
    for p in [
        "Functional magnetic resonance imaging (fMRI) observes brain activity non-invasively through the blood-oxygen-level-dependent (BOLD) signal. Early functional connectivity studies computed a single correlation matrix over an entire scan and treated it as a stable trait of the individual. Over the past decade, however, a growing body of work has shown that connectivity structure fluctuates on the order of tens of seconds even at rest, and that these fluctuations relate systematically to cognitive state, arousal, and attentional allocation rather than reflecting measurement noise alone.",
        "These observations gave rise to the field of dynamic functional connectivity (dFC) and to attempts to model the brain as a system transitioning among a finite set of recurring states. The central technical difficulty is deciding how to partition a continuous time series so as to define state boundaries, since every downstream analysis — the number of states, their connectivity patterns, and comparisons across individuals — depends on that decision.",
        "The most widely used approach is the fixed-length sliding window. While simple to implement, it is sensitive to an arbitrary window-length hyperparameter, offers no guarantee that true transitions align with window boundaries, and cannot in principle capture states of short duration. In effect, the sliding window imposes boundaries rather than discovering them from the data.",
    ]:
        d.para(p)

    d.heading("1.2 Problem statement and objective", 2)
    for p in [
        "This study takes the alternative approach of deriving boundaries from the signal itself. Specifically, we apply MTAD-GAT, a multivariate time-series anomaly detection model, to BOLD signals and treat the time points at which its learned internal representation changes abruptly as candidate state boundaries. Anomaly detection models are designed to locate departures from normal patterns, and their output is ordinarily treated as noise to be removed. We invert this convention: in the fMRI setting, such anomalous points may correspond to moments at which the brain moves from one functional configuration to another.",
        "For this idea to be scientifically useful it must be stated in falsifiable form. If the detected boundaries reflect genuine state transitions, the resulting segments should exhibit internally consistent and mutually distinguishable patterns of neural activity. Crucially, that distinguishability must be demonstrated through information other than what was used to create the partition.",
        "We therefore reduce the validation to a representation-learning problem: segments are clustered by connectivity pattern to obtain state labels, a separate representation model is trained on the raw BOLD time series of each state alone, and the resulting latent representations are quantitatively tested for mutual separation.",
    ]:
        d.para(p)

    d.heading("1.3 Hypothesis and contributions", 2)
    d.para("The central hypothesis of this study is as follows.")
    d.para("Hypothesis: The embedding change points detected by MTAD-GAT are not random noise but "
           "meaningful boundaries at which functional brain states shift; consequently, states "
           "defined by these boundaries yield mutually distinguishable representations in the latent "
           "space of a representation-learning model.", indent=0, italic=True, after=160)
    d.para("The contributions are fourfold.")
    for p in [
        "First, we design and implement a pipeline that uses the magnitude of change in a time-series anomaly detector's internal embedding as the criterion for fMRI state segmentation, providing a data-driven alternative to fixed-length windows.",
        "Second, we articulate a design principle that separates the information source used for state labeling from that used for representation learning. Connectivity matrices serve only for clustering, while representation learning receives raw time series, so that the validation does not become circular.",
        "Third, we introduce cross-state cosine similarity of latent representations as a validation metric and report a mean off-diagonal value of -0.006 across three states.",
        "Fourth, by contrasting a single shared model with per-state independent models, we show empirically that raw time-series input yields state-specific representations only when combined with per-state model separation.",
    ]:
        d.para(p)

    # ── 2. Related work ──
    d.heading("2. Related Work", 1, page_break=True)
    d.heading("2.1 Dynamic functional connectivity and brain state analysis", 2)
    for p in [
        "Hutchison et al. [1] comprehensively reviewed temporal fluctuations in resting-state connectivity and argued that they cannot be attributed to methodological artifacts alone. Allen et al. [2] established the procedure of clustering sliding-window connectivity matrices with K-means to define recurring connectivity states, which became a standard analytic framework in subsequent dFC research.",
        "Vidaurre et al. [3] used hidden Markov models to show that brain network dynamics are hierarchically organized in time. Such state-space approaches share our concern with modeling transitions as latent variables, but require the number of states and the form of the observation model to be specified in advance.",
        "Preti et al. [4] surveyed methodological issues in dynamic connectivity analysis and emphasized the strong influence of window length and state-count selection on the results. This concern motivates our search for a window-free segmentation criterion.",
    ]:
        d.para(p)

    d.heading("2.2 Graph attention networks and multivariate anomaly detection", 2)
    for p in [
        "The Graph Attention Network (GAT) of Veličković et al. [5] learns attention coefficients when aggregating information from neighboring nodes, assigning different importance to different neighbors instead of using fixed weights. This is well suited to settings where the relational structure among nodes is unknown a priori or varies over time.",
        "MTAD-GAT, proposed by Zhao et al. [6], applies this idea to multivariate time series by combining a feature-axis attention module, which captures inter-variable relations, with a time-axis attention module, which captures inter-timepoint relations. The outputs of both, concatenated with the original signal, are encoded by a GRU and trained under joint reconstruction and forecasting objectives.",
        "fMRI data map naturally onto this structure, as 100 ROIs constitute a multivariate time series with time-varying interactions. Treating ROIs as graph nodes, feature-axis attention models inter-regional functional interaction while time-axis attention models temporal dependency. Our use differs from the original work in that we exploit the temporal change of GRU hidden states rather than the anomaly score itself.",
        "The change point detection literature [7] has likewise considered distance changes in a representation space as boundary signals. Our segmentation criterion can be viewed as change point detection over a learned representation space.",
    ]:
        d.para(p)

    d.heading("2.3 fMRI foundation models and representation learning", 2)
    for p in [
        "The Transformer of Vaswani et al. [8] and the Masked Autoencoder (MAE) of He et al. [9] have become standard components of large-scale unsupervised representation learning. MAE masks part of the input and learns to reconstruct it, thereby capturing structural regularities without labels.",
        "BrainLM, proposed by Ortega Caro et al. [10], applies masked autoencoding to fMRI time series as a foundation model and demonstrates that representations pretrained on large recordings transfer to downstream tasks. We adopt the BrainLM architecture as a per-state representation extractor, but rather than reusing pretrained weights we train each model independently on the data of a single state to obtain state-specific representations.",
        "BolT, by Bedel et al. [11], applies fused window Transformers directly to raw fMRI time series, hierarchically integrating temporal context. Whereas BolT processes the entire series with a single model, our design trains separate models per state. As shown in Section 5.7, this difference proves decisive for our validation result.",
    ]:
        d.para(p)

    # ── 3. Methods ──
    d.heading("3. Methods", 1, page_break=True)
    d.heading("3.1 Pipeline overview", 2)
    d.para("The pipeline comprises five stages, as shown in Figure 1. Starting from raw BOLD signals, "
           "MTAD-GAT detects state transition boundaries; a functional connectivity matrix is computed "
           "for each resulting segment; these matrices are clustered to assign state labels; and finally "
           "an independent BrainLM is trained per state and the orthogonality of its latent "
           "representations is assessed.")
    d.para("The most important principle in this design is the separation between the information "
           "source used for state labeling and that used for representation learning. Connectivity "
           "matrices are used only for clustering and are never fed to the representation model. Were "
           "we to cluster on connectivity matrices and then learn representations from those same "
           "matrices, obtaining distinguishable representations would be a foregone conclusion and "
           "would carry no evidential value. By feeding raw time series instead, the model must "
           "rediscover state structure from temporal dynamics that played no role in clustering, and "
           "only then does latent separation constitute independent evidence for the validity of the "
           "state definition.")
    d.figure(F / "fig1_pipeline.png",
             "Figure 1. Overview of the proposed pipeline. Connectivity matrices are used only for "
             "state labeling; representation learning operates on raw BOLD time series.", width_in=3.9)

    d.heading("3.2 State boundary detection with MTAD-GAT", 2)
    for p in [
        "MTAD-GAT consists of four components. A one-dimensional convolution layer locally smooths each ROI time series to reduce high-frequency noise. A feature-axis graph attention layer treats the 100 ROIs as nodes and learns the strength of inter-regional interaction as attention coefficients. A time-axis graph attention layer treats time points within a window as nodes and learns temporal dependency. Finally, a GRU encodes the concatenation of both attention outputs with the original signal into a sequence-level hidden state. The model is trained with the sum of reconstruction and forecasting losses.",
        "After training, GRU hidden states are extracted at each time point using a sliding window of size 64. Denoting the hidden state at time t by z_t, the change between consecutive time points is defined as the squared Euclidean distance. A moving average of length 5 smooths this change series, and the 20 time points with the largest values are selected as candidate transitions.",
        "The selected boundaries are then post-processed under a minimum segment length of 30 TR, which prevents correlation matrices from being estimated on samples too small to be stable. The rationale for the procedure is that a GRU hidden state summarizes the multivariate pattern of recent time points, so an abrupt shift in that state indicates that the pattern dominating the signal has been replaced by another.",
    ]:
        d.para(p)

    d.heading("3.3 Functional connectivity matrices", 2)
    for p in [
        "For each segment, Pearson correlation coefficients among the 100 ROI time series yield a 100×100 symmetric matrix. Because correlation coefficients are bounded to [-1, 1] and compressed near the extremes, a Fisher-Z transform based on the inverse hyperbolic tangent is applied to render the distribution closer to normal. This benefits the subsequent K-means clustering, which presupposes Euclidean geometry.",
        "As the matrix is symmetric, only the upper triangle is retained and flattened into a 4,950-dimensional vector, which serves as the clustering feature representing each segment.",
    ]:
        d.para(p)

    d.heading("3.4 State labeling via K-means clustering", 2)
    for p in [
        "The 308 connectivity vectors pooled across all subjects are standardized and clustered with mini-batch K-means. The number of clusters was set to K=4, informed by the range of state counts reported in prior dFC work together with the elbow criterion. The random seed was fixed at 42 for reproducibility.",
        "Clustering is performed over all segments without regard to subject identity, reflecting the assumption that the same states recur across individuals. Consequently, each cluster represents a connectivity configuration shared across subjects rather than an individual-specific pattern.",
    ]:
        d.para(p)

    d.heading("3.5 Per-state BrainLM representation learning", 2)
    for p in [
        "For each state, a separate BrainLM is trained using only the raw BOLD time series of segments labeled with that state. The model is a Transformer-based masked autoencoder that projects the 100-dimensional input to 256 dimensions, prepends a learnable CLS token, adds sinusoidal positional encoding, and reconstructs the signal through a 4-layer/8-head encoder and a 2-layer decoder. Fifteen percent of time points are masked at random, and the mean squared error at masked positions serves as the loss.",
        "Each segment constitutes one training example. Concatenating several segments per example is also possible, but sharply reduces the number of examples in sparsely populated states, so segment-level examples were adopted. As segments differ in length, each is padded to the maximum length within its state, and padded positions are excluded from the loss.",
        "After training, all segments of the corresponding state are passed through the model and the 256-dimensional CLS output is taken as the latent representation of that segment.",
    ]:
        d.para(p)

    d.heading("3.6 Evaluation metric for latent separation", 2)
    d.para("For each state, the mean of all its latent vectors is computed and L2-normalized to define "
           "the representative direction of that state. The inner product between two such directions "
           "is their cosine similarity: values near 1 indicate that the two states point in essentially "
           "the same direction, whereas values near 0 indicate mutually orthogonal directions. If the "
           "state definition is valid, off-diagonal entries are expected to be close to zero.")
    d.para("As auxiliary evidence we also examine cluster separation in PCA and t-SNE projections, the "
           "distribution of latent L2 norms per state, and the cumulative explained variance of "
           "principal components within each state.")

    # ── 4. Experimental setup ──
    d.heading("4. Experimental Setup", 1, page_break=True)
    d.heading("4.1 Data", 2)
    d.para("We used resting-state fMRI data released by the Human Connectome Project. Each subject's "
           "signal is parcellated into 100 ROIs. Of 97 subjects in total, 70 were used to train "
           "MTAD-GAT and the remaining 27 were used for state segmentation and all subsequent "
           "analyses. The two sets are disjoint, so the signals of the analyzed subjects played no "
           "part in training MTAD-GAT.")
    d.table(
        [["Item", "Value"],
         ["Dataset", "Human Connectome Project (resting-state fMRI)"],
         ["Total subjects", "97"],
         ["MTAD-GAT training", "70"],
         ["Segmentation and analysis", "27"],
         ["Number of ROIs", "100"],
         ["Total segments", "308"],
         ["Segment length (mean / range)", "105.2 TR / 31 – 549 TR"]],
        caption="Table 1. Data specification", widths=[2, 3])

    d.heading("4.2 Hyperparameters", 2)
    d.para("Table 2 lists the principal settings of each pipeline stage. All random seeds were fixed "
           "at 42 to ensure reproducibility.")
    d.table(
        [["Stage", "Parameter", "Value"],
         ["Segmentation", "Window size", "64"],
         ["", "Smoothing window", "5"],
         ["", "Number of change points", "20"],
         ["", "Minimum segment length", "30 TR"],
         ["Connectivity", "Correlation", "Pearson"],
         ["", "Fisher-Z transform", "Applied"],
         ["", "Feature dimension", "4,950 (upper triangle)"],
         ["Clustering", "Algorithm", "Mini-batch K-means"],
         ["", "Number of clusters K", "4"],
         ["", "Standardization", "Applied"],
         ["BrainLM", "d_model", "256"],
         ["", "Encoder / decoder layers", "4 / 2"],
         ["", "Attention heads", "8"],
         ["", "FFN dimension", "1,024"],
         ["", "Mask ratio", "15%"],
         ["", "Learning rate / batch size", "1e-4 / 8"],
         ["", "Max epochs / early-stop patience", "50 / 10"]],
        caption="Table 2. Key hyperparameters", widths=[2, 3, 2])

    d.heading("4.3 Data splitting", 2)
    d.para("Training, validation, and test sets were split at the subject level. Splitting segments of "
           "the same subject across sets would leak individual-specific signal characteristics and bias "
           "validation loss optimistically, so each subject was assigned wholly to one set. The 308 "
           "examples were divided into 212 / 49 / 47.")

    # ── 5. Results ──
    d.heading("5. Results and Discussion", 1, page_break=True)
    d.heading("5.1 Segmentation results", 2)
    d.para("A total of 308 segments were obtained from 27 subjects, corresponding to an average of "
           "11.4 segments per subject. Segment length averaged 105.2 TR with a range from 31 to 549 TR "
           "(Figure 2).")
    d.para("Notably, the length distribution is broad rather than concentrated at a particular value. "
           "A fixed-length window would have produced segments of identical length, so this dispersion "
           "shows that the criterion responded to the data in placing boundaries. At the same time, the "
           "presence of segments as long as 549 TR indicates that hidden-state changes within those "
           "intervals were not pronounced enough to rank among the top 20, which is itself a "
           "consequence of fixing the number of change points.")
    d.figure(F / "fig2_segmentation.png",
             "Figure 2. Segmentation results. (a) Segment length distribution; "
             "(b) number of segments per subject.")

    d.heading("5.2 State clustering results", 2)
    d.para("Clustering the 308 connectivity vectors with K=4 produced states of size 99, 121, 72, and "
           "16. States 0 through 2 obtained adequate samples, whereas State 3 comprised only 16 "
           "segments, or 5.2% of the total.")
    d.para("Figure 3 shows the centroid connectivity matrix of each state. The four states exhibit "
           "distinguishable connectivity structures, differing in the degree to which synchronous "
           "activity within particular sets of regions is emphasized and in the strength of "
           "anti-synchronous relations between region sets. This suggests that the clustering captured "
           "genuinely different connectivity configurations rather than an arbitrary partition. "
           "Assigning each state to a specific functional brain network, however, requires mapping ROI "
           "indices onto a standard atlas, which remains future work.")
    d.figure(F / "fig3_cm_centroids.png",
             "Figure 3. Centroid functional connectivity matrix of each state; "
             "diagonal entries are set to zero.")

    d.heading("5.3 Per-state BrainLM training", 2)
    d.para("Independent BrainLMs were trained for States 0, 1, and 2. State 3 received 12 examples in "
           "the training set and none in the validation set, making it impossible to compute the "
           "validation loss on which early stopping depends, and was therefore excluded. This exclusion "
           "is not arbitrary but a structural consequence of subject-level splitting combined with "
           "sample scarcity.")
    d.table(
        [["State", "Train / Val / Test", "Max length", "Final train loss", "Final val loss", "Epochs"],
         ["State 0", "62 / 20 / 17", "252", "92.81", "98.83", "17"],
         ["State 1", "86 / 20 / 15", "292", "92.20", "101.15", "24"],
         ["State 2", "52 / 9 / 11", "237", "92.97", "115.67", "19"],
         ["State 3", "12 / 0 / 4", "—", "—", "—", "excluded"]],
        caption="Table 3. Per-state BrainLM training results", widths=[1.2, 2, 1.2, 1.5, 1.5, 1.2])
    d.para("All three models stopped between epochs 17 and 24 under the early-stopping criterion, and "
           "the narrow gap between training and validation loss indicates no severe overfitting "
           "(Figure 4). The validation loss of State 2 is higher at 115.67, plausibly because it has "
           "the fewest training examples (52) and only nine validation examples, yielding a "
           "high-variance estimate. The large absolute magnitude of the losses (90–116) reflects the "
           "scale of the raw BOLD signal; what matters for cross-state comparison is the convergence "
           "behavior rather than the absolute value.")
    d.figure(F / "fig4_training.png",
             "Figure 4. Per-state BrainLM training outcomes. (a) Final training and validation loss; "
             "(b) epochs completed at early stopping.")

    d.heading("5.4 Orthogonality of latent representations", 2)
    d.para("Figure 5(a) reports cosine similarities among the L2-normalized mean latent vectors of "
           "each state. The off-diagonal entries are -0.059 for States 0–1, -0.005 for States 0–2, "
           "and 0.048 for States 1–2, giving a mean of -0.006 with a range from -0.059 to 0.048. All "
           "three values are below 0.06 in absolute magnitude, indicating that the state "
           "representations point in nearly orthogonal directions.")
    d.para("This satisfies the validation criterion set out in this study. Each BrainLM observed only "
           "the raw time series of its assigned state and received neither connectivity matrices nor "
           "state labels as input. That representations in distinct directions nonetheless emerged "
           "implies the existence of regularities that distinguish the states at the level of the time "
           "series itself.")
    d.para("The L2-norm distributions in Figure 5(b) also differ across states. State 0 exhibits "
           "relatively large norms with a broad distribution, whereas State 2 is concentrated in a "
           "narrow range. Norm magnitude may be read as representational strength and distributional "
           "width as within-state heterogeneity.")
    d.figure(F / "fig5_cosine_l2.png",
             "Figure 5. (a) Cross-state latent cosine similarity; (b) latent L2-norm distributions.")

    d.heading("5.5 Visual separation in latent space", 2)
    d.para("Because cosine similarity summarizes only the mean direction of each state, separation at "
           "the level of individual representations must also be examined. Figure 6 projects the 292 "
           "L2-normalized latent vectors into two dimensions via PCA and t-SNE. Under both the linear "
           "projection (PCA) and the nonlinear one (t-SNE), the three states tend to occupy "
           "distinguishable regions.")
    d.para("Consistent separation across two projection methods supports the conclusion that the "
           "result is not an artifact of a particular dimensionality-reduction technique. Some overlap "
           "persists at cluster boundaries, likely reflecting segments that span transitions between "
           "states or that were assigned near a decision boundary during clustering.")
    d.figure(F / "fig6_pca_tsne.png",
             "Figure 6. Two-dimensional projections of state latents. (a) PCA; (b) t-SNE.")

    d.heading("5.6 Within-state structure", 2)
    d.para("Figure 7(a) compares the mean profile of each state over the 30 latent dimensions with the "
           "greatest between-state variance. The three curves cross one another and reverse sign "
           "across several dimensions, showing that differences between states are qualitative — "
           "different dimensions are activated — rather than mere differences in magnitude.")
    d.para("Figure 7(b) traces the cumulative explained variance of principal components within each "
           "state. A curve that rises quickly indicates that the state's representations are "
           "summarized by a low-dimensional structure, suggesting a relatively coherent single "
           "pattern. A curve that rises slowly suggests that distinct sub-patterns coexist within the "
           "state, which may also signal that the number of clusters K warrants reconsideration.")
    d.figure(F / "fig7_latent_profile.png",
             "Figure 7. (a) Mean latent profile per state; (b) within-state cumulative explained "
             "variance.")

    d.heading("5.7 Design factor analysis: shared versus per-state models", 2)
    d.para("To determine whether raw time-series input alone achieves state separation, we compared a "
           "condition in which all segments were trained in a single BrainLM without regard to state "
           "(V3) against the per-state independent models of this study (V4). The two conditions share "
           "the same raw time-series input format and the same model architecture, differing only in "
           "whether models are separated by state.")
    d.para("As Figure 8 shows, off-diagonal cosine similarity under the shared model ranged from 0.960 "
           "to 0.989: the three states pointed in essentially the same direction. The shared model "
           "failed to learn state distinctions and converged instead to an average representation "
           "common to all data. Under per-state models the same metric fell to between -0.059 and "
           "0.048.")
    d.para("This contrast carries an important methodological implication. Choosing raw time series as "
           "input is not by itself sufficient; state-specific representations emerge only when that "
           "choice is combined with a per-state training structure. At the same time, this result "
           "bears directly on the interpretive caveat discussed in Section 5.9.")
    d.figure(F / "fig8_v3_vs_v4.png",
             "Figure 8. Cosine similarity under shared (V3) versus per-state (V4) model "
             "configurations.")

    d.heading("5.8 Per-subject state occupancy", 2)
    d.para("Figure 9 shows the proportion of each subject's segments assigned to the four states. "
           "Subjects do not share a uniform composition; the state in which each predominantly resides "
           "differs, and subjects who move evenly among several states coexist with those concentrated "
           "in one.")
    d.para("Two interpretations are available. One is that state occupancy reflects a stable individual "
           "trait, in which case it could serve as a candidate biomarker. The other is that it reflects "
           "arousal level or other incidental factors at the time of scanning. The present data cannot "
           "adjudicate between them; linking occupancy to cognitive scores or demographic variables "
           "would be required.")
    d.figure(F / "fig9_occupancy.png",
             "Figure 9. Brain state occupancy per subject.")

    d.heading("5.9 Discussion and limitations", 2)
    d.para("Although the results are consistent with the hypothesis, the scope of their interpretation "
           "must be stated clearly. Four factors constrain the conclusions.")
    for p in [
        "First, an interpretive caveat arises from independent training. Because each per-state BrainLM was trained from a different random initialization, the three latent spaces are not aligned to begin with. In unaligned high-dimensional spaces, two arbitrary vectors tend to be nearly orthogonal by chance, so we cannot exclude the possibility that part of the observed low cosine similarity stems from independent initialization rather than from substantive differences between states. Ruling this out requires a control experiment applying the identical procedure to randomly partitioned segments. If comparable orthogonality appears under random segmentation, the metric loses its force as evidence for the validity of the state definition; conversely, if random segmentation yields substantially higher similarity, the hypothesis is strongly supported. This control was not conducted here and constitutes the most immediate priority for future work.",
        "Second, sample size is limited. With 27 subjects and 308 segments, the stability of cluster centroids and the generalizability of the state structure cannot be asserted. State 3 in particular comprised only 16 samples, could not form a validation set, and was excluded from analysis, meaning that the K=4 state system was not fully validated.",
        "Third, the basis for choosing K deserves scrutiny. We adopted K=4, but the near-vanishing size of State 3 suggests this may not be optimal. A systematic search using internal validity indices such as the silhouette coefficient, together with reanalysis under K=3, is warranted.",
        "Fourth, anatomical interpretation is absent. Determining which functional brain networks correspond to each state's connectivity pattern requires mapping ROI indices onto a standard atlas. Only with that step can the neuroscientific meaning of the defined states be assessed.",
    ]:
        d.para(p)

    # ── 6. Conclusion ──
    d.heading("6. Conclusion", 1, page_break=True)
    d.para("This study designed a pipeline that uses the embedding change points detected by a "
           "multivariate time-series anomaly detection model as state transition boundaries in fMRI "
           "BOLD signals, and validated that design from a representation-learning perspective. The "
           "core of the design is the separation of information sources: state labels are assigned by "
           "clustering functional connectivity matrices, while representation learning receives only "
           "raw time series, so that validation does not become circular.")
    d.para("Latent representations from three independently trained BrainLMs were nearly orthogonal, "
           "with a mean off-diagonal cosine similarity of -0.006, and PCA and t-SNE projections showed "
           "a corresponding tendency toward separation. Under a single shared model without state "
           "separation, the same metric exceeded 0.96, demonstrating that per-state independent "
           "training is essential to the formation of state-specific representations.")
    d.para("Nevertheless, because the per-state models were trained independently from different "
           "initializations, it is premature to conclude that the observed orthogonality reflects "
           "substantive between-state differences alone. A control experiment using random "
           "segmentation is required before this metric can be established as evidence for the "
           "validity of the state definition. Expanding the sample, determining the number of clusters "
           "systematically, mapping states onto an anatomical atlas, and modeling inter-state "
           "transition probabilities are further tasks that follow.")
    d.para("Despite these limitations, this study reinterprets change points — ordinarily discarded as "
           "byproducts of anomaly detection — as a criterion for brain state segmentation, and lays "
           "out a concrete procedure for validating the result in the representation space of a "
           "foundation model. The pipeline applies directly to new data of the same format and offers "
           "room for extension as a tool for characterizing an individual's brain state composition "
           "without supervised labels.")


# =============================================================================
# 참고문헌 (공통)
# =============================================================================
REFERENCES = [
    "[1] Hutchison, R. M., Womelsdorf, T., Allen, E. A., Bandettini, P. A., Calhoun, V. D., "
    "Corbetta, M., et al. (2013). Dynamic functional connectivity: Promise, issues, and "
    "interpretations. NeuroImage, 80, 360–378.",
    "[2] Allen, E. A., Damaraju, E., Plis, S. M., Erhardt, E. B., Eichele, T., & Calhoun, V. D. "
    "(2014). Tracking whole-brain connectivity dynamics in the resting state. Cerebral Cortex, "
    "24(3), 663–676.",
    "[3] Vidaurre, D., Smith, S. M., & Woolrich, M. W. (2017). Brain network dynamics are "
    "hierarchically organized in time. Proceedings of the National Academy of Sciences, 114(48), "
    "12827–12832.",
    "[4] Preti, M. G., Bolton, T. A., & Van De Ville, D. (2017). The dynamic functional connectome: "
    "State-of-the-art and perspectives. NeuroImage, 160, 41–54.",
    "[5] Veličković, P., Cucurull, G., Casanova, A., Romero, A., Liò, P., & Bengio, Y. (2018). "
    "Graph Attention Networks. International Conference on Learning Representations (ICLR).",
    "[6] Zhao, H., Wang, Y., Duan, J., Huang, C., Cao, D., Tong, Y., et al. (2020). Multivariate "
    "Time-series Anomaly Detection via Graph Attention Network. IEEE International Conference on "
    "Data Mining (ICDM), 841–850.",
    "[7] Aminikhanghahi, S., & Cook, D. J. (2017). A survey of methods for time series change point "
    "detection. Knowledge and Information Systems, 51(2), 339–367.",
    "[8] Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., et al. "
    "(2017). Attention is all you need. Advances in Neural Information Processing Systems (NeurIPS).",
    "[9] He, K., Chen, X., Xie, S., Li, Y., Dollár, P., & Girshick, R. (2022). Masked autoencoders "
    "are scalable vision learners. IEEE/CVF Conference on Computer Vision and Pattern Recognition "
    "(CVPR), 16000–16009.",
    "[10] Ortega Caro, J., de O. Fonseca, A. H., Averill, C., Rizvi, S. A., Rosati, M., Cross, "
    "J. L., et al. (2024). BrainLM: A foundation model for brain activity recordings. International "
    "Conference on Learning Representations (ICLR).",
    "[11] Bedel, H. A., Sivgin, I., Dalmaz, O., Dar, S. U. H., & Çukur, T. (2023). BolT: Fused "
    "window transformers for fMRI time series analysis. Medical Image Analysis, 88, 102841.",
    "[12] Van Essen, D. C., Smith, S. M., Barch, D. M., Behrens, T. E. J., Yacoub, E., & Ugurbil, "
    "K. (2013). The WU-Minn Human Connectome Project: An overview. NeuroImage, 80, 62–79.",
    "[13] Schaefer, A., Kong, R., Gordon, E. M., Laumann, T. O., Zuo, X.-N., Holmes, A. J., et al. "
    "(2018). Local-global parcellation of the human cerebral cortex from intrinsic functional "
    "connectivity MRI. Cerebral Cortex, 28(9), 3095–3114.",
    "[14] Cho, K., van Merriënboer, B., Gulcehre, C., Bahdanau, D., Bougares, F., Schwenk, H., & "
    "Bengio, Y. (2014). Learning phrase representations using RNN encoder-decoder for statistical "
    "machine translation. Conference on Empirical Methods in Natural Language Processing (EMNLP).",
    "[15] Liu, X., & Duyn, J. H. (2013). Time-varying functional network information extracted from "
    "brief instances of spontaneous brain activity. Proceedings of the National Academy of Sciences, "
    "110(11), 4392–4397.",
]


def main():
    d = Docx()
    korean(d)
    english(d)
    d.heading("참고문헌 / References", 1, page_break=True)
    for r in REFERENCES:
        d.reference(r)
    d.save(OUT)
    print(f"saved: {OUT}")


if __name__ == "__main__":
    main()
