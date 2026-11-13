# 발표 자료 생성 스크립트

세션 스크래치패드에 있던 생성 스크립트를 프로젝트로 옮긴 것입니다.

## 준비

```bash
cd scripts/deck
npm install pptxgenjs          # node_modules 생성
export NODE_PATH="$PWD/node_modules"
```

`build_*.js`는 pptx 스킬의 `apply_theme.js`를 절대경로로 참조합니다.
스킬 경로가 바뀌면 각 파일 상단의 `require(...)` 경로를 고쳐야 합니다.

## 스크립트

| 파일 | 산출물 | 비고 |
|---|---|---|
| `build_qa_deck.js` | `강기호 연구 정리 ppt.pptx` (36장) | **현재 사용 중인 메인 덱** |
| `build_deck.js` | `V4_연구결과_발표.pptx` (18장) | 삭제된 덱 — 재생성 가능 |
| `build_req_deck.js` | `요청분석_결과_발표.pptx` (21장) | 삭제된 덱 — 재생성 가능 |
| `build_present.js` | `요청분석_발표용.pptx` (19장) | 삭제된 덱 — 재생성 가능 |
| `build_khbm.py` | `KHBM_2025_abstract_GihoKang.docx` | 초록 (국문·영문) |
| `qa_deck.py` | — | 경계 이탈·여백·겹침·텍스트 넘침 검사 |

```bash
NODE_PATH="$PWD/node_modules" node build_qa_deck.js
/opt/anaconda3/envs/giho/bin/python qa_deck.py "../../강기호 연구 정리 ppt.pptx"
```

## 주의

- 재생성은 기존 pptx를 **덮어씁니다**. PowerPoint에서 직접 고친 서식·위치는 복원되지 않습니다.
- 이 환경에는 LibreOffice·pdftoppm이 없어 슬라이드를 렌더링해 눈으로 볼 수 없습니다.
  대신 `qa_deck.py`로 기하 검사만 합니다.

## 초록 현행본 위치 (2026-10-22 기준)

`build_khbm.py`가 만드는 `KHBM_2025_abstract_GihoKang.docx`는 **구버전**입니다.
검토 피드백을 반영한 현행본은 `~/Downloads/abstract_GihoKang.docx`이며,
`apply_review.py`가 그 파일을 제자리에서 수정합니다(실행 시 `_수정전백업.docx` 자동 생성).
