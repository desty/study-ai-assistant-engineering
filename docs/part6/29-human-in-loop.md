# Ch 29. 휴먼 개입 설계

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part6/ch29_human_in_loop.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - 사람을 부르는 **두 가지 트리거** — 실패 임계 / 고위험 액션
    - **승인 큐** 상태 머신 — pending · approved · rejected · expired
    - Slack · 내부 대시보드로 받는 **승인 인터페이스**
    - **감사 로그** JSON 스키마 — who · when · what · why
    - LangGraph `interrupt_before` (Ch 23) 와의 연결
    - 5대 함정 (전부 에스컬레이션 · 영구 펜딩 · TTL 부재 · 컨텍스트 누락 · 감사 누락)

!!! quote "전제"
    [Ch 23 LangGraph interrupt](../part5/23-langgraph.md) · [Ch 28 Tool Safeguard](28-guardrails.md) 의 high-risk 분류. 가드레일이 escalate 한 케이스를 사람이 받는 단계.

---

## 1. 개념 — 사람을 부르는 두 트리거

자동화의 목표는 **모든 걸 자동으로** 가 아니라 **자동으로 다룰 수 있는 것만 자동으로** 입니다. 두 종류 케이스는 사람이 받아야 합니다.

![두 트리거](../assets/diagrams/ch29-escalation-triggers.svg#only-light)
![두 트리거](../assets/diagrams/ch29-escalation-triggers-dark.svg#only-dark)

| 트리거 | 성격 | 예시 |
|---|---|---|
| **① 실패 임계 초과** | 자동 (시스템 신호) | retry 5회 실패 · guardrail escalate · confidence < 0.6 |
| **② 고위험 액션** | 사전 정책 (사람이 미리 정함) | 큰 금액 환불 · 비가역 (계정 삭제) · 외부 메시지 |

둘 다 **같은 승인 큐로 흘러야** 감사 추적이 한 곳에 모입니다. 트리거별로 큐를 따로 두면 누가 무엇을 결정했는지 사후 추적이 흩어짐.

> "Plan for human intervention with **two triggers**: failure thresholds and high-risk actions." — *OpenAI Practical Guide*

---

## 2. 왜 필요한가 — 자동화만으론 안 되는 이유

**① 책임 소재**. AI 가 ₩100만원 환불을 잘못 승인하면 누가 책임지나? 회사. 그러나 **사람이 승인 버튼을 누른 기록이 있으면 책임이 분산**되고, 정책 개선의 근거가 됩니다.

**② 비가역성**. 계정 삭제·DB drop·외부 이메일 발송은 되돌릴 수 없습니다. 자동화 신뢰도가 99% 라도, 1% 가 비가역이면 회복 비용이 자동화 절감 비용을 초과.

**③ 분포 외 케이스**. AI 는 학습 분포 안에서만 강합니다. confidence 가 낮을 때 우기지 않고 사람을 부르는 게 더 안전.

**④ 학습 신호**. 사람의 결정 = 라벨. 승인/거절 사유까지 기록하면 평가셋(Ch 16) 에 합류 가능.

---

## 3. 어디에 쓰이는가 — 임계값 설계

| 도메인 | 자동 가능 | 사람 필수 |
|---|---|---|
| **CS 환불** | < ₩50k · 정책 명확 | ≥ ₩100k · 정책 모호 · VIP 고객 |
| **HR 휴가** | 일반 연차 1~3일 | 5일 초과 · 무급 휴직 · 동시 인원 50%↑ |
| **결제** | 일반 결제 | 신규 고객 첫 ₩1M 결제 · 위험국 카드 |
| **문서 발송** | 사내 메모 | 외부 고객 메일 · 보도자료 · 법적 문서 |
| **DB 변경** | SELECT · 미리 검증된 INSERT | DELETE · DROP · ALTER |

**임계값은 도메인 전문가가 정합니다.** 엔지니어가 추측해서 박지 마세요. 임계값은 코드에 박힌 매직 넘버가 아니라 **policy registry** 에 두고 PM/법무가 PR 리뷰.

---

## 4. 최소 예제 — 승인 큐와 LangGraph interrupt

```python title="approval/queue.py" linenums="1" hl_lines="11 19 28"
import uuid, time, json
from enum import Enum
import redis.asyncio as redis

r = redis.from_url(os.environ["REDIS_URL"])
TTL_SECONDS = 24 * 3600

class State(str, Enum):
    PENDING = "pending"; APPROVED = "approved"
    REJECTED = "rejected"; EXPIRED = "expired"

async def enqueue(action: str, args: dict, user_id: str,             # (1)!
                  trigger: str, trace_id: str) -> str:
    case_id = str(uuid.uuid4())
    case = {
        "case_id": case_id, "action": action, "args": args,
        "user_id": user_id, "trigger": trigger, "trace_id": trace_id,
        "state": State.PENDING, "created_at": time.time(),
    }
    await r.setex(f"case:{case_id}", TTL_SECONDS, json.dumps(case))   # (2)!
    await notify_slack(case)
    return case_id

async def decide(case_id: str, decision: State,                       # (3)!
                 reviewer: str, reason: str = ""):
    raw = await r.get(f"case:{case_id}")
    if not raw: raise KeyError("case not found or expired")
    case = json.loads(raw)
    case.update({
        "state": decision, "reviewer": reviewer,
        "reason": reason, "decided_at": time.time(),
    })
    await audit_log(case)                                             # (4)!
    await r.delete(f"case:{case_id}")
    return case
```

1. case 생성 시 **trace_id** 를 같이 박아 LLM trace (Ch 27) 와 연결.
2. Redis TTL 24h. 만료되면 자동 삭제 + 별도 expired 처리 (아래).
3. reviewer 가 결정. reason 은 필수에 가깝게.
4. 모든 결정은 immutable audit log 로.

### LangGraph 와 결합

LangGraph 의 `interrupt_before` (Ch 23) 가 사람 게이트의 인프라 역할:

```python title="graphs/refund.py" linenums="1"
from langgraph.graph import StateGraph

graph = StateGraph(RefundState)
graph.add_node("classify", classify_node)
graph.add_node("compute_amount", compute_node)
graph.add_node("approve_gate", approve_gate_node)                       # (1)!
graph.add_node("execute", execute_refund_node)

graph.add_edge("classify", "compute_amount")
graph.add_edge("compute_amount", "approve_gate")
graph.add_edge("approve_gate", "execute")

app = graph.compile(
    checkpointer=SqliteSaver(...),
    interrupt_before=["execute"],                                        # (2)!
)
```

1. `approve_gate_node` 안에서 amount > 임계 시 `enqueue(...)` 호출.
2. `execute` 직전에 그래프가 멈춤 → 사람이 결정 후 `app.invoke(None, config)` 로 재개.

---

## 5. 실전 — 상태 머신과 승인 인터페이스

승인 큐는 **상태 머신**입니다. 모든 케이스는 정확히 한 종료 경로로만 끝납니다.

![승인 큐 상태 머신](../assets/diagrams/ch29-approval-state.svg#only-light)
![승인 큐 상태 머신](../assets/diagrams/ch29-approval-state-dark.svg#only-dark)

| 상태 | 다음 | 트리거 |
|---|---|---|
| **Pending** | Approved / Rejected / Expired | reviewer 결정 또는 TTL |
| **Approved** | Resume (Agent 재개) | reviewer approve |
| **Rejected** | Notify user (사유 동반) | reviewer reject |
| **Expired** | Auto-reject + on-call alert | 24h 경과 |
| **Audit** | (final) | 모든 종료 경로 수렴 |

### Slack 승인 UI

가장 빠르게 만드는 방법은 Slack interactive message:

```python title="approval/slack.py" linenums="1"
async def notify_slack(case):
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*승인 요청* · `{case['action']}` · {case['trigger']}"}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*User*\n{case['user_id']}"},
            {"type": "mrkdwn", "text": f"*Args*\n```{json.dumps(case['args'])[:200]}```"},
        ]},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "Approve"},
             "style": "primary", "action_id": f"approve_{case['case_id']}"},
            {"type": "button", "text": {"type": "plain_text", "text": "Reject"},
             "style": "danger", "action_id": f"reject_{case['case_id']}"},
            {"type": "button", "text": {"type": "plain_text", "text": "Open Trace"},
             "url": f"{LANGFUSE_URL}/trace/{case['trace_id']}"},                # (1)!
        ]},
    ]
    await slack.chat_postMessage(channel=APPROVAL_CHANNEL, blocks=blocks)
```

1. **Trace 링크** 가 결정적. reviewer 가 LLM 의 추론 과정을 볼 수 있어야 정보 기반 결정.

### 감사 로그 스키마

```python title="approval/audit.py" linenums="1"
AUDIT_SCHEMA = {
    "case_id":     "uuid",
    "trace_id":    "linked LLM trace",
    "action":      "what was requested",
    "args":        "redacted args (PII 제거)",
    "trigger":     "failure_threshold | high_risk_policy",
    "user_id":     "end user (subject)",
    "reviewer":    "decided by (Slack user)",
    "decision":    "approved | rejected | expired",
    "reason":      "free text from reviewer",
    "created_at":  "epoch s",
    "decided_at":  "epoch s",
    "ttl_at":      "epoch s",
}
```

**Append-only**. 한 번 쓰면 못 고침. 컴플라이언스 감사 대비 7년 보관이 일반적이며 도메인별로 다름.

### TTL 만료 처리

```python title="approval/expire_worker.py"
# cron · 1분마다 실행
async def expire_worker():
    async for key in r.scan_iter("case:*"):
        raw = await r.get(key)
        if not raw: continue
        case = json.loads(raw)
        if time.time() - case["created_at"] > TTL_SECONDS:
            case["state"] = State.EXPIRED
            await audit_log(case)
            await alert_oncall(case)                                     # (1)!
            await r.delete(key)
```

1. expired 는 자동 reject 지만 **on-call 알림**도 같이. "사람이 24h 동안 못 본 케이스" = 운영 이슈 신호.

---

## 6. 자주 깨지는 포인트

- **모든 걸 에스컬레이션**. 처음 운영 시 보수적으로 깔다 보면 큐가 폭주, 운영팀 번아웃. **trigger rate 일별 모니터링** + 임계값 주간 튜닝.
- **TTL 없음**. pending 이 영원히 쌓임. reviewer 가 잠깐 자리 비우면 사용자는 무한 대기. **24h TTL + auto-reject + on-call alert**.
- **컨텍스트 누락**. Slack 메시지에 args 만 보내고 trace 링크 없음 → reviewer 가 "왜 이게 high-risk 인지" 모름. **trace_id · 가드레일이 잡은 이유 · 유사 과거 케이스 N건** 같이 첨부.
- **승인 기다리는 동안 UX 침묵**. 사용자가 앱을 새로고침해도 "처리 중" 만 보임. **"검토 중 — 평균 12분"** 같은 ETA 노출.
- **감사 로그가 mutable**. 누군가 사후 수정하면 감사 의미 없음. append-only DB · S3 object lock · WORM 스토리지.
- **PII 가 audit log 에 평문**. 결정에 필요한 만큼만 redact 후 저장. 원본은 짧은 TTL 의 별도 vault.
- **트리거를 코드에 매직 넘버로**. `if amount > 100000` 이 핸들러 안에 박힘 → 정책 변경이 PR. 별도 policy.yaml + reviewer 지정.

---

## 7. 운영 체크리스트

- [ ] 두 트리거(실패 임계 · 고위험 정책) 모두 한 큐로 수렴
- [ ] 임계값이 코드 외부 (policy.yaml · feature flag) 에 정의
- [ ] case TTL 24h 기본 + 야간·휴일 정책
- [ ] expired → auto-reject + on-call alert
- [ ] Slack/Dashboard 메시지에 trace_id 링크 필수
- [ ] reviewer 결정 시 reason 필수 입력
- [ ] audit log append-only · 7년 보관 (도메인 규제 따라)
- [ ] PII 가 큐·로그에 평문 안 들어가도록 마스킹
- [ ] 큐 길이 · 평균 결정 시간 · expired rate 메트릭
- [ ] LangGraph interrupt 와 큐가 case_id 로 연결 (resume 가능)
- [ ] reviewer 의 결정이 평가셋 라벨로 합류 (Ch 16)

---

## 8. 연습문제 & 다음 챕터

1. CS 환불 챗봇의 자동/사람 임계값을 설계하라 (금액·고객등급·사유 3축). 표로 작성하고 각 임계의 근거를 1줄씩.
2. §4 의 `enqueue / decide` 를 받아 expired 워커를 구현하라. expired 도 audit log 에 기록되어야 한다.
3. Slack 승인 메시지에 reviewer 가 더 좋은 결정을 하도록 어떤 정보 3개를 더 첨부할 것인가? 이유와 함께.
4. 임계값을 너무 보수적으로 잡아 큐가 폭주하는 상황을 가정하라. 운영 메트릭 3개로 진단하고 임계 조정 절차를 설계하라.

**다음 챕터** — 가드레일·승인까지 깔린 시스템의 비용·지연을 어떻게 줄이나. [Ch 30 비용·지연 최적화](30-cost-latency.md) 로.

---

## 원전

- OpenAI — *A Practical Guide to Building Agents* §Plan for Human Intervention
- LangGraph docs — `interrupt_before` · `get_state` · resume 패턴
- Slack — *Interactive components* (block kit · action buttons)
- AWS Well-Architected — Operational Excellence (audit · runbook)
