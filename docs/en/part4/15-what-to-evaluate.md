# Ch 15. What to Evaluate

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part4/ch15_what_to_evaluate.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - **AI systems without evaluation are unreliable** — why you need numbers, not hunches
    - **Three layers of evaluation** — Retrieval · Generation · End-to-End
    - **Offline (pre-deployment) vs. Online (post-deployment)** — the same metric means different things at each stage
    - A metric catalog — which signal matters when
    - Common traps: single-metric obsession, "bigger models are always better," and test set leakage

!!! quote "Prerequisites"
    Part 2 ([Ch 4](../part2/04-api-start.md)–[Ch 8](../part2/08-tool-calling.md)) and Part 3 ([Ch 9](../part3/09-why-rag.md)–[Ch 14](../part3/14-langchain-multimodal.md)). You've assembled a prototype RAG or tool-calling system.

---

## 1. Concept — The "it works" illusion

You ship a chatbot. A user asks "what's the refund policy?" and gets a plausible answer. You try three more times. All plausible. **Let's deploy.**

That's the trap. LLM outputs are **probabilistic** and **sensitive to input**. Manual testing on a handful of examples hides the real questions:

- Does hallucination only hit certain question types?
- Is the retriever pulling the wrong doc, and the LLM is just papering over it?
- Are dates and numbers subtly wrong?
- Did you tweak the prompt once and break something else without noticing?

**Evaluation** is the process of turning these unknowns into **repeatable numbers**. It's your test suite. It's your A/B experiment. Without it, your system stays in "got lucky" mode forever.

---

## 2. Why it matters — Three concrete reasons

**① Catching regressions.** Every time you change a prompt line, swap model versions, or tweak a retriever parameter, you need to know if you broke something that used to work. Manual testing: hard to do 10 cases. An eval script: 100 cases in 30 seconds.

**② Making decisions.** "Should we use Haiku instead of Sonnet?" "Does adding a reranker help?" Without numbers, it's all gut feel. With Recall@5 jumping from 0.62 to 0.81, the choice is clear.

**③ Building trust.** In enterprise settings, legal, security, and operations teams will ask: "How often does this get it wrong?" You need to say `Faithfulness: 0.93`. "It works pretty well" doesn't close the conversation.

---

## 3. Where evaluation fits — Three layers

![Three layers of evaluation](../assets/diagrams/ch15-eval-3layers.svg#only-light)
![Three layers of evaluation](../assets/diagrams/ch15-eval-3layers-dark.svg#only-dark)

A RAG system has at least two blocks: search and generation. The user's experience is the sum of both. So you measure at three points in time.

### 3-1. Retrieval layer — Did we pull the right documents?

This happens before the LLM. Question → top-k docs. That's it.

| Metric | Meaning | When to use |
|---|---|---|
| **Recall@k** | Fraction of questions where the gold doc is in top-k | Measure search coverage |
| **Precision@k** | Fraction of top-k results that are actually relevant | When top-k is too broad |
| **MRR** (Mean Reciprocal Rank) | Average rank position of the right answer | When position matters — is it #1 or buried? |
| **nDCG** | Ranking score weighted by relevance | When relevance is a spectrum (highly, somewhat) |

### 3-2. Generation layer — Did we build the right answer from those docs?

**Fix** the retrieval results (assume they're correct). Now measure only: does the LLM output match the documents?

| Metric | Meaning | When to use |
|---|---|---|
| **Faithfulness** | Fraction of answer supported by the provided docs | Catch hallucination (the whole point of RAG) |
| **Correctness** | Semantic match to the ground truth | When there's a clear right answer (QA) |
| **Coherence** | Logical flow and readability | For summaries and long-form responses |
| **Groundedness** | Strict version of Faithfulness — sentence-level accuracy | Medical, legal, high-stakes domains |

### 3-3. End-to-End layer — Did the user actually get what they needed?

Run the whole pipeline once. Score only the final output.

| Metric | Meaning | When to use |
|---|---|---|
| **Helpfulness** | Usefulness (human score or LLM judge) | Most common E2E metric |
| **Task Success** | Did the user's goal actually get accomplished | Agents and multi-step workflows |
| **Safety** | Absence of harmful, discriminatory, or refusal failures | Operational necessity |
| **User Feedback** | Thumbs up/down, re-queries, abandonment | Online signals |

!!! tip "Why three layers?"
    If only E2E is low, you don't know where to fix. But if Retrieval scores 0.85, Generation scores 0.80, and E2E is 0.40, you've just learned: **fix the prompt**. If Retrieval is 0.30 but the others are fine, **add a reranker**. Layered metrics tell you **where to dig**.

---

## 4. Minimal example — Recall@k in 30 lines

First, the intuition: evaluation isn't complex. Let's run a retrieval eval in a single script.

```python title="eval_retrieval.py" linenums="1" hl_lines="14 23"
import chromadb
from openai import OpenAI

oai = OpenAI()
client = chromadb.PersistentClient(path='./chroma')
col = client.get_collection('docs')

# (1)! Eval set: questions paired with gold doc IDs
dataset = [
    ('What is the refund policy?', 'doc-refund-01'),
    ('How many days for shipping?', 'doc-shipping-02'),
    ('How do I apply a coupon?', 'doc-coupon-03'),
]

def embed(text):
    return oai.embeddings.create(
        model='text-embedding-3-small', input=text
    ).data[0].embedding

def recall_at_k(k=5):  # (2)!
    hits = 0
    for q, gold_id in dataset:
        res = col.query(query_embeddings=[embed(q)], n_results=k)
        retrieved_ids = res['ids'][0]
        if gold_id in retrieved_ids:
            hits += 1
    return hits / len(dataset)

print(f'Recall@5 = {recall_at_k(5):.2f}')
print(f'Recall@3 = {recall_at_k(3):.2f}')
```

1. **Gold set** — question + correct doc ID pairs. Start with 3; grow to 30–100 in Ch 16.
2. **recall@k** — "is the right doc anywhere in the top-k?" Binary. For ranked position, use MRR instead.

That's all. One 3-line eval function. You just converted "does my retriever work?" into a **number** that changes when you modify embeddings, chunking, or retrieval parameters.

---

## 5. In practice — Offline vs. Online

![Offline vs. Online](../assets/diagrams/ch15-offline-vs-online.svg#only-light)
![Offline vs. Online](../assets/diagrams/ch15-offline-vs-online-dark.svg#only-dark)

Evaluation has **two axes**. Do only one and you'll find a blind spot.

### 5-1. Offline — Before deployment, fixed data

**When**: Every time you change a prompt, model, or parameter. Ideally in CI/CD, blocking bad merges.

**Data**: A **versioned gold set** (Chapter 16 in detail). Don't change it mid-experiment or comparisons break.

```python title="offline_ci.py" linenums="1"
# Minimal CI skeleton
THRESHOLDS = {
    'recall@5': 0.80,
    'faithfulness': 0.85,
}

def run_eval():
    scores = {
        'recall@5': evaluate_retrieval(gold_set),
        'faithfulness': evaluate_faithfulness(gold_set),
    }
    for name, score in scores.items():
        assert score >= THRESHOLDS[name], f'{name} regressed: {score:.2f}'
    return scores

if __name__ == '__main__':
    print(run_eval())
```

**Upsides**: reproducible, fast, cheap. Once written, you run it hundreds of times.  
**Blindspots**: doesn't measure real-world cases outside your test set.

### 5-2. Online — After deployment, real users

**When**: Canary (5% traffic) · A/B tests · continuous monitoring.

**Data**: User logs and feedback. Sample from the live stream.

| Signal | Meaning |
|---|---|
| 👍/👎 | Intuitive but low response rates (5–15%) |
| Re-query rate | User asks a follow-up immediately — lower is better |
| Session length | Number of turns to solve a task (for agents) |
| Abandonment | User leaves mid-response |
| Manual review samples | Daily: sample 100 cases, humans rate on a 3-point scale |

**Upsides**: real usage · catches long-term trends.  
**Blindspots**: noisy, hard to isolate cause, feedback lag.

### 5-3. Close the loop: offline and online are partners

Failed cases found online get **added to your offline gold set**. This is the Ch 16 operating loop.

```
Real user logs → Sample failures → Label → Update gold set → Next offline eval round
```

---

## 6. Common failure modes

### 6-1. Obsession with a single metric

"Look, our Faithfulness is 0.91!" But Recall@5 is 0.30. Meaning: the LLM is **faithfully answering the wrong document**. Every layer needs at least one metric.

### 6-2. "Bigger model = better"

Sonnet sometimes scores **lower** Faithfulness than Haiku. Larger models are more confident at inference, filling gaps with plausible-sounding reasoning instead of admitting uncertainty. You'll swap Sonnet for Haiku and get better results. Evaluation reveals this. Guessing doesn't.

### 6-3. Test set leakage

You tweak the prompt bit by bit. Over time, it's not the model that's overfit — **you are**, to your eval set. Fix: hold out a **separate set** (30–50 unseen examples) and score against that at the end.

### 6-4. Deploy on offline scores alone

Your offline eval hit 0.92. Users ask different questions. Deploy to canary (5% traffic) and **monitor for at least 3 days**. If offline and online metrics diverge, that's a signal.

---

## 7. Operational checklist

- [ ] **Picked at least one metric per layer** (Retrieval · Generation · E2E)
- [ ] Gold set is **versioned** (git/DVC) and labeling guidelines are documented
- [ ] Eval script **runs in CI** and blocks merges on threshold violations
- [ ] Online dashboard exists (Grafana, Langfuse) **before canary launch**
- [ ] Failure case loop is live: 👎 or low judge scores → weekly review → gold set refresh
- [ ] **LLM judge API cost** is in budget (it's not cheap if you score thousands daily)
- [ ] **Hold-out set exists** (defend against eval set overfitting)
- [ ] New features include "how we evaluate this" in the PR description

---

## 8. Exercises and next steps

### Review

1. For each of the three layers (Retrieval, Generation, E2E), pick one metric and explain in one sentence why you chose it.
2. Your E2E score is low, but Retrieval and Generation scores are fine. Where's the bug?
3. Offline scores are stable, but online metrics dropped. Give three hypotheses.
4. Why is a single metric (e.g., Faithfulness alone) dangerous? Use a concrete example.

### Hands-on

- **Take the QA prompt from [Ch 5](../part2/05-prompt-cot.md).** Pick 10 questions, hand-label gold answers, then score `correctness` using Claude Haiku as judge. Modify the prompt once and log the score change.

### Further reading

- **Stanford CS329A Lec 17** — Agentic Evaluations · Long-Horizon Tasks. See project `_research/stanford-cs329a.md`
- **Stanford CME 295 Lec 8** — Evaluation & LLM-as-a-Judge. See project `_research/stanford-cme295.md`
- Ragas official metric catalog (faithfulness · answer_relevancy · context_precision)

---

**Next** → [Ch 16. Building Eval Sets](16-evalset.md) — How to actually construct and maintain 30–100 gold examples in practice :material-arrow-right:
