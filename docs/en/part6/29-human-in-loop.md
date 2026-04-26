# Ch 29. Human-in-Loop Design

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/en/part6/ch29_human_in_loop.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - **Two triggers to escalate to humans** — failure threshold · high-risk action
    - **Approval queue state machine** — pending · approved · rejected · expired
    - **Approval interface** via Slack and internal dashboard
    - **Audit log JSON schema** — who · when · what · why
    - Connection to LangGraph `interrupt_before` (Ch 23)
    - Five failure modes (all-escalate · indefinite pending · missing TTL · missing context · missing audit trail)

!!! quote "Prerequisites"
    [Ch 23 LangGraph interrupt](../part5/23-langgraph.md) · [Ch 28 Tool Safeguard](28-guardrails.md) — high-risk classification. You understand how guardrails escalate to humans.

---

## 1. Concept — two triggers to call a human

Automation's goal isn't **automate everything**. It's **automate only what you can handle**. Two cases must land with a human.

![Two escalation triggers](../assets/diagrams/ch29-escalation-triggers.svg#only-light)
![Two escalation triggers](../assets/diagrams/ch29-escalation-triggers-dark.svg#only-dark)

| Trigger | Character | Example |
|---|---|---|
| **① Failure threshold exceeded** | Automatic (system signal) | 5 retries failed · guardrail escalate · confidence < 0.6 |
| **② High-risk action** | Pre-policy (humans decide upfront) | Large refund · irreversible (delete account) · external message |

Both **must flow into the same approval queue**. If you split queues by trigger, your audit trail scatters. You can't track who decided what.

> "Plan for human intervention with **two triggers**: failure thresholds and high-risk actions." — *OpenAI Practical Guide*

---

## 2. Why you need this — automation alone isn't enough

**① Accountability**. If the AI approves a ₩1M refund wrongly, who's liable? The company. But **if a human clicked approve and there's a record, liability spreads, and you have grounds for policy improvement.**

**② Irreversibility**. Account deletion, DB DROP, external email send — you can't undo them. Even at 99% reliability, the 1% irreversible case means recovery costs exceed your automation savings.

**③ Out-of-distribution cases**. LLMs are strong inside their training distribution. When confidence dips, it's safer to escalate than to guess.

**④ Learning signal**. Human decisions = labels. If you log approval/rejection with reason, it joins your evaluation set (Ch 16).

---

## 3. Where it's used — threshold design

| Domain | Automate | Needs human |
|---|---|---|
| **CS refund** | < ₩50k · policy clear | ≥ ₩100k · policy fuzzy · VIP customer |
| **HR time off** | Standard 1–3 day leave | >5 days · unpaid leave · >50% concurrent |
| **Payment** | Regular purchases | New customer's first ₩1M · risky country card |
| **Document send** | Internal memo | External customer email · press release · legal doc |
| **DB change** | SELECT · pre-validated INSERT | DELETE · DROP · ALTER |

**Domain experts set the threshold. Don't guess.** Thresholds aren't magic numbers baked into handlers. They live in a **policy registry** and get PM/legal review on PRs.

---

## 4. Minimal example — approval queue and LangGraph interrupt

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

1. Embed **trace_id** at case creation to link to LLM trace (Ch 27).
2. Redis TTL 24h. Auto-deletes on expiry + separate expired handling (below).
3. Reviewer decides. Reason is nearly required.
4. Every decision goes to immutable audit log.

### Combining with LangGraph

LangGraph's `interrupt_before` (Ch 23) is your human gate's infrastructure:

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

1. Inside `approve_gate_node`, call `enqueue(...)` when amount > threshold.
2. Graph pauses before `execute` — human decides, then you resume via `app.invoke(None, config)`.

---

## 5. Hands-on — state machine and approval UI

An approval queue is a **state machine**. Every case terminates on exactly one path.

![Approval queue state machine](../assets/diagrams/ch29-approval-state.svg#only-light)
![Approval queue state machine](../assets/diagrams/ch29-approval-state-dark.svg#only-dark)

| State | Next | Trigger |
|---|---|---|
| **Pending** | Approved / Rejected / Expired | Reviewer decides or TTL |
| **Approved** | Resume (agent resumes) | Reviewer approve |
| **Rejected** | Notify user (with reason) | Reviewer reject |
| **Expired** | Auto-reject + on-call alert | 24h elapsed |
| **Audit** | (final) | All exit paths converge |

### Slack approval UI

Fastest way: Slack interactive message.

```python title="approval/slack.py" linenums="1"
async def notify_slack(case):
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*Approval Request* · `{case['action']}` · {case['trigger']}"}},
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

1. **Trace link is critical.** The reviewer needs to see the LLM's reasoning to make an informed call.

### Audit log schema

```python title="approval/audit.py" linenums="1"
AUDIT_SCHEMA = {
    "case_id":     "uuid",
    "trace_id":    "linked LLM trace",
    "action":      "what was requested",
    "args":        "redacted args (PII removed)",
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

**Append-only.** Write once, can't edit. Compliance audits typically want 7 years of retention; rules vary by domain.

### TTL expiry handling

```python title="approval/expire_worker.py"
# cron · runs every 1 minute
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

1. Expired is auto-reject, but **also alert on-call.** "Cases no one reviewed in 24h" = operational signal.

---

## 6. Common failure modes

- **Escalate everything.** When you start, you're conservative, the queue floods, ops burns out. **Monitor trigger rate daily + tune thresholds weekly.**
- **No TTL.** Pending cases stack forever. One reviewer takes a day off, user waits indefinitely. **24h TTL + auto-reject + on-call alert.**
- **Missing context.** Slack message shows only args, no trace link → reviewer doesn't know why this is high-risk. **Attach trace_id · guardrail reason · similar past cases.**
- **Silent UX during approval wait.** User refreshes the app, sees "processing" forever. **Show "In review — avg 12 min" ETA.**
- **Mutable audit log.** Someone edits it after the fact, audit is worthless. **Append-only DB · S3 object lock · WORM storage.**
- **PII in plaintext audit log.** Redact what you need for the decision, store the original in a short-TTL vault elsewhere.
- **Thresholds as magic numbers.** `if amount > 100000` buried in a handler — policy change requires a PR. **Use separate policy.yaml + reviewer assignment.**

---

## 7. Operations checklist

- [ ] Both triggers (failure threshold · high-risk policy) converge into one queue
- [ ] Thresholds defined outside code (policy.yaml · feature flag)
- [ ] Case TTL 24h baseline + after-hours/holiday policy
- [ ] Expired → auto-reject + on-call alert
- [ ] Slack/dashboard message includes trace_id link
- [ ] Reviewer must provide reason on approval/rejection
- [ ] Audit log append-only · 7-year retention (per domain regulation)
- [ ] No plaintext PII in queue or log — mask it
- [ ] Metrics: queue length · mean decision time · expiry rate
- [ ] LangGraph interrupt tied to queue via case_id (resumable)
- [ ] Reviewer decisions join evaluation set as labels (Ch 16)

---

## 8. Exercises & next chapter

1. Design auto/human thresholds for a CS refund chatbot (amount · customer tier · reason on 3 axes). Create a table; justify each threshold in one line.
2. Take the `enqueue / decide` from §4 and implement the expired worker. Expired cases must log to audit.
3. What three pieces of info would you add to the Slack approval message so reviewers decide better? Explain why.
4. Assume you set thresholds too conservatively and the queue floods. Design three metrics to diagnose it, then design a threshold adjustment procedure.

**Next** → [Ch 30 Cost & Latency Optimization](30-cost-latency.md) — guardrails and approval are live; now cut costs and latency. :material-arrow-right:

---

## Sources

- OpenAI — *A Practical Guide to Building Agents* §Plan for Human Intervention
- LangGraph docs — `interrupt_before` · `get_state` · resume patterns
- Slack — *Interactive components* (block kit · action buttons)
- AWS Well-Architected — Operational Excellence (audit · runbook)
