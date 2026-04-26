# Ch 32. When to Fine-Tune — and When Not To

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/en/part7/ch32_when_to_finetune.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - **Why "AI project = fine-tuning" is a trap**
    - A 4-gate decision tree — getting stuck at any gate means holding off
    - **Prompt · RAG · SFT · DPO** — trade-offs, cost, and timeline for each
    - Problems fine-tuning solves well vs. problems it doesn't
    - **Data requirements** — what numbers like "hundreds" or "tens of thousands" actually mean
    - Six critical pitfalls (skipping RAG · underestimating labeling cost · one-shot training · no eval set · injecting facts via SFT · starting with base models)

!!! quote "Prerequisites"
    [Ch 31](31-model-arch.md) covered the three training stages. What we can actually touch is **SFT (Ch 33) and DPO (Ch 34)** — both phases where **data costs exceed GPU costs.**

---

## 1. Concept — The right question is "do we even need fine-tuning"

Fine-tuning is the **last card in most LLM projects.** If you assume from day one that you'll fine-tune, you're signing up for:

- Months of data labeling
- Hundreds of thousands to millions in GPU costs
- Every base model upgrade forces you to retrain everything
- No eval set means you can't detect regressions

All that expense can vanish on a problem that **Prompt + RAG alone would have solved.**

![Decision tree](../assets/diagrams/ch32-finetune-decision.svg#only-light)
![Decision tree](../assets/diagrams/ch32-finetune-decision-dark.svg#only-dark)

| Gate | Pass if | If blocked |
|---|---|---|
| ① Does Prompt + RAG solve it? | "No" proven by eval set | Stick with Prompt/RAG |
| ② Do you have a solid eval set? | 1K+ (q, gold answer) pairs | Build eval first (Ch 16) |
| ③ Is labeling cost < savings? | 1-year ROI is positive | Remodel the math |
| ④ Can you operate retraining quarterly? | Pipeline + GPU budget + owner assigned | Use API + prompt instead |

**You must pass all four gates** before fine-tuning is even on the table. Even then, start with a PoC (small LoRA run) to measure impact before full training.

---

## 2. Why you need it — Two ceilings on Prompt and RAG

If you hit either of these ceilings, SFT becomes justified.

**① Tone, style, and output format aren't stable.** Prompt + few-shot gets you to 80%, but 5% of cases produce a different format. In production, that 5% is expensive. SFT is your best tool here.

**② Model size hits the cost wall.** Claude Opus solves it; Claude Haiku doesn't. Fine-tune Haiku to fit your domain, and the **long-term cost savings dwarf the SFT cost.** Chapter 30's model routing becomes more aggressive.

Conversely, **injecting new facts is not an SFT problem** — RAG is far more efficient. To push facts through fine-tuning means retraining on every update. That's a heavy toll.

> "Fine-tuning teaches **how**, RAG provides **what**." — Industry conventional wisdom

---

## 3. Where they fit — Four approaches compared

![Four approaches](../assets/diagrams/ch32-approach-matrix.svg#only-light)
![Four approaches](../assets/diagrams/ch32-approach-matrix-dark.svg#only-dark)

| Approach | Strengths | Weaknesses | Cost | Time |
|---|---|---|---|---|
| **① Prompt** | Format tweaks · single task | Domain facts · large-scale tone shift | $ | mins |
| **② RAG** | Domain facts · freshness · citations | Tone · format enforcement | $$ | days |
| **③ SFT (LoRA)** | Tone · output format · classification | New fact injection | $$$ | weeks |
| **④ DPO/RLHF** | Safety · politeness · refusal policy | Data collection · overfitting | $$$$ | months |

**Try in order**: ①→②→③→④. Each move to the next level requires proving that **the previous level hit its ceiling—and eval sets have to show it.**

### By problem type

| Problem | First try | Then |
|---|---|---|
| "Answer in our company voice" | ① Prompt + few-shot | ③ SFT if that stalls |
| "Answer from internal wiki" | ② RAG | ③ SFT when citation precision tops out |
| "Classify legal docs into 5 buckets" | ① Prompt → ③ SFT (Haiku) | Cost optimization play |
| "Rejection tone needs new policy" | ④ DPO (small batch) | SFT won't stabilize it |
| "Real-time stock price answers" | ② RAG (with tool calls) | Never ③—facts age too fast |
| "Stable JSON output format" | ① + tool-use (Ch 6) | ③ SFT if that doesn't land |

---

## 4. Minimal example — 10-point fine-tuning readiness checklist

```python title="checklist.py" linenums="1"
QUESTIONS = [
    ("Do you have 1000+ eval examples?", "no"),                      # (1)!
    ("Does Prompt + 5 few-shots fail 30%+ of the time?", "no"),
    ("Have you tried RAG yet?", "no"),                               # (2)!
    ("Are failures clustered in tone, format, or classification?", "no"),
    ("Is fact accuracy the root cause of failures?", "yes"),         # (3)!
    ("Do you have 1K+ labeled (q,a) pairs and budget?", "no"),
    ("Are you optimizing for a smaller, cheaper model?", "no"),     # (4)!
    ("Do you need new safety or refusal policies?", "no"),
    ("Does your team own the quarterly retrain pipeline?", "no"),
    ("Have you validated a LoRA PoC (100 samples) already?", "no"),
]

# 7+ yes answers = time to explore fine-tuning
yes_count = sum(1 for _, a in QUESTIONS if a == "yes")
print(f"YES: {yes_count}/10 → {'explore SFT' if yes_count >= 7 else 'not yet'}")
```

1. No eval set = can't measure impact. Chapter 16 first, always.
2. Skipping RAG then jumping to SFT is 90% wasted effort.
3. **If fact accuracy is the issue, RAG solves it** — not fine-tuning.
4. Cost optimization SFT (fine-tuning Haiku for your domain) is a legitimate reason.

Below 7 yes answers? Fill those in first. Starting SFT at 6 risks expensive failure.

---

## 5. Hands-on — Data volume intuition

| Task type | Minimum | Recommended | Good results |
|---|---:|---:|---:|
| Classification (10 classes) | 500 | 2K | 5K |
| Tone/style transfer | 1K | 5K | 20K |
| Domain-specific chat SFT | 5K | 20K | 100K |
| General instruction tuning | 50K | 200K | 1M+ |
| DPO (preferences) | 1K | 5K | 20K |

**"When in doubt, start at 5K"** is your safety baseline. Less than that, noise drowns signal.

### Quality beats quantity

| Pitfall | What happens |
|---|---|
| One person labels everything | Their biases bake into the model |
| Auto-generated examples only | The model's own weaknesses amplify |
| 5% label noise | Training stalls (fatal in small datasets) |
| Eval set leaks into training | High validation scores, poor real-world performance |

Apply the labeling guidelines from Ch 16 at the same rigor to fine-tuning data.

### PoC phase — 100–500 examples first

Before full training, run a **PoC**:

1. Grab 100–500 real examples
2. Fine-tune with LoRA (r=8, lightweight — see Ch 33)
3. Eval on your test set: if baseline + 5 points better → go full scale
4. If +5 points doesn't appear → more data won't fix it; revisit your approach

**+5 points varies by domain,** but the signal is what matters: "Do we see movement in the PoC phase?"

### Cost model — 1-year ROI

```
SFT cost = labeling + GPU + quarterly eval/retrain
        ≈ (5K × $1) + ($500) + ($200/month × 12) ≈ $7,900

Annual savings = (Opus cost per token - Haiku cost per token) × yearly calls
        Example: ($0.030 - $0.001) × 1M calls = $29,000

ROI = 29,000 / 7,900 ≈ 3.7 → positive. (Quality must stay equal.)
```

If ROI is below 1.0, **don't do it.** Add operational overhead and you need 1.5+ to feel safe.

---

## 6. Common failure modes

- **Jumping to SFT without trying RAG first.** Fact accuracy problems are RAG's sweet spot. Baking facts into fine-tuning is expensive and brittle on every update.
- **Underestimating labeling cost.** Making 5K (q,a) pairs isn't trivial — one labeler at 50/day needs 100 working days. Outsourcing runs $1–5 per pair.
- **One-shot training, then static.** Your base model ships a new version quarterly. Your SFT needs to retrain. Without infrastructure and ownership, it rots.
- **No eval set.** You train, metrics look good, then production burns. Eval sets come **before** training data.
- **Injecting facts via SFT.** Once a fact lands in weights, updates are locked behind retraining. Separate facts (RAG) from behavior (SFT).
- **Starting with base models instead of instruct.** Instruct models already have one SFT pass. You do domain tuning on top. Base models need 100x more data.
- **Skipping PoC.** You label 5K examples, train for days, gain 0 points. Big loss. Always 100-sample PoC first.
- **Watching only training loss, not domain metrics.** Final accuracy or F1 on your eval set is truth. Loss and perplexity are supporting signals.

---

## 7. Operations checklist

- [ ] Documented decision for all four gates (passed or blocked)
- [ ] Eval set 1K+ ready before labeling training data
- [ ] PoC (100–500 samples) shows signal before scaling
- [ ] Cost model (1-year ROI) is positive on the numbers
- [ ] Training data has zero overlap with eval set
- [ ] Multiple labelers + written guidelines + inter-rater agreement checks
- [ ] Quarterly retraining pipeline + GPU budget + named owner
- [ ] Base vs. instruct model choice documented
- [ ] Post-training: measure both domain accuracy and safety regressions
- [ ] Rollback-ready version control for model checkpoints

---

## 8. Exercises

1. Your internal IT helpdesk chatbot gets 60% of "internal policy" questions right. Apply the four gates — what's your first move?
2. You want answers in "official company voice." Rank: Prompt few-shot, RAG, SFT. Why that order?
3. SFT costs $7,900. Annual calls = 100K (10% of 1M). Calculate ROI and decide: ship or no-ship?
4. Your PoC (100 samples) hit baseline +1 point instead of +5. List three next moves.

**Next** → [Ch 33. LoRA and QLoRA in Practice](33-lora-qlora.md) :material-arrow-right:
You've cleared the gates. Time to get your hands dirty on the first tractable training job.

---

## Sources

- Stanford CME 295 — *Transformers and LLMs* Lec 4
- Hu et al. (2021) *LoRA: Low-Rank Adaptation of Large Language Models*
- OpenAI · Anthropic — fine-tuning best practice docs
- Industry guides: data collection · labeling · ROI modeling
