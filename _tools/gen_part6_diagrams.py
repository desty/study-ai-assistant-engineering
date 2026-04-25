"""Part 6 다이어그램 제너레이터.

Ch 26: prod-arch (production layers), resilience-flow (retry · cache · breaker)
Ch 27~30: 추후 추가
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
# Ch 26. Production 아키텍처 — 5 레이어 한 장
# =====================================================================

def prod_arch(theme):
    CW, CH = 1200, 640
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Production 아키텍처 — PoC 와의 차이는 "분리"', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'API · LLM · Retrieval · Session · Observability 다섯 레이어가 각자 실패하고 각자 회복한다.', theme))

    pal = P(theme)
    t = T(theme)

    NW, NH = 150, 70

    # Row 1: User
    user_x = (CW - NW) // 2
    user_y = 90
    lines.extend(node(user_x, user_y, NW, NH, 'input', theme, title='Client', sub='Web · Mobile · API'))

    # Row 2: API Gateway (FastAPI)
    gw_x = (CW - 240) // 2
    gw_y = 200
    lines.extend(node(gw_x, gw_y, 240, NH, 'gate', theme, title='API Gateway (FastAPI)',
                      sub='auth · rate limit · async', detail='요청 라우팅 + 백프레셔'))

    # User → Gateway
    lines.extend(arrow_line(user_x + NW/2, user_y + NH + 2, gw_x + 120, gw_y - 2, theme, kind='primary'))

    # Row 3: 3 service layers (LLM / Retrieval / Session)
    row3_y = 330
    layer_w, layer_h = 260, 170
    gap = 60
    total = 3 * layer_w + 2 * gap
    left = (CW - total) // 2

    layers = [
        {
            'role': 'llm',
            'title': 'LLM Layer',
            'sub': 'provider abstraction',
            'items': ['• cache (prompt key)', '• retry + backoff', '• circuit breaker', '• model router'],
        },
        {
            'role': 'tool',
            'title': 'Retrieval Layer',
            'sub': 'vector + lexical',
            'items': ['• embedding cache', '• vector store', '• reranker', '• filter (metadata)'],
        },
        {
            'role': 'memory',
            'title': 'Session Store',
            'sub': 'Redis · KV + TTL',
            'items': ['• thread state', '• user prefs', '• rate window', '• idempotency key'],
        },
    ]

    layer_xs = []
    for i, lyr in enumerate(layers):
        x = left + i * (layer_w + gap)
        layer_xs.append(x)
        role = lyr['role']
        # Card
        lines.append(f'  <rect x="{x}" y="{row3_y}" width="{layer_w}" height="{layer_h}" rx="12" fill="{t["node_mask"]}"/>')
        lines.append(f'  <rect x="{x}" y="{row3_y}" width="{layer_w}" height="{layer_h}" rx="12" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.5"/>')
        lines.append(f'  <text x="{x + layer_w/2}" y="{row3_y + 30}" text-anchor="middle" font-size="15" font-weight="700" fill="{pal[role]["text"]}">{lyr["title"]}</text>')
        lines.append(f'  <text x="{x + layer_w/2}" y="{row3_y + 50}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{lyr["sub"]}</text>')
        for k, item in enumerate(lyr['items']):
            lines.append(f'  <text x="{x + 20}" y="{row3_y + 80 + k*22}" font-size="12" fill="{pal[role]["sub"]}">{item}</text>')

    # Gateway → 3 layers (fanned arrows)
    gx_center = gw_x + 120
    gy_bot = gw_y + NH + 2
    for x in layer_xs:
        lines.extend(arrow_line(gx_center, gy_bot, x + layer_w/2, row3_y - 2, theme, kind='primary'))

    # Row 4: Observability bus (full width band)
    obs_y = 540
    obs_h = 70
    obs_x = left
    obs_w = total
    lines.append(f'  <rect x="{obs_x}" y="{obs_y}" width="{obs_w}" height="{obs_h}" rx="12" fill="{pal["token"]["fill"]}" stroke="{pal["token"]["stroke"]}" stroke-width="1.5"/>')
    lines.append(f'  <text x="{obs_x + obs_w/2}" y="{obs_y + 28}" text-anchor="middle" font-size="14" font-weight="700" fill="{pal["token"]["text"]}">Observability Bus  ·  trace · log · cost · latency</text>')
    lines.append(f'  <text x="{obs_x + obs_w/2}" y="{obs_y + 50}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["token"]["sub"]}">LangSmith / Langfuse / OpenTelemetry → Ch 27</text>')

    # 3 layers → Observability (dashed feedback arrows)
    for x in layer_xs:
        lines.extend(arrow_line(x + layer_w/2, row3_y + layer_h + 2, x + layer_w/2, obs_y - 2, theme, kind='feedback'))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 26. Resilience flow — cache → rate limit → retry → breaker → fallback
# =====================================================================

def resilience_flow(theme):
    CW, CH = 1200, 480
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '한 번의 LLM 호출이 살아남는 길', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '캐시 → 레이트리밋 → 재시도 → 서킷브레이커 → 폴백. 모든 단계가 빠지면 장애로 전이된다.', theme))

    pal = P(theme)
    t = T(theme)

    NW, NH = 150, 80
    Y = 130
    GAP = 30
    total = 5 * NW + 4 * GAP
    LEFT = (CW - total) // 2

    stages = [
        ('memory', '① Cache',     'prompt hash',   'hit ⇒ 즉시 반환'),
        ('gate',   '② Rate Limit','token bucket',  '초과 ⇒ 429 / queue'),
        ('llm',    '③ LLM Call',  'provider API',  'timeout 30s'),
        ('error',  '④ Retry',     'exp · jitter',  '5xx · 429 · timeout'),
        ('output', '⑤ Result',    'JSON · stream', '정상 응답'),
    ]

    xs = [LEFT + i * (NW + GAP) for i in range(5)]
    for i, (role, title, sub, detail) in enumerate(stages):
        lines.extend(node(xs[i], Y, NW, NH + 30, role, theme, title=title, sub=sub, detail=detail))

    # Primary flow arrows
    cy = Y + (NH + 30) / 2
    for i in range(4):
        x1 = xs[i] + NW + 2
        x2 = xs[i + 1] - 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))

    # Circuit breaker — separate gate above the LLM/Retry pair
    cb_x = xs[2] + NW // 2 - 60
    cb_y = Y - 70
    lines.append(f'  <rect x="{cb_x}" y="{cb_y}" width="120" height="50" rx="10" fill="{pal["error"]["fill"]}" stroke="{pal["error"]["stroke"]}" stroke-width="1.5"/>')
    lines.append(f'  <text x="{cb_x + 60}" y="{cb_y + 22}" text-anchor="middle" font-size="13" font-weight="700" fill="{pal["error"]["text"]}">Circuit Breaker</text>')
    lines.append(f'  <text x="{cb_x + 60}" y="{cb_y + 40}" text-anchor="middle" font-size="10" font-family="JetBrains Mono, monospace" fill="{pal["error"]["sub"]}">5회 연속 실패 ⇒ open</text>')

    # Breaker → LLM (down arrow, escalate kind)
    lines.extend(arrow_line(cb_x + 60, cb_y + 50 + 2, xs[2] + NW/2, Y - 2, theme, kind='escalate', label='trip'))

    # Fallback below — dashed bypass when breaker open
    fb_y = Y + NH + 30 + 80
    fb_x = xs[3] - 30
    fb_w = 220
    lines.append(f'  <rect x="{fb_x}" y="{fb_y}" width="{fb_w}" height="60" rx="10" fill="{pal["gate"]["fill"]}" stroke="{pal["gate"]["stroke"]}" stroke-width="1.5" stroke-dasharray="4,3"/>')
    lines.append(f'  <text x="{fb_x + fb_w/2}" y="{fb_y + 25}" text-anchor="middle" font-size="13" font-weight="700" fill="{pal["gate"]["text"]}">Fallback</text>')
    lines.append(f'  <text x="{fb_x + fb_w/2}" y="{fb_y + 45}" text-anchor="middle" font-size="10" font-family="JetBrains Mono, monospace" fill="{pal["gate"]["sub"]}">stale cache · 작은 모델 · 사람 이관</text>')

    # Retry exhausted → Fallback
    lines.extend(arrow_line(xs[3] + NW/2, Y + NH + 30 + 2, fb_x + fb_w/2, fb_y - 2, theme, kind='warning', label='exhausted'))

    # Fallback → Result (success arrow up-right)
    lines.extend(arrow_path(
        f'M {fb_x + fb_w} {fb_y + 30} Q {xs[4] - 10} {fb_y + 30}, {xs[4] + NW/2} {Y + NH + 30 + 2}',
        theme, kind='success', label='degraded ok',
        label_pos=(xs[4] + NW/2, fb_y + 10),
    ))

    # Bottom tip bar
    lines.append(f'  <rect x="40" y="{CH - 35}" width="{CW-80}" height="22" rx="4" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')
    lines.append(f'  <text x="{CW/2}" y="{CH - 19}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">캐시·레이트리밋은 호출 전 · 재시도·브레이커는 호출 중 · 폴백은 호출 실패 후. 한 줄에서 다섯 정책이 다른 이유로 작동.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 28. Guardrails 7종 — 계층형 방어
# =====================================================================

def guardrails_7layers(theme):
    CW, CH = 1240, 620
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '가드레일 7종 — 입력 4 + 출력 3 의 계층 방어', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '하나로는 부족하다. 입력·툴 호출·출력 세 위치에 특화된 필터를 배치해 한 곳이 뚫려도 다음이 잡는다.', theme))

    pal = P(theme)
    t = T(theme)

    # User · Agent · Output positions
    UNW, UNH = 130, 60
    USER_X, USER_Y = 60, 280
    AGENT_X, AGENT_Y = 540, 260
    AGENT_W, AGENT_H = 160, 100
    OUT_X, OUT_Y = 1050, 280

    # Input-side rails (4) — between user and agent, vertical stack
    in_rails = [
        ('gate',   '① Relevance',   'topic classifier'),
        ('error',  '② Safety',      'jailbreak · injection'),
        ('memory', '③ Moderation',  'hate · violence'),
        ('token',  '④ Rules',       'regex · blocklist'),
    ]
    RW, RH = 200, 56
    in_x = USER_X + UNW + 30
    in_y0 = 100
    in_gap = 14
    in_centers = []
    for i, (role, title, sub) in enumerate(in_rails):
        ry = in_y0 + i * (RH + in_gap)
        in_centers.append(ry + RH/2)
        lines.append(f'  <rect x="{in_x}" y="{ry}" width="{RW}" height="{RH}" rx="8" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.5"/>')
        lines.append(f'  <text x="{in_x + 14}" y="{ry + 24}" font-size="13" font-weight="700" fill="{pal[role]["text"]}">{title}</text>')
        lines.append(f'  <text x="{in_x + 14}" y="{ry + 44}" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{sub}</text>')

    # User node
    lines.extend(node(USER_X, USER_Y, UNW, UNH, 'input', theme, title='User', sub='input'))

    # Agent node
    lines.append(f'  <rect x="{AGENT_X}" y="{AGENT_Y}" width="{AGENT_W}" height="{AGENT_H}" rx="14" fill="{pal["llm"]["fill"]}" stroke="{pal["llm"]["stroke"]}" stroke-width="2"/>')
    lines.append(f'  <text x="{AGENT_X + AGENT_W/2}" y="{AGENT_Y + 32}" text-anchor="middle" font-size="16" font-weight="700" fill="{pal["llm"]["text"]}">Agent</text>')
    lines.append(f'  <text x="{AGENT_X + AGENT_W/2}" y="{AGENT_Y + 56}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["llm"]["sub"]}">LLM + Tools</text>')
    lines.append(f'  <text x="{AGENT_X + AGENT_W/2}" y="{AGENT_Y + 78}" text-anchor="middle" font-size="10" fill="{pal["llm"]["sub"]}">루프 · 툴 선택</text>')

    # Tool safeguard ⑤ — above the agent
    ts_x = AGENT_X + 5
    ts_y = AGENT_Y - 80
    ts_w, ts_h = 150, 60
    lines.append(f'  <rect x="{ts_x}" y="{ts_y}" width="{ts_w}" height="{ts_h}" rx="8" fill="{pal["tool"]["fill"]}" stroke="{pal["tool"]["stroke"]}" stroke-width="1.5"/>')
    lines.append(f'  <text x="{ts_x + ts_w/2}" y="{ts_y + 24}" text-anchor="middle" font-size="13" font-weight="700" fill="{pal["tool"]["text"]}">⑤ Tool Safeguard</text>')
    lines.append(f'  <text x="{ts_x + ts_w/2}" y="{ts_y + 44}" text-anchor="middle" font-size="10" font-family="JetBrains Mono, monospace" fill="{pal["tool"]["sub"]}">low/med/high · 승인</text>')
    # Tool → Agent (down)
    lines.extend(arrow_line(ts_x + ts_w/2, ts_y + ts_h + 2, AGENT_X + AGENT_W/2, AGENT_Y - 2, theme, kind='warning', label='gate'))

    # Output-side rails (3) — between agent and output, vertical stack
    out_rails = [
        ('gate',   '⑥ PII Filter',       'mask · redact'),
        ('error',  '⑦ Output Validate',  '브랜드 · 정책'),
        ('output', '✓ Final Response',   'user-safe'),
    ]
    out_x = AGENT_X + AGENT_W + 30
    out_y0 = 150
    out_gap = 14
    out_centers = []
    for i, (role, title, sub) in enumerate(out_rails):
        ry = out_y0 + i * (RH + out_gap)
        out_centers.append(ry + RH/2)
        lines.append(f'  <rect x="{out_x}" y="{ry}" width="{RW}" height="{RH}" rx="8" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.5"/>')
        lines.append(f'  <text x="{out_x + 14}" y="{ry + 24}" font-size="13" font-weight="700" fill="{pal[role]["text"]}">{title}</text>')
        lines.append(f'  <text x="{out_x + 14}" y="{ry + 44}" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{sub}</text>')

    # Output node
    lines.extend(node(OUT_X, OUT_Y, UNW, UNH, 'output', theme, title='Response', sub='to user'))

    # Arrows: User → in-rails (one bundle line)
    user_cx = USER_X + UNW
    user_cy = USER_Y + UNH/2
    # Single arrow user → middle of in-stack
    lines.extend(arrow_line(user_cx + 2, user_cy, in_x - 2, user_cy, theme, kind='primary'))
    # in-stack → Agent (single arrow from right of stack to agent)
    lines.extend(arrow_line(in_x + RW + 2, user_cy, AGENT_X - 2, AGENT_Y + AGENT_H/2, theme, kind='primary', label='passed'))

    # Agent → out-stack
    lines.extend(arrow_line(AGENT_X + AGENT_W + 2, AGENT_Y + AGENT_H/2, out_x - 2, OUT_Y + UNH/2, theme, kind='primary'))
    # out-stack → Response
    lines.extend(arrow_line(out_x + RW + 2, OUT_Y + UNH/2, OUT_X - 2, OUT_Y + UNH/2, theme, kind='success'))

    # Section labels
    lines.append(f'  <text x="{in_x + RW/2}" y="{in_y0 - 14}" text-anchor="middle" font-size="11" font-weight="700" fill="{t["legend_text"]}" font-family="JetBrains Mono, monospace">INPUT GUARDRAILS</text>')
    lines.append(f'  <text x="{out_x + RW/2}" y="{out_y0 - 14}" text-anchor="middle" font-size="11" font-weight="700" fill="{t["legend_text"]}" font-family="JetBrains Mono, monospace">OUTPUT GUARDRAILS</text>')

    # Bottom tip
    lines.append(f'  <rect x="40" y="{CH - 35}" width="{CW-80}" height="22" rx="4" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')
    lines.append(f'  <text x="{CW/2}" y="{CH - 19}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">위반 시 즉시 차단(reject) · 마스킹(transform) · 사람 승인(escalate) 셋 중 하나로 응답한다.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 28. Optimistic execution — serial vs parallel guardrail
# =====================================================================

def optimistic_exec(theme):
    CW, CH = 1180, 460
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Optimistic Execution — 가드레일은 LLM 과 병렬', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '직렬로 깔면 가드레일 추가할 때마다 지연이 누적된다. 병렬로 돌리고 위반 시 abort.', theme))

    pal = P(theme)
    t = T(theme)

    # 2 timelines (serial top, parallel bottom)
    LEFT = 80
    RIGHT = CW - 60
    SERIAL_Y = 120
    PARALLEL_Y = 290
    BAR_H = 40

    def bar(x, y, w, role, label, sub=''):
        out = []
        out.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{BAR_H}" rx="6" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.5"/>')
        out.append(f'  <text x="{x + w/2}" y="{y + 18}" text-anchor="middle" font-size="12" font-weight="700" fill="{pal[role]["text"]}">{label}</text>')
        if sub:
            out.append(f'  <text x="{x + w/2}" y="{y + 32}" text-anchor="middle" font-size="10" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{sub}</text>')
        return out

    # === Serial (top) ===
    lines.append(f'  <text x="{LEFT}" y="{SERIAL_Y - 24}" font-size="13" font-weight="700" fill="{t["title"]}">직렬 (느림)</text>')
    seg_w = 180
    gap = 6
    serial_segs = [
        ('gate',   'Input GR', '40ms'),
        ('llm',    'LLM',      '2400ms'),
        ('error',  'Output GR', '60ms'),
    ]
    sx = LEFT
    for role, label, sub in serial_segs:
        lines.extend(bar(sx, SERIAL_Y, seg_w, role, label, sub))
        sx += seg_w + gap
    total_serial = (seg_w + gap) * 3 - gap
    # Total marker
    lines.append(f'  <line x1="{LEFT}" y1="{SERIAL_Y + BAR_H + 12}" x2="{LEFT + total_serial}" y2="{SERIAL_Y + BAR_H + 12}" stroke="{t["arrow_dark"]}" stroke-width="1.5"/>')
    lines.append(f'  <text x="{LEFT + total_serial/2}" y="{SERIAL_Y + BAR_H + 28}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{t["legend_text"]}">총 ≈ 2500ms</text>')

    # === Parallel (bottom) ===
    lines.append(f'  <text x="{LEFT}" y="{PARALLEL_Y - 24}" font-size="13" font-weight="700" fill="{t["title"]}">병렬 · Optimistic (빠름)</text>')
    # LLM bar (long)
    llm_w = 360
    lines.extend(bar(LEFT, PARALLEL_Y, llm_w, 'llm', 'LLM', '2400ms'))
    # Above: Input GR (short, parallel start)
    lines.extend(bar(LEFT, PARALLEL_Y - BAR_H - 6, 80, 'gate', 'Input GR', '40ms'))
    # Below: Output GR runs after LLM but in parallel with response delivery? Actually Output GR is on tokens as they stream. We show it overlapping last 30%
    out_w = 100
    lines.extend(bar(LEFT + llm_w - out_w, PARALLEL_Y + BAR_H + 6, out_w, 'error', 'Output GR', 'streaming'))

    # Abort marker — vertical dashed line at LLM partial when violation detected
    abort_x = LEFT + 230
    lines.append(f'  <line x1="{abort_x}" y1="{PARALLEL_Y - BAR_H - 16}" x2="{abort_x}" y2="{PARALLEL_Y + BAR_H + BAR_H + 16}" stroke="{pal["error"]["stroke"]}" stroke-width="2" stroke-dasharray="4,3"/>')
    lines.append(f'  <text x="{abort_x + 8}" y="{PARALLEL_Y - BAR_H - 20}" font-size="11" font-weight="700" fill="{pal["error"]["text"]}">위반 감지 시 즉시 abort</text>')

    # Total marker for parallel
    lines.append(f'  <line x1="{LEFT}" y1="{PARALLEL_Y + BAR_H + 60}" x2="{LEFT + llm_w}" y2="{PARALLEL_Y + BAR_H + 60}" stroke="{t["arrow_dark"]}" stroke-width="1.5"/>')
    lines.append(f'  <text x="{LEFT + llm_w/2}" y="{PARALLEL_Y + BAR_H + 76}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{t["legend_text"]}">총 ≈ 2400ms (지연 0 추가)</text>')

    # Side note panel
    note_x = LEFT + llm_w + 60
    note_y = 120
    note_w = 360
    note_h = 280
    lines.append(f'  <rect x="{note_x}" y="{note_y}" width="{note_w}" height="{note_h}" rx="10" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="1"/>')
    lines.append(f'  <text x="{note_x + 16}" y="{note_y + 24}" font-size="13" font-weight="700" fill="{t["title"]}">Optimistic 의 핵심</text>')
    notes = [
        '① LLM 호출과 가드레일을 동시 시작',
        '② 위반 감지 시 LLM 응답 폐기',
        '③ 사용자 보지 못함 (스트리밍이면 차단)',
        '④ 정상 케이스 지연 0 추가',
        '',
        '단, 안전·PII 같은 hard fail 은',
        '입력 단계에서 직렬 검사 후 통과시킨다.',
        '"빠르지만 위험한 토큰" 을 흘리지 않기 위함.',
    ]
    for i, ln in enumerate(notes):
        lines.append(f'  <text x="{note_x + 16}" y="{note_y + 56 + i*26}" font-size="12" fill="{t["legend_text"]}">{ln}</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 29. Escalation triggers — 2 trigger paths into approval queue
# =====================================================================

def escalation_triggers(theme):
    CW, CH = 1200, 540
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '휴먼 개입 — 두 가지 트리거', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '실패 임계 초과(자동) · 고위험 액션(사전 정책). 둘 다 같은 승인 큐로 흘러야 감사 추적이 한 곳에 모인다.', theme))

    pal = P(theme)
    t = T(theme)

    # Two trigger boxes (left)
    TW, TH = 230, 100
    TX = 60
    T1_Y = 110
    T2_Y = 290

    # Trigger 1 — Failure threshold
    lines.append(f'  <rect x="{TX}" y="{T1_Y}" width="{TW}" height="{TH}" rx="12" fill="{pal["error"]["fill"]}" stroke="{pal["error"]["stroke"]}" stroke-width="2"/>')
    lines.append(f'  <text x="{TX + TW/2}" y="{T1_Y + 28}" text-anchor="middle" font-size="14" font-weight="700" fill="{pal["error"]["text"]}">① 실패 임계 초과</text>')
    lines.append(f'  <text x="{TX + 14}" y="{T1_Y + 52}" font-size="11" fill="{pal["error"]["sub"]}">• retry 5회 실패</text>')
    lines.append(f'  <text x="{TX + 14}" y="{T1_Y + 70}" font-size="11" fill="{pal["error"]["sub"]}">• guardrail escalate</text>')
    lines.append(f'  <text x="{TX + 14}" y="{T1_Y + 88}" font-size="11" fill="{pal["error"]["sub"]}">• low confidence (&lt; 0.6)</text>')

    # Trigger 2 — High-risk action
    lines.append(f'  <rect x="{TX}" y="{T2_Y}" width="{TW}" height="{TH}" rx="12" fill="{pal["gate"]["fill"]}" stroke="{pal["gate"]["stroke"]}" stroke-width="2"/>')
    lines.append(f'  <text x="{TX + TW/2}" y="{T2_Y + 28}" text-anchor="middle" font-size="14" font-weight="700" fill="{pal["gate"]["text"]}">② 고위험 액션</text>')
    lines.append(f'  <text x="{TX + 14}" y="{T2_Y + 52}" font-size="11" fill="{pal["gate"]["sub"]}">• 큰 금액 환불 (&gt; ₩100k)</text>')
    lines.append(f'  <text x="{TX + 14}" y="{T2_Y + 70}" font-size="11" fill="{pal["gate"]["sub"]}">• 비가역 (계정 삭제)</text>')
    lines.append(f'  <text x="{TX + 14}" y="{T2_Y + 88}" font-size="11" fill="{pal["gate"]["sub"]}">• 외부 메시지 (이메일)</text>')

    # Approval queue (center)
    QW, QH = 240, 150
    QX = 460
    QY = 200
    lines.append(f'  <rect x="{QX}" y="{QY}" width="{QW}" height="{QH}" rx="14" fill="{pal["memory"]["fill"]}" stroke="{pal["memory"]["stroke"]}" stroke-width="2"/>')
    lines.append(f'  <text x="{QX + QW/2}" y="{QY + 30}" text-anchor="middle" font-size="15" font-weight="700" fill="{pal["memory"]["text"]}">Approval Queue</text>')
    lines.append(f'  <text x="{QX + QW/2}" y="{QY + 52}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["memory"]["sub"]}">pending · TTL · context</text>')
    # Mini queue items
    for i in range(3):
        iy = QY + 70 + i * 24
        lines.append(f'  <rect x="{QX + 20}" y="{iy}" width="{QW - 40}" height="18" rx="3" fill="{t["legend_bg"]}" stroke="{pal["memory"]["stroke"]}" stroke-width="0.8"/>')
        lines.append(f'  <text x="{QX + 30}" y="{iy + 13}" font-size="10" font-family="JetBrains Mono, monospace" fill="{pal["memory"]["sub"]}">case_{i+1} · {["fail","risk","fail"][i]} · 2m ago</text>')

    # Trigger arrows → Queue
    lines.extend(arrow_line(TX + TW + 2, T1_Y + TH/2, QX - 2, QY + 50, theme, kind='escalate', label='auto'))
    lines.extend(arrow_line(TX + TW + 2, T2_Y + TH/2, QX - 2, QY + 100, theme, kind='warning', label='policy'))

    # Reviewer (top right)
    RW, RH = 220, 100
    RX = 870
    R1_Y = 110
    lines.extend(node(RX, R1_Y, RW, RH, 'tool', theme, title='Reviewer (Slack/Dashboard)', sub='approve · reject · edit'))

    # Audit log (bottom right)
    AX = 870
    A_Y = 290
    lines.append(f'  <rect x="{AX}" y="{A_Y}" width="{RW}" height="{RH}" rx="12" fill="{pal["token"]["fill"]}" stroke="{pal["token"]["stroke"]}" stroke-width="1.5"/>')
    lines.append(f'  <text x="{AX + RW/2}" y="{A_Y + 30}" text-anchor="middle" font-size="14" font-weight="700" fill="{pal["token"]["text"]}">Audit Log (immutable)</text>')
    lines.append(f'  <text x="{AX + 14}" y="{A_Y + 56}" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["token"]["sub"]}">case_id · who · when</text>')
    lines.append(f'  <text x="{AX + 14}" y="{A_Y + 76}" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["token"]["sub"]}">decision · diff · trace_id</text>')

    # Queue → Reviewer
    lines.extend(arrow_line(QX + QW + 2, QY + 40, RX - 2, R1_Y + RH/2, theme, kind='primary', label='notify'))
    # Reviewer → Audit
    lines.extend(arrow_line(RX + RW/2, R1_Y + RH + 2, AX + RW/2, A_Y - 2, theme, kind='feedback', label='log'))
    # Queue → Audit (직접도 기록 — 들어온 사실)
    lines.extend(arrow_path(
        f'M {QX + QW/2} {QY + QH + 2} Q {QX + QW/2 + 100} {A_Y + 130}, {AX + 30} {A_Y + RH/2}',
        theme, kind='feedback', label='enqueued',
        label_pos=(QX + QW/2 + 130, A_Y + 90),
    ))

    # Resume arrow back to system (left curve from reviewer to where? back to Trigger 1 area as dashed)
    lines.extend(arrow_path(
        f'M {RX + 10} {R1_Y + RH + 2} C {RX + 10} {R1_Y + RH + 60}, {QX + QW/2} {QY - 60}, {QX + QW/2} {QY - 2}',
        theme, kind='success', label='resume / reject',
        label_pos=(RX - 80, R1_Y + RH + 40),
    ))

    # Bottom tip
    lines.append(f'  <rect x="40" y="{CH - 35}" width="{CW-80}" height="22" rx="4" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')
    lines.append(f'  <text x="{CW/2}" y="{CH - 19}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">①은 자동 트리거 · ②는 사전 정책. 모든 결정은 Audit Log 에 기록되어 사후 감사·법적 근거가 된다.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 29. Approval state machine
# =====================================================================

def approval_state_machine(theme):
    CW, CH = 1180, 460
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '승인 큐 상태 머신 — Pending 에서 끝까지', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '대기 → 결정 → 재개 또는 거절. TTL 만료는 자동 reject 로 떨어뜨려 영구 펜딩을 막는다.', theme))

    pal = P(theme)
    t = T(theme)

    NW, NH = 140, 70

    # 5 states: Pending → (Approved | Rejected | Expired) → Resume / Notify
    pending_x, pending_y = 80, 200
    approved_x, approved_y = 380, 100
    rejected_x, rejected_y = 380, 220
    expired_x, expired_y = 380, 340

    resume_x, resume_y = 700, 100
    notify_x, notify_y = 700, 220
    auto_x, auto_y = 700, 340

    final_x, final_y = 1000, 220

    # Pending
    lines.extend(node(pending_x, pending_y, NW, NH + 30, 'memory', theme, title='① Pending', sub='queue', detail='TTL 시작'))
    # Approved / Rejected / Expired
    lines.extend(node(approved_x, approved_y, NW, NH, 'output', theme, title='② Approved', sub='reviewer'))
    lines.extend(node(rejected_x, rejected_y, NW, NH, 'error', theme, title='② Rejected', sub='reviewer'))
    lines.extend(node(expired_x, expired_y, NW, NH, 'gate', theme, title='② Expired', sub='TTL > 24h'))

    # Resume / Notify / Auto-reject
    lines.extend(node(resume_x, resume_y, NW, NH, 'llm', theme, title='③ Resume', sub='Agent 재개'))
    lines.extend(node(notify_x, notify_y, NW, NH, 'token', theme, title='③ Notify User', sub='reason 동반'))
    lines.extend(node(auto_x, auto_y, NW, NH, 'error', theme, title='③ Auto-reject', sub='+ on-call alert'))

    # Final state — Audit
    lines.extend(node(final_x, final_y, NW, NH + 30, 'token', theme, title='④ Audit', sub='log + metrics', detail='who/when/why'))

    # Arrows from Pending
    px_right = pending_x + NW + 2
    pcy = pending_y + (NH + 30)/2
    lines.extend(arrow_line(px_right, pcy - 30, approved_x - 2, approved_y + NH/2, theme, kind='success', label='approve'))
    lines.extend(arrow_line(px_right, pcy, rejected_x - 2, rejected_y + NH/2, theme, kind='escalate', label='reject'))
    lines.extend(arrow_line(px_right, pcy + 40, expired_x - 2, expired_y + NH/2, theme, kind='warning', label='timeout'))

    # State 2 → State 3
    lines.extend(arrow_line(approved_x + NW + 2, approved_y + NH/2, resume_x - 2, resume_y + NH/2, theme, kind='primary'))
    lines.extend(arrow_line(rejected_x + NW + 2, rejected_y + NH/2, notify_x - 2, notify_y + NH/2, theme, kind='primary'))
    lines.extend(arrow_line(expired_x + NW + 2, expired_y + NH/2, auto_x - 2, auto_y + NH/2, theme, kind='primary'))

    # State 3 → Audit (all converge)
    lines.extend(arrow_line(resume_x + NW + 2, resume_y + NH/2, final_x - 2, final_y + 20, theme, kind='feedback'))
    lines.extend(arrow_line(notify_x + NW + 2, notify_y + NH/2, final_x - 2, final_y + (NH+30)/2, theme, kind='feedback'))
    lines.extend(arrow_line(auto_x + NW + 2, auto_y + NH/2, final_x - 2, final_y + 80, theme, kind='feedback'))

    # Bottom tip
    lines.append(f'  <rect x="40" y="{CH - 35}" width="{CW-80}" height="22" rx="4" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')
    lines.append(f'  <text x="{CW/2}" y="{CH - 19}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">TTL 24h 이 기본값. 야간·휴일 정책에 맞춰 조정. 모든 종료 경로가 Audit 에 모인다.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 27. Trace waterfall — one request as nested spans
# =====================================================================

def trace_waterfall(theme):
    CW, CH = 1240, 520
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '한 요청의 Trace — span 으로 분해', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '같은 요청을 span 7개로 펼친다. 무엇이 비싸고 무엇이 느린지 즉시 보인다.', theme))

    pal = P(theme)
    t = T(theme)

    # Time axis: 0 ~ 2600 ms
    AXIS_LEFT = 280
    AXIS_RIGHT = CW - 200
    AXIS_W = AXIS_RIGHT - AXIS_LEFT
    T_MAX = 2600  # ms

    def t_to_x(ms):
        return AXIS_LEFT + (ms / T_MAX) * AXIS_W

    # Time axis line
    AXIS_Y = 110
    lines.append(f'  <line x1="{AXIS_LEFT}" y1="{AXIS_Y}" x2="{AXIS_RIGHT}" y2="{AXIS_Y}" stroke="{t["arrow_dark"]}" stroke-width="1.5"/>')
    # Ticks every 500ms
    for ms in range(0, T_MAX + 1, 500):
        x = t_to_x(ms)
        lines.append(f'  <line x1="{x}" y1="{AXIS_Y - 4}" x2="{x}" y2="{AXIS_Y + 4}" stroke="{t["arrow_dark"]}" stroke-width="1"/>')
        lines.append(f'  <text x="{x}" y="{AXIS_Y - 10}" text-anchor="middle" font-size="10" font-family="JetBrains Mono, monospace" fill="{t["legend_text"]}">{ms}ms</text>')

    # Spans: (label, role, start_ms, dur_ms, cost, level)
    spans = [
        ('HTTP request',         'input',  0,    2580, '—',         0),
        ('Auth · rate limit',    'gate',   10,   30,   '—',         1),
        ('Input guardrails',     'gate',   45,   200,  '$0.0001',   1),
        ('Retrieval',            'tool',   250,  220,  '$0.0002',   1),
        ('  embed (query)',      'token',  255,  60,   '$0.00005',  2),
        ('  vector search',      'tool',   320,  90,   '—',         2),
        ('  rerank',             'tool',   415,  50,   '$0.00015',  2),
        ('LLM call (Opus)',      'llm',    480,  2000, '$0.025',    1),
        ('Output guardrails',    'error',  2485, 70,   '$0.00005',  1),
    ]

    SPAN_H = 28
    SPAN_GAP = 6
    SPAN_Y0 = AXIS_Y + 30
    LABEL_W = 220

    for i, (label, role, start, dur, cost, level) in enumerate(spans):
        sy = SPAN_Y0 + i * (SPAN_H + SPAN_GAP)
        x0 = t_to_x(start)
        x1 = t_to_x(start + dur)
        w = max(x1 - x0, 4)
        # Label (left)
        indent = level * 14
        lines.append(f'  <text x="{AXIS_LEFT - LABEL_W + 12 + indent}" y="{sy + 18}" font-size="12" fill="{pal[role]["text"]}">{label}</text>')
        # Bar
        lines.append(f'  <rect x="{x0}" y="{sy}" width="{w}" height="{SPAN_H}" rx="4" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.2"/>')
        # Duration text inside if wide enough
        if w > 60:
            lines.append(f'  <text x="{x0 + w/2}" y="{sy + 18}" text-anchor="middle" font-size="10" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{dur}ms</text>')
        else:
            lines.append(f'  <text x="{x1 + 6}" y="{sy + 18}" font-size="10" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{dur}ms</text>')
        # Cost (right side)
        lines.append(f'  <text x="{AXIS_RIGHT + 14}" y="{sy + 18}" font-size="11" font-family="JetBrains Mono, monospace" fill="{t["legend_text"]}">{cost}</text>')

    # Header for cost column
    lines.append(f'  <text x="{AXIS_RIGHT + 14}" y="{SPAN_Y0 - 12}" font-size="11" font-weight="700" fill="{t["legend_text"]}" font-family="JetBrains Mono, monospace">cost</text>')
    lines.append(f'  <text x="{AXIS_LEFT - LABEL_W + 12}" y="{SPAN_Y0 - 12}" font-size="11" font-weight="700" fill="{t["legend_text"]}" font-family="JetBrains Mono, monospace">span</text>')

    # Bottom tip
    lines.append(f'  <rect x="40" y="{CH - 35}" width="{CW-80}" height="22" rx="4" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')
    lines.append(f'  <text x="{CW/2}" y="{CH - 19}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">LLM call 이 전체의 78% · 비용의 99%. 최적화는 가장 굵은 막대부터 (Ch 30).</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 27. Three signals — logs / metrics / traces
# =====================================================================

def three_signals(theme):
    CW, CH = 1200, 520
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '관측성의 3 신호 — Logs · Metrics · Traces', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '하나만 보면 장애의 1/3 만 보인다. 셋이 같은 trace_id 로 묶여야 디버깅이 한 번에 끝난다.', theme))

    pal = P(theme)
    t = T(theme)

    # 3 columns
    CW_COL = 320
    GAP = 40
    total = 3 * CW_COL + 2 * GAP
    LEFT = (CW - total) // 2
    TOP = 110
    HEIGHT = 270

    cols = [
        {
            'role': 'token',
            'title': 'Logs',
            'sub': 'structured · per event',
            'q': '"무슨 일이 일어났나"',
            'items': ['• request 시작/끝', '• 에러 stack trace', '• 사용자 액션', '• 가드레일 위반'],
            'kpi': 'searchable · ELK · CloudWatch',
        },
        {
            'role': 'gate',
            'title': 'Metrics',
            'sub': 'aggregated · timeseries',
            'q': '"얼마나 자주 / 얼마나 빨리"',
            'items': ['• p50/p95/p99 latency', '• req/sec · error rate', '• cost · token usage', '• cache hit rate'],
            'kpi': 'Prometheus · Datadog',
        },
        {
            'role': 'llm',
            'title': 'Traces',
            'sub': 'causal · across spans',
            'q': '"어디서 어디로 흘렀나"',
            'items': ['• span tree (Ch 27 §1)', '• cross-service 호출', '• prompt + response', '• cost per span'],
            'kpi': 'LangSmith · Langfuse · OTel',
        },
    ]

    for i, c in enumerate(cols):
        x = LEFT + i * (CW_COL + GAP)
        role = c['role']
        # Card
        lines.append(f'  <rect x="{x}" y="{TOP}" width="{CW_COL}" height="{HEIGHT}" rx="14" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="2"/>')
        lines.append(f'  <text x="{x + CW_COL/2}" y="{TOP + 32}" text-anchor="middle" font-size="18" font-weight="700" fill="{pal[role]["text"]}">{c["title"]}</text>')
        lines.append(f'  <text x="{x + CW_COL/2}" y="{TOP + 54}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{c["sub"]}</text>')
        lines.append(f'  <text x="{x + CW_COL/2}" y="{TOP + 80}" text-anchor="middle" font-size="13" font-style="italic" fill="{pal[role]["sub"]}">{c["q"]}</text>')
        for k, item in enumerate(c['items']):
            lines.append(f'  <text x="{x + 24}" y="{TOP + 114 + k*22}" font-size="12" fill="{pal[role]["sub"]}">{item}</text>')
        # KPI footer
        lines.append(f'  <line x1="{x + 20}" y1="{TOP + HEIGHT - 50}" x2="{x + CW_COL - 20}" y2="{TOP + HEIGHT - 50}" stroke="{pal[role]["stroke"]}" stroke-width="0.8" stroke-dasharray="3,2"/>')
        lines.append(f'  <text x="{x + CW_COL/2}" y="{TOP + HEIGHT - 28}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal[role]["text"]}">{c["kpi"]}</text>')

    # Bottom — common trace_id band
    band_y = TOP + HEIGHT + 40
    band_h = 60
    band_x = LEFT
    band_w = total
    lines.append(f'  <rect x="{band_x}" y="{band_y}" width="{band_w}" height="{band_h}" rx="12" fill="{pal["memory"]["fill"]}" stroke="{pal["memory"]["stroke"]}" stroke-width="1.5"/>')
    lines.append(f'  <text x="{band_x + band_w/2}" y="{band_y + 26}" text-anchor="middle" font-size="14" font-weight="700" fill="{pal["memory"]["text"]}">공통 trace_id · user_id · request_id</text>')
    lines.append(f'  <text x="{band_x + band_w/2}" y="{band_y + 46}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["memory"]["sub"]}">셋을 묶는 키. 한 ID 로 검색하면 logs · metrics · traces 가 동시에 떨어져야 한다.</text>')

    # Connect 3 cols → band
    for i in range(3):
        x = LEFT + i * (CW_COL + GAP) + CW_COL/2
        lines.extend(arrow_line(x, TOP + HEIGHT + 2, x, band_y - 2, theme, kind='feedback'))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 30. Cost techniques — 4 levers vs baseline
# =====================================================================

def cost_techniques(theme):
    CW, CH = 1240, 540
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '비용·지연 4 레버 — Baseline 대비 효과', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '캐싱 · 라우팅 · 배치 · 컨텍스트 압축. 레버는 누적 가능하지만 첫 한 개로 보통 절반이 빠진다.', theme))

    pal = P(theme)
    t = T(theme)

    # Bars showing relative cost (baseline = 100, others reduce)
    BAR_X0 = 320
    BAR_W_FULL = 700  # baseline bar full width
    BAR_H = 50
    BAR_GAP = 18
    Y0 = 110

    rows = [
        ('Baseline',         'error',  100, '$0.025',  '2400ms', '단일 Opus, 캐시·라우팅 없음'),
        ('+ Prompt cache',   'memory',  60, '$0.015',  '1900ms', '시스템 + 도구 정의 캐싱 90% off'),
        ('+ Model routing',  'gate',    32, '$0.008',  '1200ms', '쉬운 60% 는 Haiku 로'),
        ('+ Batch API',      'tool',    20, '$0.005',  'async',  '비실시간만 50% off'),
        ('+ Context 압축',   'token',   14, '$0.0035', '900ms',  '이력 요약 · max_tokens 축소'),
    ]

    for i, (label, role, pct, cost, latency, note) in enumerate(rows):
        y = Y0 + i * (BAR_H + BAR_GAP)
        w = BAR_W_FULL * pct / 100
        # Label
        lines.append(f'  <text x="{BAR_X0 - 14}" y="{y + 30}" text-anchor="end" font-size="13" font-weight="700" fill="{t["title"]}">{label}</text>')
        # Bar
        lines.append(f'  <rect x="{BAR_X0}" y="{y}" width="{w}" height="{BAR_H}" rx="6" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.5"/>')
        # Inner pct text
        lines.append(f'  <text x="{BAR_X0 + 14}" y="{y + 30}" font-size="14" font-weight="700" fill="{pal[role]["text"]}">{pct}%</text>')
        # Right side: cost / latency / note
        lines.append(f'  <text x="{BAR_X0 + BAR_W_FULL + 20}" y="{y + 18}" font-size="12" font-family="JetBrains Mono, monospace" fill="{t["legend_text"]}">{cost} · {latency}</text>')
        lines.append(f'  <text x="{BAR_X0 + BAR_W_FULL + 20}" y="{y + 36}" font-size="11" fill="{pal[role]["sub"]}">{note}</text>')

    # Vertical reference line at baseline width
    ref_x = BAR_X0 + BAR_W_FULL
    lines.append(f'  <line x1="{ref_x}" y1="{Y0 - 6}" x2="{ref_x}" y2="{Y0 + 5*(BAR_H+BAR_GAP)}" stroke="{t["arrow_dark"]}" stroke-width="1" stroke-dasharray="3,3"/>')
    lines.append(f'  <text x="{ref_x}" y="{Y0 - 12}" text-anchor="middle" font-size="10" font-family="JetBrains Mono, monospace" fill="{t["legend_text"]}">baseline 100%</text>')

    # Bottom tip
    lines.append(f'  <rect x="40" y="{CH - 35}" width="{CW-80}" height="22" rx="4" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')
    lines.append(f'  <text x="{CW/2}" y="{CH - 19}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">수치는 예시. 도메인·트래픽에 따라 효과 달라짐 — 실측 후 적용 순서 결정.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 30. Model router — Haiku/Sonnet/Opus tier
# =====================================================================

def model_router(theme):
    CW, CH = 1180, 480
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '모델 라우터 — 한 모델로 다 풀지 말 것', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '쉬운 질의는 Haiku 로 · 어려운 것만 Opus. 분류기 비용을 합쳐도 baseline 대비 60% 절감.', theme))

    pal = P(theme)
    t = T(theme)

    NW, NH = 130, 70

    # User → Classifier → 3 branches
    USER_X, USER_Y = 60, 200
    CLF_X, CLF_Y = 260, 200
    CLF_W = 170
    OUT_X = 760

    lines.extend(node(USER_X, USER_Y, NW, NH, 'input', theme, title='Query', sub='사용자 입력'))
    # Classifier (slightly larger)
    lines.append(f'  <rect x="{CLF_X}" y="{CLF_Y}" width="{CLF_W}" height="{NH + 30}" rx="12" fill="{pal["gate"]["fill"]}" stroke="{pal["gate"]["stroke"]}" stroke-width="2"/>')
    lines.append(f'  <text x="{CLF_X + CLF_W/2}" y="{CLF_Y + 28}" text-anchor="middle" font-size="14" font-weight="700" fill="{pal["gate"]["text"]}">Classifier (Haiku)</text>')
    lines.append(f'  <text x="{CLF_X + CLF_W/2}" y="{CLF_Y + 50}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["gate"]["sub"]}">난이도 분류</text>')
    lines.append(f'  <text x="{CLF_X + CLF_W/2}" y="{CLF_Y + 72}" text-anchor="middle" font-size="10" font-family="JetBrains Mono, monospace" fill="{pal["gate"]["sub"]}">~$0.0005 · 200ms</text>')

    # 3 branches
    branches = [
        ('llm', 'Haiku',   '60%',  'FAQ · 분류 · 요약', '$0.001 · 400ms'),
        ('llm', 'Sonnet',  '30%',  '일반 답변',          '$0.012 · 1200ms'),
        ('llm', 'Opus',    '10%',  '복잡 추론·코드',     '$0.030 · 2400ms'),
    ]
    BRANCH_W = 220
    BRANCH_H = 90
    GAP_Y = 14
    branch_xs_y = []
    for i, (role, name, pct, scope, cost) in enumerate(branches):
        bx = 500
        by = 80 + i * (BRANCH_H + GAP_Y)
        branch_xs_y.append((bx, by))
        # Card
        lines.append(f'  <rect x="{bx}" y="{by}" width="{BRANCH_W}" height="{BRANCH_H}" rx="12" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.5"/>')
        lines.append(f'  <text x="{bx + 16}" y="{by + 26}" font-size="14" font-weight="700" fill="{pal[role]["text"]}">{name}</text>')
        lines.append(f'  <text x="{bx + BRANCH_W - 16}" y="{by + 26}" text-anchor="end" font-size="14" font-weight="700" fill="{pal[role]["text"]}">{pct}</text>')
        lines.append(f'  <text x="{bx + 16}" y="{by + 48}" font-size="11" fill="{pal[role]["sub"]}">{scope}</text>')
        lines.append(f'  <text x="{bx + 16}" y="{by + 72}" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{cost}</text>')

    # Arrows: User → Clf → 3 branches
    lines.extend(arrow_line(USER_X + NW + 2, USER_Y + NH/2, CLF_X - 2, CLF_Y + (NH+30)/2, theme, kind='primary'))
    clf_right = CLF_X + CLF_W + 2
    clf_cy = CLF_Y + (NH + 30)/2
    for (bx, by) in branch_xs_y:
        lines.extend(arrow_line(clf_right, clf_cy, bx - 2, by + BRANCH_H/2, theme, kind='primary'))

    # Output node (right)
    lines.extend(node(OUT_X + 100, USER_Y, NW, NH, 'output', theme, title='Response', sub=''))
    # Branches → Output
    for (bx, by) in branch_xs_y:
        lines.extend(arrow_line(bx + BRANCH_W + 2, by + BRANCH_H/2, OUT_X + 100, USER_Y + NH/2, theme, kind='success'))

    # Side note panel
    note_x = 980
    note_y = 80
    note_w = 180
    note_h = 250
    lines.append(f'  <rect x="{note_x}" y="{note_y}" width="{note_w}" height="{note_h}" rx="10" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="1"/>')
    lines.append(f'  <text x="{note_x + 16}" y="{note_y + 24}" font-size="13" font-weight="700" fill="{t["title"]}">실효 비용</text>')
    note_lines = [
        '평균 = ',
        '0.6×0.001',
        '+ 0.3×0.012',
        '+ 0.1×0.030',
        '+ classifier',
        '= ~$0.0073',
        '',
        'baseline Opus',
        '$0.030 의 24%',
    ]
    for i, ln in enumerate(note_lines):
        lines.append(f'  <text x="{note_x + 16}" y="{note_y + 52 + i*22}" font-size="12" font-family="JetBrains Mono, monospace" fill="{t["legend_text"]}">{ln}</text>')

    # Bottom tip
    lines.append(f'  <rect x="40" y="{CH - 35}" width="{CW-80}" height="22" rx="4" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')
    lines.append(f'  <text x="{CW/2}" y="{CH - 19}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">분류기가 틀리면 품질 저하 — 평가셋에서 라우팅 정확도 별도 측정 (Ch 16/17).</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# main
# =====================================================================

def main():
    print('Part 6 diagrams:')
    for name, fn in [
        ('ch26-prod-arch', prod_arch),
        ('ch26-resilience', resilience_flow),
        ('ch27-trace-waterfall', trace_waterfall),
        ('ch27-three-signals', three_signals),
        ('ch28-guardrails-7layers', guardrails_7layers),
        ('ch28-optimistic-exec', optimistic_exec),
        ('ch29-escalation-triggers', escalation_triggers),
        ('ch29-approval-state', approval_state_machine),
        ('ch30-cost-techniques', cost_techniques),
        ('ch30-model-router', model_router),
    ]:
        save(name, fn('light'), fn('dark'))


if __name__ == '__main__':
    main()
