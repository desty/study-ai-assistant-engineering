# Why Models

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/en/part1/ch01_why_model.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - The intuition for telling **rule-shaped problems** apart from **model-shaped problems**
    - The **three criteria** OpenAI recommends checking before you reach for an LLM
    - A hands-on demo of where rules silently break — and what a model picks up

---

## 1. A small experiment

Read the five user messages below. Goal: classify each as a **refund request or not**.

| # | Message | Refund? |
|:--:|---|:--:|
| 1 | "I want a refund." | ✅ |
| 2 | "Give me my money back." | ✅ |
| 3 | "This isn't at all what I expected. What should I do?" | ✅ (implicit) |
| 4 | "What is your refund policy?" | ❌ (info request) |
| 5 | "My friend told me they got a refund." | ❌ (just chatter) |

**Question**: can a one-line rule like `if "refund" in message` get all five right?

- 1, 2, 4, and 5 are doable somehow. **#3 isn't** — the word "refund" doesn't appear at all.
- Add more rules to filter out 4 and 5 and you start writing dozens of lines, plus a fresh one every time a new phrasing shows up.

That's the smell of "this should be a model, not rules."

---

## 2. Rules vs. models — the real difference

![Two approaches](../assets/diagrams/rule-vs-model.svg#only-light)
![Two approaches](../assets/diagrams/rule-vs-model-dark.svg#only-dark)

Top: the author has to enumerate every case. Bottom: the model **infers cases it has never seen**.

| | Rules (code) | Model (LLM) |
|---|---|---|
| **Mental model** | "If this condition, then this result" | "Given this context, what's the most likely result" |
| **Strengths** | Predictable · free · fast · auditable | Handles unstructured input · understands new phrasings without training |
| **Weaknesses** | Every new phrasing needs a new rule · maintenance cost grows | Probabilistic · cost · latency · harder to verify |
| **How it fails** | **Silent miss** | **Confident wrong answer** (hallucination) |
| **Debug** | Stack traces, logs | Prompts, examples, eval sets |

---

## 3. Three criteria for reaching for a model

Anthropic and OpenAI's engineering guides converge on the same three triggers. **Hit at least one, and a model is worth considering.** Hit none, and you should write code instead.

<div class="infocards" markdown>

<div class="card" markdown>
#### :material-puzzle: Complex judgment
Decisions that **rules can't fully cover** — exceptions, context-sensitive calls, fuzzy boundaries.

**Examples**: customer-service refund approvals, insurance claim review, anomalous-transaction detection.
</div>

<div class="card" markdown>
#### :material-file-document-alert: Hard-to-maintain rules
A ruleset that's **so large or fragile that updates cost more than they're worth**.

**Examples**: vendor security review checklists with hundreds of lines and dozens of edge cases.
</div>

<div class="card" markdown>
#### :material-text-box-search: Unstructured data
The work fundamentally requires **interpreting natural language** — pulling meaning from documents, holding conversations.

**Examples**: insurance claims, internal knowledge search, customer-support summarization.
</div>

</div>

!!! tip "The bar"
    Just one criterion clearly satisfied → go. None clearly met → stop. A model dropped in for the wrong reasons usually performs **worse than the rules** it replaced.

---

## 4. Where assistants actually pay off

Apply the criteria to real work:

| Scenario | Why a model | Criteria |
|---|---|---|
| User intent classification (refund request vs policy question vs other) | Many phrasings | ③ unstructured |
| Document QA ("which page covers our security policy?") | Document understanding | ③ + ② large ruleset |
| Meeting summary → action items | Context-sensitive | ① + ③ |
| CS email reply drafts | Tone and situation | ① + ③ |
| Ticket routing by content | Many ambiguous cases | ① + ② |

### Where this book starts on the technology ladder

![Technology ladder](../assets/diagrams/tech-ladder.svg#only-light)
![Technology ladder](../assets/diagrams/tech-ladder-dark.svg#only-dark)

Cost and complexity climb left-to-right; so does what you can handle. Skipping straight to "agents" is almost always over-engineering.

---

## 5. Minimal example — watch a rule break

Plain Python, no installs.

```python title="rule_vs_intent.py" linenums="1" hl_lines="5 14"
messages = [
    "I want a refund.",
    "Give me my money back.",
    "This isn't at all what I expected. What should I do?",  # (1)!
    "What is your refund policy?",
    "My friend told me they got a refund.",
]

KEYWORDS = ["refund", "money back", "return"]

def is_refund_request_by_rule(msg: str) -> bool:
    return any(k in msg.lower() for k in KEYWORDS)

for m in messages:
    print(f"[{is_refund_request_by_rule(m)}]  {m}")
```

1. The graveyard of rule-based intent detection. None of the keywords appear — but the meaning is clearly a refund request.

### Output

| # | Result | Message | Verdict |
|:-:|:-:|---|---|
| 1 | `True`  | I want a refund. | ✅ |
| 2 | `True`  | Give me my money back. | ✅ |
| 3 | `False` | This isn't at all what I expected. What should I do? | ❌ **miss** |
| 4 | `True`  | What is your refund policy? | ❌ **false positive** |
| 5 | `True`  | My friend told me they got a refund. | ❌ **false positive** |

One miss and two false positives out of five. Production-unviable.

### The same problem with an LLM (we'll run this for real in Part 2)

```python title="intent_by_llm.py" linenums="1"
from anthropic import Anthropic
client = Anthropic()

SYSTEM = """Decide if the user message is a refund request.
Answer with one word: YES or NO."""

for m in messages:
    r = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=5,
        system=SYSTEM,
        messages=[{"role": "user", "content": m}],
    )
    print(f"[{r.content[0].text.strip()}]  {m}")
```

Expected output:

| # | Result | Message | Note |
|:-:|:-:|---|---|
| 1 | `YES` | I want a refund. | |
| 2 | `YES` | Give me my money back. | |
| 3 | `YES` | This isn't at all what I expected… | **picks up the implicit intent** |
| 4 | `NO`  | What is your refund policy? | distinguishes info request |
| 5 | `NO`  | My friend told me they got a refund. | distinguishes chatter |

The point: **without adding new rules**, the model picks up phrasings you never wrote down.

---

## 6. Hands-on — does my work need a model?

A 30-minute self-diagnostic:

1. Write the problem in **one sentence**: "Given ___, decide ___."
2. Collect **30 input/output examples**, mixed evenly across normal, edge, and ambiguous cases.
3. Write the simplest possible rule — keyword matching, regex, lookup table.
4. How many of the 30 did it get right? Look at the **distribution of mistakes**, not just the average.
5. Bucket the failures:
   - A. "Adding one more rule fixes it" → keep using code
   - B. "There are too many phrasings to enumerate" → **model candidate**
   - C. "Even a human is unsure" → reconsider the problem definition itself
6. If bucket B is **30%+** of failures, a model is worth the cost.

!!! note "Output"
    The output of this diagnostic is the seed of your eval set. Part 4 picks it up.

---

## 7. Common pitfalls

!!! warning "Mistake 1: model first, problem second"
    Reaching for a model "to look smart" turns a 5-line rule into a 200-line system. **If none of the three criteria fire, no model.**

!!! warning "Mistake 2: expecting the model to handle everything"
    Models are **probabilistic**. Same input, different output is allowed. **Never put a model behind anything that needs a deterministic guarantee** — pricing, permissions, payment processing.

!!! warning "Mistake 3: shipping without an eval"
    "The prompt looks good" ≠ "it works in production." Without the eval set from Part 4 you'll be arguing about vibes.

!!! warning "Mistake 4: avoiding the rule + model hybrid"
    Most production systems are **rules + model**. Filter the obvious cases with rules, send only the ambiguous ones to the model. Cheaper, faster, more stable.

---

## 8. Production checklist

- [ ] Monthly review: are we using a model where code would do?
- [ ] Reverse review: are we still using rules where a model would clearly help?
- [ ] Track the **hybrid ratio** — what fraction of inputs is handled by rules vs the model?
- [ ] Quarterly dashboard for model **cost · latency · accuracy**
- [ ] Every new use case must clear the **three-criteria checklist** before it gets a model

---

## 9. Exercises

- [ ] Pick three things in your current work that **rules can't solve cleanly**. For each, mark which of the three criteria applies.
- [ ] Run §5's code. Record the rule's miss and false-positive counts.
- [ ] Add **10 exception rules** to the keyword list. Re-measure accuracy. Where does it stop helping?
- [ ] From your own project, write one paragraph each on: (a) one feature that **does not** need a model, and (b) one feature where a model would clearly beat rules.

---

## 10. At a glance

![Decision flow](../assets/diagrams/decision-flow.svg#only-light)
![Decision flow](../assets/diagrams/decision-flow-dark.svg#only-dark)

---

**Next** → [What is an LLM](02-what-is-llm.md) :material-arrow-right:
If you're reaching for a model, you should know how the thing actually works.
