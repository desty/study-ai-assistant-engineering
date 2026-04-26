# Ch 17. LLM-as-a-Judge

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/en/part4/ch17_llm_as_judge.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - **Judge design** — pairwise comparison vs. rubric scoring
    - **Four biases** — position · length · self-preference · verbosity
    - **Human calibration** — validating Judge reliability through agreement rates
    - Building a Judge in Claude and measuring bias with A/B flips
    - The mindset: never treat a Judge's verdict as ground truth

!!! quote "Prerequisites"
    [Ch 15](15-what-to-evaluate.md)–[Ch 16](16-evalset.md). You have a gold set, and you need a way to **score how similar** an LLM response is to it.

---

## 1. Concept — Who scores the answer?

You've got correct answers in your gold set. But LLM responses don't spit out **exact character matches**. The meaning is right, but the wording differs. How do you score that?

- **Exact match** — nearly useless. "March 2024" vs "2024/03" fails
- **BLEU/ROUGE** — n-gram overlap. Depends on phrasing luck, not meaning
- **Embedding similarity** — catches the topic, misses factuality
- **Humans** — accurate but slow and expensive

**LLM-as-a-Judge** automates the fourth option. You let a different LLM either pick the better of two answers or assign a 1–5 score.

```
Judge(question, answer_A, answer_B, rubric) → 'A' or 'B' or 'tie'
Judge(question, answer, rubric) → score: 1..5
```

The key: this isn't manufacturing fake ground truth. It's **approximating human judgment**. That's why validating the Judge's reliability is non-negotiable.

---

## 2. Why you need it

- **Scale**: 100 human evaluations take hours. 100 Judge calls take minutes and cost $0.50.
- **Consistency**: humans drift with mood and fatigue. Judge outputs the same result for the same input.
- **Fast iteration**: tweak a prompt line and get the score instantly.

But there are limits. Judges **have stronger biases in certain areas** than humans do, and they **favor their own model family** (§5). So "Judge + periodic human sampling" is the standard pattern.

---

## 3. Where it's used — two modes

### 3.1 Pairwise comparison

"Which of A or B is better?" — single decision, **high consistency**. Best for model and prompt A/B tests.

### 3.2 Rubric scoring

"Rate this answer 1–5 on accuracy · completeness · brevity." Absolute grading. Good for regression tests and time-series tracking.

| Mode | Pros | Cons | When |
|---|---|---|---|
| Pairwise | Aligns with human judgment · simple | O(N²) comparison cost | model · prompt comparison |
| Rubric | O(N) · absolute scores · axis-wise analysis | Judge criteria drift | regression · operational monitoring |

In practice you use **both**. Rubric is your main metric, pairwise is the tiebreaker on important calls.

---

## 4. Minimal example — Claude as a pairwise judge

![Judge workflow](../assets/diagrams/ch17-judge-workflow.svg#only-light)
![Judge workflow](../assets/diagrams/ch17-judge-workflow-dark.svg#only-dark)

```python title="judge_pairwise.py" linenums="1" hl_lines="10 28"
import anthropic
import json

client = anthropic.Anthropic()

JUDGE_PROMPT = """You are an evaluator of customer support chatbot responses in English.

## Evaluation criteria (rubric)
1. Accuracy — grounded in the provided document
2. Completeness — addresses every part of the question
3. Brevity — no unnecessary repetition or verbosity

Read the question, reference document, and two responses. Judge which is better.
Bias warning: ignore position and length. Evaluate content only.

Output must be JSON:
{"winner": "A" | "B" | "tie", "reason": "…", "scores": {"A": {...}, "B": {...}}}
"""

def judge(question, doc, answer_a, answer_b):  # (1)!
    msg = client.messages.create(
        model='claude-haiku-4-5-20251001',  # (2)! Judging is cheap
        max_tokens=400,
        system=JUDGE_PROMPT,
        messages=[{
            'role': 'user',
            'content': f'Question: {question}\n\nDocument:\n{doc}\n\n'
                       f'Answer A:\n{answer_a}\n\nAnswer B:\n{answer_b}',
        }],
    )
    return json.loads(msg.content[0].text)
```

1. **Judge function signature** — takes question, reference doc, two answers, returns a JSON verdict.
2. **Haiku is enough** — judging is a comparative task, so a lightweight model works fine. If agreement drops below ~0.75, upgrade to Sonnet.

---

## 5. Hands-on — measuring and correcting bias

![Judge's four biases](../assets/diagrams/ch17-judge-biases.svg#only-light)
![Judge's four biases](../assets/diagrams/ch17-judge-biases-dark.svg#only-dark)

### 5.1 Position bias — A/B flip test

The most critical check. Run the same A·B pair **in reverse order**, then measure agreement.

```python title="measure_position_bias.py" linenums="1"
def measure_position_bias(samples):
    """samples = [{'q', 'doc', 'a', 'b'}, ...]"""
    agree = 0
    for s in samples:
        r1 = judge(s['q'], s['doc'], s['a'], s['b'])  # A·B order
        r2 = judge(s['q'], s['doc'], s['b'], s['a'])  # B·A order (flipped)

        # Flip r2's winner back to original labels
        inverted = {'A': 'B', 'B': 'A', 'tie': 'tie'}[r2['winner']]

        if r1['winner'] == inverted:
            agree += 1
    rate = agree / len(samples)
    print(f'Position consistency: {rate:.2f}  (target ≥ 0.85)')
    return rate
```

**Below 0.85?** Emphasize "content only, position-blind" in the rubric, or upgrade the Judge model.

### 5.2 Length bias — correlation check

Measure the correlation between response length and Judge score. If r ≥ 0.3, the Judge thinks "longer is better."

```python title="length_correlation.py" linenums="1"
from scipy.stats import pearsonr

def length_vs_score(samples, judge_scores):
    lens = [len(s['answer']) for s in samples]
    r, _ = pearsonr(lens, judge_scores)
    print(f'length~score correlation: {r:.2f}')
    return r
```

**Fix**: add "brevity 1–5" as an explicit axis in the rubric and weight it in the total.

### 5.3 Human calibration — agreement rate

Run a weekly sample (10–20 cases) where **humans independently grade**, then compute alignment with the Judge.

```python title="human_agreement.py" linenums="1"
def agreement(judge_verdicts, human_verdicts):
    """Both are ['A', 'B', 'tie', ...]"""
    match = sum(1 for j, h in zip(judge_verdicts, human_verdicts) if j == h)
    return match / len(human_verdicts)
```

- **≥ 0.80**: Judge scores are safe for offline metrics
- **0.60–0.80**: caution. high-stakes decisions need humans
- **< 0.60**: redesign the Judge. clarify the rubric or swap the model

### 5.4 Self-preference defense

Claude Judges favor Claude answers. Mitigations:

- Use a **different model family** as Judge (e.g., if responses are from Claude, Judge with GPT)
- Or run **dual judges** and escalate disagreements to humans

---

## 6. Common pitfalls

### 6.1 Treating the Judge as ground truth

Mistake: "Judge score went up, so quality improved" in the report. **Without human calibration, the Judge's bias becomes your metric.**

Rule: report Judge scores **alongside agreement rate**. If agreement drops, distrust the Judge result too.

### 6.2 Vague rubrics

"Is the response good? 1–5" breeds bias. Break it into concrete axes:

- Bad: "response quality 1–5"
- Good: "accuracy 1–5, completeness 1–5, brevity 1–5" — separate axes, then average

### 6.3 Same-model Judge

Using `claude-opus` to judge `claude-opus` responses triggers self-preference. If both are Claude in production, **use a two-model ensemble** to offset it.

### 6.4 Judge cost explosion

Eval set of 100 × 20 parameter sweeps = 2000 Judge calls. Sonnet pricing = tens of dollars. **Start with Haiku.** If Haiku agreement ≥ 0.75, stick with it. Below that, upgrade a sample to Sonnet.

---

## 7. Operational checklist

- [ ] Rubric is split into concrete axes (accuracy, completeness, brevity, etc.)
- [ ] **A/B flip consistency ≥ 0.85** is checked before deployment
- [ ] **Weekly human sample (≥10 cases)** tracks Judge agreement rate
- [ ] Judge model is **a different family** from the evaluated model
- [ ] Rubric includes **brevity score** to mitigate length bias
- [ ] **Cost budget** for Judge calls is tracked (model · call count · tokens)
- [ ] **Alert on agreement drop** (Slack, dashboard)
- [ ] Pairwise results are **time-series logged** so you can spot drift

---

## 8. Exercises & next chapter

### Review questions

1. Explain pairwise vs. rubric mode in two scenarios: model A/B selection and operational monitoring.
2. Write the formula to measure position bias and explain why 0.85 is the target.
3. Your Judge's agreement rate came in at 0.55. List three possible causes and how you'd fix each.
4. In two paragraphs, explain why "ship based on Judge score alone" is risky.

### Hands-on

- Take 10 QA pairs from Ch 16's gold set. Generate responses with two prompt versions (baseline · CoT). Run pairwise Judge comparison and measure A/B flip consistency.
- Run the same responses through both Claude and GPT Judges. **Quantify self-preference.**

### Sources

- **Stanford CME 295 Lecture 8** — LLM-as-a-Judge, bias, calibration. See `_research/stanford-cme295.md`
- **MT-Bench / Chatbot Arena** (Zheng et al.) — pairwise judge standard reference
- **Anthropic Building Effective Agents** — eval loop design. See `_research/anthropic-building-effective-agents.md`

---

**Next** → [Ch 18. Reasoning Quality](18-reasoning-quality.md) :material-arrow-right:
Improve the answer itself with CoT, self-consistency, best-of-N, and verifier patterns.
