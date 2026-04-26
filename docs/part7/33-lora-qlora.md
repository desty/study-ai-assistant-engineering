# Ch 33. LoRA / QLoRA 실전 (Colab)

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part7/ch33_lora_qlora.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **Full FT vs LoRA** — 무엇이 학습되나
    - **QLoRA** — 4-bit 양자화로 Colab T4 한 장에 8B 모델 학습
    - rank `r` · alpha `α` · target_modules 의 의미와 시작 값
    - **Hugging Face PEFT + TRL SFTTrainer** 30줄 골격
    - VRAM 분배 — 어디서 OOM 나는가
    - Adapter 저장 · 로딩 · merge
    - 6대 함정 (rank 너무 크게 · target_modules 빠뜨림 · eval loss 만 보기 · seq_len 폭주 · 베이스 모델 mismatch · 학습률 잘못)

!!! quote "전제"
    [Ch 32](32-when-to-finetune.md) 의 4 게이트 통과 + PoC 신호. 이 챕터는 손맛 — 노트북 한 번 돌리는 것이 목표.

---

## 1. 개념 — Full FT 와 LoRA 의 차이 한 장

![Full FT vs LoRA](../assets/diagrams/ch33-lora-vs-full.svg#only-light)
![Full FT vs LoRA](../assets/diagrams/ch33-lora-vs-full-dark.svg#only-dark)

**Full FT**: 모델의 모든 가중치 W 를 갱신. 가중치가 100억 개면 100억 개 다 업데이트.

**LoRA** (Low-Rank Adaptation): W 는 동결, 옆에 작은 두 행렬 A·B 만 학습.

$$
W' = W + A \cdot B \quad (A: d \times r,\ B: r \times d,\ r \ll d)
$$

- 학습 가능 파라미터 ≈ **전체의 0.1~1%**
- 베이스 모델은 그대로 → 여러 도메인 adapter 를 동시에 가지고 swap 가능
- 추론 시 `W + AB` 로 합치면 추가 지연 0

> "8B 모델 LoRA 학습은 노트북 GPU 한 장으로 가능. Full FT 는 H100 8장 클러스터 필요."

### QLoRA = LoRA + 4-bit 양자화

LoRA 만으로도 충분히 가벼운데, 베이스 모델을 **4-bit 로 압축** 해서 메모리에 올리면 더 가벼워집니다. 8B 모델이 ~5GB 로 줄어 Colab T4 (16GB) 한 장에 돌아감.

핵심 트릭: **베이스는 4-bit, LoRA 행렬은 16-bit**. 학습 정밀도는 LoRA 에서만 필요하므로.

---

## 2. 왜 필요한가 — 비용·속도·운영

| 측면 | Full FT | LoRA | QLoRA |
|---|---|---|---|
| VRAM (8B) | 80+ GB | 16~24 GB | 8~10 GB |
| 학습 시간 | 며칠 | 수 시간 | 수 시간 |
| 체크포인트 | 16~32 GB | 50~500 MB | 50~500 MB |
| GPU | H100 ×4~8 | A100 ×1 / RTX 4090 | T4 (Colab) |
| 비용 (1 회) | $5K~$50K | $50~$500 | $0~$50 |
| 운영 swap | 어렵 (모델 통째) | 쉬움 (adapter 만) | 쉬움 |

**대부분의 도메인 SFT 는 LoRA 면 충분**. Full FT 는 base 모델 자체를 만들 때만 필요.

---

## 3. 어디에 쓰이는가 — Hyperparameter 시작 값

| 파라미터 | 의미 | 시작값 | 튜닝 방향 |
|---|---|---|---|
| `r` (rank) | 학습 capacity | 16 | 적으면 ↑ (32, 64), 과적합 ↓ (8) |
| `lora_alpha` | 스케일 (보통 2r) | 32 | r×2 가 무난 |
| `target_modules` | 어디에 LoRA 부착 | `q_proj, v_proj` | 더 강하게: + `k_proj, o_proj`, FFN |
| `lora_dropout` | 정규화 | 0.05 | 과적합 시 0.1 |
| `learning_rate` | 학습률 | 2e-4 | LoRA 는 full FT 보다 큼 |
| `num_train_epochs` | epoch | 3 | early stop 권장 |
| `batch_size` | 배치 | 4 (gradient_accumulation 4) | VRAM 한도 |
| `max_seq_length` | 시퀀스 길이 | 1024 | 데이터 분포 따라 |

**rank 16 + α=32 + q,v_proj** 가 가장 흔한 시작점. 안 되면 target_modules 늘리고, 그래도 안 되면 r 키움.

---

## 4. 최소 예제 — Colab 30줄 골격

```python title="qlora_train.py" linenums="1" hl_lines="9 18 28 33"
import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig

MODEL = "meta-llama/Llama-3.1-8B-Instruct"

bnb = BitsAndBytesConfig(                                                # (1)!
    load_in_4bit=True, bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
)
tok = AutoTokenizer.from_pretrained(MODEL)
tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(MODEL, quantization_config=bnb, device_map="auto")
model = prepare_model_for_kbit_training(model)

lora_cfg = LoraConfig(                                                   # (2)!
    r=16, lora_alpha=32, lora_dropout=0.05,
    target_modules=["q_proj", "v_proj"],
    bias="none", task_type="CAUSAL_LM",
)
model = get_peft_model(model, lora_cfg)
model.print_trainable_parameters()                                       # ≈ 0.5%

ds = load_dataset("json", data_files="data/train.jsonl", split="train")  # (3)!

trainer = SFTTrainer(
    model=model, tokenizer=tok, train_dataset=ds,
    args=SFTConfig(
        output_dir="out", per_device_train_batch_size=4,
        gradient_accumulation_steps=4, num_train_epochs=3,
        learning_rate=2e-4, bf16=True,
        logging_steps=10, save_strategy="epoch",
        max_seq_length=1024,                                              # (4)!
    ),
)
trainer.train()
trainer.save_model("out/adapter")                                        # ~50MB
```

1. NF4 양자화 + double-quant + bf16 compute. 표준 QLoRA 설정.
2. r=16 · alpha=32 · q/v 만. 가장 무난한 시작.
3. Chat 데이터는 미리 `apply_chat_template` 으로 전처리하면 안전 (jsonl 의 `text` 필드).
4. seq_len 1024 면 T4 OOM 안 남. 길게 쓰면 batch 줄여야.

### 데이터 포맷

```json title="data/train.jsonl"
{"text": "<|im_start|>user\n환불 정책이 어떻게 되나요?<|im_end|>\n<|im_start|>assistant\n저희는 30일 환불을...<|im_end|>"}
{"text": "..."}
```

또는 `messages` 형식으로 두고 토크나이저의 `apply_chat_template` 으로 자동 변환. 모델별 special token 다르므로 **베이스 모델의 chat template 사용** 이 안전.

### 학습 후 — Adapter 만 저장

```python
trainer.save_model("out/adapter")            # 어댑터만 ~50MB
# tokenizer 도 같이
tok.save_pretrained("out/adapter")
```

추론 시:

```python
from peft import PeftModel
base = AutoModelForCausalLM.from_pretrained(MODEL, quantization_config=bnb, device_map="auto")
model = PeftModel.from_pretrained(base, "out/adapter")                  # adapter 부착
```

또는 **merge** 하여 단일 가중치로 저장 (배포 단순화):

```python
merged = model.merge_and_unload()
merged.save_pretrained("out/merged")        # 베이스 + adapter 합친 통짜
```

---

## 5. 실전 — VRAM 분배와 트러블슈팅

QLoRA 학습 중 메모리는 보통 이렇게 분배됩니다.

![QLoRA pipeline](../assets/diagrams/ch33-qlora-pipeline.svg#only-light)
![QLoRA pipeline](../assets/diagrams/ch33-qlora-pipeline-dark.svg#only-dark)

| 항목 | 비중 | 줄이기 |
|---|---:|---|
| Base (4bit) | ~55% | 모델 작게 (3B/7B) |
| Activations | ~20% | seq_len ↓ · batch ↓ · grad checkpoint |
| Optimizer (Adam) | ~10% | paged_adamw_8bit |
| LoRA + grads | ~5% | r ↓ |
| Headroom | ~10% | 여유 |

**OOM 진단 순서**:

1. `gradient_checkpointing=True` 켰는가? (activation 메모리 절반)
2. `optim="paged_adamw_8bit"` 인가? (옵티마이저 4배 압축)
3. `max_seq_length` 가 데이터 분포 대비 너무 큰가?
4. `per_device_train_batch_size` 1 로 내려도 안 되면 모델이 큼

### 학습 중 모니터링

```python
# 또는 Weights & Biases
trainer.add_callback(...)  # 또는 args.report_to=["wandb"]
```

| 신호 | 의미 |
|---|---|
| Train loss 가 천천히 감소 | OK |
| Train loss 가 0 으로 수렴 | 과적합 의심 (데이터 너무 적음) |
| Train loss 가 안 떨어짐 | LR 너무 작거나 target_modules 부족 |
| Eval loss 가 train loss 따라감 | OK |
| Eval loss 가 train 보다 빨리 ↑ | 과적합 → epoch ↓ |
| 첫 배치 OOM | seq_len 또는 batch ↓ |

### Eval — loss 만 보지 말 것

학습 loss 는 **데이터 분포에서의 perplexity** 일 뿐. 우리 도메인 평가셋의 **정확도/F1/Judge 점수** 가 진짜 신호.

```python
# 매 epoch 끝나고 eval set 으로 추론 → Ch 17 LLM-as-Judge
preds = [generate(model, q) for q, _ in eval_set]
score = judge(preds, eval_set)                                          # (1)!
```

1. Ch 17 Judge 또는 도메인 정확도 metric. baseline (no FT) 대비 +5pt 이상이 검증 통과.

### Adapter merge vs swap

| 운영 패턴 | 장점 | 단점 |
|---|---|---|
| **Merge** (단일 가중치) | 추론 단순 · 지연 0 | 도메인별 모델 따로 보관 |
| **Swap** (adapter 부착) | 한 베이스 + N adapter · 빠른 swap | 추론 코드에 PEFT 필요 |

도메인 5개 = adapter 5개를 한 서버에서 swap 운영하면 메모리 절감.

---

## 6. 자주 깨지는 포인트

- **rank 를 처음부터 64+ 로**. 작은 데이터(1K~5K)에서 r=64 면 과적합. **r=16 부터** + 효과 측정 후 키움.
- **target_modules 빠뜨림**. `q_proj, v_proj` 만이 시작 — 표현력 부족하면 `k_proj, o_proj` 추가, 그 다음 FFN (`gate_proj, up_proj, down_proj`).
- **eval loss 만 보고 판단**. loss 떨어졌는데 도메인 정확도는 그대로일 수 있음. **도메인 평가셋이 진짜 메트릭** (Ch 32 §5 PoC 신호 +5pt).
- **seq_len 폭주**. 학습 데이터 분포 안 보고 max_seq_length=4096 → OOM. p95 길이 + 안전 margin (×1.2) 정도가 적정.
- **베이스 모델 mismatch**. 학습은 Llama-3.1-8B-Instruct 로, 추론은 base 로 → 결과 엉망. tokenizer + 모델 ID 일치 확인.
- **학습률 잘못**. Full FT 의 1e-5 를 LoRA 에 쓰면 학습 안 됨. **LoRA 는 1e-4 ~ 5e-4** 가 일반.
- **체크포인트 매 step 저장**. 디스크 폭주. `save_strategy="epoch"` + `save_total_limit=2` 권장.
- **양자화 충돌 (bf16 vs fp16)**. T4 는 fp16 호환, A100/H100 은 bf16 권장. 모델 dtype + bnb_4bit_compute_dtype 정렬.

---

## 7. 운영 체크리스트

- [ ] PoC (100~500 샘플) 로 baseline +5pt 신호 본 후 본 학습
- [ ] tokenizer · 베이스 모델 · adapter 의 ID/버전 매칭 기록
- [ ] `chat_template` 적용 일관 (학습 = 추론)
- [ ] 평가는 도메인 metric (loss + Judge + 정확도)
- [ ] 회귀 테스트 (이전 adapter 와 같은 평가셋 비교)
- [ ] adapter 메타데이터 저장 — 학습 데이터 hash, hyperparam, base 버전
- [ ] safety regression — 학습으로 거절 정책이 깨지지 않았나 (Ch 28)
- [ ] 양자화 후 추론 dtype 정합 (fp16/bf16)
- [ ] merge 한 모델 vs swap 운영 패턴 결정
- [ ] 비용 모델 — GPU 시간 + 라벨링 + 운영 (1년 ROI · Ch 32)

---

## 8. 연습문제 & 다음 챕터

1. Llama-3.1-8B-Instruct 를 받아 200개 (q,a) 샘플로 PoC LoRA 를 돌려라. baseline 대비 효과를 도메인 평가셋에서 측정.
2. r=8 / 16 / 32 의 세 설정으로 같은 데이터 학습하고 도메인 정확도 + 학습 시간 + adapter 크기를 표로.
3. Adapter swap 운영을 가정하라. 베이스 1개 + 도메인 adapter 3개 (CS · 기술지원 · HR) 의 메모리·지연 비교 설계.
4. 학습 중 OOM 이 첫 배치에서 났다. 진단 5 단계 (위 §5) 를 적용하고 어디서 해결되는지 시뮬레이션.

**다음 챕터** — 소형 모델·증류·DPO · Part 7 마무리. [Ch 34](34-small-model-distill.md) 로.

---

## 원전

- Hu et al. (2021) *LoRA: Low-Rank Adaptation of Large Language Models*
- Dettmers et al. (2023) *QLoRA: Efficient Finetuning of Quantized LLMs*
- Hugging Face — *PEFT* docs · *TRL SFTTrainer* docs
- Stanford CME 295 Lec 4
