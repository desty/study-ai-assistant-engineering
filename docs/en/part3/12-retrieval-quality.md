# Ch 12. Improving Retrieval Quality

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part3/ch12_retrieval_quality.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - **Answer quality is 70% retrieval quality** — why generation alone can't fix a bad search
    - **Five types of retrieval failure** (recall · precision · ranking · metadata · chunk boundaries)
    - **BM25 + Dense hybrid search** (RRF merging)
    - **Cross-encoder reranker** — boost precision by reordering your top candidates
    - **MMR** (diversity) and **metadata filters**
    - Tradeoffs between chunk size · top-k · rerank cost

!!! quote "Prerequisites"
    You've run `mini_rag.py` from [Ch 11](11-pipeline.md).

---

## 1. Concept — Retrieval sets the ceiling on answers

In Ch 11's query pipeline, if you pull back **irrelevant documents**, the LLM tries to answer from them anyway. You get hallucination or "I don't know."

> **Generation can't recover from retrieval failure.**

So the biggest time sink in Part 3 is improving retrieval quality. This chapter is your toolbox.

---

## 2. Five types of retrieval failure

| Type | Symptom | Root cause |
|---|---|---|
| **Recall miss** | Relevant doc **never in top-k** | Query–doc representation gap · chunk boundary issues |
| **Precision miss** | Junk docs **mixed into top-k** | ANN score alone · no diversity |
| **Ranking error** | Relevant doc exists **but ranks low** | Dense-only limits (semantic similarity ≠ exact match) |
| **Metadata ignored** | Stale or private docs in top-k | No `updated_at` or `owner` filters |
| **Chunk boundary** | Answer **spans two chunks** | Fixed-length chunking |

Each type needs **different tools**. This chapter maps them.

---

## 3. Where it's used

The techniques here go into **every production RAG**:

- FAQ bot using just top-1? → **rerank to fix ranking**
- Long policy documents? → **BM25 hybrid for exact clause matches**
- Multilingual docs? → **metadata filter by language**
- Freshness matters? → **updated_at filter**

---

## 4. Minimal example — Dense vs BM25 vs Hybrid

```bash
pip install rank-bm25
```

```python title="dense_vs_bm25.py" linenums="1" hl_lines="16 23"
from openai import OpenAI
from rank_bm25 import BM25Okapi
import numpy as np

openai = OpenAI()

docs = [
    "Refunds available within 7 days of purchase, manager approval required.",
    "Shipping: 2–3 business days, +2 days for remote areas.",
    "Points: 1% of purchase amount, valid for 3 months.",
    "Warranty: 1 year from purchase date.",
    "Non-refundable items: custom-made products, opened software.",
]

# Dense
def embed(texts):
    r = openai.embeddings.create(model="text-embedding-3-small", input=texts)
    return np.array([d.embedding for d in r.data])

doc_vecs = embed(docs)

# BM25
tokenized = [d.split() for d in docs]           # (1)!
bm25 = BM25Okapi(tokenized)

query = "I want my money back"
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

1. Whitespace splitting is rough for most languages. Production code needs a proper tokenizer (`kiwi`, `KoNLPy` for Korean, spaCy for others).
2. BM25 only scores high if **"refund"** or **"money"** appears verbatim. It has no semantic knowledge.

**Key observations**:

- Dense finds meaning without the exact word ("I want my money back" → refund doc)
- BM25 matches only documents with the word present
- Both miss cases the other catches → combine them (§5.2)

---

## 5. Hands-on

### 5.1 Hybrid search pipeline

![Hybrid search + Reranker](../assets/diagrams/ch12-hybrid-pipeline.svg#only-light)
![Hybrid search + Reranker](../assets/diagrams/ch12-hybrid-pipeline-dark.svg#only-dark)

- **Dense** misses exact terms and numbers that **BM25** catches
- **BM25** misses synonyms and paraphrases that **Dense** catches
- Merge their top-N results using **RRF (Reciprocal Rank Fusion)**:

```python title="rrf.py" linenums="1" hl_lines="4 5 6"
def rrf_merge(ranked_lists: list[list[int]], k: int = 60) -> dict:
    """Merge ranked lists by converting each rank to 1/(k+rank) and summing."""
    scores = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank + 1)
    return scores

# Usage
dense_top20 = list(np.argsort(-dense_scores)[:20])
bm25_top20  = list(np.argsort(-bm25_scores)[:20])
merged = rrf_merge([dense_top20, bm25_top20])
final_top5 = sorted(merged, key=merged.get, reverse=True)[:5]
```

RRF is the standard way to merge two rankers with different score scales. Parameter `k=60` works well in most cases.

### 5.2 Reranker — re-sort your candidates

Dense + BM25 might return top-10, but **relevant docs could rank low**. A **cross-encoder reranker** fixes that.

![Reranker effect](../assets/diagrams/ch12-rerank-impact.svg#only-light)
![Reranker effect](../assets/diagrams/ch12-rerank-impact-dark.svg#only-dark)

**Dense vs cross-encoder**:

| | Dense (Bi-encoder) | Cross-encoder (Reranker) |
|---|---|---|
| Method | Embed query and doc **separately**, then score with dot product | Feed query + doc **together**, output relevance |
| Accuracy | Medium | **High** |
| Speed | **Very fast** (millions of docs) | Slower (practically top-50 max) |
| Role | **Recall** (cast wide) | **Precision** (rank tight) |

**In practice**: Dense/BM25 gets you top-20–50, then cross-encoder re-sorts just the **top 5–10**.

```python title="rerank.py" linenums="1"
import voyageai  # or cohere

vo = voyageai.Client()

def rerank(query: str, docs: list[str], top_k: int = 5):
    r = vo.rerank(
        query=query,
        documents=docs,
        model="rerank-2",
        top_k=top_k,
    )
    return [(item.document, item.relevance_score) for item in r.results]

# Usage
candidates = [docs[i] for i in merged_top20]
final = rerank("I want my money back", candidates, top_k=5)
for doc, score in final:
    print(f"{score:.3f}  {doc}")
```

**Alternatives**:

- **Voyage** `rerank-2` — multilingual · higher accuracy
- **Cohere** `rerank-v3` — established standard
- **BGE Reranker** (open-source) — runs on your GPU
- **Custom cross-encoder** (HuggingFace `sentence-transformers/ms-marco-*`)

### 5.3 MMR — diversity

If top-5 is all near-duplicates, information density plummets. **MMR (Maximal Marginal Relevance)** balances relevance and **diversity**:

```
score(doc) = λ · relevance(doc) − (1−λ) · max_sim(doc, already_selected)
```

Built into Chroma and LangChain:

```python
results = col.query(
    query_embeddings=[q_emb],
    n_results=10,
    # LangChain: search_type="mmr", search_kwargs={"lambda_mult": 0.5}
)
```

With `λ=0.5`, you balance relevance and diversity equally. Lower it to emphasize diversity when you're getting too many similar chunks.

### 5.4 Metadata filters

Filter **before search** using `where` conditions:

```python title="filter_examples.py"
# Only recent documents
col.query(
    query_embeddings=[q_emb],
    n_results=10,
    where={"updated_at": {"$gte": "2026-01-01"}},
)

# Only from one team (access control)
col.query(
    query_embeddings=[q_emb],
    n_results=10,
    where={"$and": [{"owner": "finance"}, {"lang": "en"}]},
)
```

**Filter first, then search** — you get better latency. Your first line of defense for access control · freshness · language separation.

### 5.5 Parameter tuning — chunk size · top-k · overlap

Set once and forget? No. You'll cycle through **failure analysis → adjust** repeatedly:

| Parameter | Increase it | Decrease it |
|---|---|---|
| **Chunk size** ↑ | Preserve context · lower precision · more tokens | Finer detail · lose context · fewer tokens |
| **Chunk overlap** ↑ | Protect boundaries · redundancy grows | Better index efficiency · boundary cutoff risk |
| **Top-k** ↑ | Higher recall · more noise · more prompt tokens | Tight results · miss relevant docs |

**Starting point** (English and mixed-language):

- `chunk_size=512`, `overlap=64`, `top-k=10` → rerank down to `top-5`

### 5.6 Collect and classify retrieval failures

```python title="retrieval_log.py" linenums="1"
def log_retrieval(query, retrieved, used, user_feedback=None):
    """Log search results and user feedback."""
    record = {
        "query": query,
        "retrieved_ids": [r["id"] for r in retrieved],
        "retrieved_scores": [r["score"] for r in retrieved],
        "used_id": used["id"],           # what the LLM actually cited
        "feedback": user_feedback,       # 👍/👎
    }
    # Append to DB or file
```

**Weekly review**: Take 20 cases with 👎 feedback and bucket them into the 5 failure types from §2. Fix the most common first (that feeds into Ch 13 Advanced RAG).

---

## 6. Common breaking points

!!! warning "Mistake 1: Shrink chunks blindly"
    Recall goes up, but context gets cut and answer quality can drop. Tiny chunks in your prompt lose their relationship to each other.  
    **Fix**: Start with `chunk_size=512 · overlap=64`. Adjust only after failure analysis.

!!! warning "Mistake 2: Rerank top-500"
    Cross-encoders are slow. Reranking 500 docs pushes p95 latency to 5–10 seconds.  
    **Fix**: Dense/BM25 gets you **top-20–50** first, then rerank only that.

!!! warning "Mistake 3: Expect fresh docs without filters"
    A question like "What's today's announcement?" returns a 3-year-old doc at rank 1. Semantic similarity doesn't capture recency.  
    **Fix**: Use `updated_at` filter + recency boost (multiply score by time decay).

!!! warning "Mistake 4: Tokenize Korean with just split()"
    `"환불해주세요"` becomes one token; BM25 fails to match. Semantically it's there, but no word overlap.  
    **Fix**: Use a morphological analyzer (`kiwi`, `KoNLPy`) before BM25.

!!! warning "Mistake 5: Don't track reranker cost"
    Voyage and Cohere rerank APIs cost money and add latency. Costs grow fast with top-k and call volume.  
    **Fix**: Log cost and latency per call → monthly budget. Consider switching to local BGE reranker.

---

## 7. Production checklist

- [ ] **Weekly review of 5 failure types** (at least 20 samples)
- [ ] **Parameter log** — chunk_size, overlap, top-k, rerank top-n
- [ ] **Dense vs BM25 vs Hybrid A/B test** → pick your baseline
- [ ] **Reranker cost/latency dashboard** (price per Voyage/Cohere call)
- [ ] **Metadata filter required** — access control · freshness · language
- [ ] **Recency boost formula documented** (e.g., `score * exp(-days/30)`)
- [ ] **MMR lambda (λ) tuned per use case**
- [ ] **Retrieval failure logs** (separate bucket for top-1 score below threshold)

---

## 8. Practice problems

- [ ] Run §4's `dense_vs_bm25.py` on 10 English and 10 non-English sentences, list strengths per type
- [ ] Compare RRF merge output to each ranker's top-5 — quantify the merge benefit
- [ ] Attach Voyage rerank-2 to §5.2, measure precision before/after top-10 → top-5
- [ ] Vary chunk_size to 256 · 512 · 1024 on the same query, log precision/recall deltas
- [ ] Artificially make old docs rank first, then solve with `updated_at` filter

---

## 9. Further reading

- **BM25** — Robertson & Zaragoza (2009), *"The Probabilistic Relevance Framework"*
- **RRF** — Cormack et al. (2009), *"Reciprocal Rank Fusion outperforms Condorcet..."*
- **Voyage rerank-2**: [docs.voyageai.com/reference/reranker-api](https://docs.voyageai.com){target=_blank} — officially recommended by Anthropic
- **Cohere Rerank v3**: [docs.cohere.com/docs/rerank-2](https://docs.cohere.com){target=_blank}
- **BGE Reranker**: huggingface.co/BAAI/bge-reranker-large
- **LangChain Retrievers**: [python.langchain.com/docs/modules/data_connection/retrievers](https://python.langchain.com){target=_blank}
- **Stanford CME 295 Lec 7** — archived in project `_research/stanford-cme295.md`

---

**Next** → [Ch 13. Advanced RAG](13-advanced-rag.md) :material-arrow-right:  
Foundations set. Now **HyDE · Self-RAG · GraphRAG · Agentic RAG** — production-grade techniques from the papers.
