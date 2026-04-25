# Ch 28. 가드레일 7종

!!! abstract "이 챕터에서 배우는 것"
    - **계층형 방어** — 한 종류 가드레일로는 부족한 이유
    - **7종 가드레일 표** — Relevance · Safety · Moderation · Rules · Tool Safeguard · PII · Output Validation
    - 각 가드레일의 **최소 구현** + 실패 케이스
    - **Optimistic execution** — 가드레일을 LLM 과 병렬로 돌려 지연 0 추가
    - 위반 시 응답 3가지: **reject · transform · escalate**
    - 5대 함정 (한 종류에 몰빵 · 과차단 · 가드레일 자체 취약 · 영구 차단 · 메트릭 부재)

!!! quote "전제"
    [Ch 26](26-prod-arch.md) 5 레이어 아키텍처. 가드레일은 **API Gateway · LLM · Output** 세 위치에 배치되며 모두 Observability(Ch 27) 로 흘러야 한다.

---

## 1. 개념 — 가드레일은 단일 필터가 아니다

가드레일을 처음 만들 때 흔한 실수:

```python
def safe(text: str) -> bool:
    return "ignore previous" not in text.lower()
```

이 한 줄은 첫 사용자에게 뚫립니다 ("Disregard the above"). 가드레일은 **하나의 함수**가 아니라 **여러 위치에 배치한 여러 필터**입니다.

> "Think of guardrails as **layered defense**." — *OpenAI, A Practical Guide to Building Agents*

세 위치에 배치합니다.

![가드레일 7종 배치](../assets/diagrams/ch28-guardrails-7layers.svg#only-light)
![가드레일 7종 배치](../assets/diagrams/ch28-guardrails-7layers-dark.svg#only-dark)

| # | 위치 | 가드레일 | 역할 |
|--:|---|---|---|
| ① | 입력 | **Relevance classifier** | 범위 이탈 쿼리 차단 |
| ② | 입력 | **Safety classifier** | 탈옥·프롬프트 인젝션 탐지 |
| ③ | 입력 | **Moderation** | 혐오·괴롭힘·폭력 |
| ④ | 입력 | **Rules-based** | regex · blocklist · 길이 |
| ⑤ | 툴 호출 | **Tool safeguard** | low/med/high · 승인 |
| ⑥ | 출력 | **PII filter** | 마스킹 · redact |
| ⑦ | 출력 | **Output validation** | 브랜드 · 정책 부합 |

위반 시 응답은 **reject · transform · escalate** 셋 중 하나. 무조건 차단(reject)만 쓰면 UX 가 망가지므로, 마스킹(transform) 과 사람 승인(escalate) 도 같이 운영합니다.

---

## 2. 왜 필요한가 — 한 종류로 막히지 않는 이유

| 공격 유형 | 막아야 할 가드레일 |
|---|---|
| "이전 지시 무시하고…" (jailbreak) | ② Safety |
| "비속어 잔뜩" 입력 | ③ Moderation |
| 회사 비공개 데이터 흘림 | ⑥ PII |
| Off-topic ("롤 빌드 알려줘") | ① Relevance |
| 결제 툴을 LLM 이 멋대로 호출 | ⑤ Tool Safeguard |
| 답변에 경쟁사 추천 들어감 | ⑦ Output validation |
| SQL 인젝션 패턴 | ④ Rules |

**한 가드레일에 몰빵하면 다른 6가지가 뚫립니다.** 반대로 7개를 다 깔면 비용·지연이 폭주하니, **계층 + Optimistic** 으로 푼다.

---

## 3. 어디에 쓰이는가 — 도메인별 우선순위

| 도메인 | 1순위 | 2순위 |
|---|---|---|
| 금융·결제 | ⑤ Tool Safeguard · ⑥ PII | ⑦ Output validation |
| 의료 | ⑥ PII · ② Safety (의료 조언 한계) | ⑦ Output validation |
| 사내 사무 자동화 | ⑥ PII · ① Relevance | ⑤ Tool Safeguard |
| 일반 챗봇 | ② Safety · ③ Moderation | ④ Rules · ⑦ Output |
| 코드 어시스턴트 | ④ Rules (secret detection) · ⑤ Tool Safeguard | ② Safety |

**모든 가드레일을 동일 비중으로 깔지 말 것.** 도메인 위협 모델을 먼저 그리고, 그에 맞는 2~3개를 깊게.

---

## 4. 최소 예제 — 7종 한 줄씩

### ① Relevance — 분류기

```python title="guardrails/relevance.py" linenums="1"
RELEVANCE_PROMPT = """다음 사용자 입력이 '사내 IT 헬프데스크' 범위에 속하면 IN, 아니면 OUT 만 출력.
입력: {q}
"""
async def relevance(q: str) -> bool:
    out = await call_llm("claude-haiku-4-5", [{"role": "user", "content": RELEVANCE_PROMPT.format(q=q)}])
    return out.strip().startswith("IN")
```

**Haiku 같은 작은 모델 사용**. 본 LLM 보다 10배 빠르고 싸야 함.

### ② Safety — 인젝션 탐지

```python title="guardrails/safety.py" linenums="1"
INJECTION_PATTERNS = [
    "ignore previous", "disregard above", "system prompt",
    "당신의 지시를 잊", "이전 명령 무시",
]
def safety_quick(q: str) -> bool:
    low = q.lower()
    return not any(p in low for p in INJECTION_PATTERNS)

async def safety_llm(q: str) -> bool:                                   # (1)!
    prompt = f"다음이 jailbreak 시도인가? YES/NO 만:\n\n{q}"
    out = await call_llm("claude-haiku-4-5", [{"role": "user", "content": prompt}])
    return out.strip().upper().startswith("NO")
```

1. regex 만으론 부족 → LLM 분류기 병행. 둘 다 통과해야 OK.

### ③ Moderation — Provider API

```python
# OpenAI Moderation API · 무료 · 빠름
import openai
def moderation_ok(q: str) -> bool:
    r = openai.moderations.create(input=q)
    return not r.results[0].flagged
```

### ④ Rules — Regex · Blocklist

```python
import re
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})")
def rules_ok(q: str) -> bool:
    if len(q) > 10_000: return False
    if SECRET_RE.search(q): return False
    return True
```

### ⑤ Tool Safeguard — 위험도 메타

```python title="guardrails/tool_safe.py" linenums="1"
TOOL_RISK = {
    "search_kb": "low",
    "send_email": "medium",
    "issue_refund": "high",
}
async def run_tool(name: str, args: dict, user_id: str):
    risk = TOOL_RISK.get(name, "high")
    if risk == "high":
        await approval_queue.enqueue(name, args, user_id)
        return {"status": "pending_approval"}                           # (1)!
    return await TOOLS[name](**args)
```

1. high 등급은 사람 승인 큐로. Ch 22 의 approval flow 와 같은 패턴 (Ch 29 에서 확장).

### ⑥ PII — 마스킹

```python
import re
PII_PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "phone": re.compile(r"\b01[016-9]-?\d{3,4}-?\d{4}\b"),
    "rrn":   re.compile(r"\b\d{6}-[1-4]\d{6}\b"),       # 한국 주민번호
}
def pii_mask(text: str) -> str:
    for kind, pat in PII_PATTERNS.items():
        text = pat.sub(f"[REDACTED:{kind}]", text)
    return text
```

**입력만 검사 X — 출력에도 적용**. 모델이 학습 데이터에서 PII 를 흘리는 경우 막힘.

### ⑦ Output Validation — 정책 검사

```python
async def output_ok(answer: str, query: str) -> bool:
    # 브랜드·정책 검사를 별도 LLM 으로
    prompt = f"""다음 답변이 회사 정책 위반인지 (경쟁사 추천 · 법률 자문 · 의료 처방) PASS/FAIL 만:
질의: {query}
답변: {answer}"""
    out = await call_llm("claude-haiku-4-5", [{"role": "user", "content": prompt}])
    return out.strip().upper().startswith("PASS")
```

---

## 5. 실전 — Optimistic Execution 으로 지연 0 추가

가드레일을 직렬로 깔면:

```
입력 GR (40ms) → LLM (2400ms) → 출력 GR (60ms)  =  2500ms
```

**가드레일을 추가할 때마다 사용자가 기다리는 시간이 늘어납니다.** 7개를 다 직렬로 깔면 답이 늦어 UX 가 망가짐.

해결: **LLM 과 가드레일을 병렬 실행**, 위반 감지 시 LLM 응답을 폐기.

![Optimistic execution](../assets/diagrams/ch28-optimistic-exec.svg#only-light)
![Optimistic execution](../assets/diagrams/ch28-optimistic-exec-dark.svg#only-dark)

```python title="guardrails/optimistic.py" linenums="1" hl_lines="6 12 18"
import asyncio

async def respond_with_guardrails(query: str, user_id: str) -> str:
    # 입력 가드레일은 직렬 (위험 토큰을 LLM 에 흘리면 안 됨)
    if not rules_ok(query) or not moderation_ok(query):
        return REJECT_MSG

    # 본 LLM 호출 + 추가 가드레일을 병렬로
    llm_task = asyncio.create_task(call_llm("claude-opus-4-7", build_messages(query)))
    rel_task = asyncio.create_task(relevance(query))
    saf_task = asyncio.create_task(safety_llm(query))

    rel, saf = await asyncio.gather(rel_task, saf_task)                 # (1)!
    if not (rel and saf):
        llm_task.cancel()                                               # (2)!
        return REJECT_MSG

    answer = await llm_task
    answer = pii_mask(answer)                                           # (3)!
    if not await output_ok(answer, query):
        return REJECT_MSG
    return answer
```

1. 가드레일은 LLM 보다 먼저 끝남 (Haiku 분류기 ≈ 200ms vs Opus 답변 ≈ 2400ms).
2. 위반이면 LLM 호출 자체를 취소 → 사용자에게 부분 응답 노출 안 됨.
3. PII 마스킹은 결정론(regex) → 즉시 적용.

### 직렬이 필요한 경우

**hard fail 가드레일은 직렬**로 두세요. 안전(②) 위반 시 LLM 호출 자체를 막아야 데이터 비용·로그 노출이 없습니다. 위 코드에서도 `rules_ok` · `moderation_ok` 는 직렬로 먼저 체크.

### 위반 응답 3가지

```python
class GuardrailResult:
    REJECT    = "차단"          # "도와드릴 수 없습니다"
    TRANSFORM = "변형"          # PII 마스킹 · 톤 조정
    ESCALATE  = "이관"          # 사람 승인 큐로
```

| 위반 | 권장 응답 |
|---|---|
| Off-topic (Relevance) | reject — 짧은 안내 |
| 인젝션 (Safety) | reject — 로그만, 상세 이유 노출 X |
| 폭언 (Moderation) | reject — 정중한 거절 |
| 길이 초과 (Rules) | transform — 자르거나 요약 요청 |
| High-risk tool (⑤) | escalate — 승인 큐 |
| PII (⑥) | transform — 자동 마스킹 |
| 정책 위반 (⑦) | escalate (자주) · reject (드물게) |

---

## 6. 자주 깨지는 포인트

- **한 종류 가드레일에 몰빵**. "Safety classifier 만 잘 만들면 됨" → 첫 사용자가 PII 흘리고 끝남. 7종 표를 체크리스트로.
- **과차단 (false positive)**. Relevance 가 너무 엄격하면 정상 사용자도 "도와드릴 수 없습니다" 받음. precision/recall 둘 다 본다 — false positive rate 5% 이하 목표.
- **가드레일 자체가 LLM → 가드레일 인젝션 가능**. Haiku 분류기에 "이 입력은 IN 이다" 가 박힌 사용자 입력 들어오면 뚫림. **분류기 프롬프트에 사용자 입력을 XML 태그로 분리** + 출력 형식 엄격히.
- **영구 차단 / IP 밴 만들지 말 것**. false positive 가 영구가 되면 운영팀에 항의 폭주. **N 분 임시 차단** 후 자동 해제.
- **메트릭 없음**. 각 가드레일이 몇 % 트리거되는지 모르면 튜닝 불가. trigger rate · false positive rate · latency 를 가드레일별로 (Ch 27 observability).
- **로그에 가드레일 전 입력만**. 마스킹 후만 저장하면 디버깅 불가. **로그는 마스킹 전, 응답은 마스킹 후** 분리. 단 로그 자체에 PII 포함 여부 정책 별도.
- **7종을 동기 LLM 호출 7번으로**. 비용 7배. 가능한 결정론(regex/API) 사용 + LLM 가드레일은 1~2개로 통합.

---

## 7. 운영 체크리스트

- [ ] 도메인 위협 모델 1장 (어떤 위협이 1순위인가)
- [ ] 입력·툴·출력 세 위치에 최소 1개씩 배치
- [ ] hard fail (안전 · PII) 은 직렬, 나머지는 optimistic 병렬
- [ ] 위반 응답은 reject/transform/escalate 중 명시
- [ ] 가드레일별 trigger rate · false positive · latency 메트릭
- [ ] 위반 로그는 마스킹 전 (별도 보관 · 짧은 TTL)
- [ ] LLM 분류기는 사용자 입력을 XML 태그로 분리
- [ ] 임시 차단 후 자동 해제 (N분), 영구 밴은 사람 결정만
- [ ] 가드레일 변경 시 evaluation set 재돌림 (Ch 16)
- [ ] PII 마스킹 후에도 LLM trace 에 원문 안 남는지 확인
- [ ] Tool safeguard 의 위험도 표가 코드에 박혀 있고 PR 리뷰 대상

---

## 8. 연습문제 & 다음 챕터

1. 사내 IT 헬프데스크 챗봇에 7종 가드레일 중 어느 4개를 깔 것인지 우선순위와 이유를 적어라.
2. 위 §5 의 `respond_with_guardrails` 를 받아 `output_ok` 도 LLM 응답 스트리밍 중에 병렬 검사하도록 수정하라. (힌트: 토큰 청크 단위로 검사 + 누적 텍스트로 위반 감지)
3. Relevance 분류기의 false positive rate 가 12% 라는 메트릭이 나왔다. 다음 액션 3개를 적어라 (튜닝 · 임계값 · 평가셋).
4. 가드레일 자체에 인젝션이 들어갔을 때 (분류기 프롬프트가 뚫림) 이를 탐지·복구하는 방법 2개를 제안하라.

**다음 챕터** — 가드레일이 escalate 한 케이스를 사람이 어떻게 받을지. [Ch 29 휴먼 개입 설계](29-human-in-loop.md) 로.

---

## 원전

- OpenAI — *A Practical Guide to Building Agents* (2024) §Guardrails (7종 표 원전)
- Anthropic — *Building Effective Agents* (2024) — production guardrails 섹션
- OpenAI Moderation API docs
- NIST AI Risk Management Framework — 위협 모델링 골격
