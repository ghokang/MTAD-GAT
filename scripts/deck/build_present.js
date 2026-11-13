// 요청 분석 결과 — 교수님 요청 (1)~(4) + dwell time 만 수록
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/Users/mac/.claude/skills/synced/a3d420dd-7bca-4cf8-b3b3-ed5e5de273b8_0001a5c5-5808-4cc0-9bb9-b3820e9fcf4b/pptx/scripts/apply_theme.js");

const ROOT = "/Users/mac/Desktop/code/MTAD-GAT";
const ADD = (f) => path.join(ROOT, "visualization_ver4_add", f);
const V5F = (f) => path.join(ROOT, "visualization_ver5", f);
const OUT = path.join(ROOT, "요청분석_발표용.pptx");

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
// =============================================================================
// 발표용 — 슬라이드는 비우고 해석·예상답변은 노트로
// =============================================================================
pres.addSection({ title: "표지" });
{
  const s = pres.addSlide({ masterName: "TITLE_DARK", ...S("표지") });
  s.addText("교수님 요청 분석 결과", { placeholder: "eyebrow" });
  s.addText("Degree Centrality 기반 Brain State 해석", { placeholder: "title" });
  s.addText("(1) DC 정의  (2) 표면 시각화  (3) 7-Network 요약  (4) 통계 검정  (5) Dwell time",
    { placeholder: "body" });
  s.addText("V4 K=4 · 피험자 27명 · 세그먼트 308개 · Schaefer-100 / Yeo 7-Network",
    { placeholder: "meta" });
  s.addNotes(
    "[인사] 요청하신 다섯 항목 분석을 모두 마쳐 보고드립니다.\n\n" +
    "[구성 안내] (1)~(3)은 State 수준에서 DC를 만들고 시각화·요약한 내용이고, " +
    "(4)와 dwell time은 피험자별로 계산한 뒤 State 간 차이를 검정한 내용입니다.\n\n" +
    "[데이터] HCP 휴식상태 fMRI 27명. MTAD-GAT 임베딩 변화점으로 분할한 세그먼트 308개. " +
    "ROI는 Schaefer-100 피질 영역, 네트워크는 Yeo 7-Network 기준입니다.");
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("표지") });
  s.addText("요청사항 수행 현황", { placeholder: "title" });

  const rows = [
    ["요청", "수행 결과", "슬라이드"],
    ["(1) row-wise thresholding → 100×1 DC", "완료 · 각 행 상위 10%, 10개 유지", "4"],
    ["(2) 100×1 벡터 brain surface 시각화", "완료 · ENIGMA TOOLBOX, fsa5", "6–7"],
    ["(3) 7-Network로 7×1 요약 + bar plot", "완료 · Yeo 7 네트워크 평균", "9–10"],
    ["(4) subject별 DC → ANOVA + pair t-test", "완료 · F(3,71) = 218.6, 6/6 pair 유의", "12–14"],
    ["(5) dwell time 평균±SD → ANOVA + t-test", "완료 · 방문당 F(3,71) = 10.78", "16–17"],
  ];
  tbl(s, rows, { x: 0.6, y: 1.6, w: 12.1, colW: [5.6, 4.9, 1.6], rowH: 0.62, fontSize: 14 });

  card(s, { x: 0.6, y: 5.3, w: 12.1, h: 1.1, fill: PALE, name: "scope" });
  s.addText([
    { text: "분석 조건  ", options: { bold: true, color: NAVY, fontSize: 14 } },
    { text: "K = 4 · CM은 Pearson 상관 + Fisher-Z 변환 · thresholding은 각 행 상위 10% (부호 유지)",
      options: { fontSize: 14, color: INK } },
  ], { x: 0.85, y: 5.48, w: 11.6, h: 0.75, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  s.addNotes(
    "[요약] 다섯 항목 모두 완료했습니다.\n\n" +
    "[관측 단위 구분 — 먼저 짚고 갈 것] (1)~(3)은 State에 속한 세그먼트 전체를 모아 " +
    "State 하나당 DC 하나를 만든 group-level 결과입니다. (4)와 (5)는 요청대로 피험자별로 " +
    "먼저 계산한 뒤, (subject × State) 관측 75개를 State로 묶어 검정했습니다.\n\n" +
    "[그래서 숫자가 조금 다릅니다] (1)의 State별 DC(5.23/6.96/8.61/11.35)와 " +
    "(4)의 평균 DC(5.98/7.66/9.63/12.19)가 다른 이유가 이것입니다. " +
    "전자는 세그먼트를 전부 풀링한 값, 후자는 피험자별로 묶은 뒤 평균한 값입니다. " +
    "크기 순서는 동일합니다.");
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
  s.addText("(1) DC 계산과 State별 결과", { placeholder: "title" });
  const yy = qa(s, {
    q: "100×100 행렬에 row-wise thresholding을 적용해 100×1 DC를 만들어 달라",
    a: "각 행 99개 후보 중 상위 10개만 남겨 합산 → State별 DC 산출 완료",
    color: TEAL,
  });

  card(s, { x: 0.6, y: yy, w: 6.1, h: 1.9, fill: "F7F9FC", name: "steps" });
  s.addText(
    "1) 대각(자기 연결) 제외        → 행당 99개 후보\n" +
    "2) 각 행에서 상위 10% 유지     → 행당 10개\n" +
    "3) 유지된 element를 행 방향 합 → DC_i",
    { x: 0.9, y: yy + 0.32, w: 5.5, h: 1.3, fontSize: 12.5, color: INK, fontFace: "Courier New",
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.5 });

  const rows = [
    ["State", "n_CM", "평균 DC", "최대 DC ROI"],
    ["State 1", "121", "5.23", "LH_Vis_8"],
    ["State 0", "99", "6.96", "LH_Vis_9"],
    ["State 2", "72", "8.61", "LH_Vis_9"],
    ["State 3", "16", "11.35", "RH_Vis_8"],
  ];
  tbl(s, rows, { x: 7.1, y: yy, w: 5.6, colW: [1.5, 0.95, 1.35, 1.8], rowH: 0.38, fontSize: 12.5 });

  s.addNotes(
    "[설명] 각 행에서 가장 강한 상위 10개 연결만 남겨 더했습니다. 약한 연결까지 모두 더하면 " +
    "잡음이 섞이기 때문입니다.\n\n" +
    "[해석] DC 크기가 State 1 < 0 < 2 < 3으로 뚜렷한 계단을 이룹니다. 네 State 모두 " +
    "최대 DC ROI가 Visual network 소속입니다 — 크기는 달라도 가장 강한 허브의 위치는 같습니다.\n\n" +
    "[예상질문 1 — 왜 상위 10%인가?] 관행적 선택입니다. 5%/15%로 바꾸는 민감도 분석 옵션은 " +
    "구현해 두었으나 아직 실행하지 않았습니다. 다음 단계로 확인하겠습니다.\n\n" +
    "[예상질문 2 — CM을 먼저 평균했나, DC를 먼저 구했나?] CM을 먼저 평균한 뒤 thresholding " +
    "했습니다. 이유가 두 가지입니다. 첫째, thresholding은 상위 10%를 '고르는' 과정이라 잡음이 " +
    "크면 운 좋게 큰 값이 뽑혀 DC가 부풀려집니다. 둘째, 세그먼트가 짧을수록 그 편향이 큽니다 — " +
    "실제로 세그먼트 길이와 세그먼트별 DC의 상관이 r = −0.295입니다. 길이 31~60 TP 조각은 " +
    "DC 평균 9.02, 200 TP 이상 조각은 7.36입니다. State마다 평균 세그먼트 길이가 달라서 " +
    "(State 1은 118 TP, State 3은 90 TP) 세그먼트별 DC를 평균하면 길이 효과가 State 비교에 " +
    "섞여 들어갑니다.\n\n" +
    "[예상질문 3 — State 3은 세그먼트 16개뿐인데?] 검정력이 낮습니다. 피험자도 9명뿐이고 " +
    "27명 중 18명은 한 번도 방문하지 않았습니다. State 3 관련 결론은 탐색적으로만 해석해야 합니다.");
}

// =============================================================================
pres.addSection({ title: "(2) 표면 시각화" });
{
  const s = pres.addSlide({ masterName: "SECTION", ...S("(2) 표면 시각화") });
  s.addText("(2)", { placeholder: "num" });
  s.addText("Brain surface 시각화", { placeholder: "title" });
  s.addText("ENIGMA TOOLBOX · fsa5 표면 · parcel_to_surface + plot_cortical",
    { placeholder: "body" });
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(2) 표면 시각화") });
  s.addText("(2) State별 DC 피질 분포", { placeholder: "title" });
  const yy = qa(s, {
    q: "100×1 벡터를 brain surface에 시각화해 달라 (ENIGMA TOOLBOX)",
    a: "State별 DC 표면 맵 완료 — 공통 color range로 네 State를 직접 비교",
    color: TEAL,
  });
  figure(s, { file: ADD("fig1_surface_dc_by_state.png"), x: 4.12, y: yy, w: 5.1, ratio: 1.27,
    caption: "공통 color range (각 행 좌→우: LH lat / LH med / RH med / RH lat)" });

  s.addNotes(
    "[읽는 법] 네 행이 State 0~3이고, 각 행은 왼쪽부터 좌반구 바깥면, 좌반구 안쪽면, " +
    "우반구 안쪽면, 우반구 바깥면입니다. 네 State를 같은 색 기준으로 칠했기 때문에 " +
    "밝기를 직접 비교할 수 있습니다.\n\n" +
    "[해석] 밝은 영역의 위치가 네 State에서 비슷하고 전체 밝기만 다릅니다. " +
    "가장 밝은 곳은 모두 후두엽 시각 영역입니다.\n\n" +
    "[기술 메모] ENIGMA TOOLBOX는 vtk 9.3.1에 고정해야 동작합니다. 9.4 이상에서는 " +
    "PointSet 관련 오류가 발생합니다.");
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(2) 표면 시각화") });
  s.addText("(2) 전체 평균 대비 State별 편차", { placeholder: "title" });
  figure(s, { file: ADD("fig2_surface_dc_deviation.png"), x: 3.95, y: 1.4, w: 5.45, ratio: 1.28,
    caption: "State별 DC − 전체 평균 DC (붉은색 = 그 State에서 상대적으로 강화)" });

  s.addNotes(
    "[왜 이 그림이 필요한가] 앞 슬라이드는 절대 크기라 State 3이 통째로 밝게 보입니다. " +
    "전체 평균을 빼면 각 State에서 상대적으로 두드러지는 영역만 남습니다.\n\n" +
    "[해석] 편차 맵에서도 State 간 패턴 차이가 크지 않습니다. 각 State마다 특별히 " +
    "두드러지는 영역이 뚜렷이 갈린다면 여기서 보여야 하는데, 그런 모습은 관찰되지 않았습니다.\n\n" +
    "[이어질 이야기] 이 인상이 (4)번의 '100개 ROI 전부 유의'와 어떻게 연결되는지는 " +
    "14번 슬라이드에서 다시 말씀드립니다.");
}

// =============================================================================
pres.addSection({ title: "(3) 7-Network" });
{
  const s = pres.addSlide({ masterName: "SECTION", ...S("(3) 7-Network") });
  s.addText("(3)", { placeholder: "num" });
  s.addText("Yeo 7-Network 요약", { placeholder: "title" });
  s.addText("Schaefer2018_100Parcels_7Networks_order_info.txt 레이블 사용",
    { placeholder: "body" });
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(3) 7-Network") });
  s.addText("(3) 100×1 → 7×1 요약", { placeholder: "title" });
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
    rowH: 0.45, fontSize: 13 });

  s.addNotes(
    "[계산 방식] 각 네트워크에 속한 ROI들의 DC를 평균했습니다. ROI 개수는 네트워크마다 " +
    "5개(Limbic)에서 24개(Default Mode)까지 다릅니다.\n\n" +
    "[해석 — 이 표의 핵심] 7개 네트워크 전부가 State 1 → 3 방향으로 함께 올라갑니다. " +
    "특정 네트워크만 오르고 다른 네트워크는 내려가는 패턴이 아닙니다. " +
    "네트워크 간 순위(Vis > SomMot > DorsAttn > Default > Cont > SalVentAttn > Limbic)도 " +
    "네 State에서 거의 그대로 유지됩니다.\n\n" +
    "[의미] 상태가 바뀔 때 뇌의 '어느 부분이 중심이냐'가 재배치되는 것이 아니라, " +
    "전체가 함께 오르내리는 양상으로 보입니다.");
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(3) 7-Network") });
  s.addText("(3) 네트워크별 bar plot", { placeholder: "title" });
  figure(s, { file: ADD("fig5_network_dc_barplot.png"), x: 0.9, y: 1.85, w: 11.5, ratio: 2.96,
    caption: "(좌) 네트워크별 State 비교 grouped bar plot  (우) 네트워크별 State 프로파일" });

  s.addNotes(
    "[읽는 법] 왼쪽 그림에서 네 색 막대가 모든 네트워크에서 같은 순서로 늘어섭니다. " +
    "오른쪽 프로파일은 네 선이 서로 교차하지 않고 평행하게 놓입니다.\n\n" +
    "[해석] 선이 교차하지 않는다는 것이 중요합니다. 교차한다면 '어떤 State에서는 " +
    "A 네트워크가 더 중심이고 다른 State에서는 B가 중심'이라는 뜻인데, 그런 역전이 " +
    "관찰되지 않습니다.\n\n" +
    "[색상] Yeo 7-Network 표준 색상을 사용했습니다.");
}

// =============================================================================
pres.addSection({ title: "(4) 통계 검정" });
{
  const s = pres.addSlide({ masterName: "SECTION", ...S("(4) 통계 검정") });
  s.addText("(4)", { placeholder: "num" });
  s.addText("State 간 DC 차이 검정", { placeholder: "title" });
  s.addText("피험자별 CM → DC · 관측 단위 (subject × State) 75개 · ANOVA + pair별 t-test",
    { placeholder: "body" });
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(4) 통계 검정") });
  s.addText("(4-a) State 간 DC가 다른가", { placeholder: "title" });
  const yy = qa(s, {
    q: "subject별 CM으로 DC를 만들어 State별로 다른지 ANOVA로 확인 (F, p 보고)",
    a: "F(3, 71) = 218.56,  p = 8.97e-36,  η² = 0.90",
    color: GREEN,
  });

  const rows = [
    ["State", "피험자 수", "평균 DC", "표준편차"],
    ["State 1", "21", "5.979", "0.675"],
    ["State 0", "24", "7.661", "0.544"],
    ["State 2", "21", "9.625", "0.806"],
    ["State 3", "9", "12.185", "0.623"],
  ];
  tbl(s, rows, { x: 0.6, y: yy, w: 6.0, colW: [1.5, 1.5, 1.5, 1.5], rowH: 0.45, fontSize: 13 });

  card(s, { x: 7.0, y: yy, w: 5.7, h: 2.25, fill: PALE, name: "unit" });
  s.addText([
    { text: "관측 단위\n", options: { bold: true, color: NAVY, fontSize: 14.5 } },
    { text: "각 피험자의 세그먼트를 State별로 묶어 CM을 평균한 뒤 DC 계산\n" +
            "→ (subject × State) 쌍, 총 N = 75\n\n" +
            "비모수 확인: Kruskal-Wallis H = 66.78, p = 2.08e-14",
      options: { fontSize: 13, color: INK } },
  ], { x: 7.25, y: yy + 0.22, w: 5.2, h: 1.9, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 });

  s.addNotes(
    "[요청대로 피험자별 계산] 표의 n은 세그먼트 수가 아니라 피험자 수입니다. " +
    "각 피험자의 세그먼트를 State별로 묶어 CM을 평균하고 DC를 구했습니다. " +
    "그렇게 얻은 75개 관측을 State로 묶어 검정했습니다.\n\n" +
    "[해석] η² = 0.90은 전체 분산의 90%를 State 구분이 설명한다는 뜻입니다. " +
    "비모수 Kruskal-Wallis에서도 같은 결론이 나와 분포 치우침 때문은 아닙니다.\n\n" +
    "[예상질문 — (1)번 표의 DC와 왜 다른가?] (1)은 State의 세그먼트를 전부 풀링해 한 번에 " +
    "평균한 group-level 값이고, 여기는 피험자별로 먼저 묶은 값입니다. 피험자마다 세그먼트 " +
    "수가 8~14개로 달라 값이 어긋납니다. 크기 순서는 동일합니다.\n\n" +
    "[예상질문 — 독립성 가정은?] 엄밀히는 위배됩니다. 한 피험자가 여러 State에 기여합니다. " +
    "그래서 비모수 Kruskal-Wallis와 Welch t-test를 함께 보고했고 결론은 동일했습니다.\n\n" +
    "[스스로 짚을 점] State를 CM 군집으로 정의했고 DC도 같은 CM에서 유도되므로, " +
    "이 큰 F값에는 정의상 당연한 부분이 섞여 있습니다.");
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(4) 통계 검정") });
  s.addText("(4-a) State pair별 two-sample t-test", { placeholder: "title" });
  const yy = qa(s, {
    q: "각 state pair별 DC 비교를 two-sample t-test로 (t, p 보고)",
    a: "6개 쌍 전부 유의 — |t| = 8.48 ~ 23.57",
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
    rowH: 0.48, fontSize: 12.5 });

  s.addNotes(
    "[검정 방식] equal variance를 가정한 Student's t-test입니다. 보조로 Welch t-test도 " +
    "계산했고 결론은 같았습니다. FDR q는 6개 쌍에 대한 Benjamini-Hochberg 보정값입니다.\n\n" +
    "[해석] 효과크기 Cohen's d가 2.76~9.39로 극단적으로 큽니다. 보통 0.8이면 '큰 효과'라고 " +
    "봅니다.\n\n" +
    "[정직하게 덧붙일 점] 다만 State가 DC 크기 자체로 갈린 묶음이기 때문에, 이 크기는 " +
    "어느 정도 정의상 당연한 결과이기도 합니다. 독립적인 검증 지표가 필요합니다.\n\n" +
    "[State 3 관련] State 3이 들어간 세 쌍은 피험자 9명에 기반합니다. d값이 가장 큰 쌍들이지만 " +
    "표본이 작다는 점을 함께 말씀드려야 합니다.");
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(4) 통계 검정") });
  s.addText("(4-b, 4-c) 네트워크·ROI 수준", { placeholder: "title" });
  const yy = qa(s, {
    q: "네트워크별, ROI별로도 State 간 차이가 있는가",
    a: "7 / 7 네트워크, 100 / 100 ROI 모두 FDR q < 0.05",
    color: GREEN,
  });

  figure(s, { file: ADD("fig7_anova_boxplots.png"), x: 2.67, y: yy, w: 8.0, ratio: 2.0,
    caption: "Global DC 및 7개 네트워크별 DC의 State 간 분포 (점 = subject × State 관측)" });

  s.addNotes(
    "[결과] 네트워크별 F는 31.2~110.9 사이이고 7개 전부 FDR 보정 후 유의했습니다. " +
    "ROI 수준에서도 100개 전부가 유의했습니다.\n\n" +
    "[예상질문 — 100개 전부 유의한 것이 좋은 결과인가?] 뒤집어 보면 '어느 영역이 특별히 " +
    "다른지 가려내지 못했다'는 뜻이기도 합니다. 전부 다르다는 것은 공간적 특이성 정보가 " +
    "없다는 것과 같습니다.\n\n" +
    "[후속 제안] (2)번 편차 맵과 (3)번 프로파일에서 본 인상 — 네트워크들이 함께 오르내린다 — " +
    "과 합쳐 보면, 이 차이의 상당 부분이 전역적인 연결 강도 차이일 가능성이 있습니다. " +
    "이를 분리하려면 각 관측의 DC를 자기 평균으로 나눈 상대 DC로 같은 검정을 반복해야 합니다. " +
    "다음 단계로 진행하겠습니다.\n\n" +
    "[상자그림 읽는 법] 상자는 가운데 50% 구간, 가로선은 중앙값, 점은 개별 " +
    "(subject × State) 관측입니다.");
}

// =============================================================================
pres.addSection({ title: "(5) Dwell time" });
{
  const s = pres.addSlide({ masterName: "SECTION", ...S("(5) Dwell time") });
  s.addText("(5)", { placeholder: "num" });
  s.addText("Dwell time 분석", { placeholder: "title" });
  s.addText("피험자별 time point 개수 × 0.72초(TR) · 평균±표준편차 · ANOVA + pair별 t-test",
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
    ["State", "피험자 수", "총 점유 [초]", "방문당 체류 [초]", "방문 횟수"],
    ["State 1", "21", "491.3 ± 327.1", "340.8 ± 298.4", "1.71"],
    ["State 0", "24", "301.2 ± 235.8", "116.1 ± 72.4", "2.42"],
    ["State 2", "21", "225.6 ± 202.7", "90.7 ± 60.8", "2.10"],
    ["State 3", "9", "115.8 ± 128.4", "66.3 ± 53.0", "1.44"],
  ];
  tbl(s, rows, { x: 0.6, y: yy, w: 6.4, colW: [1.3, 1.1, 1.5, 1.6, 0.9], rowH: 0.45, fontSize: 12 });

  figure(s, { file: ADD("fig13_dwell_time.png"), x: 7.25, y: yy + 0.05, w: 5.45, ratio: 2.50 });

  s.addNotes(
    "[두 가지 정의] ① 총 점유 시간 = 그 State 세그먼트 길이의 총합 × TR. " +
    "② 방문당 체류 시간 = 같은 State가 연속된 구간마다 길이를 재어 피험자별로 평균 × TR. " +
    "dynamic FC 문헌에서 dwell time이라 하면 보통 ②를 뜻하므로 둘 다 보고했습니다.\n\n" +
    "[해석] 연결이 가장 약한 State 1에 한 번 들어가면 평균 340초, 가장 강한 State 3은 " +
    "66초 만에 빠져나옵니다.\n\n" +
    "[표준편차가 큰 점] State 1은 340.8 ± 298.4로 편차가 매우 큽니다. 피험자 간 차이가 " +
    "크다는 뜻이므로 평균만으로 단정하면 안 됩니다.\n\n" +
    "[예상질문 — 점유율의 합이 100%인가?] 표의 값은 그 State를 방문한 피험자들만의 " +
    "평균입니다. 백분율로 바꾸면 합이 131%가 됩니다. 전체 27명 기준 실제 시간 점유율은 " +
    "State1 44.2%, State0 31.0%, State2 20.3%, State3 4.5%입니다.\n\n" +
    "[예상질문 — 시간 해상도 하한은?] 세그먼테이션의 최소 길이 제약 때문에 약 22.3초" +
    "(31 TP)입니다. 그보다 짧은 상태 전환은 원리적으로 관측되지 않습니다.");
}

{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("(5) Dwell time") });
  s.addText("(5) Dwell time 검정 결과", { placeholder: "title" });
  const yy = qa(s, {
    q: "dwell time이 state별로 다른지 ANOVA + pair별 two-sample t-test",
    a: "두 정의 모두 유의 — 총 점유 F = 6.39,  방문당 체류 F = 10.78",
    color: GREEN,
  });

  const rows = [
    ["Pair", "총 점유 t", "p", "방문당 t", "p"],
    ["State0 vs State1", "−2.256", "0.029 *", "−3.576", "0.00088 ***"],
    ["State0 vs State2", "+1.145", "0.259 n.s.", "+1.263", "0.213 n.s."],
    ["State0 vs State3", "+2.224", "0.034 *", "+1.874", "0.070 n.s."],
    ["State1 vs State2", "+3.164", "0.0030 **", "+3.764", "0.00054 ***"],
    ["State1 vs State3", "+3.308", "0.0026 **", "+2.715", "0.011 *"],
    ["State2 vs State3", "+1.493", "0.147 n.s.", "+1.044", "0.305 n.s."],
  ];
  tbl(s, rows, { x: 0.6, y: yy, w: 12.1, colW: [3.3, 2.2, 2.2, 2.2, 2.2], rowH: 0.47, fontSize: 12.5 });

  s.addNotes(
    "[ANOVA 상세] 총 점유 시간 F(3,71) = 6.392, p = 6.77e-04, η² = 0.21. " +
    "방문당 체류 시간 F(3,71) = 10.779, p = 6.39e-06, η² = 0.31. " +
    "비모수 Kruskal-Wallis에서도 동일한 결론입니다.\n\n" +
    "[해석 — 가장 중요한 포인트] 유의한 쌍은 모두 State 1이 끼어 있습니다. 즉 State 1만 " +
    "다른 State들과 체류 시간이 확실히 다르고, State 0·2·3 사이에는 유의한 차이가 없습니다. " +
    "따라서 '연결이 약할수록 오래 간다'가 아니라 'State 1만 유독 오래 간다'가 정확한 " +
    "서술입니다.\n\n" +
    "[효과크기] 방문당 체류 시간의 η²가 0.31로 총 점유 시간의 0.21보다 큽니다. " +
    "State 1이 오래 유지되는 것은 '자주 방문해서'가 아니라 '한 번 들어가면 길게 머물러서'로 " +
    "보입니다 — 방문 횟수는 1.71회로 오히려 적습니다.\n\n" +
    "[표기] * p<0.05, ** p<0.01, *** p<0.001. 보정 전 값입니다.");
}

// =============================================================================
pres.addSection({ title: "정리" });
{
  const s = pres.addSlide({ masterName: "CLOSING", ...S("정리") });
  s.addText("정리와 다음 단계", { placeholder: "title" });

  s.addText("요청 분석 결과", { x: 0.9, y: 1.75, w: 5.8, h: 0.33, fontSize: 15, bold: true,
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
    { x: 0.9, y: 2.2, w: 5.8, h: 2.8, fontSize: 13.5, isTextBox: true,
      paraSpaceAfter: 9, lineSpacingMultiple: 1.2 });

  s.addText("다음 단계", { x: 7.1, y: 1.75, w: 5.3, h: 0.33, fontSize: 15, bold: true,
    color: "97A3C9", isTextBox: true, margin: 0 });
  const next = [
    { n: 1, t: "전역 크기 통제", d: "상대 DC로 같은 검정 반복 — 100/100 중 영역 특이성 분리" },
    { n: 2, t: "민감도 분석", d: "상위 5% / 15%로 바꿔 결론이 유지되는지 확인" },
    { n: 3, t: "K=2·3 dwell time", d: "현재 K=4만 수행 — 나머지 K에도 동일 분석" },
    { n: 4, t: "움직임 교란 통제", d: "피험자별 FD 산출 → State별 FD 비교" },
  ];
  let y = 2.2;
  next.forEach((o) => {
    s.addShape(pres.ShapeType.ellipse, { x: 7.1, y: y + 0.02, w: 0.44, h: 0.44,
      fill: { color: CORAL }, line: { color: CORAL, width: 0 }, objectName: `nc-${o.n}` });
    s.addText(String(o.n), { x: 7.1, y: y + 0.02, w: 0.44, h: 0.44, align: "center",
      valign: "middle", fontSize: 14, bold: true, color: "FFFFFF", isTextBox: true, margin: 0 });
    s.addText(o.t, { x: 7.72, y, w: 4.7, h: 0.32, fontSize: 14, bold: true, color: "FFFFFF",
      isTextBox: true, margin: 0 });
    s.addText(o.d, { x: 7.72, y: y + 0.33, w: 4.7, h: 0.55, fontSize: 12, color: "A9B4D4",
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.15 });
    y += 1.13;
  });

  s.addNotes(
    "[마무리] 요청하신 다섯 항목 모두 완료했습니다.\n\n" +
    "[가장 먼저 할 것] 1번 전역 크기 통제입니다. 100개 ROI가 전부 유의하다는 결과가 " +
    "실제로 영역별 특이성인지, 아니면 전반적 연결 강도 차이인지 분리해야 " +
    "결과를 해석할 수 있습니다.\n\n" +
    "[남은 한계] 관측 독립성(한 피험자가 여러 State에 기여), State 3의 작은 표본(9명), " +
    "dwell time 시간 해상도 하한 22.3초, 머리 움직임 교란 미통제 — 네 가지입니다.\n\n" +
    "[질문 받기]");
}

// =============================================================================
pres.addSection({ title: "부록" });
{
  const s = pres.addSlide({ masterName: "CONTENT", ...S("부록") });
  s.addText("부록: 용어 정리", { placeholder: "title" });

  const terms = [
    { t: "CM (연결성 행렬)", d: "한 세그먼트 안에서 100개 ROI가 서로 얼마나 같이 움직였는지 적은 100×100 표. 각 칸 = Pearson 상관의 Fisher-Z 값", c: NAVY },
    { t: "DC (Degree Centrality)", d: "각 ROI가 자신의 가장 강한 상위 10% 연결로부터 받는 총 연결 강도. 100×1 벡터", c: NAVY },
    { t: "FC magnitude (전역 연결강도)", d: "CM에 적힌 숫자들의 전반적 크기. 누가 중심인지가 아니라 표 전체의 수위", c: TEAL },
    { t: "ANOVA / F값", d: "셋 이상 집단의 평균을 한 번에 비교. F = 집단 사이의 차이 ÷ 집단 안의 흩어짐", c: TEAL },
    { t: "FDR q", d: "100개 ROI를 각각 검정하면 차이가 없어도 5개쯤 우연히 유의하게 나온다. 이를 보정한 값", c: CORAL },
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

  s.addNotes("[부록] 발표 중에는 넘기고, 용어 질문이 나오면 돌아옵니다.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("saved:", OUT);
})();
