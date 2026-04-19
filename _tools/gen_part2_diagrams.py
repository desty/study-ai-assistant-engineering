"""Part 2 챕터별 다이어그램 생성.

Ch 4: api-pipeline (요청-응답 흐름)
Ch 5, 6, 7, 8: 추후 추가
"""
import os
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from svg_prim import (
    svg_header, svg_footer, text_title, text_subtitle,
    node, arrow_line, arrow_path,
    arrow_legend, role_legend,
)

BASE = str(HERE.parent / 'docs' / 'assets' / 'diagrams')
os.makedirs(BASE, exist_ok=True)

NODE_W, NODE_H = 140, 90


def layout_centered_row(n, canvas_w, node_w, gap):
    total = n * node_w + (n - 1) * gap
    left = (canvas_w - total) // 2
    return [left + i * (node_w + gap) for i in range(n)]


def save(name, light_svg, dark_svg):
    with open(f'{BASE}/{name}.svg', 'w') as f:
        f.write(light_svg)
    with open(f'{BASE}/{name}-dark.svg', 'w') as f:
        f.write(dark_svg)
    os.system(f'rsvg-convert -w 1920 {BASE}/{name}.svg -o {BASE}/{name}.png 2>&1 | head -3')
    print(f'  ✓ {name}')


# =====================================================================
# Ch 4. API 요청-응답 파이프라인
# =====================================================================

def api_pipeline(theme):
    """내 코드 → HTTPS → API 서버 → 모델 → 응답 → 내 코드 루프."""
    CW, CH = 1040, 320
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'API 요청 한 번의 흐름', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'client.messages.create() 한 번 = 이 6단계', theme))

    specs = [
        ('input',  '내 코드',      'your app',        'Python/SDK'),
        ('tool',   '네트워크',     'HTTPS POST',      'TLS 암호화'),
        ('model',  'API 서버',     'Anthropic',       '라우팅·인증'),
        ('llm',    'Claude 모델',  'inference',       '토큰 생성'),
        ('tool',   '네트워크',     'HTTPS 응답',      'JSON'),
        ('output', '내 코드',      'parse',           'response.content'),
    ]
    xs = layout_centered_row(len(specs), CW, NODE_W, 20)
    y = 110
    # Arrows
    for i in range(len(xs) - 1):
        x1 = xs[i] + NODE_W + 2
        x2 = xs[i + 1] - 2
        cy = y + NODE_H // 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))
    for x, (role, t, s, d) in zip(xs, specs):
        lines.extend(node(x, y, NODE_W, NODE_H + 25, role, theme, title=t, sub=s, detail=d))

    # Legend
    lines.extend(role_legend(
        60, 240,
        [('input', '내 코드'), ('tool', '네트워크'), ('model', 'API 서버'),
         ('llm', 'Claude'), ('output', '결과')],
        theme, width=920, cols=5,
    ))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 4. 에러 처리 + 재시도 흐름
# =====================================================================

def retry_flow(theme):
    """요청 → status check → 성공 / 재시도 (loopback) / 최종 실패."""
    CW, CH = 1000, 460
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '에러 처리와 재시도 전략', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '네트워크 이슈는 일상 — fallback 경로를 설계', theme))

    # Layout (subtitle y=58, first node below 80)
    REQ_X, REQ_Y = 40, 180
    CHK_X, CHK_Y = 240, 180
    OK_X,  OK_Y  = 460, 80       # top-right (success path) — below subtitle
    RETRY_X, RETRY_Y = 460, 320  # bottom-right (retry path)
    FAIL_X,  FAIL_Y  = 720, 320
    CHK_CX = CHK_X + NODE_W // 2   # 310
    CHK_BOT = CHK_Y + NODE_H       # 270

    # Arrows BEFORE nodes
    lines.extend(arrow_line(REQ_X + NODE_W, REQ_Y + NODE_H // 2,
                            CHK_X, CHK_Y + NODE_H // 2, theme, kind='primary'))
    # CHK → OK (up-right, success)
    lines.extend(arrow_line(CHK_X + NODE_W, CHK_Y + 15,
                            OK_X, OK_Y + NODE_H // 2, theme, kind='success', label='200 OK'))
    # CHK → RETRY (down-right, warning)
    lines.extend(arrow_line(CHK_X + NODE_W, CHK_Y + NODE_H - 15,
                            RETRY_X, RETRY_Y + NODE_H // 2, theme, kind='warning', label='429 / 5xx'))
    # RETRY → FAIL
    lines.extend(arrow_line(RETRY_X + NODE_W, RETRY_Y + NODE_H // 2,
                            FAIL_X, FAIL_Y + NODE_H // 2, theme, kind='escalate', label='N회 실패'))
    # RETRY → CHK loopback (goes LEFT under CHK and UP)
    retry_lx = RETRY_X                # 460
    retry_cy = RETRY_Y + NODE_H // 2  # 365
    loop_y   = 295                    # between CHK bottom 270 and RETRY top 320
    path = (
        f'M {retry_lx},{retry_cy} '
        f'L {retry_lx - 20},{retry_cy} '
        f'L {retry_lx - 20},{loop_y} '
        f'L {CHK_CX},{loop_y} '
        f'L {CHK_CX},{CHK_BOT}'
    )
    # Label placed on VERTICAL segment (far from warning label on CHK→RETRY arrow)
    lines.extend(arrow_path(
        path, theme, kind='feedback',
        label_pos=(retry_lx - 20 - 60, retry_cy - 25),
        label='backoff',
    ))

    # Nodes (after arrows)
    lines.extend(node(REQ_X, REQ_Y, NODE_W, NODE_H, 'input',  theme, title='API 요청', sub='create()'))
    lines.extend(node(CHK_X, CHK_Y, NODE_W, NODE_H, 'gate',   theme, title='응답 코드', sub='status check'))
    lines.extend(node(OK_X, OK_Y,   NODE_W, NODE_H, 'output', theme, title='성공', sub='response'))
    lines.extend(node(RETRY_X, RETRY_Y, NODE_W, NODE_H, 'memory', theme, title='재시도', sub='exp. backoff'))
    lines.extend(node(FAIL_X, FAIL_Y, NODE_W, NODE_H, 'error', theme, title='최종 실패', sub='raise / log'))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 5. 프롬프트 해부 — System / Few-shot / User / Model / Response
# =====================================================================

def prompt_anatomy(theme):
    """프롬프트의 구성 요소 한 줄 흐름."""
    CW, CH = 1040, 280
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '프롬프트의 해부', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'messages 배열의 구성 요소와 흐름', theme))

    specs = [
        ('input',  '시스템 지침',    'system',    '역할·규칙·출력형식'),
        ('memory', 'Few-shot 예시',  'optional',  'Q-A 짝 1~3개'),
        ('input',  '현재 질문',      'user',      '실제 요청'),
        ('model',  'LLM',           'inference', '토큰 생성'),
        ('output', '응답',           'assistant', '원하는 형식'),
    ]
    xs = layout_centered_row(len(specs), CW, 160, 24)
    y = 100
    for i in range(len(xs) - 1):
        x1 = xs[i] + 160 + 2
        x2 = xs[i + 1] - 2
        cy = y + NODE_H // 2 + 12  # taller nodes, adjust
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))
    for x, (role, t, s, d) in zip(xs, specs):
        lines.extend(node(x, y, 160, NODE_H + 25, role, theme, title=t, sub=s, detail=d))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 5. CoT 비교 — 직답 vs 단계별 추론
# =====================================================================

def cot_comparison(theme):
    """동일 질문에 직답 vs CoT 두 경로 비교."""
    CW, CH = 1040, 340
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '직답 vs Chain-of-Thought', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '같은 모델·같은 질문, 프롬프트 한 줄 차이', theme))

    Q_X = 40
    # Row 1 — direct
    Y1 = 100
    DIRECT_LLM_X = 280
    DIRECT_ANS_X = 560
    # Row 2 — CoT
    Y2 = 220
    COT_LLM_X = 280
    COT_REASON_X = 560
    COT_ANS_X = 820

    # Shared question node vertical-center between rows
    Q_Y = (Y1 + Y2) // 2  # 160

    # Arrows
    # Question → direct LLM (up-right)
    lines.extend(arrow_line(Q_X + NODE_W, Q_Y + NODE_H // 2 - 10,
                            DIRECT_LLM_X, Y1 + NODE_H // 2, theme, kind='primary', label='직답'))
    # Direct LLM → Answer
    lines.extend(arrow_line(DIRECT_LLM_X + NODE_W, Y1 + NODE_H // 2,
                            DIRECT_ANS_X, Y1 + NODE_H // 2, theme, kind='primary'))
    # Question → CoT LLM (down-right)
    lines.extend(arrow_line(Q_X + NODE_W, Q_Y + NODE_H // 2 + 10,
                            COT_LLM_X, Y2 + NODE_H // 2, theme, kind='primary', label='단계별'))
    # CoT LLM → reasoning
    lines.extend(arrow_line(COT_LLM_X + NODE_W, Y2 + NODE_H // 2,
                            COT_REASON_X, Y2 + NODE_H // 2, theme, kind='primary'))
    # reasoning → answer
    lines.extend(arrow_line(COT_REASON_X + NODE_W, Y2 + NODE_H // 2,
                            COT_ANS_X, Y2 + NODE_H // 2, theme, kind='primary'))

    # Nodes
    lines.extend(node(Q_X, Q_Y, NODE_W, NODE_H, 'input', theme, title='질문', sub='user'))
    lines.extend(node(DIRECT_LLM_X, Y1, NODE_W, NODE_H, 'model', theme, title='LLM', sub='direct'))
    lines.extend(node(DIRECT_ANS_X, Y1, NODE_W, NODE_H, 'error', theme, title='답', sub='오답 위험'))
    lines.extend(node(COT_LLM_X, Y2, NODE_W, NODE_H, 'model', theme, title='LLM', sub='+ step-by-step'))
    lines.extend(node(COT_REASON_X, Y2, NODE_W, NODE_H, 'token', theme, title='추론 단계', sub='reasoning'))
    lines.extend(node(COT_ANS_X, Y2, NODE_W, NODE_H, 'output', theme, title='답', sub='더 정확'))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 6. 구조화 출력 파이프라인 — LLM → parse → validate → ok / retry / fallback
# =====================================================================

def structured_output_flow(theme):
    CW, CH = 1040, 460
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '구조화 출력 파이프라인', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'JSON을 부탁하고 → 검증 → 통과 or 재시도 or fallback', theme))

    # Main row (top)
    REQ_X, REQ_Y = 40, 190
    LLM_X, LLM_Y = 220, 190
    PARSE_X, PARSE_Y = 420, 190
    VAL_X, VAL_Y = 620, 190
    # Outcome row (bottom)
    OK_X, OK_Y = 220, 340
    RETRY_X, RETRY_Y = 480, 340
    FAIL_X, FAIL_Y = 740, 340

    # Arrows BEFORE nodes
    # Main horizontal chain
    for a, b in [(REQ_X + NODE_W, LLM_X), (LLM_X + NODE_W, PARSE_X), (PARSE_X + NODE_W, VAL_X)]:
        cy = REQ_Y + NODE_H // 2
        lines.extend(arrow_line(a, cy, b, cy, theme, kind='primary'))

    # VAL → OK (down-left, success)
    lines.extend(arrow_line(VAL_X + 20, VAL_Y + NODE_H,
                            OK_X + NODE_W, OK_Y + NODE_H // 2, theme, kind='success', label='valid'))
    # VAL → RETRY (down, warning)
    lines.extend(arrow_line(VAL_X + NODE_W // 2, VAL_Y + NODE_H,
                            RETRY_X + NODE_W // 2, RETRY_Y, theme, kind='warning', label='parse fail'))
    # VAL → FAIL (down-right, escalate)
    lines.extend(arrow_line(VAL_X + NODE_W - 20, VAL_Y + NODE_H,
                            FAIL_X, FAIL_Y + NODE_H // 2, theme, kind='escalate', label='N회 실패'))

    # RETRY → LLM loopback (goes UP between main & subtitle)
    retry_cx = RETRY_X + NODE_W // 2
    llm_cx = LLM_X + NODE_W // 2
    loop_y = 130  # between subtitle 58-78 and main row 190
    path = (
        f'M {retry_cx},{RETRY_Y} '
        f'L {retry_cx},{loop_y} '
        f'L {llm_cx},{loop_y} '
        f'L {llm_cx},{LLM_Y}'
    )
    lines.extend(arrow_path(
        path, theme, kind='feedback',
        label_pos=((retry_cx + llm_cx) // 2, loop_y - 12),
        label='에러 포함 재질의',
    ))

    # Nodes
    lines.extend(node(REQ_X, REQ_Y, NODE_W, NODE_H, 'input', theme, title='요청', sub='user input'))
    lines.extend(node(LLM_X, LLM_Y, NODE_W, NODE_H, 'model', theme, title='LLM', sub='JSON 생성'))
    lines.extend(node(PARSE_X, PARSE_Y, NODE_W, NODE_H, 'tool', theme, title='파싱', sub='json.loads'))
    lines.extend(node(VAL_X, VAL_Y, NODE_W, NODE_H, 'gate', theme, title='검증', sub='Pydantic'))
    lines.extend(node(OK_X, OK_Y, NODE_W, NODE_H, 'output', theme, title='통과', sub='dict → 사용'))
    lines.extend(node(RETRY_X, RETRY_Y, NODE_W, NODE_H, 'memory', theme, title='재시도', sub='with error ctx'))
    lines.extend(node(FAIL_X, FAIL_Y, NODE_W, NODE_H, 'error', theme, title='Fallback', sub='규칙/기본값'))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 6. 세 가지 방법 비교 — 프롬프트 힌트 / Tool-use / JSON mode
# =====================================================================

def output_methods_comparison(theme):
    CW, CH = 1000, 300
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '구조화 출력의 3가지 방법', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '왼쪽일수록 쉽고, 오른쪽일수록 엄격 — 프로덕션은 오른쪽으로', theme))

    specs = [
        ('memory', '프롬프트 힌트',    'prompt hint',      '적중률 70~90%'),
        ('tool',   'Tool-use 스키마',  'tool schema',      '적중률 95~99%'),
        ('output', 'Native JSON mode', 'json_schema',      '적중률 ~100%'),
    ]
    # 3 nodes, 260 wide, 40 gap
    xs = layout_centered_row(len(specs), CW, 260, 40)
    y = 110
    node_h = 140

    # Arrows
    for i in range(len(xs) - 1):
        x1 = xs[i] + 260 + 2
        x2 = xs[i + 1] - 2
        cy = y + node_h // 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))

    for x, (role, t, s, d) in zip(xs, specs):
        lines.extend(node(x, y, 260, node_h, role, theme, title=t, sub=s, detail=d))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 7. Blocking vs Streaming — 같은 5초 응답의 두 가지 경험
# =====================================================================

def blocking_vs_stream(theme):
    from svg_prim import P, T
    CW, CH = 1040, 400
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Blocking vs Streaming', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '같은 5초 응답을 사용자는 어떻게 경험하는가', theme))

    pal = P(theme)
    t = T(theme)

    # Row Y positions
    Y_LABEL_1 = 130
    Y_ROW_1 = 110   # node row top for blocking
    Y_LABEL_2 = 240
    Y_ROW_2 = 220   # node row top for streaming
    Y_AXIS = 330

    NH = 60
    req_w = 80
    result_w = 120

    # Time axis: map time (0~5s) to x (180 → 900)
    AXIS_X0 = 180
    AXIS_X1 = 900

    def t_to_x(t_sec):
        return AXIS_X0 + (t_sec / 5.0) * (AXIS_X1 - AXIS_X0)

    # === Row 1: Blocking ===
    # Left label
    lines.append(f'  <text x="40" y="{Y_LABEL_1 + 6}" font-size="13" font-weight="700" fill="{t["title"]}">한 번에</text>')
    lines.append(f'  <text x="40" y="{Y_LABEL_1 + 22}" font-size="10" fill="{t["subtitle"]}" font-family="JetBrains Mono, monospace">blocking</text>')

    # Request node (small)
    lines.extend(node(100, Y_ROW_1, req_w, NH, 'input', theme, title='요청', sub='POST'))

    # Long wait bar (gray) from end of req to result start
    wait_x1 = 100 + req_w
    wait_x2 = t_to_x(5.0) - 10
    wait_h = 30
    wait_y = Y_ROW_1 + (NH - wait_h) // 2
    pal_e = pal['error']
    lines.append(f'  <rect x="{wait_x1}" y="{wait_y}" width="{wait_x2 - wait_x1}" height="{wait_h}" rx="6" fill="{pal_e["fill"]}" stroke="{pal_e["stroke"]}" stroke-width="1" stroke-dasharray="4,3"/>')
    lines.append(f'  <text x="{(wait_x1 + wait_x2) // 2}" y="{wait_y + wait_h // 2 + 4}" text-anchor="middle" font-size="12" font-weight="600" fill="{pal_e["text"]}">대기 · 사용자는 빈 화면</text>')

    # Result node at t=5s
    lines.extend(node(wait_x2 + 5, Y_ROW_1, result_w, NH, 'output', theme, title='전체 응답', sub='at 5.0s'))

    # === Row 2: Streaming ===
    lines.append(f'  <text x="40" y="{Y_LABEL_2 + 6}" font-size="13" font-weight="700" fill="{t["title"]}">스트리밍</text>')
    lines.append(f'  <text x="40" y="{Y_LABEL_2 + 22}" font-size="10" fill="{t["subtitle"]}" font-family="JetBrains Mono, monospace">streaming</text>')

    lines.extend(node(100, Y_ROW_2, req_w, NH, 'input', theme, title='요청', sub='POST'))

    # TTFT small gap (0.3s)
    ttft_x1 = 100 + req_w
    ttft_x2 = t_to_x(0.3)
    pal_g = pal['gate']
    lines.append(f'  <rect x="{ttft_x1}" y="{Y_ROW_2 + (NH - 20) // 2}" width="{ttft_x2 - ttft_x1}" height="20" rx="4" fill="{pal_g["fill"]}" stroke="{pal_g["stroke"]}" stroke-width="1"/>')
    lines.append(f'  <text x="{(ttft_x1 + ttft_x2) // 2}" y="{Y_ROW_2 + NH // 2 + 4}" text-anchor="middle" font-size="10" fill="{pal_g["text"]}" font-family="JetBrains Mono, monospace">TTFT 0.3s</text>')

    # Small token rects over time 0.3 → 5.0
    tok_times = [0.6, 1.0, 1.5, 2.2, 3.0, 3.8, 4.5, 5.0]
    pal_tok = pal['token']
    for tt in tok_times:
        x = t_to_x(tt) - 18
        lines.append(f'  <rect x="{x}" y="{Y_ROW_2 + 12}" width="24" height="36" rx="4" fill="{pal_tok["fill"]}" stroke="{pal_tok["stroke"]}" stroke-width="1"/>')
        lines.append(f'  <text x="{x + 12}" y="{Y_ROW_2 + 36}" text-anchor="middle" font-size="9" fill="{pal_tok["text"]}" font-family="JetBrains Mono, monospace">t</text>')

    # Annotation
    lines.append(f'  <text x="{t_to_x(2.6):.0f}" y="{Y_ROW_2 - 10}" text-anchor="middle" font-size="11" fill="{t["subtitle"]}">사용자는 토큰이 들어오는 대로 화면에서 봄</text>')

    # === Time axis ===
    lines.append(f'  <line x1="{AXIS_X0}" y1="{Y_AXIS}" x2="{AXIS_X1}" y2="{Y_AXIS}" stroke="{t["arrow"]}" stroke-width="1.5"/>')
    for sec in [0, 1, 2, 3, 4, 5]:
        x = t_to_x(sec)
        lines.append(f'  <line x1="{x}" y1="{Y_AXIS}" x2="{x}" y2="{Y_AXIS + 6}" stroke="{t["arrow"]}" stroke-width="1"/>')
        lines.append(f'  <text x="{x}" y="{Y_AXIS + 22}" text-anchor="middle" font-size="11" fill="{t["subtitle"]}" font-family="JetBrains Mono, monospace">{sec}s</text>')
    lines.append(f'  <text x="{AXIS_X0 - 10}" y="{Y_AXIS + 22}" text-anchor="end" font-size="11" fill="{t["subtitle"]}">시간 →</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 8. Tool Calling 루프 — LLM ↔ 툴 ↔ 결과 ↔ LLM ↔ …
# =====================================================================

def tool_use_loop(theme):
    """사용자 → LLM → (tool_use 결정) → 툴 실행 → tool_result → LLM → 최종 응답."""
    CW, CH = 1040, 420
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Tool Calling 루프', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'LLM 이 "도구가 필요하다"고 판단 → 호출 → 결과를 받아 이어서 추론', theme))

    USER_X, USER_Y = 40, 180
    LLM_X, LLM_Y = 240, 180
    GATE_X, GATE_Y = 460, 180
    TOOL_X, TOOL_Y = 680, 80
    RESULT_X, RESULT_Y = 680, 280
    FINAL_X, FINAL_Y = 880, 180

    # Arrows
    lines.extend(arrow_line(USER_X + NODE_W, USER_Y + NODE_H // 2,
                            LLM_X, LLM_Y + NODE_H // 2, theme, kind='primary'))
    lines.extend(arrow_line(LLM_X + NODE_W, LLM_Y + NODE_H // 2,
                            GATE_X, GATE_Y + NODE_H // 2, theme, kind='primary'))
    # GATE → TOOL (up-right)
    lines.extend(arrow_line(GATE_X + NODE_W, GATE_Y + 15,
                            TOOL_X, TOOL_Y + NODE_H // 2, theme, kind='warning', label='tool_use'))
    # GATE → FINAL (right)
    lines.extend(arrow_line(GATE_X + NODE_W, GATE_Y + NODE_H // 2,
                            FINAL_X, FINAL_Y + NODE_H // 2, theme, kind='success', label='end_turn'))
    # TOOL → RESULT (down)
    lines.extend(arrow_line(TOOL_X + NODE_W // 2, TOOL_Y + NODE_H,
                            RESULT_X + NODE_W // 2, RESULT_Y, theme, kind='primary'))
    # RESULT → LLM loopback (left, below main row)
    # Path: result_left → left → up to above LLM → down to LLM bottom
    res_lx = RESULT_X
    res_cy = RESULT_Y + NODE_H // 2
    loop_y = 350
    llm_cx = LLM_X + NODE_W // 2
    llm_bot = LLM_Y + NODE_H
    path = (
        f'M {res_lx},{res_cy} '
        f'L {res_lx - 30},{res_cy} '
        f'L {res_lx - 30},{loop_y} '
        f'L {llm_cx},{loop_y} '
        f'L {llm_cx},{llm_bot}'
    )
    lines.extend(arrow_path(
        path, theme, kind='feedback',
        label_pos=((res_lx - 30 + llm_cx) // 2, loop_y - 12),
        label='tool_result 포함 재요청',
    )
    )

    lines.extend(node(USER_X, USER_Y, NODE_W, NODE_H, 'input', theme, title='사용자', sub='user message'))
    lines.extend(node(LLM_X, LLM_Y, NODE_W, NODE_H, 'model', theme, title='LLM', sub='inference'))
    lines.extend(node(GATE_X, GATE_Y, NODE_W, NODE_H, 'gate', theme, title='판단', sub='stop_reason'))
    lines.extend(node(TOOL_X, TOOL_Y, NODE_W, NODE_H, 'tool', theme, title='툴 실행', sub='your function'))
    lines.extend(node(RESULT_X, RESULT_Y, NODE_W, NODE_H, 'memory', theme, title='tool_result', sub='반환값'))
    lines.extend(node(FINAL_X, FINAL_Y, NODE_W, NODE_H, 'output', theme, title='최종 응답', sub='text'))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 8. Tool 3 종류 — Data / Action / Orchestration
# =====================================================================

def tool_three_kinds(theme):
    CW, CH = 1000, 320
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '툴의 3가지 종류 (OpenAI Practical Guide)', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '무슨 일을 하느냐로 분류 · 안전성 관점이 다름', theme))

    specs = [
        ('tool',   'Data',          'retrieve',      '컨텍스트 조회 (읽기)'),
        ('llm',    'Action',        'mutate',        '상태 변경 (쓰기·결제·발송)'),
        ('memory', 'Orchestration', 'sub-agent',     '다른 에이전트/툴 조합'),
    ]
    xs = layout_centered_row(len(specs), CW, 280, 30)
    y = 110
    node_h = 140

    # Arrows between (no directional — just visual separators)
    for i in range(len(xs) - 1):
        x1 = xs[i] + 280 + 2
        x2 = xs[i + 1] - 2
        cy = y + node_h // 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))

    for x, (role, t, s, d) in zip(xs, specs):
        lines.extend(node(x, y, 280, node_h, role, theme, title=t, sub=s, detail=d))

    lines.extend(svg_footer())
    return '\n'.join(lines)


GENERATORS = [
    ('ch4-api-pipeline',           api_pipeline),
    ('ch4-retry-flow',             retry_flow),
    ('ch5-prompt-anatomy',         prompt_anatomy),
    ('ch5-cot-comparison',         cot_comparison),
    ('ch6-structured-output-flow', structured_output_flow),
    ('ch6-methods-comparison',     output_methods_comparison),
    ('ch7-blocking-vs-stream',     blocking_vs_stream),
    ('ch8-tool-use-loop',          tool_use_loop),
    ('ch8-tool-three-kinds',       tool_three_kinds),
]


if __name__ == '__main__':
    for name, fn in GENERATORS:
        save(name, fn('light'), fn('dark'))
    print(f'\n✓ {len(GENERATORS)} diagrams × 2 themes')
