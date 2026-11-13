// 요청 분석 결과 — 교수님 요청 (1)~(4) + dwell time 만 수록
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/Users/mac/.claude/skills/synced/a3d420dd-7bca-4cf8-b3b3-ed5e5de273b8_0001a5c5-5808-4cc0-9bb9-b3820e9fcf4b/pptx/scripts/apply_theme.js");

const ROOT = "/Users/mac/Desktop/code/MTAD-GAT";
const ADD = (f) => path.join(ROOT, "visualization_ver4_add", f);
const V5F = (f) => path.join(ROOT, "visualization_ver5", f);
const OUT = path.join(ROOT, "요청분석_결과_발표.pptx");

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
pres.addSection({ title: "표지" });
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

// 요청사항 수행 현황
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("표지") });
  s.addText("요청사항 수행 현황", { placeholder: "title" });

  const rows = [
    ["요청", "수행 결과", "슬라이드"],
    ["(1) row-wise thresholding → 100×1 DC", "완료 · 상위 10%, 행별 10개 유지", "4"],
    ["(2) 100×1 벡터 brain surface 시각화", "완료 · ENIGMA TOOLBOX, fsa5", "6-7"],
    ["(3) Schaefer 7-Network로 7×1 요약 + bar plot", "완료 · Yeo 7 네트워크 평균", "9"],
    ["(4) subject별 DC → ANOVA + pair별 t-test", "완료 · F(3,71) = 218.6, 6/6 pair 유의", "11-13"],
    ["(5) dwell time 평균±SD → ANOVA + t-test", "완료 · F(3,71) = 10.78 (방문당)", "15-16"],
  ];
  tbl(s, rows, { x: 0.6, y: 1.45, w: 12.1, colW: [5.6, 4.9, 1.6], rowH: 0.52, fontSize: 13 });

  card(s, { x: 0.6, y: 4.6, w: 12.1, h: 1.5, fill: PALE, name: "scope" });
  s.addText([
    { text: "분석 조건  ", options: { bold: true, color: NAVY, fontSize: 14 } },
    { text: "K = 4 (Brain State 4개) · 피험자 27명 · 세그먼트 308개 · " +
            "CM은 Pearson 상관 + Fisher-Z 변환 · thresholding은 각 행 상위 10% (부호 유지) · " +
            "ROI는 Schaefer-100 (피질만), 네트워크는 Yeo 7-Network 기준.",
      options: { fontSize: 13.5, color: INK } },
  ], { x: 0.85, y: 4.8, w: 11.6, h: 1.1, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  s.addNotes("요청 다섯 항목 모두 완료했고, 해석의 타당성 확인을 위해 세 가지를 자체 추가했습니다.");
}

// 용어 정리
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("표지") });
  s.addText("용어 정리", { placeholder: "title" });

  const terms = [
    { t: "CM (연결성 행렬)", d: "한 세그먼트 안에서 100개 ROI가 서로 얼마나 같이 움직였는지 적은 100×100 표. 각 칸 = Pearson 상관의 Fisher-Z 값", c: NAVY },
    { t: "DC (Degree Centrality)", d: "각 ROI가 자신의 가장 강한 상위 10% 연결로부터 받는 총 연결 강도. 100×1 벡터", c: NAVY },
    { t: "FC magnitude (전역 연결강도)", d: "CM에 적힌 숫자들의 전반적 크기. 누가 중심인지가 아니라 표 전체의 수위", c: TEAL },
    { t: "ANOVA / F값", d: "셋 이상 집단의 평균을 한 번에 비교하는 검정. F = 집단 사이의 차이 ÷ 집단 안의 흩어짐", c: TEAL },
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

  s.addNotes("CM은 조각 하나의 친밀도 표, DC는 그 표에서 뽑은 구역별 중심성 점수입니다. " +
    "FC magnitude는 표 전체의 수위이고, FDR q는 100번 검정에 따른 우연한 유의성을 걸러낸 값입니다.");
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
    { text: "편차 맵에서도 State 간 패턴 차이가 크지 않습니다. 각 State에서 두드러지는 " +
            "영역이 뚜렷이 갈린다면 여기서 보여야 하는데, 그런 모습은 관찰되지 않았습니다.",
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
    ["Limbic", "4", "2.41", "3.56", "4.33", "6.83"],
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
    { text: "State는 CM을 군집화해 정의했고 DC도 같은 CM에서 유도되므로, 이 큰 F값에는 " +
            "정의상 당연한 부분이 섞여 있습니다. 독립적인 검증 지표가 필요합니다.",
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

// =============================================================================// =============================================================================
// Q&A — 요청 범위 안에서 답할 수 있는 질문만
// =============================================================================
pres.addSection({ title: "Q&A" });

function qaCards(slide, items) {
  let y = 1.4;
  items.forEach((o, i) => {
    card(slide, { x: 0.6, y, w: 12.1, h: 1.28, fill: PALE, name: `qa-${i}` });
    slide.addText([
      { text: "Q. ", options: { bold: true, color: o.c, fontSize: 14 } },
      { text: o.q, options: { bold: true, color: o.c, fontSize: 14 } },
    ], { x: 0.9, y: y + 0.12, w: 11.5, h: 0.34, isTextBox: true, margin: 0 });
    slide.addText([
      { text: "A. ", options: { bold: true, color: INK, fontSize: 12.5 } },
      { text: o.a, options: { fontSize: 12.5, color: INK } },
    ], { x: 0.9, y: y + 0.5, w: 11.5, h: 0.68, isTextBox: true, margin: 0,
         lineSpacingMultiple: 1.18 });
    y += 1.38;
  });
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("Q&A") });
  s.addText("예상 질문 즉답 (1)", { placeholder: "title" });
  qaCards(s, [
    { c: AMBER, q: "왜 하필 상위 10%인가?",
      a: "관행적 선택입니다. 5% / 15%로 바꾸는 민감도 분석 옵션(--top-pct)은 구현해 두었으나 아직 실행하지 않았습니다. 다음 단계로 확인하겠습니다." },
    { c: NAVY, q: "CM을 먼저 평균하고 thresholding 했는가, 반대인가?",
      a: "CM을 먼저 평균한 뒤 thresholding 했습니다. 순서를 바꾸면 DC가 1.2~1.4 정도 커집니다(thresholding이 비선형이라). 평균을 먼저 내는 쪽이 세그먼트 잡음에 강합니다." },
    { c: NAVY, q: "(1)번 표의 DC와 (4)번 표의 DC가 왜 다른가?",
      a: "(1)은 State 전체 CM을 한 번에 평균한 값이고, (4)는 피험자별로 먼저 묶은 뒤 평균한 값입니다. 피험자마다 세그먼트 수가 8~14개로 달라 값이 어긋납니다." },
    { c: CORAL, q: "100개 ROI가 전부 유의한 것이 좋은 결과인가?",
      a: "뒤집어 보면 \"어느 영역이 특별히 다른지 가려내지 못했다\"는 뜻이기도 합니다. 영역 특이성을 보려면 전역 크기를 통제한 추가 분석이 필요합니다." },
  ]);
  s.addNotes("네 번째 질문이 핵심입니다. 100/100이 유의하다는 건 공간적 특이성 정보가 없다는 뜻이라, " +
    "전역 크기를 통제한 분석이 후속으로 필요합니다.");
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("Q&A") });
  s.addText("예상 질문 즉답 (2)", { placeholder: "title" });
  qaCards(s, [
    { c: AMBER, q: "State 3은 피험자 9명뿐인데 신뢰할 수 있나?",
      a: "검정력이 낮습니다. 세그먼트 16개 / 피험자 9명이고, 27명 중 18명은 한 번도 방문하지 않았습니다. State 3 관련 결론은 탐색적으로만 해석해야 합니다." },
    { c: AMBER, q: "dwell time 점유율의 합이 100%가 되는가?",
      a: "표의 퍼센트는 그 State를 방문한 피험자들만의 평균이라 합이 131%입니다. 전체 27명 기준 실제 점유율은 State1 44.2 / State0 31.0 / State2 20.3 / State3 4.5%입니다." },
    { c: NAVY, q: "관측 단위가 (subject × State)인데 독립성 가정은?",
      a: "엄밀히는 위배됩니다. 한 피험자가 여러 State에 기여합니다. 보조로 비모수 Kruskal-Wallis와 Welch t-test를 함께 보고했고, 결론은 동일했습니다." },
    { c: NAVY, q: "dwell time의 시간 해상도 하한은?",
      a: "세그먼테이션의 최소 길이 제약 때문에 약 22.3초(31 TP)입니다. 그보다 짧은 상태 전환은 원리적으로 관측되지 않으며, 방문당 체류 시간의 하한도 같습니다." },
  ]);
}

// =============================================================================
pres.addSection({ title: "정리" });
{
  const s = pres.addSlide({ masterName: "CLOSING", ...S("정리") });
  s.addText("정리", { placeholder: "title" });

  s.addText("요청 분석 결과", { x: 0.9, y: 1.7, w: 5.8, h: 0.33, fontSize: 15, bold: true,
    color: "97A3C9", isTextBox: true, margin: 0 });
  const done = [
    "(1) DC 정의 — State 1 < 0 < 2 < 3 (5.23 → 11.35)",
    "(2) 표면 시각화 — ENIGMA TOOLBOX fsa5 완료",
    "(3) 7-Network — 모든 State에서 Vis 최고 / Limbic 최저",
    "(4) ANOVA F(3,71) = 218.6, η² = 0.90 · 6/6 pair 유의",
    "(5) Dwell time — 방문당 F = 10.78, State 1만 유의하게 길다",
  ];
  s.addText(done.map((t, i) => ({ text: t, options: { bullet: true,
    breakLine: i !== done.length - 1, color: "FFFFFF" } })),
    { x: 0.9, y: 2.15, w: 5.8, h: 2.7, fontSize: 13.5, isTextBox: true,
      paraSpaceAfter: 8, lineSpacingMultiple: 1.2 });

  card(s, { x: 0.9, y: 5.05, w: 5.8, h: 1.55, fill: "1E2A52", name: "limit" });
  s.addText([
    { text: "해석 시 유의\n", options: { bold: true, color: AMBER, fontSize: 14 } },
    { text: "State는 CM 군집으로 정의했고 DC도 같은 CM에서 유도되므로, 큰 F값에는 " +
            "정의상 당연한 부분이 섞여 있습니다. 독립적 검증이 필요합니다.",
      options: { color: "CFD7EC", fontSize: 12.5 } },
  ], { x: 1.15, y: 5.25, w: 5.3, h: 1.25, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 });

  s.addText("다음 단계", { x: 7.1, y: 1.7, w: 5.3, h: 0.33, fontSize: 15, bold: true,
    color: "97A3C9", isTextBox: true, margin: 0 });
  const next = [
    { n: 1, t: "민감도 분석", d: "상위 5% / 15%로 바꿔 DC 결론이 유지되는지 확인" },
    { n: 2, t: "전역 크기 통제", d: "100/100 유의의 어느 부분이 영역 특이성인지 분리" },
    { n: 3, t: "K=2·3 dwell time", d: "현재 K=4만 수행 — 나머지 K에도 동일 분석" },
    { n: 4, t: "움직임 교란 통제", d: "피험자별 FD 산출 → State별 FD 비교" },
  ];
  let y = 2.15;
  next.forEach((o) => {
    s.addShape(pres.ShapeType.ellipse, { x: 7.1, y: y + 0.02, w: 0.42, h: 0.42,
      fill: { color: CORAL }, line: { color: CORAL, width: 0 }, objectName: `nc-${o.n}` });
    s.addText(String(o.n), { x: 7.1, y: y + 0.02, w: 0.42, h: 0.42, align: "center",
      valign: "middle", fontSize: 14, bold: true, color: "FFFFFF", isTextBox: true, margin: 0 });
    s.addText(o.t, { x: 7.7, y, w: 4.7, h: 0.32, fontSize: 14, bold: true, color: "FFFFFF",
      isTextBox: true, margin: 0 });
    s.addText(o.d, { x: 7.7, y: y + 0.32, w: 4.7, h: 0.5, fontSize: 12, color: "A9B4D4",
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.15 });
    y += 1.1;
  });

  s.addNotes("요청하신 다섯 항목 모두 완료했습니다. 다음 단계로는 민감도 분석과 " +
    "전역 크기 통제 분석을 먼저 진행하려 합니다.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("saved:", OUT);
})();
