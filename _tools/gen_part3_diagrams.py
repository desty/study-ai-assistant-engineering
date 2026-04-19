"""Part 3 다이어그램 제너레이터.

Ch 9: llm-vs-rag (비교), fine-tune-vs-rag (선택 기준)
Ch 10, 11, 12, 13, 14: 추후 추가
"""
import os
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from svg_prim import (
    svg_header, svg_footer, text_title, text_subtitle,
    node, arrow_line, arrow_path,
    P, T,
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
# Ch 9. LLM 단독 vs LLM + RAG — 같은 질문의 두 경로
# =====================================================================

def llm_vs_rag(theme):
    CW, CH = 1040, 400
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'LLM 단독 vs LLM + RAG', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '같은 질문, 다른 근거 — "환불 정책이 어떻게 되나요?"', theme))

    # Row 1: LLM 단독
    Q_Y = 200
    NAIVE_LLM_X, NAIVE_LLM_Y = 320, 100
    NAIVE_ANS_X, NAIVE_ANS_Y = 640, 100

    # Row 2: LLM + RAG
    RETRIEVE_X, RETRIEVE_Y = 320, 290
    RAG_LLM_X, RAG_LLM_Y = 540, 290
    RAG_ANS_X, RAG_ANS_Y = 760, 290

    # Shared question
    Q_X = 40

    # Arrows — naive path
    lines.extend(arrow_line(Q_X + NODE_W, Q_Y + NODE_H // 2 - 20,
                            NAIVE_LLM_X, NAIVE_LLM_Y + NODE_H // 2, theme, kind='primary', label='직접'))
    lines.extend(arrow_line(NAIVE_LLM_X + NODE_W, NAIVE_LLM_Y + NODE_H // 2,
                            NAIVE_ANS_X, NAIVE_ANS_Y + NODE_H // 2, theme, kind='warning'))

    # Arrows — RAG path
    lines.extend(arrow_line(Q_X + NODE_W, Q_Y + NODE_H // 2 + 20,
                            RETRIEVE_X, RETRIEVE_Y + NODE_H // 2, theme, kind='primary', label='+RAG'))
    lines.extend(arrow_line(RETRIEVE_X + NODE_W, RETRIEVE_Y + NODE_H // 2,
                            RAG_LLM_X, RAG_LLM_Y + NODE_H // 2, theme, kind='primary', label='문서'))
    lines.extend(arrow_line(RAG_LLM_X + NODE_W, RAG_LLM_Y + NODE_H // 2,
                            RAG_ANS_X, RAG_ANS_Y + NODE_H // 2, theme, kind='primary'))

    # Nodes
    lines.extend(node(Q_X, Q_Y, NODE_W, NODE_H, 'input', theme, title='질문', sub='user'))
    # Naive
    lines.extend(node(NAIVE_LLM_X, NAIVE_LLM_Y, NODE_W, NODE_H + 20, 'model', theme,
                      title='LLM', sub='학습 지식만', detail='hallucination 위험'))
    lines.extend(node(NAIVE_ANS_X, NAIVE_ANS_Y, NODE_W, NODE_H + 20, 'error', theme,
                      title='답', sub='출처 없음', detail='그럴듯한 추측'))
    # RAG
    lines.extend(node(RETRIEVE_X, RETRIEVE_Y, NODE_W, NODE_H, 'tool', theme,
                      title='검색', sub='vector DB'))
    lines.extend(node(RAG_LLM_X, RAG_LLM_Y, NODE_W, NODE_H, 'model', theme,
                      title='LLM', sub='+ 검색 문서'))
    lines.extend(node(RAG_ANS_X, RAG_ANS_Y, NODE_W, NODE_H, 'output', theme,
                      title='답', sub='출처 포함'))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 9. Fine-tune vs RAG — 결정 트리
# =====================================================================

def finetune_vs_rag(theme):
    CW, CH = 1000, 340
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Fine-tune vs RAG — 언제 뭘 쓰나', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '해결하려는 게 "지식"이면 RAG, "행동·스타일"이면 파인튜닝', theme))

    # 2 columns
    RAG_X, RAG_Y = 60, 110
    FT_X, FT_Y = 540, 110
    col_w = 400
    col_h = 180

    pal = P(theme)

    # RAG column (green/tool)
    lines.extend(node(RAG_X, RAG_Y, col_w, col_h, 'tool', theme,
                      title='RAG 선택', sub='외부 지식'))
    # Overlaid text
    lines.append(f'  <text x="{RAG_X + 20}" y="{RAG_Y + 105}" font-size="11" fill="{pal["tool"]["text"]}">• 최신 정보 (가격·재고·이벤트)</text>')
    lines.append(f'  <text x="{RAG_X + 20}" y="{RAG_Y + 125}" font-size="11" fill="{pal["tool"]["text"]}">• 회사 내부 문서 (정책·매뉴얼)</text>')
    lines.append(f'  <text x="{RAG_X + 20}" y="{RAG_Y + 145}" font-size="11" fill="{pal["tool"]["text"]}">• 추적 가능성 (citation)</text>')
    lines.append(f'  <text x="{RAG_X + 20}" y="{RAG_Y + 165}" font-size="11" fill="{pal["tool"]["text"]}">• 자주 바뀌는 데이터</text>')

    # FT column (purple/model)
    lines.extend(node(FT_X, FT_Y, col_w, col_h, 'model', theme,
                      title='Fine-tune 선택', sub='모델 행동'))
    lines.append(f'  <text x="{FT_X + 20}" y="{FT_Y + 105}" font-size="11" fill="{pal["model"]["text"]}">• 특정 말투·포맷 고정</text>')
    lines.append(f'  <text x="{FT_X + 20}" y="{FT_Y + 125}" font-size="11" fill="{pal["model"]["text"]}">• 복잡한 분류·추출 태스크</text>')
    lines.append(f'  <text x="{FT_X + 20}" y="{FT_Y + 145}" font-size="11" fill="{pal["model"]["text"]}">• 소형 모델로 품질·비용 최적화</text>')
    lines.append(f'  <text x="{FT_X + 20}" y="{FT_Y + 165}" font-size="11" fill="{pal["model"]["text"]}">• 변경 주기 긴 지식</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 10. 임베딩 파이프라인 — 텍스트 → 임베딩 → 벡터DB → 검색
# =====================================================================

def embedding_pipeline(theme):
    CW, CH = 1040, 280
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '임베딩 파이프라인', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '텍스트를 숫자 벡터로 → 의미적으로 가까운 것을 검색', theme))

    specs = [
        ('input',  '원문 텍스트',    'docs · query',   '"환불 정책…"'),
        ('model',  '임베딩 모델',    'encoder',        'OpenAI/Voyage/BGE'),
        ('token',  '벡터',          '1536-d float',   '[0.12, -0.03, ...]'),
        ('memory', '벡터 DB',       'store + ANN',    'Chroma/Qdrant/Pinecone'),
        ('tool',   '검색 (top-k)',  'cosine sim',     '가장 가까운 N개'),
    ]
    xs = layout_centered_row(len(specs), CW, 180, 22)
    y = 100
    for i in range(len(xs) - 1):
        x1 = xs[i] + 180 + 2
        x2 = xs[i + 1] - 2
        cy = y + (NODE_H + 25) // 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))
    for x, (role, t, s, d) in zip(xs, specs):
        lines.extend(node(x, y, 180, NODE_H + 25, role, theme, title=t, sub=s, detail=d))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 10. 의미 공간 — 2D 시각화로 "의미가 가까운 것이 공간에서도 가깝다"
# =====================================================================

def semantic_space(theme):
    from svg_prim import P, T
    CW, CH = 900, 540
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '의미 공간 (Embedding Space)', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '의미가 비슷한 문장은 벡터 공간에서도 서로 가까이 모임', theme))

    pal = P(theme)
    t = T(theme)

    # Plot area
    PLOT_X, PLOT_Y = 80, 100
    PLOT_W, PLOT_H = 740, 380

    # Plot border (subtle)
    lines.append(f'  <rect x="{PLOT_X}" y="{PLOT_Y}" width="{PLOT_W}" height="{PLOT_H}" rx="8" fill="none" stroke="{t["legend_border"]}" stroke-width="1" stroke-dasharray="4,3"/>')

    # Axis label hint
    lines.append(f'  <text x="{PLOT_X + 8}" y="{PLOT_Y + 16}" font-size="10" fill="{t["subtitle"]}" font-family="JetBrains Mono, monospace">x, y = 축소된 임베딩 (실제는 1536차원)</text>')

    # Clusters: (center_x, center_y, points[(dx, dy, label)], role, cluster_label)
    clusters = [
        (180, 170, [
            (-20, -10, '강아지'),
            ( 15, -20, '고양이'),
            (-10,  20, '토끼'),
            ( 20,  15, '햄스터'),
        ], 'input', '동물'),
        (560, 160, [
            (-20, -15, '피자'),
            ( 20, -10, '김치찌개'),
            ( 15,  20, '샌드위치'),
            (-20,  18, '라면'),
        ], 'llm', '음식'),
        (400, 360, [
            (-25, -10, 'AI'),
            ( -5, -25, 'LLM'),
            ( 20,  10, '딥러닝'),
            ( 25, -18, '트랜스포머'),
        ], 'tool', '기술'),
    ]

    # Draw clusters
    for cx, cy, points, role, label in clusters:
        c = pal[role]
        # Cluster fill circle (very subtle)
        lines.append(f'  <circle cx="{cx}" cy="{cy}" r="70" fill="{c["fill"]}" opacity="0.4"/>')
        lines.append(f'  <circle cx="{cx}" cy="{cy}" r="70" fill="none" stroke="{c["stroke"]}" stroke-width="1" stroke-dasharray="3,3"/>')
        # Cluster label (top-right of circle)
        lines.append(f'  <text x="{cx + 55}" y="{cy - 60}" font-size="12" font-weight="700" fill="{c["stroke"]}">{label}</text>')
        # Points
        for dx, dy, plabel in points:
            px, py = cx + dx, cy + dy
            lines.append(f'  <circle cx="{px}" cy="{py}" r="5" fill="{c["stroke"]}"/>')
            lines.append(f'  <text x="{px + 8}" y="{py + 4}" font-size="11" fill="{c["text"]}">{plabel}</text>')

    # Query point — near 기술 cluster
    q_x, q_y = 440, 330
    lines.append(f'  <circle cx="{q_x}" cy="{q_y}" r="10" fill="none" stroke="{pal["error"]["stroke"]}" stroke-width="2"/>')
    lines.append(f'  <circle cx="{q_x}" cy="{q_y}" r="5" fill="{pal["error"]["stroke"]}"/>')
    # Top-k circle showing search radius
    lines.append(f'  <circle cx="{q_x}" cy="{q_y}" r="65" fill="none" stroke="{pal["error"]["stroke"]}" stroke-width="1.5" stroke-dasharray="5,4"/>')
    lines.append(f'  <text x="{q_x + 15}" y="{q_y - 8}" font-size="12" font-weight="700" fill="{pal["error"]["stroke"]}">query</text>')
    lines.append(f'  <text x="{q_x + 15}" y="{q_y + 8}" font-size="10" fill="{pal["error"]["text"]}" font-family="JetBrains Mono, monospace">"요즘 AI는"</text>')

    # Annotation for top-k
    lines.append(f'  <text x="{q_x + 60}" y="{q_y + 58}" font-size="11" fill="{pal["error"]["stroke"]}" font-family="JetBrains Mono, monospace">top-k = 가장 가까운 이웃</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 11. RAG 파이프라인 — Indexing phase + Query phase
# =====================================================================

def rag_pipeline(theme):
    CW, CH = 1100, 500
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'RAG 파이프라인 — 두 단계', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'Indexing (준비) + Query (실행) · 둘은 벡터 DB로 연결됨', theme))

    from svg_prim import group_container

    # === Indexing row (top) ===
    IDX_Y = 130
    idx_specs = [
        ('input',  '문서',        'docs'),
        ('tool',   '로드',        'PDF/HTML/MD'),
        ('tool',   'Chunking',    'split'),
        ('model',  '임베딩',      'encoder'),
        ('memory', '벡터 DB',     'store'),
    ]
    idx_xs = layout_centered_row(5, CW, 160, 26)
    for i in range(len(idx_xs) - 1):
        x1 = idx_xs[i] + 160 + 2
        x2 = idx_xs[i + 1] - 2
        cy = IDX_Y + NODE_H // 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))
    for x, (role, t, s) in zip(idx_xs, idx_specs):
        lines.extend(node(x, IDX_Y, 160, NODE_H, role, theme, title=t, sub=s))

    # Group container for indexing
    idx_left = idx_xs[0] - 16
    idx_right = idx_xs[-1] + 160 + 16
    lines.extend(group_container(idx_left, IDX_Y - 28, idx_right - idx_left, NODE_H + 44,
                                  'INDEXING (한 번, 문서 업데이트 시 재실행)', 'tool', theme))

    # === Query row (bottom) ===
    QRY_Y = 340
    qry_specs = [
        ('input',  '질문',        'query'),
        ('model',  '임베딩',      'same encoder'),
        ('memory', '검색 top-k',  'ANN'),
        ('llm',    'Augment',     'prompt + context'),
        ('output', '생성 + 인용',  'LLM'),
    ]
    qry_xs = layout_centered_row(5, CW, 160, 26)
    for i in range(len(qry_xs) - 1):
        x1 = qry_xs[i] + 160 + 2
        x2 = qry_xs[i + 1] - 2
        cy = QRY_Y + NODE_H // 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))
    for x, (role, t, s) in zip(qry_xs, qry_specs):
        lines.extend(node(x, QRY_Y, 160, NODE_H, role, theme, title=t, sub=s))

    # Group container for query
    qry_left = qry_xs[0] - 16
    qry_right = qry_xs[-1] + 160 + 16
    lines.extend(group_container(qry_left, QRY_Y - 28, qry_right - qry_left, NODE_H + 44,
                                  'QUERY (매 요청)', 'llm', theme))

    # Dashed arrow: Indexing store → Query retrieve (conceptual link)
    from svg_prim import arrow_path
    idx_store_cx = idx_xs[4] + 80
    idx_store_bot = IDX_Y + NODE_H
    qry_ret_cx = qry_xs[2] + 80
    qry_ret_top = QRY_Y
    path = f'M {idx_store_cx},{idx_store_bot + 28} L {idx_store_cx},{(idx_store_bot + qry_ret_top) // 2} L {qry_ret_cx},{(idx_store_bot + qry_ret_top) // 2} L {qry_ret_cx},{qry_ret_top - 28}'
    lines.extend(arrow_path(
        path, theme, kind='feedback',
        label_pos=((idx_store_cx + qry_ret_cx) // 2, (idx_store_bot + qry_ret_top) // 2 - 12),
        label='같은 벡터 공간',
    ))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 11. Chunking 전략 비교
# =====================================================================

def chunking_strategies(theme):
    from svg_prim import P, T
    CW, CH = 1000, 380
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Chunking 전략 — 크기의 트레이드오프', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '너무 작으면 맥락 손실, 너무 크면 정밀도 하락', theme))

    pal = P(theme)
    t = T(theme)

    # Document bar visualization — three different chunk patterns on same doc
    DOC_X = 220
    DOC_W = 720

    def draw_chunked_bar(y, label, sub, chunks, role):
        # label left
        lines.append(f'  <text x="40" y="{y + 20}" font-size="13" font-weight="700" fill="{t["title"]}">{label}</text>')
        lines.append(f'  <text x="40" y="{y + 36}" font-size="10" fill="{t["subtitle"]}" font-family="JetBrains Mono, monospace">{sub}</text>')
        # bars
        c = pal[role]
        cur_x = DOC_X
        for w_ratio in chunks:
            w = DOC_W * w_ratio
            lines.append(f'  <rect x="{cur_x}" y="{y}" width="{w - 2}" height="40" rx="4" fill="{c["fill"]}" stroke="{c["stroke"]}" stroke-width="1.5"/>')
            cur_x += w

    # Small chunks (many)
    draw_chunked_bar(110, '작게 (~200토큰)', 'fixed, overlap=0', [1/10] * 10, 'memory')
    # Medium chunks
    draw_chunked_bar(190, '중간 (~512토큰)', 'fixed, overlap=50', [1/5] * 5, 'token')
    # Big chunks
    draw_chunked_bar(270, '크게 (~2000토큰)', 'fixed / section', [1/2, 1/2], 'llm')

    # Annotation arrow showing doc extent
    lines.append(f'  <line x1="{DOC_X}" y1="{90}" x2="{DOC_X + DOC_W}" y2="{90}" stroke="{t["arrow"]}" stroke-width="1.5"/>')
    lines.append(f'  <text x="{DOC_X + DOC_W // 2}" y="{80}" text-anchor="middle" font-size="11" fill="{t["subtitle"]}">← 문서 한 개 (예: 10페이지 정책 문서) →</text>')

    # Caption rows
    CAP_Y = 330
    captions = [
        ('작게', '세밀한 검색 · 맥락 부족', pal['memory']['text']),
        ('중간', '균형점 (대부분 권장)', pal['token']['text']),
        ('크게', '맥락 보존 · 무관 내용도 같이', pal['llm']['text']),
    ]
    caption_y = 330
    lines.append(f'  <text x="40" y="{caption_y}" font-size="11" fill="{t["subtitle"]}">• 작게: 세밀 · 맥락 손실  |  중간: 균형 (권장)  |  크게: 맥락 보존 · 정밀도↓</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 12. Hybrid 검색 파이프라인 — Dense + BM25 병렬 → RRF merge → rerank
# =====================================================================

def hybrid_retrieval(theme):
    from svg_prim import arrow_path
    CW, CH = 1100, 440
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Hybrid 검색 + Reranker', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'Dense(의미) + BM25(키워드) 병렬 → RRF 병합 → Cross-encoder rerank', theme))

    # Query on the left
    Q_X, Q_Y = 40, 200
    # Two parallel retrievers
    DENSE_X, DENSE_Y = 260, 110
    BM25_X, BM25_Y = 260, 290
    # Merge
    MERGE_X, MERGE_Y = 500, 200
    # Rerank
    RERANK_X, RERANK_Y = 720, 200
    # Final top-k
    FINAL_X, FINAL_Y = 940, 200

    # Arrows
    # Q → Dense (up-right)
    lines.extend(arrow_line(Q_X + NODE_W, Q_Y + NODE_H // 2 - 20,
                            DENSE_X, DENSE_Y + NODE_H // 2, theme, kind='primary', label='query vec'))
    # Q → BM25 (down-right)
    lines.extend(arrow_line(Q_X + NODE_W, Q_Y + NODE_H // 2 + 20,
                            BM25_X, BM25_Y + NODE_H // 2, theme, kind='primary', label='query tokens'))
    # Dense → Merge (down-right)
    lines.extend(arrow_line(DENSE_X + NODE_W, DENSE_Y + NODE_H // 2,
                            MERGE_X, MERGE_Y + 20, theme, kind='primary', label='top-20'))
    # BM25 → Merge (up-right)
    lines.extend(arrow_line(BM25_X + NODE_W, BM25_Y + NODE_H // 2,
                            MERGE_X, MERGE_Y + NODE_H - 20, theme, kind='primary', label='top-20'))
    # Merge → Rerank
    lines.extend(arrow_line(MERGE_X + NODE_W, MERGE_Y + NODE_H // 2,
                            RERANK_X, RERANK_Y + NODE_H // 2, theme, kind='primary'))
    # Rerank → Final
    lines.extend(arrow_line(RERANK_X + NODE_W, RERANK_Y + NODE_H // 2,
                            FINAL_X, FINAL_Y + NODE_H // 2, theme, kind='success', label='top-5'))

    # Nodes
    lines.extend(node(Q_X, Q_Y, NODE_W, NODE_H, 'input',  theme, title='쿼리',     sub='user query'))
    lines.extend(node(DENSE_X, DENSE_Y, NODE_W, NODE_H, 'model',  theme, title='Dense',    sub='임베딩 + ANN', detail='의미 검색'))
    lines.extend(node(BM25_X, BM25_Y, NODE_W, NODE_H, 'tool',   theme, title='BM25',     sub='키워드 통계', detail='용어 일치'))
    lines.extend(node(MERGE_X, MERGE_Y, NODE_W, NODE_H, 'gate',  theme, title='RRF 병합',  sub='reciprocal rank'))
    lines.extend(node(RERANK_X, RERANK_Y, NODE_W, NODE_H, 'memory', theme, title='Rerank',  sub='cross-encoder'))
    lines.extend(node(FINAL_X, FINAL_Y, NODE_W, NODE_H, 'output', theme, title='최종 top-k', sub='정밀'))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 12. Rerank Impact — before vs after 순위 재배열
# =====================================================================

def rerank_impact(theme):
    from svg_prim import P, T
    CW, CH = 1000, 460
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Reranker의 효과 — 순위 재배열', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'ANN이 뽑은 top-10 중 "진짜 관련된" 5개로 재정렬', theme))

    pal = P(theme)
    t = T(theme)

    # Two columns
    LEFT_X = 100
    RIGHT_X = 560
    COL_W = 340
    ROW_H = 32
    START_Y = 110

    # Left column: raw top-10
    lines.append(f'  <text x="{LEFT_X + COL_W // 2}" y="{START_Y - 10}" text-anchor="middle" font-size="14" font-weight="700" fill="{t["title"]}">Dense ANN top-10 (raw)</text>')
    raw_items = [
        ('doc-A · 환불은 7일 이내',          True,  0.82),
        ('doc-X · 배송 정책',                False, 0.81),
        ('doc-B · 환불 사유 기록',           True,  0.80),
        ('doc-Y · 포인트 적립',              False, 0.78),
        ('doc-C · 환불 승인 절차',           True,  0.77),
        ('doc-Z · 이벤트 쿠폰',              False, 0.76),
        ('doc-D · 환불 불가 품목',           True,  0.75),
        ('doc-W · 자주 묻는 질문',           False, 0.74),
        ('doc-V · 고객 센터 연락처',         False, 0.73),
        ('doc-E · 환불 시 배송비',           True,  0.72),
    ]
    for i, (label, relevant, score) in enumerate(raw_items):
        y = START_Y + 20 + i * ROW_H
        color = pal['token'] if relevant else pal['error']
        lines.append(f'  <rect x="{LEFT_X}" y="{y - 14}" width="{COL_W}" height="{ROW_H - 6}" rx="6" fill="{color["fill"]}" stroke="{color["stroke"]}" stroke-width="1.2"/>')
        lines.append(f'  <text x="{LEFT_X + 10}" y="{y + 4}" font-size="11" fill="{color["text"]}">{i+1}. {label}</text>')
        lines.append(f'  <text x="{LEFT_X + COL_W - 10}" y="{y + 4}" text-anchor="end" font-size="10" fill="{color["sub"]}" font-family="JetBrains Mono, monospace">{score:.2f}</text>')

    # Right column: after rerank top-5
    lines.append(f'  <text x="{RIGHT_X + COL_W // 2}" y="{START_Y - 10}" text-anchor="middle" font-size="14" font-weight="700" fill="{t["title"]}">Cross-encoder rerank top-5</text>')
    rerank_items = [
        ('doc-A · 환불은 7일 이내',    0.94),
        ('doc-C · 환불 승인 절차',     0.91),
        ('doc-B · 환불 사유 기록',     0.88),
        ('doc-D · 환불 불가 품목',     0.85),
        ('doc-E · 환불 시 배송비',     0.79),
    ]
    for i, (label, score) in enumerate(rerank_items):
        y = START_Y + 20 + i * ROW_H
        color = pal['output']
        lines.append(f'  <rect x="{RIGHT_X}" y="{y - 14}" width="{COL_W}" height="{ROW_H - 6}" rx="6" fill="{color["fill"]}" stroke="{color["stroke"]}" stroke-width="1.5"/>')
        lines.append(f'  <text x="{RIGHT_X + 10}" y="{y + 4}" font-size="11" fill="{color["text"]}">{i+1}. {label}</text>')
        lines.append(f'  <text x="{RIGHT_X + COL_W - 10}" y="{y + 4}" text-anchor="end" font-size="10" fill="{color["sub"]}" font-family="JetBrains Mono, monospace">{score:.2f}</text>')

    # Legend bar (bottom)
    lg_y = 430
    lg_x = LEFT_X
    lines.append(f'  <rect x="{lg_x}" y="{lg_y}" width="14" height="14" rx="3" fill="{pal["token"]["stroke"]}"/>')
    lines.append(f'  <text x="{lg_x + 20}" y="{lg_y + 11}" font-size="11" fill="{t["legend_text"]}">관련 문서 (gold)</text>')
    lines.append(f'  <rect x="{lg_x + 150}" y="{lg_y}" width="14" height="14" rx="3" fill="{pal["error"]["stroke"]}"/>')
    lines.append(f'  <text x="{lg_x + 170}" y="{lg_y + 11}" font-size="11" fill="{t["legend_text"]}">무관 문서 (noise)</text>')

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 13. Advanced RAG 4변형 — 한 장에 요약
# =====================================================================

def advanced_rag_variants(theme):
    from svg_prim import P, T
    CW, CH = 1100, 620
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'Advanced RAG — 4 변형', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '같은 재료 · 다른 조립 — 쿼리/검색/생성의 위치와 역할이 달라짐', theme))

    pal = P(theme)
    t = T(theme)

    # 4 rows, each a mini flow
    LABEL_X = 40
    ROW_HEIGHT = 130
    ROWS_START_Y = 100

    def draw_row(row_idx, label, sub, nodes_spec):
        y_top = ROWS_START_Y + row_idx * ROW_HEIGHT
        # Row label
        lines.append(f'  <text x="{LABEL_X}" y="{y_top + 30}" font-size="13" font-weight="700" fill="{t["title"]}">{label}</text>')
        lines.append(f'  <text x="{LABEL_X}" y="{y_top + 48}" font-size="10" fill="{t["subtitle"]}" font-family="JetBrains Mono, monospace">{sub}</text>')

        # Mini nodes
        NODE_SM_W, NODE_SM_H = 100, 60
        NODE_GAP = 18
        start_x = 200
        cur_x = start_x
        for i, (role, title) in enumerate(nodes_spec):
            if i > 0:
                prev_x = cur_x
                lines.extend(arrow_line(prev_x - NODE_GAP + 2, y_top + 30,
                                         cur_x - 2, y_top + 30, theme, kind='primary'))
            c = pal[role]
            # small node
            lines.append(f'  <rect x="{cur_x}" y="{y_top}" width="{NODE_SM_W}" height="{NODE_SM_H}" rx="8" fill="{c["fill"]}" stroke="{c["stroke"]}" stroke-width="1.5"/>')
            lines.append(f'  <text x="{cur_x + NODE_SM_W // 2}" y="{y_top + NODE_SM_H // 2 + 4}" text-anchor="middle" font-size="11" font-weight="700" fill="{c["text"]}">{title}</text>')
            cur_x += NODE_SM_W + NODE_GAP

    # Row 0: Basic RAG
    draw_row(0, 'Basic RAG', '표준 파이프라인', [
        ('input', '쿼리'),
        ('tool', '검색'),
        ('model', 'LLM'),
        ('output', '답변'),
    ])

    # Row 1: HyDE
    draw_row(1, 'HyDE', '쿼리 대신 가상답변을 임베딩', [
        ('input', '쿼리'),
        ('model', '가상 답변 생성'),
        ('tool', '가상답변으로 검색'),
        ('model', 'LLM'),
        ('output', '답변'),
    ])

    # Row 2: Self-RAG
    draw_row(2, 'Self-RAG', 'LLM이 검색 필요성·품질 판단', [
        ('input', '쿼리'),
        ('gate', '검색 필요?'),
        ('tool', '검색'),
        ('gate', '결과 평가'),
        ('output', '답변'),
    ])

    # Row 3: Agentic RAG
    draw_row(3, 'Agentic RAG', '에이전트 루프 안에 검색 도구', [
        ('input', '쿼리'),
        ('llm', 'Agent'),
        ('tool', '검색·툴'),
        ('llm', '추론'),
        ('output', '답변'),
    ])

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 13. HyDE 상세 흐름
# =====================================================================

def hyde_detail(theme):
    from svg_prim import P, T
    CW, CH = 1040, 380
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'HyDE — Hypothetical Document Embeddings', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, '쿼리 임베딩이 약할 때, 가상의 답변을 만들어 그걸로 검색', theme))

    pal = P(theme)
    t = T(theme)

    # Top: Basic RAG (query embedding path)
    lines.append(f'  <text x="60" y="110" font-size="12" font-weight="700" fill="{pal["error"]["stroke"]}">❌ Basic</text>')
    lines.append(f'  <text x="60" y="128" font-size="10" fill="{t["subtitle"]}" font-family="JetBrains Mono, monospace">query embed</text>')

    # Basic: Q → embed → search
    basic_xs = [180, 400, 620]
    basic_specs = [('input', '짧은 쿼리', '"AI는?"'), ('model', '임베딩', 'noisy'), ('tool', '검색', 'top-k 불안정')]
    for i in range(len(basic_xs) - 1):
        lines.extend(arrow_line(basic_xs[i] + 160 + 2, 140,
                                 basic_xs[i + 1] - 2, 140, theme, kind='primary'))
    for x, (role, t_, s) in zip(basic_xs, basic_specs):
        lines.extend(node(x, 100, 160, 80, role, theme, title=t_, sub=s))

    # Bottom: HyDE (hypothetical answer path)
    lines.append(f'  <text x="60" y="260" font-size="12" font-weight="700" fill="{pal["output"]["stroke"]}">✓ HyDE</text>')
    lines.append(f'  <text x="60" y="278" font-size="10" fill="{t["subtitle"]}" font-family="JetBrains Mono, monospace">hyp. answer embed</text>')

    # HyDE: Q → gen-answer → embed → search
    hyde_xs = [180, 380, 580, 780]
    hyde_specs = [
        ('input', '짧은 쿼리', '"AI는?"'),
        ('model', 'LLM 가상답변', '"AI는 인공지능…"'),
        ('model', '임베딩', '긴 답변'),
        ('tool', '검색', '정확한 top-k'),
    ]
    for i in range(len(hyde_xs) - 1):
        lines.extend(arrow_line(hyde_xs[i] + 160 + 2, 290,
                                 hyde_xs[i + 1] - 2, 290, theme, kind='primary'))
    for x, (role, t_, s) in zip(hyde_xs, hyde_specs):
        lines.extend(node(x, 250, 160, 80, role, theme, title=t_, sub=s))

    lines.extend(svg_footer())
    return '\n'.join(lines)


GENERATORS = [
    ('ch9-llm-vs-rag',          llm_vs_rag),
    ('ch9-finetune-vs-rag',     finetune_vs_rag),
    ('ch10-embedding-pipeline', embedding_pipeline),
    ('ch10-semantic-space',     semantic_space),
    ('ch11-rag-pipeline',       rag_pipeline),
    ('ch11-chunking',           chunking_strategies),
    ('ch12-hybrid-pipeline',    hybrid_retrieval),
    ('ch12-rerank-impact',      rerank_impact),
    ('ch13-rag-variants',       advanced_rag_variants),
    ('ch13-hyde-detail',        hyde_detail),
    ('ch14-langchain-components', None),
    ('ch14-multimodal-rag',      None),
]


# =====================================================================
# Ch 14. LangChain 컴포넌트 관계
# =====================================================================

def langchain_components(theme):
    from svg_prim import group_around_nodes
    CW, CH = 1100, 420
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, 'LangChain — RAG 컴포넌트 관계', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'LCEL (chain) 로 조립 가능한 재료들', theme))

    # Indexing row
    IDX_Y = 140
    idx_specs = [
        ('input',  'DocumentLoader', 'PDF/MD/HTML'),
        ('tool',   'TextSplitter',   'chunk'),
        ('model',  'Embeddings',     'OpenAI/Voyage'),
        ('memory', 'VectorStore',    'Chroma/Pinecone'),
    ]
    idx_xs = layout_centered_row(4, CW, 180, 26)
    for i in range(len(idx_xs) - 1):
        x1 = idx_xs[i] + 180 + 2
        x2 = idx_xs[i + 1] - 2
        cy = IDX_Y + NODE_H // 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))
    for x, (role, t_, s) in zip(idx_xs, idx_specs):
        lines.extend(node(x, IDX_Y, 180, NODE_H, role, theme, title=t_, sub=s))
    lines.extend(group_around_nodes(idx_xs, IDX_Y, 180, NODE_H, 'INDEXING', 'tool', theme))

    # Query row
    QRY_Y = 300
    qry_specs = [
        ('input',  'Retriever',      'VectorStore.as_retriever'),
        ('model',  'PromptTemplate', '컨텍스트 + 질문'),
        ('llm',    'ChatModel',      'ChatAnthropic/OpenAI'),
        ('output', 'OutputParser',   'str | Pydantic'),
    ]
    qry_xs = layout_centered_row(4, CW, 200, 26)
    for i in range(len(qry_xs) - 1):
        x1 = qry_xs[i] + 200 + 2
        x2 = qry_xs[i + 1] - 2
        cy = QRY_Y + NODE_H // 2
        lines.extend(arrow_line(x1, cy, x2, cy, theme, kind='primary'))
    for x, (role, t_, s) in zip(qry_xs, qry_specs):
        lines.extend(node(x, QRY_Y, 200, NODE_H, role, theme, title=t_, sub=s))
    lines.extend(group_around_nodes(qry_xs, QRY_Y, 200, NODE_H, 'CHAIN (LCEL)', 'llm', theme))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# =====================================================================
# Ch 14. 멀티모달 RAG
# =====================================================================

def multimodal_rag(theme):
    from svg_prim import P, T, arrow_path
    CW, CH = 1040, 440
    lines = svg_header(CW, CH, theme)
    lines.extend(text_title(CW // 2, 36, '멀티모달 RAG — 텍스트 + 이미지', theme, size=18))
    lines.extend(text_subtitle(CW // 2, 58, 'PDF의 표·다이어그램·스크린샷까지 검색 대상으로', theme))

    pal = P(theme)
    t = T(theme)

    # Source: PDF
    SRC_X, SRC_Y = 40, 200
    lines.extend(node(SRC_X, SRC_Y, 120, 90, 'input', theme, title='PDF 문서', sub='mixed'))

    # Two parallel extraction paths
    TEXT_X, TEXT_Y = 240, 100
    IMG_X, IMG_Y = 240, 300

    lines.extend(node(TEXT_X, TEXT_Y, 180, 90, 'tool', theme, title='텍스트 추출', sub='unstructured / fitz'))
    lines.extend(node(IMG_X, IMG_Y, 180, 90, 'tool', theme, title='이미지 추출', sub='page rasterize'))

    # Arrows from PDF to both
    lines.extend(arrow_line(SRC_X + 120, SRC_Y + 30,
                             TEXT_X, TEXT_Y + 45, theme, kind='primary', label='텍스트'))
    lines.extend(arrow_line(SRC_X + 120, SRC_Y + 60,
                             IMG_X, IMG_Y + 45, theme, kind='primary', label='이미지'))

    # Embed models
    TEMB_X, TEMB_Y = 480, 100
    IEMB_X, IEMB_Y = 480, 300

    lines.extend(node(TEMB_X, TEMB_Y, 180, 90, 'model', theme, title='텍스트 임베딩', sub='text-embed-3'))
    lines.extend(node(IEMB_X, IEMB_Y, 180, 90, 'model', theme, title='멀티모달 임베딩', sub='CLIP / Voyage-mm'))

    lines.extend(arrow_line(TEXT_X + 180, TEXT_Y + 45, TEMB_X, TEMB_Y + 45, theme, kind='primary'))
    lines.extend(arrow_line(IMG_X + 180, IMG_Y + 45, IEMB_X, IEMB_Y + 45, theme, kind='primary'))

    # Vector stores
    TDB_X, TDB_Y = 720, 100
    IDB_X, IDB_Y = 720, 300
    lines.extend(node(TDB_X, TDB_Y, 140, 90, 'memory', theme, title='텍스트 DB', sub='vector'))
    lines.extend(node(IDB_X, IDB_Y, 140, 90, 'memory', theme, title='이미지 DB', sub='vector'))

    lines.extend(arrow_line(TEMB_X + 180, TEMB_Y + 45, TDB_X, TDB_Y + 45, theme, kind='primary'))
    lines.extend(arrow_line(IEMB_X + 180, IEMB_Y + 45, IDB_X, IDB_Y + 45, theme, kind='primary'))

    # Retrieve + generate
    LLM_X, LLM_Y = 900, 200
    lines.extend(node(LLM_X, LLM_Y, 120, 90, 'llm', theme, title='Vision LLM', sub='Claude/GPT-4o'))

    lines.extend(arrow_line(TDB_X + 140, TDB_Y + 70, LLM_X, LLM_Y + 30, theme, kind='success'))
    lines.extend(arrow_line(IDB_X + 140, IDB_Y + 20, LLM_X, LLM_Y + 60, theme, kind='success'))

    lines.extend(svg_footer())
    return '\n'.join(lines)


# Reassign generators (overwrite the None placeholders)
GENERATORS[-2] = ('ch14-langchain-components', langchain_components)
GENERATORS[-1] = ('ch14-multimodal-rag', multimodal_rag)

if __name__ == '__main__':
    for name, fn in GENERATORS:
        save(name, fn('light'), fn('dark'))
    print(f'\n✓ {len(GENERATORS)} diagrams × 2 themes')
