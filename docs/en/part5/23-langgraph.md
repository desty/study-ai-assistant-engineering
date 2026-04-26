# Ch 23. LangGraph — State Graphs

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/en/part5/ch23_langgraph.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - **StateGraph** — nodes · edges · conditional edges · reducers
    - **Checkpointer** — saving state after every node (SqliteSaver / Postgres)
    - **Thread ID** — persistent conversations · resuming execution
    - **Interrupt** — pausing an agent, waiting for human approval, then **resume**
    - **Streaming** — progressive responses per node (for UX)
    - Overengineering pitfalls · conditional edge hell · exceptions during streaming

!!! quote "Prerequisites"
    [Ch 22](22-tool-use.md) — approval chains. This chapter implements that approval pattern using **LangGraph's standard approach**.

---

## 1. Concept — graphs instead of loops

The agents in Ch 20–22 use **while loops**. Simple, but production systems need more:

- **Shared state**: multiple nodes reading and writing the same state
- **Checkpoints**: recovery from mid-execution failures and restarts
- **Branching and parallelism**: conditional routing and independent concurrent tasks
- **Human gates**: pausing mid-flow to wait for approval
- **Streaming**: real-time progress to the UI

Rolling your own becomes spaghetti fast. **LangGraph** is the standard framework for these patterns.

> StateGraph = **state schema** + **node functions** + **edge connections** + **checkpointer**.

---

## 2. Why you need it — loops vs. graphs

**Loop limitations**:
- State is implicit (scattered across variables) → hard to reproduce and debug
- Failures restart from the beginning (long agents cost more and add latency)
- Can't insert human approval mid-flow

**Graph advantages**:
- **State is explicit TypedDict** → type checking and trace tracking
- **Checkpoint after every node** → resume from the failure point
- **Interrupt** in one line
- **Trace is automatic** (LangSmith integration)

Cost: learning curve plus library dependency. At product scale, the gains outweigh the cost.

---

## 3. Where you use it — StateGraph anatomy

![StateGraph Anatomy](../assets/diagrams/ch23-stategraph-anatomy.svg#only-light)
![StateGraph Anatomy](../assets/diagrams/ch23-stategraph-anatomy-dark.svg#only-dark)

### 3-1. Building blocks

| Element | Purpose | Example |
|---|---|---|
| **State** | Shared memory (TypedDict) | `messages · intent · needs_human` |
| **Node** | Function that reads state and **returns updates** | `classify_intent(state) -> {'intent': 'refund'}` |
| **Edge** | Flow between nodes | `START → classify → respond → END` |
| **Conditional Edge** | Check state and **choose next node** | `intent == 'refund' → refund_check` |
| **Reducer** | Rule for merging state updates | `add_messages` (append to list) |
| **Checkpointer** | State storage backend | SqliteSaver · PostgresSaver |
| **Thread ID** | Session identifier | `{'configurable': {'thread_id': 'user-42'}}` |

### 3-2. When to use StateGraph vs. something simpler

- **Single LLM call**: overkill. Just a function.
- **Pure chaining (A→B→C, no branching)**: LCEL is simpler
- **Truly autonomous agent (LLM decides everything)**: Ch 20 loop + Ch 22 tools is enough
- **Complex state · approval · resumption**: ✅ StateGraph

---

## 4. Minimal example — three-bucket customer support graph

Intent classification → (FAQ / Refund / Bug) routing → response. Refunds trigger an interrupt.

```bash
pip install langgraph langchain-anthropic
```

```python title="support_graph.py" linenums="1" hl_lines="8 27 43"
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import Annotated
from langchain_anthropic import ChatAnthropic

class State(TypedDict):  # (1)!
    messages: Annotated[list, add_messages]
    intent: str
    response: str

llm = ChatAnthropic(model='claude-haiku-4-5-20251001')

def classify(state: State):  # (2)!
    last = state['messages'][-1].content
    prompt = f'Classify as: faq / refund / bug\nQuestion: {last}\nOne word only:'
    intent = llm.invoke(prompt).content.strip().lower()
    return {'intent': intent if intent in ['faq','refund','bug'] else 'faq'}

def faq_answer(state: State):
    r = llm.invoke(f'Answer helpfully (FAQ): {state["messages"][-1].content}')
    return {'response': r.content}

def refund_check(state: State):
    return {'response': 'Checking refund eligibility…'}  # Real code: DB lookup

def escalate(state: State):
    return {'response': 'Escalating to support team.'}

def respond(state: State):
    return {'messages': [{'role': 'assistant', 'content': state['response']}]}

def route(state: State) -> Literal['faq_answer','refund_check','escalate']:  # (3)!
    return {'faq':'faq_answer','refund':'refund_check','bug':'escalate'}[state['intent']]

# Build graph
g = StateGraph(State)
g.add_node('classify', classify)
g.add_node('faq_answer', faq_answer)
g.add_node('refund_check', refund_check)
g.add_node('escalate', escalate)
g.add_node('respond', respond)

g.add_edge(START, 'classify')
g.add_conditional_edges('classify', route)  # (4)!
for n in ['faq_answer','refund_check','escalate']:
    g.add_edge(n, 'respond')
g.add_edge('respond', END)

# Compile with checkpointer
memory = SqliteSaver.from_conn_string(':memory:')  # Production: file or database
app = g.compile(checkpointer=memory)
```

1. **State** — The key is `Annotated[list, add_messages]`. The reducer handles appending automatically.
2. **Node** — Takes state and **returns only the fields you're updating.** Don't overwrite the entire state.
3. **Router** — The function that decides the next node based on state. Return value is the next node's name.
4. **add_conditional_edges** — Register multiple branches at once.

### Running it

```python title="run_graph.py" linenums="1"
cfg = {'configurable': {'thread_id': 'user-42'}}
result = app.invoke(
    {'messages': [{'role': 'user', 'content': 'Can I get a refund for order O-1024?'}]},
    config=cfg,
)
print(result['response'])
```

**Same `thread_id` = conversation continues** (state is restored).

---

## 5. Hands-on — Interrupt and resume

![Interrupt Flow](../assets/diagrams/ch23-interrupt-flow.svg#only-light)
![Interrupt Flow](../assets/diagrams/ch23-interrupt-flow-dark.svg#only-dark)

### 5-1. Adding a gate with interrupt_before

Pause the graph **before entering** a node that needs approval.

```python title="interrupt_graph.py" linenums="1" hl_lines="4 14"
app = g.compile(
    checkpointer=memory,
    interrupt_before=['refund_check'],  # (1)! Pause before entering these nodes
)

cfg = {'configurable': {'thread_id': 'user-42'}}

# First run — execute up to classify, then pause
result = app.invoke({'messages': [{'role':'user','content':'I need a refund'}]}, cfg)

# Check state (show in operator UI)
snapshot = app.get_state(cfg)
print(snapshot.values['intent'])   # 'refund'
print(snapshot.next)                # ('refund_check',)

# Second run — resume after approval. invoke(None) signals "continue"
result = app.invoke(None, cfg)  # (2)!
print(result['response'])
```

1. **interrupt_before** — Pause just before entry. `interrupt_after` also available.
2. **invoke(None, config)** — Means "pick up where you left off." Checkpointer restores state.

### 5-2. Real-world operation pattern

| # | Time | Action | State |
|---|---|---|---|
| 1 | User request | `graph.invoke(...)` first call | — |
| 2 | Classify runs | Determine routing | — |
| 3 | `interrupt_before='refund_check'` | Pause + save state | State stored in DB |
| 4 | Return | Alert operator (Slack/dashboard) | — |
| 5 | ~10 min later, operator approves | Webhook triggered | — |
| 6 | `graph.invoke(None, {'thread_id': ...})` | Resume | State restored from DB |
| 7 | refund_check runs | Call tools | — |
| 8 | respond runs → END | Send to user | — |

**Key**: just `thread_id` is needed, and intermediate state lives in the DB, so **restarts and recovery are free**.

### 5-3. Streaming — real-time UX

```python title="stream_graph.py" linenums="1"
for chunk in app.stream(
    {'messages': [{'role':'user','content':'FAQ question'}]},
    config=cfg,
    stream_mode='updates',  # 'values' · 'messages' · 'updates' · 'debug'
):
    print(chunk)  # {node_name: {field: value}}
```

Emits a chunk after each node completes. Show "Classifying… Writing response…" progress to the user.

### 5-4. Time travel — reset to an earlier checkpoint

```python title="time_travel.py" linenums="1"
# See all checkpoints
for snap in app.get_state_history(cfg):
    print(snap.config['configurable']['checkpoint_id'], snap.next)

# Pick one, fork execution from that point with different input
past = list(app.get_state_history(cfg))[3]
new_cfg = past.config  # Start from here
app.invoke({'intent': 'faq'}, new_cfg)  # Override state + proceed
```

Useful for debugging and A/B testing.

---

## 6. Common failure modes

### 6-1. Overengineering StateGraph

A three-node flow that turns into 10 nodes with 7 conditional edges. **LCEL and plain functions** handle most of this. Only reach for StateGraph if **at least two of these three** are required: shared state, checkpoints, interrupts.

### 6-2. Conditional edge hell

Too many `add_conditional_edges(X, router_fn)` calls make flow hard to visualize. **Split into two subgraphs** if you exceed 5 conditionals.

### 6-3. Overwriting entire state

If a node returns `return state`, it wipes everything (bypassing the reducer). Always **return only the fields you're updating**: `return {'intent': 'refund'}`.

### 6-4. Missing checkpointer

`checkpointer=None` means interrupt, resume, and threading won't work. Use `SqliteSaver(':memory:')` for dev, `PostgresSaver` for production.

### 6-5. No error handling during streaming

Node throws an exception → stream stops → UI hangs. Wrap nodes in try/except, set an error state field, and let the next node route based on it.

### 6-6. Careless thread ID design

`thread_id = user_id` means two conversations by the same user get mixed up. Use `thread_id = f'{user_id}:{session_id}'` to include the session.

---

## 7. Production checklist

- [ ] Is state schema a **TypedDict** with type checking?
- [ ] Do nodes **return only updated fields?** (not the entire state)
- [ ] Is checkpointer configured for **production DB** (Postgres)?
- [ ] Is `thread_id` **unique per session,** not just per user?
- [ ] Is the **interrupt point** placed before the approval-required node?
- [ ] Does each node have **try/except** plus an error state field?
- [ ] Have conditional edges been **reviewed for refactoring** (>5 = split into subgraphs)?
- [ ] Are traces enabled **(LangSmith / Langfuse)?**
- [ ] When streaming, does the UI **distinguish chunk types** (updates/values/messages)?
- [ ] Is **time travel actually necessary** (debugging / A/B)? (Usually not.)

---

## 8. Exercises and next chapter

### Review questions

1. Name three scenarios where a plain function chain is enough instead of StateGraph.
2. Explain the difference between conditional edges and regular edges, and what the router function returns.
3. When using `interrupt_before`, where is state stored, and which API resumes it?
4. Sketch a concrete scenario showing the risk of `thread_id = user_id` alone.

### Hands-on

- Run §4's support graph in Colab. Call it twice with `thread_id='u1'` → verify state continues.
- Add the interrupt pattern from §5-1. Confirm that `invoke(None, cfg)` actually resumes.
- Use `app.get_state_history(cfg)` to list checkpoints, pick one, and time-travel it.

### References

- **LangGraph official docs** — Persistence · Interrupt · Time Travel. Archived in `_research/langgraph-persistence.md`
- **Anthropic — Building Effective Agents** — boundary between workflows and agents. Archived in `_research/anthropic-building-effective-agents.md`

---

**Next** → [Ch 24. Agent Memory](24-agent-memory.md) — thread memory / cross-thread · episodic · MemGPT layers :material-arrow-right:
