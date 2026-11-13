// V4 연구결과 발표 덱 생성
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/Users/mac/.claude/skills/synced/a3d420dd-7bca-4cf8-b3b3-ed5e5de273b8_0001a5c5-5808-4cc0-9bb9-b3820e9fcf4b/pptx/scripts/apply_theme.js");

const ROOT = "/Users/mac/Desktop/code/MTAD-GAT";
const V4 = (f) => path.join(ROOT, "visualization_ver4", f);
const ADD = (f) => path.join(ROOT, "visualization_ver4_add", f);
const V5 = (f) => path.join(ROOT, "visualization_ver5", f);
const OUT = path.join(ROOT, "V4_연구결과_발표.pptx");

const THEME = {
  name: "BrainState",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "131A33",   // 딥 미드나잇 (타이틀/결론 배경)
    lt1: "FFFFFF",
    dk2: "2F3C7E",   // 네이비 (제목 글자)
    lt2: "EDF1F8",   // 페일 블루그레이 (카드 배경)
    accent1: "E04B5A", // 코랄 (강조 — 뇌 그림의 빨강과 호응)
    accent2: "1C7293", // 틸
    accent3: "5A6BA8",
    accent4: "97A3C9",
    accent5: "E8A33D", // 앰버 (주의)
    accent6: "2E8B6F", // 그린 (통과)
    hlink: "1C7293",
    folHlink: "5A6BA8",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = "MTAD-GAT Brain State 연구";
pres.title = "V4 연구결과 보고";

const C = pres.SchemeColor;

// ── 레이아웃 ───────────────────────────────────────────────────────────────
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "eyebrow", type: "body", x: 0.9, y: 1.95, w: 11.5, h: 0.4,
      fontSize: 15, color: C.accent4, charSpacing: 2 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.9, y: 2.45, w: 11.5, h: 1.5,
      fontSize: 42, bold: true, color: C.background1, align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.9, y: 4.05, w: 11.5, h: 0.9,
      fontSize: 17, color: C.accent4 }, text: "" } },
    { placeholder: { options: { name: "meta", type: "body", x: 0.9, y: 6.25, w: 11.5, h: 0.5,
      fontSize: 13, color: C.accent3 }, text: "" } },
  ],
});

pres.defineSlideMaster({
  title: "SECTION",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "num", type: "body", x: 0.9, y: 2.5, w: 1.6, h: 1.2,
      fontSize: 64, bold: true, color: C.accent1 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 2.5, y: 2.6, w: 9.9, h: 1.0,
      fontSize: 38, bold: true, color: C.background1, align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 2.55, y: 3.65, w: 9.9, h: 0.8,
      fontSize: 16, color: C.accent4 }, text: "" } },
  ],
});

const contentObjects = [
  { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.42, w: 12.1, h: 0.85,
    fontSize: 36, bold: true, color: C.text2, align: "left", valign: "middle" }, text: "" } },
];

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  objects: contentObjects,
  slideNumber: { x: 12.6, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: "97A3C9", align: "right" },
});

pres.defineSlideMaster({
  title: "CLOSING",
  background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.9, y: 0.75, w: 11.5, h: 0.9,
      fontSize: 38, bold: true, color: C.background1, align: "left" }, text: "" } },
  ],
});

// ── 헬퍼 ───────────────────────────────────────────────────────────────────
const NAVY = "2F3C7E", CORAL = "E04B5A", TEAL = "1C7293", AMBER = "E8A33D",
      GREEN = "2E8B6F", INK = "131A33", MUTED = "5A6BA8", PALE = "EDF1F8";

/** 둥근 카드 + 제목 + 본문 */
function card(slide, { x, y, w, h, fill, name }) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, fill: { color: fill || PALE }, rectRadius: 0.08,
    line: { color: fill || PALE, width: 0 }, objectName: name,
  });
}

/** 번호 원 */
function numCircle(slide, { x, y, d, n, color }) {
  slide.addShape(pres.ShapeType.ellipse, {
    x, y, w: d, h: d, fill: { color: color }, line: { color: color, width: 0 },
    objectName: `circle-${n}`,
  });
  slide.addText(String(n), {
    x, y, w: d, h: d, align: "center", valign: "middle",
    fontSize: 15, bold: true, color: "FFFFFF", isTextBox: true, margin: 0,
  });
}

/** 큰 수치 콜아웃 카드 */
function statCard(slide, { x, y, w, h, value, unit, label, note, color }) {
  card(slide, { x, y, w, h, fill: PALE, name: `stat-${label}` });
  slide.addText(
    [{ text: value, options: { fontSize: 40, bold: true, color: color } },
     { text: unit || "", options: { fontSize: 17, bold: true, color: color } }],
    { x: x + 0.3, y: y + 0.25, w: w - 0.6, h: 0.75, align: "left", valign: "middle",
      isTextBox: true, margin: 0 });
  slide.addText(label, { x: x + 0.3, y: y + 1.02, w: w - 0.6, h: 0.32,
    fontSize: 14, bold: true, color: INK, isTextBox: true, margin: 0 });
  if (note) {
    slide.addText(note, { x: x + 0.3, y: y + 1.36, w: w - 0.6, h: Math.max(0.3, h - 1.44),
      fontSize: 11.5, color: MUTED, isTextBox: true, margin: 0, lineSpacingMultiple: 1.15 });
  }
}

/** 그림 + 캡션 */
function figure(slide, { file, x, y, w, ratio, caption }) {
  const h = w / ratio;
  slide.addImage({ path: file, x, y, w, h, objectName: path.basename(file) });
  if (caption) {
    slide.addText(caption, { x, y: y + h + 0.1, w, h: 0.3, fontSize: 11, italic: true,
      color: MUTED, isTextBox: true, margin: 0 });
  }
  return y + h;
}

/** 불릿 목록 */
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
    { x, y, w, h, fontSize: fontSize || 15, color: INK, isTextBox: true,
      paraSpaceAfter: 9, lineSpacingMultiple: 1.2 });
}

const S = (t) => ({ sectionTitle: t });

// =============================================================================
// 1. 표지
// =============================================================================
pres.addSection({ title: "표지" });
{
  const s = pres.addSlide({ masterName: "TITLE_DARK", ...S("표지") });
  s.addText("V4 파이프라인 연구결과 보고", { placeholder: "eyebrow" });
  s.addText("MTAD-GAT 기반 Brain State 정의와 해석", { placeholder: "title" });
  s.addText("per-cluster BrainLM · Degree Centrality 해석 · 무작위 대조군 검정",
    { placeholder: "body" });
  s.addText("HCP rs-fMRI · Schaefer-100 · 피험자 27명 · 세그먼트 308개",
    { placeholder: "meta" });
  s.addNotes(
    "V4 파이프라인 결과를 보고드립니다. 크게 세 부분입니다. " +
    "첫째 파이프라인 설계와 BrainLM 학습 결과, 둘째 Degree Centrality 기반 해석 분석, " +
    "셋째로 이 결과들이 실제로 의미가 있는지 검정한 무작위 대조군 실험입니다.");
}

// =============================================================================
// 2. 오늘의 결론 (executive summary)
// =============================================================================
pres.addSection({ title: "요약" });
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("요약") });
  s.addText("오늘 보고드릴 세 가지", { placeholder: "title" });

  const rows = [
    { n: 1, c: TEAL, t: "파이프라인은 설계대로 동작했다",
      d: "세그먼트 308개에서 State별 BrainLM 3개가 과적합 없이 수렴. State 간 DC 차이는 매우 크다 (η² = 0.90)." },
    { n: 2, c: NAVY, t: "그런데 State를 가르는 축은 '전역 연결강도' 하나였다",
      d: "전역 크기를 제거하면 유의 ROI가 100개 → 32개로 감소. K=2·3·4 모두 같은 축을 다른 위치에서 자른 결과." },
    { n: 3, c: CORAL, t: "무작위 분할 대조군을 통과하지 못했다",
      d: "FC 구조 지표 5개 전부 무작위와 구별 불가. dwell time 1개만 통과 (p = 0.003)." },
  ];
  let y = 1.55;
  rows.forEach((r) => {
    card(s, { x: 0.6, y, w: 12.1, h: 1.52, fill: PALE, name: `row-${r.n}` });
    numCircle(s, { x: 0.95, y: y + 0.44, d: 0.62, n: r.n, color: r.c });
    s.addText(r.t, { x: 1.85, y: y + 0.22, w: 10.5, h: 0.45, fontSize: 19, bold: true,
      color: r.c, isTextBox: true, margin: 0, valign: "middle" });
    s.addText(r.d, { x: 1.85, y: y + 0.74, w: 10.5, h: 0.6, fontSize: 13.5, color: INK,
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });
    y += 1.72;
  });
  s.addNotes(
    "결론부터 말씀드리면 세 가지입니다. 파이프라인 자체는 동작했고, " +
    "State 간 차이도 통계적으로 매우 크게 나옵니다. " +
    "다만 그 차이의 정체를 파고들어 보니 전역 연결강도 한 축이었고, " +
    "무작위로 잘라도 비슷한 결과가 나오는지 대조군을 돌려봤더니 대부분 통과하지 못했습니다.");
}

// =============================================================================
// 섹션 1
// =============================================================================
pres.addSection({ title: "1. 파이프라인" });
{
  const s = pres.addSlide({ masterName: "SECTION", ...S("1. 파이프라인") });
  s.addText("01", { placeholder: "num" });
  s.addText("파이프라인 설계와 학습 결과", { placeholder: "title" });
  s.addText("MTAD-GAT 변화점 → 세그먼트 → CM 클러스터링 → State별 BrainLM",
    { placeholder: "body" });
}

// 파이프라인 구조
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("1. 파이프라인") });
  s.addText("V4 파이프라인 5단계", { placeholder: "title" });

  const steps = [
    { t: "MTAD-GAT", d: "GRU 은닉상태 변화량으로\n상태 전환 경계 탐지", c: NAVY },
    { t: "세그먼트", d: "27명 × 평균 11.4개\n= 308개 세그먼트", c: NAVY },
    { t: "CM + K-means", d: "Pearson + Fisher-Z\n4,950차원 → State 레이블", c: TEAL },
    { t: "BrainLM", d: "State별 독립 학습\n입력 = 원시 BOLD 시계열", c: TEAL },
    { t: "해석 분석", d: "Degree Centrality\n+ dwell time", c: CORAL },
  ];
  const w = 2.22, gap = 0.25;
  let x = 0.6;
  steps.forEach((st, i) => {
    card(s, { x, y: 1.75, w, h: 2.5, fill: PALE, name: `step-${i}` });
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.9, y: 1.98, w: 0.46, h: 0.46,
      fill: { color: st.c }, line: { color: st.c, width: 0 }, objectName: `stepnum-${i}` });
    s.addText(String(i + 1), { x: x + 0.9, y: 1.98, w: 0.46, h: 0.46, align: "center",
      valign: "middle", fontSize: 13, bold: true, color: "FFFFFF", isTextBox: true, margin: 0 });
    s.addText(st.t, { x: x + 0.15, y: 2.56, w: w - 0.3, h: 0.4, align: "center",
      fontSize: 15.5, bold: true, color: st.c, isTextBox: true, margin: 0 });
    s.addText(st.d, { x: x + 0.15, y: 3.0, w: w - 0.3, h: 1.1, align: "center",
      fontSize: 12, color: INK, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });
    if (i < steps.length - 1) {
      s.addText("›", { x: x + w, y: 2.75, w: gap, h: 0.4, align: "center",
        fontSize: 20, bold: true, color: "97A3C9", isTextBox: true, margin: 0 });
    }
    x += w + gap;
  });

  card(s, { x: 0.6, y: 4.62, w: 12.1, h: 1.25, fill: "FDF3F4", name: "keypoint" });
  s.addText([
    { text: "핵심 설계 ", options: { bold: true, color: CORAL, fontSize: 14 } },
    { text: "CM은 State 레이블을 다는 데만 쓰고, 표현학습에는 시간 순서가 보존된 원시 BOLD 시계열을 넣는다. " +
            "V2(CM 시퀀스 입력) 대비 시간 동역학 정보를 살리기 위한 변경이다.",
      options: { fontSize: 14, color: INK } },
  ], { x: 0.9, y: 4.82, w: 11.5, h: 0.9, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  s.addNotes("CM은 레이블링 전용이고 BrainLM 입력은 raw timeseries라는 점이 V2와의 핵심 차이입니다.");
}

// 버전 비교 표
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("1. 파이프라인") });
  s.addText("버전별 설계 비교", { placeholder: "title" });

  const rows = [
    ["항목", "V2", "V3", "V4 (현재)"],
    ["BrainLM 입력", "CM 시퀀스 (4950-dim)", "Raw TS (공유 모델)", "Raw TS (클러스터별)"],
    ["모델 구조", "클러스터별 독립", "단일 공유", "클러스터별 독립"],
    ["학습 예제", "CM 슬라이딩 윈도우", "4개 세그먼트 concat", "각 세그먼트 = 1 예제"],
    ["총 예제 수", "~288", "~83", "308"],
    ["오프-대각 코사인", "~ -0.016", "~0.97", "-0.006"],
  ];
  s.addTable(
    rows.map((r, ri) => r.map((cell, ci) => ({
      text: cell,
      options: {
        bold: ri === 0 || (ri > 0 && ci === 0) || (ri > 0 && ci === 3),
        color: ri === 0 ? "FFFFFF" : (ci === 3 ? NAVY : INK),
        fill: ri === 0 ? { color: NAVY } : (ci === 3 ? { color: "E3E9F6" } : { color: "FFFFFF" }),
        align: ci === 0 ? "left" : "center",
      },
    }))),
    { x: 0.6, y: 1.65, w: 12.1, colW: [2.7, 3.2, 3.1, 3.1], rowH: 0.46,
      fontSize: 13, valign: "middle", border: { type: "solid", color: "D5DCEC", pt: 1 },
      margin: 0.08 });

  card(s, { x: 0.6, y: 4.75, w: 12.1, h: 1.35, fill: "FFF7E8", name: "caution" });
  s.addText([
    { text: "주의  ", options: { bold: true, color: AMBER, fontSize: 14 } },
    { text: "맨 아래 '오프-대각 코사인'은 뒤에서 다시 다룹니다. 서로 다른 모델이 만든 " +
            "잠재벡터를 비교한 값이라, 이 수치만으로는 State 분리의 증거가 되지 못합니다.",
      options: { fontSize: 14, color: INK } },
  ], { x: 0.9, y: 4.95, w: 11.5, h: 0.95, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  s.addNotes("V3는 단일 공유 모델이어서 코사인이 0.97로 분리에 실패했습니다. " +
    "V4는 -0.006인데, 이 숫자의 해석은 15번 슬라이드에서 다시 말씀드립니다.");
}

// BrainLM 학습 결과
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("1. 파이프라인") });
  s.addText("State별 BrainLM 학습 결과", { placeholder: "title" });
  figure(s, { file: V4("fig1_training_curves.png"), x: 0.6, y: 1.6, w: 6.5, ratio: 1.41,
    caption: "State별 Train / Val Loss 곡선" });

  const items = [
    { text: "3개 State 모두 과적합 징후 없이 수렴", bold: true },
    "최적 검증 손실: 98.83 / 101.15 / 115.67",
    "마스킹 비율 15%, d_model 256, encoder 4층 · 8헤드",
    "피험자 단위 train/val/test 분할로 데이터 누수 차단",
  ];
  bullets(s, { x: 7.5, y: 1.75, w: 5.2, h: 2.3, items, fontSize: 14.5 });

  card(s, { x: 7.5, y: 4.3, w: 5.2, h: 1.7, fill: "FFF7E8", name: "skip" });
  s.addText([
    { text: "State 3은 학습에서 제외\n", options: { bold: true, color: AMBER, fontSize: 14 } },
    { text: "세그먼트 16개뿐이라 검증 세트를 구성할 수 없었다. 이후 해석 분석에는 포함하되 " +
            "검정력이 낮다는 점을 감안해야 한다.", options: { fontSize: 12.5, color: INK } },
  ], { x: 7.75, y: 4.5, w: 4.7, h: 1.3, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });

  s.addNotes("세 모델 모두 안정적으로 수렴했습니다. State 3은 표본이 16개뿐이라 BrainLM 학습에서는 빠졌습니다.");
}

// =============================================================================
// 섹션 2
// =============================================================================
pres.addSection({ title: "2. 해석 분석" });
{
  const s = pres.addSlide({ masterName: "SECTION", ...S("2. 해석 분석") });
  s.addText("02", { placeholder: "num" });
  s.addText("Brain State는 무엇이 다른가", { placeholder: "title" });
  s.addText("Degree Centrality · Yeo 7-Network · dwell time", { placeholder: "body" });
}

// DC 표면 분포
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("2. 해석 분석") });
  s.addText("State별 Degree Centrality 분포", { placeholder: "title" });
  figure(s, { file: ADD("fig1_surface_dc_by_state.png"), x: 0.6, y: 1.55, w: 6.3, ratio: 1.27,
    caption: "State별 DC 피질 표면 분포 (공통 color range)" });

  s.addText("DC 정의", { x: 7.4, y: 1.6, w: 5.3, h: 0.35, fontSize: 15, bold: true,
    color: NAVY, isTextBox: true, margin: 0 });
  bullets(s, { x: 7.4, y: 2.0, w: 5.3, h: 1.5, fontSize: 13.5, items: [
    "100×100 Fisher-Z 행렬의 각 행에서 상위 10%만 유지",
    "유지된 값을 행 방향으로 합산 → 100×1 벡터",
  ]});

  const order = [
    { s: "State 1", v: "5.23", c: "97A3C9" },
    { s: "State 0", v: "6.96", c: "5A6BA8" },
    { s: "State 2", v: "8.61", c: TEAL },
    { s: "State 3", v: "11.35", c: CORAL },
  ];
  s.addText("DC 크기 순서", { x: 7.4, y: 3.6, w: 5.3, h: 0.35, fontSize: 15, bold: true,
    color: NAVY, isTextBox: true, margin: 0 });
  let yy = 4.03;
  order.forEach((o, i) => {
    card(s, { x: 7.4, y: yy, w: 5.3, h: 0.46, fill: i === 3 ? "FDF3F4" : PALE, name: `dc-${i}` });
    s.addText(o.s, { x: 7.6, y: yy, w: 2.2, h: 0.46, fontSize: 13.5, bold: true, color: INK,
      isTextBox: true, margin: 0, valign: "middle" });
    s.addText(o.v, { x: 10.0, y: yy, w: 2.5, h: 0.46, fontSize: 14, bold: true, color: o.c,
      align: "right", isTextBox: true, margin: 0, valign: "middle" });
    yy += 0.54;
  });

  s.addNotes("DC가 가장 높은 영역은 네 State 모두 Visual network이고, 가장 낮은 곳은 Limbic입니다. " +
    "즉 hub의 위치 자체는 State가 바뀌어도 거의 그대로입니다.");
}

// ANOVA 결과
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("2. 해석 분석") });
  s.addText("State 간 차이는 통계적으로 매우 크다", { placeholder: "title" });

  const stats9 = [
    { v: "F = 218.6", d: "Global DC one-way ANOVA · F(3, 71), p = 8.97e-36", c: NAVY },
    { v: "η² = 0.90", d: "전체 분산의 90%를 State가 설명", c: TEAL },
    { v: "6 / 6 pair", d: "모든 State 쌍에서 유의 (|t| = 8.5 ~ 23.6)", c: CORAL },
  ];
  let x9 = 0.6;
  stats9.forEach((o, i) => {
    card(s, { x: x9, y: 1.38, w: 3.87, h: 0.95, fill: PALE, name: `s9-${i}` });
    s.addText(o.v, { x: x9 + 0.25, y: 1.46, w: 3.37, h: 0.42, fontSize: 20, bold: true,
      color: o.c, isTextBox: true, margin: 0, valign: "middle" });
    s.addText(o.d, { x: x9 + 0.25, y: 1.88, w: 3.37, h: 0.38, fontSize: 11.5, color: MUTED,
      isTextBox: true, margin: 0 });
    x9 += 4.12;
  });

  figure(s, { file: ADD("fig7_anova_boxplots.png"), x: 2.17, y: 2.55, w: 9.0, ratio: 2.0,
    caption: "Global DC 및 네트워크별 DC의 State 간 분포 (점 = subject × State 관측)" });

  s.addNotes("관측 단위는 subject × State 쌍이고 N = 75입니다. " +
    "네트워크 수준에서도 7개 전부, ROI 수준에서는 100개 전부가 FDR 보정 후 유의했습니다.");
}

// 핵심 해석: 전역강도
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("2. 해석 분석") });
  s.addText("그런데 차이의 대부분은 '전역 연결강도'였다", { placeholder: "title" });

  figure(s, { file: ADD("fig11_relative_dc.png"), x: 1.37, y: 1.5, w: 10.6, ratio: 3.10,
    caption: "(좌) 전역 크기 제거 후 네트워크별 상대 DC  (우) State 간 상대 DC 공간 상관" });

  const cards = [
    { v: "0.72 ~ 0.97", l: "State 간 공간 상관", d: "hub 배치는 State가 바뀌어도 거의 동일", c: NAVY },
    { v: "100 → 32", l: "유의 ROI 수 (FDR)", d: "전역 크기 제거 시 3분의 1로 감소", c: CORAL },
    { v: "2 / 7", l: "남은 유의 네트워크", d: "Somatomotor, Frontoparietal Control", c: TEAL },
  ];
  let x = 0.6;
  cards.forEach((c0, i) => {
    card(s, { x, y: 5.45, w: 3.87, h: 1.5, fill: PALE, name: `rel-${i}` });
    s.addText(c0.v, { x: x + 0.25, y: 5.55, w: 3.37, h: 0.45, fontSize: 23, bold: true,
      color: c0.c, isTextBox: true, margin: 0, valign: "middle" });
    s.addText(c0.l, { x: x + 0.25, y: 6.03, w: 3.37, h: 0.28, fontSize: 13, bold: true,
      color: INK, isTextBox: true, margin: 0 });
    s.addText(c0.d, { x: x + 0.25, y: 6.33, w: 3.37, h: 0.5, fontSize: 11.5, color: MUTED,
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.15 });
    x += 4.12;
  });

  s.addNotes("각 관측의 DC를 자기 평균으로 나눠 전역 크기를 제거하면, 유의 ROI가 100개에서 32개로 줄고 " +
    "7개 네트워크 중 2개만 남습니다. 즉 State를 가르는 주된 축은 hub의 재배치가 아니라 " +
    "전반적인 연결강도의 고저입니다.");
}

// dwell time
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("2. 해석 분석") });
  s.addText("State별 체류 시간 (dwell time)", { placeholder: "title" });

  figure(s, { file: ADD("fig13_dwell_time.png"), x: 0.6, y: 1.5, w: 7.9, ratio: 2.50,
    caption: "(좌) 총 점유 시간  (우) 방문당 평균 체류 시간 · TR = 0.72초" });

  const rows = [
    ["State", "총 점유 [초]", "방문당 [초]"],
    ["State 0", "301.2 ± 235.8", "116.1 ± 72.4"],
    ["State 1", "491.3 ± 327.1", "340.8 ± 298.4"],
    ["State 2", "225.6 ± 202.7", "90.7 ± 60.8"],
    ["State 3", "115.8 ± 128.4", "66.3 ± 53.0"],
  ];
  s.addTable(
    rows.map((r, ri) => r.map((cell, ci) => ({
      text: cell,
      options: {
        bold: ri === 0 || ri === 2,
        color: ri === 0 ? "FFFFFF" : (ri === 2 ? CORAL : INK),
        fill: ri === 0 ? { color: NAVY } : (ri === 2 ? { color: "FDF3F4" } : { color: "FFFFFF" }),
        align: ci === 0 ? "left" : "right",
      },
    }))),
    { x: 8.8, y: 1.55, w: 3.9, colW: [1.25, 1.4, 1.25], rowH: 0.42, fontSize: 12,
      valign: "middle", border: { type: "solid", color: "D5DCEC", pt: 1 }, margin: 0.06 });

  bullets(s, { x: 8.8, y: 4.0, w: 3.9, h: 2.0, fontSize: 13, items: [
    { text: "DC가 가장 낮은 State 1이 가장 오래 유지", bold: true, color: CORAL },
    "방문당 체류: F(3,71) = 10.78, p = 6.4e-06",
    "총 점유: F = 6.39, p = 6.8e-04",
  ]});

  s.addNotes("연결이 약한 상태에 한 번 들어가면 평균 341초 머물고, 연결이 강한 상태는 66초 만에 빠져나옵니다. " +
    "다만 이 ANOVA 결과 자체의 해석은 뒤의 대조군 슬라이드에서 중요하게 바뀝니다.");
}

// K 민감도
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("2. 해석 분석") });
  s.addText("K를 2·3·4로 바꿔도 결론은 같다", { placeholder: "title" });

  const rows = [
    ["", "K = 2", "K = 3", "K = 4"],
    ["Global DC ANOVA", "F = 118.3", "F = 214.6", "F = 218.6"],
    ["절대 DC 유의 ROI (FDR)", "100 / 100", "99 / 100", "100 / 100"],
    ["상대 DC 유의 ROI (FDR)", "23", "21", "32"],
    ["상대 DC 유의 네트워크", "SomMot, Cont", "SomMot, Cont", "SomMot, Cont"],
    ["silhouette", "0.227", "0.170", "0.094"],
  ];
  s.addTable(
    rows.map((r, ri) => r.map((cell, ci) => ({
      text: cell,
      options: {
        bold: ri === 0 || ci === 0 || ri === 4,
        color: ri === 0 ? "FFFFFF" : (ri === 4 ? TEAL : INK),
        fill: ri === 0 ? { color: NAVY } : (ri === 4 ? { color: "E6F2F0" } : { color: "FFFFFF" }),
        align: ci === 0 ? "left" : "center",
      },
    }))),
    { x: 0.6, y: 1.62, w: 12.1, colW: [4.0, 2.7, 2.7, 2.7], rowH: 0.44, fontSize: 13,
      valign: "middle", border: { type: "solid", color: "D5DCEC", pt: 1 }, margin: 0.08 });

  card(s, { x: 0.6, y: 4.5, w: 5.9, h: 1.75, fill: PALE, name: "ari" });
  s.addText("레이블 중첩 구조", { x: 0.85, y: 4.65, w: 5.4, h: 0.32, fontSize: 14.5,
    bold: true, color: NAVY, isTextBox: true, margin: 0 });
  s.addText(
    "K=3 → K=2 : ARI 0.901 (308개 중 1개만 어긋남)\n" +
    "K=4 → K=3 : 최저·최고 DC State가 100% 보존, 중간만 분할",
    { x: 0.85, y: 5.0, w: 5.4, h: 1.0, fontSize: 13, color: INK, isTextBox: true,
      margin: 0, lineSpacingMultiple: 1.3 });

  card(s, { x: 6.8, y: 4.5, w: 5.9, h: 1.75, fill: "FDF3F4", name: "kconc" });
  s.addText("해석", { x: 7.05, y: 4.65, w: 5.4, h: 0.32, fontSize: 14.5, bold: true,
    color: CORAL, isTextBox: true, margin: 0 });
  s.addText(
    "K는 '상태가 몇 종류인가'를 바꾸는 것이 아니라, 연속적인 하나의 축을 " +
    "몇 토막으로 자르는가를 정할 뿐이다. silhouette이 K=2에서 최대이고 " +
    "단조 감소하는 것도 같은 해석을 뒷받침한다.",
    { x: 7.05, y: 5.0, w: 5.4, h: 1.1, fontSize: 12.5, color: INK, isTextBox: true,
      margin: 0, lineSpacingMultiple: 1.25 });

  s.addNotes("K를 바꿔가며 세 번 돌린 결과가 전부 같습니다. 교차표를 보면 중첩 구조가 명확합니다.");
}

// =============================================================================
// 섹션 3
// =============================================================================
pres.addSection({ title: "3. 검증" });
{
  const s = pres.addSlide({ masterName: "SECTION", ...S("3. 검증") });
  s.addText("03", { placeholder: "num" });
  s.addText("이 결과는 믿을 수 있는가", { placeholder: "title" });
  s.addText("무작위 분할 대조군 1,000회 · 잠재표현 직교성 재검토", { placeholder: "body" });
}

// 무작위 대조군 설계
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("3. 검증") });
  s.addText("무작위 분할 대조군 설계", { placeholder: "title" });

  card(s, { x: 0.6, y: 1.5, w: 12.1, h: 1.3, fill: PALE, name: "why" });
  s.addText([
    { text: "왜 필요한가  ", options: { bold: true, color: NAVY, fontSize: 15 } },
    { text: "시계열을 아무 데서나 308조각으로 잘라도 조각마다 FC는 다르고 K-means는 무조건 무언가로 묶어준다. " +
            "따라서 '묶였다'는 사실 자체는 가설의 증거가 되지 못한다.",
      options: { fontSize: 14, color: INK } },
  ], { x: 0.9, y: 1.7, w: 11.5, h: 0.95, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  s.addText("귀무 모형", { x: 0.6, y: 3.0, w: 5.9, h: 0.35, fontSize: 16, bold: true,
    color: NAVY, isTextBox: true, margin: 0 });
  card(s, { x: 0.6, y: 3.42, w: 5.9, h: 1.5, fill: "F7F9FC", name: "null" });
  s.addText(
    "실제  : [70, 33, 252, 87, …]  ← MTAD-GAT 경계\n" +
    "무작위: [252, 87, 70, 33, …]  ← 같은 길이, 순서만 섞음",
    { x: 0.85, y: 3.62, w: 5.4, h: 1.1, fontSize: 12, color: INK, fontFace: "Courier New",
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.4 });
  s.addText("세그먼트 개수와 길이 분포는 동일하게 유지하고 경계 위치만 바꾼다. 이를 1,000회 반복.",
    { x: 0.6, y: 5.05, w: 5.9, h: 0.7, fontSize: 13, color: MUTED, isTextBox: true,
      margin: 0, lineSpacingMultiple: 1.2 });

  s.addText("검정 지표 7개", { x: 6.8, y: 3.0, w: 5.9, h: 0.35, fontSize: 16, bold: true,
    color: NAVY, isTextBox: true, margin: 0 });
  bullets(s, { x: 6.8, y: 3.45, w: 5.9, h: 2.5, fontSize: 13.5, items: [
    "세그먼트 내부 동질성 — 전/후반 CM 상관 (↑)",
    "경계 대비 — 경계 양쪽 CM 상관 (↓)",
    "군집 품질 silhouette — K = 2, 3, 4 (↑)",
    "dwell time 효과크기 η² — 2가지 정의 (↑)",
  ]});

  s.addNotes("길이 분포를 맞추는 이유는, 세그먼트가 짧으면 CM 추정이 불안정해져서 " +
    "경계 위치의 효과와 길이의 효과가 섞이기 때문입니다.");
}

// 대조군 결과
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("3. 검증") });
  s.addText("대조군 결과: 7개 중 1개만 통과", { placeholder: "title" });

  figure(s, { file: V5("fig1_permutation_null.png"), x: 0.87, y: 1.4, w: 11.6, ratio: 2.51,
    caption: "회색 = 무작위 분할 1,000회 분포 · 빨간 선 = MTAD-GAT 분할 관측값 · 각 패널 제목에 z와 p 표기" });

  card(s, { x: 0.6, y: 6.5, w: 12.1, h: 0.5, fill: "E6F2EC", name: "takeaway" });
  s.addText([
    { text: "통과한 지표  ", options: { bold: true, color: GREEN, fontSize: 13 } },
    { text: "dwell time 방문당 체류 η² = 0.3188 (무작위 0.1513, z = +3.27, p = 0.003) — " +
            "7개 검정의 Bonferroni 기준 0.0071을 넘는 유일한 지표",
      options: { fontSize: 13, color: INK } },
  ], { x: 0.85, y: 6.5, w: 11.6, h: 0.5, isTextBox: true, margin: 0, valign: "middle" });

  s.addNotes("FC 구조 지표는 전부 무작위 분포 한가운데 있습니다. " +
    "특히 내부 동질성과 경계 대비는 방향조차 유리하지 않습니다. " +
    "dwell time만 분포 바깥으로 나갔고, 7개 검정이므로 Bonferroni 기준 0.0071을 적용하면 " +
    "방문당 체류 시간 하나만 통과합니다.");
}

// dwell time 재해석
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("3. 검증") });
  s.addText("dwell time 결과를 다시 읽으면", { placeholder: "title" });

  card(s, { x: 0.6, y: 1.5, w: 12.1, h: 1.45, fill: "FFF7E8", name: "reread" });
  s.addText([
    { text: "무작위로 잘라도 dwell time η² 평균이 0.15다.  ", options: { bold: true, color: AMBER, fontSize: 16 } },
    { text: "즉 아무렇게나 잘라도 State별 체류 시간 차이는 크게 나오고, 무작위 분할의 상당수가 " +
            "통계적으로 유의한 ANOVA 결과를 낸다. V4에서 보고한 p = 6.4e-06 자체는 증거가 되지 못한다.",
      options: { fontSize: 14, color: INK } },
  ], { x: 0.9, y: 1.72, w: 11.5, h: 1.05, isTextBox: true, margin: 0, lineSpacingMultiple: 1.3 });

  statCard(s, { x: 0.6, y: 3.2, w: 3.87, h: 1.95, value: "0.32", color: GREEN,
    label: "관측 η² (방문당 체류)", note: "MTAD-GAT 분할" });
  statCard(s, { x: 4.72, y: 3.2, w: 3.87, h: 1.95, value: "0.15", color: MUTED,
    label: "무작위 η² 평균", note: "1,000회 분포의 중심" });
  statCard(s, { x: 8.84, y: 3.2, w: 3.87, h: 1.95, value: "p = .003", color: GREEN,
    label: "초과분의 유의성", note: "Bonferroni 기준 0.0071 통과" });

  s.addText("남은 대안 설명", { x: 0.6, y: 5.4, w: 12.1, h: 0.33, fontSize: 15, bold: true,
    color: NAVY, isTextBox: true, margin: 0 });
  bullets(s, { x: 0.6, y: 5.75, w: 12.1, h: 1.1, fontSize: 13, items: [
    "방문당 체류 시간은 인접 세그먼트가 같은 State로 묶이는 정도에 민감하다 — '경계가 정확하다'는 뜻일 수도, 반대로 '한 상태를 불필요하게 여러 번 잘랐다(과분할)'는 뜻일 수도 있다",
    "세그먼트가 길수록 FC 크기가 낮게 추정되는 경향(길이↔강도 결합)도 완전히 배제되지 않았다",
  ]});

  s.addNotes("이 슬라이드가 오늘 가장 중요한 방법론적 포인트입니다. " +
    "dwell time ANOVA 자체가 아니라 무작위 대비 초과분만이 증거라는 것, " +
    "그리고 그 초과분도 과분할로 설명될 여지가 남아 있다는 것입니다.");
}

// 직교성 재검토
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("3. 검증") });
  s.addText("잠재표현 '직교성' 결과 재검토", { placeholder: "title" });

  card(s, { x: 0.6, y: 1.5, w: 12.1, h: 1.25, fill: "FDF3F4", name: "ortho" });
  s.addText([
    { text: "문제  ", options: { bold: true, color: CORAL, fontSize: 15 } },
    { text: "cross-cluster 코사인은 서로 다른 모델이 만든 평균 잠재벡터를 비교한 값이다. " +
            "두 모델은 따로 초기화되어 따로 학습되었으므로 좌표계를 공유하지 않는다.",
      options: { fontSize: 14, color: INK } },
  ], { x: 0.9, y: 1.7, w: 11.5, h: 0.9, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  const rows = [
    ["", "관측 코사인", "무작위 벡터 95% 구간", "구간 내"],
    ["State 0 vs 1", "-0.0593", "[-0.121, +0.120]", "예"],
    ["State 0 vs 2", "-0.0053", "[-0.121, +0.120]", "예"],
    ["State 1 vs 2", "+0.0477", "[-0.121, +0.120]", "예"],
  ];
  s.addTable(
    rows.map((r, ri) => r.map((cell, ci) => ({
      text: cell,
      options: {
        bold: ri === 0 || ci === 0,
        color: ri === 0 ? "FFFFFF" : (ci === 3 ? CORAL : INK),
        fill: ri === 0 ? { color: NAVY } : { color: "FFFFFF" },
        align: ci === 0 ? "left" : "center",
      },
    }))),
    { x: 0.6, y: 3.0, w: 7.5, colW: [2.1, 1.8, 2.4, 1.2], rowH: 0.44, fontSize: 13,
      valign: "middle", border: { type: "solid", color: "D5DCEC", pt: 1 }, margin: 0.08 });

  card(s, { x: 8.4, y: 3.0, w: 4.3, h: 1.76, fill: PALE, name: "nullcalc" });
  s.addText("256차원 무작위 단위벡터", { x: 8.65, y: 3.15, w: 3.8, h: 0.3, fontSize: 13,
    bold: true, color: NAVY, isTextBox: true, margin: 0 });
  s.addText("평균 0, 표준편차 1/√256 = 0.0625\n관측 평균의 z = 0.16",
    { x: 8.65, y: 3.5, w: 3.8, h: 1.1, fontSize: 13, color: INK, isTextBox: true,
      margin: 0, lineSpacingMultiple: 1.3 });

  s.addText(
    "결론: 코사인 ≈ 0은 State가 잘 분리되었다는 증거가 아니라, 서로 다른 모델을 비교하면 " +
    "당연히 나오는 값이다. 같은 이유로 V3 공유 모델의 0.97도 유효한 대조군이 아니다.",
    { x: 0.6, y: 5.1, w: 12.1, h: 0.8, fontSize: 15, bold: true, color: CORAL,
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  s.addNotes("무작위 벡터 20,000쌍을 시뮬레이션해서 확인했습니다. " +
    "관측된 세 값 모두 null 95% 구간 안에 있습니다. " +
    "대체 검정으로는 공유 모델 하나로 latent를 뽑은 뒤 held-out 피험자 분류 정확도나 " +
    "permutation test를 쓰는 방법을 제안드립니다.");
}

// =============================================================================
// 결론
// =============================================================================
pres.addSection({ title: "결론" });
{
  const s = pres.addSlide({ masterName: "CLOSING", ...S("결론") });
  s.addText("정리와 다음 단계", { placeholder: "title" });

  s.addText("현재 말할 수 있는 것", { x: 0.9, y: 1.85, w: 5.6, h: 0.35, fontSize: 16,
    bold: true, color: "97A3C9", isTextBox: true, margin: 0 });
  s.addText([
    { text: "세그먼트 FC를 군집화하면 겉보기에 구분되는 State가 얻어지지만, 그 구조는 사실상 " +
            "전역 연결강도라는 단일 연속 축을 임의의 K개로 절단한 결과다.",
      options: { fontSize: 14, color: "FFFFFF", breakLine: true } },
    { text: "\n전역 강도를 보정하면 Somatomotor와 Frontoparietal Control 두 네트워크의 " +
            "상대적 비중 변화만 K와 무관하게 일관되게 남는다.",
      options: { fontSize: 14, color: "FFFFFF" } },
  ], { x: 0.9, y: 2.3, w: 5.6, h: 2.5, isTextBox: true, margin: 0, lineSpacingMultiple: 1.35 });

  card(s, { x: 0.9, y: 5.0, w: 5.6, h: 1.45, fill: "1E2A52", name: "framing" });
  s.addText([
    { text: "논문 프레이밍 제안\n", options: { bold: true, color: AMBER, fontSize: 14 } },
    { text: "\"새로운 상태 정의 방법 제안\"보다 \"널리 쓰이는 분할·군집 관행이 무작위 분할과 " +
            "구별되지 않는다\"는 방법론적 검증 쪽이 현재 데이터로 방어 가능하다.",
      options: { color: "CFD7EC", fontSize: 12.5 } },
  ], { x: 1.15, y: 5.18, w: 5.1, h: 1.15, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });

  s.addText("다음 단계", { x: 7.0, y: 1.85, w: 5.4, h: 0.35, fontSize: 16, bold: true,
    color: "97A3C9", isTextBox: true, margin: 0 });
  const next = [
    { n: 1, t: "과분할 여부 판별", d: "경계 개수를 바꿔가며 dwell time 초과분의 변화를 추적", c: CORAL },
    { n: 2, t: "직교성 검정 교체", d: "공유 모델 latent → held-out 피험자 분류 정확도 / permutation test", c: TEAL },
    { n: 3, t: "움직임 교란 통제", d: "피험자별 FD 산출 후 State별 FD 비교 (전역강도와 직결)", c: AMBER },
    { n: 4, t: "외부 데이터 재현", d: "현재 '세 번 재현'은 같은 27명을 다르게 자른 것", c: "97A3C9" },
  ];
  let y = 2.3;
  next.forEach((o) => {
    numCircle(s, { x: 7.0, y: y + 0.03, d: 0.44, n: o.n, color: o.c });
    s.addText(o.t, { x: 7.62, y, w: 4.8, h: 0.33, fontSize: 14.5, bold: true,
      color: "FFFFFF", isTextBox: true, margin: 0 });
    s.addText(o.d, { x: 7.62, y: y + 0.34, w: 4.8, h: 0.52, fontSize: 12, color: "A9B4D4",
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.15 });
    y += 1.08;
  });

  s.addNotes("다음 단계 네 가지 중 1번과 3번을 먼저 돌려보려 합니다. " +
    "1번은 지금 결론에서 가장 약한 고리이고, 3번은 전역강도가 머리 움직임과 직결되기 때문입니다.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("saved:", OUT);
})();
