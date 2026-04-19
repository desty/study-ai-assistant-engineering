"""SVG diagram primitives for the AI Assistant Engineering book.

사용법:
    from svg_prim import render_diagram

    spec = {
        "viewbox": (960, 420),
        "title": "...",
        "subtitle": "...",
        "groups": [...],
        "nodes": [...],
        "arrows": [...],
        "arrow_legend": [...],
        "role_legend": [...],
    }
    light_svg = render_diagram(spec, theme="light")
    dark_svg  = render_diagram(spec, theme="dark")

Role 팔레트는 .diagram 컴포넌트와 통일: input/llm/model/token/gate/tool/memory/error/output.
모든 수치는 명시. 노드 width는 기본 120, height 90. 한 SVG 안에서 같은 크기 유지.
"""

# =====================================================================
# Palettes
# =====================================================================

PALETTE_LIGHT = {
    'input':  {'fill': '#e3f2fd', 'stroke': '#2563eb', 'text': '#0d47a1', 'sub': '#1e40af'},
    'llm':    {'fill': '#fef3e0', 'stroke': '#ea580c', 'text': '#9a3412', 'sub': '#c2410c'},
    'model':  {'fill': '#f3e8ff', 'stroke': '#7c3aed', 'text': '#4c1d95', 'sub': '#6d28d9'},
    'token':  {'fill': '#dcfce7', 'stroke': '#059669', 'text': '#064e3b', 'sub': '#047857'},
    'output': {'fill': '#d1fae5', 'stroke': '#059669', 'text': '#064e3b', 'sub': '#047857'},
    'gate':   {'fill': '#fef9c3', 'stroke': '#ca8a04', 'text': '#713f12', 'sub': '#a16207'},
    'tool':   {'fill': '#cffafe', 'stroke': '#0891b2', 'text': '#083344', 'sub': '#0e7490'},
    'memory': {'fill': '#fce7f3', 'stroke': '#db2777', 'text': '#500724', 'sub': '#be185d'},
    'error':  {'fill': '#fee2e2', 'stroke': '#dc2626', 'text': '#7f1d1d', 'sub': '#b91c1c'},
}

PALETTE_DARK = {
    'input':  {'fill': 'rgba(96,165,250,0.15)',  'stroke': '#60a5fa', 'text': '#bfdbfe', 'sub': '#60a5fa'},
    'llm':    {'fill': 'rgba(251,146,60,0.15)',  'stroke': '#fb923c', 'text': '#fed7aa', 'sub': '#fb923c'},
    'model':  {'fill': 'rgba(167,139,250,0.15)', 'stroke': '#a78bfa', 'text': '#ddd6fe', 'sub': '#a78bfa'},
    'token':  {'fill': 'rgba(52,211,153,0.15)',  'stroke': '#34d399', 'text': '#a7f3d0', 'sub': '#34d399'},
    'output': {'fill': 'rgba(52,211,153,0.2)',   'stroke': '#34d399', 'text': '#a7f3d0', 'sub': '#34d399'},
    'gate':   {'fill': 'rgba(251,191,36,0.15)',  'stroke': '#fbbf24', 'text': '#fde68a', 'sub': '#fbbf24'},
    'tool':   {'fill': 'rgba(34,211,238,0.15)',  'stroke': '#22d3ee', 'text': '#a5f3fc', 'sub': '#22d3ee'},
    'memory': {'fill': 'rgba(244,114,182,0.15)', 'stroke': '#f472b6', 'text': '#fbcfe8', 'sub': '#f472b6'},
    'error':  {'fill': 'rgba(248,113,113,0.15)', 'stroke': '#f87171', 'text': '#fecaca', 'sub': '#f87171'},
}

# Canvas / neutral colors per theme
THEME = {
    'light': {
        'bg': '#ffffff',
        'grid': '#f1f5f9',
        'node_mask': '#ffffff',
        'arrow': '#6b7280',
        'arrow_dark': '#4b5563',
        'title': '#0f172a',
        'subtitle': '#64748b',
        'legend_bg': '#f8fafc',
        'legend_border': '#e2e8f0',
        'legend_text': '#334155',
        'label_bg': '#ffffff',
        'label_border': '#e5e7eb',
        'label_text': '#475569',
        'badge_num_fill': '#ffffff',
        'group_fill_alpha': 0.04,
    },
    'dark': {
        'bg': '#020617',
        'grid': '#1e293b',
        'node_mask': '#0f172a',
        'arrow': '#64748b',
        'arrow_dark': '#94a3b8',
        'title': '#f1f5f9',
        'subtitle': '#94a3b8',
        'legend_bg': '#0f172a',
        'legend_border': '#334155',
        'legend_text': '#cbd5e1',
        'label_bg': '#0f172a',
        'label_border': '#334155',
        'label_text': '#94a3b8',
        'badge_num_fill': '#020617',
        'group_fill_alpha': 0.05,
    },
}

# Colored arrow markers - mapping kind → color key
ARROW_COLORS = {
    'primary':  None,   # neutral (uses theme arrow color)
    'async':    None,   # neutral + dashed
    'escalate': 'error',
    'feedback': 'token',
    'success':  'output',
    'warning':  'gate',
}

ARROW_DASH = {
    'primary':  None,
    'async':    '4,2',
    'escalate': None,
    'feedback': '5,3',
    'success':  None,
    'warning':  '3,3',
}


def P(theme):
    return PALETTE_LIGHT if theme == 'light' else PALETTE_DARK


def T(theme):
    return THEME[theme]


# =====================================================================
# SVG primitives
# =====================================================================

def svg_header(width, height, theme):
    t = T(theme)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" font-family="Pretendard, -apple-system, BlinkMacSystemFont, sans-serif">',
        '  <defs>',
        '    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">',
        f'      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="{t["grid"]}" stroke-width="0.5"/>',
        '    </pattern>',
        # Arrow markers (neutral + per-role)
        f'    <marker id="arr" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0,0 10,3.5 0,7" fill="{t["arrow"]}"/></marker>',
    ]
    pal = P(theme)
    for role, data in pal.items():
        lines.append(f'    <marker id="arr-{role}" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0,0 10,3.5 0,7" fill="{data["stroke"]}"/></marker>')
    lines.append('  </defs>')
    # Background + grid
    lines.append(f'  <rect width="{width}" height="{height}" fill="{t["bg"]}"/>')
    lines.append(f'  <rect width="{width}" height="{height}" fill="url(#grid)"/>')
    return lines


def svg_footer():
    return ['</svg>']


def text_title(x, y, text, theme, size=20, weight=700):
    t = T(theme)
    return [f'  <text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" font-weight="{weight}" fill="{t["title"]}">{text}</text>']


def text_subtitle(x, y, text, theme, size=12):
    t = T(theme)
    return [f'  <text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" fill="{t["subtitle"]}">{text}</text>']


def node(x, y, w, h, role, theme, num=None, title='', sub='', detail=''):
    """Draw a node with optional number badge + title + sub + detail."""
    pal = P(theme)[role]
    t = T(theme)
    cx = x + w / 2
    out = []
    # Opaque mask so arrows drawn earlier don't bleed through semi-transparent fill
    out.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{t["node_mask"]}"/>')
    # Styled
    out.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{pal["fill"]}" stroke="{pal["stroke"]}" stroke-width="1.5"/>')
    # Number badge
    title_y_offset = 26
    if num:
        out.append(f'  <circle cx="{cx}" cy="{y+22}" r="13" fill="{pal["stroke"]}"/>')
        out.append(f'  <text x="{cx}" y="{y+27}" text-anchor="middle" font-size="13" font-weight="700" fill="{t["badge_num_fill"]}" font-family="JetBrains Mono, monospace">{num}</text>')
        title_y = y + 54
        sub_y = y + 72
        detail_y = y + 86
    else:
        title_y = y + h / 2 - 4
        sub_y = y + h / 2 + 12
        detail_y = y + h / 2 + 28
    # Title
    if title:
        out.append(f'  <text x="{cx}" y="{title_y}" text-anchor="middle" font-size="14" font-weight="700" fill="{pal["text"]}">{title}</text>')
    # Sub
    if sub:
        out.append(f'  <text x="{cx}" y="{sub_y}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["sub"]}">{sub}</text>')
    # Detail (optional third line)
    if detail:
        out.append(f'  <text x="{cx}" y="{detail_y}" text-anchor="middle" font-size="10" fill="{pal["sub"]}">{detail}</text>')
    return out


def group_container(x, y, w, h, label, role, theme, dasharray='8,4'):
    """Draw a dashed grouping container with top-left label."""
    pal = P(theme)[role]
    t = T(theme)
    alpha = t['group_fill_alpha']
    # Extract rgba base for fill
    stroke = pal['stroke']
    # Use stroke color with low alpha for fill
    if stroke.startswith('#'):
        # Convert hex to rgb
        r = int(stroke[1:3], 16)
        g = int(stroke[3:5], 16)
        b = int(stroke[5:7], 16)
        fill = f'rgba({r},{g},{b},{alpha})'
    else:
        fill = f'rgba(100,100,100,{alpha})'
    out = []
    out.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="1" stroke-dasharray="{dasharray}"/>')
    out.append(f'  <text x="{x+12}" y="{y+18}" font-size="10" font-weight="700" fill="{stroke}" font-family="JetBrains Mono, monospace">{label}</text>')
    return out


def arrow_line(x1, y1, x2, y2, theme, kind='primary', label=None, label_offset=-18):
    """Horizontal/vertical/diagonal line with optional mid label.

    label_offset: y offset from arrow midpoint (negative = above, positive = below).
    For horizontal arrows, -18 keeps label safely above any node.
    """
    t = T(theme)
    pal = P(theme)
    color_role = ARROW_COLORS.get(kind)
    if color_role:
        color = pal[color_role]['stroke']
        marker = f'arr-{color_role}'
    else:
        color = t['arrow']
        marker = 'arr'
    dash = ARROW_DASH.get(kind)
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ''
    width = 1.8 if kind in ('primary', 'escalate') else 1.5
    out = [f'  <path d="M {x1},{y1} L {x2},{y2}" stroke="{color}" stroke-width="{width}" fill="none" marker-end="url(#{marker})"{dash_attr}/>']
    if label:
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2 + label_offset
        w_lbl = len(label) * 7 + 16
        out.append(f'  <rect x="{mx - w_lbl/2}" y="{my - 9}" width="{w_lbl}" height="18" rx="4" fill="{t["label_bg"]}" stroke="{t["label_border"]}" stroke-width="0.8"/>')
        out.append(f'  <text x="{mx}" y="{my + 4}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{t["label_text"]}">{label}</text>')
    return out


def arrow_path(d, theme, kind='primary', label_pos=None, label=None):
    """Arbitrary path with optional label at given position."""
    t = T(theme)
    pal = P(theme)
    color_role = ARROW_COLORS.get(kind)
    color = pal[color_role]['stroke'] if color_role else t['arrow']
    marker = f'arr-{color_role}' if color_role else 'arr'
    dash = ARROW_DASH.get(kind)
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ''
    width = 1.8 if kind in ('primary', 'escalate') else 1.5
    out = [f'  <path d="{d}" stroke="{color}" stroke-width="{width}" fill="none" marker-end="url(#{marker})"{dash_attr}/>']
    if label and label_pos:
        lx, ly = label_pos
        w_lbl = len(label) * 7 + 16
        out.append(f'  <rect x="{lx - w_lbl/2}" y="{ly - 9}" width="{w_lbl}" height="18" rx="4" fill="{t["label_bg"]}" stroke="{t["label_border"]}" stroke-width="0.8"/>')
        out.append(f'  <text x="{lx}" y="{ly + 4}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{t["label_text"]}">{label}</text>')
    return out


def arrow_legend(x, y, items, theme, title='ARROWS'):
    """Legend box for arrow kinds. items = [(label, kind), ...]"""
    t = T(theme)
    w = 200
    h = 28 + len(items) * 14
    out = []
    out.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="1"/>')
    out.append(f'  <text x="{x+12}" y="{y+20}" font-size="10" font-weight="700" fill="{t["legend_text"]}" font-family="JetBrains Mono, monospace">{title}</text>')
    pal = P(theme)
    for i, (label, kind) in enumerate(items):
        ly = y + 36 + i * 14
        color_role = ARROW_COLORS.get(kind)
        color = pal[color_role]['stroke'] if color_role else t['arrow']
        dash = ARROW_DASH.get(kind)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ''
        out.append(f'  <line x1="{x+14}" y1="{ly}" x2="{x+50}" y2="{ly}" stroke="{color}" stroke-width="1.8"{dash_attr}/>')
        out.append(f'  <text x="{x+58}" y="{ly+3}" font-size="10" fill="{t["legend_text"]}" font-family="JetBrains Mono, monospace">{label}</text>')
    return out


def role_legend(x, y, items, theme, width=640, title='ROLES', cols=3):
    """Role color legend. items = [(role, label), ...]"""
    t = T(theme)
    pal = P(theme)
    rows = (len(items) + cols - 1) // cols
    h = 28 + rows * 22
    out = []
    out.append(f'  <rect x="{x}" y="{y}" width="{width}" height="{h}" rx="8" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="1"/>')
    out.append(f'  <text x="{x+12}" y="{y+20}" font-size="10" font-weight="700" fill="{t["legend_text"]}" font-family="JetBrains Mono, monospace">{title}</text>')
    col_w = (width - 110) // cols
    for i, (role, label) in enumerate(items):
        col = i % cols
        row = i // cols
        cx = x + 110 + col * col_w
        cy = y + 36 + row * 22
        out.append(f'  <rect x="{cx}" y="{cy - 9}" width="14" height="14" rx="3" fill="{pal[role]["stroke"]}"/>')
        out.append(f'  <text x="{cx + 22}" y="{cy + 2}" font-size="11" fill="{t["legend_text"]}">{label}</text>')
    return out


# =====================================================================
# High-level helper: regular grid of nodes
# =====================================================================

def layout_row(nodes, canvas_w, node_w, node_gap, y, margin=20):
    """Given nodes list and canvas width, auto-space horizontally.

    Returns list of x positions in order.
    """
    n = len(nodes)
    total_nodes_w = n * node_w
    gaps_w = (n - 1) * node_gap
    total = total_nodes_w + gaps_w
    left = (canvas_w - total) // 2
    xs = [left + i * (node_w + node_gap) for i in range(n)]
    return xs


def connect_row(xs, y, node_w, node_h, theme, kind='primary'):
    """Draw horizontal arrows between consecutive nodes in a row."""
    out = []
    cy = y + node_h / 2
    for i in range(len(xs) - 1):
        x1 = xs[i] + node_w + 2
        x2 = xs[i + 1] - 2
        out.extend(arrow_line(x1, cy, x2, cy, theme, kind=kind))
    return out


def group_around_nodes(xs_in_group, node_y, node_w, node_h, label, role, theme, pad_x=16, pad_y=26, pad_bottom=12):
    """Compute group container bounds that properly wrap a set of nodes + label."""
    if not xs_in_group:
        return []
    x_left = min(xs_in_group) - pad_x
    x_right = max(xs_in_group) + node_w + pad_x
    y_top = node_y - pad_y
    y_bottom = node_y + node_h + pad_bottom
    return group_container(x_left, y_top, x_right - x_left, y_bottom - y_top, label, role, theme)
