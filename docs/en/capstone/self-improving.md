# Capstone — Self-Improving Assistant

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/en/capstone/self_improving.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll build"
    - **Every piece from Parts 1–7** integrated into one system
    - A **closed feedback loop** where user feedback becomes evaluation data and training data automatically
    - An **8-stage pipeline** — user → assistant → trace → failure classifier → DPO data → retrain → eval gate → deploy
    - **8-week progression guide** and a 9-item deliverables checklist
    - Five common failure modes (loop doesn't close · eval data leaks · self-reinforcement bias · negative ROI · safety regression)

!!! quote "Prerequisites"
    You've completed the core chapters in Parts 1–6. Part 7 Ch 32–33 are helpful context; **Part 7 Ch 34 (DPO) is optional** — you can start at a conceptual level.

---

## 1. Concept — Why "self-improving"?

Most LLM products ship **and then freeze**. The model stays the same, the prompt stays the same, but your users keep changing — and over time, you get more wrong answers.

This capstone's goal: **close the loop so the system gets better every week.**

![Self-improving loop](../assets/diagrams/capstone-self-improving-loop.svg#only-light)
![Self-improving loop](../assets/diagrams/capstone-self-improving-loop-dark.svg#only-dark)

| Stage | What | Source |
|---|---|---|
| ① **User** | 👍/👎 + free text + auto signals (re-query rate) | Ch 29 |
| ② **Assistant** | RAG + Agent + guardrails | Parts 3·5 |
| ③ **Trace + Log** | trace_id · cost · score attached | Ch 27 |
| ④ **Failure Classifier** | 5-tier taxonomy + Judge score | Ch 17·19 |
| ⑤ **DPO Data** | (q, ✓, ✗) pairs auto-generated | Ch 34 |
| ⑥ **Retrain (LoRA)** | Weekly schedule + small adapter | Ch 33 |
| ⑦ **Eval Gate** | baseline + Δ must pass | Ch 16 |
| ⑧ **Deploy** | adapter swap + canary | Ch 26·30 |

**Skip even one stage and self-improvement stops.** The whole system works only if the loop is closed.

---

## 2. Why it matters — Three ways static deployments decay

**① Distribution drift**. The questions users ask shift every week — further from your training data — accuracy drops.

**② New facts emerge**. Your domain launches products or changes policy, but the RAG corpus lags. Answers go stale.

**③ Known failure patterns pile up**. The same wrong answer hits the same users week after week. Support inboxes overflow.

With a closed loop, all three show up as **automatic signals** (Ch 27 metrics) that flow into stages ⑤–⑥ as training data.

---

## 3. Where it fits — The integrated architecture

![Capstone architecture](../assets/diagrams/capstone-architecture.svg#only-light)
![Capstone architecture](../assets/diagrams/capstone-architecture-dark.svg#only-dark)

Four layers:

| Layer | Modules | Core chapters |
|---|---|---|
| **Serving** | API Gateway · Guardrails · Session · Approval Queue | 26 · 28 · 29 |
| **Agent** | LangGraph · Tools · Memory · Model Router | 22–24 · 30 |
| **Knowledge** | Hybrid Retrieval · Reranker · Vector · Citation | 10–12 |
| **Eval · Learn** | Trace · Failure Classifier · Eval Set · LoRA/DPO | 16–19 · 27 · 33–34 |

**One module = one chapter.** You don't need all of them — pick what fits your domain.

### Choose a use case (pick one)

| Use case | Data | Self-improvement signal |
|---|---|---|
| In-house IT helpdesk | Wiki · ticket logs | Ticket reopening rate |
| Meeting note summarizer | Audio · memo | User edit rate |
| Code review helper | git log · PRs | Comment adoption rate |
| FAQ auto-responder | Customer inquiries | Re-query rate / human handoff |

**In-house IT with a wiki and ticket system has the richest data.** That's the recommended starting point.

---

## 4. Minimal example — Week 1 skeleton (200 lines)

```python title="capstone/app.py" linenums="1" hl_lines="11 22 32 38"
from fastapi import FastAPI, HTTPException, Header
from langfuse import observe
import uuid

app = FastAPI()

@app.post("/chat")
@observe()
async def chat(req: ChatRequest, idempotency_key: str = Header(...)):
    trace_id = str(uuid.uuid4())
    if not (await guardrails_input(req.text)):                          # (1)!
        return reject("guardrail")

    history = await session_load(req.user_id)
    docs = await retrieve(req.text, top_k=5)                            # (2)!
    answer = await agent_loop(req.text, history, docs, trace_id)        # (3)!

    if not await guardrails_output(answer):
        return reject("output_policy")
    await session_append(req.user_id, req.text, answer)
    return {"answer": answer, "trace_id": trace_id}

@app.post("/feedback")                                                  # (4)!
async def feedback(req: FeedbackRequest):
    await fb_store.save({
        "trace_id": req.trace_id,
        "thumbs": req.thumbs,        # +1 / -1
        "comment": req.comment,
        "ts": time.time(),
    })
    return {"ok": True}

# Weekly cron
async def weekly_loop():                                                # (5)!
    bad_cases = await classify_failures(window="7d", threshold=-1)
    pairs = await build_dpo_pairs(bad_cases)                            # (6)!
    if len(pairs) < 200:
        return                                                          # Not enough data → try next week
    adapter = await train_lora_dpo(pairs)
    score = await eval_against(adapter, eval_set="hold_out_v3")
    if score >= baseline + 0.03:                                        # (7)!
        await deploy_canary(adapter, percent=10)
```

1. Input guardrails (Ch 28). Hard failures (safety/moderation) run serial; others optimistic parallel.
2. RAG hybrid retrieval (Ch 12) + reranker.
3. LangGraph state machine (Ch 23). Use interrupt_before for high-risk actions.
4. Bind user feedback to trace_id and store — the loop's entry point.
5. Weekly cron. Collect failures → build DPO pairs → train → eval gate.
6. Generate (q, ✓, ✗) pairs: rejected answer = 👎 case, chosen = better answer from Judge.
7. **Won't deploy if +3 points aren't gained.** This gate stops regression.

---

## 5. Hands-on — 8-week progression

| Week | Activity | Deliverable |
|---|---|---|
| 1 | Pick use case · collect data · sketch 8-stage diagram | Problem statement + architecture SVG |
| 2 | RAG pipeline (Ch 11–14) | mini_rag.py + 100 eval examples (Ch 16) |
| 3 | LangGraph Agent + seven guardrails | First working demo |
| 4 | Observability + 5 pilot users | Langfuse dashboard |
| 5 | Feedback endpoint + failure classifier (Ch 19) | 1-week log analysis report |
| 6 | DPO data generation + first LoRA train (Ch 33) | adapter v1 + eval scores |
| 7 | Weekly automation (cron + eval gate) | Auto-deploy workflow |
| 8 | 1 more week + retrospective | Final report |

**5 real users for 1 week = typically 200–500 traces.** Enough to build 100–300 (✓, ✗) pairs for DPO training.

### Evaluation — baseline · post-DPO · regression

| Metric | Measured | Target |
|---|---|---|
| Domain accuracy | 100 hold-out examples (Ch 16) | baseline +3 points |
| Latency p95 | Ch 27 metrics | baseline or lower |
| Cost / request | Ch 27 metrics | baseline ±10% |
| Guardrail trigger | Ch 28 | No regression |
| Regression set | Cases that passed before | 100% preserved |
| User CSAT | 👍 / (👍+👎) | baseline +5% |

**All six metrics must pass** before you deploy a new adapter. One regression blocks it.

### DPO data auto-generation pattern

```python title="capstone/build_pairs.py"
async def build_dpo_pairs(bad_cases):
    pairs = []
    for case in bad_cases:
        rejected = case["answer"]                       # Answer that got 👎
        # Generate better answer with Judge LLM
        chosen = await call_llm("claude-opus-4-7",
            prompt=f"Answer this question more accurately and politely:\n{case['q']}")
        # Check: does rejected differ meaningfully from chosen?
        if similarity(rejected, chosen) > 0.9:           # Too similar = weak signal
            continue
        pairs.append({
            "prompt": case["q"],
            "chosen": chosen,
            "rejected": rejected,
        })
    return pairs
```

---

## 6. Common pitfalls

- **Loop doesn't close**. You collect feedback but training is manual → forgotten in a month. **Automate the weekly cron + alerts** to make it truly self-improving.
- **Eval data leaks into training**. Eval set gets mixed into training data → great training scores, real regression. **Auto-check hashes before training starts.**
- **Self-reinforcement bias**. Generate ✓ using a Judge LLM and you encode the Judge's biases. **Spot-check 5% of chosen answers with humans** to catch drift.
- **Negative ROI**. Labeling + GPU + ops costs don't justify the savings. **Revisit Ch 32 ROI math every quarter.**
- **Safety regression**. After DPO, rejection policies weaken → jailbreak answers appear. **Keep a separate safety regression eval set** (Ch 28).
- **Adapter accumulation**. 52 adapters in a year, can't track which is best. **Version everything + auto-rollback policy.**
- **Assuming 5 users generalize**. 5-user patterns ≠ 100-user patterns. **Careful canary rollout** (10% → 50% → 100%) then expand.
- **Ignoring Judge accuracy**. If your failure classifier is 60% accurate, 40% of training data is noise. **Measure Judge accuracy separately** (Ch 17).

---

## 7. Operations checklist

- [ ] All 8 stages automated (zero manual steps)
- [ ] Every trace has trace_id · user_id · model_version · adapter_version
- [ ] Training data ↔ eval set contamination detected automatically
- [ ] Judge accuracy measured separately (target 80%+)
- [ ] 6-metric gate (accuracy · p95 · cost · guardrail · regression · CSAT) enforced
- [ ] Safety regression eval set (covers all seven guardrails)
- [ ] Adapter versioning + instant rollback possible
- [ ] Canary deployment (10% → 50% → 100%) + per-stage alerts
- [ ] Weekly metric report (auto-sent)
- [ ] 1-year ROI stays positive · reviewed every quarter

---

## 8. Deliverables checklist

| # | Item | When |
|---|---|---|
| ① | **Problem statement** — what assistant · for whom · why | Week 1 |
| ② | **Architecture SVG** — modules mapped to chapters | Week 1 |
| ③ | **Data inventory** — RAG corpus · 100+ eval examples | Week 2 |
| ④ | **Prompt/RAG/Agent strategy** — implementation code per block | Weeks 2–3 |
| ⑤ | **Seven guardrails coverage table** | Week 3 |
| ⑥ | **Evaluation results** — baseline vs post-DPO comparison | Week 7 |
| ⑦ | **20+ failure case analysis** — taxonomy classified | Week 5 |
| ⑧ | **Ops considerations** — cost · latency · safety analysis | Weeks 4–6 |
| ⑨ | **Self-improving loop design** — cadence · triggers · gates · rollback | Week 7 |

**Week 8 presentation (30 min)**:
- Demo (5 min, live)
- Architecture (5 min)
- Evaluation results (10 min, including regression)
- Retrospective (10 min — what broke, what's next)

---

## Closing — Where you go from here

Finish this capstone and the next frontier is your domain.

**Expansion paths**:

- **Multi-agent evolution** (Ch 25) — one agent runs 24/7, another handles retraining
- **Constitutional AI** (Ch 34) to lower labeling cost — but keep human review
- **Online learning** — weekly → daily → real-time (higher risk, higher cost)
- **Multi-modal** — images, audio, documents (Ch 14)

**What this book doesn't cover**:
- Distributed training (tens to hundreds of GPUs)
- Custom pretraining
- Agent simulation environments (CS329A territory)
- AGI discussions

This book assumes you're **an engineer making great use of external models.** You've now reached the deepest point possible while calling an outside API. Your next adventure is your domain's data, your users' feedback, and relentless measurement.

> "The best way to predict the future is to build it."

---

## Sources

- Stanford CS329A — *Self-Improving AI Agents* Final Project (inspiration)
- Stanford CS329A Lecture 7 — *Open-Ended Evolution of Self-Improving Agents*
- Stanford CS329A Lecture 13 — *Agentic Frameworks for SWE* (CodeMonkeys, others)
- Rafailov et al. (2023) *DPO*
- Bai et al. (2022) *Constitutional AI*
- Complete book: Ch 1–34
