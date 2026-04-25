# Ch 26. Production 아키텍처

!!! abstract "이 챕터에서 배우는 것"
    - **PoC 와 Production 의 차이** — 무엇이 추가로 필요한가
    - **5개 레이어**로 분리: API · LLM · Retrieval · Session · Observability
    - 한 번의 LLM 호출을 **살아남게** 하는 5단계 (cache · rate limit · retry · breaker · fallback)
    - **FastAPI · async · Redis · tenacity** 로 짜는 최소 골격
    - 동기/비동기 결정 · 멱등성 · 백프레셔
    - 5대 함정 (모두 동기 · 캐시 미사용 · 무작정 재시도 · 단일 provider · 세션을 메모리에)

!!! quote "전제"
    [Part 5](../part5/20-what-is-agent.md) 까지의 단일 agent · LangGraph · 메모리. 이제 **여러 사용자가 동시에** 부르고, **장애가 항상 일어난다**는 가정으로 다시 짠다.

---

## 1. 개념 — PoC 가 production 이 되려면

PoC 는 보통 이렇습니다.

```python
@app.post("/chat")
def chat(msg: str):
    return client.messages.create(model="...", messages=[{"role": "user", "content": msg}])
```

이 코드가 실패하는 순간:

- **2명이 동시에 부름** — 동기 핸들러가 한 줄로 줄 섬
- **provider 가 30초 멈춤** — 우리 서버 워커도 30초 멈춤
- **rate limit 도달** — 모든 사용자에게 500 에러
- **같은 질문 100번** — 매번 토큰 비용 발생
- **trace 없음** — 무엇이 느려졌는지 알 수 없음

Production 아키텍처는 이 다섯 문제를 **레이어로 분리**해서 푸는 일입니다.

![Production 아키텍처](../assets/diagrams/ch26-prod-arch.svg#only-light)
![Production 아키텍처](../assets/diagrams/ch26-prod-arch-dark.svg#only-dark)

| 레이어 | 책임 | 실패 시 영향 |
|---|---|---|
| **API Gateway** | 인증 · 라우팅 · 레이트리밋 · async | 전체 정지 |
| **LLM Layer** | provider 추상화 · 캐시 · 재시도 · 라우팅 | 답변 품질 / 비용 |
| **Retrieval Layer** | 벡터 + lexical · 임베딩 캐시 · reranker | 답변 정확도 |
| **Session Store** | thread state · prefs · idempotency | 대화 단절 |
| **Observability** | trace · log · cost · latency | 보이지 않는 장애 |

핵심은 **각 레이어가 독립적으로 실패하고 회복**한다는 점. retrieval 이 죽어도 LLM 만으로 답하거나, LLM provider 가 죽으면 다른 provider 로 라우팅.

---

## 2. 왜 필요한가 — 한 핸들러에 다 넣으면 안 되는 이유

**① 동시성**. 한 사용자의 LLM 호출이 5초면, 동기 워커 4개로는 초당 0.8 req. async + connection pool 이 있어야 1워커당 50+ req.

**② 격리**. 캐시·재시도·트레이싱 로직이 비즈니스 코드와 섞이면 핸들러가 200줄이 되고, 한 군데 고치다 다른 곳을 깬다.

**③ 다중 provider**. Anthropic 이 죽었을 때 OpenAI 로 즉시 전환하려면, 호출하는 코드가 provider 를 모르도록 추상화해야 함.

**④ 비용 가시성**. trace·로그가 한 곳으로 모이지 않으면 "어떤 endpoint 가 비싼지" 모름. 비용 폭주를 알아채는 게 1주일 늦어짐.

**⑤ 멱등성**. 사용자가 새로고침하면 같은 요청이 두 번 들어옴. 결제·이메일 같은 부수효과 액션은 두 번 실행되면 안 됨.

---

## 3. 어디에 쓰이는가 — 3가지 전형 패턴

| 시나리오 | 핵심 결정 |
|---|---|
| **동기 챗 (회신 5초 내)** | FastAPI async + 스트리밍 + Redis 세션 |
| **백그라운드 분석 (10초+)** | 큐 (Celery/SQS) + Webhook 알림 + idempotency key |
| **에이전트 워크플로우** | LangGraph + checkpointer + interrupt (Ch 23) |

대부분 제품은 **동기 챗 + 백그라운드 큐** 두 트랙을 같이 운영합니다. 챗은 실시간, 무거운 작업은 큐로.

---

## 4. 최소 예제 — FastAPI + tenacity + Redis

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

1. 캐시 키는 모델 + 메시지 전체 해시. 한 글자만 달라져도 다른 키 → 의도된 변동성은 캐시 무력화.
2. `tenacity` 의 `@retry` 가 5xx · 429 · timeout 을 4회까지 자동 재시도. exponential backoff + jitter.
3. TTL 1시간. 결정론적 작업은 길게, 시간 민감한 답변은 짧게.

다음으로 FastAPI 핸들러:

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

1. **async 핸들러** — 한 워커가 동시에 수십 요청을 다룸 (LLM 응답 대기 동안 다른 요청 처리).
2. 재시도·캐시는 `call_llm` 안에서 끝남. 핸들러는 비즈니스 로직만.
3. 모든 재시도 실패 시 폴백 (예: 작은 모델, 정적 답변, "잠시 후 다시" 메시지).

---

## 5. 실전 — 한 호출이 살아남는 5단계

PoC 의 한 줄 호출은 production 에서 다섯 정책을 통과합니다.

![Resilience flow](../assets/diagrams/ch26-resilience.svg#only-light)
![Resilience flow](../assets/diagrams/ch26-resilience-dark.svg#only-dark)

| 단계 | 무엇 | 시점 |
|---|---|---|
| ① **Cache** | 같은 입력 → 즉시 반환 | 호출 전 |
| ② **Rate Limit** | user/tenant 단위 token bucket | 호출 전 |
| ③ **LLM Call** | provider API · timeout 명시 | 호출 중 |
| ④ **Retry** | 5xx · 429 · timeout 만 · backoff + jitter | 실패 후 |
| ⑤ **Circuit Breaker** | 연속 실패 N회 → open · 일정 시간 차단 | retry 위 |

**Circuit breaker** 는 "한 provider 가 죽었을 때 전체 워커가 retry 로 멈추는 것" 을 막습니다. 5회 연속 실패면 30초 동안 그 provider 호출 자체를 건너뛰고 즉시 폴백.

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

1. open 상태일 때는 호출하지 않음. 즉시 폴백으로.
2. 임계 도달 시 open 으로 전환. cooldown 동안 자동 차단.

**라이브러리 선택**: 직접 구현하지 말고 `pybreaker` · `purgatory` · 클라우드 메시 (Istio) 의 기능 사용. 위 코드는 개념용.

### 멱등성 — 새로고침이 두 번 실행을 만들지 않게

```python
@app.post("/refund")
async def refund(req: RefundRequest, idempotency_key: str = Header(...)):
    if cached := await cache.get(f"idem:{idempotency_key}"):
        return json.loads(cached)
    result = await process_refund(req)
    await cache.setex(f"idem:{idempotency_key}", 86400, json.dumps(result))
    return result
```

`Idempotency-Key` 헤더는 RFC 표준. **부수효과가 있는 모든 endpoint** (결제·이메일·툴 콜) 에 강제.

---

## 6. 자주 깨지는 포인트

- **모든 걸 동기로**. `def chat(...)` 로 짜면 LLM 5초 동안 워커 1개 점유. async + ASGI (uvicorn/gunicorn) 가 기본. `requests` 대신 `httpx.AsyncClient`.
- **LLM 콜 캐시 안 함**. FAQ 질문은 90% 가 동일. 캐시 한 줄이면 비용 절반. 단, **temperature > 0 이면 캐시 키에 seed 도 포함**해야 결정론.
- **무작정 재시도**. 4xx (validation 에러) 도 재시도하면 무한 반복. `retry_if_exception_type(APIStatusError)` 처럼 5xx · 429 · timeout 으로 한정.
- **단일 provider**. Anthropic 만 호출하면 그쪽이 죽을 때 우리도 죽음. 추상화 레이어를 두고 OpenAI/Bedrock 폴백을 적어도 1개.
- **세션을 in-memory dict 에**. 워커가 2개 되는 순간 사용자가 매번 다른 워커에 붙어 대화가 끊김. Redis · Postgres 같은 외부 저장소 필수. 메모리 누수도 동시 해결.
- **timeout 명시 안 함**. SDK 기본은 길거나 무한. `timeout=30.0` 등 명시. 리트리스 워커도 같은 timeout.
- **Health check 가 LLM 호출**. `/health` 가 LLM 을 부르면 외부 장애가 곧 우리 health check 실패. 가벼운 ping 만.

---

## 7. 운영 체크리스트

- [ ] 모든 외부 호출에 timeout · retry · circuit breaker
- [ ] 캐시 hit rate 모니터링 (목표 30~70%, 결정론 기능은 더 높게)
- [ ] Rate limit 키가 user_id 단위 (IP 단위는 NAT 환경에서 깨짐)
- [ ] 부수효과 endpoint 에 `Idempotency-Key` 강제
- [ ] 세션이 외부 저장소 (Redis/PG) · 워커 수평 확장 가능
- [ ] LLM provider 추상화 + 최소 1개 폴백 provider
- [ ] async I/O 일관 (동기 라이브러리 섞이면 워커 블로킹)
- [ ] `/health` · `/ready` 분리 — ready 만이 deps 까지 본다
- [ ] 로그·trace 가 사용자 ID + request ID 로 검색 가능 (Ch 27)
- [ ] PII 가 캐시·로그에 들어가지 않는지 정책 (Ch 28)

---

## 8. 연습문제 & 다음 챕터

1. PoC 챗 핸들러를 받아 5단계 (cache · rate · retry · breaker · fallback) 를 적용한 production 버전으로 리팩터링하라. 각 단계가 독립 함수가 되도록.
2. provider 추상화 인터페이스 `LLMProvider` 를 정의하고 `AnthropicProvider` · `OpenAIProvider` 두 구현을 만들어라. `call(messages) → str` 만 노출.
3. 결제 endpoint 에 idempotency 를 적용하라. 같은 키로 두 번 호출 시 두 번째는 캐시된 응답을 즉시 반환해야 한다.
4. circuit breaker 가 open 됐을 때 사용자에게 무엇을 보여줄지 폴백 정책 3개를 적어라.

**다음 챕터** — 이 다섯 레이어가 살아 있는지 어떻게 보는가. [Ch 27 관측성과 운영](27-observability.md) 으로.

---

## 원전

- LangSmith · Langfuse 아키텍처 레퍼런스 docs
- Stripe — *Designing robust and predictable APIs with idempotency*
- Anthropic SDK — `timeout` · streaming · retry 옵션 docs
- *Release It!* (Michael Nygard) — circuit breaker · bulkhead 패턴 원전
