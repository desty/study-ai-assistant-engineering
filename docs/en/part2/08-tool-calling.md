# Ch 8. Tool Calling Fundamentals

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/en/part2/ch08_tool_calling.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - **Tool Calling (Function Calling)** — how to let an LLM invoke functions in your code
    - **Three types of tools** (Data / Action / Orchestration) — OpenAI's Practical Guide taxonomy
    - The **tool_use ↔ tool_result loop** structure between LLM and tools
    - **Pydantic validation** of parameters + **approval-based execution** for risky tools
    - Infinite loops · bad parameters · side effects — where real implementations blow up
    - The bridge into Part 5 Agents

!!! quote "Prerequisites"
    [Ch 4–7](04-api-start.md) completed. Especially **Ch 6 structured output** — tool definitions are just JSON Schema.

---

## 1. Concept — giving the LLM **hands**

Until now, the LLM has only **read and written**. It can't query the outside world (databases, APIs, files) or perform actions.

**Tool Calling** gives the LLM a pair of **hands**:

1. We **declare a list of functions** (name · description · parameter schema)
2. When the LLM reads the user request, it decides **"I need this tool"** and returns a `tool_use` response
3. Our code **executes** the function
4. We pass the result back as `tool_result`
5. The LLM reads the result, continues reasoning → final answer

![Tool calling loop](../assets/diagrams/ch8-tool-use-loop.svg#only-light)
![Tool calling loop](../assets/diagrams/ch8-tool-use-loop-dark.svg#only-dark)

The critical point: **the LLM never executes the function directly.** It only decides *which* function to call and *what* arguments to pass. **Execution always happens in our code.** That boundary is where safety begins.

---

## 2. Why you need it

- **Freshness** — information after training (weather · stock prices · inventory)
- **Private data** — company databases · customer order history
- **Actions** — sending email · charging cards · creating tickets · making reservations
- **Computation accuracy** — letting the model do math isn't reliable → use a calculator tool instead

!!! note "Relationship to Part 5 Agents"
    Tool calling is the **foundation of agents**. This chapter covers one or two tool calls. Part 5 adds length — longer loops, memory attachments, layered guardrails.

---

## 3. Three types of tools

![Three types of tools](../assets/diagrams/ch8-tool-three-kinds.svg#only-light)
![Three types of tools](../assets/diagrams/ch8-tool-three-kinds-dark.svg#only-dark)

Classification from OpenAI's Practical Guide ([_research/openai-practical-guide-to-agents.md](#)):

| Type | Examples | Safety angle |
|---|---|---|
| **Data** (read) | DB query, document search, web search, file read | **Read-only** — relatively safe |
| **Action** (write) | Email send, charge card, cancel order, issue ticket | **Side effects** — approval + audit required |
| **Orchestration** (compose) | Call another agent, bundle sub-tools | Complexity ↑, Part 5 territory |

**On the path from PoC to enterprise**:

- PoC focuses on Data (safer)
- Production adds Action → **approval queue + audit log mandatory** (Part 6 Ch 29)

---

## 4. Minimal example — calculator tool

```python title="calc_tool.py" linenums="1" hl_lines="6 7 8 9 10 11 12 13 14 15 16 17 18"
from anthropic import Anthropic

client = Anthropic()

tools = [
    {
        "name": "calculate",
        "description": "Perform simple arithmetic. Use for complex money · exchange rate · or quantity math.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A Python-evaluable arithmetic expression. Example: '1000 * 1.08 / 12'"
                },
            },
            "required": ["expression"],
        },
    }
]

def run_calculate(expression: str) -> str:  # (1)!
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"error: {e}"

# 1) First call
messages = [{"role": "user", "content": "If I save $1,000 a month at 5% annual return for 3 years, how much is just interest?"}]
r = client.messages.create(
    model="claude-haiku-4-5", max_tokens=1024,
    tools=tools, messages=messages,
)

# 2) Did we get a tool_use response?
if r.stop_reason == "tool_use":
    for block in r.content:
        if block.type == "tool_use":
            print(f"LLM requested tool: {block.name}, args: {block.input}")
            tool_result = run_calculate(**block.input)  # (2)!

            # 3) Call again with tool_result
            messages.append({"role": "assistant", "content": r.content})
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": tool_result,
                }],
            })
            r2 = client.messages.create(
                model="claude-haiku-4-5", max_tokens=1024,
                tools=tools, messages=messages,
            )
            print("Final:", r2.content[0].text)
```

1. **Execution is our code.** The LLM only passes the expression.
2. `eval` has risks covered in §6 mistake 1. Production uses a safe evaluator like `asteval`.

---

## 5. Real-world tutorial

### 5.1 Multiple tools · Pydantic validation

When the LLM passes bad parameters, we **validate tool input with Pydantic**.

```python title="multi_tools.py" linenums="1"
from pydantic import BaseModel, Field, ValidationError

class WeatherArgs(BaseModel):
    city: str = Field(..., min_length=1)
    units: str = Field(default="metric", pattern=r"^(metric|imperial)$")

class OrderLookupArgs(BaseModel):
    order_id: str = Field(..., pattern=r"^[A-Z]-\d+$")

TOOL_SPECS = {
    "get_weather": {
        "schema": WeatherArgs,
        "tool": {
            "name": "get_weather",
            "description": "Look up current weather for a city",
            "input_schema": WeatherArgs.model_json_schema(),  # (1)!
        },
        "handler": lambda args: f"{args.city} weather 15°C clear",
    },
    "lookup_order": {
        "schema": OrderLookupArgs,
        "tool": {
            "name": "lookup_order",
            "description": "Look up an order by ID (format: A-123)",
            "input_schema": OrderLookupArgs.model_json_schema(),
        },
        "handler": lambda args: f"{args.order_id}: shipping, ETA 2 days",
    },
}

def dispatch(tool_name: str, raw_input: dict) -> str:
    spec = TOOL_SPECS[tool_name]
    try:
        args = spec["schema"].model_validate(raw_input)  # (2)!
    except ValidationError as e:
        return f"invalid_input: {e}"
    return spec["handler"](args)
```

1. Extract JSON Schema from Pydantic — validation logic and tool definition **live in one place**.
2. Even if the LLM passes wrong types, ValidationError becomes a fallback.

### 5.2 Loop runs **multiple times**

One request may need multiple tool calls. If the LLM returns `stop_reason=="tool_use"` again, execute again.

```python title="agent_loop.py" linenums="1" hl_lines="6"
def chat_with_tools(user_msg: str, max_steps: int = 5) -> str:
    messages = [{"role": "user", "content": user_msg}]
    tools = [s["tool"] for s in TOOL_SPECS.values()]

    for step in range(max_steps):  # (1)!
        r = client.messages.create(
            model="claude-haiku-4-5", max_tokens=1024,
            tools=tools, messages=messages,
        )
        messages.append({"role": "assistant", "content": r.content})

        if r.stop_reason != "tool_use":  # final answer
            return "".join(b.text for b in r.content if b.type == "text")

        # Process tool_use blocks
        tool_results = []
        for block in r.content:
            if block.type == "tool_use":
                result = dispatch(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        messages.append({"role": "user", "content": tool_results})

    return "[max_steps exceeded]"
```

1. **Upper bound mandatory.** Prevents infinite loops (§6 mistake 2).

### 5.3 Approval-based execution (Action tools)

Tools with side effects must be **approved by a human before execution**. Simplest pattern:

```python title="approve_gated.py" linenums="1" hl_lines="3 4 5 6 7"
RISKY_TOOLS = {"send_email", "cancel_order", "charge_card"}

def dispatch_with_approval(tool_name: str, args: dict) -> str:
    if tool_name in RISKY_TOOLS:
        print(f"⚠️  {tool_name}({args}) approval requested")
        if input("y/N > ").strip().lower() != "y":
            return "declined_by_user"
    return dispatch(tool_name, args)
```

**In production, not CLI input**:

- Slack button (team approval)
- Internal dashboard approval queue
- LangGraph `interrupt` (Part 5 Ch 23)

### 5.4 Error and timeout handling

Tool execution can fail (external API down, etc.). Pass the error back to the LLM as `tool_result` — **the model attempts recovery**:

```python title="tool_with_timeout.py" linenums="1"
import requests

def get_weather_safe(city: str) -> str:
    try:
        r = requests.get(f"https://api.weather.com/{city}", timeout=5)
        return r.json()["description"]
    except requests.Timeout:
        return "error: weather API timeout"  # (1)!
    except Exception as e:
        return f"error: {e}"
```

1. Return the error as a string — the LLM naturally responds in English like **"The server is slow; let me check again in a moment."**

---

## 6. Common failure points

!!! warning "Mistake 1: using `eval` directly"
    `eval(expression)` runs **arbitrary code**. If the LLM passes `__import__('os').system('rm -rf /')`, disaster.  
    **Fix**: use safe evaluators like `asteval` · `numexpr`. Or `ast.parse + whitelist validation`. Production uses sandboxing (Docker · WASM).

!!! warning "Mistake 2: infinite loops"
    LLM calls the same tool over and over → without `max_steps`, tokens and costs explode.  
    **Fix**: loop limit of 5–10. Exceed it and return an explicit error. Detect repeated tool calls and **steer to a different path**.

!!! warning "Mistake 3: missing parameter validation"
    LLM passes `quantity: "two"` instead of a number — code runs anyway, data corrupted.  
    **Fix**: **always** validate with Pydantic (§5.1). On failure, return `invalid_input` tool_result → model retries.

!!! warning "Mistake 4: executing Action tools without approval"
    Charges · deletes · sends all execute **by model judgment alone** — you're waiting for a disaster.  
    **Fix**: §5.3. Maintain a `RISKY_TOOLS` list. In production, approval queue + human sign-off before execution.

!!! warning "Mistake 5: vague tool names and descriptions"
    Tools like `query_data` · `do_thing` confuse the LLM. Overlapping tools (`search_db` · `lookup_db`) also fail.  
    **Fix**: **verb + clear noun** (`create_order` · `cancel_subscription`). In description, say "when to use this" and "when not to." Reference OpenAI Practical Guide's ACI design principles (§9).

!!! warning "Mistake 6: forgetting tool_result before next call"
    Receive `tool_use` and send a new user message immediately — LLM gets confused. After `assistant + tool_use`, **always** send `user + tool_result` pair.  
    **Fix**: wrap the loop (§5.2) in a function to prevent mistakes.

---

## 7. Production checklist

- [ ] **Loop limit** `max_steps` set to 5–10
- [ ] **All tool inputs validated with Pydantic** · return `invalid_input` on failure
- [ ] **Action tool whitelist** + approval queue + audit log
- [ ] **Output size limit** — big query results overflow context
- [ ] **Per-tool timeouts** — Data 5s, Action 30s, etc.
- [ ] **Observability** — log which tools · how many times · how long (LangSmith/Langfuse)
- [ ] **Cost · latency monitoring** — tool loops raise costs fast
- [ ] **Sandboxing** — code-execution tools run in isolated Docker or WASM

---

## 8. Exercises

- [ ] Run §4's calculator example. Watch the LLM generate expressions for 3 different questions.
- [ ] §5.1's `WeatherArgs` — deliberately send `units="centigrade"` from the LLM and confirm ValidationError catches it
- [ ] §5.2 with `max_steps=2` — reproduce "[max_steps exceeded]" on a complex request
- [ ] Implement approval-based execution via Slack button or console input. Record how the LLM responds to rejection.
- [ ] Deliberately vague tool description (`"something useful"`) — measure LLM tool-selection failure rate

---

## 9. Sources and further reading

- **Anthropic Tool Use**: [docs.anthropic.com/tool-use](https://docs.anthropic.com){target=_blank}
- **OpenAI Function Calling**: [platform.openai.com/docs/guides/function-calling](https://platform.openai.com/docs){target=_blank}
- **OpenAI Practical Guide to Building Agents** — tools' three categories (Data / Action / Orchestration) · ACI design principles. Summarized in project `_research/openai-practical-guide-to-agents.md`
- **Anthropic Building Effective Agents** — importance of tool naming and descriptions. See `_research/anthropic-building-effective-agents.md`

---

## 10. Part 2 review

What Part 2 covered (5 chapters):

| Ch | Skill | Production value |
|---|---|---|
| 4 | API calls · error · retry | Foundation of every LLM app |
| 5 | Prompts · Few-shot · CoT | Model behavior locked in by contract |
| 6 | Structured output (Pydantic · tool-use schema) | JSON for downstream pipelines |
| 7 | Streaming · UX | Perceived latency matters |
| 8 | **Tool Calling** | Giving the LLM hands — start of agents |

**Part 2 completion** — from here, you should be able to build **one of these at PoC level**:

- Customer inquiry auto-classification + simple response (structured output–based)
- Document + tool lookup bot (tool calling + basic RAG preview)
- Streaming chatbot web UI (FastAPI + SSE)

---

**Next** → [Part 3. RAG — Attaching External Knowledge](../part3/09-why-rag.md) :material-arrow-right:  
So far we've used only what the model learned. Now we add **your company's documents and databases** to ground answers in evidence.
