# Ch 12. 검색 품질 개선

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part3/ch12_retrieval_quality.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **답변 품질의 70%는 검색 품질** — 생성으로는 못 메꾸는 이유
    - 검색 실패의 **5가지 유형** (recall · precision · 랭킹 · metadata · chunk 경계)
    - **BM25 + Dense** 하이브리드 검색 (RRF 병합)
    - **Cross-encoder reranker** — 순위 재배열로 정밀도 올리기
    - **MMR** (다양성) 과 **metadata filter**
    - chunk size · top-k · rerank 비용의 트레이드오프

!!! quote "전제"
    [Ch 11](11-pipeline.md) 의 `mini_rag.py` 를 돌려본 상태.

---

## 1. 개념 — 검색이 답변의 상한을 정한다

Ch 11 의 Query 파이프라인에서 **검색이 무관한 문서**를 뽑으면 LLM은 **거기서 답을 만들려고 시도**합니다. 결과는 hallucination 또는 "모르겠다".

> **생성은 검색이 놓친 걸 복구하지 못한다.**

그래서 Part 3 에서 **가장 많은 시간** 이 들어가는 건 **검색 품질 개선**. 이 챕터는 그 도구상자.

---

## 2. 검색 실패의 5가지 유형

| 유형 | 증상 | 원인 |
|---|---|---|
| **Recall 부족** | 관련 문서가 top-k 에 **아예 없음** | 쿼리-문서 표현 차이, chunk 경계 문제 |
| **Precision 부족** | 무관 문서가 top-k 에 **많이 섞임** | ANN 점수만으로 정렬, 다양성 없음 |
| **랭킹 오류** | 관련 문서가 있지만 **낮은 순위** | Dense 만의 한계 (의미 유사 ≠ 정확 매칭) |
| **Metadata 무시** | 오래된·비공개 문서가 top-k | `updated_at` · `owner` 필터 안 걸림 |
| **Chunk 경계** | 답이 **두 chunk 에 걸쳐** 있음 | 고정 길이 자르기 |

각 유형마다 **다른 도구**가 필요. 이 챕터는 그 매핑.

---

## 3. 어디에 쓰이나

이 챕터의 기법들은 **실전 RAG 전부** 에 들어갑니다:

- FAQ 봇에서 top-1 만 쓰면 → **rerank 로 순위 보정**
- 긴 정책 문서 → **BM25 하이브리드로 번호·조항 정확 매칭**
- 다국어 문서 → **metadata filter 로 언어 분리**
- 최신성이 중요한 지식 → **updated_at filter**

---

## 4. 최소 예제 — Dense vs BM25 vs Hybrid 비교

```bash
pip install rank-bm25
```

```python title="dense_vs_bm25.py" linenums="1" hl_lines="16 23"
from openai import OpenAI
from rank_bm25 import BM25Okapi
import numpy as np

openai = OpenAI()

docs = [
    "환불은 구매 후 7일 이내, 팀장 승인 필요.",
    "배송 정책: 영업일 2~3일, 도서산간 +2일.",
    "포인트는 구매 금액의 1% 적립, 3개월 이내 사용.",
    "AS 기간은 제품 구매일로부터 1년.",
    "환불 불가 품목: 맞춤 제작 상품, 개봉된 소프트웨어.",
]

# Dense
def embed(texts):
    r = openai.embeddings.create(model="text-embedding-3-small", input=texts)
    return np.array([d.embedding for d in r.data])

doc_vecs = embed(docs)

# BM25
tokenized = [d.split() for d in docs]           # (1)!
bm25 = BM25Okapi(tokenized)

query = "돈을 돌려받고 싶은데요"
q_vec = embed([query])[0]

# Dense top-3
dense_scores = doc_vecs @ q_vec
dense_top = np.argsort(-dense_scores)[:3]

# BM25 top-3
bm25_scores = bm25.get_scores(query.split())    # (2)!
bm25_top = np.argsort(-bm25_scores)[:3]

print("Dense :", [docs[i] for i in dense_top])
print("BM25  :", [docs[i] for i in bm25_top])
```

1. 한국어 토큰화는 공백 분리가 나쁨. 실전은 `kiwi`·`KoNLPy` 형태소 분석기.
2. BM25는 **"환불" · "돌려"** 단어가 **그대로** 있어야 높은 점수. 의미는 모름.

**관찰 포인트**:

- Dense 는 `"환불"` 단어 없이도 **의미**로 찾음 ("돈을 돌려받고 싶다" → 환불 문서)
- BM25 는 `"환불"` 이나 `"돌려"` 단어가 있는 문서만 매칭
- 둘 다 부분적으로만 정확 → 합치면 낫다 (§5.2)

---

## 5. 실전 튜토리얼

### 5.1 Hybrid 검색 파이프라인

![Hybrid 검색 + Reranker](../assets/diagrams/ch12-hybrid-pipeline.svg#only-light)
![Hybrid 검색 + Reranker](../assets/diagrams/ch12-hybrid-pipeline-dark.svg#only-dark)

- **Dense** 가 놓치는 것 (정확한 용어·숫자) 을 **BM25** 가 잡음
- **BM25** 가 놓치는 것 (유의어·환언) 을 **Dense** 가 잡음
- 둘의 top-N 결과를 **RRF (Reciprocal Rank Fusion)** 로 병합:

```python title="rrf.py" linenums="1" hl_lines="4 5 6"
def rrf_merge(ranked_lists: list[list[int]], k: int = 60) -> dict:
    """각 리스트의 순위를 1/(k+rank) 로 환산해 합산."""
    scores = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
    return scores

# 사용
dense_top20 = list(np.argsort(-dense_scores)[:20])
bm25_top20  = list(np.argsort(-bm25_scores)[:20])
merged = rrf_merge([dense_top20, bm25_top20])
final_top5 = sorted(merged, key=merged.get, reverse=True)[:5]
```

RRF 는 **점수 스케일이 다른** 두 검색기를 합칠 때 쓰는 표준 기법. 파라미터 `k=60` 이 대부분 잘 동작.

### 5.2 Reranker — 순위를 다시 매기기

Dense + BM25 가 top-10 을 뽑아도 **관련 문서가 낮은 순위** 일 수 있음. **Cross-encoder reranker** 가 이걸 바로잡습니다.

![Reranker 효과](../assets/diagrams/ch12-rerank-impact.svg#only-light)
![Reranker 효과](../assets/diagrams/ch12-rerank-impact-dark.svg#only-dark)

**Dense 와의 차이**:

| | Dense (Bi-encoder) | Cross-encoder (Reranker) |
|---|---|---|
| 방식 | 쿼리·문서를 **각각** 벡터화 후 내적 | 쿼리+문서를 **함께** 입력해 관련도 출력 |
| 정확도 | 중 | **높음** |
| 속도 | **매우 빠름** (수백만 문서 가능) | 느림 (실용적으로 top-50 이내) |
| 역할 | **리콜** 담당 (넓게 긁기) | **정밀도** 담당 (정교하게 정렬) |

**실전**: Dense/BM25 로 top-20~50 뽑은 뒤, Cross-encoder 로 **상위 5~10** 만 재정렬.

```python title="rerank.py" linenums="1"
import voyageai  # 또는 cohere

vo = voyageai.Client()

def rerank(query: str, docs: list[str], top_k: int = 5):
    r = vo.rerank(
        query=query,
        documents=docs,
        model="rerank-2",
        top_k=top_k,
    )
    return [(item.document, item.relevance_score) for item in r.results]

# 사용
candidates = [docs[i] for i in merged_top20]
final = rerank("돈을 돌려받고 싶은데요", candidates, top_k=5)
for doc, score in final:
    print(f"{score:.3f}  {doc}")
```

**대안**:

- **Voyage** `rerank-2` — 다국어 · 성능↑
- **Cohere** `rerank-v3` — 오래된 표준
- **BGE Reranker** (오픈) — 로컬 GPU
- **자체 cross-encoder** (HuggingFace `sentence-transformers/ms-marco-*`)

### 5.3 MMR — 다양성

top-5 가 **거의 같은 내용** 의 chunk 들로 채워지면 정보 밀도가 낮음. **MMR (Maximal Marginal Relevance)** 는 관련성과 **다양성을 함께** 고려:

```
score(doc) = λ · relevance(doc) − (1−λ) · max_sim(doc, already_selected)
```

Chroma · LangChain 에 내장:

```python
results = col.query(
    query_embeddings=[q_emb],
    n_results=10,
    # LangChain: search_type="mmr", search_kwargs={"lambda_mult": 0.5}
)
```

`λ=0.5` 면 관련성·다양성 반반. 비슷한 chunk 가 많이 중복되면 **낮춰서** 다양성 강조.

### 5.4 Metadata Filter

`where` 조건으로 **검색 전 필터링**:

```python title="filter_examples.py"
# 최신 문서만
col.query(
    query_embeddings=[q_emb],
    n_results=10,
    where={"updated_at": {"$gte": "2026-01-01"}},
)

# 특정 팀 문서만 (권한 체크)
col.query(
    query_embeddings=[q_emb],
    n_results=10,
    where={"$and": [{"owner": "finance"}, {"lang": "ko"}]},
)
```

**필터 먼저 → 검색** 순서라 성능 이득. 권한 체크 · 최신성 · 언어 분리의 **첫 번째 방어선**.

### 5.5 파라미터 튜닝 — Chunk Size · Top-k · Overlap

한 번 정하고 끝나는 값이 아니라 **실패 분석 → 조정** 의 반복:

| 파라미터 | 늘리면 | 줄이면 |
|---|---|---|
| **Chunk size** ↑ | 맥락 보존 · 정밀도 ↓ · 토큰 ↑ | 세밀 · 맥락 손실 · 토큰 ↓ |
| **Chunk overlap** ↑ | 경계 보존 · 중복 증가 | 인덱스 효율 ↑ · 경계 잘림 위험 |
| **Top-k** ↑ | 리콜 ↑ · 노이즈 ↑ · 프롬프트 토큰 ↑ | 정밀 · 놓침 위험 |

**실전 출발점** (영어·한국어 혼용):

- `chunk_size=512`, `overlap=64`, `top-k=10` → rerank 후 `top-5`

### 5.6 검색 실패 수집·분류

```python title="retrieval_log.py" linenums="1"
def log_retrieval(query, retrieved, used, user_feedback=None):
    """검색 결과와 사용자 피드백을 로그."""
    record = {
        "query": query,
        "retrieved_ids": [r["id"] for r in retrieved],
        "retrieved_scores": [r["score"] for r in retrieved],
        "used_id": used["id"],           # 최종 인용된 것
        "feedback": user_feedback,       # 👍/👎
    }
    # DB 또는 파일에 append
```

**주간 리뷰**: 👎 를 받은 케이스 20건을 §2 의 5유형으로 분류. 가장 빈도 높은 유형부터 개선 (Ch 13 Advanced RAG 의 출발점).

---

## 6. 자주 깨지는 포인트

!!! warning "실수 1. Chunk 를 무조건 작게"
    recall 은 올라가지만 **맥락이 잘려** 답변 품질은 오히려 하락 가능. 작은 chunk 들을 prompt 에 전부 넣으면 **조합 이해 실패**.  
    **대응**: §5.5 의 `chunk_size=512 · overlap=64` 에서 시작. 실패 분석에 따라 조정.

!!! warning "실수 2. Rerank 를 top-500 에 적용"
    Cross-encoder 는 **느림**. top-500 rerank 하면 p95 지연이 5~10초.  
    **대응**: Dense/BM25 로 **top-20~50** 먼저 · 그 중에서만 rerank.

!!! warning "실수 3. Metadata 필터 없이 최신 문서 기대"
    "오늘 공지사항이 뭐야" 질문에 **3년 전 문서** 가 top-1. 의미 유사도만 보면 최신성 모름.  
    **대응**: `updated_at` 필터 + 최신성 boosting (점수에 시간 감쇠 곱하기).

!!! warning "실수 4. BM25 한국어 토큰화"
    `"환불해주세요"` 를 한 단어로 보면 BM25 매칭 실패. 의미는 있는데.  
    **대응**: **형태소 분석기** (`kiwi`, `KoNLPy`) 로 토큰화 → BM25 품질 크게 개선.

!!! warning "실수 5. Rerank 비용·지연 미측정"
    Voyage/Cohere rerank API는 유료·네트워크 지연 존재. top-k · 호출 빈도에 따라 비용 가파르게 증가.  
    **대응**: 평균 호출당 비용·지연 측정 → 월별 예산. 로컬 BGE reranker 로 대체 고려.

---

## 7. 운영 시 체크할 점

- [ ] **5유형 실패 분류** 주간 리뷰 (최소 20건 샘플)
- [ ] **파라미터 기록** — chunk_size, overlap, top-k, rerank top-n
- [ ] **Dense vs BM25 vs Hybrid** A/B 비교 → 기본 결정
- [ ] **Reranker** 비용·지연 대시보드 (Voyage/Cohere 호출당 가격)
- [ ] **Metadata filter** 의무화 — 권한·최신성·언어
- [ ] **최신성 boosting** 공식 명시 (`score * exp(-days/30)` 등)
- [ ] **MMR 파라미터** (`λ`) 유즈케이스별 분리
- [ ] **검색 실패 로그** (top-1 score < 임계치 케이스 별도 수집)

---

## 8. 확인 문제

- [ ] §4 `dense_vs_bm25.py` 를 한국어 문장 10건, 영어 10건으로 돌려 유형별 강점 정리
- [ ] RRF 병합 결과와 각 검색기 단독의 top-5 를 비교 — 병합의 이득 정량화
- [ ] Voyage rerank-2 를 §5.2 예제에 붙여 top-10 → top-5 재정렬 전후 관련 문서 비율 측정
- [ ] `chunk_size` 256 · 512 · 1024 로 변경하며 같은 쿼리의 precision/recall 변화 기록
- [ ] 일부러 **오래된 문서** 를 top-1 으로 올라오도록 만든 뒤, `updated_at` filter 로 해결

---

## 9. 원전 · 더 읽을 거리

- **BM25** — Robertson & Zaragoza (2009), *"The Probabilistic Relevance Framework"*
- **RRF** — Cormack et al. (2009), *"Reciprocal Rank Fusion outperforms Condorcet..."*
- **Voyage rerank-2**: [docs.voyageai.com/reference/reranker-api](https://docs.voyageai.com){target=_blank} — Anthropic 공식 추천
- **Cohere Rerank v3**: [docs.cohere.com/docs/rerank-2](https://docs.cohere.com){target=_blank}
- **BGE Reranker**: huggingface.co/BAAI/bge-reranker-large
- **LangChain Retrievers**: [python.langchain.com/docs/modules/data_connection/retrievers](https://python.langchain.com){target=_blank}
- **Stanford CME 295 Lec 7** — 프로젝트 `_research/stanford-cme295.md`

---

**다음 챕터** → [Ch 13. Advanced RAG](13-advanced-rag.md) :material-arrow-right:  
기본기는 완성. 이제 **HyDE · Self-RAG · GraphRAG · Agentic RAG** 등 논문급 기법들.
