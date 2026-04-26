# Curriculum

**AI Assistant Engineering** — building, evaluating, and operating an AI assistant that reasons, calls tools, and improves itself. From beginner to enterprise production.

!!! quote "What this book stitches together"
    Stanford **CME 295** (LLM theory) + Stanford **CS329A** (Self-Improving Agents research frontier) + **Anthropic / OpenAI / LangGraph** engineering guides — woven into one reading order. Each chapter ends with primary-source links. This is not a recap; it's the **navigation**.

---

## 1. Roadmap

![7 parts + capstone](../assets/diagrams/roadmap.svg#only-light)
![7 parts + capstone](../assets/diagrams/roadmap-dark.svg#only-dark)

!!! info "Why evaluation comes before agents"
    Part 4 (Evaluation) is placed before Part 5 (Agents) on purpose. It tracks Anthropic's recommendation: *"start with simple prompts, optimize them with evaluation, and only escalate to agents when simpler solutions fall short."*

---

## 2. Full table of contents (34 chapters)

### Part 1 — Foundations *(3 chapters)*

| # | Chapter | Core | Reference |
|---|---|---|---|
| 1 | Why models | Rules vs. models. **OpenAI's 3-criteria test** (complex decisions, brittle rules, unstructured data) | OpenAI Practical Guide |
| 2 | What is an LLM | Tokens, context, next-token prediction, hallucinations | CME 295 Lec 1–3 |
| 3 | Assistant system overview | Input → understand → retrieve → generate → verify → store → monitor → human handoff | — |

**Deliverable**: glossary · code-vs-model decision table · assistant block diagram

---

### Part 2 — Python & API *(5 chapters)*

| # | Chapter | Core |
|---|---|---|
| 4 | Getting started with the API | Basic calls, system/user, error handling, retries |
| 5 | Prompts + CoT basics | Roles, few-shot, **Chain-of-Thought**, "I don't know" |
| 6 | Structured output | JSON Schema · Pydantic · validation · fallback |
| 7 | Streaming & UX | Token streams · partial render · cancel · timeout |
| 8 | Tool Calling basics | Function calling · param generation · safe execution |

**Deliverable**: Python sample collection · structured-output PoC · first tool-calling example

---

### Part 3 — RAG *(6 chapters)*

| # | Chapter | Core |
|---|---|---|
| 9 | Why RAG | Freshness · grounding · how it differs from fine-tuning |
| 10 | Embeddings & vector search | Cosine · MMR · vector DB role |
| 11 | RAG pipeline | Ingest · chunk · embed · retrieve · generate · cite |
| 12 | Retrieval quality | Chunk size · top-k · metadata filter · **hybrid (BM25 + dense)** · reranking |
| 13 | Advanced RAG | **HyDE · Self-RAG · GraphRAG · Agentic RAG** |
| 14 | LangChain + multimodal RAG | Retriever · chain · prompt template. **PDF layout & vision embeddings** |

**Deliverable**: document QA RAG PoC · retrieval-failure analysis · pipeline diagram

---

### Part 4 — Evaluation, Reasoning, Debugging *(5 chapters)*

| # | Chapter | Core |
|---|---|---|
| 15 | What to evaluate | Retrieval · generation · end-to-end · offline vs online |
| 16 | Building an eval set | Gold set · edge cases · coverage · classification |
| 17 | LLM-as-a-Judge | Judge model design · **biases and calibration** · human calibration |
| 18 | Reasoning quality | **CoT in depth · Self-Consistency · Best-of-N · Verifier models** |
| 19 | Failure analysis | Separating prompt / retrieval / data / ranking / generation / tool failures |

**Deliverable**: eval criteria doc · eval-set draft · failure-analysis report

---

### Part 5 — Agents & LangGraph *(6 chapters)*

| # | Chapter | Core |
|---|---|---|
| 20 | What is an agent | **Model · Tool · Instruction** (OpenAI's three pieces). LLM app vs agent |
| 21 | Agent patterns | **Anthropic's 5 patterns** (chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer) + **OpenAI's 2 patterns** (manager, decentralized) |
| 22 | Tool Use in practice | Data · Action · Orchestration tools · **ACI (Agent-Computer Interface) design** · approval gates |
| 23 | LangGraph — state graphs | StateGraph · node · edge · conditional edge · reducer · checkpointer · interrupt |
| 24 | Agent memory | **Thread-scoped vs cross-thread store** · MemGPT · episodic · KV cache |
| 25 | Multi-agent | Planner/executor · researcher/writer · verifier/responder · the cost of over-decomposition |

**Deliverable**: tool-using assistant PoC · LangGraph flow diagram · agent failure scenarios

---

### Part 6 — Production *(5 chapters)*

| # | Chapter | Core |
|---|---|---|
| 26 | Production architecture | Request flow · model/retrieval split · session/memory · sync/async · rate limits |
| 27 | Observability | Logging · tracing · **prompt/dataset versioning** · latency/cost/quality metrics · LangSmith / Langfuse |
| 28 | Seven guardrails | **Relevance · safety · PII · moderation · tool · rules-based · output validation** (OpenAI's table) |
| 29 | Human-in-the-loop | **Failure thresholds** · **high-risk actions** · escalation · audit logs |
| 30 | Cost & latency | **Prompt caching** · model routing (Haiku ↔ Sonnet ↔ Opus) · Batch API · context compression |

**Deliverable**: production architecture doc · observability metric table · safety guide · cost simulator

---

### Part 7 — Models & Fine-tuning *(4 chapters)*

| # | Chapter | Core |
|---|---|---|
| 31 | Model architecture | Transformer · attention · instruction tuning · base vs chat · open vs hosted |
| 32 | When to fine-tune | Prompt / RAG / structured output come first. Data quantity and quality requirements |
| 33 | LoRA / QLoRA in practice | PEFT · QLoRA · data format · training loop |
| 34 | Small models, distillation, DPO | Latency / cost · distillation · **DPO** (in the SFT → DPO → RLHF context) |

**Deliverable**: fine-tuning needs assessment · Colab notebook · small-model deployment ideas

---

### Capstone — Self-Improving Assistant

User feedback logs → automatic failure classification → **convert to DPO data → weekly retraining loop**. A miniature of the CS329A final project.

**Deliverables**: problem statement · architecture · data composition · Prompt/RAG/Agent strategy · evaluation results · failure analysis · ops considerations · self-improvement loop design

---

## 3. Reference map

=== "University courses"

    - [CS329A — Self-Improving AI Agents (Stanford)](https://cs329a.stanford.edu/){ target=_blank } — agent research frontier
    - [CME 295 — Transformers & LLMs (Stanford)](https://cme295.stanford.edu/syllabus/){ target=_blank } — theoretical backbone
    - [CS329T — Building and Evaluating Agentic Systems (Stanford)](https://web.stanford.edu/class/cs329t/){ target=_blank } — project-based eval discipline

=== "Vendor engineering guides"

    - **Anthropic** [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents){ target=_blank } — 5 patterns
    - **OpenAI** [A Practical Guide to Building Agents (PDF)](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf){ target=_blank } — 3 components, 7 guardrails
    - **LangGraph** official docs — StateGraph · checkpointer · memory
    - Claude Cookbook · OpenAI Cookbook · LangSmith / Langfuse tutorials

=== "Recent papers (joined where used)"

    - **RAG**: Self-RAG · HyDE · GraphRAG
    - **Reasoning**: Chain-of-Thought · Self-Consistency · Tree of Thoughts · Let's Verify Step by Step · Archon
    - **Alignment**: InstructGPT (RLHF) · DPO · Constitutional AI
    - **Agents**: ReAct · Reflexion · Voyager · SWE-agent · MemGPT · CodeMonkeys
    - **Efficient FT**: LoRA · QLoRA

!!! note "Primary-source first"
    This book doesn't paraphrase summaries. Each chapter ends with primary-source links — the book is **"in what order, and how to read"** — the navigation, not the destination.

## 4. Stanford course mapping

| CME 295 | Our chapter |
|---|---|
| Lec 1–3 (Transformer · LLM) | Part 1 Ch 2, Part 7 Ch 31 |
| Lec 3 (prompting / ICL) | Part 2 Ch 5 |
| Lec 4 (training, quantization, LoRA) | Part 7 Ch 33 |
| Lec 5 (tuning, RLHF, DPO) | Part 7 Ch 34 |
| Lec 6 (reasoning) | Part 4 Ch 18 |
| Lec 7 (RAG, function calling, ReAct) | Part 3 · Part 5 |
| Lec 8 (LLM-as-a-Judge) | **Part 4 Ch 17** |

| CS329A | Our chapter |
|---|---|
| Lec 2–3 (test-time compute, verification) | **Part 4 Ch 18** |
| Lec 4–5 (ReAct, multi-step) | Part 5 Ch 20–22 |
| Lec 14 (memory) | **Part 5 Ch 24** |
| Lec 13 (SWE agents, CodeMonkeys) | Part 5 Ch 25 + Capstone |
| Lec 17 (long-horizon eval) | Part 4 Ch 15 |
| Lec 7 (self-evolution) · Final project | **Capstone** |

---

## 5. Prerequisites

<div class="infocards" markdown>

<div class="card" markdown>
#### :material-language-python: Python
Functions, classes, async basics. Virtual environments and pip.
</div>

<div class="card" markdown>
#### :material-console: Shell
Common commands and environment variables. Skip if you only use Colab.
</div>

<div class="card" markdown>
#### :material-function: Reading math
Matrix multiplication, probability, softmax. Part 1 covers what you need.
</div>

<div class="card" markdown>
#### :material-brain: ML basics
Helpful, **not required**.
</div>

</div>

## 6. What you'll be able to do

A self-check:

- [ ] Pick the right tool — code, prompt, RAG, agent, fine-tuning — for any new problem
- [ ] Decompose an assistant into **input · understand · retrieve · generate · verify · store · monitor · handoff** blocks
- [ ] Diagnose RAG failures at the **prompt / retrieval / data / ranking / generation** level
- [ ] Map a real problem to **Anthropic's 5 patterns and OpenAI's 2 patterns**
- [ ] Build a multi-step workflow with persistence, interrupts, and memory in **LangGraph**
- [ ] Improve output quality with **LLM-as-a-Judge, self-consistency, best-of-N, verifiers**
- [ ] Apply the **seven guardrails** as a checklist to a production system
- [ ] Cut cost and latency systematically with **prompt caching, model routing, batching**
- [ ] Decide whether fine-tuning is actually needed, and run **LoRA/QLoRA** on Colab when it is
- [ ] Design the **feedback log → failure classification → DPO data → retraining** self-improvement loop

## 7. Suggested grading split

- Weekly assignments 30% · hands-on PoCs 30% · mid-course design review 15% · final project 25%

**Pass tiers**:

- **Beginner** — can sketch the structure and explain the terms
- **Basic** — submits RAG · structured output · eval set
- **Advanced** — agent + ops design + guardrails + improvement report
- **Enterprise** — finishes the capstone (Self-Improving Assistant)

## 8. 14-week schedule

| Week | Content |
|---|---|
| 1 | Ch 1–2: why models · LLM basics |
| 2 | Ch 3, 4: assistant structure · first API call |
| 3 | Ch 5, 6: prompts + CoT · structured output |
| 4 | Ch 7, 8: streaming/UX · tool calling |
| 5 | Ch 9, 10: why RAG · embeddings/vector search |
| 6 | Ch 11, 12: pipeline · retrieval quality |
| 7 | Ch 13, 14: Advanced RAG · LangChain + multimodal |
| 8 | Ch 15, 16: eval criteria · eval set |
| 9 | Ch 17, 18: LLM-as-Judge · reasoning quality |
| 10 | Ch 19, 20: failure analysis · what is an agent |
| 11 | Ch 21, 22: agent patterns · tool use |
| 12 | Ch 23, 24: LangGraph · agent memory |
| 13 | Ch 25, 26, 27: multi-agent · production architecture · observability |
| 14 | Ch 28, 29, 30 · Part 7 overview · capstone review |

Part 7 (fine-tuning) is treated as a **deep-dive option**. The 14-week course covers Parts 1–6; budget 16–18 weeks for all 34 chapters.

## 9. Priority guide

**Must do first** — code vs models · LLM basics · structured output · RAG · evaluation · **agent patterns · guardrails**

**Then** — agent depth · production architecture · observability · **cost/latency** · **agent memory**

**Later** — fine-tuning · distillation · small models

## 10. One sentence

> Don't go deep into models first. Learn the blocks of a real assistant and design clearly across **Prompt / RAG / Agent / Evaluation / Operations / Guardrails**.

---

[:material-arrow-right-box: Start Part 1](../part1/01-why-model.md){ .md-button .md-button--primary }
[:material-cog: How this book works](system.md){ .md-button }
