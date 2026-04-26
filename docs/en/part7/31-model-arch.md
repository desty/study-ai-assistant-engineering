# Ch 31. Model Architecture Overview

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/en/part7/ch31_model_arch.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "What you'll learn"
    - **The Transformer block — a simplified dissection**: embedding · self-attention · FFN · residual connections
    - **Next-token prediction as a single training objective**
    - **Three training stages** — Pretraining → SFT → RLHF/DPO and what each does
    - **Base vs. Instruct vs. Chat models** — what the names mean
    - **Where modern variants fit** — MoE · RoPE in one sentence each
    - **Skip the formulas** — build intuition first
    - **Five operational facts** that save you from disasters: context window limits · tokenizers · quantization · MoE · model cards

!!! quote "Prerequisites"
    Part 1–2 basics. Calculus and linear algebra help but aren't required. This chapter's goal is **enough intuition to operate models well from the outside**, not how to build them.

---

## 1. Concept — One Transformer block

Almost every LLM is a variant of the **Transformer** (2017). Modern models stack N identical blocks (usually 24–80), and each block does exactly two things.

![Transformer block](../assets/diagrams/ch31-transformer-block.svg#only-light)
![Transformer block](../assets/diagrams/ch31-transformer-block-dark.svg#only-dark)

| Stage | What it does | Role |
|---|---|---|
| **Tokens** | String → integer sequence | "Hello world" → `[101, 5023, ...]` |
| **Token Embedding** | Integer → high-dimensional vector (d_model) | Semantic representation |
| **Position (RoPE)** | Inject position information | Add "word order" |
| **Self-Attention** × N | Tokens exchange information | Context-dependent representation |
| **FFN (Feed-Forward)** × N | Nonlinear transform | Expressiveness |
| **LM Head + Softmax** | hidden → vocab distribution | Probability of next token |

**Every LLM's training goal is exactly one thing**: predict the probability distribution of the next token. That's it. Repeat "what follows 'hello'?" billions of times, and grammar, factual knowledge, code, reasoning — all emerge as side effects.

### Self-Attention in one sentence

> "Each token sees every token in the sequence (including itself) and learns **how much to attend to each** through learned weights."

For the math (Q·K·V · softmax · scale), see the original *Attention is All You Need*. What matters for operations:

- **Attention cost is quadratic in sequence length** (O(n²)). Double context → cost and latency roughly ×4 — this is why context compression (Ch 30) exists.
- **Multi-head**: Run the same attention N times in parallel (h=8–64). Different heads are believed to specialize in different relationships (syntax · co-occurrence · coreference).

### FFN — Mixture of Experts variant

Standard FFN: all tokens pass through the same large weight matrix. **MoE** (Mixtral · DeepSeek · estimated GPT-4) replaces FFN with multiple experts (e.g., 8) and activates only a subset per token (e.g., 2). **Total parameters large, but active parameters small** — more efficient inference.

### Residual + LayerNorm

**Residual connections** like `x + Attn(LN(x))` let deep networks learn. LayerNorm (or RMSNorm) stabilizes numerics.

---

## 2. Why this matters — intuition changes how you operate

You can run LLMs without knowing these formulas. But miss these facts and you'll have problems.

| Fact | Operational consequence |
|---|---|
| **Attention is O(n²)** | Context ×2 → cost and latency ≈ ×4. Infinite context doesn't exist. |
| **Models learn at the token level** | "Count to 200 characters" is surprisingly weak (BPE tokens ≠ characters). |
| **Next-token prediction is the training goal** | Models lean toward "plausible answer" over "I don't know" (source of hallucination). |
| **Position is only stable within training distribution** | Stretch beyond training context and quality drops fast. |
| **Tokenizer varies per model** | Same Korean sentence → different token counts → different costs. |

These five facts alone speed up your diagnosis in Ch 30 (cost and latency) and Ch 19 (failure analysis) by hours.

---

## 3. Where it's used — Three training stages

The same Transformer gets tuned **three times** before it becomes what you use.

![Three training stages](../assets/diagrams/ch31-training-stages.svg#only-light)
![Three training stages](../assets/diagrams/ch31-training-stages-dark.svg#only-dark)

### Stage 1 — Pretraining (Base model)

- **Data**: Web + code + books = trillions of tokens
- **Goal**: Next-token prediction only
- **Result**: **Base model** — continues sentences, but doesn't "take instructions and answer"
- **Cost**: Tens of millions to hundreds of millions of dollars · thousands of GPUs
- **You can't do this**. Model companies run it once; you use the result.

### Stage 2 — SFT (Supervised Fine-Tuning)

- **Data**: Human-written (instruction, response) pairs — tens to hundreds of thousands
- **Goal**: Learn to "take instruction and respond"
- **Result**: **Instruct model** (first step of Llama-3-Instruct, Qwen-Chat, etc.)
- **Cost**: Tens of thousands to hundreds of thousands of dollars
- **You can start here** (LoRA — Ch 33)

### Stage 3 — RLHF / DPO

- **Data**: Humans annotate (good response, bad response) pairs — thousands to tens of thousands
- **Goal**: Align on safety · tone · factuality
- **Result**: **Chat model** (ChatGPT, Claude, final version of Llama-3-Instruct)
- **Two approaches**:
  - **RLHF**: Train a reward model → PPO reinforcement learning. Complex · expensive · unstable.
  - **DPO** (2023): No reward model; optimize directly from preference pairs. Much simpler → Ch 34
- **You can do this too** — DPO is as accessible as SFT.

---

## 4. Minimal example — Inference with Hugging Face base model

```python title="hf_base.py" linenums="1"
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

tok = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B")          # (1)!
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B",
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

prompt = "The capital of France is"
ids = tok(prompt, return_tensors="pt").to(model.device)
out = model.generate(**ids, max_new_tokens=20, do_sample=False)
print(tok.decode(out[0]))
# → "The capital of France is Paris. The capital of Germany is..."
```

1. `Llama-3.1-8B` is the base model; `Llama-3.1-8B-Instruct` is the chat model (SFT+DPO). Base doesn't "answer questions" — it just continues text.

**Observation**: Watch the base model continue plainly instead of responding in answer format. Feel the difference SFT adds.

---

## 5. Hands-on — Five operational facts

### ① Context window — truth vs. advertising

| Model | Advertised context | Effective context |
|---|---|---|
| Claude Opus 4.7 | 1M tokens | Search and summarization OK; deep reasoning safe up to 200k |
| GPT-4 Turbo | 128k | Accuracy drops after ~80k (reported) |
| Llama-3.1-8B | 128k | Without RoPE scaling, trust only up to 8k |

**Advertised and effective context differ.** Measure with benchmarks like RULER and Needle-in-Haystack.

### ② Tokenizer — Korean token cost

```python
from transformers import AutoTokenizer
t1 = AutoTokenizer.from_pretrained("gpt2")
t2 = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B")

s = "안녕하세요, 반갑습니다."
print(len(t1.encode(s)), len(t2.encode(s)))   # Example: 27 vs 11
```

Same Korean text costs 2–3× more tokens in some models. **Check your tokenizer when estimating cost.** Claude and GPT-4o have well-aligned Korean tokenizers; older GPT variants are inefficient.

### ③ Quantization — same model, different memory

| Precision | bits/param | 8B model memory | Quality |
|---|---:|---:|---|
| FP32 | 32 | 32 GB | Baseline |
| BF16 | 16 | 16 GB | Nearly identical |
| INT8 | 8 | 8 GB | Slight loss |
| INT4 (QLoRA bnb) | 4 | 4 GB | Minor loss (usually OK) |

The core trick for running 8B models on consumer GPUs — covered in Ch 33's QLoRA.

### ④ MoE models in operation

Total 671B parameters (DeepSeek-V3) but only 37B active → **inference cost matches smaller models**. But **memory = total parameters** — VRAM is the bottleneck. Hosted APIs are usually smarter.

### ⑤ Reading a model card

When adopting a new model, check:

- **Training data cutoff** — does it include our domain's timeframe?
- **Context length + safe range** (see ①)
- **License** — commercial use allowed? (Llama 3 yes, some restricted)
- **Benchmark scores** — trust benchmarks close to your domain only
- **Tokenizer + multilingual support**
- **Safety / refusal policy** — might conflict with your guardrails (Ch 28)

---

## 6. Common pitfalls

- **Diving into formulas**. Operators need attention intuition; skip Q·K·V math. Spend that time on context limits · tokenizers · costs.
- **Using base models for chat**. Base just continues text — won't answer. Use Instruct or Chat variants.
- **Assuming advertised = effective context**. 1M context doesn't mean use all 1M safely. Measure effective limits with your own domain tasks.
- **Treating tokens like characters**. "200 characters" varies wildly by model and language. Count with the tokenizer.
- **Assuming all models share a tokenizer**. SFT data built on one tokenizer but applied to another → training fails or halves efficiency.
- **Trusting active parameters for MoE memory**. VRAM = total parameters. 671B MoE is never a small model.
- **Skipping evaluation after quantization**. INT4 "almost identical on average" doesn't mean your domain is average. Always run domain tests after quantizing.

---

## 7. Operational checklist

- [ ] Record the exact model ID · version · training cutoff you're running
- [ ] Measure effective context on your representative task
- [ ] Check Korean tokenization efficiency (input to cost model)
- [ ] If quantizing, run domain regression tests
- [ ] Base / Instruct / Chat distinction is clear
- [ ] Review model card license and safety policy (align with Ch 28)
- [ ] For MoE models, split VRAM and cost budgets between hosted and self-hosted

---

## 8. Exercises & next chapter

1. Run the same prompt ("Q: What's the capital of Korea? A:") on Llama-3.1-8B-Base and Llama-3.1-8B-Instruct. Observe the difference in one sentence.
2. Pick 100 Korean sentences. Compare token counts across GPT-4o · Claude · Llama-3 · GPT-2. Table the cost differences.
3. Starting from "Attention is O(n²)", explain in a paragraph how context compression (Ch 30 ④) reduces cost.
4. For your domain, rank the five model card items by priority when adopting a new model.

**Next** → [When to Fine-Tune](32-when-to-finetune.md) — so when should you actually tune a model? :material-arrow-right:

---

## References

- Vaswani et al. (2017) *Attention is All You Need*
- Touvron et al. (2023) *Llama: Open and Efficient Foundation Language Models*
- Ouyang et al. (2022) *Training language models to follow instructions with human feedback* (RLHF)
- Rafailov et al. (2023) *Direct Preference Optimization* (DPO)
- Stanford CME 295 — *Transformers and LLMs* Lectures 1–4
- Hugging Face — *transformers* documentation
