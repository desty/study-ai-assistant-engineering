"""Part 1 + about/ 의 모든 .diagram을 SVG로 변환.

산출물: docs/assets/diagrams/<slug>.svg + <slug>-dark.svg
"""
import os
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from svg_prim import (
    svg_header, svg_footer, text_title, text_subtitle,
    node, group_around_nodes, arrow_line, arrow_path,
    arrow_legend, role_legend,
    PALETTE_LIGHT, PALETTE_DARK, THEME,
)

BASE = str(HERE.parent / 'docs' / 'assets' / 'diagrams')
os.makedirs(BASE, exist_ok=True)

NODE_W, NODE_H = 140, 80
NODE_GAP = 28


def layout_centered_row(n, canvas_w, node_w, gap):
    total = n * node_w + (n - 1) * gap
    left = (canvas_w - total) // 2
    return [left + i * (node_w + gap) for i in range(n)]


def connect_row(xs, y, theme, kind='primary', label_per_arrow=None):
    out = []
    cy = y + NODE_H // 2
    for i in range(len(xs) - 1):
        x1 = xs[i] + NODE_W + 2
        x2 = xs[i + 1] - 2
        label = label_per_arrow[i] if label_per_arrow and i < len(label_per_arrow) else None
        out.extend(arrow_line(x1, cy, x2, cy, theme, kind=kind, label=label))
    return out


def save(name, light_svg, dark_svg):
    with open(f'{BASE}/{name}.svg', 'w') as f:
        f.write(light_svg)
    with open(f'{BASE}/{name}-dark.svg', 'w') as f:
        f.write(dark_svg)
    # PNG for verification
    os.system(f'rsvg-convert -w 1920 {BASE}/{name}.svg -o {BASE}/{name}.png 2>&1 | head -3')
    print(f'  ✓ {name}')


# =====================================================================
# 1. 사이트맵 (about/system.md)
# =====================================================================

def site_map(theme):
    CW, CH = 900, 260
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 38, '📚 사이트 맵', theme, size=16))  # no emoji actually
    # Remove emoji from title — use plain
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 38, '사이트 맵', theme, size=18))

    specs = [
        ('input',  '홈',      'index.md',           ''),
        ('tool',   '소개',    'about/',             '학습 시스템 · 학습 내용'),
        ('llm',    '본문 7부', 'part1 ~ part7',      '각 Part 3~6챕터'),
        ('output', '캡스톤',   'capstone',          'Self-Improving Assistant'),
    ]
    xs = layout_centered_row(len(specs), CW, NODE_W, NODE_GAP)
    y = 90
    # Arrows first
    lines.extend(connect_row(xs, y, theme, kind='primary'))
    # Nodes (with detail if present — we'll squeeze into sub for short cases)
    for x, (role, title, sub, detail) in zip(xs, specs):
        lines.extend(node(x, y, NODE_W, NODE_H + 20, role, theme, title=title, sub=sub, detail=detail))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# 2. 학습 로드맵 (about/curriculum.md) — 8 nodes, 2 rows
# =====================================================================

def roadmap(theme):
    CW, CH = 960, 300
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '7부 + 캡스톤', theme, size=18))

    row1 = [
        ('input',  'Part 1', '입문'),
        ('llm',    'Part 2', 'Python · API'),
        ('tool',   'Part 3', 'RAG'),
        ('gate',   'Part 4', '평가·추론'),
    ]
    row2 = [
        ('llm',    'Part 5', 'Agent · LangGraph'),
        ('memory', 'Part 6', '운영'),
        ('model',  'Part 7', '모델·파인튜닝'),
        ('output', '캡스톤',  'Self-Improving'),
    ]

    Y1, Y2 = 80, 190
    xs1 = layout_centered_row(4, CW, NODE_W, NODE_GAP)
    xs2 = layout_centered_row(4, CW, NODE_W, NODE_GAP)

    # Arrows row1
    lines.extend(connect_row(xs1, Y1, theme, kind='primary'))
    # Arrow row1 last → row2 first (curved down-left)
    last_x1 = xs1[-1] + NODE_W // 2
    first_x2 = xs2[0] + NODE_W // 2
    y1_bot = Y1 + NODE_H
    y2_top = Y2
    lines.extend(arrow_path(
        f'M {last_x1},{y1_bot} Q {last_x1},{(y1_bot + y2_top) / 2} {(last_x1 + first_x2) / 2},{(y1_bot + y2_top) / 2} Q {first_x2},{(y1_bot + y2_top) / 2} {first_x2},{y2_top}',
        theme, kind='primary',
    ))
    # Arrows row2
    lines.extend(connect_row(xs2, Y2, theme, kind='primary'))

    for x, (role, t, s) in zip(xs1, row1):
        lines.extend(node(x, Y1, NODE_W, NODE_H, role, theme, title=t, sub=s))
    for x, (role, t, s) in zip(xs2, row2):
        lines.extend(node(x, Y2, NODE_W, NODE_H, role, theme, title=t, sub=s))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# 3. 두 가지 접근 — Rule vs Model (part1/01-why-model.md)
# =====================================================================

def rule_vs_model(theme):
    CW, CH = 960, 390
    NW, NH = 155, 85
    GAP = 72  # 노드 간 간격 — 라벨(최대 51px)이 여유 있게 들어감

    pal = PALETTE_LIGHT if theme == 'light' else PALETTE_DARK
    t_data = THEME[theme]

    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '두 가지 접근', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '같은 입력, 다른 처리 방식', theme))

    total = 3 * NW + 2 * GAP
    LEFT = (CW - total) // 2
    xs = [LEFT + i * (NW + GAP) for i in range(3)]

    Y1, Y2 = 110, 260
    cy1 = Y1 + NH // 2
    cy2 = Y2 + NH // 2

    row1 = [
        ('input',  '사용자 메시지', 'input'),
        ('gate',   'if-else 체인', 'deterministic'),
        ('output', '결과 A',       '고정'),
    ]
    row2 = [
        ('input',  '사용자 메시지', 'input'),
        ('llm',    'LLM',         'probabilistic'),
        ('output', '결과 B',       '가변'),
    ]

    # === 1. 화살표 선만 먼저 (라벨 없이) — 노드 뒤에 깔림 ===
    for i in range(2):
        x1 = xs[i] + NW + 2
        x2 = xs[i + 1] - 2
        lines.extend(arrow_line(x1, cy1, x2, cy1, theme, kind='primary'))
        lines.extend(arrow_line(x1, cy2, x2, cy2, theme, kind='primary'))

    # === 2. 노드 ===
    for x, (role, title_t, s) in zip(xs, row1):
        lines.extend(node(x, Y1, NW, NH, role, theme, title=title_t, sub=s))
    for x, (role, title_t, s) in zip(xs, row2):
        lines.extend(node(x, Y2, NW, NH, role, theme, title=title_t, sub=s))

    # === 3. 라벨 배지 — 노드 이후에 그려서 Z-order 확보 ===
    # 첫 번째 화살표 중앙 x 위치
    mx = xs[0] + NW + GAP // 2

    for lbl, cy in [('Rule', cy1), ('Model', cy2)]:
        lw = len(lbl) * 7 + 16
        lx = mx - lw / 2
        lines.append(f'  <rect x="{lx:.1f}" y="{cy - 9}" width="{lw}" height="18" rx="4" '
                     f'fill="{t_data["label_bg"]}" stroke="{t_data["label_border"]}" stroke-width="0.8"/>')
        lines.append(f'  <text x="{mx}" y="{cy + 4}" text-anchor="middle" font-size="11" '
                     f'font-family="JetBrains Mono, monospace" '
                     f'fill="{t_data["label_text"]}">{lbl}</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# 4. 기술 선택의 계단 (part1/01-why-model.md)
# =====================================================================

def tech_ladder(theme):
    CW, CH = 960, 220
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '기술 선택의 계단', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '왼쪽 → 오른쪽으로 갈수록 비용·복잡도 ↑', theme))

    specs = [
        ('input',  '코드/규칙', 'Part 1'),
        ('llm',    'Prompt',   'Part 2'),
        ('tool',   'RAG',      'Part 3'),
        ('memory', 'Agent',    'Part 5'),
        ('model',  'Fine-tune', 'Part 7'),
    ]
    xs = layout_centered_row(len(specs), CW, 130, 22)
    y = 100
    # Arrows with 부족 labels
    for i in range(len(xs) - 1):
        x1 = xs[i] + 130 + 2
        x2 = xs[i + 1] - 2
        cy = y + NODE_H // 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary', label='부족'))
    for x, (role, t, s) in zip(xs, specs):
        lines.extend(node(x, y, 130, NODE_H, role, theme, title=t, sub=s))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# 5. 결정 흐름 (part1/01-why-model.md §10)
# =====================================================================

def decision_flow(theme):
    CW, CH = 900, 300
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '결정 흐름', theme, size=18))

    # 새 기능 → 3조건 체크 → (Yes: 모델) / (No: 코드)
    # Layout: new_feature (left) → gate (center) → two branches (right)
    NEW_X, NEW_Y = 40, 110
    GATE_X, GATE_Y = 270, 110
    YES_X, YES_Y = 540, 60
    NO_X,  NO_Y  = 540, 160

    # Arrows
    lines.extend(arrow_line(NEW_X + NODE_W, NEW_Y + NODE_H // 2,
                            GATE_X, GATE_Y + NODE_H // 2, theme, kind='primary'))
    lines.extend(arrow_line(GATE_X + NODE_W, GATE_Y + NODE_H // 2,
                            YES_X, YES_Y + NODE_H // 2, theme, kind='success', label='Yes'))
    lines.extend(arrow_line(GATE_X + NODE_W, GATE_Y + NODE_H // 2,
                            NO_X, NO_Y + NODE_H // 2, theme, kind='warning', label='No'))

    lines.extend(node(NEW_X, NEW_Y, NODE_W, NODE_H, 'input',  theme, title='새 기능', sub='problem'))
    lines.extend(node(GATE_X, GATE_Y, NODE_W, NODE_H, 'gate',   theme, title='3조건 체크', sub='decision'))
    lines.extend(node(YES_X, YES_Y, NODE_W, NODE_H, 'llm',    theme, title='모델', sub='Prompt → RAG → Agent'))
    lines.extend(node(NO_X, NO_Y,  NODE_W, NODE_H, 'output', theme, title='코드', sub='deterministic'))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# 6. 다음 토큰 한 번 생성하기 (part1/02-what-is-llm.md §3 #1)
# =====================================================================

def next_token_once(theme):
    CW, CH = 900, 240
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '다음 토큰 한 번 생성하기', theme, size=18))

    specs = [
        ('input',  '입력',       'context',     "'오늘 점심은'"),
        ('model',  'LLM',        'probability', '다음 토큰 확률'),
        ('model',  '샘플링',     'temperature', '확률에 따라 선택'),
        ('output', '다음 토큰',   'output',      "'김치찌개'"),
    ]
    xs = layout_centered_row(4, CW, NODE_W, NODE_GAP)
    y = 90
    lines.extend(connect_row(xs, y, theme, kind='primary'))
    for x, (role, t, s, d) in zip(xs, specs):
        lines.extend(node(x, y, NODE_W, NODE_H + 25, role, theme, title=t, sub=s, detail=d))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# 7. 컨텍스트 윈도우 (part1/02-what-is-llm.md §4)
# =====================================================================

def context_window(theme):
    CW, CH = 960, 260
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '컨텍스트 윈도우 = 한 번에 보이는 종이', theme, size=17))
    lines.extend(text_subtitle(CW // 2, 58, '예: 200,000 토큰', theme))

    specs = [
        ('error',  '예전 대화',        'truncated',  '잘려나감'),
        ('input',  '시스템 프롬프트',   'system',     ''),
        ('input',  '최근 대화',         'history',    ''),
        ('input',  '현재 질문',         'user',       ''),
        ('output', '응답 자리',         'assistant',  ''),
    ]
    xs = layout_centered_row(5, CW, 140, 22)
    y = 110
    lines.extend(connect_row(xs, y, theme, kind='primary'))
    for x, (role, t, s, d) in zip(xs, specs):
        lines.extend(node(x, y, 140, NODE_H + 25, role, theme, title=t, sub=s, detail=d))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# 8. hallucination (part1/02-what-is-llm.md §7)
# =====================================================================

def hallucination(theme):
    CW, CH = 900, 240
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'hallucination이 생기는 순간', theme, size=18))

    specs = [
        ('input', '질문',    'user',       "'발명가 홍길동의 대표 특허는?'"),
        ('model', '내부 상태', 'reasoning',  "'발명가+특허'에 맞을 것만 조합"),
        ('error', '확신 오답', 'hallucination', '그럴듯한 특허명 창작'),
    ]
    xs = layout_centered_row(3, CW, 240, 30)
    y = 80
    cy = y + (NODE_H + 40) // 2
    for i in range(len(xs) - 1):
        x1 = xs[i] + 240 + 2
        x2 = xs[i + 1] - 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))
    for x, (role, t, s, d) in zip(xs, specs):
        lines.extend(node(x, y, 240, NODE_H + 40, role, theme, title=t, sub=s, detail=d))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# 9. 한눈 요약 (part1/02-what-is-llm.md §13)
# =====================================================================

def llm_summary(theme):
    CW, CH = 1200, 200
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 30, 'LLM 한 번의 호출, 전체 흐름', theme, size=17))

    specs = [
        ('input',  '텍스트',       'raw input'),
        ('input',  '토큰화',       'tokenize'),
        ('gate',   '컨텍스트 체크', 'window fit?'),
        ('model',  'LLM',          'probability'),
        ('model',  '샘플링',       'temperature'),
        ('token',  '다음 토큰',     'append / loop'),
        ('output', '최종 응답',     'assistant'),
    ]
    xs = layout_centered_row(len(specs), CW, 140, 20)
    y = 75
    lines.extend(connect_row(xs, y, theme, kind='primary'))
    for x, (role, t, s) in zip(xs, specs):
        lines.extend(node(x, y, 140, NODE_H, role, theme, title=t, sub=s))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# 10. 흔한 오해 (part1/03-assistant-overview.md §1)
# =====================================================================

def common_misconception(theme):
    CW, CH = 800, 200
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '흔한 오해', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '"Assistant = 프롬프트 하나"', theme))

    specs = [
        ('input',  '사용자', 'message'),
        ('model',  'LLM',    'one call'),
        ('output', '응답',   'done'),
    ]
    xs = layout_centered_row(3, CW, NODE_W, NODE_GAP)
    y = 90
    lines.extend(connect_row(xs, y, theme, kind='primary'))
    for x, (role, t, s) in zip(xs, specs):
        lines.extend(node(x, y, NODE_W, NODE_H, role, theme, title=t, sub=s))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# 11. 각 블록의 기술 라벨 (part1/03-assistant-overview.md §4)
# =====================================================================

def tech_labels(theme):
    CW, CH = 960, 220
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '각 블록의 기술 라벨', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'CODE · MODEL · RAG · EXT', theme))

    specs = [
        ('input',  '입력',   'CODE'),
        ('llm',    '이해',   'MODEL'),
        ('tool',   '검색',   'RAG + EXT'),
        ('llm',    '생성',   'MODEL'),
        ('gate',   '검증',   'CODE + MODEL'),
        ('memory', '저장',   'EXT (DB)'),
    ]
    xs = layout_centered_row(len(specs), CW, 130, 20)
    y = 95
    # Arrows
    for i in range(len(xs) - 1):
        x1 = xs[i] + 130 + 2
        x2 = xs[i + 1] - 2
        cy = y + NODE_H // 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))
    for x, (role, t, s) in zip(xs, specs):
        lines.extend(node(x, y, 130, NODE_H, role, theme, title=t, sub=s))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Batch generate all
# =====================================================================

GENERATORS = [
    ('sitemap',              site_map),
    ('roadmap',              roadmap),
    ('rule-vs-model',        rule_vs_model),
    ('tech-ladder',          tech_ladder),
    ('decision-flow',        decision_flow),
    ('next-token-once',      next_token_once),
    ('context-window',       context_window),
    ('hallucination',        hallucination),
    ('llm-summary',          llm_summary),
    ('common-misconception', common_misconception),
    ('tech-labels',          tech_labels),
]

if __name__ == '__main__':
    for name, fn in GENERATORS:
        light = fn('light')
        dark = fn('dark')
        save(name, light, dark)
    print(f'\n✓ {len(GENERATORS)} diagrams × 2 themes written to {BASE}/')
