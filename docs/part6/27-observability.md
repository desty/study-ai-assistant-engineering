# Ch 27. 관측성과 운영

!!! abstract "이 챕터에서 배우는 것"
    - 로그·지표·트레이스의 **3 신호** — 왜 셋이 다 필요한가
    - **Trace span** 으로 한 요청을 분해 — LLM 콜이 차지하는 비중을 본다
    - **structured logging** + `trace_id` 일관 전파
    - LangSmith / Langfuse / OpenTelemetry 연결
    - Prompt **version registry** + A/B 롤아웃
    - 6대 함정 (로그만 = 관측 · trace 에 시크릿 · 단일 지표 · 카디널리티 폭주 · 표본만 보기 · prompt 버전 미관리)

!!! quote "전제"
    [Ch 26](26-prod-arch.md) 의 5 레이어. 가드레일(Ch 28) · 휴먼 개입(Ch 29) 의 결정을 **trace 한 줄로 추적**할 수 있어야 한다.

---

## 1. 개념 — 3 신호 없이 운영하지 말 것

PoC 의 관측은 보통 `print()` 입니다. Production 에선 부족합니다.

> **Logs** "무슨 일?" · **Metrics** "얼마나 자주/빨리?" · **Traces** "어디서 어디로?"

![관측의 3 신호](../assets/diagrams/ch27-three-signals.svg#only-light)
![관측의 3 신호](../assets/diagrams/ch27-three-signals-dark.svg#only-dark)

| 신호 | 단위 | 도구 | 답하는 질문 |
|---|---|---|---|
| **Logs** | event | ELK · CloudWatch · Loki | "이 사용자에게 정확히 무엇이 떨어졌나" |
| **Metrics** | timeseries | Prometheus · Datadog | "최근 1h 평균 지연이 평소 대비?" |
| **Traces** | span tree | LangSmith · Langfuse · OTel | "어떤 step 에서 시간/돈이 다 갔나" |

**핵심은 셋을 같은 키로 묶는 것**입니다. `trace_id` · `user_id` · `request_id` 가 모든 신호에 박혀 있어야, 한 ID 로 검색해 log·metric·trace 가 동시에 떨어집니다. 안 그러면 사용자 컴플레인이 들어와도 "그 시점에 무슨 일이 있었는지" 못 짜맞춤.

---

## 2. 왜 필요한가 — 한 신호로는 1/3 만 보인다

**로그만**: "에러 났다" 는 알지만 "얼마나 자주" 모름. 사용자가 1명만 영향이면 알람 OK, 1만 명이면 P0 — 메트릭 없이는 구분 불가.

**메트릭만**: "p95 가 5초로 튀었다" 는 알지만 **어느 사용자/어느 step** 에서 튀었는지 모름. trace 없이는 디버깅 시작점이 없음.

**트레이스만**: 한 요청은 보지만 **시스템 전체 트렌드** 는 못 봄. 메트릭이 없으면 SLO 측정 불가.

세 신호가 같은 trace_id 로 묶일 때만 **사용자 컴플레인 한 건 → trace_id 검색 → 로그+메트릭+span 트리 동시에 → 5분 안에 원인** 이 됩니다.

---

## 3. 어디에 쓰이는가 — 한 요청을 span 으로 펼치기

가장 먼저 만들 것: **요청 1건의 trace waterfall**.

![Trace waterfall](../assets/diagrams/ch27-trace-waterfall.svg#only-light)
![Trace waterfall](../assets/diagrams/ch27-trace-waterfall-dark.svg#only-dark)

| span | 시간 | 비용 | 비고 |
|---|---:|---:|---|
| HTTP request | 2580ms | — | 전체 |
| Auth · rate limit | 30ms | — | gateway |
| Input guardrails | 200ms | $0.0001 | Haiku 분류기 |
| Retrieval (전체) | 220ms | $0.0002 | 하위 3 span |
| ↳ embed query | 60ms | $0.00005 | |
| ↳ vector search | 90ms | — | Chroma |
| ↳ rerank | 50ms | $0.00015 | Cohere |
| **LLM call (Opus)** | **2000ms** | **$0.025** | **78% 시간 · 99% 비용** |
| Output guardrails | 70ms | $0.00005 | |

이 한 장이 **최적화 우선순위**를 즉시 알려줍니다 — LLM call 이 굵으면 Ch 30 (캐싱·라우팅), retrieval 이 굵으면 Ch 12 (rerank·캐시) 로.

---

## 4. 최소 예제 — Langfuse 연결과 structured log

### Langfuse 한 줄 트레이싱

```python title="app/llm_client.py" linenums="1" hl_lines="2 7 14"
from langfuse import observe, Langfuse
lf = Langfuse()                                                         # (1)!

@observe(as_type="generation")                                          # (2)!
async def call_llm(model: str, messages: list, *, trace_id: str) -> str:
    lf.update_current_observation(
        input=messages, model=model, metadata={"trace_id": trace_id},
    )
    resp = client.messages.create(model=model, messages=messages, max_tokens=1024)
    out = resp.content[0].text
    lf.update_current_observation(
        output=out,
        usage_details={"input": resp.usage.input_tokens,
                       "output": resp.usage.output_tokens},
    )
    return out
```

1. `LANGFUSE_*` 환경변수만 있으면 자동 전송. self-hosted 가능.
2. `@observe` 데코레이터가 span 을 자동 생성. 입출력·토큰 수·비용·지연이 함께 기록.

### Structured logging — JSON 한 줄

```python title="app/log.py" linenums="1"
import json, logging, time, contextvars

trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts": time.time(),
            "level": record.levelname,
            "msg": record.getMessage(),
            "trace_id": trace_id_var.get(),                              # (1)!
            "logger": record.name,
            **getattr(record, "extra", {}),
        }, ensure_ascii=False)

log = logging.getLogger("app")
h = logging.StreamHandler()
h.setFormatter(JsonFormatter())
log.addHandler(h); log.setLevel(logging.INFO)
```

1. `contextvars` 로 비동기 핸들러 안에서도 trace_id 자동 전파. FastAPI middleware 에서 한 번만 set.

### 메트릭 — Prometheus 게이지·카운터

```python
from prometheus_client import Counter, Histogram
LLM_CALLS = Counter("llm_calls_total", "LLM calls", ["model", "status"])
LLM_LATENCY = Histogram("llm_latency_seconds", "LLM latency", ["model"])

# 핸들러에서
LLM_CALLS.labels(model=model, status="ok").inc()
LLM_LATENCY.labels(model=model).observe(elapsed)
```

**라벨에 user_id 박지 마세요** — 카디널리티 폭주로 메트릭 DB 가 죽음. user_id 는 trace 에만.

---

## 5. 실전 — Prompt registry + A/B 롤아웃

운영에서 빈번한 사고: **프롬프트만 살짝 고쳤는데 회귀**. 대응은 **버전 관리**.

```python title="prompts/registry.py" linenums="1"
PROMPTS = {
    "answer_v1": {
        "version": "1.0.0",
        "owner": "alice",
        "template": "당신은 사내 IT 도우미...\n질문: {q}\n답:",
        "model": "claude-sonnet-4-6",
    },
    "answer_v2": {
        "version": "2.0.0",
        "owner": "bob",
        "template": "당신은 사내 IT 도우미. 모르는 건 모른다고...\n질문: {q}\n답:",
        "model": "claude-opus-4-7",
    },
}
```

**A/B 롤아웃**:

```python title="app/router.py" linenums="1"
import hashlib

def pick_prompt(user_id: str) -> str:
    bucket = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 100
    if bucket < 10:                                                      # (1)!
        return "answer_v2"
    return "answer_v1"

# 핸들러
prompt_key = pick_prompt(req.user_id)
log.info("prompt_pick", extra={"prompt_key": prompt_key, "user_id": req.user_id})
```

1. 10% 만 v2. trace 에 `prompt_key` 가 박히면 Langfuse 에서 v1/v2 평균 점수·지연·비용을 한 번에 비교 (Ch 17 LLM-as-Judge 의 pairwise 와 결합 가능).

### 핵심 지표 (Golden signals)

| 지표 | 목표값 예 | 장애 신호 |
|---|---|---|
| **Latency p95** | < 3.5s | p95 > 5s 5분 지속 |
| **Error rate** | < 1% | 5분 평균 > 3% |
| **Cost per request** | < $0.05 | 일일 평균 > $0.08 |
| **Cache hit rate** | > 30% | < 10% (캐시 키 깨짐 의심) |
| **Guardrail trigger rate** | < 5% | > 15% (false positive 의심) |
| **Approval queue depth** | < 50 | > 200 (운영팀 capacity 초과) |
| **Eval score (online)** | > baseline | baseline 대비 5pt 하락 |

**SLO** 는 위 중 3~4개로 좁혀서 정의. 너무 많으면 어느 것도 못 지킴.

---

## 6. 자주 깨지는 포인트

- **로그 있으면 관측 됨 착각**. 로그는 "이미 알고 있는 이벤트" 만 잡음. 트렌드·인과 관계는 메트릭/트레이스가 본다.
- **트레이스에 시크릿 유출**. API key · 토큰 · 사용자 비밀번호가 prompt 로 들어가면 Langfuse 에 평문 저장. **redact 미들웨어 필수** (regex + 가드레일 PII 와 동일 패턴).
- **카디널리티 폭주**. `Counter(..., labels=["user_id"])` 처럼 high-cardinality 라벨 → 메트릭 DB 가 OOM. **라벨은 enum 가능한 차원만** (model · status · region).
- **단일 지표만 보기**. p95 만 보면 p99 사고를 못 잡음. p50/p95/p99 + error rate + cost 를 같은 대시보드에.
- **표본만 보기 (sampling)**. trace 1% sampling 하면 희귀 에러가 안 잡힘. **에러는 100% · 정상은 1~10%** 의 tail-sampling.
- **Prompt 버전 관리 부재**. 누가 언제 무엇을 바꿨는지 모름 → 회귀 추적 불가. registry + git tag + trace 박힘.
- **알람 채널이 Slack 한 곳**. 새벽 P0 가 묻힘. PagerDuty 같은 escalation 정책 분리.
- **메트릭 dashboard 가 1개**. 누구나 보지만 누구도 책임 안 짐. **한 dashboard = 한 owner**.

---

## 7. 운영 체크리스트

- [ ] `trace_id` 가 모든 로그·메트릭·trace 에 박힘
- [ ] 시크릿 redact 미들웨어 (Langfuse 전송 전)
- [ ] 메트릭 라벨 카디널리티 통제 (user_id 금지)
- [ ] p50/p95/p99 latency · error rate · cost 4종 기본 대시보드
- [ ] tail sampling — 에러 100% · 정상 1~10%
- [ ] prompt registry + A/B 롤아웃 + trace 에 `prompt_key` 박힘
- [ ] SLO 3~4개로 좁혀 정의 · 위반 시 알람
- [ ] Dashboard 마다 owner 1명
- [ ] 알람 escalation (Slack → PagerDuty → 야간 oncall)
- [ ] Eval score (online) 트래킹 — 회귀 자동 감지
- [ ] 데이터 보존 정책 — log 30d · trace 7d · audit 7y (Ch 29)

---

## 8. 연습문제 & 다음 챕터

1. 사용자 컴플레인 한 건 ("답이 이상해요") 이 왔을 때, trace_id 만으로 5분 안에 원인을 좁히는 절차를 7단계로 설계하라.
2. 위 §3 의 trace waterfall 을 보고, 이 시스템에서 **가장 먼저 최적화해야 할 단계** 와 그 이유를 적어라. (Ch 30 의 답을 미리 시뮬레이션)
3. Prompt v2 를 10% → 100% 롤아웃하기 위한 단계별 게이트 (메트릭·임계·기간) 를 설계하라.
4. 한 메트릭 라벨에 `user_id` 를 넣었다는 사실을 발견했다. 즉시 수정 + 과거 데이터 정리 + 재발 방지의 3단 대응을 적어라.

**다음 챕터** — 이 trace 를 보면서 비용·지연을 줄이는 구체 기법. [Ch 30 비용·지연 최적화](30-cost-latency.md) 로.

---

## 원전

- *Distributed Systems Observability* — Cindy Sridharan (3 신호 정의 원전)
- Google SRE Book — *Monitoring Distributed Systems* (golden signals · SLO)
- Langfuse · LangSmith 공식 docs (LLM-specific tracing)
- OpenTelemetry — *Semantic Conventions for Generative AI* (2024~)
- Prometheus — best practices on label cardinality
