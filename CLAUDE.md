# AI Assistant Engineering — 프로젝트 가이드

> 다음 세션의 Claude에게 남기는 인계 문서. 이 파일은 자동 로드됨.

## 0. 한 줄 요약

**초보 → 엔터프라이즈급 AI Assistant 개발/운영**을 목표로 하는 책형 학습 사이트. MkDocs Material로 빌드, GitHub Pages 배포 예정. 저자(`desty`)가 학습 내용을 구조화해 공개하는 용도.

## 1. 프로젝트 정체성

- **사이트 제목**: AI Assistant Engineering
- **부제**: RAG, Agents, Evaluation, and Production LLM Systems
- **대상**: Assistant·업무자동화·RAG를 만들어야 하는 개발자, PM, 플랫폼·백엔드 엔지니어
- **철학**: "모델을 깊게 파기 전에 **Prompt / RAG / Agent / 평가 / 운영**을 구조로 이해하게 만든다"
- **진행 방식**: 개념 30% / 실습 50% / 리뷰 20%
- **완주 후 성과물**: Self-Improving Assistant 캡스톤 1개

## 2. 디렉토리 구조

```
_study/
├── CLAUDE.md                    ← 이 파일 (자동 로드)
├── mkdocs.yml                   ← 사이트 설정
├── requirements.txt             ← mkdocs-material 등
├── .venv/                       ← 로컬 빌드용
├── .gitignore
├── .github/workflows/deploy.yml ← GitHub Pages 자동 배포
├── .claude/skills/              ← 프로젝트 로컬 스킬
│   ├── diagram-svg/             ← SVG 다이어그램 생성 규칙
│   └── research-capture/        ← 외부 자료 저장 규칙
├── _tools/                      ← 🆕 Python 유틸 (diagram 제너레이터)
│   ├── svg_prim.py              ← 공용 primitives (node/arrow/group/legend)
│   ├── gen_ch3_8blocks.py       ← Ch 3 다이어그램
│   └── gen_part1_diagrams.py    ← Part 1 + about/ 11개 일괄 생성
├── docs/                        ← 공개되는 책 본문
│   ├── index.md
│   ├── stylesheets/extra.css    ← .diagram 컴포넌트 · infocards 정의
│   ├── javascripts/mathjax.js
│   ├── about/
│   │   ├── system.md            ← 학습 시스템 (사이트 설계·챕터 템플릿)
│   │   └── curriculum.md        ← 학습 내용 (Part 1~7 목차)
│   ├── assets/diagrams/         ← 챕터 대표 SVG (diagram-svg 스킬 출력)
│   ├── part1/                   ← ✅ 본문 완성
│   │   ├── 01-why-model.md
│   │   ├── 02-what-is-llm.md
│   │   └── 03-assistant-overview.md
│   ├── part2/ ~ part7/          ← 스텁 (본문 집필 전, Draft 표시)
│   └── capstone/
│       └── self-improving.md    ← 스텁
├── _plans/                      ← 🆕 집필 계획 · 이어하기 용 (비공개)
│   ├── README.md                ← 전체 상태 대시보드
│   ├── writing-log.md           ← 세션별 작업 로그
│   ├── part2-plan.md ~ part7-plan.md
│   └── capstone-plan.md
└── _research/                   ← 참고자료 아카이브 (비공개)
    ├── README.md
    ├── stanford-cs329a.md · stanford-cme295.md
    ├── anthropic-building-effective-agents.md
    ├── openai-practical-guide-to-agents.md
    ├── langgraph-persistence.md
    └── cocoon-architecture-diagram-skill.md  ← 검토만·미채택
```

## 3. 로컬 개발

```bash
.venv/bin/mkdocs serve -a 127.0.0.1:8765   # 자동 리로드 개발 서버
.venv/bin/mkdocs build --strict            # 링크·빌드 검증
```

`--strict`로 경고 없이 빌드되는 걸 배포 조건으로 삼는다. 새 의존성 추가 시 `requirements.txt` 업데이트.

## 4. 집필 컨벤션 (반드시 지킬 것)

### 챕터 템플릿 (8단계)
1. 개념 설명
2. 왜 필요한가
3. 어디에 쓰이는가
4. 최소 예제
5. 실전 튜토리얼
6. 자주 깨지는 포인트
7. 운영 시 체크할 점
8. 연습문제

한 챕터 = **20~40분** 분량. 다이어그램을 **첫 스크롤 안**에 배치.

### 코드 블록
- ` ```python title="파일명.py" linenums="1" hl_lines="6 10"`
- 설명은 `# (1)!` 주석 앵커 + 코드 아래 번호 리스트로 툴팁
- 한 블록 40줄 상한

### 시각화 — 단일 체계 (SVG)

이 책은 **Mermaid도 `.diagram` HTML도 쓰지 않는다**. 모든 흐름 다이어그램은 **SVG 페어** (light + dark) 로.

세 가지 도구로 전체를 커버:

1. **시퀀스·스텝** → 마크다운 **표**
2. **비교·요약 카드** → **`.infocards`** (extra.css에 정의)
3. **모든 다이어그램** → **`diagram-svg` 스킬** (`.claude/skills/diagram-svg/SKILL.md`) — Python 제너레이터 → SVG 페어 → `![](...#only-light/dark)` embed

**소스 체인**:
```
_tools/gen_*.py  (Python 제너레이터 · 편집 가능)
    ↓
docs/assets/diagrams/*.svg  (책에 embed 되는 것)
    ↓  rsvg-convert -w 1920 
docs/assets/diagrams/*.png  (verification only · git 제외)
```

공용 primitives는 **`_tools/svg_prim.py`**: `svg_header`, `node`, `arrow_line`, `arrow_path`, `group_around_nodes`, `arrow_legend`, `role_legend` 등. 새 다이어그램 추가 시 `_tools/gen_<주제>.py` 만들어 import해 사용.

**Cocoon AI · Mermaid 미채택** — 우리 책 톤에 맞게 `diagram-svg` 직접 운영.

### SVG 생성 Lesson Learned

- **이모지(📥 📊 ✨) 쓰지 말 것** — rsvg-convert는 색 이모지를 검은 실루엣으로만 렌더.
- 대신: **숫자 배지**(solid circle + 숫자) 또는 SVG로 직접 그린 심플 글리프.
- 폰트는 root `font-family` 속성에 직접 (Pretendard) — 외부 `@import` 금지.
- XML 특수 문자 이스케이프: `&` → `&amp;`
- 생성 후 반드시 `rsvg-convert -w 1920 file.svg -o file.png` 로 PNG export 검증.
- **반드시 light + dark 두 버전 생성** — `<slug>.svg` + `<slug>-dark.svg`.
- 임베드는 `![alt](path.svg#only-light)` + `![alt](path-dark.svg#only-dark)` 페어.
- **라벨은 화살표 위(-18px offset)**에 — 노드 사각형에 가려지지 않게.
- **그룹 컨테이너는 포함 노드 경계 + 패딩으로 계산** — 고정 좌표 박기 금지. `group_around_nodes` 헬퍼 사용.

### SVG role 클래스 (9종, light/dark 팔레트)

`_tools/svg_prim.py` 의 `PALETTE_LIGHT` / `PALETTE_DARK` 참고. role 문자열을 `node(..., role='X', ...)` 로 전달.

| role | 용도 | light stroke | dark stroke |
|---|---|---|---|
| `input` | 입력/컨텍스트/사용자 | `#2563eb` | `#60a5fa` |
| `model` | LLM 내부 처리 | `#7c3aed` | `#a78bfa` |
| `llm` | LLM 호출 (에이전트 맥락) | `#ea580c` | `#fb923c` |
| `token` | 토큰·중간 산출물 | `#059669` | `#34d399` |
| `output` | 최종 출력 | `#059669` | `#34d399` |
| `gate` | 검증·게이트·결정 | `#ca8a04` | `#fbbf24` |
| `tool` | 외부 툴·API | `#0891b2` | `#22d3ee` |
| `memory` | 메모리·저장소 | `#db2777` | `#f472b6` |
| `error` | 에러·핸드오프 | `#dc2626` | `#f87171` |


### 표
- 개념 4~7개 비교 시에만
- 첫 열은 **용어/이름**, 마지막 열은 **왜 중요한가**

### ASCII art 정렬 금지 🚫
- `↑` · `|` · 공백으로 **문자를 세로로 맞추는 의사(pseudo) 다이어그램을 쓰지 말 것.**
- 이유: **한글 · 영문 · 이모지 · 문장부호의 렌더링 너비가 전부 다름.** 코드블록(monospace)에서도 깨지고, 본문(proportional)에서는 더 심하게 깨짐. 사용자 폰트·브라우저·OS마다 결과가 다름.
- 대신:
  - **2차원 관계**(원문 ↔ 분리 ↔ 라벨) → **표(table)**
  - **흐름·화살표·계층** → **`.diagram`** 또는 **SVG**
  - **강조가 필요한 단일 줄** → 인라인 코드 또는 `<mark>`
- 판별법: "이 블록이 깨지면 의미가 안 전달되는가?" → Yes면 표·`.diagram`·SVG로.

## 5. 커리큘럼 상태 (2026-04-18)

### v2 확정 (2026-04-18)
- **Part 1**. 입문 — 3장 (임베딩 챕터는 Part 3로 이동)
- **Part 2**. Python으로 LLM 다루기 — 5장 (스트리밍·UX 신설)
- **Part 3**. RAG — 6장 (임베딩 이동 · Advanced RAG 신설 · 멀티모달 절)
- **Part 4**. 평가·추론·디버깅 — 5장 (LLM-as-Judge · 추론 품질 신설)
- **Part 5**. Agent & LangGraph — 6장 (Agent 패턴 · Agent 메모리 신설)
- **Part 6**. 운영형 AI Assistant — 5장 (가드레일 7종 · 비용·지연 최적화 신설)
- **Part 7**. 모델 & 파인튜닝 — 4장
- **캡스톤**. Self-Improving Assistant

총 **34챕터**. 14주 본과정(Part 1~6) · 전체 16–18주. 전체 목차는 [docs/about/curriculum.md](docs/about/curriculum.md).

### v2 반영 완료된 결정
`_research/` 기반 평가에서 드러났던 공백들 — 모두 v2에 반영:

- [x] Chapter 임베딩 Part 1 → Part 3 이동 (Ch 10)
- [x] 추론(Reasoning) 전담 챕터 (Part 4 Ch 18)
- [x] Agent 메모리 챕터 (Part 5 Ch 24)
- [x] LLM-as-Judge 챕터 (Part 4 Ch 17)
- [x] 가드레일 7종 챕터 (Part 6 Ch 28)
- [x] 비용·지연 최적화 챕터 (Part 6 Ch 30)
- [x] 스트리밍·UX 챕터 (Part 2 Ch 7)
- [x] Advanced RAG 챕터 (Part 3 Ch 13)
- [x] 멀티모달 RAG 절 (Part 3 Ch 14)

### v2 이후 진행 상태
- [x] Part 1 3챕터 초안 완성
- [x] **스켈레톤 완성** — Part 2~7 + 캡스톤 총 32개 스텁 + 각 Part plan 문서 생성 (2026-04-18)
- [ ] **Part 1 검수** — 문장·예제·다이어그램 보강 (다음 작업)
- [ ] **Part 2 본문 집필** (그 다음)
- [ ] Part 3~7 본문
- [ ] 캡스톤 상세 설계
- [ ] 14주 운영표 SVG 타임라인

## 5-1. 집필 계획 & 이어하기 (`_plans/`)

작업이 중간에 끊겨도 이어지게 하는 허브.

- **[`_plans/README.md`](_plans/README.md)** — 전체 진행 대시보드. **세션 시작 시 첫 번째로 읽을 곳**.
- **[`_plans/writing-log.md`](_plans/writing-log.md)** — 세션별 작업 기록. 매 세션 종료 전 갱신.
- **[`_plans/partN-plan.md`](_plans/)** — Part별 학습 목표·챕터별 계획·열린 결정·집필 순서·원전 참고.
- **[`_plans/capstone-plan.md`](_plans/capstone-plan.md)** — 캡스톤 설계.

**규칙**:
1. 챕터 하나 완성할 때마다 해당 `partN-plan.md` 의 status 갱신
2. 세션 끝날 때 `writing-log.md` 에 한 줄 추가
3. 본문 집필 중 **열린 결정**이 생기면 plan 파일 상단에 기록

## 6. 참고자료 아카이브 규칙 (`_research/`)

**절대 원칙**: 읽지 않은 것을 읽은 것처럼 쓰지 말 것. 사용자(desty)가 이걸 최우선으로 본다.

- **한 페이지 = 한 파일**. 파일명은 출처+주제로.
- frontmatter에 `url`, `fetched`(YYYY-MM-DD), `source_type`, `scope` 필수.
- 본문 4섹션: ① 한 줄 요지 ② 이 페이지에서 확인된 내용 ③ 우리 커리큘럼 매핑 ④ TODO(안 읽은 페이지 목록)
- **AI WebFetch 요약의 한계를 명시**하라 — 원문과 AI 주변 지식이 섞였을 수 있음.
- 3rd-party 블로그·Medium·요약글은 출처 표시 없이 섞지 말 것.

자세한 규칙과 템플릿은 `.claude/skills/research-capture/SKILL.md`에 있음. 새 자료 추가 시 그 스킬을 호출.

## 7. 사용자(desty) 협업 스타일

- **솔직함을 최우선** — "제대로 검토했냐"는 질문이 여러 번 나왔음. 과장·추정·허위 작업 완료 보고 절대 금지.
- **판단을 맡겨 달라** — 좋다/나쁘다/어디가 약하다를 분명히. "괜찮아 보입니다" 류는 거부됨.
- **계획부터 보자는 요청이 많음** — 구현 전에 구조·선택지·트레이드오프를 먼저 제시.
- **한국어**로 응답.
- Auto mode로 자주 돌림 — 작업은 자율적으로, 단 파괴적 작업·외부 공유는 확인.

## 8. 배포

- **GitHub Actions 워크플로우 준비 완료**: `.github/workflows/deploy.yml` — `main` 브랜치 push 또는 수동 실행 시 MkDocs 빌드 후 Pages 배포.
- 최신 방식 사용: `actions/upload-pages-artifact@v3` + `actions/deploy-pages@v4` (gh-pages 브랜치 방식 아님).
- **사용자가 해야 할 일** (아직 안 됨):
  1. GitHub에 레포지토리 생성 (예: `ai-assistant-engineering`)
  2. 로컬에서 `git init && git remote add origin ...` 후 첫 커밋·푸시
  3. 레포 Settings → Pages → Source를 **"GitHub Actions"** 로 설정
  4. 첫 푸시로 워크플로우 트리거
  5. 배포 후 `mkdocs.yml`의 `site_url`을 실제 URL로 업데이트

## 9. 세션 시작 시 해야 할 일

1. 이 파일 + `docs/about/curriculum.md` + `docs/about/system.md` 읽기.
2. `_research/README.md`로 현재 아카이브 상태 파악.
3. "§5 남은 설계 결정"에서 뭘 건드릴지 사용자와 합의.
4. 새 웹 자료를 받을 땐 **research-capture 스킬**을 호출해 규칙대로 저장.
