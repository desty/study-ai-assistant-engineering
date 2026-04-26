# Ch 26. Production Architecture

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part6/ch26_prod_arch.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - **PoC vs. production** — what changes when real traffic hits
    - **Five layers**: API · LLM · Retrieval · Session · Observability
    - **How one LLM call survives**: cache → rate limit → call → retry → circuit breaker → fallback (5 stages)
    - **Minimum skeleton** in FastAPI · async · Redis · tenacity
    - Sync/async tradeoffs · idempotency · backpressure
    - **Five pitfalls** (all-sync · no cache · blind retry · single provider · session in memory)

!!! quote "Prerequisites"
    You've completed [Part 5](../part5/20-what-is-agent.md) — single agents, LangGraph, conversation memory. Now we rebuild everything assuming **multiple concurrent users** and **failures always happen**.

---

## 1. Concept — From PoC to production

Your PoC looks like this.

```python
@app.post("/chat")
def chat(msg: str):
    return client.messages.create(model="...", messages=[{"role": "user", "content": msg}])
```

This code breaks the moment:

- **Two users call at once** — single synchronous handler queues requests
- **Provider freezes for 30 seconds** — our server hangs for 30 seconds too
- **Rate limit hit** — all users get 500 errors
- **Same question asked 100 times** — we pay token cost every time
- **No trace** — we have no idea what got slow

Production architecture **splits these five problems into layers**, each handling one.

![Production architecture](../assets/diagrams/ch26-prod-arch.svg#only-light)
![Production architecture](../assets/diagrams/ch26-prod-arch-dark.svg#only-dark)

| Layer | Responsibility | Failure impact |
|---|---|---|
| **API Gateway** | Auth · routing · rate limit · async | Total shutdown |
| **LLM Layer** | Provider abstraction · cache · retry · routing | Answer quality / cost |
| **Retrieval Layer** | Vector + lexical · embedding cache · reranking | Answer accuracy |
| **Session Store** | Thread state · preferences · idempotency | Conversation breaks |
| **Observability** | Trace · log · cost · latency | Invisible failures |

The key insight: **each layer fails and recovers independently.** Retrieval dies? The LLM answers from context alone. A provider dies? Route to another. Nothing depends on everything working.

---

## 2. Why it matters — why one big handler doesn't scale

**① Concurrency.** If one LLM call takes 5 seconds and you have four sync workers, you handle 0.8 requests per second. With async + connection pool, one worker handles 50+ req/sec.

**② Separation of concerns.** Cache, retry, tracing logic mixed into business code bloats your handler to 200 lines. One fix breaks three things.

**③ Multi-provider switching.** When Anthropic goes down, you need to flip to OpenAI instantly. That requires a provider abstraction layer that the caller knows nothing about.

**④ Cost visibility.** Trace and logs scattered across services means you can't answer "which endpoint is expensive?" You learn about cost spikes a week late.

**⑤ Idempotency.** Users refresh the page — same request hits twice. Operations like billing or email can't run twice. You need a deduplication layer.

---

## 3. Where it's used — three typical patterns

| Scenario | Core decision |
|---|---|
| **Synchronous chat (reply within 5 seconds)** | FastAPI async + streaming + Redis session |
| **Background analysis (10+ seconds)** | Queue (Celery/SQS) + webhook notification + idempotency key |
| **Agent workflow** | LangGraph + checkpointer + interrupt (Ch 23) |

Most products run **both sync chat and background queue tracks.** Chat is real-time; heavy work queues.

---

## 4. Minimal example — FastAPI + tenacity + Redis

```python title="app/llm_client.py" linenums="1" hl_lines="9 18 26"
import os, hashlib, json
from anthropic import Anthropic, APIStatusError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import redis.asyncio as redis

client = Anthropic()
cache = redis.from_url(os.environ["REDIS_URL"])

def cache_key(model: str, messages: list) -> str:                       # (1)!
    body = json.dumps({"m": model, "x": messages}, sort_keys=True)
    return f"llm:{hashlib.sha256(body.encode()).hexdigest()}"

@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(APIStatusError),
)
async def call_llm(model: str, messages: list) -> str:                  # (2)!
    key = cache_key(model, messages)
    if hit := await cache.get(key):
        return hit.decode()
    resp = client.messages.create(
        model=model, max_tokens=1024, messages=messages, timeout=30.0,
    )
    text = resp.content[0].text
    await cache.setex(key, 3600, text)                                  # (3)!
    return text
```

1. Cache key is model + full message hash. One character difference = different key. Intentional variation busts the cache.
2. `tenacity`'s `@retry` decorator auto-retries 5xx, 429, timeout up to 4 times. Exponential backoff with jitter.
3. TTL 1 hour. Deterministic tasks can go longer; time-sensitive answers shorter.

Now the FastAPI handler:

```python title="app/main.py" linenums="1" hl_lines="6 13 18"
from fastapi import FastAPI, HTTPException
from app.llm_client import call_llm

app = FastAPI()

@app.post("/chat")
async def chat(req: ChatRequest):                                       # (1)!
    if not await rate_ok(req.user_id):
        raise HTTPException(status_code=429, detail="rate limit")
    history = await session_load(req.user_id)
    messages = history + [{"role": "user", "content": req.text}]
    try:
        answer = await call_llm("claude-opus-4-7", messages)            # (2)!
    except Exception:
        answer = await fallback_response(req.text)                      # (3)!
    await session_append(req.user_id, req.text, answer)
    return {"answer": answer}
```

1. **Async handler** — one worker handles dozens of concurrent requests (processing others while waiting for the LLM).
2. Retry and cache live inside `call_llm`. The handler only knows business logic.
3. If all retries fail, fallback (e.g., smaller model, static response, "try again later").

---

## 5. Hands-on — the five stages one call survives

A PoC one-liner becomes a five-stage gauntlet in production.

![Resilience flow](../assets/diagrams/ch26-resilience.svg#only-light)
![Resilience flow](../assets/diagrams/ch26-resilience-dark.svg#only-dark)

| Stage | What | When |
|---|---|---|
| ① **Cache** | Same input → return immediately | Before call |
| ② **Rate Limit** | Per-user/tenant token bucket | Before call |
| ③ **LLM Call** | Provider API · explicit timeout | During call |
| ④ **Retry** | 5xx · 429 · timeout only · backoff + jitter | On failure |
| ⑤ **Circuit Breaker** | N consecutive failures → open · block for a period | Above retry |

**Circuit breaker** prevents "one provider dies, all workers retry forever, server melts." After 5 consecutive failures, stop calling that provider for 30 seconds — immediately fallback instead.

```python title="app/breaker.py" linenums="1"
import time

class CircuitBreaker:
    def __init__(self, threshold=5, cooldown=30):
        self.threshold, self.cooldown = threshold, cooldown
        self.failures, self.opened_at = 0, None

    def allow(self) -> bool:
        if self.opened_at and time.time() - self.opened_at < self.cooldown:
            return False                                                # (1)!
        return True

    def record(self, ok: bool):
        if ok:
            self.failures, self.opened_at = 0, None
        else:
            self.failures += 1
            if self.failures >= self.threshold:
                self.opened_at = time.time()                            # (2)!
```

1. When open, don't call. Jump straight to fallback.
2. Threshold hit → flip to open, auto-block for cooldown duration.

**Library choice**: use `pybreaker` · `purgatory` · cloud mesh (Istio) instead of rolling your own. Code above is concept only.

### Idempotency — user refresh doesn't double-execute

```python
@app.post("/refund")
async def refund(req: RefundRequest, idempotency_key: str = Header(...)):
    if cached := await cache.get(f"idem:{idempotency_key}"):
        return json.loads(cached)
    result = await process_refund(req)
    await cache.setex(f"idem:{idempotency_key}", 86400, json.dumps(result))
    return result
```

`Idempotency-Key` header is RFC standard. **Enforce it on every endpoint with side effects** (payments · emails · tool calls).

---

## 6. Common pitfalls

- **Everything is synchronous.** `def chat(...)` blocks one worker for 5 seconds per LLM call. Use async + ASGI (uvicorn/gunicorn) as default. Swap `requests` for `httpx.AsyncClient`.
- **LLM calls aren't cached.** 90% of FAQ questions are identical. One cache line cuts cost in half. But if `temperature > 0`, add seed to the cache key to preserve determinism.
- **Blind retries.** Retrying 4xx (validation errors) creates infinite loops. Limit retries to 5xx, 429, timeout only — like `retry_if_exception_type(APIStatusError)`.
- **Single provider.** Call Anthropic only? When they're down, you're down. Abstraction layer + at least one fallback (OpenAI/Bedrock) is non-negotiable.
- **Session in memory dict.** Two workers? Users ping different ones each request and lose conversation context. Redis or Postgres required. Solves memory leaks too.
- **No timeout.** SDK defaults are long or infinite. Explicitly set `timeout=30.0`. Threadless workers need the same timeout.
- **Health check calls LLM.** If `/health` makes an LLM request, external outages become your outages. `/health` should be lightweight ping only.

---

## 7. Operations checklist

- [ ] All external calls have timeout · retry · circuit breaker
- [ ] Cache hit rate tracked (target 30–70%, higher for deterministic tasks)
- [ ] Rate limit is per user_id (per IP fails in NAT)
- [ ] Side-effect endpoints enforce `Idempotency-Key`
- [ ] Session in external store (Redis/PG) · horizontal scaling works
- [ ] LLM provider abstraction + at least one fallback provider
- [ ] Async I/O consistent (no sync libraries blocking workers)
- [ ] `/health` and `/ready` split — ready checks dependencies, health doesn't
- [ ] Logs/trace searchable by user ID + request ID (Ch 27)
- [ ] PII policy enforced — never in cache or logs (Ch 28)

---

## 8. Exercises & next chapter

1. Take a PoC chat handler and refactor it to production using all five stages (cache · rate · retry · breaker · fallback). Make each stage its own function.
2. Define `LLMProvider` interface and write `AnthropicProvider` + `OpenAIProvider` implementations. Expose only `call(messages) → str`.
3. Add idempotency to a payment endpoint. Second call with same key returns cached response immediately.
4. Design three fallback policies for when circuit breaker opens. What do you show the user?

**Next** → [Ch 27 — Observability and Operations](27-observability.md) :material-arrow-right:  
These five layers only work if you can **see** them. Next chapter: tracing, logging, cost tracking, and the dashboards that keep production alive.

---

## Sources

- LangSmith · Langfuse architecture reference docs
- Stripe — *Designing robust and predictable APIs with idempotency*
- Anthropic SDK — `timeout` · streaming · retry options documentation
- *Release It!* (Michael Nygard) — circuit breaker · bulkhead patterns
