"""Ch 3 — AI Assistant 8 블록 다이어그램 (light + dark)"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from svg_prim import (
    svg_header, svg_footer, text_title, text_subtitle,
    node, group_around_nodes, arrow_line, arrow_path,
    arrow_legend, role_legend,
    P, T,
)

CANVAS_W, CANVAS_H = 960, 620
NODE_W, NODE_H = 120, 90
NODE_GAP = 22  # horizontal gap inside row
LAYER_GAP = 30  # horizontal gap between group containers

# 6 main-row nodes in 3 layers: [1] [2 3 4] [5 6]
# Compute xs so that layers wrap nodes with equal padding
layer_sizes = [1, 3, 2]  # number of nodes per layer
PAD_X = 16  # padding inside group

def layer_inner_width(n, node_w, gap, pad):
    return n * node_w + (n - 1) * gap + 2 * pad

layer_widths = [layer_inner_width(n, NODE_W, NODE_GAP, PAD_X) for n in layer_sizes]
# widths: [152, 432, 282]
total_layers_w = sum(layer_widths) + LAYER_GAP * (len(layer_widths) - 1)
# = 152 + 432 + 282 + 60 = 926
margin_x = (CANVAS_W - total_layers_w) // 2
# margin_x = 17

# Layer x positions
layer_xs = []
cursor = margin_x
for w in layer_widths:
    layer_xs.append(cursor)
    cursor += w + LAYER_GAP

NODE_Y = 125

# Node xs (within layers)
node_xs = []
for li, (lx, n) in enumerate(zip(layer_xs, layer_sizes)):
    for i in range(n):
        node_xs.append(lx + PAD_X + i * (NODE_W + NODE_GAP))

# Verify mapping: indices 0 | 1 2 3 | 4 5

# === Specs ===
main_nodes = [
    ('input',  '1', '입력',       'intake'),
    ('llm',    '2', '이해',       'understand'),
    ('tool',   '3', '검색',       'retrieve'),
    ('llm',    '4', '생성',       'generate'),
    ('gate',   '5', '검증',       'validate'),
    ('memory', '6', '저장',       'persist'),
]

# Bottom row: 7 under center of Layer 2, 8 under center of Layer 3
# Layer 2 center = layer_xs[1] + layer_widths[1]/2
l2_center = layer_xs[1] + layer_widths[1] // 2
l3_center = layer_xs[2] + layer_widths[2] // 2

Y_BOT = 360
MON_X = l2_center - NODE_W // 2
HAN_X = l3_center - NODE_W // 2


def render(theme):
    lines = svg_header(CANVAS_W, CANVAS_H, theme)
    lines.extend(text_title(CANVAS_W // 2, 36, 'AI Assistant의 8 블록', theme))
    lines.extend(text_subtitle(CANVAS_W // 2, 58, '3개 레이어로 묶어 본 운영형 Assistant 파이프라인', theme))

    # Group containers (wrap main-row nodes)
    group_labels = [
        ('LAYER 1 · INTAKE',                'input'),
        ('LAYER 2 · REASONING (LLM + RAG)', 'llm'),
        ('LAYER 3 · SAFETY &amp; PERSIST',  'gate'),
    ]
    node_idx = 0
    for (label, role), n_count in zip(group_labels, layer_sizes):
        xs_in_group = node_xs[node_idx:node_idx + n_count]
        lines.extend(group_around_nodes(xs_in_group, NODE_Y, NODE_W, NODE_H, label, role, theme))
        node_idx += n_count

    # Main arrows (drawn BEFORE nodes)
    cy = NODE_Y + NODE_H // 2
    for i in range(len(node_xs) - 1):
        x1 = node_xs[i] + NODE_W + 2
        x2 = node_xs[i + 1] - 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))

    # === Cross-cutting arrows ===
    # 6 → 7 (logs, async)
    mem_cx = node_xs[5] + NODE_W // 2
    mon_cx = MON_X + NODE_W // 2
    mem_bot = NODE_Y + NODE_H
    via_y = Y_BOT - 30
    lines.extend(arrow_path(
        f'M {mem_cx},{mem_bot} L {mem_cx},{via_y} L {mon_cx},{via_y} L {mon_cx},{Y_BOT}',
        theme, kind='async',
        label_pos=((mem_cx + mon_cx) / 2, via_y - 10),
        label='logs',
    ))

    # 5 → 8 (escalate, curved)
    gate_cx = node_xs[4] + NODE_W // 2
    han_cx = HAN_X + NODE_W // 2
    gate_bot = NODE_Y + NODE_H
    # Quadratic bezier downward
    mid_y = (gate_bot + Y_BOT) // 2
    lines.extend(arrow_path(
        f'M {gate_cx},{gate_bot} Q {gate_cx},{mid_y} {han_cx},{Y_BOT}',
        theme, kind='escalate',
        label_pos=(gate_cx + (han_cx - gate_cx) // 2, mid_y + 15),
        label='on fail / high-risk',
    ))

    # 8 → 6 (feedback, curved right-side loop)
    han_rx = HAN_X + NODE_W
    han_ry = Y_BOT + NODE_H // 2
    mem_bx = node_xs[5] + NODE_W - 20
    loop_x = han_rx + 40
    lines.extend(arrow_path(
        f'M {han_rx},{han_ry} Q {loop_x},{han_ry} {loop_x},{(han_ry + mem_bot) / 2} Q {loop_x},{mem_bot + 15} {mem_bx},{mem_bot + 15} L {mem_bx},{mem_bot}',
        theme, kind='feedback',
        label_pos=(loop_x + 5, mem_bot + 15),
        label='feedback',
    ))

    # Main nodes (on top of arrows)
    for (x, (role, num, title, sub)) in zip(node_xs, main_nodes):
        lines.extend(node(x, NODE_Y, NODE_W, NODE_H, role, theme, num=num, title=title, sub=sub))

    # Bottom nodes
    lines.extend(node(MON_X, Y_BOT, NODE_W, NODE_H, 'tool',  theme, num='7', title='모니터링',     sub='observe'))
    lines.extend(node(HAN_X, Y_BOT, NODE_W, NODE_H, 'error', theme, num='8', title='휴먼 핸드오프', sub='escalate'))

    # Legends
    lines.extend(arrow_legend(
        720, 500,
        [('primary', 'primary'), ('async', 'async'), ('escalate', 'escalate'), ('feedback', 'feedback')],
        theme,
    ))
    lines.extend(role_legend(
        60, 500,
        [('input', '입력/사용자'), ('llm', 'LLM 호출'), ('tool', '툴/검색'),
         ('gate', '검증/게이트'), ('memory', '저장/메모리'), ('error', '에러/핸드오프')],
        theme, width=640,
    ))

    lines.extend(svg_footer())
    return '\n'.join(lines)


if __name__ == '__main__':
    BASE = str(HERE.parent / 'docs' / 'assets' / 'diagrams')
    with open(f'{BASE}/ch3-assistant-8blocks.svg', 'w') as f:
        f.write(render('light'))
    with open(f'{BASE}/ch3-assistant-8blocks-dark.svg', 'w') as f:
        f.write(render('dark'))
    print('✓ light + dark written')
