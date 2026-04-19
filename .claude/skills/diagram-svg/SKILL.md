---
name: diagram-svg
description: Generate production-quality SVG diagrams for the AI Assistant Engineering book. Use when a chapter needs a signature visual (architecture, agent, RAG pipeline, memory, flow) that goes beyond the inline `.diagram` HTML component. Output goes to `docs/assets/diagrams/*.svg` and is embedded in chapters via `![](...)` or direct `<img src>`. Validated by `rsvg-convert`.
---

# diagram-svg

이 프로젝트만의 SVG 다이어그램 생성 규칙. **Cocoon 외부 스킬을 채택하지 않고** fireworks-tech-graph 방법론을 참고해 우리 책의 톤에 맞게 정비.

## 언제 호출하나

- 챕터 대표 비주얼 (챕터당 1~2장, 한 장으로 개념 요약)
- RAG 파이프라인 · Agent 아키텍처 · Memory 계층 · Multi-agent 토폴로지
- Part 3·5·6·캡스톤의 system 다이어그램
- 인라인 `.diagram` HTML로 표현이 부족할 때

## 절대 원칙

1. **출력 경로**: `docs/assets/diagrams/<chapter-slug>-<name>.svg`
2. **ViewBox 고정**: `0 0 960 600`(default) · `0 0 960 800`(tall) · `0 0 1200 600`(wide)
3. **텍스트 오버플로 금지** — 노드 폭 안에 반드시 수납. 추산: `text.length × 7px ≤ width - 16px`
4. **화살표는 노드 가장자리에 앵커** — 중심-중심 직선 금지, 오소고날(L자) 우선
5. **색으로만 의미를 전달하지 말 것** — 라벨·모양·대시 함께 사용
6. **한국어 폰트**: Noto Sans KR 또는 Pretendard, `<style>` 블록에 `font-family` 임베드 (외부 `@import` 금지 — rsvg-convert 깨짐)
7. **생성 후 반드시 검증**: `rsvg-convert file.svg -o /dev/null` 이 에러 없이 끝나야 함

## 절차

### 1. 분류
어떤 타입인가: architecture · data-flow · flowchart · agent · memory · sequence · comparison · timeline · mind-map · UML?

### 2. 레이아웃 계획
- 레이어(층)를 먼저 정한다: 예) `User → Gateway → Agent → Tools / Memory → LLM → Output`
- 한 레이어 내 노드 수 ≤ 5. 많으면 그룹 컨테이너(dashed rect)로 묶음
- 8px 그리드 스냅 · 수평 120px · 수직 120px · 캔버스 여백 40px

### 3. Shape Vocabulary (의미-모양 매핑)

| 개념 | 모양 |
|---|---|
| User / 사용자 | 원 + 바디 선 (stick figure) 또는 라운드 rect + 👤 |
| LLM / 모델 | rounded rect + ✨/🧠 아이콘, 그라디언트 fill |
| Agent / Orchestrator | **육각형** 또는 double-border rounded rect (능동 컨트롤러 신호) |
| Memory (short-term) | rounded rect, **dashed border** (휘발성) |
| Memory (long-term) | **실린더** (DB 모양) |
| Vector Store | 실린더 + 내부 가로 3선 |
| Graph DB | 원 3개 겹침 |
| Tool / Function | rect + 🔧 또는 ⚙️ |
| API / Gateway | 육각형(single border) |
| Queue / Stream | 수평 tube(pipe) |
| Document / File | folded-corner rect (📄) |
| Browser / UI | rect + 3-dot titlebar |
| Decision | **다이아몬드** (플로우차트 전용) |
| Process | rounded rect (기본) |
| External Service | dashed border 또는 ☁️ 아이콘 |
| Data / Artifact | 평행사변형 |

### 4. Arrow Semantics

| 흐름 | 색 | stroke | dash | 의미 |
|---|---|---|---|---|
| Primary data | `#2563eb` blue | 2px | none | 주 요청/응답 경로 |
| Control / trigger | `#ea580c` orange | 1.5px | none | 시스템 간 트리거 |
| Memory read | `#059669` green | 1.5px | none | 저장소 조회 |
| Memory write | `#059669` green | 1.5px | `5,3` | 저장/기록 |
| Async / event | `#6b7280` gray | 1.5px | `4,2` | 이벤트 기반 |
| Embedding / transform | `#7c3aed` purple | 1px | none | 데이터 변환 |
| Feedback loop | `#7c3aed` purple | 1.5px (curved) | none | 반복 추론 루프 |

**2종 이상의 흐름이 공존하면 반드시 legend 포함.**

### 5. Color Palette — 반드시 **light + dark 한 쌍**으로

모든 SVG는 **라이트·다크 두 버전**을 함께 생성:
- `<slug>.svg` — light 모드용
- `<slug>-dark.svg` — dark 모드용

임베드 시 Material의 `#only-light` / `#only-dark` 앵커로 자동 스왑:

```markdown
![alt](../assets/diagrams/<slug>.svg#only-light)
![alt](../assets/diagrams/<slug>-dark.svg#only-dark)
```

#### Light 팔레트 (흰 bg, 파스텔 fill + 진한 text)

| role | fill | border(stroke) | text |
|---|---|---|---|
| input | `#e3f2fd` | `#2563eb` | `#0d47a1` |
| llm | `#fef3e0` | `#ea580c` | `#9a3412` |
| model | `#f3e8ff` | `#7c3aed` | `#4c1d95` |
| token | `#dcfce7` | `#059669` | `#064e3b` |
| gate | `#fef9c3` | `#ca8a04` | `#713f12` |
| tool | `#cffafe` | `#0891b2` | `#083344` |
| memory | `#fce7f3` | `#db2777` | `#500724` |
| error | `#fee2e2` | `#dc2626` | `#7f1d1d` |

#### Dark 팔레트 (slate-950 bg, RGBA fill + 파스텔 text)

| role | fill (rgba alpha 0.15) | stroke (bright) | text (pastel) |
|---|---|---|---|
| input | `rgba(96,165,250,0.15)` | `#60a5fa` | `#bfdbfe` |
| llm | `rgba(251,146,60,0.15)` | `#fb923c` | `#fed7aa` |
| model | `rgba(167,139,250,0.15)` | `#a78bfa` | `#ddd6fe` |
| token | `rgba(52,211,153,0.15)` | `#34d399` | `#a7f3d0` |
| gate | `rgba(251,191,36,0.15)` | `#fbbf24` | `#fde68a` |
| tool | `rgba(34,211,238,0.15)` | `#22d3ee` | `#a5f3fc` |
| memory | `rgba(244,114,182,0.15)` | `#f472b6` | `#fbcfe8` |
| error | `rgba(248,113,113,0.15)` | `#f87171` | `#fecaca` |

다크 공통 색:
- 배경: `#020617` (slate-950)
- 노드 opaque mask: `#0f172a` (slate-900)
- 그리드 선: `#1e293b` (slate-800)
- 일반 화살표: `#64748b` (slate-500)
- 일반 텍스트: `#f1f5f9` (slate-100)
- 부라벨: `#94a3b8` (slate-400)
- 레전드 bg: `#0f172a`, border `#334155`

**숫자 배지** 다크 모드에서는 text fill 을 `#020617` 로 (어두운 배경 위 밝은 배지).

### 6. 생성 방법 — Python 리스트 append (MANDATORY)

직접 `cat > file.svg` 로 쓰지 말 것. 항상 파이썬 리스트 append 방식:

```python
python3 << 'EOF'
lines = []
lines.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 600" font-family="Pretendard, -apple-system, sans-serif">')
lines.append('  <defs>')
lines.append('    <marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">')
lines.append('      <polygon points="0,0 10,3.5 0,7" fill="#6b7280"/>')
lines.append('    </marker>')
lines.append('  </defs>')
# ... 노드마다 rect + text + (선택) 아이콘
# ... 화살표마다 path with marker-end
lines.append('</svg>')

with open('docs/assets/diagrams/ch3-assistant-pipeline.svg', 'w') as f:
    f.write('\n'.join(lines))
print("✓ written")
EOF
```

**이유**: 한 줄 한 줄 검증 가능, 인용부·들여쓰기 실수 최소화. 생성 후 반드시 `rsvg-convert` 검증.

### 7. 검증 & PNG export

```bash
rsvg-convert docs/assets/diagrams/ch3-assistant-pipeline.svg -o /dev/null && echo "✓ valid"
# 선택: 1920px 와이드 PNG도 export
rsvg-convert -w 1920 docs/assets/diagrams/ch3-assistant-pipeline.svg -o docs/assets/diagrams/ch3-assistant-pipeline.png
```

### 8. 챕터에 임베드 — **light/dark 페어 필수**

```markdown
![alt](../assets/diagrams/<slug>.svg#only-light)
![alt](../assets/diagrams/<slug>-dark.svg#only-dark)
```

`#only-light` · `#only-dark`는 Material for MkDocs의 내장 앵커 — 현재 테마에 따라 자동 표시/숨김.

## SVG 세부 규칙

- **텍스트**: 최소 12px · 라벨 13~14px · 부라벨 11px · 타이틀 16~18px · 모든 text에 `text-anchor="middle"` 명시 필수
- **rect**: `rx="8"` 라운드 · `stroke-width="1.5"`
- **화살표 라벨**: `<rect fill="#ffffff" opacity="0.95">` 배경 필수, text 위에 그 rect를 먼저 깔기
- **drop shadow**: `<filter>` 정의 후 중요 노드에만 sparingly. 기본은 없음
- **legend**: viewBox 하단 여백에 배치, 경계 밖

## Validation Checklist (커밋 전)

- [ ] `rsvg-convert` 통과
- [ ] 텍스트가 노드 안에 들어감 (오버플로 없음)
- [ ] 화살표가 노드 내부를 관통하지 않음 (충돌 없음)
- [ ] 화살표 라벨에 흰색 배경 rect
- [ ] 화살표 색이 2종 이상이면 legend 존재
- [ ] 제목 · 간단한 설명 포함
- [ ] 파일명: `<chapter-slug>-<purpose>.svg`

## 고급 패턴 (Cocoon template에서 차용)

### 1. 그리드 배경 (기술적 미감)
```svg
<defs>
  <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e2e8f0" stroke-width="0.5"/>
  </pattern>
</defs>
<rect width="100%" height="100%" fill="url(#grid)"/>
```
라이트 모드는 `#e2e8f0`, 다크면 `#1e293b`. 40×40 권장.

### 2. 그룹 컨테이너 (리전·도메인·보안 그룹)

**대시 스타일 + 좌상단 라벨** — 여러 노드를 한 경계로 묶을 때:

```svg
<rect x="160" y="40" width="820" height="520" rx="12"
      fill="rgba(37, 99, 235, 0.04)"
      stroke="#2563eb" stroke-width="1" stroke-dasharray="8,4"/>
<text x="172" y="60" fill="#2563eb" font-size="11" font-weight="700">LLM Layer</text>
```

- `stroke-dasharray="8,4"`: 도메인 경계 (region, layer)
- `stroke-dasharray="4,4"`: 보안 그룹 (tighter dash)
- fill은 색상 알파 `0.04~0.08` 로 아주 희미하게

### 3. 멀티라인 컴포넌트 (리스트형)

```svg
<rect x="200" y="380" width="110" height="100" rx="8" fill="..." stroke="..."/>
<text x="255" y="400" text-anchor="middle" font-size="12" font-weight="700">S3 Buckets</text>
<text x="255" y="420" text-anchor="middle" font-size="10" fill="#64748b">• bucket-one</text>
<text x="255" y="434" text-anchor="middle" font-size="10" fill="#64748b">• bucket-two</text>
<text x="255" y="448" text-anchor="middle" font-size="10" fill="#64748b">• bucket-three</text>
<text x="255" y="466" text-anchor="middle" font-size="9" fill="#f59e0b">OAI Protected</text>
```

각 라인 간격 14~16px. 마지막 라인은 요약/상태 (색상 accent).

### 4. 곡선 경로 (인증·피드백·우회 흐름)

직선이 어색한 경우 quadratic/cubic bezier:

```svg
<path d="M 80 140 L 80 200 Q 80 220 100 220 L 200 220 Q 220 220 220 240 L 220 278"
      fill="none" stroke="#db2777" stroke-width="1.5" stroke-dasharray="5,5"/>
```

- `Q cx,cy x,y`: quadratic bezier (부드러운 코너)
- `C cx1,cy1 cx2,cy2 x,y`: cubic bezier (S-curve)
- 인증 플로우는 보통 **dashed + 곡선**

### 5. 인-다이어그램 레전드 (우상단)

외부 legend 대신 SVG 안쪽 코너에 붙이는 방식. 스페이스 절약:

```svg
<text x="720" y="70" font-size="11" font-weight="700" fill="#334155">Legend</text>
<rect x="720" y="82" width="16" height="10" rx="2" fill="..." stroke="..." stroke-width="1"/>
<text x="742" y="90" font-size="9" fill="#64748b">Frontend</text>
<!-- 한 줄당 16px 간격 -->
```

### 6. 서머리 카드 (SVG 바깥의 HTML 래퍼)

다이어그램 페이지 자체가 목적일 때 — SVG 아래 3장짜리 카드 그리드로 **핵심 포인트 요약**:

```html
<div class="diagram-page">
  <header><span class="pulse-dot"></span><h1>RAG Pipeline</h1></header>
  <div class="diagram-container"><svg>...</svg></div>
  <div class="cards">
    <div class="card"><span class="dot cyan"></span><h3>Retrieve</h3><ul><li>embedding</li>...</ul></div>
    ...
  </div>
  <p class="footer">AI Assistant Engineering · Part 3</p>
</div>
```

docs/stylesheets/extra.css 에 `.diagram-page` 클래스 예정 — 필요 시 그때 추가.

### 7. Z-order 규칙 (화살표가 노드 뒤로)

SVG는 문서 순서대로 그려짐 → **화살표를 먼저, 노드를 나중에** 그리면 화살표가 노드 뒤에 깔림 (노드 안을 관통 X).

반투명 fill 노드 뒤에 화살표가 비치는 게 싫으면: **불투명 bg rect 먼저, 반투명 styled rect 그 위에**:

```svg
<!-- 1. 연결 화살표들 (먼저) -->
<path d="M ..." ... marker-end="url(#arr)"/>

<!-- 2. 노드: 불투명 배경 → 반투명 스타일 -->
<rect x="X" y="Y" width="W" height="H" rx="8" fill="#ffffff"/>         <!-- 마스킹 -->
<rect x="X" y="Y" width="W" height="H" rx="8" fill="rgba(...,0.4)" stroke="..."/>
<text ...>Label</text>
```

---

## Lesson Learned (꼭 지킬 것)

- 🚫 **이모지 사용 금지** — rsvg-convert는 색 이모지를 검은 실루엣으로 변환. `📥 📊 ✨` 모두 깨짐.
- ✅ **숫자 배지** — `<circle fill="stroke_color"/>` + `<text fill="#fff">1</text>` 조합
- ✅ **SVG 직접 그린 심플 글리프** — 삼각형·원·사각형 조합으로 최소한의 아이콘 (선택)
- ✅ **라벨에 흰색 배경 rect** — `<rect fill="#ffffff" stroke="#e5e7eb"/>` 깔고 위에 text
- ✅ **Pretendard 또는 Noto Sans KR** — 한글 렌더링을 위해 root `font-family` 속성에 지정

## 금지 사항

- 외부 폰트 `@import` (rsvg-convert 깨짐)
- 중심-중심 직선 화살표 (오소고날 우선)
- 색으로만 의미 전달 (라벨 없이 파란색만으로 "primary"라고 하지 말 것)
- 다크 모드 대응을 한 파일에 섞기 (`-dark.svg` 별도)
- ViewBox 없는 SVG · 고정 px width/height (반응형 깨짐)
