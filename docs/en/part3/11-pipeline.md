# Ch 11. The Full RAG Pipeline

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part3/ch11_pipeline.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - RAG's two stages — **Indexing** (document prep) + **Query** (execution)
    - Document collection · chunking · embedding · storage · retrieval · augmentation · generation · **citation**
    - Build one **end-to-end working system** with a small PDF set
    - The three gotchas: chunk boundaries cut mid-sentence · citation hallucination · context overflow

!!! quote "Prerequisites"
    [Ch 9](09-why-rag.md) and [Ch 10](10-embedding.md) required. Colab + OpenAI or Anthropic key.

---

## 1. Concept — RAG is two stages

The first mistake is treating RAG as a black box: "feed documents, get answers." Split it into **two stages** instead.

![RAG pipeline: two stages](../assets/diagrams/ch11-rag-pipeline.svg#only-light)
![RAG pipeline: two stages](../assets/diagrams/ch11-rag-pipeline-dark.svg#only-dark)

| | **Indexing (prep)** | **Query (execution)** |
|---|---|---|
| When | **Once** when documents are added or changed | **Every time** a user asks |
| Cost | Batch (offline OK) | Real-time (p95 goal: 1–2 sec) |
| Steps | Load → chunk → embed → store | Embed query → retrieve → augment prompt → generate |
| Connection | **Vector DB** — both share the same embedding space |

Separating them cleanly means **batch pipelines** (indexing) and **live services** (query) can be tuned independently.

---

## 2. Why split it this way

Real bugs live **between stages**:

- Document load returns **malformed text** (PDF tables · OCR garbage) → chunking breaks → empty embeddings
- You swap embedding models but **leave the vector DB alone** → dimension mismatch
- Retrieval works fine but **augmentation overflows tokens** partway through

Every stage must be **observable** to fix anything.

---

## 3. Where it's used

Real-world examples:

- **Internal knowledge Q&A bots** — Notion / Confluence / Google Drive docs end-to-end
- **Support assistants** — FAQs · product manuals · policies
- **Codebase QA** — source + README + commit messages
- **Legal / medical search** — case law · papers (citation required)

---

## 4. Minimal example — 8 steps end-to-end

```bash
pip install anthropic openai chromadb pypdf
```

Start with two tiny policy documents:

```python title="mini_rag.py" linenums="1" hl_lines="16 22 29 39 48"
from anthropic import Anthropic
from openai import OpenAI
import chromadb

anthropic = Anthropic()
openai = OpenAI()

# ---------- INDEXING ----------

# 1) Load documents (here, hardcoded strings)
docs = [
    {
        "id": "refund_policy",
        "text": """[Refund Policy]
Refunds accepted within 7 days of purchase with manager approval.
Products used 5+ consecutive days require executive approval.
Emergency cases: email notice first, apply retroactively.""",
        "source": "policy.md#refund",
    },
    {
        "id": "shipping_policy",
        "text": """[Shipping Policy]
2–3 business days from order date.
Remote areas: +2 days additional.
Free shipping on orders $50+.""",
        "source": "policy.md#shipping",
    },
]

# 2) Chunking — here they're short enough to keep whole
chunks = docs  # In production, see §5.2 for splitting

def embed(texts):
    res = openai.embeddings.create(model="text-embedding-3-small", input=texts)
    return [d.embedding for d in res.data]

# 3) Embedding + 4) Store
chroma = chromadb.PersistentClient(path="./mini_rag_db")
col = chroma.get_or_create_collection(name="policies")
col.upsert(
    ids=[c["id"] for c in chunks],
    documents=[c["text"] for c in chunks],
    embeddings=embed([c["text"] for c in chunks]),
    metadatas=[{"source": c["source"]} for c in chunks],
)

# ---------- QUERY ----------

def rag_answer(question: str, k: int = 2) -> str:
    # 5) Embed query + 6) Retrieve
    q_emb = embed([question])[0]
    res = col.query(query_embeddings=[q_emb], n_results=k)
    retrieved = [
        (doc, meta["source"]) for doc, meta
        in zip(res["documents"][0], res["metadatas"][0])
    ]

    # 7) Augment — append retrieval results to the prompt
    context = "\n\n".join(f"[{src}]\n{doc}" for doc, src in retrieved)
    system = f"""Answer only from the company documents below.
If the answer is not in the documents, say "Not in the documents."
Always cite the [source] at the end of your answer.

{context}"""

    # 8) Generate
    r = anthropic.messages.create(
        model="claude-haiku-4-5", max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": question}],
    )
    return r.content[0].text

print(rag_answer("I want to refund a purchase"))
```

Expected output:

```
You can request a refund within 7 days of purchase with manager approval.
If the product was used for 5+ consecutive days, you'll also need executive approval.

Citation: [policy.md#refund]
```

**That's all there is.** The rest of Part 3 is about raising the quality, speed, and scale of each stage.

---

## 5. Hands-on

### 5.1 Document collection — loaders by format

```python title="loaders.py" linenums="1"
from pypdf import PdfReader
from pathlib import Path

def load_pdf(path: str) -> list[dict]:
    """Split by page · include page number in metadata."""
    reader = PdfReader(path)
    return [
        {"text": p.extract_text() or "", "source": f"{path}#page={i+1}"}
        for i, p in enumerate(reader.pages)
    ]

def load_markdown(path: str) -> list[dict]:
    text = Path(path).read_text()
    # Split by headings
    sections = []
    current = {"title": "intro", "text": ""}
    for line in text.split("\n"):
        if line.startswith("## "):
            if current["text"].strip():
                sections.append(current)
            current = {"title": line[3:].strip(), "text": ""}
        else:
            current["text"] += line + "\n"
    if current["text"].strip():
        sections.append(current)
    return [{"text": s["text"], "source": f"{path}#{s['title']}"} for s in sections]
```

!!! tip "PDF gotchas"
    `pypdf` extracts text only. **Tables, images, formulas** break. For production, compare `unstructured` · `docling` · `PyMuPDF (fitz)`.

### 5.2 Chunking strategies

![Chunking strategies compared](../assets/diagrams/ch11-chunking.svg#only-light)
![Chunking strategies compared](../assets/diagrams/ch11-chunking-dark.svg#only-dark)

**Production recommendation**:

| Strategy | Description | When |
|---|---|---|
| **Fixed size** | Cut every N tokens with overlap | Recommended starting point |
| **By section** | Respect heading / paragraph boundaries | Structured docs (Markdown, HTML) |
| **Semantic** | Cut at meaning shifts | Quality-first scenarios |
| **Sliding window** | Small chunks + heavy overlap | Prioritize retrieval recall |

**With LangChain**:

```python title="chunker.py" linenums="1"
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,         # Characters, not tokens (512 chars ≈ 150–300 tokens)
    chunk_overlap=50,        # Overlap to preserve boundary context
    separators=["\n\n", "\n", ". ", " ", ""],  # (1)!
)

def chunk_docs(docs: list[dict]) -> list[dict]:
    out = []
    for d in docs:
        for i, chunk in enumerate(splitter.split_text(d["text"])):
            out.append({
                "text": chunk,
                "source": f"{d['source']}#chunk={i}",
            })
    return out
```

1. Priority: paragraph → line → sentence → space. Respects boundaries to **minimize semantic loss**.

### 5.3 Storage + metadata for citation

To track **where each fact came from**, metadata design is critical.

```python title="metadata_schema.py" linenums="1"
# Recommended metadata schema
{
    "source": "policy.md#refund",       # Origin doc + anchor
    "chunk_id": 3,                       # Position in document
    "updated_at": "2026-04-15",          # For staleness checks
    "owner": "legal-team",               # For permission checks
    "doc_type": "policy",                # For filtering (policy | faq | wiki)
    "lang": "en",                        # For multi-language filtering
}
```

Use metadata filters on retrieval:

```python
col.query(
    query_embeddings=[q_emb],
    n_results=5,
    where={"doc_type": "policy", "lang": "en"},
)
```

### 5.4 Augmentation — formatting for the prompt

How you inject retrieval results into the prompt shapes generation quality.

```python title="augment.py" linenums="1" hl_lines="6 7 8"
def build_prompt(question: str, retrieved: list[dict]) -> str:
    # Defend against overflow — keep only top k
    retrieved = retrieved[:5]
    context = "\n\n".join(
        f"<doc source=\"{c['source']}\" updated=\"{c.get('updated_at', 'N/A')}\">\n"
        f"{c['text']}\n"
        f"</doc>"
        for c in retrieved
    )
    return f"""<context>
{context}
</context>

Answer only from the above documents. If not found, say "Not in the documents."
Support every claim with a [source] citation."""
```

XML tags draw clear boundaries — the model won't confuse documents with user input (defense against prompt injection).

### 5.5 Enforce citations

If the answer comes back without citations, **auto-requery**:

```python title="citation_enforce.py" linenums="1"
import re

def has_citation(text: str) -> bool:
    return bool(re.search(r"\[[\w\-\.#=]+\]", text))

def answer_with_citation(question, retrieved, retries=1):
    for attempt in range(retries + 1):
        r = anthropic.messages.create(
            model="claude-haiku-4-5", max_tokens=512,
            system=build_prompt(question, retrieved),
            messages=[{"role": "user", "content": question}],
        )
        text = r.content[0].text
        if has_citation(text):
            return text
    # Final fallback — return without citation but log it
    return text + "\n\n[Warning: no citation found]"
```

### 5.6 Token budget management

Enforce `max_tokens` and context budgets:

```python title="token_budget.py" linenums="1"
# Example: Claude Haiku context 200K
# system 500 + user question 100 + retrieved docs N + response 2048 <= 200K
#   → retrieved docs budget ≈ 197K max
# In practice, much tighter: aim for 5–10 retrieved chunks for fast response
```

---

## 6. Common pitfalls

!!! warning "Mistake 1. Chunk boundaries cut sentences in half"
    Fixed-length cuts often **split a sentence mid-word**. Embedding quality · answer accuracy both suffer.  
    **Fix**: use `RecursiveCharacterTextSplitter` to **respect paragraph → line → sentence** boundaries. Add 50–100 character overlap to preserve context across boundaries.

!!! warning "Mistake 2. Citation hallucination"
    You prompt "cite your source" but the model **invents [sources] that don't exist**.  
    **Fix**: (a) list allowed sources in the prompt, (b) **validate citations after generation** (must be in actual retrieval results), (c) use LangChain's `citations` feature.

!!! warning "Mistake 3. Context overflow"
    You dump top-10 results straight into the prompt → exceeds context window → error.  
    **Fix**: cap k (5–10) + token limit per chunk + **budget calculations**. If over, summarize or drop results.

!!! warning "Mistake 4. Document updates don't show up"
    You edited the PDF/Markdown but it's not in the search results. Needs **re-embedding and vector DB upsert**.  
    **Fix**: compare file hashes → **incremental re-embedding pipeline** for only changed files. Cron or Git hook trigger.

!!! warning "Mistake 5. Sensitive docs leaked into the index"
    Salary tables · PII slips into the RAG corpus → anyone can find it via retrieval.  
    **Fix**: classify documents → **split by sensitivity into separate collections** + metadata-based permissions. Safest: **don't index sensitive data at all**.

---

## 7. Production checklist

- [ ] **Indexing pipeline** automated (detect changes → re-embed → upsert)
- [ ] **Incremental updates** — don't re-embed everything
- [ ] **Chunking parameters** logged (size, overlap, separators) — reproducibility
- [ ] **Metadata schema** documented (source · updated_at · owner · doc_type · lang)
- [ ] **Citation validation** — verify [source] in response actually came from retrieval
- [ ] **Token budget dashboard** — break down system / retrieval / query / response · flag overages
- [ ] **Low-recall logs** — collect cases where top-k scores are low (signals missing content)
- [ ] **Permission filtering** — separate collections by user group or access level

---

## 8. Exercises

- [ ] Run §4's `mini_rag.py` and build a bot with 5–10 of your own docs
- [ ] Apply 2 of the 4 chunking strategies from §5.2 to the same document and compare retrieval quality
- [ ] Deliberately trigger citation hallucination (demand fake [sources]) and verify §5.5 catches it
- [ ] Simulate document update — edit the original, add incremental re-embedding code
- [ ] Vary top-k: 1 / 5 / 20. Compare answer quality, token spend, and latency

---

## 9. Sources and further reading

- **LangChain RAG Tutorial**: [python.langchain.com/docs/tutorials/rag](https://python.langchain.com/docs/tutorials/rag){target=_blank}
- **LlamaIndex** (RAG-focused framework): [docs.llamaindex.ai](https://docs.llamaindex.ai){target=_blank}
- **Anthropic "Adding context with RAG"**: [docs.anthropic.com](https://docs.anthropic.com){target=_blank}
- **Chunking strategies**: Pinecone blog "Chunking Strategies for LLM Applications"
- **Stanford CME 295 Lec 7** — project `_research/stanford-cme295.md`

---

**Next** → [Ch 12. Improving Retrieval Quality](12-retrieval-quality.md) :material-arrow-right:  
You've got the basic pipeline working. Now we **diagnose why retrieval fails** and use hybrid search and reranking to pull better documents into the prompt.
