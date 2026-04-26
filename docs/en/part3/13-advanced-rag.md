# Ch 13. Advanced RAG

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part3/ch13_advanced_rag.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - **HyDE** (Hypothetical Document Embeddings) — embed a hypothetical answer instead of the raw query
    - **Self-RAG** — let the LLM **judge whether retrieval is needed, and whether results are good**
    - **GraphRAG** — entity-graph-based reasoning (concept intro)
    - **Agentic RAG** — search as a tool inside the Part 5 agent loop
    - Query rewriting, multi-query, recursive retrieval
    - "Advanced doesn't always mean better" — cost, latency, and complexity trade-offs

!!! quote "Prerequisites"
    [Ch 12](12-retrieval-quality.md) — hybrid search, rerankers, and metadata filters feel natural.

---

## 1. Concept — when basic RAG hits its ceiling

The pipelines from Ch 11–12 handle **80% of queries**. But a few patterns make basic RAG struggle:

| Failure mode | Example | Fix |
|---|---|---|
| **Short, vague queries** | "AI?" · "policy?" | **HyDE** · Query Rewriting |
| **Queries you can answer without retrieval** | "Hi there" → RAG waste | **Self-RAG** |
| **Questions that need multiple sources stitched together** | "Who's the budget owner for Team A × Project B?" | **GraphRAG** |
| **Queries that need search → compute → search again** | "This year's growth rate vs. last year?" | **Agentic RAG** |

Each variant solves **one specific bottleneck**. In practice, you combine them.

![Advanced RAG variants](../assets/diagrams/ch13-rag-variants.svg#only-light)
![Advanced RAG variants](../assets/diagrams/ch13-rag-variants-dark.svg#only-dark)

---

## 2. Why you need them — three structural limits of basic RAG

1. **Query ↔ document representation mismatch** — users write short queries ("refund?") while documents are long. Embedding distance grows.
2. **Assumes retrieval is always needed** — small talk, quick math, greetings waste retrieval budgets.
3. **Assumes one search is enough** — complex questions need multiple lookups.

Each variant addresses one of these.

---

## 3. Where they're used

| Technique | When it shines | Cost |
|---|---|---|
| **HyDE** | Short queries · expert domains | +1 LLM call |
| **Self-RAG** | General chatbots · cut unnecessary searches | +1–2 LLM calls |
| **GraphRAG** | Multi-entity questions · summarization | Big index build |
| **Agentic RAG** | Complex questions · external tools | Multiple loop iterations (Part 5) |

---

## 4. HyDE — minimal example

**The idea**: short query embeddings are noisy. **Generate a fake answer** with an LLM, embed that longer text instead → better document matches.

![HyDE details](../assets/diagrams/ch13-hyde-detail.svg#only-light)
![HyDE details](../assets/diagrams/ch13-hyde-detail-dark.svg#only-dark)

```python title="hyde.py" linenums="1" hl_lines="7 8 9 10 11 12"
from anthropic import Anthropic
from openai import OpenAI

anthropic = Anthropic()
openai = OpenAI()

def hyde_search(query: str, col, k: int = 5):
    # 1) Ask LLM to generate a hypothetical answer
    r = anthropic.messages.create(
        model="claude-haiku-4-5", max_tokens=256,
        system="Write a factual answer to the question below. It doesn't need to be perfect. Keep it to 4 sentences.",
        messages=[{"role": "user", "content": query}],
    )
    hypothetical = r.content[0].text

    # 2) Embed the hypothetical answer
    emb = openai.embeddings.create(
        model="text-embedding-3-small",
        input=[hypothetical],
    ).data[0].embedding

    # 3) Search for real documents using the hypothetical embedding
    res = col.query(query_embeddings=[emb], n_results=k)
    return res

# Usage
results = hyde_search("refund policy?", col)
```

**Result**: short queries see **20–40% better recall** (depends on domain).

**Trap**: if the LLM makes up a wrong answer, you'll search in the wrong direction → see §6.

---

## 5. Hands-on

### 5.1 Query Rewriting / Expansion

HyDE's cousin: **rephrase and expand** the query with an LLM, then do multi-query retrieval.

```python title="query_expansion.py" linenums="1"
def expand_query(q: str) -> list[str]:
    r = anthropic.messages.create(
        model="claude-haiku-4-5", max_tokens=256,
        system="Rewrite the user's query as 3 different questions with the same meaning. Return only a JSON array.",
        messages=[{"role": "user", "content": q}],
    )
    import json
    return json.loads(r.content[0].text)

# Search with each variant, then merge with RRF
variants = [query] + expand_query(query)
ranked_lists = [search(v) for v in variants]
final = rrf_merge(ranked_lists)   # Reuse Ch 12's RRF
```

### 5.2 Self-RAG — decide whether to search

```python title="self_rag.py" linenums="1" hl_lines="4 16"
def self_rag(query: str) -> str:
    # 1) Decide: does this query need external documents?
    decision = anthropic.messages.create(
        model="claude-haiku-4-5", max_tokens=10,
        system="""Does answering this user's question require searching external documents?
Answer only YES or NO.""",
        messages=[{"role": "user", "content": query}],
    ).content[0].text.strip()

    context = ""
    if decision.startswith("YES"):
        # 2) Retrieve + assess result quality
        retrieved = search(query, k=5)
        context = format_context(retrieved)

        # 3) Self-assess: are these results good enough?
        quality = anthropic.messages.create(
            model="claude-haiku-4-5", max_tokens=10,
            system=f"""Can you answer the question with the search results below?
{context}
YES/NO""",
            messages=[{"role": "user", "content": query}],
        ).content[0].text.strip()
        if quality.startswith("NO"):
            # Fallback: rewrite query, retry, or escalate
            return "Search results aren't sufficient. I'll connect you with a specialist."

    # 4) Generate final answer (with or without context)
    r = anthropic.messages.create(
        model="claude-haiku-4-5", max_tokens=512,
        system=(context or "Answer from general knowledge."),
        messages=[{"role": "user", "content": query}],
    )
    return r.content[0].text
```

**Win**: "Hi" doesn't waste retrieval budget. Incomplete results escalate to a human.

**Cost**: 2–3× more LLM calls. **Adds latency and expense** — gate this carefully, don't use it for every query.

### 5.3 Multi-step / Recursive Retrieval

Complex questions need **first search + follow-up search** cycles:

```
Q: "This year's growth rate vs. last year?"

Step 1: search "last year's revenue" → found $10B
Step 2: search "this year's revenue" → found $13B
Step 3: LLM calculates → 30%
```

Implementation is **Part 5 Agent territory**. Just the concept here.

### 5.4 GraphRAG — concept intro

Microsoft's GraphRAG (2024):

1. **Extract entities and relationships** from documents (LLM-powered)
2. **Store as a knowledge graph** (Neo4j, NetworkX)
3. **At query time, combine graph traversal + vector search**
4. Strong on multi-hop questions ("Who is X's manager's manager?")

**Pros**: great for structural queries.  
**Cons**: **index build cost is 10–100× basic RAG.** Massive LLM calls for entity extraction.

**Recommendation**: only if you have a small domain (thousands of docs), need summaries, or face many multi-hop questions. General FAQ chatbots don't need this.

### 5.5 Agentic RAG — the bridge to Part 5

Agents (Part 5) have **search as a callable tool** and invoke it multiple times:

```
Agent loop:
  1. receive user question
  2. think "what do I need to know?"
  3. call search_policy(query="refund") tool
  4. see results, think "not enough"
  5. call search_database(...)
  6. satisfied → generate final answer
```

Combines Part 2 Ch 8 (Tool Calling) + Part 5 (Agent patterns). Strong for **complex questions** and **multi-domain scenarios**.

---

## 6. Pitfalls — where these break

!!! warning "Pitfall 1. Blindly adding 'Advanced' to everything"
    HyDE and Self-RAG **add LLM calls**. If basic RAG already works, you're paying more for no gain.  
    **Fix**: A/B test with Part 4 evaluation. If gain < 5%, hold off.

!!! warning "Pitfall 2. HyDE hallucinations point you wrong"
    A bad hypothetical answer steers search off course → **wrong final answer**.  
    **Fix**: (a) keep hypothetical answers to 2–3 sentences, (b) search with **both** raw query and HyDE embedding (RRF merge), (c) track hallucination rate.

!!! warning "Pitfall 3. Self-RAG misjudges and hallucinates"
    Model decides "no retrieval needed," then invents an answer (hallucination risk returns).  
    **Fix**: conservative prompt ("if any company context might help, say YES"). Or always search but only evaluate result quality.

!!! warning "Pitfall 4. GraphRAG indexing costs you more than you save"
    100,000 documents → 100,000 LLM calls for entity extraction. Easy six figures in cost.  
    **Fix**: pilot on 1,000 docs to estimate cost; scale gradually. Use a cheap fast model (Haiku).

!!! warning "Pitfall 5. Stacking all techniques at once"
    HyDE + Self-RAG + Rerank + Multi-query = 5–7 LLM calls per query, 3–5 second latency, 10× cost.  
    **Fix**: Add **one at a time**. Measure the actual gain. Kill it if cost > benefit.

---

## 7. Production checklist

- [ ] Advanced techniques chosen via A/B testing on evaluation set (Part 4)
- [ ] Dashboard tracking **LLM calls, cost, latency per query**
- [ ] If using HyDE, **monitor hallucination rate** of fake answers
- [ ] Self-RAG **gate accuracy** (TP/FP of "needs search" decision)
- [ ] GraphRAG index **build and update costs** budgeted separately
- [ ] **Multi-technique sequence documented** (Query rewrite → HyDE → hybrid search → rerank …)
- [ ] Agentic RAG uses Part 5 agent operations guidelines alongside this

---

## 8. Exercises

- [ ] Run §4's `hyde.py`. Compare top-5 results to basic RAG on the same query — measure relevance ratio.
- [ ] Evaluate §5.2 Self-RAG on 10 queries (half need retrieval, half are chitchat) — what's the decision accuracy?
- [ ] Try Query Rewriting on cross-language queries ("refund policy" + Korean documents) — note recall change.
- [ ] Compare HyDE + Rerank vs. Basic + Rerank — latency and quality trade-off?
- [ ] GraphRAG: **document the concept, don't code it yet.** Create a decision tree: is it right for my project?

---

## 9. Sources and further reading

- **HyDE**: Gao et al. (2022), *"Precise Zero-Shot Dense Retrieval without Relevance Labels"*
- **Self-RAG**: Asai et al. (2023), *"Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection"*
- **GraphRAG**: Edge et al., Microsoft (2024), *"From Local to Global: A Graph RAG Approach to Query-Focused Summarization"* · [github.com/microsoft/graphrag](https://github.com/microsoft/graphrag){target=_blank}
- **Agentic RAG**: LangChain, LlamaIndex tutorials
- **Stanford CME 295 Lec 7** — in project `_research/stanford-cme295.md`

---

**Next** → [Ch 14. LangChain in Practice + Multimodal RAG](14-langchain-multimodal.md) :material-arrow-right:  
Assemble RAG pipelines fast with a framework, then unlock **PDF layout and image-based** retrieval.
