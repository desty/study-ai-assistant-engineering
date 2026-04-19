"""Part 4 다이어그램 제너레이터.

Ch 15: eval-3layers (평가의 3층), offline-vs-online (두 축)
Ch 16~19: 추후 추가
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

NODE_W, NODE_H = 140, 90


def save(name, light_svg, dark_svg):
    with open(f'{BASE}/{name}.svg', 'w') as f:
        f.write(light_svg)
    with open(f'{BASE}/{name}-dark.svg', 'w') as f:
        f.write(dark_svg)
    os.system(f'rsvg-convert -w 1920 {BASE}/{name}.svg -o {BASE}/{name}.png 2>&1 | head -3')
    print(f'  ✓ {name}')


# =====================================================================
# Ch 15. 평가의 3층 — Retrieval / Generation / E2E
# =====================================================================

def eval_3layers(theme):
    CW, CH = 1080, 520
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '평가의 3층 — 어느 블록의 문제인지 지목한다', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'E2E만 보면 실패 원인이 안 보인다. 층별로 쪼개야 고칠 수 있다.', theme))

    pal = P(theme)
    t = T(theme)

    # 3 rows: each row = layer label (left) + 3 metric nodes
    LABEL_X = 40
    LABEL_W = 180
    NODE_START_X = 260
    NODE_GAP = 20
    ROW_HEIGHT = 120
    Y0 = 100
    MW, MH = 180, 90  # metric box

    rows = [
        {
            'role': 'tool',
            'layer': '1. Retrieval',
            'layer_sub': '검색 품질',
            'question': '필요한 문서를 가져왔는가?',
            'metrics': [
                ('Recall@k', 'top-k 안에\n정답 문서 있음'),
                ('MRR', '정답의 순위\n역수 평균'),
                ('nDCG', '관련도 가중\n랭킹 점수'),
            ],
        },
        {
            'role': 'model',
            'layer': '2. Generation',
            'layer_sub': '생성 품질',
            'question': '그 문서로 올바른 답을 만들었나?',
            'metrics': [
                ('Faithfulness', '답변이 문서에\n근거하는 비율'),
                ('Correctness', '정답과 의미\n일치 여부'),
                ('Coherence', '앞뒤 일관성 ·\n가독성'),
            ],
        },
        {
            'role': 'output',
            'layer': '3. End-to-End',
            'layer_sub': '종합 · 사용자 체감',
            'question': '사용자가 실제로 만족했나?',
            'metrics': [
                ('Helpfulness', '유용성 점수\n(judge/human)'),
                ('Safety', '유해·오답 비율 ·\n거부율'),
                ('Task Success', '의도한 과제\n완수율'),
            ],
        },
    ]

    for i, row in enumerate(rows):
        y = Y0 + i * ROW_HEIGHT
        role = row['role']
        # Left label box
        lines.extend(node(LABEL_X, y, LABEL_W, MH, role, theme,
                          title=row['layer'], sub=row['layer_sub'], detail=row['question']))
        # 3 metric boxes
        for j, (mname, mdetail) in enumerate(row['metrics']):
            mx = NODE_START_X + j * (MW + NODE_GAP)
            # Draw metric box manually (multi-line)
            lines.append(f'  <rect x="{mx}" y="{y}" width="{MW}" height="{MH}" rx="10" fill="{t["node_mask"]}"/>')
            lines.append(f'  <rect x="{mx}" y="{y}" width="{MW}" height="{MH}" rx="10" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.5"/>')
            lines.append(f'  <text x="{mx + MW/2}" y="{y + 30}" text-anchor="middle" font-size="15" font-weight="700" font-family="JetBrains Mono, monospace" fill="{pal[role]["text"]}">{mname}</text>')
            # detail lines
            for k, dline in enumerate(mdetail.split('\n')):
                lines.append(f'  <text x="{mx + MW/2}" y="{y + 56 + k*16}" text-anchor="middle" font-size="11" fill="{pal[role]["sub"]}">{dline}</text>')

    # Bottom tip
    lines.append(f'  <rect x="40" y="475" width="{CW-80}" height="30" rx="6" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="1"/>')
    lines.append(f'  <text x="{CW/2}" y="494" text-anchor="middle" font-size="12" fill="{t["legend_text"]}">E2E가 낮은데 Retrieval은 괜찮다면 → Generation 문제. 반대라면 검색부터 고친다.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 15. Offline vs Online 평가 — 두 축의 역할
# =====================================================================

def offline_vs_online(theme):
    CW, CH = 1040, 460
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Offline vs Online 평가 — 배포 전과 후', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '같은 지표라도 실험실 수치와 실사용 수치는 다르다. 둘 다 본다.', theme))

    pal = P(theme)
    t = T(theme)

    # 2 columns: offline (left) + online (right)
    COL_W = 440
    COL_H = 330
    OFF_X = 40
    ON_X = 560
    COL_Y = 90

    # Offline column (tool / green)
    lines.extend(group_container(OFF_X, COL_Y, COL_W, COL_H, 'OFFLINE · 배포 전', 'tool', theme, dasharray='4,3'))
    lines.extend(group_container(ON_X, COL_Y, COL_W, COL_H, 'ONLINE · 배포 후', 'memory', theme, dasharray='4,3'))

    # Offline content
    off_items = [
        ('언제?', '코드 바꾸기 전 · CI/CD 게이트'),
        ('데이터', '고정 gold set (Ch 16)'),
        ('장점', '재현 가능 · 빠름 · 비용 낮음'),
        ('지표', 'Recall@k · Faithfulness · Judge 점수'),
        ('한계', '실사용자의 진짜 의도를 못 봄'),
    ]
    for i, (k, v) in enumerate(off_items):
        y = COL_Y + 60 + i * 50
        lines.append(f'  <text x="{OFF_X + 20}" y="{y}" font-size="12" font-weight="700" font-family="JetBrains Mono, monospace" fill="{pal["tool"]["text"]}">{k}</text>')
        lines.append(f'  <text x="{OFF_X + 80}" y="{y}" font-size="12" fill="{pal["tool"]["sub"]}">{v}</text>')

    # Online content
    on_items = [
        ('언제?', '카나리 배포 · A/B · 상시 모니터링'),
        ('데이터', '실사용자 로그 · 피드백'),
        ('장점', '진짜 사용성 · 장기 추세'),
        ('지표', '만족도(👍/👎) · 재질문율 · 과제 완수율'),
        ('한계', '노이즈 큼 · 지연 반영 · 원인 분리 어려움'),
    ]
    for i, (k, v) in enumerate(on_items):
        y = COL_Y + 60 + i * 50
        lines.append(f'  <text x="{ON_X + 20}" y="{y}" font-size="12" font-weight="700" font-family="JetBrains Mono, monospace" fill="{pal["memory"]["text"]}">{k}</text>')
        lines.append(f'  <text x="{ON_X + 80}" y="{y}" font-size="12" fill="{pal["memory"]["sub"]}">{v}</text>')

    # Flow arrow between columns
    lines.extend(arrow_line(OFF_X + COL_W + 5, COL_Y + COL_H/2,
                            ON_X - 5, COL_Y + COL_H/2, theme,
                            kind='primary', label='배포'))

    # Feedback loop (online → offline)
    lines.extend(arrow_path(
        f'M {ON_X + 40} {COL_Y + COL_H + 6} C {ON_X + 40} {COL_Y + COL_H + 50}, '
        f'{OFF_X + COL_W - 40} {COL_Y + COL_H + 50}, {OFF_X + COL_W - 40} {COL_Y + COL_H + 6}',
        theme, kind='feedback', label_pos=(CW/2, COL_Y + COL_H + 55),
        label='실패 케이스 → gold set 보강'))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 16. Evalset 구축 파이프라인 — 실사용 로그 → gold set
# =====================================================================

def evalset_pipeline(theme):
    CW, CH = 1120, 420
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Evalset 구축 파이프라인 — 실사용에서 gold 까지', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '평가셋은 한 번 만들고 끝이 아니라 실사용 실패에서 계속 자란다.', theme))

    pal = P(theme)
    t = T(theme)

    # 5-node horizontal flow
    Y = 170
    NW, NH = 180, 100
    GAP = 30
    total = 5 * NW + 4 * GAP
    LEFT = (CW - total) // 2

    steps = [
        ('memory',  '1', '실사용 로그',    'prod traffic',  '질문·응답·👎'),
        ('tool',    '2', '샘플링',        'stratified',    '난이도·도메인 균형'),
        ('input',   '3', '레이블링',      'human / LLM',   'gold answer 작성'),
        ('gate',    '4', '검수',          'QA review',     '이중 체크 · hold-out 분리'),
        ('output',  '5', 'Gold Set',      'versioned',     'git/DVC 관리'),
    ]

    xs = [LEFT + i * (NW + GAP) for i in range(5)]

    # Arrows between
    for i in range(4):
        x1 = xs[i] + NW + 2
        x2 = xs[i+1] - 2
        cy = Y + NH / 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))

    # Nodes with number badges
    for (role, num, title, sub, detail), x in zip(steps, xs):
        lines.extend(node(x, Y, NW, NH + 10, role, theme,
                          num=num, title=title, sub=sub, detail=detail))

    # Loop back from "Gold Set" to "샘플링" — a failed case found online goes back
    # Curve from bottom of node 5 back up to top of node 2
    x_start = xs[4] + NW / 2
    y_start = Y + NH + 14
    x_end = xs[1] + NW / 2
    y_end = Y - 4
    mid_y = y_start + 90
    d = f'M {x_start} {y_start} C {x_start} {mid_y}, {x_end} {mid_y}, {x_end} {y_end}'
    lines.extend(arrow_path(d, theme, kind='feedback',
                            label_pos=(CW / 2, mid_y + 2),
                            label='운영 중 실패 케이스 → 다음 라운드 샘플 풀에 추가'))

    # Bottom bar
    lines.append(f'  <rect x="40" y="370" width="{CW-80}" height="30" rx="6" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="1"/>')
    lines.append(f'  <text x="{CW/2}" y="389" text-anchor="middle" font-size="12" fill="{t["legend_text"]}">권장 최소 규모: QA 30건 · 요약 30건 · 분류 100건 (Ch 15 예고). hold-out 20~30%는 별도 보관.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 16. Coverage Matrix — 난이도 × 도메인 (샘플링 타겟)
# =====================================================================

def coverage_matrix(theme):
    CW, CH = 1040, 460
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Coverage Matrix — 난이도 × 도메인 균형', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '쉬운 FAQ만 모으면 E2E 점수는 올라가지만 실제 품질은 제자리.', theme))

    pal = P(theme)
    t = T(theme)

    # 3×4 grid (rows: 난이도 3단계, cols: 도메인 4개)
    ROWS = ['쉬움', '보통', '어려움']
    COLS = ['FAQ', '정책', '장애대응', '수치·계산']
    # target counts per cell (total ~100)
    TARGETS = [
        [10, 8, 6, 4],   # 쉬움
        [8, 10, 10, 8],  # 보통
        [4, 6, 10, 16],  # 어려움
    ]
    ROLE_MAP = ['output', 'gate', 'error']  # 쉬움·보통·어려움 색

    CELL_W = 140
    CELL_H = 70
    GRID_LEFT = 200
    GRID_TOP = 120

    # Column headers
    for j, col in enumerate(COLS):
        cx = GRID_LEFT + j * CELL_W + CELL_W / 2
        lines.append(f'  <text x="{cx}" y="{GRID_TOP - 16}" text-anchor="middle" font-size="13" font-weight="700" fill="{t["title"]}">{col}</text>')

    # Rows
    for i, row in enumerate(ROWS):
        ry = GRID_TOP + i * CELL_H + CELL_H / 2 + 4
        lines.append(f'  <text x="{GRID_LEFT - 14}" y="{ry}" text-anchor="end" font-size="13" font-weight="700" fill="{t["title"]}">{row}</text>')
        role = ROLE_MAP[i]
        for j, col in enumerate(COLS):
            cx = GRID_LEFT + j * CELL_W
            cy = GRID_TOP + i * CELL_H
            count = TARGETS[i][j]
            # Cell bg
            lines.append(f'  <rect x="{cx}" y="{cy}" width="{CELL_W-6}" height="{CELL_H-6}" rx="6" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1"/>')
            lines.append(f'  <text x="{cx + (CELL_W-6)/2}" y="{cy + 36}" text-anchor="middle" font-size="22" font-weight="700" font-family="JetBrains Mono, monospace" fill="{pal[role]["text"]}">{count}</text>')
            lines.append(f'  <text x="{cx + (CELL_W-6)/2}" y="{cy + 55}" text-anchor="middle" font-size="10" fill="{pal[role]["sub"]}">건</text>')

    # Total
    lines.append(f'  <text x="{CW/2}" y="{GRID_TOP + 3*CELL_H + 36}" text-anchor="middle" font-size="13" font-weight="700" fill="{t["title"]}">합계 = 100건 (분류 태스크 기준 예시)</text>')

    # Side note (right of grid)
    notes_x = GRID_LEFT + 4 * CELL_W + 30
    notes = [
        ('✓ 쉬움 30%',  '회귀 테스트 용'),
        ('✓ 보통 36%',  '일반 사용자 케이스'),
        ('✓ 어려움 36%', '실제 실패가 나오는 구간'),
        ('', ''),
        ('편향 주의',   '한 셀이 0 이면 그 영역은 평가 불가'),
        ('시간 균형',   '분기마다 로그에서 신규 샘플 추가'),
    ]
    for i, (k, v) in enumerate(notes):
        y = GRID_TOP + i * 26
        if k:
            lines.append(f'  <text x="{notes_x}" y="{y}" font-size="11" font-weight="700" fill="{t["label_text"]}" font-family="JetBrains Mono, monospace">{k}</text>')
            lines.append(f'  <text x="{notes_x}" y="{y+14}" font-size="10" fill="{t["legend_text"]}">{v}</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 17. Judge Workflow — Pairwise 비교 + Human calibration 루프
# =====================================================================

def judge_workflow(theme):
    CW, CH = 1120, 460
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'LLM-as-a-Judge — Pairwise 비교와 Human Calibration', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'Judge 점수는 기본 신호일 뿐. 사람 샘플 검수로 주기적 보정한다.', theme))

    pal = P(theme)
    t = T(theme)

    # Layout:
    #  Left: 질문 + 응답 A / 응답 B
    #  Center: Judge LLM
    #  Right: 점수 (A 우세 / B 우세 / tie)
    #  Bottom: Human sample (10%) → 합의율 체크
    NW, NH = 160, 70

    Q_X, Q_Y = 40, 120
    A_X, A_Y = 40, 210
    B_X, B_Y = 40, 300
    JUDGE_X, JUDGE_Y = 360, 210
    SCORE_X, SCORE_Y = 620, 210
    HUMAN_X, HUMAN_Y = 870, 210

    # Arrows
    # Q → Judge
    lines.extend(arrow_line(Q_X + NW, Q_Y + NH/2, JUDGE_X, JUDGE_Y + 30, theme, kind='primary'))
    # A → Judge
    lines.extend(arrow_line(A_X + NW, A_Y + NH/2, JUDGE_X, JUDGE_Y + NH/2 + 20, theme, kind='primary'))
    # B → Judge
    lines.extend(arrow_line(B_X + NW, B_Y + NH/2, JUDGE_X, JUDGE_Y + NH + 20, theme, kind='primary'))
    # Judge → Score
    lines.extend(arrow_line(JUDGE_X + NW + 40, JUDGE_Y + NH/2 + 20, SCORE_X, SCORE_Y + NH/2 + 20, theme,
                            kind='primary', label='판정'))
    # Score → Human (10% sample)
    lines.extend(arrow_line(SCORE_X + NW, SCORE_Y + NH/2 + 20, HUMAN_X, HUMAN_Y + NH/2 + 20, theme,
                            kind='warning', label='10% 샘플'))
    # Human → back to Judge as feedback (calibration)
    x_start = HUMAN_X + 40
    y_start = HUMAN_Y + NH + 40
    x_end = JUDGE_X + NW / 2 + 20
    y_end = JUDGE_Y + NH + 40 + 20
    mid_y = y_start + 100
    d = f'M {x_start} {y_start} C {x_start} {mid_y}, {x_end} {mid_y}, {x_end} {y_end}'
    lines.extend(arrow_path(d, theme, kind='feedback',
                            label_pos=((x_start + x_end) / 2, mid_y + 2),
                            label='합의율 &lt; 0.8 → 프롬프트·rubric 재튜닝'))

    # Nodes
    lines.extend(node(Q_X, Q_Y, NW, NH, 'input', theme, title='질문', sub='user'))
    lines.extend(node(A_X, A_Y, NW, NH, 'token', theme, title='응답 A', sub='model X'))
    lines.extend(node(B_X, B_Y, NW, NH, 'token', theme, title='응답 B', sub='model Y'))
    lines.extend(node(JUDGE_X, JUDGE_Y, NW + 40, NH + 40, 'gate', theme,
                      title='Judge LLM', sub='rubric + A·B', detail='"A 우세 / B 우세 / 무승부"'))
    lines.extend(node(SCORE_X, SCORE_Y, NW, NH + 40, 'output', theme,
                      title='판정 점수', sub='ratio / score', detail='오프라인 지표'))
    lines.extend(node(HUMAN_X, HUMAN_Y, NW, NH + 40, 'memory', theme,
                      title='Human 검수', sub='합의율 계산', detail='κ · agreement'))

    # Bottom bar
    lines.append(f'  <rect x="40" y="410" width="{CW-80}" height="30" rx="6" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="1"/>')
    lines.append(f'  <text x="{CW/2}" y="429" text-anchor="middle" font-size="12" fill="{t["legend_text"]}">A/B 위치를 뒤집어 다시 돌려 위치 편향도 함께 측정. Judge 는 가벼운 Haiku·GPT-4.1-mini 로 시작, 합의율 보고 필요 시 Sonnet 승급.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 17. Judge 편향 4종 — position / length / self-preference / verbosity
# =====================================================================

def judge_biases(theme):
    CW, CH = 1080, 460
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Judge 의 4가지 편향 — 인지하고 보정한다', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '순진하게 Judge 를 쓰면 실제 품질이 아니라 편향이 점수가 된다.', theme))

    pal = P(theme)
    t = T(theme)

    # 2×2 grid of bias cards
    CARD_W, CARD_H = 480, 140
    GAP_X, GAP_Y = 40, 30
    LEFT = (CW - 2 * CARD_W - GAP_X) // 2
    TOP = 100

    biases = [
        {
            'role': 'error',
            'title': '1. Position Bias',
            'sub': 'A·B 순서에 따라 결과가 달라짐',
            'detail': ['Judge 가 첫 번째 응답을 선호하는 경향',
                       '완화: A·B 순서 뒤집어 2회 → 평균',
                       '측정: 뒤집기 전후 결정 일치율 (&lt;0.8 주의)'],
        },
        {
            'role': 'error',
            'title': '2. Length Bias',
            'sub': '긴 응답을 품질 좋다고 착각',
            'detail': ['토큰 많을수록 "자세해 보인다"로 가중',
                       '완화: rubric 에 "간결성도 점수" 명시',
                       '측정: 응답 길이 vs 점수 상관관계 확인'],
        },
        {
            'role': 'error',
            'title': '3. Self-Preference',
            'sub': 'Judge 가 자기 계열 모델을 편애',
            'detail': ['Claude Judge 가 Claude 응답 선호 경향',
                       '완화: Judge 모델과 평가 대상 모델 분리',
                       '측정: 같은 응답을 다른 Judge 로도 평가 비교'],
        },
        {
            'role': 'error',
            'title': '4. Verbosity / Confidence Bias',
            'sub': '자신감 있게 쓴 걸 맞다고 판정',
            'detail': ['hedging 없는 단정적 어조 선호',
                       '완화: rubric 에 "근거 제시 여부" 포함',
                       '측정: 의도적 오답(자신감↑) 섞어 판별력 확인'],
        },
    ]

    for i, b in enumerate(biases):
        col = i % 2
        row = i // 2
        x = LEFT + col * (CARD_W + GAP_X)
        y = TOP + row * (CARD_H + GAP_Y)
        role = b['role']
        # Card
        lines.append(f'  <rect x="{x}" y="{y}" width="{CARD_W}" height="{CARD_H}" rx="10" fill="{t["node_mask"]}"/>')
        lines.append(f'  <rect x="{x}" y="{y}" width="{CARD_W}" height="{CARD_H}" rx="10" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.5"/>')
        # Title
        lines.append(f'  <text x="{x + 20}" y="{y + 28}" font-size="15" font-weight="700" fill="{pal[role]["text"]}">{b["title"]}</text>')
        # Sub
        lines.append(f'  <text x="{x + 20}" y="{y + 48}" font-size="12" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{b["sub"]}</text>')
        # Detail bullets
        for k, dl in enumerate(b['detail']):
            lines.append(f'  <text x="{x + 20}" y="{y + 76 + k*20}" font-size="11" fill="{pal[role]["sub"]}">• {dl}</text>')

    # Bottom bar
    lines.append(f'  <rect x="40" y="400" width="{CW-80}" height="40" rx="6" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="1"/>')
    lines.append(f'  <text x="{CW/2}" y="419" text-anchor="middle" font-size="12" fill="{t["legend_text"]}">각 편향은 독립이 아니라 섞여 나타난다. 1·2 는 pairwise 고유 · 3·4 는 rubric 에서도 발생.</text>')
    lines.append(f'  <text x="{CW/2}" y="433" text-anchor="middle" font-size="11" fill="{t["subtitle"]}">주기적 human sample (&gt;= 주 10건) 으로 drift 모니터링</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 18. 추론 기법 4종 — single / CoT / self-consistency / best-of-N+verifier
# =====================================================================

def reasoning_4methods(theme):
    CW, CH = 1120, 560
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '추론 품질 향상 4기법 — 같은 모델, 다른 전략', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '한 번 묻는 대신, 여러 번·다른 방식으로 묻고 합치면 품질이 오른다.', theme))

    pal = P(theme)
    t = T(theme)

    # 4 rows, each with: [label] [Q] [LLM ops] [Answer]
    ROW_H = 115
    Y0 = 95
    LABEL_X, LABEL_W = 30, 180
    Q_X, Q_W = 230, 60
    OP_X = 320
    ANS_X = 940
    ANS_W = 130

    methods = [
        {
            'role': 'model',
            'title': '① Single (baseline)',
            'sub': '직접 답 하나',
            'cost': 'N=1 · 저비용',
            'structure': ['llm_1'],  # single box
        },
        {
            'role': 'llm',
            'title': '② CoT (Chain-of-Thought)',
            'sub': '"단계별로 생각해"',
            'cost': 'N=1 · 토큰만 ↑',
            'structure': ['cot_chain'],
        },
        {
            'role': 'token',
            'title': '③ Self-Consistency',
            'sub': 'N개 샘플 + 다수결',
            'cost': 'N=5~20 · 비용 ×N',
            'structure': ['parallel_vote'],
        },
        {
            'role': 'gate',
            'title': '④ Best-of-N + Verifier',
            'sub': 'N개 생성 → verifier 선택',
            'cost': 'N=5~20 + verifier',
            'structure': ['parallel_verify'],
        },
    ]

    for i, m in enumerate(methods):
        y = Y0 + i * ROW_H
        role = m['role']
        # Label card on left
        lines.append(f'  <rect x="{LABEL_X}" y="{y + 5}" width="{LABEL_W}" height="{ROW_H - 25}" rx="8" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.3"/>')
        lines.append(f'  <text x="{LABEL_X + 14}" y="{y + 28}" font-size="13" font-weight="700" fill="{pal[role]["text"]}">{m["title"]}</text>')
        lines.append(f'  <text x="{LABEL_X + 14}" y="{y + 48}" font-size="11" fill="{pal[role]["sub"]}">{m["sub"]}</text>')
        lines.append(f'  <text x="{LABEL_X + 14}" y="{y + 68}" font-size="10" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{m["cost"]}</text>')

        # Q node (small)
        qy = y + 20
        lines.append(f'  <rect x="{Q_X}" y="{qy}" width="{Q_W}" height="40" rx="6" fill="{pal["input"]["fill"]}" stroke="{pal["input"]["stroke"]}" stroke-width="1"/>')
        lines.append(f'  <text x="{Q_X + Q_W/2}" y="{qy + 25}" text-anchor="middle" font-size="12" font-weight="700" fill="{pal["input"]["text"]}">Q</text>')

        # Arrow Q → ops
        lines.extend(arrow_line(Q_X + Q_W, qy + 20, OP_X, qy + 20, theme, kind='primary'))

        # Ops visualization
        cx = (OP_X + ANS_X) / 2
        cy = qy + 20

        if m['structure'] == ['llm_1']:
            # Single LLM box
            lines.append(f'  <rect x="{OP_X + 30}" y="{qy}" width="110" height="40" rx="6" fill="{pal["model"]["fill"]}" stroke="{pal["model"]["stroke"]}" stroke-width="1"/>')
            lines.append(f'  <text x="{OP_X + 85}" y="{qy + 25}" text-anchor="middle" font-size="11" font-weight="700" fill="{pal["model"]["text"]}">LLM</text>')
            lines.extend(arrow_line(OP_X + 140, qy + 20, ANS_X, qy + 20, theme, kind='primary'))

        elif m['structure'] == ['cot_chain']:
            # Three small linked steps "Step 1 → Step 2 → Step 3"
            step_w = 90
            step_y = qy
            xs_step = [OP_X + 20, OP_X + 20 + step_w + 20, OP_X + 20 + 2*(step_w + 20)]
            for k, sx in enumerate(xs_step):
                lines.append(f'  <rect x="{sx}" y="{step_y}" width="{step_w}" height="40" rx="6" fill="{pal["llm"]["fill"]}" stroke="{pal["llm"]["stroke"]}" stroke-width="1"/>')
                lines.append(f'  <text x="{sx + step_w/2}" y="{step_y + 25}" text-anchor="middle" font-size="11" fill="{pal["llm"]["text"]}">Step {k+1}</text>')
            for k in range(2):
                x1 = xs_step[k] + step_w
                x2 = xs_step[k+1]
                lines.extend(arrow_line(x1, step_y + 20, x2, step_y + 20, theme, kind='primary'))
            lines.extend(arrow_line(xs_step[-1] + step_w, step_y + 20, ANS_X, step_y + 20, theme, kind='primary'))

        elif m['structure'] == ['parallel_vote']:
            # N parallel LLM calls → vote box
            ny = [qy - 18, qy, qy + 18]
            for k in range(5):
                ey = qy + (k - 2) * 16
                lines.append(f'  <rect x="{OP_X + 20}" y="{ey}" width="100" height="14" rx="4" fill="{pal["token"]["fill"]}" stroke="{pal["token"]["stroke"]}" stroke-width="0.8"/>')
                lines.append(f'  <text x="{OP_X + 70}" y="{ey + 11}" text-anchor="middle" font-size="9" font-family="JetBrains Mono, monospace" fill="{pal["token"]["text"]}">LLM[t={k+1}]</text>')
            # vote box
            vx = OP_X + 170
            lines.append(f'  <rect x="{vx}" y="{qy - 5}" width="110" height="50" rx="6" fill="{pal["gate"]["fill"]}" stroke="{pal["gate"]["stroke"]}" stroke-width="1.2"/>')
            lines.append(f'  <text x="{vx + 55}" y="{qy + 15}" text-anchor="middle" font-size="11" font-weight="700" fill="{pal["gate"]["text"]}">Majority</text>')
            lines.append(f'  <text x="{vx + 55}" y="{qy + 32}" text-anchor="middle" font-size="10" fill="{pal["gate"]["sub"]}">Vote</text>')
            # arrows from each LLM to vote (simple short)
            for k in range(5):
                ey = qy + (k - 2) * 16 + 7
                lines.append(f'  <line x1="{OP_X + 120}" y1="{ey}" x2="{vx}" y2="{qy + 20}" stroke="{t["arrow"]}" stroke-width="0.8"/>')
            lines.extend(arrow_line(vx + 110, qy + 20, ANS_X, qy + 20, theme, kind='primary'))

        elif m['structure'] == ['parallel_verify']:
            # N parallel LLM calls → verifier → best
            for k in range(5):
                ey = qy + (k - 2) * 16
                lines.append(f'  <rect x="{OP_X + 20}" y="{ey}" width="100" height="14" rx="4" fill="{pal["token"]["fill"]}" stroke="{pal["token"]["stroke"]}" stroke-width="0.8"/>')
                lines.append(f'  <text x="{OP_X + 70}" y="{ey + 11}" text-anchor="middle" font-size="9" font-family="JetBrains Mono, monospace" fill="{pal["token"]["text"]}">LLM[t={k+1}]</text>')
            vx = OP_X + 170
            lines.append(f'  <rect x="{vx}" y="{qy - 5}" width="110" height="50" rx="6" fill="{pal["gate"]["fill"]}" stroke="{pal["gate"]["stroke"]}" stroke-width="1.2"/>')
            lines.append(f'  <text x="{vx + 55}" y="{qy + 15}" text-anchor="middle" font-size="11" font-weight="700" fill="{pal["gate"]["text"]}">Verifier</text>')
            lines.append(f'  <text x="{vx + 55}" y="{qy + 32}" text-anchor="middle" font-size="10" fill="{pal["gate"]["sub"]}">(score/test)</text>')
            for k in range(5):
                ey = qy + (k - 2) * 16 + 7
                lines.append(f'  <line x1="{OP_X + 120}" y1="{ey}" x2="{vx}" y2="{qy + 20}" stroke="{t["arrow"]}" stroke-width="0.8"/>')
            lines.extend(arrow_line(vx + 110, qy + 20, ANS_X, qy + 20, theme, kind='success', label='best'))

        # Answer node
        lines.append(f'  <rect x="{ANS_X}" y="{qy}" width="{ANS_W}" height="40" rx="6" fill="{pal["output"]["fill"]}" stroke="{pal["output"]["stroke"]}" stroke-width="1"/>')
        lines.append(f'  <text x="{ANS_X + ANS_W/2}" y="{qy + 25}" text-anchor="middle" font-size="11" font-weight="700" fill="{pal["output"]["text"]}">Answer</text>')

    # Bottom bar
    lines.append(f'  <rect x="40" y="540" width="{CW-80}" height="15" rx="3" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.5"/>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 18. Cost vs Quality — 각 기법의 트레이드오프 (bar comparison)
# =====================================================================

def cost_vs_quality(theme):
    CW, CH = 1000, 440
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Cost vs Quality — 언제 어느 기법을 쓸까', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '같은 모델에서 토큰·호출을 늘리면 품질은 오르지만 비용·지연도 비선형', theme))

    pal = P(theme)
    t = T(theme)

    # 4 bars: methods x (cost, quality)
    methods = [
        ('Single', 'model', 1.0, 0.60),
        ('CoT', 'llm', 1.5, 0.72),
        ('Self-Consistency (N=5)', 'token', 5.0, 0.80),
        ('Best-of-N + Verifier (N=5)', 'gate', 6.0, 0.87),
    ]
    # axes
    AX_L = 280
    AX_R = 920
    BASE_Y = 370
    TOP_Y = 110
    # Quality scale 0.5~1.0 mapped to TOP_Y..BASE_Y
    def qy(q):
        return BASE_Y - (q - 0.5) * (BASE_Y - TOP_Y) / 0.5
    # Cost scale 0~7 mapped to AX_L..AX_R
    def cx(c):
        return AX_L + c / 7.0 * (AX_R - AX_L)

    # Axes
    lines.append(f'  <line x1="{AX_L}" y1="{BASE_Y}" x2="{AX_R}" y2="{BASE_Y}" stroke="{t["arrow_dark"]}" stroke-width="1.2"/>')
    lines.append(f'  <line x1="{AX_L}" y1="{BASE_Y}" x2="{AX_L}" y2="{TOP_Y - 10}" stroke="{t["arrow_dark"]}" stroke-width="1.2"/>')
    # X label
    lines.append(f'  <text x="{(AX_L+AX_R)/2}" y="{BASE_Y + 40}" text-anchor="middle" font-size="12" font-weight="700" fill="{t["title"]}">Cost (호출 수 × 토큰) →</text>')
    # Y label
    lines.append(f'  <text x="{AX_L - 30}" y="{(TOP_Y+BASE_Y)/2}" text-anchor="middle" font-size="12" font-weight="700" fill="{t["title"]}" transform="rotate(-90 {AX_L - 30} {(TOP_Y+BASE_Y)/2})">Quality (judge score) →</text>')
    # X ticks
    for c in [1, 3, 5, 7]:
        xv = cx(c)
        lines.append(f'  <line x1="{xv}" y1="{BASE_Y}" x2="{xv}" y2="{BASE_Y + 5}" stroke="{t["arrow_dark"]}" stroke-width="1"/>')
        lines.append(f'  <text x="{xv}" y="{BASE_Y + 20}" text-anchor="middle" font-size="10" fill="{t["legend_text"]}" font-family="JetBrains Mono, monospace">{c}×</text>')
    # Y ticks
    for q in [0.5, 0.6, 0.7, 0.8, 0.9]:
        yv = qy(q)
        lines.append(f'  <line x1="{AX_L - 5}" y1="{yv}" x2="{AX_L}" y2="{yv}" stroke="{t["arrow_dark"]}" stroke-width="1"/>')
        lines.append(f'  <text x="{AX_L - 10}" y="{yv + 4}" text-anchor="end" font-size="10" fill="{t["legend_text"]}" font-family="JetBrains Mono, monospace">{q:.1f}</text>')

    # Plot points + labels
    for name, role, cost, quality in methods:
        pxv = cx(cost)
        pyv = qy(quality)
        lines.append(f'  <circle cx="{pxv}" cy="{pyv}" r="10" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="2"/>')
        lines.append(f'  <text x="{pxv + 16}" y="{pyv + 4}" font-size="11" font-weight="700" fill="{pal[role]["text"]}">{name}</text>')
        lines.append(f'  <text x="{pxv + 16}" y="{pyv + 18}" font-size="10" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">cost={cost}× · Q={quality:.2f}</text>')

    # Note
    lines.append(f'  <rect x="40" y="100" width="220" height="70" rx="6" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="1"/>')
    lines.append(f'  <text x="54" y="120" font-size="11" font-weight="700" fill="{t["title"]}">예시 수치</text>')
    lines.append(f'  <text x="54" y="138" font-size="10" fill="{t["legend_text"]}">수학 20건 기준 측정</text>')
    lines.append(f'  <text x="54" y="152" font-size="10" fill="{t["legend_text"]}">도메인별로 다름</text>')
    lines.append(f'  <text x="54" y="166" font-size="10" fill="{t["legend_text"]}">반드시 자기 eval 로 확인</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 19. Failure Taxonomy — 실패 원인 5층 + 각 수정 경로
# =====================================================================

def failure_taxonomy(theme):
    CW, CH = 1160, 480
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '실패 분류 Taxonomy — 어느 층의 문제인가', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '"왜 틀렸는가?"를 층별로 쪼개야 수정이 가능하다. LLM 교체는 최후.', theme))

    pal = P(theme)
    t = T(theme)

    # Top: 실패 관찰 (root)
    ROOT_X, ROOT_Y = (CW - 200) // 2, 85
    lines.extend(node(ROOT_X, ROOT_Y, 200, 55, 'error', theme,
                      title='실패 사례 (log)', sub='👎 · low judge score'))

    # 5 branches
    BRANCH_Y = 220
    BRANCHES = [
        ('input',   '1. Prompt',       'system/few-shot\n부족 · 모호',           '프롬프트 재설계\nCh 5 · few-shot 추가'),
        ('memory',  '2. Retrieval',    'top-k 에 정답 없음\n(Ch 12 recall↓)',      'reranker · hybrid\n임베딩 교체'),
        ('tool',    '3. Data',         'chunk 경계 · 오타\ngold doc 품질',          'chunking 재설정\n문서 정제'),
        ('model',   '4. Generation',   '문서 있는데 답을\n왜곡 / hallucination',    'temperature↓\nCoT · Ch 18'),
        ('gate',    '5. Tool / Flow',  'tool call 잘못\n상태 전이 오류',            'tool description\nACI 재설계'),
    ]

    bw = 180
    bh = 130
    gap = 20
    total_w = 5 * bw + 4 * gap
    start_x = (CW - total_w) // 2

    fix_y = BRANCH_Y + bh + 30
    fix_h = 60

    for i, (role, title, issue, fix) in enumerate(BRANCHES):
        bx = start_x + i * (bw + gap)

        # Arrow from root to branch
        lines.extend(arrow_line(ROOT_X + 100, ROOT_Y + 55 + 2,
                                bx + bw / 2, BRANCH_Y - 2, theme, kind='primary'))

        # Branch box
        lines.append(f'  <rect x="{bx}" y="{BRANCH_Y}" width="{bw}" height="{bh}" rx="10" fill="{t["node_mask"]}"/>')
        lines.append(f'  <rect x="{bx}" y="{BRANCH_Y}" width="{bw}" height="{bh}" rx="10" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.5"/>')
        lines.append(f'  <text x="{bx + bw/2}" y="{BRANCH_Y + 28}" text-anchor="middle" font-size="14" font-weight="700" fill="{pal[role]["text"]}">{title}</text>')
        for k, iline in enumerate(issue.split('\n')):
            lines.append(f'  <text x="{bx + bw/2}" y="{BRANCH_Y + 58 + k*18}" text-anchor="middle" font-size="11" fill="{pal[role]["sub"]}">{iline}</text>')

        # Arrow branch → fix
        lines.extend(arrow_line(bx + bw / 2, BRANCH_Y + bh + 2, bx + bw / 2, fix_y - 2, theme, kind='success'))

        # Fix box (dashed outline)
        lines.append(f'  <rect x="{bx + 10}" y="{fix_y}" width="{bw - 20}" height="{fix_h}" rx="6" fill="{t["legend_bg"]}" stroke="{pal["output"]["stroke"]}" stroke-width="1" stroke-dasharray="4,3"/>')
        for k, fline in enumerate(fix.split('\n')):
            lines.append(f'  <text x="{bx + bw/2}" y="{fix_y + 22 + k*16}" text-anchor="middle" font-size="10" fill="{pal["output"]["text"]}" font-family="JetBrains Mono, monospace">{fline}</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 19. Debug Loop — trace → classify → fix → verify
# =====================================================================

def debug_loop(theme):
    CW, CH = 1000, 380
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Debug Loop — 실패 한 건에서 시작해 평가셋을 키운다', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '한 건의 실패 → 분류 → 수정 → 평가셋 합류 → 다음 라운드 회귀 방지', theme))

    pal = P(theme)
    t = T(theme)

    # 4 nodes in a circle-like loop
    NW, NH = 180, 95
    Y = 170
    xs = [60, 300, 540, 780]

    steps = [
        ('tool',   '1', 'Trace',    'LangSmith /\nLangfuse',    '입력·검색·생성 전 과정'),
        ('gate',   '2', 'Classify', '5 택소노미',              'prompt · retrieval · data\ngeneration · tool'),
        ('input',  '3', 'Fix',      'root cause 수정',         '한 층만 · 측정 가능'),
        ('output', '4', 'Verify',   'evalset 에 추가',         '회귀 테스트 · 재현 보장'),
    ]

    for (role, num, title, sub, detail), x in zip(steps, xs):
        lines.extend(node(x, Y, NW, NH + 20, role, theme,
                          num=num, title=title, sub=sub, detail=detail))

    # Horizontal arrows
    for i in range(3):
        x1 = xs[i] + NW + 2
        x2 = xs[i+1] - 2
        cy = Y + (NH + 20) / 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))

    # Loop back (4 → 1)
    x_start = xs[3] + NW / 2
    y_start = Y + NH + 22
    x_end = xs[0] + NW / 2
    y_end = Y - 2
    mid_y = y_start + 80
    d = f'M {x_start} {y_start} C {x_start} {mid_y}, {x_end} {mid_y}, {x_end} {y_end}'
    lines.extend(arrow_path(d, theme, kind='feedback',
                            label_pos=(CW/2, mid_y + 2),
                            label='다음 실패 트리거 시 같은 루프 반복 (영구 개선)'))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# main
# =====================================================================

def main():
    print('Part 4 diagrams:')
    for name, fn in [
        ('ch15-eval-3layers', eval_3layers),
        ('ch15-offline-vs-online', offline_vs_online),
        ('ch16-evalset-pipeline', evalset_pipeline),
        ('ch16-coverage-matrix', coverage_matrix),
        ('ch17-judge-workflow', judge_workflow),
        ('ch17-judge-biases', judge_biases),
        ('ch18-reasoning-4methods', reasoning_4methods),
        ('ch18-cost-vs-quality', cost_vs_quality),
        ('ch19-failure-taxonomy', failure_taxonomy),
        ('ch19-debug-loop', debug_loop),
    ]:
        save(name, fn('light'), fn('dark'))


if __name__ == '__main__':
    main()
