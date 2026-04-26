# Ch 10. Embeddings and Vector Search Basics

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/en/part3/ch10_embedding.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - **Embeddings** — turning sentences into high-dimensional vectors and why that's useful
    - **Cosine similarity** to measure "meanings are close"
    - What **vector databases** (Chroma · Qdrant · Pinecone) actually do
    - **ANN** (Approximate Nearest Neighbor) and why you don't brute-force search
    - Real-world traps: dimension mismatch · mixed languages · normalization

!!! quote "Prerequisites"
    Read [Ch 9](09-why-rag.md) "Why RAG?" and understand RAG's role in the pipeline.

---

## 1. Concept — sentences as numbers

You know intuitively that "dog" and "cat" are similar, while "dog" and "pizza" are far apart. A computer sees none of that. **By themselves, the text strings are just different characters.**

**Embeddings** turn that intuition into numbers:

```
"dog"   → [0.12, -0.03, 0.87, ..., 0.41]     (1536 numbers)
"cat"   → [0.14, -0.01, 0.82, ..., 0.39]     (points almost the same direction)
"pizza" → [-0.40, 0.78, -0.12, ..., 0.05]    (points completely different)
```

Similar meaning becomes nearby vectors. That's the whole idea.

![Semantic space](../assets/diagrams/ch10-semantic-space.svg#only-light)
![Semantic space](../assets/diagrams/ch10-semantic-space-dark.svg#only-dark)

In reality that's 1536 dimensions (OpenAI `text-embedding-3-small`). The picture above shrinks it to 2D for intuition.

---

## 2. Why you need this — the limits of keyword search

Old-school keyword search (BM25 etc.) only finds exact word matches:

| Query | Traditional search result |
|---|---|
| "refund" | Documents with "refund" in them |
| "get my money back" | **No refund docs found** (keyword mismatch) |
| "refund policy" | Documents in English only |

**Semantic search** based on embeddings finds **meaning**, not keywords:

- "get my money back" ≈ "refund" → same cluster
- "refund policy" ≈ "환불 정책" (multilingual models)

This is what powers RAG.

---

## 3. Where embeddings are used

- **RAG search** — the main job of Part 3
- **Semantic search** — internal wikis, code search
- **Recommendations** — finding similar products or content
- **Deduplication** — clustering similar documents
- **Classification** (zero-shot) — compare text to category embeddings

---

## 4. Minimal example — similarity of three sentences

```bash
pip install openai numpy
```

```python title="similarity.py" linenums="1" hl_lines="8 9 10"
from openai import OpenAI
import numpy as np

client = OpenAI()

sentences = ["The dog barks loudly", "A dog is barking", "Pizza tastes delicious"]

res = client.embeddings.create(           # (1)!
    model="text-embedding-3-small",
    input=sentences,
)
vecs = np.array([d.embedding for d in res.data])

def cosine(a, b):                         # (2)!
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

print(f"dog-dog:     {cosine(vecs[0], vecs[1]):.3f}")   # expect ~0.85–0.95
print(f"dog-pizza:   {cosine(vecs[0], vecs[2]):.3f}")   # expect ~0.20–0.40
```

1. OpenAI's embedding model. Anthropic doesn't have a dedicated embedding API; **Voyage AI is recommended** instead.
2. **Cosine similarity**: the angle between two vectors. Range: -1 to 1. Closer to 1 = more similar.

If "dog-dog" is near 0.9 and "dog-pizza" is near 0.3, your embedding model works well. If "dog-pizza" is above 0.5, the model is either too coarse or weak on English.

---

## 5. Hands-on

### 5.1 Choosing an embedding model

| Model | Dimension | Multilingual | Cost | Notes |
|---|:-:|:-:|:-:|---|
| **OpenAI** `text-embedding-3-small` | 1536 | △ | $ | General purpose, budget-friendly |
| **OpenAI** `text-embedding-3-large` | 3072 | ○ | $$$ | Better quality |
| **Voyage** `voyage-3` | 1024 | ○ | $$ | Anthropic-recommended |
| **BGE-M3** (open source) | 1024 | ○○ | Free (local GPU) | Strong multilingual |
| **sentence-transformers** (open) | 384–768 | △ | Free | Lightweight, fast |

**How to choose**:
- Heavy Korean content → **BGE-M3** or **Voyage**
- Prototyping → **OpenAI small**
- GPU available → **BGE-M3** locally
- All-in Anthropic → **Voyage** (official recommendation)

### 5.2 Cosine similarity and normalization

```python title="cosine_math.py" linenums="1"
import numpy as np

def cosine(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# If vectors are normalized, dot product IS cosine similarity
def cosine_normalized(a, b):
    return np.dot(a, b)  # (1)!

# Most OpenAI/Voyage embeddings come L2 normalized (length=1)
# → Pre-normalized for storage; query search just uses dot product
```

1. **For millions of documents, this optimization matters.** `np.dot` gets GPU/BLAS acceleration.

### 5.3 Vector DB — hands-on with Chroma

Finding top-k from millions of documents goes to a **vector database**. **Chroma** is the easiest starting point:

```bash
pip install chromadb
```

```python title="chroma_basic.py" linenums="1" hl_lines="4 12 17"
import chromadb
from openai import OpenAI

chroma = chromadb.PersistentClient(path="./chroma_db")   # (1)!
client = OpenAI()

def embed(texts: list[str]) -> list[list[float]]:
    res = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [d.embedding for d in res.data]

# Create collection (think: table)
col = chroma.get_or_create_collection(name="faq_kb")

docs = [
    "Refunds available within 7 days of purchase. Manager approval required.",
    "Shipping takes 2–3 business days from order date.",
    "Loyalty points earn 1% per dollar spent, valid for 3 months.",
]
col.add(                                              # (2)!
    ids=[f"doc-{i}" for i in range(len(docs))],
    documents=docs,
    embeddings=embed(docs),
    metadatas=[{"source": "policy.md"} for _ in docs],
)

# Search
query = "How do I get a refund?"
q_emb = embed([query])[0]
result = col.query(query_embeddings=[q_emb], n_results=2)   # (3)!

for doc, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
    print(f"distance={dist:.3f}  [{meta['source']}]  {doc}")
```

1. Persists to disk (`./chroma_db/`). For memory-only, use `chromadb.Client()`.
2. Store documents, vectors, and metadata together. Metadata is used for **filtering** and **citations**.
3. Query by embedding, get top-k. **Distance** is the metric (lower = closer). For cosine distance, `0 = exact match`.

### 5.4 ANN — why not brute-force?

Finding top-10 from 1M documents means **1M cosine calculations**. Too slow.

**ANN (Approximate Nearest Neighbor)** returns a **near-perfect result fast**:

- **HNSW** (Hierarchical Navigable Small World) — hierarchical graph traversal. Chroma and Qdrant use this by default.
- **IVF** (Inverted File) — narrow down clusters first
- **PQ** (Product Quantization) — compress vectors to save memory

At 99% accuracy, you get **100× speedup**. For Part 3, just know "ANN exists" — your vector DB handles it.

### 5.5 Query vs. document embeddings — asymmetric

Embedding queries and documents with the same model usually works. But **long documents vs. short queries** benefit from newer models that support **role hints**:

**Voyage example**:

```python
# For storage (documents)
client.embed(texts=docs, input_type="document")

# For search (queries)
client.embed(texts=[query], input_type="query")
```

This is called **symmetric vs. asymmetric** embedding. If accuracy gaps are large, use different roles for queries and documents.

---

## 6. Common pitfalls

!!! warning "Pitfall 1. Dimension mismatch"
    You embed with OpenAI small (1536 dims), store vectors, then switch to Voyage (1024 dims). Explosion. Or upgrade your model and dimensions change.  
    **Fix**: Record `embedding_model` and `dimension` in collection metadata. On model change, **re-embed everything**. Happens more often than you'd think.

!!! warning "Pitfall 2. Normalization confusion"
    Some models return L2 normalized (length=1), others don't. Using dot product on non-normalized vectors gives wrong values.  
    **Fix**: Force normalization post-embedding: `vec / np.linalg.norm(vec)`. If your DB uses cosine distance, it handles this internally.

!!! warning "Pitfall 3. Mixed languages"
    Korean docs + English query (or vice versa) tanks quality unless you use a **multilingual model**.  
    **Fix**: Check multilingual benchmarks for Voyage, BGE-M3, or OpenAI's large model. For Korean-only, consider KURE or KoE5.

!!! warning "Pitfall 4. Over-interpreting short queries"
    A one-word query like "refund" has high variance in the embedding space — lots of noise. Unrelated docs creep into top-k.  
    **Fix**: (a) Use HyDE to generate hypothetical answers first (Ch 13), (b) Hybrid keyword+semantic search (Ch 12), (c) Prompt-based query expansion.

!!! warning "Pitfall 5. No metadata on save"
    Later you forget which doc a result came from, which section, who owns it. No citations. No permission filtering.  
    **Fix**: Always store metadata at save time: `source`, `page`, `section`, `updated_at`, `owner`.

---

## 7. Operations checklist

- [ ] **Log embedding model · dimension · version** in collection metadata
- [ ] **Normalization strategy consistent** across documents and queries
- [ ] **Language distribution monitoring** (query/doc language ratios) → guides model replacement
- [ ] **Re-embedding script ready** (batch operation for model upgrades)
- [ ] **Metadata filtering active** (`updated_at >= X`, `owner == Y`)
- [ ] **Vector DB backups periodic** (re-embedding at scale is expensive)
- [ ] **Search latency monitored** (p95 > 300ms? tune ANN parameters)
- [ ] **PII in embeddings** — be aware: personal info bakes into vectors (reconstruction attacks studied)

---

## 8. Exercises

- [ ] Take §4's `similarity.py`, run it on 10 pairs (synonyms, antonyms, unrelated), and make a table of similarity scores
- [ ] Add 5–10 FAQs to the Chroma example in §5.3 and test top-k quality with varied queries
- [ ] Run the same docs on **both OpenAI small and Voyage-3** side by side. Compare top-3 result differences.
- [ ] Intentionally skip normalization on a vector. Calculate cosine similarity. See how much values drift.
- [ ] Mix English questions with Korean documents. Measure top-k quality. Feel the need for multilingual models.

---

## 9. Sources and further reading

- **OpenAI Embeddings**: [platform.openai.com/docs/guides/embeddings](https://platform.openai.com/docs){target=_blank}
- **Voyage AI**: [docs.voyageai.com](https://docs.voyageai.com){target=_blank} — Anthropic's official recommendation
- **BGE-M3** (multilingual open source): [huggingface.co/BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3){target=_blank}
- **Chroma**: [docs.trychroma.com](https://docs.trychroma.com){target=_blank}
- **HNSW paper** — Malkov & Yashunin (2018), "Efficient and Robust ANN Search Using Hierarchical NSW Graphs"
- **Stanford CME 295 Lec 7** — research summary in `_research/stanford-cme295.md`

---

**Next** → [Ch 11. The RAG Pipeline End-to-End](11-pipeline.md) :material-arrow-right:  
Embeddings plus vector DB are ingredients. Next: **retrieval, ranking, citation — the full flow from document ingestion to grounded answers.**
