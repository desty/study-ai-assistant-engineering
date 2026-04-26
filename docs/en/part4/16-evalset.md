# Ch 16. Building Evaluation Sets

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part4/ch16_evalset.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - **Gold sets** (evaluation datasets with correct answers) at **30–100 samples** — building them for real
    - **Representative sampling** — coverage across difficulty and domains
    - **Synthetic vs. human labeling** — when to trust the LLM and when you need people
    - **Operating eval sets** — versioning, hold-out splits, refreshing from production failures
    - Three pitfalls: data leakage, bias in labels, and "only easy questions"

!!! quote "Prerequisites"
    [Ch 15](15-what-to-evaluate.md) — you've picked your metrics (Recall@5, Faithfulness, Helpfulness…). Here you build the **data those metrics will consume**.

---

## 1. Concept — Evaluation is half data

The metrics from Ch 15 (Recall@5, Faithfulness, Helpfulness…) are formulas. To get real numbers, you need **question + answer pairs**. This is called an **evaluation set** or **gold set**.

```
gold set = [(question, gold_doc_ids, gold_answer, metadata)] × N samples
```

The quality of your evaluation can never exceed the quality of this dataset. Even the best Judge or Metric yields only noise on top of a sloppy gold set.

### Why "gold"

**Ground truth data** — answers you've confirmed are correct. Unlike training data, these answers have been reviewed by people and marked "correct." That's why they cost. That's why you can't make many. That's why you need to make them well.

---

## 2. Why you need it — three limits of manual testing

**① Doesn't scale.** Testing 10 questions manually and saying "it works" is meaningless if those 10 don't represent what users actually ask. Running 100 tests automatically becomes a regression test.

**② Not reproducible.** "It answered that question well last week" is recalled bias. A scripted eval set produces the **same number for the same input**, so you can compare week to week.

**③ Biased testing.** The questions developers think of are already questions you solve well. Real users ask **things you never imagined**. Your eval set needs to bridge that gap.

---

## 3. Where to get data — four sources

### 3-1. Production logs (priority one)

If you're already running the system, **real traffic questions** are the best source. The distribution is actually real.

- Risk: PII · sensitive data → **masking required**
- Alternative: internal QA logs, beta user logs

### 3-2. Reverse-generate from documents

Give documents to an LLM: "Create 3 questions this document can answer" — synthetic. **Fast but distribution differs from real use.**

### 3-3. Domain expert brainstorming

Ask the ops team, CS team: "What do users ask about a lot?" Labor-intensive but **great for finding edge cases**.

### 3-4. Public benchmarks (supplementary)

MMLU, TriviaQA, KoBEST, etc. Rarely matches your domain exactly, so use **only for warm-up**.

!!! tip "Recommended mix"
    60% production logs + 30% expert brainstorming + 10% synthetic/public. Early on without production data, lean synthetic, **but swap to real logs the moment you deploy**.

---

## 4. Minimal example — start with 10 QA pairs

Looks hard, but **start with 10**. Waiting for a perfect 100 gives you zero.

```python title="build_evalset_v1.py" linenums="1" hl_lines="6 20"
import json
from pathlib import Path

# (1)! First 10 samples — write by hand. Question + gold doc IDs + model answer
SEED = [
    {
        'id': 'q001',
        'question': 'What is your refund policy?',
        'gold_doc_ids': ['doc-refund-01'],
        'gold_answer': 'Refunds are available within 7 days of purchase for unused items. See My Account > Refund Request for details.',
        'difficulty': 'easy',
        'domain': 'policy',
    },
    # ... nine more samples in the same format
]

def save_evalset(items, path='evalset/qa_v1.jsonl'):  # (2)!
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

save_evalset(SEED)
```

1. **Five minimum fields** — id, question, gold_doc_ids (for retrieval eval), gold_answer (for generation eval), difficulty/domain (for sampling and analysis). Add more later.
2. **JSONL format** — one line per sample. Diffs are clear in git, and you can stream-process it.

With just these 10, the `recall@k` script from Ch 15 **runs**. Add more incrementally.

---

## 5. Hands-on — operating a 100-sample gold set

![Evalset pipeline](../assets/diagrams/ch16-evalset-pipeline.svg#only-light)
![Evalset pipeline](../assets/diagrams/ch16-evalset-pipeline-dark.svg#only-dark)

### 5-1. Design the coverage matrix first

Collecting 100 samples randomly biases you toward certain areas. **Plan upfront how many of each type you need.**

![Difficulty × domain coverage](../assets/diagrams/ch16-coverage-matrix.svg#only-light)
![Difficulty × domain coverage](../assets/diagrams/ch16-coverage-matrix-dark.svg#only-dark)

Fill in target counts on a difficulty × domain grid first. Cells left blank become targets you consciously hunt for.

### 5-2. Sampling — stratified

Random pulls from production logs skew toward easy questions. Use **stratified sampling** instead.

```python title="sample_stratified.py" linenums="1"
import random
from collections import defaultdict

def stratified_sample(logs, matrix):
    """logs = [{'question', 'difficulty', 'domain'}, ...]
       matrix = {('easy','faq'): 10, ('hard','numeric'): 16, ...}
    """
    buckets = defaultdict(list)
    for log in logs:
        key = (log['difficulty'], log['domain'])
        buckets[key].append(log)

    sampled = []
    for key, target in matrix.items():
        pool = buckets.get(key, [])
        if len(pool) < target:
            print(f'⚠ {key}: pool shortage ({len(pool)}/{target}) — need synthetic or brainstorm')
        sampled.extend(random.sample(pool, min(target, len(pool))))
    return sampled
```

Fill gaps with synthesis (§3-2) or brainstorming.

### 5-3. Labeling — hybrid human + LLM

**LLM draft → human review** gives you the best quality-to-cost ratio.

| Stage | Who | What |
|---|---|---|
| 1. Draft | LLM (Claude Haiku) | Generate gold_answer candidate from documents |
| 2. Review | Domain owner | Verify factuality, completeness, edit if needed |
| 3. Second pass | Different person | Double-check 10–20% sample |
| 4. Approve | PM / Tech Lead | Final merge |

**Write a labeling guide** — one page. If different people use different standards for "correct answer," your numbers will bounce around.

### 5-4. Hold-out split

Set aside **20–30%** of your eval set (hold-out).

- Regular evalset: runs every prompt change → overfits
- Hold-out: runs once a quarter → **true signal**

A big gap between them signals you're overfitting to the eval set.

### 5-5. Versioning

```
evalset/
  qa_v1.jsonl          # first draft, 10 samples
  qa_v2.jsonl          # expanded to 30
  qa_v3.jsonl          # 100 samples, matrix balanced
  qa_holdout.jsonl     # hold-out 30 samples (separate)
  CHANGELOG.md         # what changed and why
  labeling_guide.md
```

Git works fine (JSONL is diff-friendly). For larger sets, use DVC.

---

## 6. Common pitfalls

### 6-1. Evaluation set leakage

Most common and most destructive. Symptom: "score goes up with every prompt change, but user feedback plateaus."

Cause: you see an eval-set failure → tune the prompt to fix it → **overfit to the eval set only**.

Fix: **don't peek at hold-out**. CI runs on the regular set, quarterly reviews use hold-out only.

### 6-2. Biased labels

If different labelers use different standards for "correct," gold itself is shaky.

- Summarization: "Is short better or long better?"
- Generation: "Where does hallucination begin?"

Mitigate with **labeling guide + 10–20% double-check**.

### 6-3. The "only easy questions" trap

Developers naturally avoid questions that fail. Result: the eval set becomes a list of things you're already good at. Harder questions fail in production.

Defense: **require ≥30% hard** in your coverage matrix. **Auto-collect questions that get 👎 feedback**.

### 6-4. Build once and stop

"The eval set from last year" is a museum piece. Domains, users, and models all changed but the numbers stayed. **Refresh quarterly** — add new samples from production logs, retire old ones.

---

## 7. Production checklist

- [ ] You have at least 30 (QA) · 30 (summarization) · 100 (classification) initial gold samples
- [ ] **Coverage matrix** visualizes difficulty and domain balance
- [ ] **Labeling guide** (1–2 pages) is written and shared with the team
- [ ] **Hold-out 20–30%** is in a separate file and **does not run in CI**
- [ ] `evalset/CHANGELOG.md` logs "when, why, how many" for each update
- [ ] **Quarterly sampling cycle** from production logs is established
- [ ] **PII masking policy** covers names, phone, address, card numbers
- [ ] **Negative feedback (👎) auto-enters** the sampling pool

---

## 8. Exercises

### Check your understanding

1. Pick your domain (e-commerce, healthcare, HR, etc) and fill a 3×4 coverage matrix. Write target counts in each cell.
2. Name **three warning signs** of evaluation set leakage.
3. Why is **LLM draft + human review better** than pure human labeling?
4. Why enforce **"≥30% hard"** in your coverage matrix?

### Hands-on

- Build a **10-sample QA gold set** for your prototype and run the `recall_at_k` script from [Ch 15](15-what-to-evaluate.md) §4. Record the first number.
- Use Haiku to draft `gold_answer` for the same 10 samples and compare to your hand-written versions. How different are they?

### Sources

- **Stanford CS329A HW** — Agent evaluation set construction guide. See `_research/stanford-cs329a.md`.
- **Ragas documentation** — `testset generation` module (synthetic test sets).
- **Anthropic Building Effective Agents** — evaluation data collection patterns. See `_research/anthropic-building-effective-agents.md`.

---

**Next** → [Ch 17. LLM-as-a-Judge](17-llm-as-judge.md) :material-arrow-right:
You have gold samples. Now, **who scores whether the output matches?** The answer isn't always a human.
