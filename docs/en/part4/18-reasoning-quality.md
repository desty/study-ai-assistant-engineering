# Ch 18. Lifting Reasoning Quality

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part4/ch18_reasoning_quality.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - **Four ways to improve reasoning quality** by changing your strategy — same model, different approach
    - **CoT variants · Self-Consistency · Best-of-N · Verifiers** — each fits a different problem
    - **Test-time compute** — trade money for quality at inference time
    - Building Self-Consistency on math problems and Best-of-N + pytest on code
    - The three bottlenecks that hit as you grow N: cost, latency, and verifier quality

!!! quote "Prerequisites"
    [Ch 15](15-what-to-evaluate.md)–[Ch 17](17-llm-as-judge.md). You've got evaluation metrics and a Judge. Now you'll focus on **lifting the quality of answers themselves** instead of just measuring them.

---

## 1. Concept — don't ask once, ask better multiple times

Ask an LLM the same question five times and you'll get five different answers. That **randomness** isn't a bug—it's your biggest asset. This chapter is about turning it into a feature.

![Four reasoning techniques](../assets/diagrams/ch18-reasoning-4methods.svg#only-light)
![Four reasoning techniques](../assets/diagrams/ch18-reasoning-4methods-dark.svg#only-dark)

Four strategies at a glance:

| Technique | Idea | Key advantage |
|---|---|---|
| ① Single | One direct answer | Fast and cheap |
| ② **CoT** | "Think step by step" → reveal reasoning trace | Just need more tokens |
| ③ **Self-Consistency** | N samples → majority vote | Strong on math and multiple choice |
| ④ **Best-of-N + Verifier** | N candidates → verifier picks the best | Unbeatable on code and checkable tasks |

All four rest on the same principle: **test-time compute** — freeze the model weights and spend more **inference time** to buy quality.

---

## 2. Why you need this

**① When you can't swap the model.** You need 70% → 85% accuracy but don't have budget for Claude Opus. Inference strategy can bridge that gap.

**② When the domain doesn't forgive mistakes.** Math, code, money calculations fail catastrophically once. N+5 majority vote or verification raises your floor.

**③ When you already have a Judge setup.** The Judge from [Ch 17](17-llm-as-judge.md) becomes a verifier. You're reusing what works.

**Trade-off**: cost and latency both multiply by N. We'll address that in §6.

---

## 3. Where each technique shines — domain by domain

### 3-1. CoT variants

- **Math and logic**: Just saying "think step by step" lifts accuracy by 20–40 percentage points (Wei 2022)
- **Complex classification**: Writing out your reasoning catches shallow pattern-matching errors
- **Limits**: Wrong reasoning can sound plausible. (Ch 19 covers failure modes.)

### 3-2. Self-Consistency

- **Discrete answers only**: numbers, categories, multiple choice
- **How it works**: Sample many CoT paths → extract final answer from each → take the majority vote
- **Not for**: summaries or freeform writing (you can't vote on continuous answers)

### 3-3. Best-of-N + Verifier

- **Verifiable tasks**: code (run it), SQL (execute on DB), math (substitute back)
- **How it works**: Generate N candidates → verifier scores or passes each → pick the highest
- **Verifier types**:
    - **Deterministic**: pytest, SQL execution, regex
    - **LLM-as-verifier**: Reuse your Judge (rubric-based)
    - **Reward model**: Learned scorer (research-grade)

### 3-4. Tree of Thoughts (concept only)

Branch search as a tree. More complex to build, higher cost. This book mentions it for context; see Yao et al. 2023 if you're curious.

---

## 4. Minimal example — Self-Consistency on a math problem

```python title="self_consistency.py" linenums="1" hl_lines="11 25"
import anthropic
from collections import Counter
import re

client = anthropic.Anthropic()

COT_SYS = """Solve the problem step by step. On the last line, write your final answer in this exact format:
ANSWER: <number only>"""

def sample_one(question, temperature=0.7):  # (1)!
    msg = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=500,
        system=COT_SYS,
        messages=[{'role': 'user', 'content': question}],
        # Anthropic SDK: temperature parameter
    )
    text = msg.content[0].text
    m = re.search(r'ANSWER:\s*([-\d.]+)', text)
    return m.group(1) if m else None

def self_consistency(question, n=5):  # (2)!
    answers = [sample_one(question) for _ in range(n)]
    answers = [a for a in answers if a is not None]
    if not answers:
        return None, 0
    most_common, cnt = Counter(answers).most_common(1)[0]
    return most_common, cnt / n  # answer + confidence (agreement rate)

q = 'A box has 24 apples. Three people split them equally. How many apples per person?'
ans, conf = self_consistency(q, n=5)
print(f'Answer: {ans}, Confidence: {conf:.0%}')
```

1. **Single sampler** — high temperature for diversity. CoT system prompt coaxes the model to reason aloud.
2. **Majority vote** — return the most common answer and its agreement rate. 100% match = very confident. 40% = caution.

**Use the confidence score**: trust only 0.8+, escalate lower ones to a human or different model.

---

## 5. Production tutorial — Best-of-N + pytest verifier on code

Adding a **deterministic verifier** (pytest) to code generation transforms your results.

### 5-1. Flow

```
Q: "Write a function add(a,b) that returns the sum"
  ↓
N=5 generations (temperature=0.8)
  ↓
Test each candidate in a sandbox
  ↓
Return first passing candidate (or use Judge for best)
```

### 5-2. Code

```python title="best_of_n_code.py" linenums="1" hl_lines="12 32"
import subprocess, tempfile, os, textwrap
import anthropic

client = anthropic.Anthropic()

def generate_candidates(prompt, n=5):
    results = []
    for _ in range(n):
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=400,
            messages=[{'role': 'user', 'content': prompt}],
        )
        results.append(msg.content[0].text)
    return results

TEST_CODE = """
def test_add():
    from solution import add
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
"""

def verify(code):  # (1)!
    with tempfile.TemporaryDirectory() as td:
        with open(f'{td}/solution.py', 'w') as f:
            f.write(code)
        with open(f'{td}/test_solution.py', 'w') as f:
            f.write(TEST_CODE)
        r = subprocess.run(
            ['pytest', '-q', td], capture_output=True, text=True, timeout=15
        )
        return r.returncode == 0

def best_of_n(prompt, n=5):  # (2)!
    for i, cand in enumerate(generate_candidates(prompt, n)):
        code = extract_python(cand)  # extract code block
        if verify(code):
            return code, i  # return first pass
    return None, -1
```

1. **Verifier** — pytest gives a deterministic pass/fail. No LLM guessing involved.
2. **Best-of-N loop** — return on first pass (early exit). If all fail, return None.

### 5-3. Expected results

- N=1: ~60% accuracy
- N=5 + verifier: **90%+**  
Cost scales to ~2–3× on average (early exit saves us from hitting the full 5×).

![Cost vs Quality](../assets/diagrams/ch18-cost-vs-quality.svg#only-light)
![Cost vs Quality](../assets/diagrams/ch18-cost-vs-quality-dark.svg#only-dark)

---

## 6. Gotchas

### 6-1. Tokens and cost multiply by N

Self-Consistency with N=5 = 5× cost · 5× latency (if you don't parallelize). **Measure the quality gain on your eval set first.** Does the improvement justify the spend?

### 6-2. Verifier becomes the ceiling

Best-of-N can never exceed your verifier's quality. If your LLM Judge agrees only 70% of the time, there's a hard cap. Calibration from [Ch 17](17-llm-as-judge.md) is essential.

### 6-3. Not enough diversity

If temperature is 0.3 and you run N=20, you'll get 20 near-identical answers. Pointless. **Self-Consistency needs temperature ≥ 0.7.**

### 6-4. Self-Consistency on continuous outputs

Majority vote doesn't work for "write a summary." For continuous outputs, use **Judge-based Best-of-N** (pick the best, don't vote).

### 6-5. Early stopping trap

Returning on first pass keeps latency low and cost proportional, but quality is identical. For **maximum quality**, generate all N and pick the best with a Judge. Choose based on your goal.

---

## 7. Operations checklist

- [ ] Specified which **task types** get Self-Consistency vs Best-of-N (math, code, classification only)
- [ ] Decided N by **measuring on your eval set** (don't defaultN=5 by habit)
- [ ] Confirmed verifier is **deterministic (pytest, regex)** or LLM-based with tracked agreement rate
- [ ] Verified token and latency costs **×N** fit your SLO
- [ ] Parallelized if possible (N=5 parallel = 1× latency; N=5 serial = 5× latency)
- [ ] Logging **Self-Consistency confidence** (agreement %) for auto-escalation of low cases
- [ ] Measured early-stopping impact on quality
- [ ] Periodically compared **smaller model + inference strategy** vs **larger model alone**

---

## 8. Exercises & next

### Check your understanding

1. Why is Self-Consistency incompatible with summaries? What's the Best-of-N + Judge alternative and why does it work?
2. Name two extra risks when your verifier is an LLM Judge (see [Ch 17](17-llm-as-judge.md)).
3. Write a formula comparing N=1 (Single) vs N=5 (Self-Consistency) on cost, latency, and quality.
4. When does upgrading the model beat increasing test-time compute?

### Hands-on

- Compare Haiku alone vs Haiku + Self-Consistency (N=5) on 10 GSM8K math problems. Record accuracy for each.
- Implement Best-of-N + pytest on 10 LeetCode Easy problems. Record accuracy at N=1, N=3, N=5.

### Sources

- **Wei et al. 2022** — Chain-of-Thought Prompting
- **Wang et al. 2022** — Self-Consistency
- **Cobbe et al. 2021** — Verifier and reward models
- **Stanford CS329A Lec 2–3** — Test-time compute, Archon, "Let's Verify Step by Step". See project `_research/stanford-cs329a.md`

---

**Next** → [Ch 19. Failure Analysis and Debugging](19-failure-analysis.md) — now that you have numbers, it's time to figure out **why they went wrong** and separate causes by layer :material-arrow-right:
