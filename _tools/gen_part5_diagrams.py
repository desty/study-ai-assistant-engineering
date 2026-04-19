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

def main():
    print('Part 5 diagrams:')
    for name, fn in [
        ('ch20-app-vs-agent', app_vs_agent),
        ('ch20-autonomy-levels', autonomy_levels),
        ('ch21-seven-patterns', seven_patterns),
        ('ch21-pattern-decision', pattern_decision),
    ]:
        save(name, fn('light'), fn('dark'))


if __name__ == '__main__':
    main()
