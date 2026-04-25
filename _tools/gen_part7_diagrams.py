"""Part 7 다이어그램 제너레이터.

Ch 31: transformer-block (단순화 블록 도식), training-stages (Pretrain → SFT → RLHF/DPO)
Ch 32~34: 추후 추가
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
# Ch 31. Transformer block — simplified anatomy
# =====================================================================

def transformer_block(theme):
    CW, CH = 1180, 600
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Transformer 블록 — 단순화 해부도', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '입력 토큰이 임베딩 → N개 블록(self-attention + FFN) → 다음 토큰 분포로 변환된다.', theme))

    pal = P(theme)
    t = T(theme)

    # Left side — input flow
    NW, NH = 160, 56

    # Token / Embedding column (left)
    LX = 60
    tokens_y = 110
    lines.extend(node(LX, tokens_y, NW, NH, 'input', theme,
                      title='Tokens', sub='"안녕 세계" → [101, 5023, ...]'))

    embed_y = tokens_y + 90
    lines.extend(node(LX, embed_y, NW, NH, 'token', theme,
                      title='Token Embedding', sub='dim = d_model'))

    pos_y = embed_y + 90
    lines.extend(node(LX, pos_y, NW, NH, 'token', theme,
                      title='+ Position (RoPE)', sub='순서 정보 주입'))

    # Arrows down
    for (y1, y2) in [(tokens_y + NH, embed_y), (embed_y + NH, pos_y)]:
        lines.extend(arrow_line(LX + NW/2, y1 + 2, LX + NW/2, y2 - 2, theme, kind='primary'))

    # Block × N (center) — group container
    BX = 320
    BY = 90
    BW = 540
    BH = 380
    lines.extend(group_container(BX, BY, BW, BH, 'TRANSFORMER BLOCK × N (e.g. N=32)', 'model', theme))

    # Inside block: 4 sub-nodes vertically
    SUB_W = 220
    SUB_H = 60
    SUB_X = BX + (BW - SUB_W) // 2 - 60
    sub_y0 = BY + 50

    sub_nodes = [
        ('gate',   'LayerNorm',                 '안정화'),
        ('llm',    'Multi-Head Self-Attention', '토큰끼리 정보 교환'),
        ('gate',   'LayerNorm',                 '안정화'),
        ('model',  'Feed-Forward (FFN/MoE)',    '비선형 변환'),
    ]
    sub_ys = []
    for i, (role, title, sub) in enumerate(sub_nodes):
        sy = sub_y0 + i * (SUB_H + 22)
        sub_ys.append(sy)
        lines.extend(node(SUB_X, sy, SUB_W, SUB_H, role, theme, title=title, sub=sub))

    # Arrows between sub-nodes
    for i in range(3):
        lines.extend(arrow_line(SUB_X + SUB_W/2, sub_ys[i] + SUB_H + 2,
                                SUB_X + SUB_W/2, sub_ys[i+1] - 2, theme, kind='primary'))

    # Residual connections (right side curves)
    res_x = SUB_X + SUB_W + 30
    # Skip 1: around attention (LN + Attn)
    lines.extend(arrow_path(
        f'M {SUB_X + SUB_W} {sub_ys[0] + SUB_H/2} L {res_x} {sub_ys[0] + SUB_H/2} L {res_x} {sub_ys[1] + SUB_H + 14} L {SUB_X + SUB_W - 4} {sub_ys[1] + SUB_H + 14}',
        theme, kind='feedback', label='residual',
        label_pos=(res_x + 50, (sub_ys[0] + sub_ys[1] + SUB_H) / 2),
    ))
    # Skip 2: around FFN
    lines.extend(arrow_path(
        f'M {SUB_X + SUB_W} {sub_ys[2] + SUB_H/2} L {res_x} {sub_ys[2] + SUB_H/2} L {res_x} {sub_ys[3] + SUB_H + 14} L {SUB_X + SUB_W - 4} {sub_ys[3] + SUB_H + 14}',
        theme, kind='feedback', label='residual',
        label_pos=(res_x + 50, (sub_ys[2] + sub_ys[3] + SUB_H) / 2),
    ))

    # Right column — output flow
    RX = 920
    lines.extend(node(RX, embed_y, NW, NH, 'gate', theme,
                      title='LM Head (linear)', sub='hidden → vocab'))
    lines.extend(node(RX, embed_y + 90, NW, NH, 'output', theme,
                      title='Softmax', sub='다음 토큰 확률 분포'))
    lines.extend(node(RX, embed_y + 180, NW, NH, 'output', theme,
                      title='Sample / argmax', sub='다음 토큰 결정'))

    # Arrows
    lines.extend(arrow_line(RX + NW/2, embed_y + NH + 2, RX + NW/2, embed_y + 90 - 2, theme, kind='primary'))
    lines.extend(arrow_line(RX + NW/2, embed_y + 90 + NH + 2, RX + NW/2, embed_y + 180 - 2, theme, kind='primary'))

    # Cross arrows: pos → block · block → LM head
    lines.extend(arrow_line(LX + NW + 2, pos_y + NH/2, BX + 4, BY + BH/2, theme, kind='primary', label='hidden'))
    lines.extend(arrow_line(BX + BW + 2, BY + BH/2, RX - 2, embed_y + NH/2, theme, kind='primary', label='hidden'))

    # Bottom info bar
    lines.append(f'  <rect x="40" y="{CH - 60}" width="{CW-80}" height="44" rx="6" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')
    lines.append(f'  <text x="{CW/2}" y="{CH - 38}" text-anchor="middle" font-size="12" fill="{t["legend_text"]}">d_model · n_heads · n_layers · vocab_size 가 모델 크기를 결정. Llama-3-8B ≈ d=4096 · h=32 · L=32 · V=128k.</text>')
    lines.append(f'  <text x="{CW/2}" y="{CH - 20}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">MoE 는 FFN 자리에 여러 expert 중 일부만 활성. attention 은 그대로.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 31. Training stages — Pretrain → SFT → RLHF/DPO
# =====================================================================

def training_stages(theme):
    CW, CH = 1200, 540
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '학습 3단계 — 같은 모델, 세 번 다듬는다', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'Base 모델은 다음 토큰만 예측. 사람이 쓰기 좋게 만드는 건 SFT 와 정렬(RLHF/DPO).', theme))

    pal = P(theme)
    t = T(theme)

    # 3 stage cards horizontally
    SW, SH = 320, 320
    GAP = 30
    total = 3 * SW + 2 * GAP
    LEFT = (CW - total) // 2
    TOP = 100

    stages = [
        {
            'role': 'input',
            'tag': 'Stage 1',
            'title': 'Pretraining',
            'sub': '대규모 텍스트 · 다음 토큰 예측',
            'data': '데이터: web · code · 책 (수T tokens)',
            'output': '결과: Base 모델',
            'cost': '비용: 수십M~수억 $',
            'who': '주체: 모델 회사 (OpenAI · Anthropic · Meta)',
            'note': '문법·세상 지식이 들어옴.\nChat 처럼 응답하지 않음.',
        },
        {
            'role': 'gate',
            'tag': 'Stage 2',
            'title': 'SFT (Supervised FT)',
            'sub': '지시-응답 쌍 학습',
            'data': '데이터: 수만~수십만 (q,a)',
            'output': '결과: Instruct 모델',
            'cost': '비용: 수K~수십K $',
            'who': '주체: 모델 회사 + 우리 (도메인 SFT)',
            'note': '"질문하면 답한다" 가 들어옴.\nLoRA 로 가능 (Ch 33).',
        },
        {
            'role': 'output',
            'tag': 'Stage 3',
            'title': 'RLHF / DPO',
            'sub': '인간 선호로 정렬',
            'data': '데이터: 수K (chosen, rejected) 쌍',
            'output': '결과: Chat / Aligned 모델',
            'cost': '비용: 수K $ (DPO) ~ 수십K (RLHF)',
            'who': '주체: 모델 회사 (대부분)',
            'note': '안전·톤·사실성 정렬.\nDPO 는 reward model 불필요.',
        },
    ]

    for i, s in enumerate(stages):
        x = LEFT + i * (SW + GAP)
        role = s['role']
        # Card
        lines.append(f'  <rect x="{x}" y="{TOP}" width="{SW}" height="{SH}" rx="14" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="2"/>')
        # Tag badge
        lines.append(f'  <rect x="{x + 16}" y="{TOP + 16}" width="70" height="22" rx="4" fill="{pal[role]["stroke"]}"/>')
        lines.append(f'  <text x="{x + 51}" y="{TOP + 32}" text-anchor="middle" font-size="11" font-weight="700" fill="{t["badge_num_fill"]}" font-family="JetBrains Mono, monospace">{s["tag"]}</text>')
        # Title
        lines.append(f'  <text x="{x + SW/2}" y="{TOP + 64}" text-anchor="middle" font-size="17" font-weight="700" fill="{pal[role]["text"]}">{s["title"]}</text>')
        lines.append(f'  <text x="{x + SW/2}" y="{TOP + 86}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{s["sub"]}</text>')
        # Items
        items = [s['data'], s['output'], s['cost'], s['who']]
        for k, item in enumerate(items):
            lines.append(f'  <text x="{x + 24}" y="{TOP + 124 + k*22}" font-size="11" fill="{pal[role]["sub"]}">{item}</text>')
        # Note
        nx = x + 24
        ny = TOP + 232
        lines.append(f'  <line x1="{x + 20}" y1="{ny - 6}" x2="{x + SW - 20}" y2="{ny - 6}" stroke="{pal[role]["stroke"]}" stroke-width="0.8" stroke-dasharray="3,2"/>')
        for k, ln in enumerate(s['note'].split('\n')):
            lines.append(f'  <text x="{nx}" y="{ny + 14 + k*18}" font-size="11" fill="{pal[role]["text"]}">{ln}</text>')

    # Arrows between stages
    for i in range(2):
        x1 = LEFT + i * (SW + GAP) + SW
        x2 = LEFT + (i + 1) * (SW + GAP)
        cy = TOP + SH/2
        lines.extend(arrow_line(x1 + 2, cy, x2 - 2, cy, theme, kind='primary'))

    # Bottom indicator — what we touch
    bx = LEFT
    by = TOP + SH + 30
    bw = total
    bh = 50
    lines.append(f'  <rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="10" fill="{pal["memory"]["fill"]}" stroke="{pal["memory"]["stroke"]}" stroke-width="1.5"/>')
    lines.append(f'  <text x="{bx + bw/2}" y="{by + 22}" text-anchor="middle" font-size="13" font-weight="700" fill="{pal["memory"]["text"]}">우리가 직접 건드릴 수 있는 단계</text>')
    lines.append(f'  <text x="{bx + bw/2}" y="{by + 40}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["memory"]["sub"]}">Pretraining ✗  ·  SFT (LoRA) ✓  ·  DPO ✓ (소량 데이터로) → Ch 33·34</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 32. Decision tree — when to fine-tune
# =====================================================================

def finetune_decision(theme):
    CW, CH = 1200, 600
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '파인튜닝 결정 트리 — 4 단계 게이트', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '대부분의 "AI 프로젝트 = 파인튜닝" 가정은 틀린다. 4 게이트 모두 통과해야 비로소 검토 시작.', theme))

    pal = P(theme)
    t = T(theme)

    # Vertical decision tree
    Q_W, Q_H = 380, 70
    OPT_W, OPT_H = 200, 50
    Q_X = (CW - Q_W) // 2
    GAP = 40

    questions = [
        ('① Prompt + RAG 로 풀리나?',  'Yes', 'No', 'Prompt/RAG 만 (Ch 4·11)'),
        ('② 평가셋이 충분한가? (수K+)', 'No',  'Yes', '평가셋부터 (Ch 16)'),
        ('③ 데이터 수집·라벨 비용 &lt; 절감?', 'No', 'Yes', '비용 모델 재검토 (Ch 30)'),
        ('④ 매 분기 재학습 운영 가능?', 'No',  'Yes', 'API + prompt 로 (Ch 7·30)'),
    ]

    Y0 = 100
    for i, (q, off_label, on_label, off_action) in enumerate(questions):
        qy = Y0 + i * (Q_H + 50)
        # Question box
        lines.append(f'  <rect x="{Q_X}" y="{qy}" width="{Q_W}" height="{Q_H}" rx="10" fill="{pal["gate"]["fill"]}" stroke="{pal["gate"]["stroke"]}" stroke-width="2"/>')
        lines.append(f'  <text x="{Q_X + Q_W/2}" y="{qy + Q_H/2 + 5}" text-anchor="middle" font-size="14" font-weight="700" fill="{pal["gate"]["text"]}">{q}</text>')
        # Off branch (left exit)
        ox = Q_X - OPT_W - 30
        oy = qy + (Q_H - OPT_H) / 2
        lines.append(f'  <rect x="{ox}" y="{oy}" width="{OPT_W}" height="{OPT_H}" rx="8" fill="{pal["error"]["fill"]}" stroke="{pal["error"]["stroke"]}" stroke-width="1.5"/>')
        lines.append(f'  <text x="{ox + OPT_W/2}" y="{oy + 22}" text-anchor="middle" font-size="11" font-weight="700" fill="{pal["error"]["text"]}">→ {off_label}</text>')
        lines.append(f'  <text x="{ox + OPT_W/2}" y="{oy + 38}" text-anchor="middle" font-size="10" font-family="JetBrains Mono, monospace" fill="{pal["error"]["sub"]}">{off_action}</text>')
        # Q → off arrow
        lines.extend(arrow_line(Q_X, qy + Q_H/2, ox + OPT_W + 2, oy + OPT_H/2, theme, kind='warning', label=off_label))
        # On branch — down to next (or to final at bottom)
        if i < len(questions) - 1:
            lines.extend(arrow_line(Q_X + Q_W/2, qy + Q_H + 2, Q_X + Q_W/2, Y0 + (i+1)*(Q_H + 50) - 2, theme, kind='primary', label=on_label))

    # Final verdict box
    fy = Y0 + len(questions) * (Q_H + 50)
    fw = 460
    fh = 70
    fx = (CW - fw) // 2
    lines.append(f'  <rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" rx="12" fill="{pal["output"]["fill"]}" stroke="{pal["output"]["stroke"]}" stroke-width="2"/>')
    lines.append(f'  <text x="{fx + fw/2}" y="{fy + 30}" text-anchor="middle" font-size="15" font-weight="700" fill="{pal["output"]["text"]}">✓ 파인튜닝 검토 시작</text>')
    lines.append(f'  <text x="{fx + fw/2}" y="{fy + 52}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["output"]["sub"]}">SFT (Ch 33) → 필요 시 DPO (Ch 34)</text>')

    # Last Q → final
    lines.extend(arrow_line(Q_X + Q_W/2, Y0 + (len(questions)-1)*(Q_H+50) + Q_H + 2,
                            Q_X + Q_W/2, fy - 2, theme, kind='success', label='Yes'))

    # Bottom tip
    lines.append(f'  <rect x="40" y="{CH - 35}" width="{CW-80}" height="22" rx="4" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')
    lines.append(f'  <text x="{CW/2}" y="{CH - 19}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">한 게이트만 막혀도 파인튜닝은 보류. 통과 후에도 PoC 로 효과 측정한 뒤 본 학습.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 32. Approach matrix — Prompt vs RAG vs FT vs RLHF
# =====================================================================

def approach_matrix(theme):
    CW, CH = 1240, 540
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '4 접근법 비교 — 무엇이 부족할 때 어디로?', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '문제 유형별 첫 시도. 파인튜닝은 항상 마지막 카드.', theme))

    pal = P(theme)
    t = T(theme)

    # 4 columns
    CW_COL = 280
    GAP = 18
    total = 4 * CW_COL + 3 * GAP
    LEFT = (CW - total) // 2
    TOP = 100
    HEIGHT = 360

    cols = [
        {
            'role': 'input',
            'tag': '①',
            'title': 'Prompt',
            'sub': '0 데이터',
            'good': '형식 변경 · 스타일 · 단일 작업',
            'bad': '도메인 사실 · 대규모 톤 변환',
            'cost': '$ 적음',
            'time': '시간: 분',
            'when': '항상 첫 시도',
        },
        {
            'role': 'tool',
            'tag': '②',
            'title': 'RAG',
            'sub': '문서 + 임베딩',
            'good': '도메인 사실 · 최신 정보 · citation',
            'bad': '톤·말투 · 느린 추론 · 형식 강제',
            'cost': '$$ 인덱싱 + 검색',
            'time': '시간: 일',
            'when': '지식 부족이면 먼저',
        },
        {
            'role': 'gate',
            'tag': '③',
            'title': 'SFT (LoRA)',
            'sub': '수K (q,a) 쌍',
            'good': '도메인 톤·말투 · 출력 형식 안정 · 분류',
            'bad': '새 사실 주입 (비효율)',
            'cost': '$$$ 라벨링 + GPU',
            'time': '시간: 주',
            'when': '톤 / 형식 / 분류 안정 필요',
        },
        {
            'role': 'output',
            'tag': '④',
            'title': 'DPO / RLHF',
            'sub': '수K 선호 쌍',
            'good': '안전 · 정중함 · 거절 정책',
            'bad': '데이터 수집 어려움 · 과적합',
            'cost': '$$$$ 선호 라벨링',
            'time': '시간: 월',
            'when': '품질이 SFT 천장 · 정렬 필요',
        },
    ]

    for i, c in enumerate(cols):
        x = LEFT + i * (CW_COL + GAP)
        role = c['role']
        # Card
        lines.append(f'  <rect x="{x}" y="{TOP}" width="{CW_COL}" height="{HEIGHT}" rx="12" fill="{pal[role]["fill"]}" stroke="{pal[role]["stroke"]}" stroke-width="1.8"/>')
        # Tag + title
        lines.append(f'  <text x="{x + 20}" y="{TOP + 36}" font-size="22" font-weight="700" fill="{pal[role]["text"]}">{c["tag"]}</text>')
        lines.append(f'  <text x="{x + 56}" y="{TOP + 36}" font-size="18" font-weight="700" fill="{pal[role]["text"]}">{c["title"]}</text>')
        lines.append(f'  <text x="{x + 20}" y="{TOP + 56}" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal[role]["sub"]}">{c["sub"]}</text>')

        # Sections
        sections = [
            ('GOOD',  c['good'],  pal[role]['stroke']),
            ('WEAK',  c['bad'],   t['arrow_dark']),
            ('COST',  c['cost'],  pal[role]['sub']),
            ('TIME',  c['time'],  pal[role]['sub']),
            ('WHEN',  c['when'],  pal[role]['stroke']),
        ]
        for k, (lbl, txt, col) in enumerate(sections):
            ly = TOP + 86 + k * 56
            lines.append(f'  <text x="{x + 20}" y="{ly}" font-size="10" font-weight="700" font-family="JetBrains Mono, monospace" fill="{col}">{lbl}</text>')
            # Wrap text simply: split by space if longer than 28 chars
            if len(txt) <= 32:
                lines.append(f'  <text x="{x + 20}" y="{ly + 18}" font-size="11" fill="{pal[role]["text"]}">{txt}</text>')
            else:
                # naive 2-line wrap
                words = txt.split()
                line1, line2 = '', ''
                for w in words:
                    if len(line1) + len(w) <= 28:
                        line1 += (' ' if line1 else '') + w
                    else:
                        line2 += (' ' if line2 else '') + w
                lines.append(f'  <text x="{x + 20}" y="{ly + 18}" font-size="11" fill="{pal[role]["text"]}">{line1}</text>')
                lines.append(f'  <text x="{x + 20}" y="{ly + 32}" font-size="11" fill="{pal[role]["text"]}">{line2}</text>')

    # Bottom flow arrow ① → ② → ③ → ④
    ay = TOP + HEIGHT + 30
    lines.append(f'  <line x1="{LEFT}" y1="{ay}" x2="{LEFT + total}" y2="{ay}" stroke="{t["arrow_dark"]}" stroke-width="2" marker-end="url(#arr)"/>')
    lines.append(f'  <text x="{LEFT}" y="{ay + 22}" font-size="12" font-weight="700" fill="{t["title"]}">시도 순서 · 비용·시간 증가</text>')
    lines.append(f'  <text x="{LEFT + total}" y="{ay + 22}" text-anchor="end" font-size="12" font-weight="700" fill="{t["title"]}">정렬·정밀</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 33. Full FT vs LoRA — weight update visualization
# =====================================================================

def lora_vs_full(theme):
    CW, CH = 1200, 540
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Full FT vs LoRA — 무엇이 학습되나', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'Full FT 는 모든 가중치 W 를 갱신. LoRA 는 W 는 동결, 옆에 작은 A·B 만 학습.', theme))

    pal = P(theme)
    t = T(theme)

    # 2 columns: Full FT (left) vs LoRA (right)
    COL_W = 480
    GAP = 80
    LEFT_X = (CW - 2*COL_W - GAP) // 2
    RIGHT_X = LEFT_X + COL_W + GAP
    TOP = 100
    BLOCK_H = 320

    # Group containers
    lines.extend(group_container(LEFT_X, TOP, COL_W, BLOCK_H, 'FULL FINE-TUNING', 'error', theme))
    lines.extend(group_container(RIGHT_X, TOP, COL_W, BLOCK_H, 'LORA · LOW-RANK ADAPTATION', 'output', theme))

    # === Left side: full FT — single big W block, all flame ===
    BIG_X = LEFT_X + 130
    BIG_Y = TOP + 90
    BIG_W = 220
    BIG_H = 140
    lines.append(f'  <rect x="{BIG_X}" y="{BIG_Y}" width="{BIG_W}" height="{BIG_H}" rx="10" fill="{pal["error"]["fill"]}" stroke="{pal["error"]["stroke"]}" stroke-width="2.5"/>')
    lines.append(f'  <text x="{BIG_X + BIG_W/2}" y="{BIG_Y + 50}" text-anchor="middle" font-size="38" font-weight="700" fill="{pal["error"]["text"]}" font-family="JetBrains Mono, monospace">W</text>')
    lines.append(f'  <text x="{BIG_X + BIG_W/2}" y="{BIG_Y + 88}" text-anchor="middle" font-size="13" fill="{pal["error"]["sub"]}">d × d (수백M~수십B)</text>')
    lines.append(f'  <text x="{BIG_X + BIG_W/2}" y="{BIG_Y + 110}" text-anchor="middle" font-size="13" font-weight="700" fill="{pal["error"]["text"]}">전체 갱신 🔥</text>')
    lines.append(f'  <text x="{BIG_X + BIG_W/2}" y="{BIG_Y + 132}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["error"]["sub"]}">trainable = 100%</text>')

    # Below: stats
    sx = LEFT_X + 30
    sy = BIG_Y + BIG_H + 30
    stats_l = [
        '• VRAM: 8B 모델 ≈ 80 GB+ (옵티마이저 포함)',
        '• 체크포인트: 16~32 GB',
        '• 학습 시간: 며칠 (8B 기준)',
        '• 새 모델 = 새 가중치 전체',
    ]
    for i, s in enumerate(stats_l):
        lines.append(f'  <text x="{sx}" y="{sy + i*22}" font-size="12" fill="{pal["error"]["sub"]}">{s}</text>')

    # === Right side: LoRA — W frozen + small A·B trainable ===
    # Frozen W (left)
    FW_X = RIGHT_X + 60
    FW_Y = TOP + 100
    FW_W = 180
    FW_H = 120
    lines.append(f'  <rect x="{FW_X}" y="{FW_Y}" width="{FW_W}" height="{FW_H}" rx="10" fill="{pal["model"]["fill"]}" stroke="{pal["model"]["stroke"]}" stroke-width="1.5" stroke-dasharray="4,3"/>')
    lines.append(f'  <text x="{FW_X + FW_W/2}" y="{FW_Y + 50}" text-anchor="middle" font-size="32" font-weight="700" fill="{pal["model"]["text"]}" font-family="JetBrains Mono, monospace">W</text>')
    lines.append(f'  <text x="{FW_X + FW_W/2}" y="{FW_Y + 78}" text-anchor="middle" font-size="12" font-weight="700" fill="{pal["model"]["text"]}">동결 🧊</text>')
    lines.append(f'  <text x="{FW_X + FW_W/2}" y="{FW_Y + 100}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["model"]["sub"]}">freeze</text>')

    # + sign
    plus_x = FW_X + FW_W + 18
    plus_y = FW_Y + FW_H/2
    lines.append(f'  <text x="{plus_x}" y="{plus_y + 10}" text-anchor="middle" font-size="36" font-weight="700" fill="{t["title"]}">+</text>')

    # Small A·B (right side, trainable)
    AB_X = plus_x + 30
    A_W, A_H = 35, 100
    B_W, B_H = 100, 35
    A_Y = FW_Y + 10
    # A: tall thin (d × r)
    lines.append(f'  <rect x="{AB_X}" y="{A_Y}" width="{A_W}" height="{A_H}" rx="6" fill="{pal["output"]["fill"]}" stroke="{pal["output"]["stroke"]}" stroke-width="2"/>')
    lines.append(f'  <text x="{AB_X + A_W/2}" y="{A_Y + A_H/2 + 5}" text-anchor="middle" font-size="20" font-weight="700" fill="{pal["output"]["text"]}" font-family="JetBrains Mono, monospace">A</text>')
    lines.append(f'  <text x="{AB_X + A_W/2}" y="{A_Y + A_H + 16}" text-anchor="middle" font-size="9" font-family="JetBrains Mono, monospace" fill="{pal["output"]["sub"]}">d×r</text>')
    # B: short wide (r × d)
    BB_X = AB_X + A_W + 16
    BB_Y = A_Y + (A_H - B_H) / 2
    lines.append(f'  <rect x="{BB_X}" y="{BB_Y}" width="{B_W}" height="{B_H}" rx="6" fill="{pal["output"]["fill"]}" stroke="{pal["output"]["stroke"]}" stroke-width="2"/>')
    lines.append(f'  <text x="{BB_X + B_W/2}" y="{BB_Y + B_H/2 + 5}" text-anchor="middle" font-size="20" font-weight="700" fill="{pal["output"]["text"]}" font-family="JetBrains Mono, monospace">B</text>')
    lines.append(f'  <text x="{BB_X + B_W/2}" y="{BB_Y + B_H + 14}" text-anchor="middle" font-size="9" font-family="JetBrains Mono, monospace" fill="{pal["output"]["sub"]}">r×d</text>')

    # Trainable annotation
    lines.append(f'  <text x="{AB_X + (A_W + B_W) / 2}" y="{A_Y - 12}" text-anchor="middle" font-size="11" font-weight="700" fill="{pal["output"]["text"]}">학습 🔥 (r=8~64)</text>')

    # Effective W' = W + A·B
    eq_y = FW_Y + FW_H + 36
    lines.append(f'  <text x="{RIGHT_X + COL_W/2}" y="{eq_y}" text-anchor="middle" font-size="14" font-family="JetBrains Mono, monospace" fill="{t["title"]}">W\' = W + A·B  ·  trainable ≈ 0.1~1% of full</text>')

    # Stats below
    sxr = RIGHT_X + 30
    syr = eq_y + 24
    stats_r = [
        '• VRAM: 8B 모델 ≈ 16~24 GB (QLoRA 면 ~10 GB)',
        '• 체크포인트: 수십 MB ~ 수백 MB',
        '• 학습 시간: 수 시간',
        '• Adapter 만 저장 · 베이스 공유 · 합치기 가능',
    ]
    for i, s in enumerate(stats_r):
        lines.append(f'  <text x="{sxr}" y="{syr + i*22}" font-size="12" fill="{pal["output"]["sub"]}">{s}</text>')

    # Bottom tip
    lines.append(f'  <rect x="40" y="{CH - 35}" width="{CW-80}" height="22" rx="4" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')
    lines.append(f'  <text x="{CW/2}" y="{CH - 19}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">대부분의 도메인 SFT 는 LoRA 로 충분. Full FT 는 base 모델 자체를 만들 때만.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 33. QLoRA training pipeline — 5 steps
# =====================================================================

def qlora_pipeline(theme):
    CW, CH = 1200, 480
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'QLoRA 학습 파이프라인 — 5 단계', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'Colab T4 (16GB) 한 장으로 8B 모델 SFT. 4-bit 로 메모리 압축 → LoRA 만 학습.', theme))

    pal = P(theme)
    t = T(theme)

    NW, NH = 180, 90
    GAP = 18
    total = 5 * NW + 4 * GAP
    LEFT = (CW - total) // 2
    Y = 130

    steps = [
        ('input',  '① Data',          'jsonl (q,a)',     'apply_chat_template'),
        ('model',  '② Base + 4bit',    'bnb 4bit · NF4',  'load_in_4bit=True'),
        ('output', '③ LoRA 부착',      'PeftModel',       'r=16, alpha=32'),
        ('llm',    '④ Trainer',        'SFTTrainer',      'epochs=3 · lr=2e-4'),
        ('token',  '⑤ Adapter 저장',   'save_pretrained', '~50MB · merge 가능'),
    ]

    xs = [LEFT + i * (NW + GAP) for i in range(5)]
    for i, (role, title, sub, detail) in enumerate(steps):
        lines.extend(node(xs[i], Y, NW, NH + 30, role, theme, title=title, sub=sub, detail=detail))

    cy = Y + (NH + 30) / 2
    for i in range(4):
        x1 = xs[i] + NW + 2
        x2 = xs[i + 1] - 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))

    # Memory bar — visualize VRAM usage
    bar_y = Y + NH + 30 + 60
    bar_h = 36
    bar_x = LEFT
    bar_w = total
    lines.append(f'  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="8" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')

    # Segments
    seg = [
        ('Base 4-bit', 0.55, pal['model']),
        ('LoRA',       0.05, pal['output']),
        ('Activations', 0.20, pal['gate']),
        ('Optimizer',   0.10, pal['llm']),
        ('Headroom',    0.10, None),
    ]
    cur_x = bar_x
    for label, frac, color in seg:
        seg_w = bar_w * frac
        if color:
            lines.append(f'  <rect x="{cur_x}" y="{bar_y}" width="{seg_w}" height="{bar_h}" rx="8" fill="{color["fill"]}" stroke="{color["stroke"]}" stroke-width="1"/>')
            lines.append(f'  <text x="{cur_x + seg_w/2}" y="{bar_y + 16}" text-anchor="middle" font-size="11" font-weight="700" fill="{color["text"]}">{label}</text>')
            lines.append(f'  <text x="{cur_x + seg_w/2}" y="{bar_y + 30}" text-anchor="middle" font-size="10" font-family="JetBrains Mono, monospace" fill="{color["sub"]}">{int(frac*100)}%</text>')
        else:
            lines.append(f'  <text x="{cur_x + seg_w/2}" y="{bar_y + 22}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">{label} {int(frac*100)}%</text>')
        cur_x += seg_w

    lines.append(f'  <text x="{bar_x}" y="{bar_y - 10}" font-size="11" font-weight="700" fill="{t["title"]}" font-family="JetBrains Mono, monospace">VRAM 분배 (T4 16GB · 8B 모델 QLoRA)</text>')

    # Bottom tip
    lines.append(f'  <rect x="40" y="{CH - 35}" width="{CW-80}" height="22" rx="4" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')
    lines.append(f'  <text x="{CW/2}" y="{CH - 19}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">베이스가 메모리 절반. activation 이 둘째. LoRA 자체는 거의 0. seq_len · batch 줄여 activation 압축.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 34. SFT vs DPO vs RLHF — alignment pipeline comparison
# =====================================================================

def alignment_compare(theme):
    CW, CH = 1240, 540
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '정렬 3 방식 — SFT · DPO · RLHF', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '같은 Base 에서 출발해 사람 선호로 다듬는 세 길. DPO 가 RLHF 의 단순화 버전이라 우선순위.', theme))

    pal = P(theme)
    t = T(theme)

    # 3 horizontal pipelines (rows)
    ROW_H = 130
    Y_START = 100
    NW, NH = 130, 60

    # Row 1: SFT
    sft_y = Y_START
    lines.append(f'  <text x="60" y="{sft_y + ROW_H/2 - 5}" font-size="15" font-weight="700" fill="{pal["gate"]["text"]}">SFT</text>')
    lines.append(f'  <text x="60" y="{sft_y + ROW_H/2 + 14}" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["gate"]["sub"]}">데이터: (q, a)</text>')
    sft_nodes = [
        (200, 'input',  'Base',     'pretrained'),
        (380, 'token',  '(q, a) 쌍', '수K~수십K'),
        (580, 'gate',   'SFT',      'next-token loss'),
        (780, 'output', 'Instruct', 'chat 가능'),
    ]
    for x, role, title, sub in sft_nodes:
        lines.extend(node(x, sft_y + (ROW_H - NH)/2, NW, NH, role, theme, title=title, sub=sub))
    for i in range(3):
        x1 = sft_nodes[i][0] + NW + 2
        x2 = sft_nodes[i+1][0] - 2
        cy = sft_y + ROW_H/2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))

    # Row 2: DPO
    dpo_y = Y_START + ROW_H + 20
    lines.append(f'  <text x="60" y="{dpo_y + ROW_H/2 - 5}" font-size="15" font-weight="700" fill="{pal["output"]["text"]}">DPO</text>')
    lines.append(f'  <text x="60" y="{dpo_y + ROW_H/2 + 14}" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["output"]["sub"]}">데이터: (q, ✓, ✗)</text>')
    dpo_nodes = [
        (200, 'gate',   'Instruct', 'SFT 후'),
        (380, 'memory', '선호 쌍',   'chosen/rejected'),
        (580, 'output', 'DPO loss', 'reward 식 X'),
        (780, 'output', 'Aligned',  '톤·정중함'),
    ]
    for x, role, title, sub in dpo_nodes:
        lines.extend(node(x, dpo_y + (ROW_H - NH)/2, NW, NH, role, theme, title=title, sub=sub))
    for i in range(3):
        x1 = dpo_nodes[i][0] + NW + 2
        x2 = dpo_nodes[i+1][0] - 2
        cy = dpo_y + ROW_H/2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))

    # Row 3: RLHF
    rlhf_y = Y_START + 2 * (ROW_H + 20)
    lines.append(f'  <text x="60" y="{rlhf_y + ROW_H/2 - 5}" font-size="15" font-weight="700" fill="{pal["error"]["text"]}">RLHF</text>')
    lines.append(f'  <text x="60" y="{rlhf_y + ROW_H/2 + 14}" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["error"]["sub"]}">데이터: (q, ✓, ✗)</text>')
    rlhf_nodes = [
        (200, 'gate',   'Instruct', 'SFT 후'),
        (380, 'memory', 'Reward Model', '선호로 학습'),
        (580, 'error',  'PPO',       'RL 루프'),
        (780, 'output', 'Aligned',   '복잡·불안정'),
    ]
    for x, role, title, sub in rlhf_nodes:
        lines.extend(node(x, rlhf_y + (ROW_H - NH)/2, NW, NH, role, theme, title=title, sub=sub))
    for i in range(3):
        x1 = rlhf_nodes[i][0] + NW + 2
        x2 = rlhf_nodes[i+1][0] - 2
        cy = rlhf_y + ROW_H/2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))

    # Right side — comparison panel
    panel_x = 950
    panel_y = Y_START
    panel_w = 250
    panel_h = 3 * ROW_H + 40
    lines.append(f'  <rect x="{panel_x}" y="{panel_y}" width="{panel_w}" height="{panel_h}" rx="10" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="1"/>')
    lines.append(f'  <text x="{panel_x + 16}" y="{panel_y + 24}" font-size="13" font-weight="700" fill="{t["title"]}">비교 요약</text>')
    note = [
        ('SFT', '· 가장 단순', '· 새 행동 학습', '· 거절·정렬 약함', ''),
        ('DPO', '· reward 모델 X', '· 안정 · 빠름', '· 5K 쌍이면 OK', '· 2026 표준'),
        ('RLHF', '· reward + PPO', '· 데이터 효율 ↑', '· 불안정 · 비쌈', '· 대형사만'),
    ]
    yy = panel_y + 52
    for label, *items in note:
        lines.append(f'  <text x="{panel_x + 16}" y="{yy}" font-size="12" font-weight="700" fill="{t["title"]}">{label}</text>')
        yy += 18
        for it in items:
            if it:
                lines.append(f'  <text x="{panel_x + 24}" y="{yy}" font-size="11" fill="{t["legend_text"]}">{it}</text>')
                yy += 16
        yy += 6

    # Bottom tip
    lines.append(f'  <rect x="40" y="{CH - 35}" width="{CW-80}" height="22" rx="4" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')
    lines.append(f'  <text x="{CW/2}" y="{CH - 19}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">우리 첫 시도는 SFT. 거절 톤·정렬이 SFT 천장에 부딪히면 DPO. RLHF 는 안 가도 됨.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 34. Distillation pipeline — Teacher → Student
# =====================================================================

def distillation(theme):
    CW, CH = 1180, 480
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '증류 (Distillation) — 큰 모델로 작은 모델 가르치기', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'Teacher (Opus) 가 만든 답을 Student (Haiku) 가 학습. 비용·지연 절감 + 도메인 특화.', theme))

    pal = P(theme)
    t = T(theme)

    NW, NH = 160, 80

    # Stage 1: Unlabeled queries
    q_x, q_y = 60, 200
    lines.extend(node(q_x, q_y, NW, NH, 'input', theme, title='Unlabeled Q',
                      sub='log · 합성', detail='수K~수만'))

    # Stage 2: Teacher (large model)
    tch_x, tch_y = 280, 130
    lines.append(f'  <rect x="{tch_x}" y="{tch_y}" width="{NW + 40}" height="{NH + 60}" rx="14" fill="{pal["llm"]["fill"]}" stroke="{pal["llm"]["stroke"]}" stroke-width="2.5"/>')
    lines.append(f'  <text x="{tch_x + (NW+40)/2}" y="{tch_y + 36}" text-anchor="middle" font-size="16" font-weight="700" fill="{pal["llm"]["text"]}">Teacher</text>')
    lines.append(f'  <text x="{tch_x + (NW+40)/2}" y="{tch_y + 60}" text-anchor="middle" font-size="13" font-family="JetBrains Mono, monospace" fill="{pal["llm"]["sub"]}">Opus / GPT-4</text>')
    lines.append(f'  <text x="{tch_x + (NW+40)/2}" y="{tch_y + 86}" text-anchor="middle" font-size="11" fill="{pal["llm"]["sub"]}">정확 · 비싸 · 느림</text>')
    lines.append(f'  <text x="{tch_x + (NW+40)/2}" y="{tch_y + 110}" text-anchor="middle" font-size="11" fill="{pal["llm"]["sub"]}">$0.030/req</text>')

    # Stage 3: Synthetic dataset
    ds_x, ds_y = 540, 200
    lines.extend(node(ds_x, ds_y, NW, NH, 'token', theme, title='(q, a*) Dataset',
                      sub='Teacher 답을 정답으로', detail='필터링·검증 필수'))

    # Stage 4: Student SFT
    stu_x, stu_y = 760, 130
    lines.append(f'  <rect x="{stu_x}" y="{stu_y}" width="{NW}" height="{NH + 60}" rx="14" fill="{pal["output"]["fill"]}" stroke="{pal["output"]["stroke"]}" stroke-width="2.5"/>')
    lines.append(f'  <text x="{stu_x + NW/2}" y="{stu_y + 36}" text-anchor="middle" font-size="16" font-weight="700" fill="{pal["output"]["text"]}">Student</text>')
    lines.append(f'  <text x="{stu_x + NW/2}" y="{stu_y + 60}" text-anchor="middle" font-size="13" font-family="JetBrains Mono, monospace" fill="{pal["output"]["sub"]}">Haiku / 8B</text>')
    lines.append(f'  <text x="{stu_x + NW/2}" y="{stu_y + 86}" text-anchor="middle" font-size="11" fill="{pal["output"]["sub"]}">SFT · LoRA</text>')
    lines.append(f'  <text x="{stu_x + NW/2}" y="{stu_y + 110}" text-anchor="middle" font-size="11" fill="{pal["output"]["sub"]}">$0.001/req</text>')

    # Stage 5: Deployed student
    dep_x, dep_y = 980, 200
    lines.extend(node(dep_x, dep_y, NW, NH, 'gate', theme, title='Deploy',
                      sub='30× 저렴', detail='도메인 특화'))

    # Arrows
    lines.extend(arrow_line(q_x + NW + 2, q_y + NH/2, tch_x - 2, tch_y + (NH+60)/2, theme, kind='primary'))
    lines.extend(arrow_line(tch_x + NW + 40 + 2, tch_y + (NH+60)/2, ds_x - 2, ds_y + NH/2, theme, kind='primary', label='generate'))
    lines.extend(arrow_line(ds_x + NW + 2, ds_y + NH/2, stu_x - 2, stu_y + (NH+60)/2, theme, kind='primary', label='train'))
    lines.extend(arrow_line(stu_x + NW + 2, stu_y + (NH+60)/2, dep_x - 2, dep_y + NH/2, theme, kind='success'))

    # Filter step (annotation between teacher → dataset)
    lines.append(f'  <text x="{(tch_x + NW + 40 + ds_x) / 2}" y="{ds_y - 12}" text-anchor="middle" font-size="11" font-family="JetBrains Mono, monospace" fill="{pal["error"]["text"]}">+ 필터 (judge · 규칙)</text>')

    # Bottom tip
    lines.append(f'  <rect x="40" y="{CH - 35}" width="{CW-80}" height="22" rx="4" fill="{t["legend_bg"]}" stroke="{t["legend_border"]}" stroke-width="0.8"/>')
    lines.append(f'  <text x="{CW/2}" y="{CH - 19}" text-anchor="middle" font-size="11" fill="{t["legend_text"]}">Teacher 의 편향·할루시 그대로 복제 위험. 필터링이 학습보다 중요.</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# main
# =====================================================================

def main():
    print('Part 7 diagrams:')
    for name, fn in [
        ('ch31-transformer-block', transformer_block),
        ('ch31-training-stages', training_stages),
        ('ch32-finetune-decision', finetune_decision),
        ('ch32-approach-matrix', approach_matrix),
        ('ch33-lora-vs-full', lora_vs_full),
        ('ch33-qlora-pipeline', qlora_pipeline),
        ('ch34-alignment-compare', alignment_compare),
        ('ch34-distillation', distillation),
    ]:
        save(name, fn('light'), fn('dark'))


if __name__ == '__main__':
    main()
