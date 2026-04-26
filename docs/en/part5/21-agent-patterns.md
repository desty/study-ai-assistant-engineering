# Ch 21. Seven Agent Patterns

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/en/part5/ch21_agent_patterns.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - **Anthropic's five workflow patterns** — Prompt Chaining · Routing · Parallelization · Orchestrator-Workers · Evaluator-Optimizer
    - **OpenAI's two agent patterns** — Single-Agent · Multi-Agent
    - **Pattern decision tree** — top-down questions to pick the right pattern for your situation
    - **5–15 line minimal snippets** for each pattern
    - Why "memorizing pattern names" is a trap — baseline is always a single LLM + RAG

!!! quote "Prerequisites"
    [Ch 20](20-what-is-agent.md) — the boundary between apps and agents, and the five essential elements of a loop. This chapter is a catalog: "if you need a loop, how do you build it?"

---

## 1. Concept — Patterns are vocabulary

When you talk about agents and workflows, you need **shared vocabulary** or design discussions fall apart.

- "We'll call the LLM multiple times…" → How many? Sequentially? In parallel? Who decides?
- "Let's use an agent" → Single? Multi? Manager? Decentralized?

**Anthropic's "Building Effective Agents"** (2024) organizes this into 5+2:

| Category | Pattern | Source | Decision maker |
|---|---|---|---|
| **Workflow** (deterministic) | ① Prompt Chaining | Anthropic | Developer |
| | ② Routing | Anthropic | Developer |
| | ③ Parallelization | Anthropic | Developer |
| | ④ Orchestrator-Workers | Anthropic | Developer (+LLM sub-decisions) |
| | ⑤ Evaluator-Optimizer | Anthropic | Developer |
| **Agent** (autonomous) | ⑥ Single-Agent | OpenAI/Anthropic | LLM |
| | ⑦ Multi-Agent | OpenAI | LLM × N |

The key difference: **workflows hard-code the path** while **agents let the LLM decide**. It's a spectrum of how "agentic" you want to go (see Ch 20).

---

## 2. Why patterns matter — what happens without them

If you stitch together "call the LLM, look at the result, call something else" **ad-hoc**, you end up with:

- Deeply nested `if` statements with special cases in each branch
- Missed opportunities for parallelism (always sequential)
- Inconsistent retry logic — unclear where to restart on failure
- Teammates asking "why's it structured this way?" and you can't explain

With a pattern name:

- "That's **routing + orchestrator-workers**" → understood in five seconds
- Each pattern has **matching failure strategies and eval approaches** (Ch 19)
- Your code becomes predictable → handoffs and maintenance improve

---

## 3. Seven patterns at a glance

![Seven patterns](../assets/diagrams/ch21-seven-patterns.svg#only-light)
![Seven patterns](../assets/diagrams/ch21-seven-patterns-dark.svg#only-dark)

One line each:

### ⓪ Baseline — single LLM + RAG

Try this **before** adding patterns. Part 3 covers most of it.

### ① Prompt Chaining — LLM → LLM → LLM

One output feeds the next input. **Step-by-step transformations** like outline → draft → polish. Simple and powerful.

### ② Routing — Classifier → specialist LLM

Classify the input type, then **route to the right handler**. FAQ, refunds, and bug reports each get their own prompt.

### ③ Parallelization — N calls concurrently

Run independent tasks **in parallel**, then **merge** (voting, weighted average). Part 4's Self-Consistency is an example of this pattern.

### ④ Orchestrator-Workers — Planner → Worker × N

A top-level LLM **breaks work down and assigns it**. Sub-workers execute their tasks. Common for complex research or multi-step coding.

### ⑤ Evaluator-Optimizer — Gen ↔ Critic loop

Generate → evaluate → **regenerate**. Repeat until quality converges. Works for translation, code polish, writing.

### ⑥ Single Agent — LLM + Tools loop

The basic agent from Ch 20. One LLM **drives the loop**. Good for customer support, data exploration.

### ⑦ Multi-Agent — Manager / Decentralized

Multiple agents split roles. Covered in detail in Ch 25.

---

## 4. Minimal examples — 5–15 lines

The smallest viable code for each pattern. Real code adds error handling and tracing, but this shows the **structure**.

### 4.1 Prompt Chaining

```python title="chaining.py" linenums="1"
def outline(topic):   return call('Create a 5-bullet outline: ' + topic)
def draft(outline):   return call('Write a draft from this outline:\n' + outline)
def polish(draft):    return call('Refine sentences and cut length in half:\n' + draft)

result = polish(draft(outline('Report writing guide')))
```

### 4.2 Routing

```python title="routing.py" linenums="1"
def router(q):
    cat = call(f'Classify as: faq / refund / bug\nQuestion: {q}\nOutput one word only').strip()
    return {'faq': faq_handler, 'refund': refund_handler, 'bug': bug_handler}[cat](q)
```

### 4.3 Parallelization

```python title="parallel.py" linenums="1"
from concurrent.futures import ThreadPoolExecutor

def multi_review(text):
    prompts = ['grammar and awkward phrasing', 'factual accuracy', 'logical flow']
    with ThreadPoolExecutor() as ex:
        reviews = list(ex.map(lambda p: call(f'Review for {p}:\n{text}'), prompts))
    return call(f'Synthesize these 3 reviews:\n' + '\n---\n'.join(reviews))
```

### 4.4 Orchestrator-Workers

```python title="orchestrator.py" linenums="1"
def orchestrate(task):
    plan = call(f'Break this into 3 subtasks as a JSON list: {task}')
    subtasks = json.loads(plan)
    results = [call(f'Execute subtask: {st}') for st in subtasks]  # can parallelize
    return call(f'Combine results:\n' + '\n'.join(results))
```

### 4.5 Evaluator-Optimizer

```python title="evaluator_optimizer.py" linenums="1"
def gen_with_critique(topic, max_rounds=3):
    draft = call(f'Draft: {topic}')
    for _ in range(max_rounds):
        feedback = call(f'Evaluate and provide fixes:\n{draft}')
        if 'OK' in feedback[:20]:
            return draft
        draft = call(f'Revise based on feedback:\n{draft}\n---\n{feedback}')
    return draft
```

### 4.6 Single Agent

This is the agent loop skeleton from Ch 20. (See Ch 20 §5.)

### 4.7 Multi-Agent

Detailed in Ch 25. Here's just the manager snippet:

```python title="multi_agent_manager.py" linenums="1"
def manager(task):
    plan = planner_agent(task)         # agent 1: planning
    research = researcher_agent(plan)  # agent 2: research
    draft = writer_agent(research)     # agent 3: writing
    return critic_agent(draft)         # agent 4: validation
```

Each sub-function runs the Ch 20 agent loop internally.

---

## 5. In practice — which pattern fits

![Pattern decision tree](../assets/diagrams/ch21-pattern-decision-dark.svg#only-light)
![Pattern decision tree](../assets/diagrams/ch21-pattern-decision-dark.svg#only-dark)

Follow the questions **top to bottom**. When you hit YES, stop — that's your pattern.

### 5.1 Three real examples

**Case A: Customer support bot (FAQ + refunds + bug reports)**

- Q1: Single LLM + RAG? → **NO** (FAQ, refunds, and bug handling are completely different)
- Q2: Routing by input type? → **YES**
- ✅ **Routing**

**Case B: Research → write a report**

- Q1: Single LLM + RAG → NO (too many steps)
- Q2: Route by input type → NO
- Q3: Step-by-step pipeline? → **YES** (research → outline → draft → polish)
- ✅ **Prompt Chaining**

**Case C: Auto code review**

- Q1–4 → NO
- Q5: Generate → evaluate → regenerate? → **YES**
- ✅ **Evaluator-Optimizer**

### 5.2 Combining patterns

Real products use **multiple patterns together**:
- Routing (classify type) → each category uses Chaining or an Agent
- Multi-Agent where each agent runs Evaluator-Optimizer for quality convergence
- Parallelization for N candidates → Evaluator picks the winner

There's no "one pattern only" rule. But **you need to explain why you combined them**.

---

## 6. Common pitfalls

### 6.1 Memorizing pattern names instead of solving problems

You say "We use Orchestrator-Workers" but can't explain why you need it. Patterns are **solutions to problems**, not an identity.

Principle: Problem first → vocabulary second.

### 6.2 Skipping the baseline

Most "we need an agent" cases solve with **a single LLM + solid RAG + good prompts**. Before adopting patterns from this chapter, make sure you nailed Part 3.

### 6.3 Over-engineering Orchestrator-Workers

The planner breaks a 3-step job into 5. Tokens and latency × 5, accuracy unchanged. **Give the planner a max_subtasks limit**.

### 6.4 Evaluator and Generator are the same model

A model can't critique its own output well (Ch 17 self-preference bias). Make the Evaluator a **different family or size**.

### 6.5 Escaping to Multi-Agent when Single-Agent fails

Single agent isn't working? Don't assume "split into 4 agents and it'll fix itself." That usually means **4× complexity + debug nightmare**. Ch 25 explains why this is a trap.

---

## 7. Production checklist

- [ ] Did you **document your 1–2 patterns** by name for design reviews?
- [ ] Did you **measure baseline** (single LLM + RAG) first before adopting a pattern?
- [ ] Do you have a **failure taxonomy** (Ch 19) for your patterns?
- [ ] Do Orchestrator-Workers and Multi-Agent have **max_subtasks / max_agents caps**?
- [ ] Are Evaluator and Generator **different models**?
- [ ] For combined patterns, are **boundaries clear** in your code (routing-to-chaining boundary marked with comments)?
- [ ] Can you **isolate traces** per pattern for measurement? (LangSmith/Langfuse tags)
- [ ] Do you **measure pattern changes** against your eval set (Part 4)?

---

## 8. Exercises & next chapter

### Comprehension

1. What's the core difference between Workflow patterns and Agent patterns (in terms of who decides)?
2. Use §5's decision tree to pick one pattern for your prototype problem.
3. Why does the intuition "split into 4 agents and it'll get better" often backfire? (2 sentences)
4. What bias emerges when Evaluator and Generator are **the same model**? (See Ch 17.)

### Hands-on

- Take one of the §4 snippets and adapt it to your problem in **under 10 lines**.
- Compare single LLM vs. your pattern on 10 eval examples from Part 4.

### References

- **Anthropic — Building Effective Agents** (Schluntz & Zhang, 2024) — source for the five patterns. In the project: `_research/anthropic-building-effective-agents.md`
- **OpenAI — A Practical Guide to Building Agents** — Single vs Multi, Manager/Decentralized. In the project: `_research/openai-practical-guide-to-agents.md`

---

**Next** → [Ch 22. Tool Use in Practice](22-tool-use.md) — Data · Action · Orchestration tools · ACI design :material-arrow-right:
