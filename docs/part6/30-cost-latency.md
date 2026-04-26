# Ch 30. 비용·지연 최적화

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part6/ch30_cost_latency.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **4 레버** — Prompt cache · Model routing · Batch API · Context 압축
    - 각 레버의 **실효 절감** 추정 (도메인별 차이 인지)
    - **Anthropic prompt caching** — 5분 TTL · 90% 입력 비용 할인
    - **모델 라우터** — Haiku/Sonnet/Opus 3 티어 · 분류기 비용 vs 절감
    - **Batch API** — 비실시간 50% 할인 운영 패턴
    - **Context 압축** — 이력 요약 · max_tokens 제어
    - 6대 함정 (캐시 키 깨짐 · 라우터 오분류 · 배치를 동기에 · 압축으로 정보 손실 · 측정 안 하고 적용 · prefix instability)
    - **Part 6 마무리** — 운영 졸업 상태 5종

!!! quote "전제"
    [Ch 27](27-observability.md) 의 trace waterfall 로 **무엇이 가장 굵은지** 본 상태. LLM call 이 78% 시간 · 99% 비용이라면 거기부터 깎는다.

---

## 1. 개념 — 한 번에 하나씩, 측정하면서

비용·지연 최적화는 **추측으로 시작하면 망합니다**. trace 와 메트릭이 먼저, 가설은 그 다음, 적용은 그 후, 측정은 항상.

> "Premature optimization is the root of all evil." — Knuth

LLM 시대에 적용하면: **trace 없이 캐싱부터 깔지 말 것**. 어디가 굵은지 모르고 깎으면 효과 없는 곳을 깎아 코드만 복잡해집니다.

![4 레버](../assets/diagrams/ch30-cost-techniques.svg#only-light)
![4 레버](../assets/diagrams/ch30-cost-techniques-dark.svg#only-dark)

| 레버 | 누구를 | 절감 (예시) | 위험 |
|---|---|---|---|
| **① Prompt cache** | 시스템·도구 정의 같은 정적 prefix | -40~50% 입력 비용 | 캐시 키 깨짐 → hit 0 |
| **② Model routing** | 쉬운 60% 를 Haiku 로 | -50~70% 평균 비용 | 분류기 오분류 |
| **③ Batch API** | 실시간 아닌 워크로드 | -50% 비용 | 응답 지연 (분~시간) |
| **④ Context 압축** | 긴 대화·문서 컨텍스트 | -30~70% 입력 토큰 | 정보 손실 |

수치는 예시. **첫 한 개로 보통 절반이 빠집니다** — 굳이 4개 다 쓸 필요 없음. 굵은 것부터.

---

## 2. 왜 필요한가 — 트래픽 ×10 의 함정

PoC 단계에서 한 요청 $0.025 는 작아 보입니다. 일 1000 호출 = $25/일 = $750/월. 견딜 만함.

트래픽이 ×10 가 되면? $7,500/월. ×100 면 $75,000/월. **사용자 1명당 단가가 같으면 매출이 비용을 못 따라잡습니다**. 마진이 음수가 되어가는 회사는 의외로 흔합니다.

지연도 같습니다. p95 가 5초면 **사용자 이탈률이 단계적으로 뜁니다** (Ch 7 의 TTFT 논의). 챗 UX 는 1초 미만 첫 토큰이 분기점.

---

## 3. 어디에 쓰이는가 — 어떤 워크로드에 어떤 레버

| 워크로드 | 1순위 레버 | 2순위 |
|---|---|---|
| 사내 챗봇 (시스템 프롬프트 길고 동일) | ① Prompt cache | ② Routing |
| 일반 챗 (사용자별 맥락 다름) | ② Routing | ④ Context 압축 |
| 야간 대량 문서 분류 | ③ Batch API | ② Routing |
| 긴 대화 어시스턴트 | ④ Context 압축 | ① Cache |
| 코드 리뷰 봇 (시스템 + 가이드라인 큼) | ① Cache | ② Routing |
| 실시간 검색 RAG | ② Routing | ① Cache (도구 정의) |

---

## 4. 최소 예제 — 4 레버 한 줄씩

### ① Anthropic Prompt Caching

```python title="app/cached_call.py" linenums="1" hl_lines="6 12"
from anthropic import Anthropic
client = Anthropic()

resp = client.messages.create(
    model="claude-sonnet-4-6",
    system=[
        {"type": "text", "text": LONG_SYSTEM_PROMPT,                    # (1)!
         "cache_control": {"type": "ephemeral"}},
    ],
    tools=[
        *TOOLS,                                                          # (2)!
    ],
    messages=[{"role": "user", "content": user_q}],
    extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
)
# resp.usage.cache_read_input_tokens · cache_creation_input_tokens
```

1. `cache_control` 박힌 블록부터 **이전까지의 모든 prefix** 가 캐시 단위. 시스템 프롬프트가 5~10k 토큰이면 큰 절감.
2. tools 정의는 자동 캐시 (블록 자체가 정적이면). 도구 추가/제거 시 cache miss.

**TTL 5분**. 5분 안에 후속 호출이 와야 hit. 트래픽이 sparse 하면 효과 작음.

### ② Model Router

![Model router](../assets/diagrams/ch30-model-router.svg#only-light)
![Model router](../assets/diagrams/ch30-model-router-dark.svg#only-dark)

```python title="app/router.py" linenums="1"
ROUTER_PROMPT = """다음 질의 난이도를 EASY/MED/HARD 한 단어로:
질의: {q}
기준: EASY=FAQ·요약 · MED=일반 답변 · HARD=다단계 추론·코드"""

async def route(q: str) -> str:
    out = await call_llm("claude-haiku-4-5",
                         [{"role": "user", "content": ROUTER_PROMPT.format(q=q)}])
    tier = out.strip().split()[0].upper()
    return {
        "EASY": "claude-haiku-4-5",
        "MED":  "claude-sonnet-4-6",
        "HARD": "claude-opus-4-7",
    }.get(tier, "claude-sonnet-4-6")
```

**실효 평균** (60% Haiku · 30% Sonnet · 10% Opus) ≈ $0.0073/호출. baseline Opus $0.030 대비 **24%**.

**핵심**: 분류기 자체도 비용 (~$0.0005). 분류기가 본 LLM 보다 10배 싸야 의미 있음. 그리고 **분류 정확도** 를 평가셋(Ch 16) 에서 별도 측정 — 오분류 시 품질 저하.

### ③ Batch API

```python
# Anthropic Message Batches · OpenAI Batch · 50% 할인
batch = client.messages.batches.create(requests=[
    {"custom_id": f"job-{i}", "params": {"model": "...", "messages": [...]}}
    for i in range(1000)
])
# 응답은 분~24시간 안에. 수동 polling 또는 webhook
```

**비실시간 워크로드만**: 야간 분류·요약·임베딩 인덱싱·평가 자동 채점. 사용자 대화에 쓰면 안 됨.

### ④ Context 압축 — 대화 이력 요약

```python title="app/compress.py"
async def compress_history(history: list[dict], keep_last_n: int = 4) -> list[dict]:
    if len(history) <= keep_last_n + 2:
        return history
    older = history[:-keep_last_n]
    summary = await call_llm("claude-haiku-4-5", [{
        "role": "user",
        "content": f"다음 대화를 5줄 이내 사실 위주 요약:\n\n{render(older)}"
    }])
    return [{"role": "system", "content": f"이전 대화 요약:\n{summary}"}] + history[-keep_last_n:]
```

긴 대화에서 입력 토큰 폭주를 막음. **단점**: 요약이 정보 손실 → 사용자 선호 같은 "잊으면 안 되는 사실" 은 별도 메모리(Ch 24) 에.

추가 기법:

- `max_tokens` 를 적정값으로 제한 — Opus 가 2000 토큰 답을 안 해도 되는데 풀로 쓰면 비싼 토큰 출력.
- system prompt 정리 — 안 쓰는 지시문 제거.
- few-shot 예제 N 개 줄이기 (Ch 5).

---

## 5. 실전 — 적용 순서와 측정

**적용 순서**:

1. **trace waterfall 로 굵은 막대 식별** (Ch 27).
2. **첫 레버 적용 + A/B 측정** (Ch 27 §5 의 prompt 롤아웃 패턴 그대로).
3. 메트릭 7종 (latency p95, cost/req, eval score 등) **회귀 없는지 확인**.
4. 문제 없으면 100% 롤아웃, 다음 레버.
5. **eval score 가 떨어지면 즉시 롤백**.

**누적 효과** (예시):

| 단계 | 평균 비용 | p95 latency | eval score |
|---|---:|---:|---:|
| Baseline (Opus only) | $0.025 | 2400ms | 8.4 |
| + Prompt cache | $0.015 | 1900ms | 8.4 |
| + Model routing | $0.008 | 1200ms | 8.2 (-0.2) |
| + max_tokens 제한 | $0.007 | 1000ms | 8.2 |

**eval score 0.2 하락이 비용 70% 절감 가치가 있는가?** 는 제품 결정. 단순 비용만 보지 말 것.

### Cost dashboard

| 패널 | 측정 |
|---|---|
| Cost / day | 일별 총 비용 추세 |
| Cost / request (model 별) | Haiku/Sonnet/Opus 분포 |
| Cache hit rate | prompt cache · LLM cache 분리 |
| Token usage histogram | input/output 비대칭 발견 |
| Router decision mix | Easy/Med/Hard 비율 (drift 감지) |
| p50/p95 latency by model | tier 별 SLO |

### Caching 키 안정성 — prefix instability

Prompt cache 의 가장 흔한 사고: **시스템 프롬프트 안에 동적 값** (현재 시각, 사용자 이름) 이 들어감 → 매 호출이 다른 prefix → cache miss 100%.

**규칙**: `cache_control` 박힌 블록 **앞쪽**은 100% 결정론. 동적 값은 user message 또는 별도 블록으로.

---

## 6. 자주 깨지는 포인트

- **캐시 키 깨짐**. 시스템 프롬프트 안에 timestamp · uuid · 사용자명 → hit rate 0%. cache hit metric 이 0 으로 떨어지면 즉시 의심.
- **라우터 오분류**. HARD 를 EASY 로 라우팅 → 품질 저하. 라우팅 정확도 평가셋 별도 + 주기적 점검.
- **배치 API 를 동기에**. 사용자 대기 시간이 분 단위가 되면 UX 망가짐. 배치는 **사용자가 기다리지 않는 작업** 에만.
- **압축이 정보 손실**. 사용자 "내 이름은 alice" → 요약에서 누락 → 다음 턴에 모름. 메모리(Ch 24) 와 분리.
- **측정 없이 적용**. 캐시 깔고 만족, hit rate 안 봄 → 사실 0%. 메트릭이 먼저.
- **모든 레버를 동시에**. 회귀 발생 시 어느 레버가 원인인지 못 찾음. **하나씩 + A/B + 메트릭**.
- **max_tokens 너무 짧게**. 답이 잘림 → 사용자 컴플레인. eval 에서 잘림 비율(truncation rate) 메트릭.
- **Provider 단가 변경에 둔감**. 분기마다 단가 바뀜 → 비용 모델 stale. 자동 동기화 또는 분기 리뷰.

---

## 7. 운영 체크리스트

- [ ] trace waterfall 에서 가장 굵은 막대를 1순위로 공략
- [ ] Prompt cache 의 cache_control 앞쪽이 100% 결정론
- [ ] Cache hit rate 일 단위 모니터링 (목표 > 30%)
- [ ] Model router 의 분류 정확도 평가셋 분리 측정
- [ ] Router decision mix 메트릭 (drift 감지)
- [ ] Batch API 는 비실시간 워크로드에만
- [ ] Context 압축은 메모리(Ch 24) 와 분리, 손실 위험 인지
- [ ] max_tokens 제한 + truncation rate 메트릭
- [ ] 적용 시 A/B + eval score 회귀 게이트
- [ ] Cost dashboard 6 패널 (위 §5)
- [ ] Provider 단가 변경 자동 반영
- [ ] 비용 알람 (일일 한도 + 전일 대비 ×2 시 page)

---

## 8. 연습문제 & Part 6 마무리

1. Ch 27 의 trace waterfall (LLM 78% 시간 · 99% 비용) 을 받아 4 레버 중 어느 것을 1·2 순위로 적용할 것인가? 이유와 함께.
2. 시스템 프롬프트에 "오늘 날짜는 {today}" 가 박혀 있어 cache hit 0% 라는 진단이 나왔다. 캐시 깨지지 않는 형태로 재설계하라.
3. Model router 정확도 평가셋 100개를 만들 때, 어느 비율 (Easy/Med/Hard) 로 샘플링할 것인지 + 라벨링 가이드 3줄.
4. Batch API 50% 할인을 받기 위해 우리 서비스에서 비실시간으로 옮길 수 있는 워크로드 3개를 식별하라.

---

## Part 6 마무리 — 운영 졸업 상태 5종

Part 6 5챕터를 끝낸 시점에서 가져야 할 산출물:

| # | 산출물 | 어느 챕터 |
|---|---|---|
| ① | **5 레이어 아키텍처 문서** + 다이어그램 | Ch 26 |
| ② | **trace + 3 신호 대시보드** (한 trace_id 로 묶임) | Ch 27 |
| ③ | **가드레일 7종 체크리스트** + 각 위반 응답 정책 | Ch 28 |
| ④ | **승인 큐 + audit log** (LangGraph interrupt 와 연결) | Ch 29 |
| ⑤ | **비용·지연 4 레버 적용 기록** + 회귀 게이트 | Ch 30 |

이 5개를 가지고 다음 단계는:

- **Part 7**: 모델·파인튜닝 (운영하다 보면 작은 모델로 옮길 필요가 생김 — 이때 fine-tune 의 자리)
- **캡스톤**: Self-Improving Assistant — Part 1~6 전부를 하나의 시스템으로 통합

**다음 Part** → [Part 7 모델·파인튜닝](../part7/31-model-arch.md) 으로.

---

## 원전

- Anthropic — *Prompt Caching* docs (2024)
- Anthropic — *Message Batches API* docs
- OpenAI — *Batch API* docs
- *Designing Data-Intensive Applications* — 비용·지연 트레이드오프 일반론
- Google SRE — *The Site Reliability Workbook* (capacity planning · cost)
