// 추가분석 결과 — 질문/즉답 형식 발표 덱
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/Users/mac/.claude/skills/synced/a3d420dd-7bca-4cf8-b3b3-ed5e5de273b8_0001a5c5-5808-4cc0-9bb9-b3820e9fcf4b/pptx/scripts/apply_theme.js");

const ROOT = "/Users/mac/Desktop/code/MTAD-GAT";
const ADD = (f) => path.join(ROOT, "visualization_ver4_add", f);
const V5F = (f) => path.join(ROOT, "visualization_ver5", f);
const V4F = (f) => path.join(ROOT, "visualization_ver4", f);
const V6F = (f) => path.join(ROOT, "visualization_ver6_k2_stride64", f);
const V7F = (f) => path.join(ROOT, "visualization_ver7_k2", f);
const OUT = path.join(ROOT, "강기호 연구 정리 ppt.pptx");

const THEME = {
  name: "AddAnalysis",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "131A33", lt1: "FFFFFF", dk2: "2F3C7E", lt2: "EDF1F8",
    accent1: "E04B5A", accent2: "1C7293", accent3: "5A6BA8", accent4: "97A3C9",
    accent5: "E8A33D", accent6: "2E8B6F", hlink: "1C7293", folHlink: "5A6BA8",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = "MTAD-GAT Brain State 연구";
pres.title = "추가분석 결과 보고";

const C = pres.SchemeColor;

pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "eyebrow", type: "body", x: 0.9, y: 2.0, w: 11.5, h: 0.4,
      fontSize: 15, color: C.accent4, charSpacing: 2 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.9, y: 2.5, w: 11.5, h: 1.4,
      fontSize: 42, bold: true, color: C.background1, align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.9, y: 4.0, w: 11.5, h: 0.9,
      fontSize: 17, color: C.accent4 }, text: "" } },
    { placeholder: { options: { name: "meta", type: "body", x: 0.9, y: 6.25, w: 11.5, h: 0.5,
      fontSize: 13, color: C.accent3 }, text: "" } },
  ],
});

pres.defineSlideMaster({
  title: "SECTION",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "num", type: "body", x: 0.9, y: 2.5, w: 2.2, h: 1.2,
      fontSize: 56, bold: true, color: C.accent1 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 3.1, y: 2.6, w: 9.3, h: 1.0,
      fontSize: 36, bold: true, color: C.background1, align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 3.15, y: 3.65, w: 9.3, h: 0.8,
      fontSize: 15, color: C.accent4 }, text: "" } },
  ],
});

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.38, w: 12.1, h: 0.8,
      fontSize: 32, bold: true, color: C.text2, align: "left", valign: "middle" }, text: "" } },
  ],
  slideNumber: { x: 12.6, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: "97A3C9", align: "right" },
});

pres.defineSlideMaster({
  title: "CLOSING",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.9, y: 0.7, w: 11.5, h: 0.9,
      fontSize: 36, bold: true, color: C.background1, align: "left" }, text: "" } },
  ],
});

const NAVY = "2F3C7E", CORAL = "E04B5A", TEAL = "1C7293", AMBER = "E8A33D",
      GREEN = "2E8B6F", INK = "131A33", MUTED = "5A6BA8", PALE = "EDF1F8";

function card(slide, { x, y, w, h, fill, name }) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, fill: { color: fill || PALE }, rectRadius: 0.08,
    line: { color: fill || PALE, width: 0 }, objectName: name,
  });
}

/** 큰 수치 콜아웃 카드 */
function statCard(slide, { x, y, w, h, value, label, note, color }) {
  card(slide, { x, y, w, h, fill: PALE, name: `stat-${label}` });
  slide.addText(value, { x: x + 0.25, y: y + 0.18, w: w - 0.5, h: 0.6,
    fontSize: 30, bold: true, color: color, isTextBox: true, margin: 0, valign: "middle" });
  slide.addText(label, { x: x + 0.25, y: y + 0.82, w: w - 0.5, h: 0.32,
    fontSize: 13, bold: true, color: INK, isTextBox: true, margin: 0 });
  if (note) {
    slide.addText(note, { x: x + 0.25, y: y + 1.14, w: w - 0.5,
      h: Math.max(0.28, h - 1.2), fontSize: 11.5, color: MUTED, isTextBox: true,
      margin: 0, lineSpacingMultiple: 1.15 });
  }
}

function figure(slide, { file, x, y, w, ratio, caption }) {
  const h = w / ratio;
  slide.addImage({ path: file, x, y, w, h, objectName: path.basename(file) });
  if (caption) {
    slide.addText(caption, { x, y: y + h + 0.08, w, h: 0.28, fontSize: 10.5, italic: true,
      color: MUTED, isTextBox: true, margin: 0 });
  }
  return y + h;
}

function bullets(slide, { x, y, w, h, items, fontSize }) {
  slide.addText(
    items.map((t, i) => ({
      text: typeof t === "string" ? t : t.text,
      options: {
        bullet: true, breakLine: i !== items.length - 1,
        bold: typeof t === "object" && t.bold,
        color: typeof t === "object" && t.color ? t.color : INK,
      },
    })),
    { x, y, w, h, fontSize: fontSize || 14, color: INK, isTextBox: true,
      paraSpaceAfter: 8, lineSpacingMultiple: 1.2 });
}

/** 질문 띠 + 즉답 — 이 덱의 핵심 모티프 */
function qa(slide, { q, a, color, y }) {
  const yy = y === undefined ? 1.32 : y;
  card(slide, { x: 0.6, y: yy, w: 12.1, h: 0.52, fill: "1E2A52", name: "q-band" });
  slide.addText([
    { text: "Q.  ", options: { bold: true, color: AMBER, fontSize: 14 } },
    { text: q, options: { color: "FFFFFF", fontSize: 14 } },
  ], { x: 0.85, y: yy, w: 11.6, h: 0.52, isTextBox: true, margin: 0, valign: "middle" });

  slide.addText([
    { text: "A.  ", options: { bold: true, color: color || CORAL, fontSize: 19 } },
    { text: a, options: { bold: true, color: color || CORAL, fontSize: 19 } },
  ], { x: 0.65, y: yy + 0.6, w: 12.0, h: 0.52, isTextBox: true, margin: 0, valign: "middle" });

  return yy + 1.22;
}

function tbl(slide, rows, opt) {
  const { x, y, w, colW, rowH, fontSize, hi } = opt;
  slide.addTable(
    rows.map((r, ri) => r.map((cell, ci) => ({
      text: cell,
      options: {
        bold: ri === 0 || ci === 0 || (hi !== undefined && ri === hi),
        color: ri === 0 ? "FFFFFF" : (hi !== undefined && ri === hi ? CORAL : INK),
        fill: ri === 0 ? { color: NAVY }
            : (hi !== undefined && ri === hi ? { color: "FDF3F4" } : { color: "FFFFFF" }),
        align: ci === 0 ? "left" : "center",
      },
    }))),
    { x, y, w, colW, rowH: rowH || 0.36, fontSize: fontSize || 12, valign: "middle",
      border: { type: "solid", color: "D5DCEC", pt: 1 }, margin: 0.06 });
}

const S = (t) => ({ sectionTitle: t });

// =============================================================================
pres.addSection({ title: "표지" });

// 요청사항 수행 현황

// =============================================================================
// 버전별 아키텍처 비교 — 덱 맨 앞(표지 다음)에 삽입
// =============================================================================
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("표지") });
  s.addText("버전별 파이프라인 아키텍처", { placeholder: "title" });

  const rows = [
    ["", "BrainLM 입력", "학습 예제 구성", "예제 수", "핵심 변경 / 목적"],
    ["V1", "CM 시퀀스", "단일 공유 모델", "—", "최초 구현 · 군집 품질 낮음"],
    ["V2", "CM 시퀀스 (4,950-dim)", "CM 6개 슬라이딩 윈도우", "~288", "클러스터별 독립 모델 도입"],
    ["V3", "Raw BOLD 시계열", "세그먼트 4개 concat", "~83", "입력을 원시 신호로 교체 · 단일 공유 모델"],
    ["V4", "Raw BOLD 시계열", "세그먼트 1개 = 예제 1개 (0 패딩)", "308", "클러스터별 독립 + CM과 1:1 대응"],
    ["V6", "Raw BOLD 시계열", "State 전체 concat → 64 TP 균일 분할 · State별 모델", "505", "길이 교란 제거 (교수님 요청 방식)"],
    ["V7", "Raw BOLD 시계열", "V6와 동일한 윈도우 · 모델은 하나만 학습", "1,009", "latent를 같은 좌표계에서 비교"],
  ];
  tbl(s, rows, { x: 0.6, y: 1.3, w: 12.1, colW: [0.9, 2.3, 4.4, 1.0, 3.5],
    rowH: 0.42, fontSize: 11, hi: 6 });

  s.addText("해석·검증 단계 (BrainLM 학습과 별개)", { x: 0.6, y: 4.55, w: 12.1, h: 0.32,
    fontSize: 14, bold: true, color: NAVY, isTextBox: true, margin: 0 });

  const rows2 = [
    ["", "무엇을 하는가", "산출물"],
    ["V4-add", "Degree Centrality · 7-Network 요약 · dwell time · State 간 통계 검정",
     "v4*_add_report"],
    ["V5", "무작위 분할 대조군 1,000회 — 경계가 무작위보다 나은지 permutation 검정",
     "v5_report"],
  ];
  tbl(s, rows2, { x: 0.6, y: 4.95, w: 12.1, colW: [1.4, 7.6, 3.1],
    rowH: 0.44, fontSize: 11 });

  card(s, { x: 0.6, y: 6.2, w: 12.1, h: 0.8, fill: PALE, name: "vnote" });
  s.addText([
    { text: "현재 사용  ", options: { bold: true, color: NAVY, fontSize: 13 } },
    { text: "해석 분석(DC · dwell time)은 V4-add, 표현학습 비교는 V6·V7, 분할 타당성 검증은 V5를 사용합니다. " +
            "V6는 교수님 요청 방식 그대로이고, V7은 그 한계(모델마다 좌표계가 달라 latent 비교 불가)를 보완한 것입니다.",
      options: { fontSize: 12.5, color: INK } },
  ], { x: 0.85, y: 6.2, w: 11.6, h: 0.8, isTextBox: true, margin: 0, valign: "middle", lineSpacingMultiple: 1.2 });

  s.addNotes(
    "[큰 흐름] V1~V3은 입력을 무엇으로 할지 찾아간 과정입니다. V1·V2는 연결성 행렬(CM)을 " +
    "입력으로 썼는데, CM은 시간 순서를 버리기 때문에 BOLD 신호의 동역학을 담지 못합니다. " +
    "V3에서 원시 시계열로 바꿨지만 단일 공유 모델이라 State가 분리되지 않았습니다.\n\n" +
    "[V4] 클러스터별 독립 모델 + 원시 시계열 조합입니다. CM은 State 레이블을 다는 데만 쓰고 " +
    "학습에는 그 세그먼트의 원시 신호를 그대로 넣어, CM 하나와 예제 하나가 1:1로 대응됩니다.\n\n" +
    "[V6] V4는 세그먼트 길이가 31~549 TP로 제각각이라 0으로 패딩해야 했고, 예제마다 " +
    "실제 정보량이 10배 넘게 차이 났습니다. V6는 State 전체를 이어붙여 64 TP로 균일하게 " +
    "잘라 그 교란을 없앴습니다. 대신 CM과의 1:1 대응을 포기했습니다.\n\n" +
    "[V4-add와 V5] 이 둘은 BrainLM 학습이 아니라 해석과 검증 단계입니다. V4-add는 " +
    "교수님이 요청하신 DC·네트워크 요약·dwell time 분석이고, V5는 '이 결과가 무작위 분할과 " +
    "구별되는가'를 검정한 대조군입니다.\n\n" +
    "[V7] V6에서 State별로 모델을 따로 학습하면 각 모델의 latent 좌표계가 공유되지 않아 " +
    "latent를 직접 비교할 수 없습니다. V7은 같은 윈도우 데이터로 모델을 하나만 학습해 " +
    "1,009개 윈도우의 latent를 같은 공간에 놓습니다.\n\n" +
    "[V5가 빠진 이유] V5는 BrainLM을 학습하지 않습니다. 세그먼트 경계의 품질만 " +
    "검정하므로 위쪽 표가 아니라 아래쪽 표에 넣었습니다.");
}

// 용어 정리
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("표지") });
  s.addText("용어 정리", { placeholder: "title" });

  const terms = [
    { t: "CM (연결성 행렬)", d: "한 세그먼트 안에서 100개 ROI가 서로 얼마나 같이 움직였는지 적은 100×100 표. 각 칸 = Pearson 상관의 Fisher-Z 값", c: NAVY },
    { t: "DC (Degree Centrality)", d: "각 ROI가 자신의 가장 강한 상위 10% 연결로부터 받는 총 연결 강도. 100×1 벡터", c: NAVY },
    { t: "FC magnitude (전역 연결강도)", d: "CM에 적힌 숫자들의 전반적 크기. 누가 중심인지가 아니라 표 전체의 수위", c: TEAL },
    { t: "상대 DC (relative DC)", d: "DC ÷ 그 관측의 평균 DC. 전역 수위를 지우고 공간 패턴만 남긴 값", c: TEAL },
    { t: "FDR q", d: "100개 ROI를 각각 검정하면 차이가 없어도 5개쯤 우연히 유의하게 나온다. 이를 보정한 값. p는 보정 전, q는 보정 후", c: CORAL },
    { t: "유의 ROI", d: "100개 중 \"State에 따라 DC가 진짜 달라졌다\"고 판정된 구역 수", c: CORAL },
  ];
  let x = 0.6, y = 1.45;
  terms.forEach((o, i) => {
    card(s, { x, y, w: 5.95, h: 1.62, fill: PALE, name: `term-${i}` });
    s.addText(o.t, { x: x + 0.25, y: y + 0.14, w: 5.45, h: 0.35, fontSize: 15, bold: true,
      color: o.c, isTextBox: true, margin: 0 });
    s.addText(o.d, { x: x + 0.25, y: y + 0.52, w: 5.45, h: 0.98, fontSize: 12.5, color: INK,
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });
    if (i % 2 === 0) { x += 6.15; } else { x = 0.6; y += 1.78; }
  });

  s.andNotes = null;
  s.addNotes("CM은 조각 하나의 친밀도 표, DC는 그 표에서 뽑은 구역별 중심성 점수입니다. " +
    "FC magnitude는 표 전체의 수위이고, FDR q는 100번 검정에 따른 우연한 유의성을 걸러낸 값입니다.");
}

// =============================================================================
pres.addSection({ title: "(0) BrainLM latent" });
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(0) BrainLM latent") });
  s.addText("(0) BrainLM latent 비교", { placeholder: "title" });

  card(s, { x: 0.6, y: 1.3, w: 12.1, h: 0.5, fill: "1E2A52", name: "lead" });
  s.addText("State별로 독립 학습한 BrainLM에서 CLS 토큰 latent(256-dim)를 추출해 State 간 분리 정도를 확인",
    { x: 0.85, y: 1.3, w: 11.6, h: 0.5, fontSize: 14, color: "FFFFFF",
      isTextBox: true, margin: 0, valign: "middle" });

  const st = [
    { v: "3개 모델", d: "State 0·1·2 독립 학습 (State 3은 n=16로 제외)", c: NAVY },
    { v: "256-dim", d: "CLS 토큰 latent · 예제 99 / 121 / 72개", c: TEAL },
    { v: "−0.006", d: "오프-대각 코사인 평균 (V3 공유 모델은 0.96~0.99)", c: CORAL },
  ];
  let x0 = 0.6;
  st.forEach((o, i) => {
    card(s, { x: x0, y: 1.95, w: 3.87, h: 0.95, fill: PALE, name: `bl-${i}` });
    s.addText(o.v, { x: x0 + 0.25, y: 2.03, w: 3.37, h: 0.42, fontSize: 20, bold: true,
      color: o.c, isTextBox: true, margin: 0, valign: "middle" });
    s.addText(o.d, { x: x0 + 0.25, y: 2.45, w: 3.37, h: 0.38, fontSize: 11, color: MUTED,
      isTextBox: true, margin: 0 });
    x0 += 4.12;
  });

  figure(s, { file: V4F("fig2_pooled_latent.png"), x: 2.67, y: 3.1, w: 8.0, ratio: 2.31,
    caption: "Pooled latent의 PCA(좌)와 t-SNE(우) 투영 · L2 정규화 후" });

  s.addNotes(
    "[무엇을 한 것인가] State별로 BrainLM을 따로 학습시킨 뒤, 각 모델이 만든 요약 벡터" +
    "(CLS 토큰 latent, 256차원)를 뽑아 State 간에 얼마나 다른지 코사인 유사도로 쟀습니다.\n\n" +
    "[결과] 오프-대각 코사인 평균 −0.006으로 거의 직교했고, PCA·t-SNE 투영에서도 " +
    "State별로 분리된 군집을 이뤘습니다. 반면 V3처럼 단일 공유 모델을 쓰면 0.96~0.99로 " +
    "분리에 실패합니다.\n\n" +
    "[반드시 함께 말씀드려야 할 한계] 이 코사인은 서로 다른 모델이 만든 벡터를 비교한 " +
    "값입니다. 세 모델은 각자 랜덤 초기화되어 따로 학습됐으므로 좌표계를 공유하지 않습니다. " +
    "256차원에서 아무 관계 없는 두 벡터의 코사인은 평균 0, 95% 구간 [−0.121, +0.120]인데, " +
    "관측된 세 값(−0.059, −0.005, +0.048)이 모두 그 구간 안에 있습니다. " +
    "즉 '거의 직교'는 State 분리의 증거가 아니라 서로 다른 모델을 비교하면 당연히 나오는 " +
    "값입니다. 같은 이유로 V3의 0.97도 유효한 대조군이 아닙니다.\n\n" +
    "[t-SNE 분리도 같은 문제] 이 그림의 군집 분리 역시 증거가 아닙니다. 같은 State " +
    "데이터로 seed만 바꿔 학습한 두 모델도 똑같이 완벽하게 갈립니다(7번 슬라이드 대조군). " +
    "분리는 'State가 다르다'가 아니라 '모델이 둘이다'의 결과입니다.\n\n" +
    "[대안] 공유 모델 하나로 전체 latent를 뽑은 뒤 ① held-out 피험자에서 State 분류 정확도 " +
    "② 레이블을 섞는 permutation test로 분리도를 재정의하는 방법을 제안드립니다. " +
    "V7에서 실제로 그렇게 했고, 정확도 0.710 · 치환 귀무값 0.501 ± 0.024가 나왔습니다.");
}

// =============================================================================
// 학습 방식 비교 도식
// =============================================================================
pres.addSection({ title: "(0-1) 학습 방식 비교" });
// =============================================================================
// BrainLM 학습 데이터 구성 방식 비교 (V4 vs V6) — 도식 슬라이드
// (0) BrainLM latent 비교 바로 다음에 들어간다
// =============================================================================
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(0-1) 학습 방식 비교") });
  s.addText("(0-1) BrainLM을 어떻게 학습시켰나 — V4 vs V6", { placeholder: "title" });

  // 공통 스케일: 가로 6.9인치 = 443 TP (세그먼트 31 + 120 + 292)
  const PX = 6.9 / 443;      // TP → inch
  const X0 = 2.25;           // 막대 시작 x
  const SEG = [31, 120, 292];
  const SEGC = ["#E04B5A", "#1C7293", "#2F3C7E"];

  // ── V4 블록 ──────────────────────────────────────────────────────────────
  card(s, { x: 0.6, y: 1.3, w: 12.1, h: 2.45, fill: "FBFCFE", name: "v4box" });
  s.addText([
    { text: "V4  ", options: { bold: true, color: NAVY, fontSize: 16 } },
    { text: "세그먼트 1개 = 예제 1개 · 가장 긴 것에 맞춰 0으로 패딩",
      options: { color: INK, fontSize: 13.5 } },
  ], { x: 0.85, y: 1.4, w: 11.6, h: 0.35, isTextBox: true, margin: 0 });

  let y = 1.85;
  SEG.forEach((len, i) => {
    s.addText(`세그먼트 ${String.fromCharCode(65 + i)}`, {
      x: 0.85, y: y - 0.03, w: 1.3, h: 0.3, fontSize: 11, color: INK,
      isTextBox: true, margin: 0, valign: "middle" });
    // 실제 데이터
    s.addShape(pres.ShapeType.rect, {
      x: X0, y, w: len * PX, h: 0.3, fill: { color: SEGC[i] },
      line: { color: SEGC[i], width: 0 }, objectName: `v4-real-${i}` });
    // 0 패딩
    const pad = (292 - len) * PX;
    if (pad > 0.02) {
      s.addShape(pres.ShapeType.rect, {
        x: X0 + len * PX, y, w: pad, h: 0.3, fill: { color: "D7DEE8" },
        line: { color: "C3CEDA", width: 0.5, dashType: "dash" },
        objectName: `v4-pad-${i}` });
    }
    s.addText(pad > 0.02 ? `${len} TP + 패딩 ${292 - len}` : `${len} TP`, {
      x: X0 + 292 * PX + 0.12, y: y - 0.03, w: 2.2, h: 0.3, fontSize: 10.5,
      color: pad > 0.02 ? CORAL : MUTED, isTextBox: true, margin: 0, valign: "middle" });
    y += 0.42;
  });

  s.addText([
    { text: "문제  ", options: { bold: true, color: CORAL, fontSize: 12.5 } },
    { text: "세그먼트 A는 292칸 중 261칸(89%)이 패딩. 예제마다 모델이 실제로 보는 " +
            "정보량이 10배 가까이 차이 난다. 95 백분위수로 잘라 긴 세그먼트는 뒷부분이 버려진다.",
      options: { color: INK, fontSize: 12 } },
  ], { x: 0.85, y: 3.15, w: 11.6, h: 0.5, isTextBox: true, margin: 0,
       lineSpacingMultiple: 1.15 });

  // ── V6 블록 ──────────────────────────────────────────────────────────────
  card(s, { x: 0.6, y: 3.95, w: 12.1, h: 2.95, fill: "FBFCFE", name: "v6box" });
  s.addText([
    { text: "V6  ", options: { bold: true, color: GREEN, fontSize: 16 } },
    { text: "State의 세그먼트를 모두 이어붙인 뒤 64 TP 윈도우로 균일 분할 · 패딩 없음",
      options: { color: INK, fontSize: 13.5 } },
  ], { x: 0.85, y: 4.05, w: 11.6, h: 0.35, isTextBox: true, margin: 0 });

  // 이어붙인 하나의 긴 막대
  s.addText("이어붙임", { x: 0.85, y: 4.47, w: 1.3, h: 0.3, fontSize: 11, color: INK,
    isTextBox: true, margin: 0, valign: "middle" });
  let cx = X0;
  SEG.forEach((len, i) => {
    s.addShape(pres.ShapeType.rect, {
      x: cx, y: 4.47, w: len * PX, h: 0.3, fill: { color: SEGC[i] },
      line: { color: "FFFFFF", width: 1 }, objectName: `v6-seg-${i}` });
    cx += len * PX;
  });
  s.addText("443 TP", { x: X0 + 6.9 + 0.12, y: 4.44, w: 1.4, h: 0.3, fontSize: 10.5,
    color: MUTED, isTextBox: true, margin: 0, valign: "middle" });

  // 64 TP 윈도우로 분할 (경계를 걸치는 것은 테두리로 표시)
  s.addText("64 TP씩", { x: 0.85, y: 5.12, w: 1.3, h: 0.3, fontSize: 11, color: INK,
    isTextBox: true, margin: 0, valign: "middle" });
  const joins = [31, 151];                 // 이어붙인 자리(TP)
  for (let w = 0; w < 6; w++) {
    const st = w * 64, en = st + 64;
    const strad = joins.some((j) => j > st && j < en);
    s.addShape(pres.ShapeType.rect, {
      x: X0 + st * PX + 0.015, y: 5.12, w: 64 * PX - 0.03, h: 0.3,
      fill: { color: strad ? "FFF1D6" : "E6F2EC" },
      line: { color: strad ? AMBER : GREEN, width: strad ? 1.5 : 1 },
      objectName: `v6-win-${w}` });
    s.addText(`W${w + 1}`, {
      x: X0 + st * PX, y: 5.12, w: 64 * PX, h: 0.3, align: "center", valign: "middle",
      fontSize: 9.5, bold: true, color: strad ? "8A6212" : "1F6B52",
      isTextBox: true, margin: 0 });
  }
  s.addText("W7은 64 TP 미달 → 버림", { x: X0 + 6.9 + 0.12, y: 5.09, w: 2.3, h: 0.3,
    fontSize: 10, color: MUTED, isTextBox: true, margin: 0, valign: "middle" });

  // 범례
  s.addShape(pres.ShapeType.rect, { x: 0.85, y: 5.66, w: 0.26, h: 0.18,
    fill: { color: "E6F2EC" }, line: { color: GREEN, width: 1 }, objectName: "lg1" });
  s.addText("한 조각 안에만 들어감", { x: 1.18, y: 5.58, w: 2.5, h: 0.32, fontSize: 10.5,
    color: INK, isTextBox: true, margin: 0, valign: "middle" });
  s.addShape(pres.ShapeType.rect, { x: 3.85, y: 5.66, w: 0.26, h: 0.18,
    fill: { color: "FFF1D6" }, line: { color: AMBER, width: 1.5 }, objectName: "lg2" });
  s.addText("이어붙인 자리를 걸침 (K=2에서 50~58%)", { x: 4.18, y: 5.58, w: 4.4, h: 0.32,
    fontSize: 10.5, color: INK, isTextBox: true, margin: 0, valign: "middle" });

  s.addText([
    { text: "효과  ", options: { bold: true, color: GREEN, fontSize: 12.5 } },
    { text: "모든 예제가 64 TP로 균일해 정보량 교란이 사라지고, 예제 수가 308 → 505개로 " +
            "늘어난다. 대신 윈도우가 세그먼트 경계를 넘나들어 CM과의 1:1 대응이 사라진다.",
      options: { color: INK, fontSize: 12 } },
  ], { x: 0.85, y: 6.3, w: 11.6, h: 0.5, isTextBox: true, margin: 0,
       lineSpacingMultiple: 1.15 });

  s.addNotes(
    "[그림 읽는 법] 가로 길이가 실제 time point 수에 비례합니다. 세그먼트 A는 31 TP, " +
    "B는 120 TP, C는 292 TP인 경우를 예로 들었습니다.\n\n" +
    "[V4 방식] 세그먼트 하나를 통째로 예제 하나로 썼습니다. 길이가 제각각이라 가장 긴 " +
    "것(그 State의 95 백분위수)에 맞춰 0으로 채웠습니다. 회색 칸이 패딩입니다. " +
    "세그먼트 A는 292칸 중 261칸이 패딩이라 전체의 89%가 빈 값입니다. attention mask로 " +
    "가려서 계산에서는 빠지지만, 예제마다 모델이 보는 실제 정보량이 10배 가까이 차이 납니다.\n\n" +
    "[V6 방식] State에 속한 세그먼트를 시간 순으로 모두 이어붙여 하나의 긴 시계열을 만든 뒤 " +
    "64 TP씩 잘랐습니다. 모든 예제가 같은 길이라 패딩이 전혀 없습니다. 예제 수도 " +
    "308개에서 505개로 늘었습니다.\n\n" +
    "[주황색 윈도우] 이어붙인 자리를 가로지르는 윈도우입니다. 서로 다른 시간대, 때로는 " +
    "서로 다른 피험자의 신호가 한 윈도우에 섞입니다. 실제 데이터에서는 K=2 기준 50~58%가 " +
    "여기에 해당합니다. 걸치는 윈도우를 버리면 깨끗해지지만 예제가 절반으로 줄어 다시 " +
    "데이터 부족 문제가 생깁니다.\n\n" +
    "[트레이드오프] V6는 길이 교란을 없앴지만 CM과의 1:1 대응을 포기했습니다. " +
    "V4에서는 'latent 하나가 CM 하나의 표현'이라고 말할 수 있었는데, V6에서는 " +
    "윈도우가 세그먼트를 넘나들어 그 해석이 성립하지 않습니다.");
}

// =============================================================================
// V6 슬라이드 — 추가분석_결과_발표.pptx 의 (0) BrainLM latent 비교 뒤에 삽입
// =============================================================================
pres.addSection({ title: "(0-2) V6 concat 방식" });

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(0-2) V6 concat 방식") });
  s.addText("(0-2) V6: State를 이어붙여 균일 토큰으로 학습", { placeholder: "title" });

  card(s, { x: 0.6, y: 1.3, w: 12.1, h: 0.5, fill: "1E2A52", name: "v6lead" });
  s.addText("요청 방식 — State에 속한 세그먼트를 모두 이어붙인 뒤 길이 64 TP(46초) 윈도우로 균일 분할하여 학습",
    { x: 0.85, y: 1.3, w: 11.6, h: 0.5, fontSize: 14, color: "FFFFFF",
      isTextBox: true, margin: 0, valign: "middle" });

  const rows = [
    ["", "V4 (기존)", "V6 (요청 방식)"],
    ["학습 예제", "세그먼트 1개 = 예제 1개", "이어붙인 뒤 균일 분할"],
    ["예제 길이", "31~549 TP (0 패딩)", "모두 64 TP (패딩 없음)"],
    ["예제 수 (K=2)", "308개", "505개 (202 + 303)"],
    ["CM과의 대응", "1:1 유지", "사라짐"],
  ];
  tbl(s, rows, { x: 0.6, y: 1.98, w: 6.2, colW: [1.9, 2.15, 2.15], rowH: 0.46, fontSize: 11.5 });

  const rows2 = [
    ["State", "세그먼트", "총 TP", "윈도우", "경계 걸침"],
    ["State 0", "138", "12,982", "202", "118 (58%)"],
    ["State 1", "170", "19,418", "303", "151 (50%)"],
  ];
  tbl(s, rows2, { x: 7.1, y: 1.98, w: 5.6, colW: [1.1, 1.1, 1.2, 1.0, 1.2],
    rowH: 0.46, fontSize: 11.5 });

  card(s, { x: 7.1, y: 3.6, w: 5.6, h: 1.3, fill: "FFF7E8", name: "strad" });
  s.addText([
    { text: "경계 걸침\n", options: { bold: true, color: AMBER, fontSize: 13.5 } },
    { text: "이어붙인 자리를 가로지르는 윈도우. 서로 다른 시간대·피험자 신호가 한 윈도우에 섞인다.",
      options: { fontSize: 12, color: INK } },
  ], { x: 7.35, y: 3.75, w: 5.1, h: 1.05, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });

  figure(s, { file: V6F("fig1_training_curves.png"), x: 0.6, y: 4.1, w: 6.2, ratio: 2.42,
    caption: "State별 BrainLM 학습 곡선 (K=2)" });

  card(s, { x: 7.1, y: 5.05, w: 5.6, h: 1.85, fill: PALE, name: "v6why" });
  s.addText([
    { text: "왜 다시 했는가\n", options: { bold: true, color: NAVY, fontSize: 13.5 } },
    { text: "V4는 세그먼트 길이가 31~549 TP로 제각각이라 예제마다 실제 정보량이 10배 넘게 " +
            "차이 났습니다. 균일 윈도우로 바꾸면 그 교란이 사라지고 예제 수도 308 → 505개로 " +
            "늘어납니다. K=2를 쓴 것은 K=3·4에서는 극단 State의 윈도우가 22~23개뿐이기 때문입니다.",
      options: { fontSize: 12, color: INK } },
  ], { x: 7.35, y: 5.22, w: 5.1, h: 1.6, isTextBox: true, margin: 0, lineSpacingMultiple: 1.18 });

  s.addNotes(
    "[무엇을 바꿨나] 교수님 요청대로 State에 속한 세그먼트를 모두 이어붙인 뒤 64 TP(46초) " +
    "단위로 균일하게 잘라 학습했습니다. V4는 세그먼트 하나를 통째로 넣고 0으로 패딩했는데, " +
    "그 방식은 예제마다 실제 정보량이 10배 넘게 차이 나는 문제가 있었습니다.\n\n" +
    "[K 선택] K=2를 기본으로 했습니다. K=3에서는 State 2의 윈도우가 23개, K=4에서는 " +
    "State 3이 22개뿐이라 학습이 불안정합니다(실제로 두 경우 모두 해당 모델의 손실이 " +
    "99~100으로 다른 모델의 두 배였습니다). K=3·4 결과도 함께 산출했습니다.\n\n" +
    "[경계 걸침 주의] 윈도우의 50~58%가 이어붙인 자리를 가로지릅니다. 그 자리에는 실제로 " +
    "존재하지 않는 급격한 변화가 생깁니다. 피험자 단위로만 이어붙이고 걸치는 윈도우를 " +
    "버리는 방식도 가능한데, 그러면 예제가 절반으로 줄어 다시 데이터 부족 문제가 생깁니다.");
}

// =============================================================================
// V6 t-SNE — V4와 같은 방식으로 그린 latent 투영 + 그 분리의 정체(대조군)
// (0-2) V6 concat 슬라이드 바로 다음에 들어간다
// =============================================================================
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(0-2) V6 concat 방식") });
  s.addText("(0-2) V6 latent 투영 — V4와 같은 방식의 t-SNE", { placeholder: "title" });

  card(s, { x: 0.6, y: 1.3, w: 12.1, h: 0.5, fill: "1E2A52", name: "t6lead" });
  s.addText("V4와 동일한 절차 — State별 latent를 모두 쌓고 L2 정규화한 뒤 PCA / t-SNE로 2차원 투영",
    { x: 0.85, y: 1.3, w: 11.6, h: 0.5, fontSize: 14, color: "FFFFFF",
      isTextBox: true, margin: 0, valign: "middle" });

  const st = [
    { v: "+0.758", d: "V6 t-SNE 2D 실루엣 (V4는 +0.852)", c: NAVY },
    { v: "1.000", d: "2D kNN 균형정확도 — V4·V6 둘 다 한 점도 안 틀림", c: TEAL },
    { v: "505개", d: "V6 윈도우 (State0 202 + State1 303)", c: CORAL },
  ];
  let x0 = 0.6;
  st.forEach((o, i) => {
    card(s, { x: x0, y: 1.95, w: 3.87, h: 0.95, fill: PALE, name: `t6s-${i}` });
    s.addText(o.v, { x: x0 + 0.25, y: 2.03, w: 3.37, h: 0.42, fontSize: 20, bold: true,
      color: o.c, isTextBox: true, margin: 0, valign: "middle" });
    s.addText(o.d, { x: x0 + 0.25, y: 2.45, w: 3.37, h: 0.38, fontSize: 11, color: MUTED,
      isTextBox: true, margin: 0 });
    x0 += 4.12;
  });

  figure(s, { file: V6F("fig8_tsne_v4_vs_v6.png"), x: 2.67, y: 3.1, w: 8.0, ratio: 2.344,
    caption: "같은 절차로 그린 V4(좌)와 V6(우)의 pooled t-SNE · L2 정규화 후" });

  s.addNotes(
    "[무엇을 그린 것인가] 교수님께서 V4에서 보신 t-SNE 그림을 V6에도 똑같이 그린 것입니다. " +
    "State별 BrainLM이 만든 256차원 latent를 모두 쌓고, 모델마다 벡터 크기가 다를 수 있으니 " +
    "L2 정규화로 크기를 지운 뒤 2차원으로 투영했습니다.\n\n" +
    "[보이는 것] V4든 V6든 State가 완벽하게 갈립니다. 2차원 좌표만 가지고 최근접이웃 " +
    "분류를 돌리면 균형정확도가 1.000, 즉 한 점도 틀리지 않습니다.\n\n" +
    "[하지만 이것을 결과로 말씀드리면 안 됩니다] 다음 장에서 보여드리겠지만, 같은 State " +
    "데이터로 seed만 바꿔 학습한 두 모델도 똑같이 완벽하게 갈립니다. 즉 이 그림이 보여주는 " +
    "것은 'State가 다르다'가 아니라 '모델이 다르다'입니다.\n\n" +
    "[질문이 나오면] V4 그림도 같은 이유로 State 분리의 증거가 아닙니다. 이 점을 먼저 " +
    "말씀드리는 편이 낫다고 판단했습니다. 제대로 된 비교는 V7(공유 모델)에서 했고, " +
    "거기서는 정확도가 1.000이 아니라 0.710이 나옵니다.");
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(0-2) V6 concat 방식") });
  s.addText("(0-2) 그 분리는 State 때문인가 — 대조군", { placeholder: "title" });

  card(s, { x: 0.6, y: 1.3, w: 12.1, h: 0.5, fill: "1E2A52", name: "t6clead" });
  s.addText("State를 바꾸지 않고 seed만 바꿔 두 모델을 학습 — State는 하나뿐인데 투영에서 갈라지는가?",
    { x: 0.85, y: 1.3, w: 11.6, h: 0.5, fontSize: 14, color: "FFFFFF",
      isTextBox: true, margin: 0, valign: "middle" });

  const rows = [
    ["비교한 두 집단", "t-SNE 2D 실루엣", "2D kNN 균형정확도"],
    ["V4 — State 0 vs 1 vs 2 (모델 3개)", "+0.852", "1.000"],
    ["V6 — State 0 vs State 1 (모델 2개)", "+0.758", "1.000"],
    ["대조군 — 같은 State 0, seed만 다름 (모델 2개)", "+0.765", "1.000"],
    ["V7 — 공유 모델 하나, 피험자 단위 5-fold", "—", "0.710"],
  ];
  tbl(s, rows, { x: 0.6, y: 1.95, w: 12.1, colW: [6.1, 3.0, 3.0], rowH: 0.42,
    fontSize: 12.5, hi: 3 });

  figure(s, { file: V6F("fig9_tsne_seed_control.png"), x: 0.6, y: 4.2, w: 6.4, ratio: 2.344,
    caption: "대조군 — 같은 State 0 데이터, seed만 다른 두 모델의 latent (n=202씩)" });

  card(s, { x: 7.2, y: 4.2, w: 5.5, h: 1.75, fill: "FFF7E8", name: "t6cnote" });
  s.addText([
    { text: "결론\n", options: { bold: true, color: AMBER, fontSize: 13.5 } },
    { text: "State가 하나뿐인 대조군(+0.765)이 실제 State 비교(+0.758)보다 오히려 더 잘 " +
            "갈립니다. 따라서 이 투영은 State 분리의 증거가 될 수 없습니다.",
      options: { fontSize: 12.5, color: INK } },
  ], { x: 7.45, y: 4.37, w: 5.0, h: 1.5, isTextBox: true, margin: 0,
       lineSpacingMultiple: 1.18 });

  card(s, { x: 7.2, y: 6.1, w: 5.5, h: 1.2, fill: PALE, name: "t6cnext" });
  s.addText([
    { text: "그래서 V7\n", options: { bold: true, color: NAVY, fontSize: 13.5 } },
    { text: "모델을 하나만 학습해 좌표계를 통일하면 정확도가 1.000이 아니라 0.710으로 " +
            "내려갑니다. 그 값이 보고 가능한 수치입니다.",
      options: { fontSize: 12.5, color: INK } },
  ], { x: 7.45, y: 6.27, w: 5.0, h: 0.95, isTextBox: true, margin: 0,
       lineSpacingMultiple: 1.18 });

  s.addNotes(
    "[대조군 설계] State 0 데이터 202개 윈도우만 가지고, 난수 seed만 111과 222로 바꿔 " +
    "BrainLM을 두 번 학습시켰습니다. 데이터는 완전히 같으니 '진짜 차이'는 0입니다. " +
    "두 모델이 각자 뽑은 latent를 앞 장과 똑같이 L2 정규화 후 t-SNE로 그렸습니다.\n\n" +
    "[결과] 완벽하게 두 덩어리로 갈립니다. 2D 실루엣 +0.765, kNN 균형정확도 1.000. " +
    "실제 State 0 대 State 1 비교(+0.758, 1.000)와 사실상 같거나 오히려 조금 더 높습니다.\n\n" +
    "[의미] 독립적으로 학습한 두 신경망은 각자 좌표축을 무작위로 정합니다. 그래서 어느 " +
    "모델에서 나온 벡터인지에 따라 latent가 서로 다른 영역에 모이고, 투영하면 당연히 " +
    "갈라집니다. 데이터가 같아도 그렇습니다. 즉 V4·V6의 t-SNE 분리는 State의 성질이 아니라 " +
    "'모델이 둘'이라는 실험 설계의 부산물입니다.\n\n" +
    "[그래서 어떻게 했나] 모델을 하나만 학습해 모든 State를 같은 좌표계에 올리는 V7로 " +
    "다시 했습니다. 거기서는 정확도가 1.000이 아니라 0.710으로 떨어지고, 레이블을 섞은 " +
    "귀무분포(0.501 ± 0.024)와 비교해 z = +8.54로 유의합니다. 그것이 저희가 보고할 수 있는 " +
    "값입니다.\n\n" +
    "[솔직하게 덧붙일 점] V7의 PCA·t-SNE 그림에서는 두 State가 눈으로는 섞여 보입니다. " +
    "분류기는 256차원 전체를 쓰지만 그림은 2차원으로 눌러 담기 때문입니다. " +
    "초록에도 이 점을 명시했습니다.");
}
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(0-2) V6 concat 방식") });
  s.addText("(0-2) latent 비교 — 요청 지표와 그 한계", { placeholder: "title" });

  figure(s, { file: V6F("fig3_latent_comparison_fixed.png"), x: 0.97, y: 1.3, w: 11.4, ratio: 3.64,
    caption: "(좌) cross-state 코사인  (중) 귀무분포 대비 — 같은 데이터·다른 seed(+0.153)가 State 간(+0.117)보다 높다  (우) 공통 입력으로 재계산한 RSA·CKA" });

  const rows = [
    ["지표", "기준선\n같은 State0 · seed만 다름", "관심\nState0 vs State1", "판정"],
    ["cross-state 코사인", "+0.153", "+0.117", "기준선이 더 높다 → 데이터 차이를 감지 못함"],
    ["RSA (r)", "0.897 ± 0.012", "0.814 ± 0.002", "3/3 반복에서 기준선이 높다 (차 0.068~0.091)"],
    ["CKA", "0.909 ± 0.014", "0.859 ± 0.003", "3/3 반복에서 기준선이 높다 (차 0.035~0.057)"],
  ];
  tbl(s, rows, { x: 0.6, y: 4.9, w: 12.1, colW: [2.3, 2.9, 2.5, 4.4], rowH: 0.44,
    fontSize: 11.5 });

  card(s, { x: 0.6, y: 6.75, w: 12.1, h: 0.6, fill: "FFF7E8", name: "limitcos" });
  s.addText([
    { text: "읽는 법  ", options: { bold: true, color: AMBER, fontSize: 13.5 } },
    { text: "같은 데이터로 seed만 바꿔 학습한 두 모델이 기준선입니다. 코사인은 기준선이 더 높아 " +
            "판정에 쓸 수 없고, RSA·CKA는 기준선보다 낮아 '표현 내용이 다르다'는 방향을 가리킵니다.",
      options: { fontSize: 12.5, color: INK } },
  ], { x: 0.85, y: 6.75, w: 11.6, h: 0.6, isTextBox: true, margin: 0, valign: "middle" });

  s.addNotes(
    "[요청 지표] cross-state 코사인은 +0.117이 나왔습니다. 그런데 256차원에서 아무 관계 없는 " +
    "두 벡터의 코사인은 95% 구간이 [−0.121, +0.120]입니다. 관측값이 그 안에 있으므로 " +
    "이 지표로는 판정할 수 없습니다.\n\n" +
    "[결정적인 확인] 같은 State 0 데이터로 seed만 바꿔 학습한 두 모델의 코사인이 +0.153으로, " +
    "State 0 대 State 1(+0.117)보다 오히려 높았습니다. 데이터가 완전히 같은데 더 높게 나오니, " +
    "코사인은 데이터 차이를 감지하지 못하는 지표입니다.\n\n" +
    "[왜 그런가] State별로 모델을 따로 학습하면 각 모델의 좌표축이 무작위로 정해집니다. " +
    "어떤 모델의 256차원 좌표를 통째로 회전시켜도 기능적으로 동일한 모델입니다. " +
    "그래서 서로 다른 모델의 벡터를 내적하는 것은 서로 다른 암호로 쓴 글을 겹쳐보는 것과 같습니다.\n\n" +
    "[RSA·CKA를 다시 계산했습니다] 처음에는 모델 A에 State A 데이터를, 모델 B에 State B " +
    "데이터를 넣고 비교했는데, 이러면 '모델 차이'와 '입력 차이'가 섞여 무효입니다. " +
    "두 모델에 똑같은 505개 윈도우를 통과시켜 다시 계산했고, 기준선(같은 State 0 데이터, " +
    "seed만 다름)도 함께 측정했습니다. seed 쌍 세 가지로 반복했습니다.\n\n" +
    "[결과] 기준선 RSA 0.897 ± 0.012 · CKA 0.909 ± 0.014, State 0 대 State 1은 " +
    "RSA 0.814 ± 0.002 · CKA 0.859 ± 0.003입니다. 세 번 모두 기준선이 더 높았고 " +
    "두 분포가 겹치지 않습니다. 즉 좌표계가 다르다는 사실 자체는 의미가 없지만, " +
    "표현이 담고 있는 거리 구조는 실제로 조금 다릅니다. 다만 차이는 0.03~0.09로 작습니다.\n\n" +
    "[그래서] 좌표계 문제가 아예 없는 재구성 손실을 주 지표로 삼았습니다.");
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(0-2) V6 concat 방식") });
  s.addText("(0-2) 교차 재구성 손실 — 좌표계 문제가 없는 지표", { placeholder: "title" });

  card(s, { x: 0.6, y: 1.3, w: 12.1, h: 0.5, fill: "1E2A52", name: "reclead" });
  s.addText("State 0 모델에 State 1 데이터를 넣으면 손실이 커지는가? 커진다면 두 State의 시간 동역학이 실제로 다르다는 직접 증거",
    { x: 0.85, y: 1.3, w: 11.6, h: 0.5, fontSize: 13.5, color: "FFFFFF",
      isTextBox: true, margin: 0, valign: "middle" });

  figure(s, { file: V6F("fig4_cross_recon_loss.png"), x: 0.75, y: 2.0, w: 5.0, ratio: 1.28,
    caption: "행 = 모델, 열 = 데이터" });

  const rows = [
    ["", "data 0", "data 1"],
    ["model 0", "53.21", "64.19"],
    ["model 1", "56.46", "55.51"],
  ];
  tbl(s, rows, { x: 6.5, y: 2.1, w: 6.2, colW: [2.0, 2.1, 2.1], rowH: 0.5, fontSize: 13.5 });

  statCard(s, { x: 6.5, y: 3.9, w: 3.0, h: 1.5, value: "54.36", color: NAVY,
    label: "자기 데이터 평균" });
  statCard(s, { x: 9.7, y: 3.9, w: 3.0, h: 1.5, value: "60.32", color: CORAL,
    label: "남의 데이터 평균" });

  card(s, { x: 6.5, y: 5.5, w: 6.2, h: 1.7, fill: "FDF3F4", name: "asym" });
  s.addText([
    { text: "+11.0%", options: { bold: true, color: CORAL, fontSize: 20 } },
    { text: "  남의 데이터에서 손실 증가\n", options: { bold: true, color: CORAL, fontSize: 12.5 } },
    { text: "이 수치는 폐기했습니다. 대각선에 학습 데이터가 섞여 있었고, "
            + "미학습 윈도우에서는 −0.4%입니다 (다음 장).",
      options: { fontSize: 11.5, bold: true, color: "8C2F39" } },
  ], { x: 6.75, y: 5.65, w: 5.7, h: 1.4, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });

  s.addNotes(
    "[왜 이 지표인가] 좌표계를 비교하지 않고 '성능'을 비교하므로 회전 문제가 없습니다. " +
    "State가 의미 없다면 자기 데이터든 남의 데이터든 손실이 같아야 합니다.\n\n" +
    "[결과] 자기 데이터 평균 54.36, 남의 데이터 평균 60.32로 11.0% 증가했습니다.\n\n" +
    "[반드시 짚을 비대칭] model 0은 자기 53.21 → 남 64.19로 20.6% 나빠지는데, " +
    "model 1은 자기 55.51 → 남 56.46으로 1.7%밖에 안 나빠집니다. 즉 효과가 거의 " +
    "model 0에서만 나옵니다. State 1 데이터가 더 다양해서 State 1 모델이 일반화를 " +
    "잘 배운 것일 수 있습니다(윈도우 303개 vs 202개).\n\n" +
    "[이 숫자는 폐기했습니다] 자기 데이터 칸에 그 모델의 학습 윈도우가 75% 섞여 " +
    "있었습니다. 학습에 쓰지 않은 윈도우에서만 다시 재면 +11.0%가 −0.4%가 됩니다. " +
    "다음 장에서 정정 내용을 설명드립니다. 이 장은 무엇이 잘못됐는지 보여드리기 위해 " +
    "남겨두었습니다.");
}

// =============================================================================
// 정정 슬라이드 — 교차 재구성 손실의 학습 데이터 누수
// (0-2) 교차 재구성 손실 슬라이드 바로 다음
// =============================================================================
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(0-2) V6 concat 방식") });
  s.addText("(0-2) 정정 — 앞 장의 +11.0%는 학습 데이터 누수였다", { placeholder: "title" });

  card(s, { x: 0.6, y: 1.3, w: 12.1, h: 0.5, fill: "8C2F39", name: "leaklead" });
  s.addText("대각선(자기 데이터)에는 그 모델이 학습에 쓴 윈도우가 75% 섞여 있었다 — 미학습 윈도우(val + test)에서만 다시 측정",
    { x: 0.85, y: 1.3, w: 11.6, h: 0.5, fontSize: 13.5, color: "FFFFFF",
      isTextBox: true, margin: 0, valign: "middle" });

  const rows = [
    ["자기 vs 남의 데이터 손실 증가율", "전체 윈도우\n(기존 보고)", "미학습 윈도우만\n(누수 없음)", "평가 예제 수"],
    ["V6 K=2  전체", "+11.0%", "−0.4%", "47 + 76"],
    ["V6 K=2  model 0", "+20.6%", "−0.8%", "47"],
    ["V6 K=2  model 1", "+1.7%", "+0.1%", "76"],
    ["V6 K=4  전체", "−3.7%", "−8.6%", "57/56/36/8"],
    ["V4 방식 (세그먼트 1개 = 예제, 0 패딩)  전체", "+11.0%", "+0.5%", "38/32/27/2"],
  ];
  tbl(s, rows, { x: 0.6, y: 2.0, w: 12.1, colW: [5.3, 2.4, 2.6, 1.8], rowH: 0.52,
    fontSize: 12, hi: 1 });

  card(s, { x: 0.6, y: 5.3, w: 5.95, h: 1.9, fill: "FDF3F4", name: "leakwhy" });
  s.addText([
    { text: "무엇이 잘못됐나\n", options: { bold: true, color: CORAL, fontSize: 14 } },
    { text: "각 State의 전체 윈도우에서 손실을 쟀습니다. 그런데 그 안에는 해당 모델이 " +
            "학습에 쓴 윈도우가 들어 있습니다(K=2: 155/202, 227/303). 남의 데이터는 " +
            "전부 처음 보는 것이므로, 비교가 '학습한 것 vs 처음 보는 것'이 되어버렸습니다.",
      options: { fontSize: 12, color: INK } },
  ], { x: 0.85, y: 5.47, w: 5.45, h: 1.6, isTextBox: true, margin: 0,
       lineSpacingMultiple: 1.18 });

  card(s, { x: 6.75, y: 5.3, w: 5.95, h: 1.9, fill: PALE, name: "leakmean" });
  s.addText([
    { text: "그래서 무엇이 남는가\n", options: { bold: true, color: NAVY, fontSize: 14 } },
    { text: "State별 독립 학습으로는 State 간 차이를 보일 수 없습니다. 미학습 데이터에서 " +
            "효과가 사라집니다(V4·V6, K = 2·3·4 전부). DC와 dwell time 결과는 머신러닝과 " +
            "무관하므로 영향받지 않습니다.",
      options: { fontSize: 12, color: INK } },
  ], { x: 7.0, y: 5.47, w: 5.45, h: 1.6, isTextBox: true, margin: 0,
       lineSpacingMultiple: 1.18 });

  s.addNotes(
    "[먼저 정정드립니다] 앞 장의 +11.0%는 쓸 수 없는 수치입니다. 제가 각 State의 " +
    "'전체' 윈도우에서 손실을 쟀는데, 자기 데이터 칸에는 그 모델이 학습에 사용한 윈도우가 " +
    "75% 들어 있었습니다. 반면 남의 데이터는 전부 처음 보는 것입니다. 그래서 그 차이는 " +
    "'State가 다르다'가 아니라 '학습한 것을 더 잘 복원한다', 즉 암기를 잰 것이었습니다.\n\n" +
    "[다시 측정] 저장된 체크포인트를 그대로 불러와 학습에 쓰지 않은 윈도우(val + test) " +
    "에서만 다시 쟀습니다. K=2에서 +11.0%가 −0.4%가 됩니다. model 0의 +20.6%도 " +
    "−0.8%로 사라집니다. K=4는 −3.7%에서 −8.6%로 더 나빠집니다.\n\n" +
    "[V4 방식도 확인했습니다] 교수님께서 물으신 '세그먼트 하나를 예제 하나로 넣고 " +
    "0으로 패딩하는' V4 방식으로도 다시 학습해 같은 계산을 했습니다. 전체 예제 기준으로는 " +
    "+11.0%로 좋아 보이지만 미학습 예제에서는 +0.5%입니다. 방식의 문제가 아니라 " +
    "측정의 문제였습니다.\n\n" +
    "[레이블 섞기 대조군은 어떻게 되나] 그 대조군은 실제와 섞음 양쪽 모두 같은 누수를 " +
    "갖고 있으므로 비교 자체는 성립합니다. 다만 의미가 달라집니다. 이제 그것이 말해주는 " +
    "것은 '같은 State로 묶인 세그먼트들이 무작위 분할보다 서로 비슷해서 모델이 더 잘 " +
    "외운다'이지, '두 State의 동역학이 다르다'가 아닙니다.\n\n" +
    "[영향 범위] DC와 dwell time은 연결성 행렬에서 바로 계산한 통계이므로 이 문제와 " +
    "무관합니다. 영향을 받는 것은 BrainLM 표현학습 비교뿐입니다. 초록에서도 해당 내용을 " +
    "빼고 DC와 dwell time 두 결과로 다시 썼습니다.");
}
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(0-2) V6 concat 방식") });
  s.addText("(0-2) 평균이 아니라 분포로 — 윈도우 505개", { placeholder: "title" });

  card(s, { x: 0.6, y: 1.3, w: 12.1, h: 0.5, fill: "1E2A52", name: "wlead" });
  s.addText("앞 장은 모델×데이터 조합당 평균 하나였다. 윈도우 하나하나의 손실을 분포로 보면 두 분포가 실제로 갈라지는지 확인할 수 있다",
    { x: 0.85, y: 1.3, w: 11.6, h: 0.5, fontSize: 13.5, color: "FFFFFF",
      isTextBox: true, margin: 0, valign: "middle" });

  figure(s, { file: V6F("fig6_window_loss_dist.png"), x: 0.75, y: 1.95, w: 11.8, ratio: 3.26,
    caption: "(좌·중) 모델별 자기 데이터 vs 남의 데이터 손실 분포  (우) 실제와 대조군 비교 — "
      + "아래 표의 '자기 데이터'에는 학습 윈도우가 포함되어 있다 (앞 장의 정정 참조)" });

  const rows = [
    ["", "자기 데이터", "남의 데이터", "증가율", "Welch t", "p", "Cohen's d"],
    ["model 0", "0.527 (n=202)", "0.642 (n=303)", "+21.9%", "9.39", "4.1e-19", "+0.86"],
    ["model 1", "0.556 (n=303)", "0.560 (n=202)", "+0.7%", "0.39", "0.70", "+0.04"],
  ];
  tbl(s, rows, { x: 0.6, y: 5.6, w: 12.1, colW: [1.5, 2.1, 2.1, 1.5, 1.5, 1.6, 1.8],
    rowH: 0.4, fontSize: 12 });

  card(s, { x: 0.6, y: 6.9, w: 12.1, h: 0.0, fill: PALE, name: "spacer" });

  s.addNotes(
    "[왜 분포로 보는가] 평균 두 개만 비교하면 '정말 갈라지는지'를 알 수 없습니다. " +
    "윈도우 505개 각각의 손실을 그려 보면 분포가 겹치는 정도까지 드러납니다.\n\n" +
    "[model 0] 자기 데이터 0.527 vs 남의 데이터 0.642로 21.9% 높습니다. " +
    "Welch t = 9.39, p = 4.1e-19, Cohen's d = +0.86으로 큰 효과입니다. " +
    "다만 d = 0.86이어도 두 분포는 상당 부분 겹칩니다 — 개별 윈도우를 보고 어느 State인지 " +
    "맞히는 것은 여전히 어렵습니다.\n\n" +
    "[model 1] 자기 0.556 vs 남 0.560으로 0.7% 차이, p = 0.70입니다. " +
    "통계적으로 아무 차이가 없습니다. 즉 State 1 모델은 State 0 데이터를 자기 데이터만큼 " +
    "잘 재구성합니다.\n\n" +
    "[이 비대칭이 핵심] 앞 장의 '평균 +11%'는 model 0의 +21.9%와 model 1의 +0.7%를 " +
    "평균한 값입니다. 효과가 한쪽에서만 나옵니다. State 1은 윈도우가 303개로 더 많고 " +
    "더 다양해서, 그 모델이 일반화를 잘 배웠을 가능성이 있습니다. 데이터 양을 맞춰 " +
    "다시 검증할 필요가 있습니다.\n\n" +
    "[오른쪽 패널] 윈도우 단위로 통합하면 실제 +12.0%, 대조군 +7.6%입니다. " +
    "앞 장의 배치 단위 집계(+10.97% vs +5.88%)와 약간 다른데, 평균을 내는 단위가 " +
    "다르기 때문입니다.\n\n" +
    "[정정] 이 분포의 '자기 데이터' 쪽에도 학습 윈도우가 섞여 있습니다. 따라서 " +
    "model 0의 +21.9%(p = 4.1e-19)는 State 차이가 아니라 암기를 반영합니다. " +
    "학습에 쓰지 않은 윈도우만 보면 model 0은 −0.8%, model 1은 +0.1%로 차이가 " +
    "없습니다. 흥미롭게도 원래도 차이가 없던 model 1 쪽이 정정 후의 결론과 일치합니다.");
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(0-2) V6 concat 방식") });
  s.addText("(0-2) 레이블 섞기 대조군 — 이 차이는 진짜인가", { placeholder: "title" });

  card(s, { x: 0.6, y: 1.3, w: 12.1, h: 0.5, fill: "1E2A52", name: "ctrllead" });
  s.addText("State별 세그먼트 수는 그대로 두고 어느 세그먼트가 어느 State인지만 무작위로 섞어 전체 과정을 반복 — 실제와 대조군 모두 같은 누수를 가지므로 비교는 성립한다",
    { x: 0.85, y: 1.3, w: 11.6, h: 0.5, fontSize: 13.5, color: "FFFFFF",
      isTextBox: true, margin: 0, valign: "middle" });

  figure(s, { file: V6F("fig5_shuffle_control.png"), x: 1.92, y: 1.95, w: 9.5, ratio: 2.83,
    caption: "(좌) 대조군 귀무분포와 실제값  (우) 개별 실행값" });

  const ccards = [
    { v: "+10.97%", l: "실제 레이블", c: CORAL },
    { v: "+5.88%", l: "대조군 24회 평균 (SD 0.77)", c: MUTED },
    { v: "p = 0.040", l: "permutation 검정 · z = +6.60", c: GREEN },
  ];
  let xx = 0.6;
  ccards.forEach((o, i) => {
    card(s, { x: xx, y: 5.62, w: 3.87, h: 1.2, fill: i === 2 ? "E6F2EC" : PALE, name: `cc-${i}` });
    s.addText(o.v, { x: xx + 0.25, y: 5.72, w: 3.37, h: 0.45, fontSize: 21, bold: true,
      color: o.c, isTextBox: true, margin: 0, valign: "middle" });
    s.addText(o.l, { x: xx + 0.25, y: 6.2, w: 3.37, h: 0.5, fontSize: 11.5, color: INK,
      isTextBox: true, margin: 0 });
    xx += 4.12;
  });

  s.addNotes(
    "[대조군 설계] State 레이블을 무작위로 섞되 State별 크기는 유지합니다. 그러면 " +
    "'State가 아무 의미 없을 때 이 지표가 얼마나 나오는가'를 알 수 있습니다.\n\n" +
    "[핵심 결과] 대조군에서도 손실이 약 6% 증가합니다. 즉 앞 장의 '+11%' 중 절반 이상은 " +
    "State와 무관하게 '모델은 자기 학습 데이터에서 손실이 낮다'는 일반적 현상입니다. " +
    "실제 증거가 되는 것은 대조군을 초과하는 부분입니다.\n\n" +
    "[판정] 실제 +10.97% vs 대조군 24회 평균 +5.88% (SD 0.77). 실제값이 대조군 24개를 " +
    "모두 넘었고 z = +6.60, permutation p = 0.040입니다.\n\n" +
    "[이 결과가 뜻하는 것을 정정합니다] 실제와 대조군 모두 같은 누수(자기 데이터 칸에 " +
    "학습 윈도우가 섞임)를 갖고 있으므로 둘의 비교 자체는 성립합니다. 다만 해석이 " +
    "달라집니다. 미학습 윈도우에서는 실제 효과가 −0.4%로 사라지므로, 이 초과분이 " +
    "말해주는 것은 '두 State의 동역학이 다르다'가 아니라 '같은 State로 묶인 세그먼트들이 " +
    "무작위 분할보다 서로 비슷해서 모델이 자기 학습 데이터를 더 잘 외운다'입니다. " +
    "군집화가 의미 있는 묶음을 찾았다는 증거는 되지만, 일반화되는 동역학 차이의 " +
    "증거는 아닙니다.\n\n" +
    "[남은 한계] ① 윈도우의 절반가량이 이어붙인 자리를 걸칩니다. ② State 레이블이 같은 " +
    "시계열에서 만든 CM에서 왔다는 순환성은 그대로 남습니다. ③ 효과가 model 0에 치우쳐 " +
    "있습니다. ④ K=3·4에서는 극단 State의 데이터 부족으로 오히려 음의 값이 나왔습니다.");
}

// =============================================================================
// V7 결과 — 공유 모델 latent 비교 (V6 대조군 슬라이드 다음에 삽입)
// =============================================================================
pres.addSection({ title: "(0-3) V7 공유 모델" });
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(0-3) V7 공유 모델") });
  s.addText("(0-3) V7은 latent를 어떻게 비교했나", { placeholder: "title" });

  // ── 왜 모델 하나인가 ─────────────────────────────────────────────────
  card(s, { x: 0.6, y: 1.28, w: 5.9, h: 1.9, fill: "FDF3F4", name: "why-v6" });
  s.addText("V6 — State별 모델 2개", { x: 0.85, y: 1.38, w: 5.4, h: 0.32,
    fontSize: 14.5, bold: true, color: CORAL, isTextBox: true, margin: 0 });
  s.addText("모델 0 → latent 좌표계 A\n모델 1 → latent 좌표계 B",
    { x: 0.85, y: 1.74, w: 5.4, h: 0.68, fontSize: 12.5, color: INK,
      fontFace: "Courier New", isTextBox: true, margin: 0, lineSpacingMultiple: 1.3 });
  s.addText("서로 다른 자로 잰 값 → 비교 불가",
    { x: 0.85, y: 2.5, w: 5.4, h: 0.55, fontSize: 13, bold: true, color: CORAL,
      isTextBox: true, margin: 0, valign: "middle" });

  card(s, { x: 6.8, y: 1.28, w: 5.9, h: 1.9, fill: "E6F2EC", name: "why-v7" });
  s.addText("V7 — 모델 1개", { x: 7.05, y: 1.38, w: 5.4, h: 0.32,
    fontSize: 14.5, bold: true, color: GREEN, isTextBox: true, margin: 0 });
  s.addText("모든 State 데이터 → 모델 하나\n윈도우 1,009개 → 좌표계 하나",
    { x: 7.05, y: 1.74, w: 5.4, h: 0.68, fontSize: 12.5, color: INK,
      fontFace: "Courier New", isTextBox: true, margin: 0, lineSpacingMultiple: 1.3 });
  s.addText("같은 자로 잼 → 비교 가능",
    { x: 7.05, y: 2.5, w: 5.4, h: 0.55, fontSize: 13, bold: true, color: GREEN,
      isTextBox: true, margin: 0, valign: "middle" });

  // ── 4단계 절차 ───────────────────────────────────────────────────────
  s.addText("비교 절차", { x: 0.6, y: 3.3, w: 12.1, h: 0.3, fontSize: 14, bold: true,
    color: NAVY, isTextBox: true, margin: 0 });

  const steps = [
    { t: "공유 모델 학습", d: "State 구분 없이 윈도우 1,009개 전부로 BrainLM 1개 학습 (마스킹 15%)", c: NAVY },
    { t: "latent 추출", d: "윈도우마다 CLS 토큰 256개 숫자. 모두 같은 공간에 놓임", c: NAVY },
    { t: "분류", d: "피험자 27명을 5조로. 4조로 분류기 학습 → 남은 1조에서 State 맞히기", c: TEAL },
    { t: "귀무분포", d: "State 레이블을 세그먼트 단위로 무작위 재배정해 20회 반복. 같은 분류기로 재측정", c: CORAL },
  ];
  let x = 0.6;
  steps.forEach((o, i) => {
    card(s, { x, y: 3.68, w: 2.84, h: 1.75, fill: PALE, name: `v7s-${i}` });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.22, y: 3.85, w: 0.42, h: 0.42,
      fill: { color: o.c }, line: { color: o.c, width: 0 }, objectName: `v7n-${i}` });
    s.addText(String(i + 1), { x: x + 0.22, y: 3.85, w: 0.42, h: 0.42, align: "center",
      valign: "middle", fontSize: 13, bold: true, color: "FFFFFF", isTextBox: true, margin: 0 });
    s.addText(o.t, { x: x + 0.75, y: 3.87, w: 1.95, h: 0.38, fontSize: 13.5, bold: true,
      color: o.c, isTextBox: true, margin: 0, valign: "middle" });
    s.addText(o.d, { x: x + 0.22, y: 4.38, w: 2.45, h: 0.95, fontSize: 11, color: INK,
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.18 });
    if (i < 3) {
      s.addText("›", { x: x + 2.84, y: 4.3, w: 0.22, h: 0.45, align: "center",
        fontSize: 19, bold: true, color: "97A3C9", isTextBox: true, margin: 0 });
    }
    x += 3.07;
  });

  // ── 판단 기준 ────────────────────────────────────────────────────────
  card(s, { x: 0.6, y: 5.62, w: 12.1, h: 1.32, fill: "F7F9FC", name: "v7crit" });
  s.addText("판단 기준", { x: 0.85, y: 5.72, w: 11.6, h: 0.3, fontSize: 13.5, bold: true,
    color: NAVY, isTextBox: true, margin: 0 });
  s.addText([
    { text: "레이블을 섞으면 latent와의 관계가 끊기므로 맞힐 수 없어야 정상이다. 실제로 섞은 레이블로는 20회 평균 0.501, " +
            "즉 우연 수준(0.500)과 같았다 — 절차 자체에 허점이 없다는 뜻이다. 반면 원래 레이블로는 ",
      options: { fontSize: 12.5, color: INK } },
    { text: "0.710", options: { fontSize: 12.5, bold: true, color: GREEN } },
    { text: "이 나왔고, 이는 섞은 20회 중 가장 높은 값(0.535)보다도 0.175 높다. → ",
      options: { fontSize: 12.5, color: INK } },
    { text: "z = +8.54,  p = 0.048", options: { fontSize: 12.5, bold: true, color: GREEN } },
  ], { x: 0.85, y: 6.04, w: 11.6, h: 0.82, isTextBox: true, margin: 0,
       lineSpacingMultiple: 1.25 });

  s.addNotes(
    "[이 장의 목적] 다음 장 결과를 보기 전에 '어떻게 비교했는지'를 먼저 설명합니다.\n\n" +
    "[왜 모델이 하나여야 하나] 신경망의 latent 좌표축은 학습할 때마다 무작위로 정해집니다. " +
    "어떤 모델의 256차원 좌표를 통째로 회전시켜도 기능적으로 똑같은 모델입니다. " +
    "그래서 따로 학습한 두 모델의 latent를 내적하거나 한 평면에 겹쳐 그리는 것은 " +
    "서로 다른 암호로 쓴 글을 겹쳐보는 것과 같습니다. 모델을 하나만 쓰면 이 문제가 " +
    "사라집니다.\n\n" +
    "[1단계] State 구분 없이 전체 데이터로 BrainLM 하나를 학습합니다. 라벨을 주지 않고 " +
    "마스킹 복원만 시키므로, 모델은 State가 뭔지 모르는 채로 신호의 표현을 배웁니다.\n\n" +
    "[2단계] 윈도우마다 CLS 토큰 256개 숫자를 뽑습니다. 모델이 하나니 1,009개가 모두 " +
    "같은 공간에 놓입니다.\n\n" +
    "[3단계] 분류기는 로지스틱 회귀입니다. 256개 숫자에 각각 가중치를 곱해 더한 값으로 " +
    "State를 판정합니다. 중요한 건 피험자 단위로 나눴다는 점입니다 — 학습에 전혀 쓰지 " +
    "않은 사람에게서 맞히는지 보므로, 외워서 맞히는 것이 불가능합니다.\n\n" +
    "[4단계] 꼬리표를 세그먼트 단위로 섞습니다. 윈도우 단위로 섞지 않는 이유는, 같은 " +
    "세그먼트에서 나온 윈도우들이 서로 강하게 닮아 있어 귀무분포가 지나치게 느슨해지기 " +
    "때문입니다.\n\n" +
    "[질문 나오면] '왜 분류기를 쓰느냐, 그냥 그림으로 보면 안 되느냐' — t-SNE는 256차원을 " +
    "2차원으로 눌러 담으므로 정보가 사라질 수 있고, 반대로 없는 군집을 만들어내기도 합니다. " +
    "그림은 보조이고 판단은 분류 정확도와 치환 검정으로 해야 합니다.");
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(0-3) V7 공유 모델") });
  s.addText("(0-3) V7: 모델 하나로 학습해 latent를 직접 비교", { placeholder: "title" });

  card(s, { x: 0.6, y: 1.28, w: 12.1, h: 0.52, fill: "1E2A52", name: "v7lead" });
  s.addText("State별 모델은 좌표계가 달라 latent를 비교할 수 없다. 모델을 하나만 학습하면 윈도우 1,009개가 같은 공간에 놓인다",
    { x: 0.85, y: 1.28, w: 11.6, h: 0.52, fontSize: 13.5, color: "FFFFFF",
      isTextBox: true, margin: 0, valign: "middle" });

  figure(s, { file: V7F("fig1_shared_latent.png"), x: 0.9, y: 1.95, w: 11.5, ratio: 3.44,
    caption: "(좌) PCA  (중) t-SNE  (우) 처음 보는 피험자에서의 State 분류 정확도와 레이블 치환 귀무분포" });

  const st = [
    { v: "0.710", d: "균형정확도 · 피험자 단위 5-fold (우연 0.500)", c: GREEN },
    { v: "0.501", d: "레이블 치환 20회 평균 ± 0.024", c: MUTED },
    { v: "p = 0.048", d: "permutation 검정 · z = +8.54", c: GREEN },
  ];
  let x0 = 0.6;
  st.forEach((o, i) => {
    card(s, { x: x0, y: 5.5, w: 3.87, h: 1.0, fill: i === 1 ? PALE : "E6F2EC", name: `v7-${i}` });
    s.addText(o.v, { x: x0 + 0.25, y: 5.58, w: 3.37, h: 0.42, fontSize: 20, bold: true,
      color: o.c, isTextBox: true, margin: 0, valign: "middle" });
    s.addText(o.d, { x: x0 + 0.25, y: 6.0, w: 3.37, h: 0.42, fontSize: 11, color: INK,
      isTextBox: true, margin: 0 });
    x0 += 4.12;
  });

  card(s, { x: 0.6, y: 6.62, w: 12.1, h: 0.42, fill: "FFF7E8", name: "v7warn" });
  s.addText([
    { text: "읽는 법  ", options: { bold: true, color: AMBER, fontSize: 12.5 } },
    { text: "t-SNE에서는 두 State가 섞여 보이지만 분류는 71%다. 2차원 투영에서 사라지는 정보를 256차원 분류기는 쓴다.",
      options: { fontSize: 12.5, color: INK } },
  ], { x: 0.85, y: 6.62, w: 11.6, h: 0.42, isTextBox: true, margin: 0, valign: "middle" });

  s.addNotes(
    "[왜 V7이 필요한가] V6까지는 State별로 모델을 따로 학습했습니다. 그러면 각 모델의 " +
    "256차원 좌표축이 무작위로 정해져, 서로 다른 모델의 latent를 비교하는 것 자체가 " +
    "성립하지 않습니다. 모델을 하나만 학습하면 윈도우 1,009개의 latent가 같은 공간에 " +
    "놓이고, 비로소 'State가 갈리는가'를 물을 수 있습니다.\n\n" +
    "[결과] 처음 보는 피험자의 latent로 State를 맞히는 균형정확도가 0.710입니다. " +
    "우연 수준은 0.500이고, 5개 fold 모두 0.66~0.77로 일관됩니다.\n\n" +
    "[귀무분포] 레이블을 세그먼트 단위로 섞어 20회 반복했더니 평균 0.501이 나왔습니다. " +
    "정확히 우연 수준이라 검정이 제대로 작동한다는 뜻입니다. 실제값 0.710은 귀무분포의 " +
    "최댓값 0.535보다도 한참 위입니다. z = +8.54, permutation p = 0.048입니다.\n\n" +
    "[그림이 안 갈라지는 이유 — 질문 나오면] t-SNE는 256차원을 2차원으로 눌러 담습니다. " +
    "State를 가르는 정보가 여러 차원에 흩어져 있으면 2차원에서는 사라집니다. " +
    "분류기는 256차원 전체를 쓰므로 2차원에서 안 보여도 가를 수 있습니다. " +
    "반대로 t-SNE가 갈라 보인다고 해서 증거가 되는 것도 아닙니다 — t-SNE는 없는 군집도 " +
    "만들어냅니다. 그림은 보조이고 판단은 분류 정확도로 해야 합니다.\n\n" +
    "[한계] 첫째, State 레이블이 같은 시계열에서 만든 CM에서 왔다는 순환성이 남습니다. " +
    "'CM으로 나눈 구분이 원시 신호의 동역학에도 드러난다'는 뜻이지 독립적 검증은 " +
    "아닙니다. 둘째, 치환 20회라 p의 하한이 0.048입니다. 셋째, K=2 기준입니다.\n\n" +
    "[의미] 이 프로젝트에서 latent 비교로는 처음으로 귀무분포를 넘은 결과입니다. " +
    "초록의 '상태별 표현이 다르다'는 주장은 이 결과를 근거로 삼는 것이 가장 정확합니다.");
}

// ===========================================================================
// 표지 — 사용자 구성에 맞춰 요청분석 파트 앞으로 이동
// ===========================================================================
{
  const s = pres.addSlide({ masterName: "TITLE_DARK", ...S("표지") });
  s.addText("교수님 요청 추가분석 결과", { placeholder: "eyebrow" });
  s.addText("Degree Centrality 기반 Brain State 해석", { placeholder: "title" });
  s.addText("(1) DC 정의  (2) 표면 시각화  (3) 7-Network 요약  (4) 통계 검정  (5) Dwell time",
    { placeholder: "body" });
  s.addText("V4 K=4 · 피험자 27명 · 세그먼트 308개 · Schaefer-100 / Yeo 7-Network",
    { placeholder: "meta" });
  s.addNotes("요청하신 네 가지 분석과 dwell time 분석을 모두 완료했습니다. " +
    "각 항목을 질문과 답 형식으로 정리했고, 마지막에 예상 질문 즉답을 붙였습니다.");
}

// =============================================================================
pres.addSection({ title: "(1) DC 정의" });
{
  const s = pres.addSlide({ masterName: "SECTION", ...S("(1) DC 정의") });
  s.addText("(1)", { placeholder: "num" });
  s.addText("Row-wise thresholding → 100×1 DC", { placeholder: "title" });
  s.addText("100×100 행렬의 각 행에서 상위 10%만 남기고 행 방향 합산", { placeholder: "body" });
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(1) DC 정의") });
  s.addText("(1) DC를 어떻게 계산했는가", { placeholder: "title" });
  const yy = qa(s, {
    q: "100×100 행렬에 row-wise thresholding을 적용해 100×1 DC를 만들어 달라",
    a: "각 행 99개 후보 중 상위 10개만 남겨 합산 → State별 DC 산출 완료",
    color: TEAL,
  });

  card(s, { x: 0.6, y: yy, w: 5.9, h: 1.65, fill: "F7F9FC", name: "steps" });
  s.addText(
    "1) 대각(자기 연결) 제외        → 행당 99개 후보\n" +
    "2) 각 행에서 상위 10% 유지     → 행당 10개\n" +
    "3) 유지된 element를 행 방향 합 → DC_i",
    { x: 0.85, y: yy + 0.2, w: 5.4, h: 1.25, fontSize: 12, color: INK, fontFace: "Courier New",
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.45 });

  const rows = [
    ["State", "n_CM", "평균 DC", "최대 DC ROI"],
    ["State 1", "121", "5.23", "LH_Vis_8"],
    ["State 0", "99", "6.96", "LH_Vis_9"],
    ["State 2", "72", "8.61", "LH_Vis_9"],
    ["State 3", "16", "11.35", "RH_Vis_8"],
  ];
  tbl(s, rows, { x: 6.8, y: yy, w: 5.9, colW: [1.6, 1.0, 1.4, 1.9], rowH: 0.33, fontSize: 11.5 });

  card(s, { x: 0.6, y: yy + 1.85, w: 12.1, h: 1.35, fill: PALE, name: "interp1" });
  s.addText([
    { text: "해석  ", options: { bold: true, color: NAVY, fontSize: 14 } },
    { text: "DC 크기가 State 1 < 0 < 2 < 3 순서로 뚜렷한 계단을 이룹니다. 네 State 모두 " +
            "최대 DC ROI가 Visual network 소속이라는 점이 이미 여기서 드러납니다 — " +
            "크기는 달라도 가장 강한 허브의 위치는 같습니다.",
      options: { fontSize: 13.5, color: INK } },
  ], { x: 0.85, y: yy + 2.03, w: 11.6, h: 1.0, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  s.addNotes("CM 평균을 먼저 낸 뒤 thresholding을 적용했습니다. 세그먼트별 DC를 평균하는 것과는 " +
    "값이 다릅니다(thresholding이 비선형이라). 평균을 먼저 내는 쪽이 잡음에 강합니다.");
}

// =============================================================================
pres.addSection({ title: "(2) 표면 시각화" });
{
  const s = pres.addSlide({ masterName: "SECTION", ...S("(2) 표면 시각화") });
  s.addText("(2)", { placeholder: "num" });
  s.addText("Brain surface 시각화", { placeholder: "title" });
  s.addText("ENIGMA TOOLBOX · fsa5 표면 · parcel_to_surface + plot_cortical", { placeholder: "body" });
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(2) 표면 시각화") });
  s.addText("(2) 100×1 DC를 피질 표면에 올리면", { placeholder: "title" });
  const yy = qa(s, {
    q: "100×1 벡터를 brain surface에 시각화해 달라 (ENIGMA TOOLBOX)",
    a: "State별 DC 표면 맵 완료 — 공통 color range로 네 State를 직접 비교",
    color: TEAL,
  });
  figure(s, { file: ADD("fig1_surface_dc_by_state.png"), x: 4.12, y: yy, w: 5.1, ratio: 1.27,
    caption: "State별 DC 피질 분포 (공통 color range)" });
  s.addNotes("네 장 모두 밝은 영역의 위치가 비슷하고 전체 밝기만 다릅니다. " +
    "이것이 뒤에서 다룰 '전역 강도' 결론의 첫 단서입니다.");
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(2) 표면 시각화") });
  s.addText("(2) 전체 평균을 빼면 State별 특이성이 보인다", { placeholder: "title" });
  figure(s, { file: ADD("fig2_surface_dc_deviation.png"), x: 0.6, y: 1.35, w: 6.1, ratio: 1.28,
    caption: "State별 DC − 전체 평균 DC (붉은색 = 그 State에서 상대적으로 강화)" });

  bullets(s, { x: 7.1, y: 1.5, w: 5.6, h: 2.6, fontSize: 14, items: [
    { text: "앞 슬라이드는 '절대 크기'라 State 3이 통째로 밝게 보인다", bold: true },
    "전체 평균을 빼면 각 State에서 상대적으로 두드러지는 영역만 남는다",
    "이 편차 맵에서도 패턴이 State 간에 크게 다르지 않다",
  ]});

  card(s, { x: 7.1, y: 4.35, w: 5.6, h: 1.85, fill: PALE, name: "interp2" });
  s.addText([
    { text: "해석\n", options: { bold: true, color: NAVY, fontSize: 14 } },
    { text: "표면 맵만으로도 \"허브 지형은 그대로, 전체 수위만 오르내린다\"는 " +
            "인상을 받을 수 있습니다. 이를 수치로 확인한 것이 18번 슬라이드의 상대 DC 분석입니다.",
      options: { fontSize: 13, color: INK } },
  ], { x: 7.35, y: 4.55, w: 5.1, h: 1.5, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  s.addNotes("ENIGMA TOOLBOX는 vtk 9.3.1에 고정해야 동작합니다. 9.4 이상에서는 오류가 납니다.");
}

// =============================================================================
pres.addSection({ title: "(3) 7-Network" });
{
  const s = pres.addSlide({ masterName: "SECTION", ...S("(3) 7-Network") });
  s.addText("(3)", { placeholder: "num" });
  s.addText("Yeo 7-Network 요약", { placeholder: "title" });
  s.addText("Schaefer2018_100Parcels_7Networks_order_info.txt 레이블 사용", { placeholder: "body" });
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(3) 7-Network") });
  s.addText("(3) 100×1을 7×1로 요약하면", { placeholder: "title" });
  const yy = qa(s, {
    q: "100×1 벡터를 7-Network 레이블로 7×1 요약한 뒤 bar plot으로 표현해 달라",
    a: "네트워크 내 ROI의 DC 평균으로 7×1 산출 — 모든 State에서 Vis 최고 · Limbic 최저",
    color: TEAL,
  });

  const rows = [
    ["Network", "n_roi", "State 1", "State 0", "State 2", "State 3"],
    ["Visual", "17", "6.67", "8.93", "10.67", "13.68"],
    ["Somatomotor", "14", "4.88", "8.14", "10.43", "12.82"],
    ["Dorsal Attention", "15", "5.66", "7.60", "9.40", "12.19"],
    ["Salience / VentAttn", "12", "4.64", "6.36", "8.13", "11.04"],
    ["Limbic", "5", "2.41", "3.56", "4.33", "6.83"],
    ["Frontoparietal Cont", "13", "4.97", "5.81", "6.90", "9.30"],
    ["Default Mode", "24", "5.16", "6.11", "7.65", "10.54"],
  ];
  tbl(s, rows, { x: 0.6, y: yy, w: 12.1, colW: [3.1, 1.2, 1.95, 1.95, 1.95, 1.95],
    rowH: 0.33, fontSize: 11.5 });

  card(s, { x: 0.6, y: yy + 2.75, w: 12.1, h: 1.25, fill: PALE, name: "interp3" });
  s.addText([
    { text: "해석  ", options: { bold: true, color: NAVY, fontSize: 14 } },
    { text: "7개 네트워크 전부가 State 1 → 3 방향으로 함께 올라갑니다. 특정 네트워크만 오르고 " +
            "다른 네트워크는 내려가는 패턴이 아닙니다. 네트워크 간 순위(Vis > SomMot > DorsAttn > … > Limbic)도 " +
            "네 State에서 동일하게 유지됩니다.",
      options: { fontSize: 13.5, color: INK } },
  ], { x: 0.85, y: yy + 2.93, w: 11.6, h: 0.9, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  s.addNotes("표의 모든 행이 같은 방향으로 움직인다는 점이 핵심입니다. " +
    "이것이 '전역 수위' 해석의 직접적 근거입니다.");
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(3) 7-Network") });
  s.addText("(3) 네트워크별 bar plot", { placeholder: "title" });
  figure(s, { file: ADD("fig5_network_dc_barplot.png"), x: 0.9, y: 1.4, w: 11.5, ratio: 2.96,
    caption: "(좌) 네트워크별 State 비교 grouped bar plot  (우) 네트워크별 State 프로파일" });
  card(s, { x: 0.6, y: 5.72, w: 12.1, h: 1.22, fill: PALE, name: "interp3b" });
  s.addText([
    { text: "읽는 법  ", options: { bold: true, color: NAVY, fontSize: 14 } },
    { text: "왼쪽 그림에서 네 색 막대가 모든 네트워크에서 같은 순서(파랑<보라<주황<빨강)로 " +
            "늘어섭니다. 오른쪽 프로파일의 네 선이 서로 교차하지 않고 평행하게 놓이는 것도 같은 뜻입니다.",
      options: { fontSize: 13.5, color: INK } },
  ], { x: 0.85, y: 5.9, w: 11.6, h: 0.85, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });
}

// =============================================================================
pres.addSection({ title: "(4) 통계 검정" });
{
  const s = pres.addSlide({ masterName: "SECTION", ...S("(4) 통계 검정") });
  s.addText("(4)", { placeholder: "num" });
  s.addText("State 간 DC 차이 검정", { placeholder: "title" });
  s.addText("관측 단위 = (subject × State) 75개 · ANOVA + pair별 two-sample t-test",
    { placeholder: "body" });
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(4) 통계 검정") });
  s.addText("(4-a) State 간 DC가 다른가", { placeholder: "title" });
  const yy = qa(s, {
    q: "subject별 CM으로 DC를 만들어 State별로 다른지 ANOVA로 확인 (F, p 보고)",
    a: "F(3, 71) = 218.56,  p = 8.97e-36,  η² = 0.90 — 매우 강하게 유의",
    color: GREEN,
  });

  const rows = [
    ["State", "n", "평균 DC", "SD"],
    ["State 1", "21", "5.979", "0.675"],
    ["State 0", "24", "7.661", "0.544"],
    ["State 2", "21", "9.625", "0.806"],
    ["State 3", "9", "12.185", "0.623"],
  ];
  tbl(s, rows, { x: 0.6, y: yy, w: 4.5, colW: [1.5, 0.8, 1.2, 1.0], rowH: 0.34, fontSize: 12 });

  bullets(s, { x: 5.4, y: yy, w: 7.3, h: 1.8, fontSize: 13.5, items: [
    { text: "관측 단위 = (subject × State) 쌍, 총 N = 75", bold: true },
    "비모수 확인: Kruskal-Wallis H = 66.78, p = 2.08e-14 → 같은 결론",
    "η² = 0.90 — 전체 분산의 90%를 State 구분이 설명",
  ]});

  card(s, { x: 0.6, y: yy + 2.0, w: 12.1, h: 1.3, fill: "FFF7E8", name: "caution4a" });
  s.addText([
    { text: "주의  ", options: { bold: true, color: AMBER, fontSize: 14 } },
    { text: "F값이 크다는 것은 \"차이가 있다\"는 뜻이지 \"경계를 잘 찾았다\"는 뜻이 아닙니다. " +
            "무작위로 잘라도 비슷한 크기의 F가 나옵니다 (19번 슬라이드).",
      options: { fontSize: 13.5, color: INK } },
  ], { x: 0.85, y: yy + 2.18, w: 11.6, h: 0.95, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  s.addNotes("평균 DC가 앞의 (1)번 표와 다른 이유는, 여기서는 피험자별로 먼저 CM을 평균한 뒤 " +
    "DC를 계산했기 때문입니다. (1)번은 State 전체 CM을 한 번에 평균했습니다.");
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(4) 통계 검정") });
  s.addText("(4-a) 어느 State 쌍이 다른가", { placeholder: "title" });
  const yy = qa(s, {
    q: "각 state pair별 DC 비교를 two-sample t-test로 (t, p 보고)",
    a: "6개 쌍 전부 유의 — |t| = 8.48 ~ 23.57,  모두 FDR q < 1e-8",
    color: GREEN,
  });

  const rows = [
    ["Pair", "평균 (a / b)", "차이", "t", "p", "FDR q", "Cohen's d"],
    ["State0 vs State1", "7.66 / 5.98", "+1.68", "+9.248", "8.78e-12", "1.05e-11", "+2.76"],
    ["State0 vs State2", "7.66 / 9.63", "−1.96", "−9.693", "2.21e-12", "3.31e-12", "−2.90"],
    ["State0 vs State3", "7.66 / 12.19", "−4.52", "−20.468", "1.44e-19", "4.33e-19", "−8.00"],
    ["State1 vs State2", "5.98 / 9.63", "−3.65", "−15.896", "6.95e-19", "1.39e-18", "−4.91"],
    ["State1 vs State3", "5.98 / 12.19", "−6.21", "−23.568", "5.25e-20", "3.15e-19", "−9.39"],
    ["State2 vs State3", "9.63 / 12.19", "−2.56", "−8.477", "3.23e-09", "3.23e-09", "−3.38"],
  ];
  tbl(s, rows, { x: 0.6, y: yy, w: 12.1, colW: [2.6, 2.0, 1.2, 1.5, 1.6, 1.6, 1.6],
    rowH: 0.37, fontSize: 11.5 });

  card(s, { x: 0.6, y: yy + 2.75, w: 12.1, h: 1.2, fill: PALE, name: "interp4a" });
  s.addText([
    { text: "해석  ", options: { bold: true, color: NAVY, fontSize: 14 } },
    { text: "효과크기 Cohen's d가 2.76~9.39로 극단적으로 큽니다(0.8이면 '큰 효과'). " +
            "다만 이는 관측 단위가 (subject × State)이고 State가 DC 크기 자체로 정의되었기 때문에 " +
            "어느 정도 당연한 결과이기도 합니다.",
      options: { fontSize: 13.5, color: INK } },
  ], { x: 0.85, y: yy + 2.93, w: 11.6, h: 0.85, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(4) 통계 검정") });
  s.addText("(4-b, 4-c) 네트워크·ROI 수준에서는", { placeholder: "title" });
  const yy = qa(s, {
    q: "네트워크별, ROI별로도 State 간 차이가 있는가",
    a: "7 / 7 네트워크, 100 / 100 ROI 모두 FDR q < 0.05 — 전부 유의",
    color: GREEN,
  });

  figure(s, { file: ADD("fig7_anova_boxplots.png"), x: 2.67, y: yy, w: 8.0, ratio: 2.0,
    caption: "Global DC 및 7개 네트워크별 DC의 State 간 분포 (점 = subject × State 관측)" });

  s.addNotes("네트워크별 F는 31.2에서 110.9 사이입니다. ROI 수준에서는 100개 전부가 " +
    "FDR 보정 후에도 유의했습니다. 뒤집어 말하면 '어느 영역이 특별히 다른가'를 " +
    "가려내지 못했다는 뜻이기도 합니다 — 전부 다르다는 건 정보가 없는 것과 같습니다.");
}

// =============================================================================
pres.addSection({ title: "(5) Dwell time" });
{
  const s = pres.addSlide({ masterName: "SECTION", ...S("(5) Dwell time") });
  s.addText("(5)", { placeholder: "num" });
  s.addText("Dwell time 분석", { placeholder: "title" });
  s.addText("time point 개수 × 0.72초(TR) · 평균±표준편차 · ANOVA + pair별 t-test",
    { placeholder: "body" });
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(5) Dwell time") });
  s.addText("(5) State별 dwell time", { placeholder: "title" });
  const yy = qa(s, {
    q: "각 subject가 각 state에 머무는 시간(TP × 0.72)을 State별 평균±SD로 리포트",
    a: "두 정의 모두 산출 — DC가 가장 낮은 State 1이 가장 오래 유지",
    color: TEAL,
  });

  const rows = [
    ["State", "n", "총 점유 [초]", "방문당 체류 [초]", "방문 횟수"],
    ["State 1", "21", "491.3 ± 327.1", "340.8 ± 298.4", "1.71"],
    ["State 0", "24", "301.2 ± 235.8", "116.1 ± 72.4", "2.42"],
    ["State 2", "21", "225.6 ± 202.7", "90.7 ± 60.8", "2.10"],
    ["State 3", "9", "115.8 ± 128.4", "66.3 ± 53.0", "1.44"],
  ];
  tbl(s, rows, { x: 0.6, y: yy, w: 6.3, colW: [1.3, 0.75, 1.65, 1.7, 0.9], rowH: 0.36, fontSize: 11.5 });

  figure(s, { file: ADD("fig13_dwell_time.png"), x: 7.15, y: yy - 0.05, w: 5.55, ratio: 2.50 });

  card(s, { x: 0.6, y: yy + 2.1, w: 12.1, h: 1.45, fill: PALE, name: "interp5" });
  s.addText([
    { text: "두 가지 정의  ", options: { bold: true, color: NAVY, fontSize: 14 } },
    { text: "① 총 점유 시간 = 그 State 세그먼트 길이의 총합 × TR  ② 방문당 체류 시간 = " +
            "같은 State가 연속된 구간(bout)마다 길이를 재어 피험자별 평균 × TR. " +
            "dynamic FC 문헌에서 dwell time이라 하면 보통 ②를 뜻하므로 둘 다 보고했습니다.",
      options: { fontSize: 13.5, color: INK } },
  ], { x: 0.85, y: yy + 2.28, w: 11.6, h: 1.1, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  s.addNotes("표의 평균은 그 State를 방문한 피험자들만의 평균입니다. " +
    "State 3은 27명 중 9명만 방문했습니다. 전체 27명 기준 시간 점유율은 " +
    "State1 44.2%, State0 31.0%, State2 20.3%, State3 4.5%입니다.");
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(5) Dwell time") });
  s.addText("(5) Dwell time 검정 결과", { placeholder: "title" });
  const yy = qa(s, {
    q: "dwell time이 state별로 다른지 ANOVA + pair별 two-sample t-test (F, p, t, p 보고)",
    a: "두 정의 모두 유의 — 총 점유 F = 6.39,  방문당 체류 F = 10.78",
    color: GREEN,
  });

  s.addText("pair별 two-sample t-test", { x: 0.6, y: yy, w: 12.1, h: 0.3, fontSize: 14,
    bold: true, color: NAVY, isTextBox: true, margin: 0 });
  const rows = [
    ["Pair", "총 점유 t", "p", "방문당 t", "p", "판정"],
    ["State0 vs State1", "−2.256", "0.029 *", "−3.576", "0.00088 ***", "유의"],
    ["State0 vs State2", "+1.145", "0.259 n.s.", "+1.263", "0.213 n.s.", "—"],
    ["State0 vs State3", "+2.224", "0.034 *", "+1.874", "0.070 n.s.", "일부"],
    ["State1 vs State2", "+3.164", "0.0030 **", "+3.764", "0.00054 ***", "유의"],
    ["State1 vs State3", "+3.308", "0.0026 **", "+2.715", "0.011 *", "유의"],
    ["State2 vs State3", "+1.493", "0.147 n.s.", "+1.044", "0.305 n.s.", "—"],
  ];
  tbl(s, rows, { x: 0.6, y: yy + 0.35, w: 12.1, colW: [2.6, 1.9, 2.0, 1.9, 2.0, 1.7],
    rowH: 0.35, fontSize: 11.5 });

  card(s, { x: 0.6, y: yy + 2.95, w: 12.1, h: 1.25, fill: PALE, name: "interp5b" });
  s.addText([
    { text: "해석  ", options: { bold: true, color: NAVY, fontSize: 14 } },
    { text: "유의한 쌍은 모두 State 1이 끼어 있습니다. 즉 State 1만 다른 State들과 체류 시간이 " +
            "확실히 다르고, State 0·2·3 사이에는 유의한 차이가 없습니다. " +
            "\"연결이 약한 상태가 오래 간다\"가 아니라 \"State 1만 유독 오래 간다\"가 정확한 서술입니다.",
      options: { fontSize: 13.5, color: INK } },
  ], { x: 0.85, y: yy + 3.13, w: 11.6, h: 0.95, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });
}

// =============================================================================
pres.addSection({ title: "추가 해석" });
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("추가 해석") });
  s.addText("추가: 이 차이는 '재배치'인가 '수위'인가", { placeholder: "title" });
  const yy = qa(s, {
    q: "(자체 추가) 100개 ROI가 전부 유의하다면, 그 차이의 정체는 무엇인가",
    a: "전역 연결강도 — 전역 크기를 제거하면 유의 ROI 100 → 32, 네트워크 7 → 2",
    color: CORAL,
  });

  figure(s, { file: ADD("fig11_relative_dc.png"), x: 2.17, y: yy, w: 9.0, ratio: 3.10,
    caption: "(좌) 전역 크기 제거 후 네트워크별 상대 DC  (우) State 간 상대 DC 공간 상관" });

  card(s, { x: 0.6, y: yy + 3.41, w: 12.1, h: 1.0, fill: "FDF3F4", name: "interp6" });
  s.addText([
    { text: "결론  ", options: { bold: true, color: CORAL, fontSize: 14 } },
    { text: "State 간 공간 상관 r = 0.72~0.97. 살아남은 네트워크는 Somatomotor와 " +
            "Frontoparietal Control 둘뿐이며, K=2·3·4에서 동일하게 재현됩니다.",
      options: { fontSize: 13.5, color: INK } },
  ], { x: 0.85, y: yy + 3.56, w: 11.6, h: 0.72, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("추가 해석") });
  s.addText("보충: 전역 강도와 상대 DC는 어떻게 구하나", { placeholder: "title" });

  card(s, { x: 0.6, y: 1.3, w: 12.1, h: 0.62, fill: "1E2A52", name: "eq" });
  s.addText([
    { text: "DC 100개", options: { color: "FFFFFF", fontSize: 16, bold: true } },
    { text: "  =  ", options: { color: AMBER, fontSize: 16, bold: true } },
    { text: "전역 강도 (숫자 1개)", options: { color: AMBER, fontSize: 16, bold: true } },
    { text: "  ×  ", options: { color: AMBER, fontSize: 16, bold: true } },
    { text: "상대 DC (숫자 100개)", options: { color: "7FD4C1", fontSize: 16, bold: true } },
  ], { x: 0.85, y: 1.3, w: 11.6, h: 0.62, isTextBox: true, margin: 0, valign: "middle",
       align: "center" });

  card(s, { x: 0.6, y: 2.07, w: 5.9, h: 1.95, fill: "F7F9FC", name: "gs" });
  s.addText("① 전역 강도 = DC 100개의 평균", { x: 0.85, y: 2.2, w: 5.4, h: 0.33,
    fontSize: 14.5, bold: true, color: NAVY, isTextBox: true, margin: 0 });
  s.addText(
    "State 1:  DC 100개 합 522.85 ÷ 100 = 5.228\n" +
    "State 3:  같은 방식으로          = 11.352\n\n" +
    "→ State 3이 전반적으로 2.17배 강함",
    { x: 0.85, y: 2.58, w: 5.4, h: 1.3, fontSize: 12.5, color: INK, fontFace: "Courier New",
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.35 });

  card(s, { x: 6.8, y: 2.07, w: 5.9, h: 1.95, fill: "F7F9FC", name: "rd" });
  s.addText("② 상대 DC = 각 DC ÷ 전역 강도", { x: 7.05, y: 2.2, w: 5.4, h: 0.33,
    fontSize: 14.5, bold: true, color: TEAL, isTextBox: true, margin: 0 });
  s.addText(
    "LH_Vis_8 (State 1):\n" +
    "   9.197 ÷ 5.228 = 1.759\n\n" +
    "→ \"평균보다 76% 높다\" (단위 없는 몫)",
    { x: 7.05, y: 2.58, w: 5.4, h: 1.3, fontSize: 12.5, color: INK, fontFace: "Courier New",
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.35 });

  const rows = [
    ["ROI", "State 1 DC", "상대 DC", "State 3 DC", "상대 DC"],
    ["LH_Vis_8", "9.20", "1.759", "15.39", "1.356"],
    ["LH_Default_PFC_4", "4.42", "0.846", "9.60", "0.846"],
    ["RH_Limbic_OFC_1", "1.02", "0.194", "4.18", "0.368"],
  ];
  tbl(s, rows, { x: 0.6, y: 4.2, w: 12.1, colW: [3.7, 2.1, 2.1, 2.1, 2.1],
    rowH: 0.42, fontSize: 12.5, hi: 2 });

  card(s, { x: 0.6, y: 5.95, w: 12.1, h: 1.0, fill: PALE, name: "why" });
  s.addText([
    { text: "읽는 법  ", options: { bold: true, color: NAVY, fontSize: 14 } },
    { text: "LH_Default_PFC_4는 DC가 4.42 → 9.60으로 두 배 넘게 뛰었지만 상대 DC는 " +
            "0.846으로 동일합니다. 이 영역이 변한 것이 아니라 뇌 전체가 올라가 같이 오른 것입니다.",
      options: { fontSize: 13.5, color: INK } },
  ], { x: 0.85, y: 6.1, w: 11.6, h: 0.75, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  s.addNotes(
    "[왜 쪼개나] DC 100개에는 두 정보가 섞여 있습니다. 전체 수위(이 State가 전반적으로 " +
    "센가)와 패턴(어느 영역이 세고 어느 영역이 약한가). 두 State를 비교할 때 무엇이 " +
    "달라졌는지 가리려면 둘을 분리해야 합니다.\n\n" +
    "[전역 강도] DC 100개의 평균입니다. State 1은 5.228, State 3은 11.352입니다. " +
    "참고로 연결표 4,950칸 전체의 평균(교과서적 의미의 global FC magnitude)은 " +
    "0.176과 0.861로 스케일이 다르지만, 두 값은 상관 1.0으로 함께 움직입니다.\n\n" +
    "[표 해석] LH_Vis_8은 상대 DC가 1.759에서 1.356으로 줄었습니다 — 전체가 오른 것보다 " +
    "덜 올라 몫이 줄었다는 뜻입니다. RH_Limbic_OFC_1은 0.194에서 0.368로 몫이 커졌습니다.\n\n" +
    "[한계 — 질문 나오면] 나누기는 'State 3 = State 1 × 상수'라는 곱셈 관계를 가정합니다. " +
    "그런데 실제 데이터를 적합해 보면 덧셈 모형(y = x + 6.12, 잔차 1.55)이 곱셈 모형" +
    "(y = 2.09x, 잔차 2.15)보다 잘 맞습니다. 또 평균으로 나누면 100개 값의 합이 100으로 " +
    "고정되어 서로 독립이 아니게 됩니다(compositional closure). 따라서 이 보조 분석은 " +
    "빼기 보정·ANCOVA·CLR 변환으로 재검증할 계획입니다. 방향성(전역 크기가 주된 축)은 " +
    "유지될 것으로 보지만 '32개'라는 숫자는 보정 방식에 따라 달라질 수 있습니다.");
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("추가 해석") });
  s.addText("추가: 무작위로 잘라도 같은 결과가 나오는가", { placeholder: "title" });
  const yy = qa(s, {
    q: "(자체 추가) 경계를 무작위로 바꿔도 같은 결과가 나오지 않겠는가",
    a: "7개 지표 중 dwell time 1개만 통과 — FC 구조 지표 5개는 무작위와 구별 불가",
    color: CORAL,
  });

  const rows = [
    ["지표", "관측", "무작위 1,000회", "z", "p"],
    ["세그먼트 내부 동질성", "0.4208", "0.4223 ± 0.0054", "−0.28", "0.61"],
    ["경계 대비", "0.3433", "0.3446 ± 0.0063", "−0.21", "0.42"],
    ["군집 품질 silhouette (K=4)", "0.1022", "0.0866 ± 0.0118", "+1.33", "0.11"],
    ["dwell time 총 점유 η²", "0.2118", "0.1226 ± 0.0424", "+2.10", "0.030"],
    ["dwell time 방문당 체류 η²", "0.3188", "0.1513 ± 0.0513", "+3.27", "0.003"],
  ];
  tbl(s, rows, { x: 0.6, y: yy, w: 12.1, colW: [4.3, 1.9, 2.9, 1.5, 1.5], rowH: 0.37, fontSize: 12, hi: 5 });

  card(s, { x: 0.6, y: yy + 2.4, w: 12.1, h: 1.45, fill: "FFF7E8", name: "interp7" });
  s.addText([
    { text: "이것이 dwell time 결과에 주는 의미  ", options: { bold: true, color: AMBER, fontSize: 14 } },
    { text: "무작위로 잘라도 dwell time η²가 평균 0.15 나옵니다. 따라서 (5)번의 " +
            "ANOVA p = 6.4e-06 자체는 증거가 되지 못하고, 무작위 대비 초과분(0.32 vs 0.15)만이 " +
            "증거입니다. 다행히 그 초과분은 Bonferroni 기준(0.05÷7 = 0.0071)을 통과했습니다.",
      options: { fontSize: 13.5, color: INK } },
  ], { x: 0.85, y: yy + 2.58, w: 11.6, h: 1.15, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });
}

// =============================================================================
pres.addSection({ title: "Q&A" });
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("Q&A") });
  s.addText("예상 질문 즉답 (1)", { placeholder: "title" });

  const qas = [
    { q: "왜 하필 상위 10%인가?", a: "관행적 선택입니다. 5%로 바꾼 민감도 분석 옵션(--top-pct)은 구현해 두었으나 아직 실행하지 않았습니다. 다음 주에 확인하겠습니다.", c: AMBER },
    { q: "CM 평균을 먼저 내고 thresholding 했는가, 반대인가?", a: "CM을 먼저 평균한 뒤 thresholding 했습니다. 순서를 바꾸면 값이 1.2~1.4 정도 커집니다(thresholding이 비선형). 평균을 먼저 내는 쪽이 세그먼트 잡음에 강합니다.", c: NAVY },
    { q: "(1)번 표의 DC와 (4)번 표의 DC가 왜 다른가?", a: "(1)은 State 전체 CM을 한 번에 평균한 값, (4)는 피험자별로 먼저 묶은 뒤 평균한 값입니다. 피험자마다 세그먼트 수가 8~14개로 달라 값이 어긋납니다.", c: NAVY },
  ];
  let y = 1.4;
  qas.forEach((o, i) => {
    card(s, { x: 0.6, y, w: 12.1, h: 1.72, fill: PALE, name: `qa1-${i}` });
    s.addText([
      { text: "Q. ", options: { bold: true, color: o.c, fontSize: 15 } },
      { text: o.q, options: { bold: true, color: o.c, fontSize: 15 } },
    ], { x: 0.9, y: y + 0.16, w: 11.5, h: 0.38, isTextBox: true, margin: 0 });
    s.addText([
      { text: "A. ", options: { bold: true, color: INK, fontSize: 13 } },
      { text: o.a, options: { fontSize: 13, color: INK } },
    ], { x: 0.9, y: y + 0.6, w: 11.5, h: 0.95, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });
    y += 1.9;
  });
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("Q&A") });
  s.addText("예상 질문 즉답 (2)", { placeholder: "title" });

  const qas = [
    { q: "100개 ROI가 전부 유의하다는 게 좋은 결과인가?", a: "아닙니다. '전부 다르다'는 것은 '어느 영역이 특별한지 가려내지 못했다'는 뜻이기도 합니다. 그래서 전역 크기를 제거한 상대 DC 분석을 추가했고, 그 결과 32개로 줄었습니다.", c: CORAL },
    { q: "State 3은 피험자 9명뿐인데 신뢰할 수 있나?", a: "검정력이 낮습니다. 세그먼트 16개 / 피험자 9명이고 18명은 한 번도 방문하지 않았습니다. State 3 관련 결론은 탐색적으로만 해석해야 합니다.", c: AMBER },
    { q: "dwell time 점유율의 합이 100%가 되는가?", a: "표의 퍼센트는 그 State를 방문한 피험자들만의 평균이라 합이 131%입니다. 전체 27명 기준 실제 점유율은 44.2 / 31.0 / 20.3 / 4.5%입니다.", c: AMBER },
  ];
  let y = 1.4;
  qas.forEach((o, i) => {
    card(s, { x: 0.6, y, w: 12.1, h: 1.72, fill: PALE, name: `qa2-${i}` });
    s.addText([
      { text: "Q. ", options: { bold: true, color: o.c, fontSize: 15 } },
      { text: o.q, options: { bold: true, color: o.c, fontSize: 15 } },
    ], { x: 0.9, y: y + 0.16, w: 11.5, h: 0.38, isTextBox: true, margin: 0 });
    s.addText([
      { text: "A. ", options: { bold: true, color: INK, fontSize: 13 } },
      { text: o.a, options: { fontSize: 13, color: INK } },
    ], { x: 0.9, y: y + 0.6, w: 11.5, h: 0.95, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });
    y += 1.9;
  });
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("Q&A") });
  s.addText("예상 질문 즉답 (3)", { placeholder: "title" });

  const qas = [
    { q: "관측 단위가 (subject × State)인데 독립성 가정은?", a: "엄밀히는 위배됩니다. 한 피험자가 여러 State에 기여합니다. 보조로 비모수 Kruskal-Wallis와 Welch t-test를 함께 보고했고, 결론은 동일했습니다.", c: NAVY },
    { q: "머리 움직임 때문일 가능성은?", a: "아직 배제하지 못했습니다. 전역 연결강도는 머리 움직임과 각성도에 민감합니다. 다음 단계로 피험자별 FD를 산출해 State별로 비교하려 합니다.", c: CORAL },
    { q: "dwell time의 시간 해상도 하한은?", a: "세그먼테이션의 최소 길이 제약 때문에 약 22.3초(31 TP)입니다. 그보다 짧은 상태 전환은 원리적으로 관측되지 않습니다.", c: NAVY },
  ];
  let y = 1.4;
  qas.forEach((o, i) => {
    card(s, { x: 0.6, y, w: 12.1, h: 1.72, fill: PALE, name: `qa3-${i}` });
    s.addText([
      { text: "Q. ", options: { bold: true, color: o.c, fontSize: 15 } },
      { text: o.q, options: { bold: true, color: o.c, fontSize: 15 } },
    ], { x: 0.9, y: y + 0.16, w: 11.5, h: 0.38, isTextBox: true, margin: 0 });
    s.addText([
      { text: "A. ", options: { bold: true, color: INK, fontSize: 13 } },
      { text: o.a, options: { fontSize: 13, color: INK } },
    ], { x: 0.9, y: y + 0.6, w: 11.5, h: 0.95, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });
    y += 1.9;
  });
}

// =============================================================================
pres.addSection({ title: "정리" });
{
  const s = pres.addSlide({ masterName: "CLOSING", ...S("정리") });
  s.addText("정리", { placeholder: "title" });

  s.addText("요청 분석 결과", { x: 0.9, y: 1.75, w: 5.7, h: 0.33, fontSize: 15, bold: true,
    color: "97A3C9", isTextBox: true, margin: 0 });
  const done = [
    "(1) DC 정의 — State 1 < 0 < 2 < 3 (5.23 → 11.35)",
    "(2) 표면 시각화 — ENIGMA TOOLBOX 완료",
    "(3) 7-Network — 모든 State에서 Vis 최고 / Limbic 최저",
    "(4) ANOVA F(3,71) = 218.6 · 6/6 pair 유의",
    "(5) Dwell time — 방문당 F = 10.78, State 1만 유의하게 길다",
  ];
  s.addText(done.map((t, i) => ({ text: t, options: { bullet: true,
    breakLine: i !== done.length - 1, color: "FFFFFF" } })),
    { x: 0.9, y: 2.2, w: 5.7, h: 2.6, fontSize: 13.5, isTextBox: true,
      paraSpaceAfter: 8, lineSpacingMultiple: 1.2 });

  card(s, { x: 0.9, y: 5.05, w: 5.7, h: 1.5, fill: "1E2A52", name: "core" });
  s.addText([
    { text: "핵심 해석\n", options: { bold: true, color: AMBER, fontSize: 14 } },
    { text: "4개 State는 서로 다른 종류가 아니라, 전역 연결강도라는 하나의 축 위에 놓인 " +
            "4개의 눈금이다.", options: { color: "CFD7EC", fontSize: 13 } },
  ], { x: 1.15, y: 5.25, w: 5.2, h: 1.2, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  s.addText("다음 단계", { x: 7.0, y: 1.75, w: 5.4, h: 0.33, fontSize: 15, bold: true,
    color: "97A3C9", isTextBox: true, margin: 0 });
  const next = [
    { n: 1, t: "민감도 분석", d: "상위 5% / 15%로 바꿔 DC 결론이 유지되는지 확인" },
    { n: 2, t: "움직임 교란 통제", d: "피험자별 FD 산출 → State별 FD 비교" },
    { n: 3, t: "과분할 여부 판별", d: "경계 개수를 바꿔가며 dwell time 초과분 추적" },
    { n: 4, t: "K=2·3 dwell time", d: "현재 K=4만 수행 — 나머지도 동일 분석 적용" },
  ];
  let y = 2.2;
  next.forEach((o) => {
    s.addShape(pres.ShapeType.ellipse, { x: 7.0, y: y + 0.02, w: 0.42, h: 0.42,
      fill: { color: CORAL }, line: { color: CORAL, width: 0 }, objectName: `nc-${o.n}` });
    s.addText(String(o.n), { x: 7.0, y: y + 0.02, w: 0.42, h: 0.42, align: "center",
      valign: "middle", fontSize: 14, bold: true, color: "FFFFFF", isTextBox: true, margin: 0 });
    s.addText(o.t, { x: 7.6, y, w: 4.8, h: 0.32, fontSize: 14, bold: true, color: "FFFFFF",
      isTextBox: true, margin: 0 });
    s.addText(o.d, { x: 7.6, y: y + 0.32, w: 4.8, h: 0.5, fontSize: 12, color: "A9B4D4",
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.15 });
    y += 1.08;
  });

  s.addNotes("요청 다섯 항목 모두 완료했습니다. 다음 단계로는 민감도 분석과 움직임 교란 통제를 " +
    "먼저 진행하려 합니다.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("saved:", OUT);
})();
