# Ch 19. Failure Analysis and Debugging

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part4/ch19_failure_analysis.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - Separate failures into a **5-layer taxonomy** — Prompt · Retrieval · Data · Generation · Tool/Flow
    - **Trace-based debugging** that actually reproduces failures — LangSmith · Langfuse
    - A repeatable **debug loop**: failure → classify → fix → prevent regression
    - How to handle **multi-layer failures** that cross boundaries
    - **Part 4 wrap-up** — a 14-week operations routine

!!! quote "Prerequisites"
    [Ch 15](15-what-to-evaluate.md)–[Ch 18](18-reasoning-quality.md). You've got numbers, a Judge, and reasoning strategies. Now you'll systematize **what to fix when something breaks**.

---

## 1. Concept — symptoms vs. causes

"The model hallucinated" is a **symptom**, not a cause. Where did it actually go wrong?

- Prompt wasn't clear enough?
- Search returned the wrong documents?
- The source document itself has a typo?
- Document was fine, but the LLM distorted it?
- Tool returned the right data, but we misinterpreted it?

If you just swap in Sonnet without diagnosing the layer, you **burn money without fixing anything**. Naming the layer unlocks **the actual fix**.

![Failure classification taxonomy](../assets/diagrams/ch19-failure-taxonomy.svg#only-light)
![Failure classification taxonomy](../assets/diagrams/ch19-failure-taxonomy-dark.svg#only-dark)

This chapter's **5-layer taxonomy** is a shared language you'll use throughout the book.

---

## 2. Why you need this

**① Cost of fixes varies wildly.** Rewriting a prompt takes 30 minutes. Adding a reranker takes a week. Cleaning documents takes a month. **Without naming the layer, prioritization breaks down.**

**② Switching models is an expensive shortcut.** Sure, Opus might improve quality by 20%. But if the real problem is retrieval, you've just tripled cost while the actual issue stays broken. Without layer-aware debugging, you'll repeat this mistake forever.

**③ Regression prevention.** Once you've fixed a case, put it in your gold set (Ch 16) so the next refactor doesn't break it again. A debug loop closes the circle — it's how you build durably.

---

## 3. The 5-layer taxonomy — how to classify

| # | Layer | Typical symptom | Typical fix | Ch reference |
|---|---|---|---|---|
| 1 | **Prompt** | Unclear instructions · missing few-shots · format drift | Redesign prompt · add examples | Ch 5 |
| 2 | **Retrieval** | Right answer not in top-k results | Add reranker · try hybrid search · switch embeddings | Ch 12 · 13 |
| 3 | **Data** | Chunk boundaries cut the answer · doc has a typo · missing info | Reset chunking · clean documents | Ch 11 |
| 4 | **Generation** | Docs are there, but answer is mangled · hallucination | Lower temperature · add CoT · add verifier | Ch 5 · 18 |
| 5 | **Tool / Flow** | Wrong arguments to a tool · state transition breaks | Improve tool description · fix ACI · state machine | Ch 8 · Part 5 |

### Diagnostic checklist

1. **Was the right document in the top-k?** → If no, it's Retrieval (2). If yes, continue.
2. **Does the document actually have the answer?** → If no, it's Data (3).
3. **Document is there, answer is still wrong?** → That's Generation (4). Bolster with CoT or a verifier.
4. **Did the reasoning chain call the wrong tool?** → That's Tool/Flow (5).
5. **Passed all checks and still broken?** → Loop back to Prompt (1).

---

## 4. Minimal example — classify one failure

Let's classify a real failure into one of the five layers.

```python title="classify_failure.py" linenums="1" hl_lines="10 19"
from dataclasses import dataclass

@dataclass
class Trace:
    question: str
    retrieved_doc_ids: list[str]
    gold_doc_ids: list[str]
    answer: str
    gold_answer: str

def classify(trace: Trace) -> str:
    # (1)! Check Retrieval first — is the right document in top-k?
    if not set(trace.gold_doc_ids) & set(trace.retrieved_doc_ids):
        return 'retrieval'

    # Data check — is the answer actually in the gold doc? (manual review needed)
    # Skipped here; in practice you'd look up the document

    # (2)! Check Generation — is the answer semantically far from gold?
    sim = similarity(trace.answer, trace.gold_answer)  # embedding cosine
    if sim < 0.6:
        # Doc is right, but answer drifts → suspect Generation
        return 'generation'

    # Prompt/Tool check — format breaks or tool call errors
    if not trace.answer.strip():
        return 'prompt'

    return 'uncertain'  # Needs human review
```

1. **First fork — Retrieval** is fastest to rule out. A set intersection does it.
2. **Second fork — Generation** uses semantic similarity. Below 0.6 = "docs were there, answer still wrong."

This one function **buckets 100 failures into 5 categories** in 5 minutes. That's the seed for your weekly review.

---

## 5. Hands-on — the trace-based debug loop

![Debug Loop](../assets/diagrams/ch19-debug-loop.svg#only-light)
![Debug Loop](../assets/diagrams/ch19-debug-loop-dark.svg#only-dark)

### 5-1. Trace collection — LangSmith / Langfuse

In production, **capture input · retrieval results · the full prompt · output · latency · cost** into a single trace. Without this, debugging is impossible.

```python title="trace_setup.py" linenums="1"
# Example using Langfuse (LangSmith works almost identically)
from langfuse import Langfuse
from langfuse.decorators import observe

lf = Langfuse()

@observe()
def rag_answer(question: str):
    docs = retrieve(question)
    prompt = build_prompt(question, docs)
    answer = generate(prompt)
    return answer, docs
```

One decorator line and every call is automatically recorded. Filter for traces marked as 👎 and move to the next step.

### 5-2. Weekly review routine — 20 case sample

```
Monday:    Pick 20 cases: last week's 👎 + low judge scores (balanced across layers)
Tuesday:   Run classify() for first pass → human confirmation → finalize
Wednesday: Pick the top 1–2 root causes per layer as fix candidates
Thursday:  Apply fixes · re-run evals · check for regression
Friday:    Move fixed cases into gold set · add to next week's regression tests
```

**Run this for just 4 weeks** and your failure distribution shifts. "Huh, retrieval problems are gone now — we're left with generation issues" → you know where to focus next.

### 5-3. Multi-layer failures — when it spans multiple layers

Often one failure touches 2–3 layers. Example: "Search missed two critical documents + prompt doesn't trigger CoT → generation gets confused and hallucinates."

The strategy:

1. **Isolate causes one at a time.** Test whether changing just the prompt to add CoT fixes it. Then test whether search alone would fix it. Don't move both dials at once.
2. **Fix cheapest layer first.** Prompt (30 min) → parameters (2 hours) → retrieval (days) → model swap (last resort).
3. **One axis at a time.** Change two things simultaneously and you can't tell which one worked.

### 5-4. Prevent regression — add to gold set

```python title="add_to_gold.py" linenums="1"
def promote_to_gold(trace, fix_description):
    """Move a fixed failure case into the eval set permanently"""
    entry = {
        'id': f'regr-{trace.id}',
        'question': trace.question,
        'gold_doc_ids': trace.gold_doc_ids,
        'gold_answer': trace.gold_answer_corrected,
        'source': 'production_failure',
        'fix': fix_description,
        'added_at': '2026-04-19',
    }
    append_jsonl(entry, 'evalset/regression.jsonl')
```

**The key**: once you've fixed a case, dump it into `regression.jsonl` so your next CI run validates it automatically. "Same mistake twice" becomes impossible.

---

## 6. Common pitfalls

### 6-1. Swap models to hide symptoms

Opus gets you 70→78% accuracy, and if the real problem is retrieval, **the failure mode stays the same**. You just paid 3x to paper over the problem. Don't upgrade models without layer diagnosis.

### 6-2. Classify nothing, fix everything

"50 failures, I'll just rewrite the prompt" is buckshot. If 40 of those 50 are retrieval failures, prompt work is **0% effective**.

### 6-3. No traces saved

"I can't reproduce it" = no traces. No debugging → wild guesses → hope for quality. Pick one — LangSmith, Langfuse, or your own logs — and **deploy it mandatory**.

### 6-4. Fix once and move on

If a fixed case isn't in the eval set, you'll break it again 3 months later on an unrelated change. Regression set inclusion is the final step that closes the loop.

### 6-5. Fix multiple layers at once

Change prompt + retrieval + model simultaneously → quality goes up, but **you have no idea what worked**. Run A/B splits, one axis at a time.

---

## 7. Production checklist

- [ ] All requests **save traces** (LangSmith/Langfuse/custom)
- [ ] `classify()` runs automatically for first-pass categorization
- [ ] **Weekly 20-case review** is on the team calendar
- [ ] Fixed failures land in **regression.jsonl** and run in CI
- [ ] **Monthly dashboard** shows failure distribution trend across the 5 layers
- [ ] Multi-layer fixes reflect "cheapest layer first" in PR descriptions
- [ ] **Model upgrade decisions** are preceded by layer analysis
- [ ] Failure root causes get **brief write-ups** (Slack/Notion) for org learning

---

## 8. Exercises

### Check your understanding

1. For each of the 5 layers, rewrite **one diagnostic question** in your own words.
2. Give an example where **model swaps help** — and an example where they don't.
3. Explain the "cheapest layer first" principle in terms of cost × impact.
4. What problem repeats if you fix a failure but don't add it to `regression.jsonl`?

### Hands-on

- Collect 20 failures from your prototype → use `classify()` for first pass → organize in a table. Find the top root cause and apply the smallest 30-minute fix you can → re-evaluate.
- Install LangSmith or Langfuse on the mini_rag from Ch 11. Find one trace in the UI and walk through it step-by-step.

### Sources

- **LangSmith / Langfuse official docs** — trace setup guides
- **Stanford CS329A homework** — failure classification tasks · agent debugging routines. See `_research/stanford-cs329a.md`.

---

## 9. Part 4 wrap-up — evaluation · reasoning · debugging cycle

Here's Part 4 in one table:

| Ch | Topic | Key output |
|---|---|---|
| 15 | What to measure | 3 layers (Retrieval·Generation·E2E) + Offline/Online |
| 16 | Build an eval set | 30–100 gold cases · coverage matrix · 20% held out |
| 17 | LLM-as-a-Judge | Pairwise/Rubric + consistency ≥0.85 · human agreement ≥0.8 |
| 18 | Reasoning quality | Self-Consistency · Best-of-N + verifier (test-time compute) |
| 19 | Failure analysis | 5-layer taxonomy · debug loop · regression inclusion |

### You're ready when

1. **30+ gold test cases** are version-controlled and auto-evaluated in CI
2. **Judge design + A/B consistency** is measured
3. You've experimented with **Self-Consistency or Best-of-N** on your own task at least once
4. **Traces are saved and failures classify** automatically
5. **At least one case** sits in `regression.jsonl`

### What's next — Part 5. Agents & LangGraph

With evaluation infrastructure in place, you're ready for **complex workflows**. No more single LLM calls — now you'll build **multi-step reasoning · tool use · state management**. Part 5 unfolds entirely on that foundation.

---

**Next** → [Ch 20. What Is an Agent](../part5/20-what-is-agent.md) :material-arrow-right:  
Now that you can measure and fix single turns, let's build systems that chain multiple LLM calls, use tools, and reason over time.
