# Ch 6. Structured Output

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part2/ch06_structured_output.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - Why **free-text responses are your pipeline's enemy**
    - **Three structured output methods** — prompt hints / tool-use schemas / native JSON mode
    - **Validation with Pydantic** + automatic retry on failure
    - Real-world schema patterns: nested, optional, enum, list
    - The parsing hell you'll hit: quote escaping, date formats, missing fields

!!! quote "Prerequisites"
    [Ch 5: Prompts + Chain-of-Thought](05-prompt-cot.md) — you've already run the "JSON hint prompt" exercise.

---

## 1. Concept — why structured output matters

Until now, you've been letting the model respond in **free text**. That breaks pipelines.

```python
# ❌ Trying to parse free text downstream
text = response.content[0].text  # "Order ID A-123, quantity 2, ship to Seoul, Gangnam district."
# ... regex? string splitting? How do you pass this to the next step?
```

```python
# ✅ Structured JSON
data = {"order_id": "A-123", "quantity": 2, "address": "Seoul, Gangnam"}
# Straight to database, API, conditional branching
```

Speaking well and outputting machine-readable format are different skills. This chapter locks down the second one.

---

## 2. Why it matters — pipeline perspective

Go back to the 8-block diagram in Part 1 Ch 3. Every step — **understand → retrieve → generate → validate → store** — passes **objects, not free text**. Without structure:

- **Understanding block**: extracted intent and entities, but the format drifts and parsing fails
- **Validation block**: can't check against schema
- **Storage block**: which database columns do you map to?
- **Tool calling** (Ch 8): parameter extraction fails → tool won't run

> Without structured output, every downstream block's reliability drops.

---

## 3. Where it's used

| Use case | Output schema |
|---|---|
| Order extraction | `{item, quantity, address, request_date}` |
| Email classification + priority | `{category: "refund"\|"shipping"\|..., priority: 1-5}` |
| Entity extraction from documents | `{people: [...], dates: [...], amounts: [...]}` |
| User intent analysis | `{intent, confidence, needs_human}` |
| Tool parameters (Ch 8) | whatever the tool defines |

---

## 4. Minimal example — extract with Pydantic

```bash
pip install anthropic pydantic
```

```python title="extract_order.py" linenums="1" hl_lines="4 5 6 7 8"
from anthropic import Anthropic
from pydantic import BaseModel

class Order(BaseModel):
    item: str
    quantity: int
    address: str

SYSTEM = """Extract order information as **JSON only**.
Schema: {"item": str, "quantity": int, "address": str}
No other text allowed."""

client = Anthropic()
r = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=256,
    system=SYSTEM,
    messages=[{"role": "user", "content": "Send 2 pairs of red running shoes to Seoul, Gangnam district."}],
)

order = Order.model_validate_json(r.content[0].text)  # (1)!
print(order.item, order.quantity, order.address)
```

1. Pydantic parses the JSON and validates types. If `quantity` comes back as "two" instead of `2`, you get `ValidationError`.

This is the baseline. But models sometimes **mix in speech** around the JSON (`"Here's the JSON: {...}"`), breaking parsing. Section 5 fixes it.

---

## 5. Hands-on

### 5.1 Three methods compared

![Three methods of structured output](../assets/diagrams/ch6-methods-comparison.svg#only-light)
![Three methods of structured output](../assets/diagrams/ch6-methods-comparison-dark.svg#only-dark)

| Method | Implementation | Success rate | Best for |
|---|---|:-:|---|
| **Prompt hint** | Schema + examples in system prompt | 70–90% | Early prototypes |
| **Tool-use schema** | Anthropic `tools` parameter | 95–99% | Production (recommended) |
| **Native JSON mode** | OpenAI `response_format={json_schema}` | ~100% | OpenAI users |

Real-world flow: **start with prompt hints → if failure rate is high, upgrade to tool-use**.

### 5.2 Structured output via tool-use (Anthropic way)

Anthropic's **tool_use** feature was built for "calling tools," but you can weaponize it for **schema enforcement without actually running the tool**. You're using it purely to force structured input.

```python title="tool_use_extract.py" linenums="1" hl_lines="5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20"
from anthropic import Anthropic
client = Anthropic()

tools = [{
    "name": "record_order",
    "description": "Records a customer order",
    "input_schema": {  # (1)!
        "type": "object",
        "properties": {
            "item":     {"type": "string", "description": "Product name"},
            "quantity": {"type": "integer", "minimum": 1},
            "address":  {"type": "string"},
        },
        "required": ["item", "quantity", "address"],
    },
}]

r = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    tools=tools,
    tool_choice={"type": "tool", "name": "record_order"},  # (2)!
    messages=[{"role": "user", "content": "Send 2 pairs of red running shoes to Seoul, Gangnam district."}],
)

# Extract input from tool_use response
for block in r.content:
    if block.type == "tool_use":
        data = block.input  # Already a dict
        print(data)
```

1. **JSON Schema** standard. `type`, `properties`, `required` are mandatory.
2. `tool_choice` **forces the model to use this tool**. Result: ~100% schema compliance.

### 5.3 Pydantic validation + automatic retry

![Structured output pipeline](../assets/diagrams/ch6-structured-output-flow.svg#only-light)
![Structured output pipeline](../assets/diagrams/ch6-structured-output-flow-dark.svg#only-dark)

The biggest failure mode with prompt hints: **the model mixes speech around the JSON**. Here's the three-step defense:

```python title="validated_extract.py" linenums="1"
import json
from pydantic import BaseModel, ValidationError
from anthropic import Anthropic

class Order(BaseModel):
    item: str
    quantity: int
    address: str

SYSTEM = """Return order info as JSON only.
Schema: {"item": str, "quantity": int, "address": str}
No other text ever."""

def extract_order(text: str, retries: int = 2) -> Order | None:
    client = Anthropic()
    messages = [{"role": "user", "content": text}]
    last_error = None

    for attempt in range(retries + 1):
        r = client.messages.create(
            model="claude-haiku-4-5", max_tokens=256,
            system=SYSTEM, messages=messages,
        )
        raw = r.content[0].text.strip()

        # 1) Extract JSON: find the first {...} block
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start < 0 or end <= 0:
            last_error = "No JSON block found"
        else:
            # 2) Parse + validate
            try:
                return Order.model_validate_json(raw[start:end])
            except (json.JSONDecodeError, ValidationError) as e:
                last_error = str(e)

        # 3) On failure, include the error in the next prompt
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content":
            f"Your previous response violated the schema: {last_error}\nReturn only valid JSON."})

    return None  # Final failure — fallback handles rules/defaults
```

**The pattern**:

1. **Extract JSON block only** (defend against surrounding speech)
2. **Validate with Pydantic** (types, required fields, constraints)
3. **Retry with error details** — the model self-corrects

!!! tip "Tool-use eliminates steps 1 and 2"
    With tool-use, JSON extraction is gone (SDK handles it) and parse failures disappear. But keep Pydantic validation anyway — models sometimes skip required fields.

### 5.4 Real-world schema patterns

```python title="advanced_schemas.py" linenums="1"
from pydantic import BaseModel, Field
from typing import Literal
from datetime import date

class Address(BaseModel):
    street: str
    city: str
    postal_code: str | None = None  # Optional

class Order(BaseModel):
    order_id: str = Field(..., pattern=r"^[A-Z]-\d+$")  # (1)!
    items: list[str]                                     # List
    quantity: int = Field(..., ge=1, le=100)             # Range constraint
    priority: Literal["low", "normal", "high"]           # Enum
    ship_date: date                                      # ISO-8601 auto-parsed
    address: Address                                     # Nested
    notes: str | None = None                              # Optional
```

1. `Field(..., pattern=...)` enforces a regex constraint.

**Heads up**: when you pass this whole schema to the model, use `model.model_json_schema()` to extract the JSON Schema, then feed that to your prompt or tool_use:

```python
schema = Order.model_json_schema()
print(json.dumps(schema, ensure_ascii=False, indent=2))
```

---

## 6. Common pitfalls

!!! warning "Pitfall 1: unescaped quotes in output"
    When text contains double quotes, the model produces invalid JSON: `"content": "He said "hello" then left"`. Result: `json.JSONDecodeError`.  
    **Fix**: add to system prompt: "Escape double quotes as \\\\" or use tool-use (SDK handles it).

!!! warning "Pitfall 2: dates and currency format drift"
    Models output `"ship_date": "next Monday"` or `"price": "₩15,000"` instead of structured formats.  
    **Fix**: put **examples in the schema** (`"e.g. 2026-04-18"`), use Pydantic Field descriptions aggressively, retry on validation failure (§5.3).

!!! warning "Pitfall 3: missing required fields"
    Models sometimes omit fields, especially when optional and required are mixed.  
    **Fix**: use `...` in Pydantic to mark required, use `required` array in tool-use, include **which field is missing** in the error message on retry.

!!! warning "Pitfall 4: schema too deep and complex"
    5+ levels of nesting confuses both models and humans. Retries won't help.  
    **Fix**: flatten to 2–3 levels. Break complex structures into **multiple separate calls** (each with one simple schema).

!!! warning "Pitfall 5: infinite retry loops"
    Every validation failure triggers a re-query. Your bill skyrockets.  
    **Fix**: cap retries at 2–3. After that, **fallback** (rule-based parser, defaults, escalate to human).

---

## 7. Production checklist

- [ ] **Pydantic models in one module** (`schemas.py`) — shared across the pipeline
- [ ] **Tool-use is default** — if you're still using prompt hints, plan a migration
- [ ] **Log validation failure rate** — 5%+ is a signal to redesign schema/prompt
- [ ] **Retry cap 2–3** with mandatory fallback path
- [ ] Schema changes consider **backwards compatibility** — write Pydantic validators to accept old formats
- [ ] Keep **test fixtures of real LLM responses** for regression testing
- [ ] **Sensitive fields** (SSN, card numbers) rejected at schema level (Part 6 Ch 28)

---

## 8. Exercises

- [ ] Add a `color: str` field to §4's `Order` schema and update the prompt. Verify extraction works.
- [ ] Intentionally call with garbage input (`"just send me anything"`). Record the `ValidationError` message.
- [ ] Convert §5.2's tool-use example to use the emotion classification from Ch 5. Hit **100% success rate**.
- [ ] Build §5.3's retry logic with a deliberately wrong schema hint. Watch it fail after 2 retries and return `None`.
- [ ] Extract §5.4's nested `Address` in an `Order`. When the model drops `address.city`, see which error message appears.

---

## 9. References & further reading

- **Anthropic Tool Use**: [docs.anthropic.com/tool-use](https://docs.anthropic.com){target=_blank} — `tools`, `tool_choice`, JSON Schema spec
- **OpenAI Structured Outputs**: [platform.openai.com/docs/guides/structured-outputs](https://platform.openai.com/docs){target=_blank}
- **Pydantic v2** official: [docs.pydantic.dev](https://docs.pydantic.dev){target=_blank}
- **JSON Schema** spec: [json-schema.org](https://json-schema.org){target=_blank}

---

**Next** → [Ch 7. Streaming and UX](07-streaming-ux.md) :material-arrow-right:
So far you've waited for the full response. Now: **token-by-token streaming** to make users feel instant.
