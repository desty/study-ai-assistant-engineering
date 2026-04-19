"""Part 5 다이어그램 제너레이터.

Ch 20: app-vs-agent (단일 호출 vs agentic loop), autonomy-levels (자율성 스펙트럼)
Ch 21~25: 추후 추가
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
# Ch 20. App vs Agent — 단일 호출 vs 루프
# =====================================================================

def app_vs_agent(theme):
    CW, CH = 1120, 460
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'LLM App vs Agent — 같은 LLM, 다른 구조', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '한 번 묻고 끝내면 App. LLM 이 스스로 도구를 골라 루프 돌면 Agent.', theme))

    pal = P(theme)
    t = T(theme)

    COL_W = 490
    COL_H = 330
    APP_X = 40
    AGT_X = 590
    COL_Y = 90

    # Group containers
    lines.extend(group_container(APP_X, COL_Y, COL_W, COL_H, 'LLM APP · 단일 호출', 'input', theme, dasharray='4,3'))
    lines.extend(group_container(AGT_X, COL_Y, COL_W, COL_H, 'AGENT · 루프 + 도구', 'llm', theme, dasharray='4,3'))

    # --- App side: user → LLM → output (linear)
    NW, NH = 110, 55
    app_y = COL_Y + 140
    app_nodes = [
        (APP_X + 30, 'input', 'User', '질문'),
        (APP_X + 180, 'model', 'LLM', '단일 호출'),
        (APP_X + 340, 'output', 'Output', '응답'),
    ]
    for i, (x, role, title, sub) in enumerate(app_nodes):
        lines.extend(node(x, app_y, NW, NH, role, theme, title=title, sub=sub))
    # Arrows app
    for i in range(2):
        x1 = app_nodes[i][0] + NW + 2
        x2 = app_nodes[i+1][0] - 2
        cy = app_y + NH / 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))

    # App traits
    traits = [
        '• 결정론적 · 1 호출',
        '• 입력 → 출력 선형',
        '• 디버깅 쉬움',
        '• 비용·지연 예측 가능',
    ]
    for i, tr in enumerate(traits):
        lines.append(f'  <text x="{APP_X + 30}" y="{COL_Y + 230 + i*22}" font-size="12" fill="{pal["input"]["sub"]}">{tr}</text>')

    # --- Agent side: user → LLM ↔ Tool, with loop
    agt_y = COL_Y + 120
    # User
    lines.extend(node(AGT_X + 30, agt_y, NW, NH, 'input', theme, title='User', sub='질문'))
    # LLM (center)
    llm_x = AGT_X + 200
    lines.extend(node(llm_x, agt_y, NW, NH + 30, 'model', theme, title='LLM', sub='다음 행동 결정', detail='thought/tool'))
    # Tool (right)
    tool_x = AGT_X + 370
    lines.extend(node(tool_x, agt_y, NW, NH + 30, 'tool', theme, title='Tool', sub='실행 결과'))
    # Output (below LLM)
    out_y = agt_y + 160
    lines.extend(node(llm_x, out_y, NW, NH, 'output', theme, title='Output', sub='완료 시'))

    # User → LLM
    lines.extend(arrow_line(AGT_X + 30 + NW + 2, agt_y + NH/2, llm_x, agt_y + (NH+30)/2, theme, kind='primary'))
    # LLM ↔ Tool (two arrows)
    lines.extend(arrow_line(llm_x + NW + 2, agt_y + (NH+30)/2 - 8, tool_x, agt_y + (NH+30)/2 - 8, theme, kind='primary', label='call'))
    lines.extend(arrow_line(tool_x, agt_y + (NH+30)/2 + 18, llm_x + NW + 2, agt_y + (NH+30)/2 + 18, theme, kind='feedback', label='result'))
    # LLM → Output (on done)
    lines.extend(arrow_line(llm_x + NW/2, agt_y + NH + 30 + 2, llm_x + NW/2, out_y - 2, theme, kind='success', label='done'))

    # Agent traits
    traits_agt = [
        '• LLM 이 루프 제어 · N 호출',
        '• 툴 선택·순서를 모델이 결정',
        '• 디버깅 어려움 (trace 필수)',
        '• 비용·지연 비결정적',
    ]
    for i, tr in enumerate(traits_agt):
        lines.append(f'  <text x="{AGT_X + 30}" y="{COL_Y + 310 + i*22}" font-size="12" fill="{pal["llm"]["sub"]}">{tr}</text>')

    # Bottom tip
    lines.append(f'  <rect x="40" y="430" width="{CW-80}" height="20" rx="4" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')
    lines.append(f'  <text x="{CW/2}" y="444" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">결정론적 워크플로우로 풀리면 App. 매번 다른 경로가 필요하면 Agent. 기본은 단일 LLM 로 시작.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 20. 자율성 스펙트럼 — 4단계
# =====================================================================

def autonomy_levels(theme):
    CW, CH = 1080, 420
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '자율성 스펙트럼 — Agent 는 단일 용어가 아니다', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '왼쪽으로 갈수록 제어·예측 가능 · 오른쪽으로 갈수록 자율적·복잡', theme))

    pal = P(theme)
    t = T(theme)

    # 4 stages horizontal
    stages = [
        {
            'role': 'input',
            'title': '① Rule-based',
            'sub': 'if-else · 스크립트',
            'detail': ['완전 결정론', '변경=코드 변경', '디버깅 최강'],
        },
        {
            'role': 'model',
            'title': '② LLM Call',
            'sub': '단일 호출 · RAG',
            'detail': ['프롬프트 = 로직', '결과 확률적', 'Ch 4 ~ 14'],
        },
        {
            'role': 'gate',
            'title': '③ Workflow',
            'sub': 'LLM + 정해진 경로',
            'detail': ['개발자가 단계 지정', 'routing · chaining', 'Ch 21 패턴'],
        },
        {
            'role': 'llm',
            'title': '④ Agent',
            'sub': 'LLM 이 경로 결정',
            'detail': ['while loop · tool use', 'ReAct · planner', '예측 불가 · 비용↑'],
        },
    ]

    SW, SH = 210, 180
    GAP = 30
    total = 4 * SW + 3 * GAP
    LEFT = (CW - total) // 2
    Y = 110

    for i, s in enumerate(stages):
        x = LEFT + i * (SW + GAP)
        role = s['role']
        # Card
        lines.append(f'  <rect x="{x}" y="{Y}" width="{SW}" height="{SH}" rx="12" fill="{t["node_mask"]}"/>')
        lines.append(f'  <rect x="{x}" y="{Y}" width="{SW}" height="{SH}" rx="12" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.5"/>')
        lines.append(f'  <text x="{x + SW/2}" y="{Y + 32}" text-anchor="middle" font-size="15" font-weight="700" fill="{pal[role]["text"]}">{s["title"]}</text>')
        lines.append(f'  <text x="{x + SW/2}" y="{Y + 54}" text-anchor="middle" font-size="12" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{s["sub"]}</text>')
        for k, dl in enumerate(s['detail']):
            lines.append(f'  <text x="{x + 20}" y="{Y + 92 + k*22}" font-size="11" fill="{pal[role]["sub"]}">• {dl}</text>')

    # Bottom arrow — spectrum
    ay = Y + SH + 40
    lines.append(f'  <line x1="{LEFT}" y1="{ay}" x2="{LEFT + total}" y2="{ay}" stroke="{t["arrow_dark"]}" stroke-width="2" marker-end="url(#arr)"/>')
    lines.append(f'  <text x="{LEFT}" y="{ay + 20}" font-size="12" font-weight="700" fill="{t["title"]}">통제·예측 가능</text>')
    lines.append(f'  <text x="{LEFT + total}" y="{ay + 20}" text-anchor="end" font-size="12" font-weight="700" fill="{t["title"]}">자율성·복잡성</text>')

    # Tip
    lines.append(f'  <text x="{CW/2}" y="{ay + 45}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">대부분 제품은 ②③ 로 충분. ④ 를 선택하기 전, 문제가 정말 비결정적인지 먼저 묻는다.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# main
# =====================================================================

# =====================================================================
# Ch 21. 7개 패턴 한 장 (Anthropic 5 + OpenAI 2)
# =====================================================================

def seven_patterns(theme):
    CW, CH = 1200, 700
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Agent 패턴 7종 — Anthropic 5 + OpenAI 2', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '워크플로우 5개(결정론적) + 에이전트 2개(자율). 기본은 단일 호출 + RAG.', theme))

    pal = P(theme)
    t = T(theme)

    # 2 row × 4 col grid (8 cells; last cell empty or for notes)
    CARD_W = 270
    CARD_H = 270
    GAP_X = 18
    GAP_Y = 18
    LEFT = (CW - 4 * CARD_W - 3 * GAP_X) // 2
    TOP = 90

    patterns = [
        {
            'role': 'input', 'cat': 'Workflow',
            'title': '① Prompt Chaining', 'sub': 'LLM → LLM → LLM',
            'desc': '한 출력이 다음 입력. 직선 파이프.',
            'when': '단계별 변환 (초안→교정→요약)',
            'mini': 'chain',
        },
        {
            'role': 'gate', 'cat': 'Workflow',
            'title': '② Routing', 'sub': 'Classifier → 전문 LLM',
            'desc': '입력 유형 분류 후 적합한 경로로.',
            'when': 'FAQ·결제·버그 유형별 응답',
            'mini': 'router',
        },
        {
            'role': 'token', 'cat': 'Workflow',
            'title': '③ Parallelization', 'sub': 'N 호출 병렬',
            'desc': '독립 작업 동시에 → 합침 (voting/가중).',
            'when': '다중 관점 리뷰 · self-consistency',
            'mini': 'parallel',
        },
        {
            'role': 'model', 'cat': 'Workflow',
            'title': '④ Orchestrator-Workers', 'sub': 'Planner → Worker×N',
            'desc': '상위 LLM 이 작업 쪼개 지시.',
            'when': '복잡 리서치·멀티스텝 코딩',
            'mini': 'orchestrator',
        },
        {
            'role': 'memory', 'cat': 'Workflow',
            'title': '⑤ Evaluator-Optimizer', 'sub': 'Gen ↔ Critic 루프',
            'desc': '생성 → 평가 → 재생성. 품질 수렴.',
            'when': '번역·코드 개선·글쓰기',
            'mini': 'eval_loop',
        },
        {
            'role': 'llm', 'cat': 'Agent',
            'title': '⑥ Single Agent', 'sub': 'LLM + Tools loop',
            'desc': 'Ch 20 의 기본 agent. 하나가 루프 주도.',
            'when': '고객지원·데이터 탐색',
            'mini': 'agent',
        },
        {
            'role': 'llm', 'cat': 'Agent',
            'title': '⑦ Multi-Agent', 'sub': 'Manager / Decentralized',
            'desc': '여러 에이전트 역할 분담 (Ch 25).',
            'when': '연구→작성·planner→executor',
            'mini': 'multi',
        },
        {
            'role': 'output', 'cat': 'Default',
            'title': '⓪ 기본 — 단일 LLM + RAG', 'sub': '패턴 도입 전 먼저',
            'desc': '대부분 문제는 단일 호출 + 좋은 프롬프트 + 문서로 충분.',
            'when': '의심되면 먼저 이걸 시도',
            'mini': 'baseline',
        },
    ]

    def draw_mini(x_base, y_base, w, h, kind, role):
        """Draw a tiny schematic inside a card area."""
        cx = x_base + w / 2
        stroke = pal[role]['stroke']
        fill_color = pal[role]['fill']
        nb = lambda bx, by, bw=28, bh=18, lbl='': (
            [f'  <rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="3" fill="{fill_color}" stroke="{stroke}" stroke-width="0.8"/>',
             f'  <text x="{bx+bw/2}" y="{by+bh/2+3}" text-anchor="middle" font-size="8" font-family="JetBrains Mono, monospace" fill="{pal[role]["text"]}">{lbl}</text>']
        )
        arr = lambda x1, y1, x2, y2: [f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{t["arrow"]}" stroke-width="0.8" marker-end="url(#arr)"/>']
        out = []
        y_mid = y_base + h / 2

        if kind == 'chain':
            xs = [x_base + 20, x_base + 70, x_base + 120, x_base + 170, x_base + 220]
            for xi in xs:
                out.extend(nb(xi, y_mid - 9, lbl='LLM'))
            for i in range(4):
                out.extend(arr(xs[i]+28, y_mid, xs[i+1], y_mid))
        elif kind == 'router':
            out.extend(nb(x_base + 20, y_mid - 9, bw=36, lbl='Router'))
            for i, dy in enumerate([-40, 0, 40]):
                out.extend(nb(x_base + 180, y_mid - 9 + dy, lbl=f'L{i+1}'))
                out.extend(arr(x_base + 56, y_mid, x_base + 180, y_mid + dy))
        elif kind == 'parallel':
            for i, dy in enumerate([-40, -15, 15, 40]):
                out.extend(nb(x_base + 80, y_mid - 9 + dy, lbl='LLM'))
            out.extend(nb(x_base + 20, y_mid - 9, lbl='Q'))
            out.extend(nb(x_base + 200, y_mid - 9, bw=36, lbl='merge'))
            for dy in [-40, -15, 15, 40]:
                out.extend(arr(x_base + 48, y_mid, x_base + 80, y_mid + dy))
                out.extend(arr(x_base + 108, y_mid + dy, x_base + 200, y_mid))
        elif kind == 'orchestrator':
            out.extend(nb(x_base + 115, y_base + 15, bw=40, lbl='Plan'))
            for i in range(3):
                wx = x_base + 40 + i * 70
                out.extend(nb(wx, y_base + 80, lbl=f'W{i+1}'))
                out.extend(arr(x_base + 135, y_base + 33, wx + 14, y_base + 80))
            out.extend(nb(x_base + 115, y_base + 130, bw=40, lbl='Merge'))
            for i in range(3):
                wx = x_base + 40 + i * 70
                out.extend(arr(wx + 14, y_base + 98, x_base + 135, y_base + 130))
        elif kind == 'eval_loop':
            out.extend(nb(x_base + 40, y_mid - 9, bw=50, lbl='Gen'))
            out.extend(nb(x_base + 160, y_mid - 9, bw=50, lbl='Critic'))
            out.extend(arr(x_base + 90, y_mid - 2, x_base + 160, y_mid - 2))
            # feedback arrow below
            out.append(f'  <path d="M {x_base+160} {y_mid+7} C {x_base+160} {y_mid+40}, {x_base+90} {y_mid+40}, {x_base+90} {y_mid+7}" stroke="{pal["token"]["stroke"]}" stroke-width="0.8" fill="none" stroke-dasharray="3,2" marker-end="url(#arr-token)"/>')
        elif kind == 'agent':
            out.extend(nb(x_base + 100, y_mid - 9, bw=40, lbl='LLM'))
            out.extend(nb(x_base + 180, y_mid - 9, bw=40, lbl='Tool'))
            out.extend(arr(x_base + 140, y_mid - 2, x_base + 180, y_mid - 2))
            out.append(f'  <path d="M {x_base+180} {y_mid+7} C {x_base+180} {y_mid+40}, {x_base+140} {y_mid+40}, {x_base+140} {y_mid+7}" stroke="{pal["token"]["stroke"]}" stroke-width="0.8" fill="none" stroke-dasharray="3,2" marker-end="url(#arr-token)"/>')
            out.extend(nb(x_base + 30, y_mid - 9, lbl='U'))
            out.extend(arr(x_base + 58, y_mid - 2, x_base + 100, y_mid - 2))
        elif kind == 'multi':
            out.extend(nb(x_base + 115, y_base + 15, bw=40, lbl='Mgr'))
            for i, role_label in enumerate(['Res', 'Plan', 'Crit']):
                wx = x_base + 40 + i * 70
                out.extend(nb(wx, y_base + 90, lbl=role_label))
                out.extend(arr(x_base + 135, y_base + 33, wx + 14, y_base + 90))
                out.extend(arr(wx + 14, y_base + 108, x_base + 135, y_base + 120))
            out.extend(nb(x_base + 115, y_base + 130, bw=40, lbl='Out'))
        elif kind == 'baseline':
            out.extend(nb(x_base + 20, y_mid - 9, lbl='U'))
            out.extend(nb(x_base + 80, y_mid - 9, bw=36, lbl='LLM'))
            out.extend(nb(x_base + 156, y_mid - 9, bw=36, lbl='RAG'))
            out.extend(nb(x_base + 230, y_mid - 9, lbl='Out'))
            out.extend(arr(x_base + 48, y_mid - 2, x_base + 80, y_mid - 2))
            out.extend(arr(x_base + 116, y_mid - 2, x_base + 156, y_mid - 2))
            out.extend(arr(x_base + 192, y_mid - 2, x_base + 230, y_mid - 2))
        return out

    for i, p in enumerate(patterns):
        col = i % 4
        row = i // 4
        x = LEFT + col * (CARD_W + GAP_X)
        y = TOP + row * (CARD_H + GAP_Y)
        role = p['role']
        # Card
        lines.append(f'  <rect x="{x}" y="{y}" width="{CARD_W}" height="{CARD_H}" rx="10" fill="{t["node_mask"]}"/>')
        lines.append(f'  <rect x="{x}" y="{y}" width="{CARD_W}" height="{CARD_H}" rx="10" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.5"/>')
        # Badge for category
        badge_color = {'Workflow': pal['gate']['stroke'], 'Agent': pal['llm']['stroke'], 'Default': pal['output']['stroke']}[p['cat']]
        lines.append(f'  <rect x="{x + CARD_W - 90}" y="{y + 10}" width="80" height="18" rx="9" fill="{badge_color}"/>')
        lines.append(f'  <text x="{x + CARD_W - 50}" y="{y + 23}" text-anchor="middle" font-size="10" font-weight="700" fill="#ffffff" font-family="JetBrains Mono, monospace">{p["cat"]}</text>')
        # Title
        lines.append(f'  <text x="{x + 16}" y="{y + 28}" font-size="14" font-weight="700" fill="{pal[role]["text"]}">{p["title"]}</text>')
        lines.append(f'  <text x="{x + 16}" y="{y + 46}" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{p["sub"]}</text>')
        # Mini schematic area
        mini_y = y + 60
        mini_h = 150
        lines.extend(draw_mini(x, mini_y, CARD_W, mini_h, p['mini'], role))
        # Desc + when
        lines.append(f'  <text x="{x + 16}" y="{y + 225}" font-size="11" fill="{pal[role]["sub"]}">{p["desc"]}</text>')
        lines.append(f'  <text x="{x + 16}" y="{y + 250}" font-size="10" font-family="JetBrains Mono, monospace" fill="{pal[role]["text"]}">쓸 때: {p["when"]}</text>')

    # Bottom note
    lines.append(f'  <text x="{CW/2}" y="{CH - 18}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">패턴 = 해결책 X · 패턴 = 어휘. 문제 먼저, 어휘는 나중. 기본은 항상 ⓪</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 21. 패턴 선택 결정 트리
# =====================================================================

def pattern_decision(theme):
    CW, CH = 1100, 460
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '어느 패턴을 쓸까 — 결정 질문', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '위에서 아래로 질문을 따라가세요. 단순한 것부터 검토.', theme))

    pal = P(theme)
    t = T(theme)

    # Vertical decision flow with yes/no branches
    # Structure:
    # Start → Q1 "단일 LLM+RAG 로 풀리나?" → YES: ⓪  / NO: ↓
    # Q2 "입력 유형 따라 분기만 필요?" → YES: Routing  / NO: ↓
    # Q3 "단계별 변환 파이프?" → YES: Chaining  / NO: ↓
    # Q4 "독립 N 호출 후 합침?" → YES: Parallelization  / NO: ↓
    # Q5 "생성 → 평가 → 재생성?" → YES: Evaluator-Optimizer / NO: ↓
    # Q6 "플래너가 서브태스크 쪼갬?" → YES: Orchestrator-Workers / NO: ↓
    # Q7 "LLM 이 루프 내 툴 선택?" → YES: Single Agent / NO: Multi-Agent

    QW, QH = 360, 42
    Q_X = (CW - QW) // 2
    YES_X = Q_X + QW + 30
    YES_W = 200
    steps = [
        ('단일 LLM + RAG 로 풀리나?',   '⓪ Baseline 사용',            'output'),
        ('입력 유형별 분기만 필요?',     '② Routing',                  'gate'),
        ('단계별 변환 파이프?',          '① Prompt Chaining',          'input'),
        ('독립 N 호출 후 합침?',         '③ Parallelization',          'token'),
        ('생성 → 평가 → 재생성?',        '⑤ Evaluator-Optimizer',      'memory'),
        ('플래너가 서브태스크 쪼갬?',    '④ Orchestrator-Workers',     'model'),
        ('LLM 이 루프 내 툴 선택?',      '⑥ Single Agent',             'llm'),
    ]
    start_y = 90
    gap = 44

    for i, (q, ans, role) in enumerate(steps):
        y = start_y + i * gap
        # Q box
        lines.append(f'  <rect x="{Q_X}" y="{y}" width="{QW}" height="{QH}" rx="8" fill="{pal["gate"]["fill"]}" stroke="{pal["gate"]["stroke"]}" stroke-width="1.2"/>')
        lines.append(f'  <text x="{Q_X + QW/2}" y="{y + QH/2 + 4}" text-anchor="middle" font-size="12" font-weight="700" fill="{pal["gate"]["text"]}">{q}</text>')
        # Yes answer box on right
        lines.append(f'  <rect x="{YES_X}" y="{y}" width="{YES_W}" height="{QH}" rx="8" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.2"/>')
        lines.append(f'  <text x="{YES_X + YES_W/2}" y="{y + QH/2 + 4}" text-anchor="middle" font-size="12" font-weight="700" fill="{pal[role]["text"]}">{ans}</text>')
        # YES arrow Q → ans
        lines.extend(arrow_line(Q_X + QW + 2, y + QH/2, YES_X - 2, y + QH/2, theme, kind='success', label='YES'))
        # Down arrow (NO) to next Q
        if i < len(steps) - 1:
            lines.extend(arrow_line(Q_X + QW/2, y + QH + 2, Q_X + QW/2, y + gap - 2, theme, kind='primary', label='NO'))

    # Below last Q: NO → Multi-Agent
    last_y = start_y + len(steps) * gap
    lines.append(f'  <rect x="{Q_X + QW/2 - YES_W/2}" y="{last_y}" width="{YES_W}" height="{QH}" rx="8" fill="{pal["llm"]["fill"]}" stroke="{pal["llm"]["stroke"]}" stroke-width="1.2"/>')
    lines.append(f'  <text x="{Q_X + QW/2}" y="{last_y + QH/2 + 4}" text-anchor="middle" font-size="12" font-weight="700" fill="{pal["llm"]["text"]}">⑦ Multi-Agent</text>')

    # Caption left
    lines.append(f'  <text x="40" y="120" font-size="11" font-weight="700" fill="{t["title"]}">원칙</text>')
    captions = [
        '위에서 아래로',
        '가장 단순한 답 먼저',
        '⓪ 에서 멈추는 게',
        '80% 의 경우',
        '정답',
    ]
    for i, c in enumerate(captions):
        lines.append(f'  <text x="40" y="{140 + i*18}" font-size="11" fill="{t["legend_text"]}">• {c}</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# main
# =====================================================================

# =====================================================================
# Ch 22. ACI Anatomy — 잘 설계된 툴의 5요소
# =====================================================================

def aci_anatomy(theme):
    CW, CH = 1120, 520
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'ACI Anatomy — 잘 설계된 Tool 의 5요소', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'LLM 은 이 5가지로만 툴을 이해한다. 하나라도 모호하면 실패.', theme))

    pal = P(theme)
    t = T(theme)

    # Central tool schema box
    SW, SH = 480, 380
    SX = 40
    SY = 90
    # Title bar
    lines.append(f'  <rect x="{SX}" y="{SY}" width="{SW}" height="{SH}" rx="12" fill="{pal["tool"]["fill"]}" stroke="{pal["tool"]["stroke"]}" stroke-width="1.8"/>')
    lines.append(f'  <text x="{SX + 20}" y="{SY + 28}" font-size="14" font-weight="700" fill="{pal["tool"]["text"]}" font-family="JetBrains Mono, monospace">tool_schema.json</text>')
    lines.append(f'  <line x1="{SX}" y1="{SY + 42}" x2="{SX + SW}" y2="{SY + 42}" stroke="{pal["tool"]["stroke"]}" stroke-width="1"/>')

    # Schema content lines
    schema = [
        ('', '{'),
        ('①', '  "name": "get_order",'),
        ('②', '  "description": "주문 id 로 주문 상세 정보(상태 · 일수 ·'),
        ('',  '                 사용 여부)를 조회한다. 환불 가능 여부'),
        ('',  '                 판단 시 필수."'),
        ('③', '  "input_schema": {'),
        ('',  '    "type": "object",'),
        ('',  '    "properties": {'),
        ('',  '      "order_id": {'),
        ('',  '        "type": "string",'),
        ('',  '        "pattern": "^O-[0-9]{4}$"'),
        ('',  '      }'),
        ('',  '    },'),
        ('',  '    "required": ["order_id"]'),
        ('',  '  }'),
        ('', '}'),
    ]
    for i, (num, line) in enumerate(schema):
        y = SY + 62 + i * 20
        if num:
            lines.append(f'  <circle cx="{SX + 14}" cy="{y - 4}" r="9" fill="{pal["tool"]["stroke"]}"/>')
            lines.append(f'  <text x="{SX + 14}" y="{y}" text-anchor="middle" font-size="10" font-weight="700" fill="#ffffff">{num}</text>')
        lines.append(f'  <text x="{SX + 32}" y="{y}" font-size="12" font-family="JetBrains Mono, monospace" fill="{pal["tool"]["text"]}">{line}</text>')

    # Right: 5 principles
    RX = SX + SW + 50
    RW = CW - RX - 40
    principles = [
        {
            'num': '①', 'role': 'input',
            'title': 'Name',
            'sub': 'snake_case · 동사 중심',
            'rule': '겹치지 않게 · 의미가 name 에 드러나야',
        },
        {
            'num': '②', 'role': 'gate',
            'title': 'Description',
            'sub': '"무엇을 · 언제 쓰는지"',
            'rule': '1~3 문장 · 선택 기준 포함 · LLM 이 이걸로 고름',
        },
        {
            'num': '③', 'role': 'memory',
            'title': 'Input Schema',
            'sub': 'JSON Schema · type/pattern',
            'rule': 'required 명시 · pattern 으로 형식 강제',
        },
        {
            'num': '④', 'role': 'output',
            'title': 'Return Shape',
            'sub': '간결한 dict/str',
            'rule': '2KB 내외 · 불필요 필드 제거 · 토큰 아끼기',
        },
        {
            'num': '⑤', 'role': 'error',
            'title': 'Error Contract',
            'sub': 'ERROR: <원인> 문자열',
            'rule': 'raise 금지 · LLM 이 보고 재시도 가능하게',
        },
    ]
    for i, p in enumerate(principles):
        y = SY + i * 72
        role = p['role']
        # Num badge
        lines.append(f'  <circle cx="{RX + 18}" cy="{y + 24}" r="16" fill="{pal[role]["stroke"]}"/>')
        lines.append(f'  <text x="{RX + 18}" y="{y + 29}" text-anchor="middle" font-size="14" font-weight="700" fill="#ffffff">{p["num"]}</text>')
        # Title
        lines.append(f'  <text x="{RX + 44}" y="{y + 20}" font-size="14" font-weight="700" fill="{pal[role]["text"]}">{p["title"]}</text>')
        lines.append(f'  <text x="{RX + 44}" y="{y + 36}" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{p["sub"]}</text>')
        lines.append(f'  <text x="{RX + 44}" y="{y + 54}" font-size="11" fill="{pal[role]["sub"]}">• {p["rule"]}</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 22. Approval Flow — Action 툴 human-in-loop
# =====================================================================

def approval_flow(theme):
    CW, CH = 1160, 460
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Approval Flow — 고위험 Action 툴의 human-in-loop', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'Data 툴은 자동 · Action 툴은 승인 · Orchestration 은 상황에 따라', theme))

    pal = P(theme)
    t = T(theme)

    # Row 1: Agent loop top
    # Row 2: Normal path (Data tool - auto)
    # Row 3: Approval path (Action tool)

    NW, NH = 130, 60
    # User
    U_X, U_Y = 40, 180
    lines.extend(node(U_X, U_Y, NW, NH, 'input', theme, title='User', sub='request'))

    # LLM
    LLM_X, LLM_Y = 230, 180
    lines.extend(node(LLM_X, LLM_Y, NW, NH + 20, 'model', theme, title='LLM', sub='tool 선택', detail='risk 분류'))

    # Classifier branch
    BR_X = LLM_X + NW + 80
    # Data path (top)
    DATA_X, DATA_Y = BR_X + 70, 90
    DATA_TOOL_X, DATA_TOOL_Y = DATA_X + NW + 40, DATA_Y
    lines.extend(node(DATA_X, DATA_Y, NW, NH, 'tool', theme, title='Data Tool', sub='auto · safe'))
    lines.extend(node(DATA_TOOL_X, DATA_TOOL_Y, NW, NH, 'output', theme, title='실행', sub='즉시'))

    # Action path (middle)
    ACT_X, ACT_Y = BR_X + 70, 200
    lines.extend(node(ACT_X, ACT_Y, NW, NH, 'gate', theme, title='Action Tool', sub='승인 필요'))
    QUEUE_X = ACT_X + NW + 40
    lines.extend(node(QUEUE_X, ACT_Y, NW, NH, 'memory', theme, title='Approval', sub='queue'))
    HUMAN_X = QUEUE_X + NW + 40
    lines.extend(node(HUMAN_X, ACT_Y, NW, NH, 'memory', theme, title='Human', sub='승인/거부'))
    EXEC_X = HUMAN_X + NW + 40
    lines.extend(node(EXEC_X, ACT_Y, NW, NH, 'output', theme, title='실행', sub='승인 후'))

    # Reject path (bottom)
    REJ_X, REJ_Y = BR_X + 70, 310
    lines.extend(node(REJ_X, REJ_Y, NW, NH, 'error', theme, title='거부', sub='LLM 에 알림'))

    # Arrows
    # user → LLM
    lines.extend(arrow_line(U_X + NW + 2, U_Y + NH/2, LLM_X, LLM_Y + (NH+20)/2, theme, kind='primary'))
    # LLM → Data (top)
    lines.extend(arrow_line(LLM_X + NW + 2, LLM_Y + 20, DATA_X, DATA_Y + NH/2, theme, kind='success', label='safe'))
    # Data → Data tool exec
    lines.extend(arrow_line(DATA_X + NW + 2, DATA_Y + NH/2, DATA_TOOL_X, DATA_TOOL_Y + NH/2, theme, kind='primary'))
    # LLM → Action (middle)
    lines.extend(arrow_line(LLM_X + NW + 2, LLM_Y + (NH+20)/2, ACT_X, ACT_Y + NH/2, theme, kind='warning', label='risky'))
    # Action → Queue → Human → Exec
    lines.extend(arrow_line(ACT_X + NW + 2, ACT_Y + NH/2, QUEUE_X, ACT_Y + NH/2, theme, kind='primary'))
    lines.extend(arrow_line(QUEUE_X + NW + 2, ACT_Y + NH/2, HUMAN_X, ACT_Y + NH/2, theme, kind='primary'))
    lines.extend(arrow_line(HUMAN_X + NW + 2, ACT_Y + NH/2, EXEC_X, ACT_Y + NH/2, theme, kind='success', label='approve'))
    # Human → Reject (diagonal)
    lines.extend(arrow_line(HUMAN_X + NW/2, ACT_Y + NH + 2, REJ_X + NW, REJ_Y + NH/2, theme, kind='escalate', label='reject'))

    # Result back to LLM (feedback)
    lines.extend(arrow_path(
        f'M {DATA_TOOL_X + NW/2} {DATA_TOOL_Y + NH + 2} '
        f'C {DATA_TOOL_X + NW/2} {DATA_TOOL_Y + 150}, '
        f'{LLM_X + NW/2} {LLM_Y + (NH+20) + 50}, '
        f'{LLM_X + NW/2} {LLM_Y + (NH+20) + 2}',
        theme, kind='feedback'))

    # Bottom tip
    lines.append(f'  <rect x="40" y="400" width="{CW-80}" height="40" rx="6" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="1"/>')
    lines.append(f'  <text x="{CW/2}" y="420" text-anchor="middle" font-size="12" fill="{t["legend_text"]}">Data 툴 (조회 · 안전) = 자동. Action 툴 (결제 · 삭제 · 전송) = 승인 큐 경유. 룰은 tool metadata 에 박아둔다.</text>')
    lines.append(f'  <text x="{CW/2}" y="434" text-anchor="middle" font-size="11" fill="{t["subtitle"]}">승인 대기 중 agent 는 일시중지 (LangGraph interrupt · Ch 23)</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# main
# =====================================================================

# =====================================================================
# Ch 23. StateGraph Anatomy — 고객 지원 플로우
# =====================================================================

def stategraph_anatomy(theme):
    CW, CH = 1160, 520
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'LangGraph StateGraph — 고객 지원 flow 예제', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'State 를 공유하는 node 와 edge. Conditional edge 로 분기.', theme))

    pal = P(theme)
    t = T(theme)

    # Left: State schema panel
    SSX, SSY = 40, 100
    SSW, SSH = 280, 380
    lines.append(f'  <rect x="{SSX}" y="{SSY}" width="{SSW}" height="{SSH}" rx="10" fill="{pal["memory"]["fill"]}" stroke="{pal["memory"]["stroke"]}" stroke-width="1.5"/>')
    lines.append(f'  <text x="{SSX + 16}" y="{SSY + 28}" font-size="14" font-weight="700" fill="{pal["memory"]["text"]}" font-family="JetBrains Mono, monospace">class State(TypedDict):</text>')
    lines.append(f'  <line x1="{SSX + 12}" y1="{SSY + 40}" x2="{SSX + SSW - 12}" y2="{SSY + 40}" stroke="{pal["memory"]["stroke"]}" stroke-width="1"/>')
    schema = [
        ('messages', 'list[Msg]', 'add_messages reducer'),
        ('intent', 'str', 'faq / refund / bug'),
        ('order_id', 'str | None', '분류 후 채워짐'),
        ('needs_human', 'bool', 'interrupt 트리거'),
        ('response', 'str', '최종 응답'),
    ]
    for i, (k, ty, cmt) in enumerate(schema):
        y = SSY + 70 + i * 60
        lines.append(f'  <text x="{SSX + 20}" y="{y}" font-size="13" font-weight="700" fill="{pal["memory"]["text"]}" font-family="JetBrains Mono, monospace">{k}: {ty}</text>')
        lines.append(f'  <text x="{SSX + 32}" y="{y + 18}" font-size="11" fill="{pal["memory"]["sub"]}"># {cmt}</text>')
    lines.append(f'  <text x="{SSX + 16}" y="{SSY + SSH - 16}" font-size="10" font-family="JetBrains Mono, monospace" fill="{pal["memory"]["sub"]}">모든 node 가 공유 · 증분 업데이트</text>')

    # Right: Graph
    GX, GY = 360, 100
    NW, NH = 130, 55

    # Nodes layout
    # START (top)
    start_y = GY + 20
    classify_x, classify_y = GX + 280, start_y
    lines.extend(node(classify_x, classify_y, NW, NH, 'input', theme, title='classify', sub='node'))
    # START circle
    lines.append(f'  <circle cx="{classify_x + NW/2}" cy="{start_y - 25}" r="12" fill="{pal["output"]["stroke"]}"/>')
    lines.append(f'  <text x="{classify_x + NW/2}" y="{start_y - 21}" text-anchor="middle" font-size="10" font-weight="700" fill="#ffffff">START</text>')
    lines.extend(arrow_line(classify_x + NW/2, start_y - 13, classify_x + NW/2, start_y - 2, theme, kind='primary'))

    # Below classify: 3 branches (FAQ / Refund / Bug)
    branch_y = classify_y + NH + 80
    faq_x = GX + 60
    refund_x = GX + 280
    bug_x = GX + 500
    lines.extend(node(faq_x, branch_y, NW, NH, 'model', theme, title='faq_answer', sub='node'))
    lines.extend(node(refund_x, branch_y, NW, NH, 'gate', theme, title='refund_check', sub='node'))
    lines.extend(node(bug_x, branch_y, NW, NH, 'error', theme, title='escalate', sub='node'))

    # Conditional edges from classify
    for bx, label in [(faq_x, 'faq'), (refund_x, 'refund'), (bug_x, 'bug')]:
        lines.extend(arrow_line(classify_x + NW/2, classify_y + NH + 2, bx + NW/2, branch_y - 2, theme, kind='warning', label=label))

    # refund_check → approval (interrupt)
    approval_y = branch_y + NH + 70
    approval_x = refund_x
    lines.extend(node(approval_x, approval_y, NW, NH + 10, 'memory', theme, title='interrupt', sub='human approval', detail='pause here'))
    lines.extend(arrow_line(refund_x + NW/2, branch_y + NH + 2, approval_x + NW/2, approval_y - 2, theme, kind='escalate', label='needs_human'))

    # respond node (merge point)
    respond_y = approval_y + NH + 60
    respond_x = classify_x
    lines.extend(node(respond_x, respond_y, NW, NH, 'output', theme, title='respond', sub='node'))
    # All branches converge
    lines.extend(arrow_line(faq_x + NW/2, branch_y + NH + 2, respond_x + NW/2, respond_y - 2, theme, kind='primary'))
    lines.extend(arrow_line(approval_x + NW/2, approval_y + NH + 12, respond_x + NW/2, respond_y - 2, theme, kind='primary', label='approved'))
    lines.extend(arrow_line(bug_x + NW/2, branch_y + NH + 2, respond_x + NW/2, respond_y - 2, theme, kind='primary'))

    # END
    end_y = respond_y + NH + 30
    lines.append(f'  <circle cx="{respond_x + NW/2}" cy="{end_y}" r="12" fill="{pal["error"]["stroke"]}"/>')
    lines.append(f'  <text x="{respond_x + NW/2}" y="{end_y + 4}" text-anchor="middle" font-size="10" font-weight="700" fill="#ffffff">END</text>')
    lines.extend(arrow_line(respond_x + NW/2, respond_y + NH + 2, respond_x + NW/2, end_y - 12, theme, kind='primary'))

    # Checkpoint icons on nodes (small save marker)
    for nx, ny in [(classify_x, classify_y), (refund_x, branch_y), (approval_x, approval_y), (respond_x, respond_y)]:
        lines.append(f'  <circle cx="{nx + NW - 10}" cy="{ny + 10}" r="6" fill="{pal["token"]["stroke"]}"/>')
        lines.append(f'  <text x="{nx + NW - 10}" y="{ny + 13}" text-anchor="middle" font-size="8" font-weight="700" fill="#ffffff">💾</text>')

    # Caption
    lines.append(f'  <text x="{GX + 280}" y="{GY + 500}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">💾 = checkpoint saved (thread_id 별). interrupt 지점에서 resume 가능.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 23. Interrupt · Checkpoint · Resume 흐름
# =====================================================================

def interrupt_flow(theme):
    CW, CH = 1160, 440
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Interrupt · Checkpoint · Resume — 인간 게이트 패턴', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'Agent 를 일시 중지, 상태 저장, 외부 이벤트로 재개. LangGraph 의 킬러 기능.', theme))

    pal = P(theme)
    t = T(theme)

    # Timeline horizontal
    NW, NH = 140, 75
    Y = 150
    xs = [50, 230, 420, 620, 810, 990]
    steps = [
        ('input', 'user 요청', '"환불해줘"', None),
        ('model', 'LLM', '의도 분류\n→ refund', 1),
        ('gate', 'refund_check\nnode', 'risky →\ninterrupt()', 2),
        ('memory', 'Checkpoint', 'state 저장\nthread_id=abc', 3),
        ('memory', 'Human\n승인', 'Slack · 대시보드\n승인 버튼', None),
        ('output', 'Resume', 'invoke(thread=\n abc) 재개', 4),
    ]

    for (role, title, sub, num), x in zip(steps, xs):
        # Multi-line sub support
        sub_lines = sub.split('\n')
        lines.append(f'  <rect x="{x}" y="{Y}" width="{NW}" height="{NH + 20}" rx="10" fill="{t["node_mask"]}"/>')
        lines.append(f'  <rect x="{x}" y="{Y}" width="{NW}" height="{NH + 20}" rx="10" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.5"/>')
        if num:
            lines.append(f'  <circle cx="{x + NW/2}" cy="{Y + 18}" r="13" fill="{pal[role]["stroke"]}"/>')
            lines.append(f'  <text x="{x + NW/2}" y="{Y + 23}" text-anchor="middle" font-size="12" font-weight="700" fill="#ffffff" font-family="JetBrains Mono, monospace">{num}</text>')
            title_y = Y + 46
        else:
            title_y = Y + 24
        lines.append(f'  <text x="{x + NW/2}" y="{title_y}" text-anchor="middle" font-size="12" font-weight="700" fill="{pal[role]["text"]}">{title.split(chr(10))[0]}</text>')
        if '\n' in title:
            lines.append(f'  <text x="{x + NW/2}" y="{title_y + 14}" text-anchor="middle" font-size="12" font-weight="700" fill="{pal[role]["text"]}">{title.split(chr(10))[1]}</text>')
        for k, sl in enumerate(sub_lines):
            sub_y = Y + NH + 5 - (len(sub_lines) - 1) * 7 + k * 14
            lines.append(f'  <text x="{x + NW/2}" y="{sub_y}" text-anchor="middle" font-size="10" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{sl}</text>')

    # Arrows
    for i in range(5):
        x1 = xs[i] + NW + 2
        x2 = xs[i+1] - 2
        cy = Y + (NH + 20) / 2
        kind = 'escalate' if i == 2 else 'primary'  # interrupt arrow special
        label = 'pause' if i == 2 else None
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind=kind, label=label))

    # Note: DB icon for checkpoint
    db_x = xs[3] + NW/2
    db_y = Y + NH + 30 + 30
    lines.append(f'  <ellipse cx="{db_x}" cy="{db_y}" rx="25" ry="8" fill="{pal["memory"]["stroke"]}"/>')
    lines.append(f'  <rect x="{db_x - 25}" y="{db_y - 8}" width="50" height="20" fill="{pal["memory"]["stroke"]}"/>')
    lines.append(f'  <ellipse cx="{db_x}" cy="{db_y + 12}" rx="25" ry="8" fill="{pal["memory"]["stroke"]}"/>')
    lines.append(f'  <text x="{db_x}" y="{db_y + 40}" text-anchor="middle" font-size="10" font-family="JetBrains Mono, monospace" fill="{pal["memory"]["sub"]}">SqliteSaver</text>')
    lines.append(f'  <text x="{db_x}" y="{db_y + 54}" text-anchor="middle" font-size="10" font-family="JetBrains Mono, monospace" fill="{pal["memory"]["sub"]}">PostgresSaver</text>')

    # Arrow checkpoint → DB
    lines.append(f'  <line x1="{db_x}" y1="{Y + NH + 25}" x2="{db_x}" y2="{db_y - 10}" stroke="{pal["memory"]["stroke"]}" stroke-width="1.5" stroke-dasharray="3,2"/>')

    # Time arrow
    lines.append(f'  <line x1="40" y1="{Y + NH + 120}" x2="{CW - 40}" y2="{Y + NH + 120}" stroke="{t["arrow_dark"]}" stroke-width="1.5" marker-end="url(#arr)"/>')
    lines.append(f'  <text x="40" y="{Y + NH + 135}" font-size="10" fill="{t["legend_text"]}" font-family="JetBrains Mono, monospace">t₀</text>')
    lines.append(f'  <text x="{CW - 40}" y="{Y + NH + 135}" text-anchor="end" font-size="10" fill="{t["legend_text"]}" font-family="JetBrains Mono, monospace">시간</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# main
# =====================================================================

# =====================================================================
# Ch 24. Memory Hierarchy — 4계층
# =====================================================================

def memory_hierarchy(theme):
    CW, CH = 1160, 480
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Agent 메모리 4계층 — 보존 기간 × 크기 × 용도', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '인간 기억 구조에서 빌려옴. LLM agent 도 이 계층을 섞어 쓴다.', theme))

    pal = P(theme)
    t = T(theme)

    layers = [
        {
            'role': 'input',
            'name': '① Sensory',
            'dur': '~초',
            'size': '원시 입력',
            'examples': ['사용자 방금 발화',
                          'tool 방금 결과',
                          '즉시 버려짐'],
            'impl': '컨텍스트 직전 토큰',
        },
        {
            'role': 'model',
            'name': '② Working',
            'dur': '세션',
            'size': '수 KB ~ 수십 KB',
            'examples': ['현재 대화 messages',
                          'state 필드 (intent 등)',
                          'scratchpad'],
            'impl': 'LangGraph thread state',
        },
        {
            'role': 'memory',
            'name': '③ Episodic',
            'dur': '수 주 ~ 수 개월',
            'size': '이벤트당 수 KB',
            'examples': ['과거 대화 로그',
                          '특정 사건 (환불 건)',
                          '시간 정보 포함'],
            'impl': 'Store · DB · vectorstore',
        },
        {
            'role': 'token',
            'name': '④ Semantic',
            'dur': '영구',
            'size': '지식 · 선호',
            'examples': ['"사용자는 한국어 선호"',
                          '도메인 규칙',
                          '재사용 가능한 사실'],
            'impl': 'Store (key-value) · 프로필',
        },
    ]

    CW_CARD = 260
    CH_CARD = 310
    GAP = 22
    total = 4 * CW_CARD + 3 * GAP
    LEFT = (CW - total) // 2
    TOP = 100

    for i, layer in enumerate(layers):
        x = LEFT + i * (CW_CARD + GAP)
        y = TOP
        role = layer['role']
        # Card
        lines.append(f'  <rect x="{x}" y="{y}" width="{CW_CARD}" height="{CH_CARD}" rx="12" fill="{t["node_mask"]}"/>')
        lines.append(f'  <rect x="{x}" y="{y}" width="{CW_CARD}" height="{CH_CARD}" rx="12" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.5"/>')
        # Title
        lines.append(f'  <text x="{x + CW_CARD/2}" y="{y + 32}" text-anchor="middle" font-size="17" font-weight="700" fill="{pal[role]["text"]}">{layer["name"]}</text>')
        # Duration · size
        lines.append(f'  <text x="{x + 18}" y="{y + 66}" font-size="11" font-weight="700" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">보존: {layer["dur"]}</text>')
        lines.append(f'  <text x="{x + 18}" y="{y + 84}" font-size="11" font-weight="700" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">크기: {layer["size"]}</text>')
        # Divider
        lines.append(f'  <line x1="{x + 18}" y1="{y + 100}" x2="{x + CW_CARD - 18}" y2="{y + 100}" stroke="{pal[role]["stroke"]}" stroke-width="0.8" stroke-dasharray="3,2"/>')
        # Examples
        lines.append(f'  <text x="{x + 18}" y="{y + 120}" font-size="11" font-weight="700" fill="{pal[role]["text"]}">예시:</text>')
        for k, ex in enumerate(layer['examples']):
            lines.append(f'  <text x="{x + 28}" y="{y + 140 + k*20}" font-size="11" fill="{pal[role]["sub"]}">• {ex}</text>')
        # Impl
        lines.append(f'  <rect x="{x + 14}" y="{y + CH_CARD - 62}" width="{CW_CARD - 28}" height="48" rx="6" fill="{t["legend_bg"]}" stroke="{pal[role]["stroke"]}" stroke-width="0.8" stroke-dasharray="3,2"/>')
        lines.append(f'  <text x="{x + CW_CARD/2}" y="{y + CH_CARD - 42}" text-anchor="middle" font-size="10" font-weight="700" fill="{pal[role]["text"]}" font-family="JetBrains Mono, monospace">구현</text>')
        lines.append(f'  <text x="{x + CW_CARD/2}" y="{y + CH_CARD - 26}" text-anchor="middle" font-size="10" fill="{pal[role]["sub"]}" font-family="JetBrains Mono, monospace">{layer["impl"]}</text>')

    # Bottom arrow — duration spectrum
    ay = TOP + CH_CARD + 25
    lines.append(f'  <line x1="{LEFT}" y1="{ay}" x2="{LEFT + total}" y2="{ay}" stroke="{t["arrow_dark"]}" stroke-width="1.5" marker-end="url(#arr)"/>')
    lines.append(f'  <text x="{LEFT}" y="{ay + 18}" font-size="11" font-weight="700" fill="{t["title"]}">짧음 · 휘발</text>')
    lines.append(f'  <text x="{LEFT + total}" y="{ay + 18}" text-anchor="end" font-size="11" font-weight="700" fill="{t["title"]}">길게 · 영구</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 24. Thread vs Store — LangGraph 2계층
# =====================================================================

def thread_vs_store(theme):
    CW, CH = 1080, 480
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'LangGraph 메모리 — Thread 와 Store 2계층', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'Thread = 한 대화 내부. Store = 여러 대화를 가로지르는 영구 기억.', theme))

    pal = P(theme)
    t = T(theme)

    # Two columns
    COL_W = 490
    COL_H = 340
    TH_X = 40
    ST_X = 550
    COL_Y = 90

    # Thread column
    lines.extend(group_container(TH_X, COL_Y, COL_W, COL_H, 'THREAD · 세션 내 (working memory)', 'model', theme, dasharray='5,3'))
    # Inside thread: 3 turns of same thread
    turn_y = [COL_Y + 50, COL_Y + 130, COL_Y + 210]
    for i, ty in enumerate(turn_y):
        lines.append(f'  <rect x="{TH_X + 30}" y="{ty}" width="{COL_W - 60}" height="60" rx="8" fill="{pal["model"]["fill"]}" stroke="{pal["model"]["stroke"]}" stroke-width="1"/>')
        lines.append(f'  <text x="{TH_X + 50}" y="{ty + 24}" font-size="12" font-weight="700" fill="{pal["model"]["text"]}" font-family="JetBrains Mono, monospace">turn {i+1}</text>')
        lines.append(f'  <text x="{TH_X + 50}" y="{ty + 44}" font-size="11" fill="{pal["model"]["sub"]}">state · messages · tool calls</text>')
    # Arrows between turns (sequential)
    for i in range(2):
        x = TH_X + COL_W / 2
        lines.extend(arrow_line(x, turn_y[i] + 60, x, turn_y[i+1], theme, kind='primary'))
    # Thread ID label
    lines.append(f'  <text x="{TH_X + COL_W/2}" y="{COL_Y + COL_H - 22}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["model"]["sub"]}">thread_id="user42:session-2026-04-19"</text>')
    lines.append(f'  <text x="{TH_X + COL_W/2}" y="{COL_Y + COL_H - 6}" text-anchor="middle" font-size="10" fill="{t["legend_text"]}">세션 끝나면 store 로 압축 · 이관</text>')

    # Store column
    lines.extend(group_container(ST_X, COL_Y, COL_W, COL_H, 'STORE · 세션 간 (long-term)', 'memory', theme, dasharray='5,3'))
    # Inside store: 3 buckets
    buckets = [
        ('user_profile', '{"lang": "ko", "tier": "premium"}', 'semantic'),
        ('past_orders',  'O-1024 (환불), O-0991 (배송 지연)', 'episodic'),
        ('preferences',  '{"tone": "formal", "reply_length": "short"}', 'semantic'),
    ]
    for i, (k, v, kind) in enumerate(buckets):
        by = COL_Y + 50 + i * 78
        lines.append(f'  <rect x="{ST_X + 30}" y="{by}" width="{COL_W - 60}" height="62" rx="8" fill="{pal["memory"]["fill"]}" stroke="{pal["memory"]["stroke"]}" stroke-width="1"/>')
        lines.append(f'  <text x="{ST_X + 50}" y="{by + 22}" font-size="12" font-weight="700" fill="{pal["memory"]["text"]}" font-family="JetBrains Mono, monospace">{k}</text>')
        lines.append(f'  <rect x="{ST_X + COL_W - 110}" y="{by + 10}" width="72" height="16" rx="8" fill="{pal["memory"]["stroke"]}"/>')
        lines.append(f'  <text x="{ST_X + COL_W - 74}" y="{by + 22}" text-anchor="middle" font-size="9" font-weight="700" fill="#ffffff" font-family="JetBrains Mono, monospace">{kind}</text>')
        lines.append(f'  <text x="{ST_X + 50}" y="{by + 42}" font-size="11" fill="{pal["memory"]["sub"]}" font-family="JetBrains Mono, monospace">{v}</text>')
    # User ID label
    lines.append(f'  <text x="{ST_X + COL_W/2}" y="{COL_Y + COL_H - 22}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["memory"]["sub"]}">namespace=("user", "42")</text>')
    lines.append(f'  <text x="{ST_X + COL_W/2}" y="{COL_Y + COL_H - 6}" text-anchor="middle" font-size="10" fill="{t["legend_text"]}">새 세션에서도 같은 user 면 동일 store 공유</text>')

    # Arrow: thread → store (compress)
    lines.extend(arrow_line(TH_X + COL_W + 5, COL_Y + COL_H / 2,
                            ST_X - 5, COL_Y + COL_H / 2, theme,
                            kind='feedback', label='세션 종료 시 추출'))

    # Bottom tip
    lines.append(f'  <rect x="40" y="{COL_Y + COL_H + 30}" width="{CW-80}" height="50" rx="6" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="1"/>')
    lines.append(f'  <text x="{CW/2}" y="{COL_Y + COL_H + 50}" text-anchor="middle" font-size="12" fill="{t["legend_text"]}">Thread = short-term (세션 working) · Store = long-term (user 프로필·과거 이벤트)</text>')
    lines.append(f'  <text x="{CW/2}" y="{COL_Y + COL_H + 68}" text-anchor="middle" font-size="11" fill="{t["subtitle"]}">"사용자 선호 추출 → store 저장 → 다음 세션 시작 시 로드" 가 기본 패턴</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 25. Manager vs Decentralized — 2 multi-agent 패턴
# =====================================================================

def manager_vs_decentralized(theme):
    CW, CH = 1160, 500
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Multi-Agent 2패턴 — Manager vs Decentralized', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '중앙이 지시하냐(Manager) / 동료끼리 넘기냐(Decentralized). 트레이드오프 다름.', theme))

    pal = P(theme)
    t = T(theme)

    COL_W = 500
    COL_H = 360
    LEFT_X = 60
    RIGHT_X = 600
    COL_Y = 90

    lines.extend(group_container(LEFT_X, COL_Y, COL_W, COL_H, 'MANAGER · 중앙 지시', 'model', theme, dasharray='4,3'))
    lines.extend(group_container(RIGHT_X, COL_Y, COL_W, COL_H, 'DECENTRALIZED · 피어 핸드오프', 'llm', theme, dasharray='4,3'))

    # Manager: 중앙 Mgr → 3 workers → Mgr
    NW, NH = 100, 50
    mgr_x = LEFT_X + (COL_W - NW) // 2
    mgr_y = COL_Y + 60
    lines.extend(node(mgr_x, mgr_y, NW, NH, 'model', theme, title='Manager', sub='계획·합치기'))

    w_y = mgr_y + NH + 80
    worker_specs = [(LEFT_X + 80,  'Researcher', 'tool'),
                    (LEFT_X + 200, 'Writer',     'input'),
                    (LEFT_X + 320, 'Critic',     'gate')]
    for (wx, wtitle, wrole) in worker_specs:
        lines.extend(node(wx, w_y, NW, NH, wrole, theme, title=wtitle, sub='worker'))
    # Arrows: Manager → workers (delegate) + workers → Manager (report)
    for (wx, _, _) in worker_specs:
        lines.extend(arrow_line(mgr_x + NW/2, mgr_y + NH + 2, wx + NW/2, w_y - 2, theme, kind='primary'))
        lines.extend(arrow_line(wx + NW/2, w_y + NH + 2, mgr_x + NW/2, mgr_y + NH + 60, theme, kind='feedback'))
    # Final output
    out_y = w_y + NH + 90
    lines.extend(node(mgr_x, out_y, NW, NH, 'output', theme, title='응답', sub='Manager 통합'))
    lines.extend(arrow_line(mgr_x + NW/2, mgr_y + NH + 60 + 15, mgr_x + NW/2, out_y - 2, theme, kind='primary'))

    # Manager traits
    traits_mgr = [
        '✓ 디버깅 쉬움 (중앙 로그)',
        '✓ 실패 격리 용이',
        '✗ Manager 병목 (모든 토큰 통과)',
        '✗ 창발적 협업 제한',
    ]
    for i, tr in enumerate(traits_mgr):
        lines.append(f'  <text x="{LEFT_X + 20}" y="{COL_Y + COL_H - 80 + i*18}" font-size="11" fill="{pal["model"]["sub"]}">{tr}</text>')

    # Decentralized: Linear handoff R → W → C
    dx = [RIGHT_X + 60, RIGHT_X + 190, RIGHT_X + 320]
    dy_ = mgr_y + 70
    d_specs = [(dx[0], 'Researcher', 'tool'),
               (dx[1], 'Writer',     'input'),
               (dx[2], 'Critic',     'gate')]
    for (xx, tt, rr) in d_specs:
        lines.extend(node(xx, dy_, NW, NH, rr, theme, title=tt, sub='peer'))
    # Arrows
    for i in range(2):
        lines.extend(arrow_line(dx[i] + NW + 2, dy_ + NH/2, dx[i+1], dy_ + NH/2, theme, kind='primary', label='handoff'))
    # Loopback (critic → writer if issue) — dashed
    lines.extend(arrow_path(
        f'M {dx[2] + NW/2} {dy_ + NH + 2} C {dx[2] + NW/2} {dy_ + NH + 60}, '
        f'{dx[1] + NW/2} {dy_ + NH + 60}, {dx[1] + NW/2} {dy_ + NH + 2}',
        theme, kind='feedback', label_pos=((dx[1] + dx[2]) / 2 + NW/2, dy_ + NH + 72),
        label='재작성 요청'))
    # Input entry
    inp_y = dy_ + NH + 130
    lines.extend(node(RIGHT_X + 30, inp_y, NW, NH, 'input', theme, title='User', sub='요청'))
    lines.extend(arrow_line(RIGHT_X + 30 + NW + 2, inp_y + NH/2, dx[0] + NW/2 - 20, dy_ + NH + 8, theme, kind='primary'))
    # Output
    lines.extend(node(dx[2] + 50, inp_y, NW, NH, 'output', theme, title='응답', sub='Critic 승인 후'))
    lines.extend(arrow_line(dx[2] + NW/2 + 20, dy_ + NH + 8, dx[2] + 50 + NW/2 - 10, inp_y + NH/2 - 5, theme, kind='primary'))

    # Decentralized traits
    traits_dec = [
        '✓ 각 agent 독립 · 병목 없음',
        '✓ 창발적 협업 · 유연',
        '✗ 무한 토스 루프 위험',
        '✗ 누가 끝낼지 불명확',
    ]
    for i, tr in enumerate(traits_dec):
        lines.append(f'  <text x="{RIGHT_X + 20}" y="{COL_Y + COL_H - 80 + i*18}" font-size="11" fill="{pal["llm"]["sub"]}">{tr}</text>')

    # Bottom
    lines.append(f'  <rect x="40" y="460" width="{CW-80}" height="32" rx="6" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="1"/>')
    lines.append(f'  <text x="{CW/2}" y="481" text-anchor="middle" font-size="12" fill="{t["legend_text"]}">의심되면 Manager. Decentralized 는 문제에 대한 확신이 있을 때만.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 25. Failure Modes — 3 대표 실패 시나리오
# =====================================================================

def failure_modes(theme):
    CW, CH = 1140, 440
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Multi-Agent 3대 실패 — 쪼개기 전에 알아둘 것', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '복잡도는 4배, 실패 모드는 4배 이상. 단일 agent 로 못 푸는 걸 확인한 뒤 도입.', theme))

    pal = P(theme)
    t = T(theme)

    CARD_W = 340
    CARD_H = 300
    GAP = 30
    TOTAL_W = 3 * CARD_W + 2 * GAP
    LEFT = (CW - TOTAL_W) // 2
    Y = 95

    cards = [
        {
            'role': 'error',
            'title': '① Context 누락',
            'sub': 'agent 간 정보 전달 실패',
            'scenario': [
                'Researcher → Writer 로 넘김',
                'Writer 는 원본 문서 못 봄',
                '→ 요약의 요약 (hallucination↑)',
            ],
            'fix': 'Manager 패턴 · shared state\n모든 agent 가 full context 읽게',
        },
        {
            'role': 'error',
            'title': '② 무한 토스 루프',
            'sub': 'peer 간 서로 미룸',
            'scenario': [
                'Writer → Critic → Writer → …',
                '명시적 종료 조건 없음',
                '→ 비용 · 지연 폭발',
            ],
            'fix': 'max_handoffs 상한\nCritic 에 "approve" 명시적 액션',
        },
        {
            'role': 'error',
            'title': '③ 책임 불명확',
            'sub': '누가 최종 결정?',
            'scenario': [
                'Researcher: "데이터 여기 있음"',
                'Writer: "애매한데, 확인해줘"',
                '→ 무한 대기 · 사용자 응답 X',
            ],
            'fix': 'Owner 지정 (default = Manager)\n최종 응답 node 단일화',
        },
    ]

    for i, c in enumerate(cards):
        x = LEFT + i * (CARD_W + GAP)
        role = c['role']
        # Card
        lines.append(f'  <rect x="{x}" y="{Y}" width="{CARD_W}" height="{CARD_H}" rx="10" fill="{t["node_mask"]}"/>')
        lines.append(f'  <rect x="{x}" y="{Y}" width="{CARD_W}" height="{CARD_H}" rx="10" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.5"/>')
        # Title
        lines.append(f'  <text x="{x + 20}" y="{Y + 32}" font-size="16" font-weight="700" fill="{pal[role]["text"]}">{c["title"]}</text>')
        lines.append(f'  <text x="{x + 20}" y="{Y + 54}" font-size="12" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{c["sub"]}</text>')
        # Divider
        lines.append(f'  <line x1="{x + 20}" y1="{Y + 70}" x2="{x + CARD_W - 20}" y2="{Y + 70}" stroke="{pal[role]["stroke"]}" stroke-width="0.8" stroke-dasharray="3,2"/>')
        # Scenario
        lines.append(f'  <text x="{x + 20}" y="{Y + 92}" font-size="11" font-weight="700" fill="{pal[role]["text"]}">시나리오</text>')
        for k, sc in enumerate(c['scenario']):
            lines.append(f'  <text x="{x + 30}" y="{Y + 112 + k*20}" font-size="11" fill="{pal[role]["sub"]}">• {sc}</text>')
        # Fix box
        fix_y = Y + 200
        lines.append(f'  <rect x="{x + 14}" y="{fix_y}" width="{CARD_W - 28}" height="80" rx="6" fill="{t["legend_bg"]}" stroke="{pal["output"]["stroke"]}" stroke-width="1" stroke-dasharray="3,2"/>')
        lines.append(f'  <text x="{x + 24}" y="{fix_y + 20}" font-size="11" font-weight="700" fill="{pal["output"]["text"]}" font-family="JetBrains Mono, monospace">대응</text>')
        for k, fl in enumerate(c['fix'].split('\n')):
            lines.append(f'  <text x="{x + 24}" y="{fix_y + 40 + k*16}" font-size="11" fill="{pal["output"]["text"]}">{fl}</text>')

    # Bottom
    lines.append(f'  <text x="{CW/2}" y="{Y + CARD_H + 30}" text-anchor="middle" font-size="12" fill="{t["legend_text"]}">"단일 agent 로 안 풀린다" 의 증거를 제시할 수 없다면 쪼개지 않는다.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# main
# =====================================================================

def main():
    print('Part 5 diagrams:')
    for name, fn in [
        ('ch20-app-vs-agent', app_vs_agent),
        ('ch20-autonomy-levels', autonomy_levels),
        ('ch21-seven-patterns', seven_patterns),
        ('ch21-pattern-decision', pattern_decision),
        ('ch22-aci-anatomy', aci_anatomy),
        ('ch22-approval-flow', approval_flow),
        ('ch23-stategraph-anatomy', stategraph_anatomy),
        ('ch23-interrupt-flow', interrupt_flow),
        ('ch24-memory-hierarchy', memory_hierarchy),
        ('ch24-thread-vs-store', thread_vs_store),
        ('ch25-manager-vs-decentralized', manager_vs_decentralized),
        ('ch25-failure-modes', failure_modes),
    ]:
        save(name, fn('light'), fn('dark'))


if __name__ == '__main__':
    main()
