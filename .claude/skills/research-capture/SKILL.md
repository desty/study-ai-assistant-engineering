---
name: research-capture
description: Fetch an external URL and save a faithful summary to _research/ using this project's strict sourcing rules. Use when the user shares a link to a doc/blog/paper they want recorded for the AI Assistant Engineering book. Enforces "one page = one file" and explicit TODO for unread siblings.
---

# research-capture

AI Assistant Engineering 프로젝트의 `_research/` 아카이브 규칙을 강제하기 위한 스킬.

## 언제 호출하나

- 사용자가 "이 링크 참고해줘 / 저장해줘 / _research에 추가"라고 할 때
- 커리큘럼 평가 전에 출처를 먼저 제대로 읽어야 할 때
- 이미 있는 자료를 **추가 페이지로 확장**할 때 (새 파일 또는 기존 파일의 TODO 체크)

## 절대 원칙

1. **읽지 않은 것을 읽은 것처럼 쓰지 않는다.** 사용자의 1순위 기준.
2. **한 URL = 한 파일.** 사이트 전체를 하나로 합치지 말 것.
3. **WebFetch 결과가 AI 요약 형태일 수 있음을 항상 의식**하라. 원문과 AI 주변 지식이 섞였을 가능성을 본문에 명시.
4. **3rd-party 블로그·Medium 글을 공식 docs 내용처럼 섞지 마라.** 섞을 거면 파일을 분리하거나 출처를 문장 단위로 표시.
5. **안 읽은 형제 페이지는 TODO로 남겨라.** 다음 세션이 이어서 수집할 출발점.

## 절차

### 1. URL 확인

- 사용자가 준 URL을 그대로 사용. 임의로 "더 대표성 있는" URL로 바꾸지 말 것.
- PDF면 `curl -sL`로 다운로드 후 `pypdf`로 텍스트 추출(WebFetch는 이진 PDF 못 읽음). `_study/.venv`에 `pypdf` 설치되어 있음.
- HTML인데 "Redirecting..." 만 반환되면 WebSearch로 **대체 공식 URL**을 찾거나, 사용자에게 확인 요청.

### 2. 파일 경로 결정

- 경로: `_research/<vendor>-<topic>.md` (소문자·하이픈).
- 이미 같은 벤더 파일이 있어도 **다른 페이지면 새 파일**을 만든다. 예:
  - `langgraph-persistence.md`
  - `langgraph-overview.md`
  - `langgraph-memory.md`

### 3. frontmatter (필수 필드)

```yaml
---
title: <벤더> — <페이지 주제>
url: <실제 fetch 한 URL>
fetched: <YYYY-MM-DD>  # 사용자 currentDate 기준
source_type: university_course | vendor_engineering_guide | vendor_framework_docs | paper | blog_post
scope: <이 파일이 다루는 범위 한 줄. "공식 docs 중 <주제> 페이지 1개만" 처럼 명확히>
---
```

### 4. 본문 4섹션 (순서 고정)

```markdown
# <제목>

## 한 줄 요지
<이 자료를 한 문장으로>

## 출처 범위 (필요 시 — 범위가 좁거나 WebFetch 한계가 있을 때)
- ✅ 실제로 읽은 것: <URL / PDF / 페이지 n~m>
- ⚠️ 주의: WebFetch가 AI 요약 형태로 왔다면 명시. 원문 인용은 원 URL 재확인 필요.
- ❌ 안 읽은 것: 아래 TODO 참조.

## 이 페이지에서 확인된 내용
<소제목으로 구조화. 표·불릿 적극 활용. 추측·보충은 금지>

## 우리 커리큘럼 매핑
| <출처 요소> | AI Assistant Engineering |
|---|---|
| ... | Part N Ch M ... |

## TODO — 아직 읽지 않은 관련 페이지
- [ ] <URL 또는 페이지 이름> — <왜 다음에 읽어야 하는지>

## 시사점 (선택)
<현재 범위에서 파생 가능한 커리큘럼 결정. "이것만 봤다"는 한계 인정하며.>
```

### 5. README 인덱스 갱신

`_research/README.md`의 해당 섹션(대학 강의 / 벤더 가이드 / 논문)에 **한 줄 링크** 추가:

```markdown
- [<제목>](<파일명>.md) — <한 줄 설명, scope 한계 포함>
```

예시: `- [LangGraph — Persistence (공식 docs 1페이지)](langgraph-persistence.md) — 개념 overview 등은 아직 안 읽음`

### 6. 사용자 보고

- 무엇을 **실제로 fetch 했는지** (URL, 성공/실패)
- 어떤 부분이 **AI 요약의 불확실성**을 가지는지
- **TODO에 남긴 다음 액션**이 무엇인지

## 금지 사항

- WebSearch 스니펫과 실제 fetch 결과를 구분 없이 섞어 쓰기
- "공식 문서에 따르면..." 이라고 써놓고 실제로는 Medium 글을 참고한 경우
- 한 파일에 여러 URL의 내용을 출처 표시 없이 합치기
- TODO 섹션 없이 파일을 마감하기 (단일 페이지·정적 PDF처럼 전체를 다 읽은 경우는 예외 — 그 경우에도 "모두 읽음"이라고 명시)
- 파일 생성 후 README 인덱스 갱신 누락

## 예시 — 이미 적용된 파일

- [_research/openai-practical-guide-to-agents.md](../../../../_research/openai-practical-guide-to-agents.md) — 전체 PDF 34p를 읽어 완결형
- [_research/langgraph-persistence.md](../../../../_research/langgraph-persistence.md) — 1페이지만 읽고 TODO로 경계 표시
