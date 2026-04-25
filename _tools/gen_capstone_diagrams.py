"""캡스톤 다이어그램 제너레이터 — Self-Improving Assistant.

- capstone-self-improving-loop: 사용자→Assistant→피드백→분류기→DPO→재학습→배포 폐쇄 루프
- capstone-architecture: Part 1~7 모듈이 통합된 아키텍처 한 장
"""
import os
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from svg_prim import (
    svg_header, svg_footer, text_title, text_subtitle,
    node, arrow_line, arrow_path,
    group_container, group_around_nodes,
    P, T,
)

BASE = str(HERE.parent / 'docs' / 'assets' / 'diagrams')
os.makedirs(BASE, exist_ok=True)


def save(name, light_svg, dark_svg):
    with open(f'{BASE}/{name}.svg', 'w') as f:
        f.write(light_svg)
    with open(f'{BASE}/{name}-dark.svg', 'w') as f:
        f.write(dark_svg)
    os.system(f'rsvg-convert -w 1920 {BASE}/{name}.svg -o {BASE}/{name}.png 2>&1 | head -3')
    print(f'  ✓ {name}')


# =====================================================================
# Capstone 1: Self-improving closed loop
# =====================================================================

def self_improving_loop(theme):
    CW, CH = 1240, 660
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Self-Improving Assistant — 폐쇄 루프', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '사용자 피드백이 평가셋이 되고, 평가셋이 학습 데이터가 되고, 학습이 다시 사용자에게로.', theme))

    pal = P(theme)
    t = T(theme)

    # 7 nodes arranged in a circle/oval
    # Top row: User · Assistant · Feedback
    # Right: Failure Classifier
    # Bottom row: DPO Data · Retrain · Eval Gate
    # Left: New Adapter · Deploy
    NW, NH = 150, 80

    # Layout (oval)
    cx, cy = CW / 2, CH / 2 - 20
    rx, ry = 480, 200

    nodes_def = [
        ('input',  '① User',          'feedback 👍👎',     0,    'Part 6 Ch 29'),
        ('llm',    '② Assistant',      'RAG + Agent',       1,    'Part 3·5'),
        ('memory', '③ Trace + Log',    'trace_id · score', 2,    'Part 6 Ch 27'),
        ('gate',   '④ Failure Classifier', 'taxonomy 5 · Judge', 3, 'Part 4 Ch 17·19'),
        ('token',  '⑤ DPO Data',       '(✓, ✗) 쌍 생성',     4,   'Part 7 Ch 34'),
        ('output', '⑥ Retrain (LoRA)', '주간 스케줄',         5,   'Part 7 Ch 33'),
        ('output', '⑦ Eval Gate',      'baseline + Δ',      6,   'Part 4 Ch 16'),
        ('tool',   '⑧ Deploy',         'adapter swap',       7,   'Part 6 Ch 26·30'),
    ]
    n = len(nodes_def)
    import math
    positions = []
    for i in range(n):
        ang = -math.pi/2 + 2*math.pi*i/n  # start at top, go clockwise
        x = cx + rx * math.cos(ang) - NW/2
        y = cy + ry * math.sin(ang) - NH/2
        positions.append((x, y))

    # Draw arrows first (under nodes)
    for i in range(n):
        x1c = positions[i][0] + NW/2
        y1c = positions[i][1] + NH/2
        x2c = positions[(i+1) % n][0] + NW/2
        y2c = positions[(i+1) % n][1] + NH/2
        # Use a curve through center side (slight arc)
        # Compute control point pulled toward center
        mx, my = (x1c + x2c) / 2, (y1c + y2c) / 2
        # Pull toward center for inward curve
        ctrl_x = mx + (cx - mx) * 0.2
        ctrl_y = my + (cy - my) * 0.2
        kind = 'success' if i == n - 1 else 'primary'
        lines.extend(arrow_path(
            f'M {x1c} {y1c} Q {ctrl_x} {ctrl_y} {x2c} {y2c}',
            theme, kind=kind,
        ))

    # Draw nodes
    for i, (role, title, sub, _, ref) in enumerate(nodes_def):
        x, y = positions[i]
        lines.extend(node(x, y, NW, NH, role, theme, title=title, sub=sub))
        # Reference label below
        lines.append(f'  <text x="{x + NW/2}" y="{y + NH + 14}" text-anchor="middle" font-size="10" font-family="JetBrains Mono, monospace" fill="{t["legend_text"]}">{ref}</text>')

    # Center label
    lines.append(f'  <text x="{cx}" y="{cy - 6}" text-anchor="middle" font-size="20" font-weight="700" fill="{t["title"]}">Self-Improving</text>')
    lines.append(f'  <text x="{cx}" y="{cy + 16}" text-anchor="middle" font-size="20" font-weight="700" fill="{t["title"]}">Loop</text>')
    lines.append(f'  <text x="{cx}" y="{cy + 42}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{t["subtitle"]}">분기 1회 · 평가셋 통과 시만 배포</text>')

    # Bottom tip
    lines.append(f'  <rect x="40" y="{CH - 35}" width="{CW-80}" height="22" rx="4" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')
    lines.append(f'  <text x="{CW/2}" y="{CH - 19}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">루프가 닫히는 것이 핵심. 한 단계만 빠져도 자기 개선이 정지한다.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Capstone 2: Integrated architecture — Part 1~7 mapping
# =====================================================================

def integrated_architecture(theme):
    CW, CH = 1240, 600
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '캡스톤 통합 아키텍처 — Part 1~7 한 장', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '본 챕터들의 모든 조각이 하나의 시스템에 들어간다. 각 모듈이 어느 챕터에서 왔는지 추적 가능.', theme))

    pal = P(theme)
    t = T(theme)

    # 4 horizontal lanes: Serving · Knowledge/Agent · Eval/Feedback · Training
    LANE_LEFT = 60
    LANE_W = 1120
    LANE_H = 110
    GAP = 16
    Y0 = 90

    lanes = [
        {
            'role': 'input', 'name': 'SERVING',
            'modules': [
                ('input',  'API Gateway',    'FastAPI · async',      'Ch 26'),
                ('gate',   'Guardrails 7',   'in/tool/out',          'Ch 28'),
                ('memory', 'Session Store',  'Redis · TTL',          'Ch 26'),
                ('error',  'Approval Queue', 'high-risk',            'Ch 29'),
            ],
        },
        {
            'role': 'llm', 'name': 'AGENT',
            'modules': [
                ('llm',    'LangGraph',      'state · interrupt',    'Ch 23'),
                ('tool',   'Tools (ACI)',    'data/action/orch',     'Ch 22'),
                ('memory', 'Memory',         'thread + store',       'Ch 24'),
                ('model',  'Model Router',   'Haiku/Sonnet/Opus',    'Ch 30'),
            ],
        },
        {
            'role': 'tool', 'name': 'KNOWLEDGE',
            'modules': [
                ('tool',   'Hybrid Retrieval', 'BM25 + dense',       'Ch 12'),
                ('tool',   'Reranker',         'cross-encoder',       'Ch 12'),
                ('memory', 'Vector Store',     'Chroma · meta',       'Ch 10·11'),
                ('token',  'Citation',         'XML 경계',           'Ch 11'),
            ],
        },
        {
            'role': 'token', 'name': 'EVAL · LEARN',
            'modules': [
                ('token',  'Trace + Logs',     'trace_id · cost',     'Ch 27'),
                ('gate',   'Failure Classifier', '5 layer · Judge',   'Ch 17·19'),
                ('output', 'Eval Set',         'gold + regression',   'Ch 16'),
                ('output', 'LoRA / DPO',       'adapter · 주간',       'Ch 33·34'),
            ],
        },
    ]

    MOD_W = 240
    MOD_H = 70

    for li, lane in enumerate(lanes):
        ly = Y0 + li * (LANE_H + GAP)
        # Lane container
        lines.extend(group_container(LANE_LEFT, ly, LANE_W, LANE_H, lane['name'], lane['role'], theme))
        # 4 modules per lane
        mod_gap = (LANE_W - 4 * MOD_W - 60) // 3
        for mi, (mrole, mtitle, msub, mref) in enumerate(lane['modules']):
            mx = LANE_LEFT + 30 + mi * (MOD_W + mod_gap)
            my = ly + (LANE_H - MOD_H) // 2 + 6
            # Module card (compact)
            lines.append(f'  <rect x="{mx}" y="{my}" width="{MOD_W}" height="{MOD_H}" rx="8" fill="{pal[mrole]["fill"]}" stroke="{pal[mrole]["stroke"]}" stroke-width="1.3"/>')
            lines.append(f'  <text x="{mx + 14}" y="{my + 22}" font-size="13" font-weight="700" fill="{pal[mrole]["text"]}">{mtitle}</text>')
            lines.append(f'  <text x="{mx + 14}" y="{my + 40}" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal[mrole]["sub"]}">{msub}</text>')
            # Right-aligned chapter ref
            lines.append(f'  <text x="{mx + MOD_W - 14}" y="{my + 60}" text-anchor="end" font-size="10" font-family="JetBrains Mono, monospace" fill="{t["legend_text"]}">{mref}</text>')

    # Side feedback arrow (closing loop) — from Eval/Learn lane back up to Agent (model router · prompt registry)
    fy_start = Y0 + 3 * (LANE_H + GAP) + LANE_H/2
    fy_end = Y0 + LANE_H/2
    fx = LANE_LEFT + LANE_W + 16
    lines.extend(arrow_path(
        f'M {fx - 16} {fy_start} L {fx + 12} {fy_start} L {fx + 12} {fy_end} L {fx - 16} {fy_end}',
        theme, kind='feedback', label='주간 학습 → 새 adapter 배포',
        label_pos=(fx + 100, (fy_start + fy_end) / 2),
    ))

    # Bottom tip
    lines.append(f'  <rect x="40" y="{CH - 35}" width="{CW-80}" height="22" rx="4" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')
    lines.append(f'  <text x="{CW/2}" y="{CH - 19}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">한 모듈 = 한 챕터로 추적 가능. 전체 챕터를 다 쓰지 않아도 캡스톤은 가능 — 단 루프는 닫혀야 한다.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# main
# =====================================================================

def main():
    print('Capstone diagrams:')
    for name, fn in [
        ('capstone-self-improving-loop', self_improving_loop),
        ('capstone-architecture', integrated_architecture),
    ]:
        save(name, fn('light'), fn('dark'))


if __name__ == '__main__':
    main()
