"""렌더러 없이 하는 PPTX QA — 슬라이드 경계 이탈 / 여백 / 텍스트 넘침 추정 / 겹침."""
import math
import sys
from pptx import Presentation
from pptx.util import Emu

DECK = sys.argv[1]
SLIDE_W, SLIDE_H = 13.333, 7.5
MARGIN = 0.5

prs = Presentation(DECK)


def inch(v):
    return Emu(v).inches if v is not None else None


def text_width_em(s):
    """글자 폭 추정: 한글/CJK = 1.0em, 그 외 = 0.52em."""
    w = 0.0
    for ch in s:
        w += 1.0 if ord(ch) > 0x1100 else 0.52
    return w


issues = []
for idx, slide in enumerate(prs.slides, start=1):
    boxes = []
    for sh in slide.shapes:
        if sh.left is None or sh.top is None:
            continue
        x, y = inch(sh.left), inch(sh.top)
        w, h = inch(sh.width) or 0, inch(sh.height) or 0
        name = sh.name or sh.shape_type
        # 1) 슬라이드 경계 이탈
        if x < -0.01 or y < -0.01 or x + w > SLIDE_W + 0.01 or y + h > SLIDE_H + 0.01:
            issues.append(f"[{idx}] 경계 이탈: {name} "
                          f"x={x:.2f} y={y:.2f} w={w:.2f} h={h:.2f} "
                          f"(right={x+w:.2f}, bottom={y+h:.2f})")
        # 2) 가장자리 여백 (슬라이드 번호 placeholder는 예외)
        if "slideNum" not in str(name) and w > 0.6 and h > 0.2:
            if x < MARGIN - 0.01 or x + w > SLIDE_W - MARGIN + 0.01:
                issues.append(f"[{idx}] 좌우 여백 부족(<0.5\"): {name} x={x:.2f} right={x+w:.2f}")
        boxes.append((name, x, y, w, h, sh))

        # 3) 텍스트 넘침 추정
        if sh.has_text_frame and len(sh.text_frame.text.strip()) > 2:
            tf = sh.text_frame
            total_lines = 0
            max_size = 0
            for para in tf.paragraphs:
                txt = "".join(r.text for r in para.runs)
                if not txt:
                    total_lines += 1
                    continue
                size = None
                for r in para.runs:
                    if r.font.size:
                        size = r.font.size.pt
                        break
                if size is None:
                    size = 14  # placeholder 상속값 미상 → 보수적 기본
                max_size = max(max_size, size)
                em_w = text_width_em(txt)
                chars_per_line = max(1.0, (w - 0.12) * 72 / size)
                total_lines += max(1, math.ceil(em_w * size / 72 / max((w - 0.12), 0.1)))
            need_h = total_lines * max_size * 1.25 / 72
            if need_h > h + 0.08:
                issues.append(f"[{idx}] 텍스트 넘침 추정: {name} "
                              f"필요 {need_h:.2f}\" > 박스 {h:.2f}\" "
                              f"(줄 {total_lines}, {max_size:.0f}pt) :: "
                              f"{tf.text[:45].replace(chr(10),' ')}")

    # 4) 겹침 (이미지/표/카드 등 비텍스트 중심으로 큰 도형끼리)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            n1, x1, y1, w1, h1, s1 = boxes[i]
            n2, x2, y2, w2, h2, s2 = boxes[j]
            ox = min(x1 + w1, x2 + w2) - max(x1, x2)
            oy = min(y1 + h1, y2 + h2) - max(y1, y2)
            if ox > 0.05 and oy > 0.05:
                a1, a2 = w1 * h1, w2 * h2
                ov = ox * oy
                # 카드 위에 텍스트를 올리는 것은 의도된 디자인 → 작은 쪽이 완전히 포함되면 통과
                contained = (x2 >= x1 - 0.02 and y2 >= y1 - 0.02 and
                             x2 + w2 <= x1 + w1 + 0.02 and y2 + h2 <= y1 + h1 + 0.02) or \
                            (x1 >= x2 - 0.02 and y1 >= y2 - 0.02 and
                             x1 + w1 <= x2 + w2 + 0.02 and y1 + h1 <= y2 + h2 + 0.02)
                if not contained and ov > 0.3 * min(a1, a2):
                    issues.append(f"[{idx}] 겹침: {n1} ↔ {n2} "
                                  f"(겹친 면적 {ov:.2f}in², 작은 도형의 {ov/min(a1,a2)*100:.0f}%)")

print(f"슬라이드 수: {len(prs.slides)}")
print(f"발견된 문제: {len(issues)}개")
for s in issues:
    print("  " + s)
