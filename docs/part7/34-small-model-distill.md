# Ch 34. 소형모델 · 증류 · DPO

!!! abstract "이 챕터에서 배우는 것"
    - **소형 모델** 의 자리 — 언제 큰 모델 대신 작은 모델
    - **Distillation** (증류) — Teacher 가 Student 를 가르치는 패턴
    - **DPO** vs RLHF — reward model 없이 정렬
    - SFT → DPO 운영 파이프라인
    - 합성 데이터의 함정 (편향 증폭 · 할루시 복제)
    - 6대 함정 (DPO 를 SFT 없이 · 증류 데이터 검증 부족 · Constitutional AI 환상 · 학습 분포 외 평가 부재 · 작은 모델로 못 푸는 문제 · 할루시 복제)
    - **Part 7 마무리** + **캡스톤으로 가는 다리**

!!! quote "전제"
    [Ch 32](32-when-to-finetune.md) 결정 트리 통과. [Ch 33](33-lora-qlora.md) LoRA 손맛 있음. 이 챕터는 큰 그림 + 다음 단계.

---

## 1. 개념 — 작은 모델의 자리

큰 모델 (Opus · GPT-4) 의 답변 품질을 작은 모델 (Haiku · 8B) 로 가져올 수 있다면 비용이 30배 빠집니다 (Ch 30).

방법 두 가지:

| 방식 | 무엇을 | 어디에 |
|---|---|---|
| **Domain SFT** (Ch 33) | 도메인 데이터로 작은 모델 직접 학습 | 라벨 데이터 있을 때 |
| **Distillation** | 큰 모델이 만든 답을 작은 모델이 따라 학습 | 라벨 데이터 부족할 때 |

증류는 **라벨링 비용을 큰 모델로 대체** 하는 패턴 — 사람이 답을 만드는 대신 Teacher 가 만들어 줍니다.

![증류 파이프라인](../assets/diagrams/ch34-distillation.svg#only-light)
![증류 파이프라인](../assets/diagrams/ch34-distillation-dark.svg#only-dark)

5 단계:

1. **Unlabeled queries** — 실로그 또는 합성 (수K~수만)
2. **Teacher 추론** — 큰 모델로 답 생성
3. **Filter** — 품질 검증 (judge · 규칙). **이 단계가 가장 중요**
4. **Student SFT (LoRA)** — Ch 33 그대로
5. **Deploy** — 작은 모델로 30× 저렴 운영

> "Distillation 은 학습 알고리즘보다 **데이터 큐레이션** 이 결과를 결정한다."

---

## 2. 왜 필요한가 — 증류가 SFT 보다 좋을 때

| 상황 | SFT 직접 | Distillation |
|---|---|---|
| 정답 라벨 있음 | ◎ | △ (불필요) |
| 정답이 모호 (긴 답변) | △ (라벨 어려움) | ◎ |
| 라벨러 비용 > Teacher API 비용 | △ | ◎ |
| 도메인 톤·스타일 학습 | ◎ | ◎ |
| 도메인 사실 정확도 | △ | △ (RAG 가 답) |

**라벨링 비용 vs Teacher API 비용** 으로 가르는 게 가장 실용적. 5K 샘플을 사람이 만들면 $5K, Teacher 로 만들면 $150 (Opus 가격으로).

---

## 3. 어디에 쓰이는가 — 정렬 3 방식 비교

LLM 의 마지막 정렬 단계 (Ch 31 의 Stage 3) 도 우리가 건드릴 수 있습니다.

![정렬 3 방식](../assets/diagrams/ch34-alignment-compare.svg#only-light)
![정렬 3 방식](../assets/diagrams/ch34-alignment-compare-dark.svg#only-dark)

| 방식 | 데이터 | 알고리즘 | 비용 | 우리도? |
|---|---|---|---|---|
| **SFT** | (q, a) | next-token loss | $$ | ◎ (Ch 33) |
| **DPO** | (q, ✓, ✗) | preference loss · reward 식 X | $$$ | ◎ |
| **RLHF** | (q, ✓, ✗) → reward model → PPO | RL 루프 | $$$$ | △ (대형사만) |

### DPO 한 줄 직관

DPO 는 **reward model + PPO 의 두 단계를 한 식**으로 합쳤습니다:

$$
\mathcal{L}_{\text{DPO}} = -\log \sigma\left(\beta \log \frac{\pi_\theta(y_w|x)}{\pi_{\text{ref}}(y_w|x)} - \beta \log \frac{\pi_\theta(y_l|x)}{\pi_{\text{ref}}(y_l|x)}\right)
$$

직관: "선호된 답(y_w)의 확률을 거절된 답(y_l)보다 높여라". 모델 두 개 (학습 중인 π_θ, 동결된 ref) 가 필요하지만 reward model 은 불필요.

**현실에서 의미**: 5K 선호 쌍이면 DPO 가능. RLHF 는 같은 데이터로 시작해도 reward model 학습 + PPO 까지 해야 함 → 보통 우리는 DPO 까지만.

### Constitutional AI — 사람 라벨 줄이는 변형

Anthropic 의 Constitutional AI 는 **사람의 선호 라벨을 LLM 자기 비평으로 대체**:

1. 모델이 답 생성
2. "이 답이 헌법 (정책) 에 부합하는가?" 를 모델 자신이 평가
3. 부적합 → 자체 수정
4. (오리지널, 수정본) 쌍으로 DPO

장점: 사람 라벨 비용 ↓. 단점: 모델 편향이 그대로 헌법 평가에 들어감 → **인간 검수 단계가 여전히 필요**.

---

## 4. 최소 예제 — DPO 30 줄

```python title="dpo_train.py" linenums="1" hl_lines="6 13 22"
from datasets import Dataset
from trl import DPOTrainer, DPOConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model

# 데이터 — 선호 쌍                                                       (1)
pairs = [
    {"prompt": "환불 가능한가요?",
     "chosen": "네, 30일 안에 가능합니다. 영수증을 준비해주세요.",
     "rejected": "환불 안 됩니다."},
    # ...
]
ds = Dataset.from_list(pairs)

base_id = "meta-llama/Llama-3.1-8B-Instruct"                            # (2)!
tok = AutoTokenizer.from_pretrained(base_id)
model = AutoModelForCausalLM.from_pretrained(base_id, torch_dtype="bfloat16", device_map="auto")
model = get_peft_model(model, LoraConfig(r=16, lora_alpha=32, target_modules=["q_proj","v_proj"]))

trainer = DPOTrainer(
    model=model, tokenizer=tok, train_dataset=ds,
    args=DPOConfig(                                                      # (3)!
        output_dir="dpo_out", per_device_train_batch_size=2,
        gradient_accumulation_steps=8, num_train_epochs=1,
        learning_rate=5e-6, beta=0.1, bf16=True,
    ),
)
trainer.train()
trainer.save_model("dpo_out/adapter")
```

1. 핵심: `prompt · chosen · rejected` 세 컬럼.
2. **DPO 는 SFT 모델 위에서 시작**. base 에 바로 DPO 하지 말 것.
3. `learning_rate` 가 SFT 보다 훨씬 작음 (5e-6). `beta` 는 KL 제약 강도 (0.1 표준).

### 증류 데이터 생성

```python title="distill_collect.py" linenums="1"
from anthropic import Anthropic
client = Anthropic()

queries = load_queries("logs.jsonl")[:5000]
out = []
for q in queries:
    a = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        messages=[{"role":"user","content": q}]
    ).content[0].text
    if pass_filter(q, a):                                               # (1)!
        out.append({"text": format_chat(q, a)})
save_jsonl("distill_train.jsonl", out)
```

1. **필터가 중요**. judge LLM (Ch 17) + 규칙 (길이·금칙어·형식). 필터 통과율은 30~70% 가 보통.

---

## 5. 실전 — SFT → DPO 운영 파이프라인

```
실로그 → SFT 데이터 (q,a) → SFT (LoRA · Ch 33)
                                      ↓
                          베이스 SFT 모델
                                      ↓
              사람이 (good, bad) 쌍 1K~5K 만들기
                                      ↓
                 DPO (LoRA · 위 §4) → Aligned 모델
                                      ↓
            도메인 평가 + safety regression (Ch 28)
                                      ↓
                    배포 (Ch 26 · adapter swap)
```

**한 분기 (3개월) 이 한 사이클**. SFT 까지 1개월, DPO 데이터 수집 1개월, DPO + 검증 1개월.

### 평가 — 분포 외(out-of-distribution) 가 진짜 신호

학습한 분포 안에서는 다 잘 됨. 진짜 평가는:

- **Hold-out 도메인**: 학습 안 한 비슷한 도메인 — 일반화 측정
- **Adversarial**: jailbreak · 인젝션 · 함정 (Ch 28)
- **Safety regression**: 정렬이 깨지지 않았는지 (Ch 28 가드레일 통과율)
- **회귀 셋**: 이전 버전이 잘 풀던 케이스 (regression.jsonl · Ch 19)

DPO 후 가장 흔한 사고: **거절 톤은 좋아졌는데 일반 답변이 짧아짐**. 분포 외 평가 없이는 못 잡음.

### Cost 모델

| 단계 | 비용 (예) |
|---|---:|
| SFT 데이터 5K 라벨링 | $2K~5K |
| SFT 학습 (LoRA QLoRA) | $50 |
| DPO 데이터 1K 쌍 | $1K~3K |
| DPO 학습 | $50 |
| 평가 인프라 (Ch 16) | $200/월 |
| **합계 (1 분기)** | **$3~8K** |

운영 절감 (Opus → Haiku 30× 저렴) 가 위 비용을 회수해야 ROI 양수. 1년 단위로 계산.

---

## 6. 자주 깨지는 포인트

- **DPO 를 SFT 없이**. base 모델에 바로 DPO 하면 학습 안 됨. SFT 가 "응답 형식" 을 가르친 다음에야 DPO 가 "어떤 응답이 좋은가" 를 가르칠 수 있음.
- **증류 데이터 검증 부족**. Teacher 가 만든 답을 그대로 학습 → Teacher 의 편향·할루시가 Student 에 그대로 복제. 필터(judge + 규칙) 가 핵심.
- **Constitutional AI 환상**. "사람 라벨 없이도 정렬 가능" 으로 들리지만 실제론 **인간 검수 단계가 여전히 필요** — 자동 평가의 편향 검증 때문.
- **분포 외 평가 부재**. 학습한 분포 안에서만 평가하면 일반화 실패를 못 잡음. hold-out · adversarial · regression 3축 필수.
- **작은 모델로 못 푸는 문제**. 복잡 추론이 필요한 작업을 Haiku 에 SFT 시킨다고 풀리지 않음. **Capability 한계는 학습으로 못 넘는다**.
- **Teacher 할루시 복제**. Opus 도 가끔 사실 오류 → 그대로 학습되면 작은 모델이 같은 오류 안정적으로 반복. 필터에 사실 검증 추가.
- **DPO beta 잘못**. 너무 크면 (β > 0.5) ref 에서 못 벗어남, 너무 작으면 (β < 0.05) ref 무시 → 학습 불안정. **0.1 시작**.
- **chosen/rejected 가 형식만 다름**. 의미 차이가 거의 없는 쌍 → 학습 안 됨. 명확하게 다른 톤·정확도·완성도여야 함.

---

## 7. 운영 체크리스트

- [ ] Distillation 시 Teacher 답에 필터 (judge + 규칙) 통과율 모니터링
- [ ] DPO 는 SFT 모델 위에서만
- [ ] DPO 데이터의 chosen/rejected 차이가 명확
- [ ] beta=0.1 시작, lr 5e-6 ~ 1e-5
- [ ] 분포 외 평가 3축 (hold-out · adversarial · regression)
- [ ] Safety regression 자동화 (Ch 28 가드레일 통과율)
- [ ] 작은 모델의 capability 한계 명시 (라우터로 hard 는 large model)
- [ ] 분기 사이클 (SFT → DPO → 평가 → 배포) 운영 가능
- [ ] 1년 ROI 계산 (Ch 32 §5)
- [ ] adapter 메타데이터 + 학습 데이터 hash + base 버전 기록

---

## 8. 연습문제 & Part 7 마무리

1. 5K query 가 있고 라벨러 예산이 $500 뿐일 때 distillation 으로 SFT 데이터를 만드는 절차 + 필터 정책을 설계하라.
2. SFT 모델의 거절 톤이 너무 차갑다. DPO 로 정중하게 바꾸려면 chosen/rejected 쌍을 어떻게 만들 것인가? 5개 예시.
3. 8B SFT+DPO 모델이 분포 외 평가에서 baseline 대비 -3pt 회귀했다. 진단 + 대응 3 옵션을 적어라.
4. 우리 도메인에서 "큰 모델로만 풀리는" 작업 1개를 식별하고, 그것을 작은 모델로 옮기지 못하는 이유를 capability 관점에서 설명하라.

---

## Part 7 마무리 — 모델·파인튜닝 졸업 상태 5종

| # | 산출물 | 어느 챕터 |
|---|---|---|
| ① | **모델 카드 검토 템플릿** + 컨텍스트 한도·토크나이저·라이선스 | Ch 31 |
| ② | **파인튜닝 결정서** (4 게이트 통과 여부) | Ch 32 |
| ③ | **LoRA PoC 노트북** + 효과 측정 결과 | Ch 33 |
| ④ | **SFT → DPO 운영 파이프라인 설계** | Ch 34 |
| ⑤ | **소형 모델 라우팅 전략** (Ch 30 과 연결) | Ch 30 + 34 |

---

## 캡스톤으로 가는 다리 — Self-Improving Assistant

Part 1~7 의 모든 조각이 합쳐지는 지점이 캡스톤입니다.

| Part | 조각 | 캡스톤에서의 역할 |
|---|---|---|
| 1 | LLM 기초 | 무엇이 가능한가 |
| 2 | API · 프롬프트 · 도구 | 호출 인터페이스 |
| 3 | RAG | 도메인 사실 |
| 4 | 평가 · 디버깅 | 자기 측정 |
| 5 | Agent · LangGraph · 메모리 | 루프 + 상태 |
| 6 | 가드레일 · 관측 · 비용 | 운영 |
| 7 | 모델 · 파인튜닝 | 자기 개선 (실패 사례를 학습 데이터로) |

**Self-Improving Assistant** 는 이 7개 조각을 한 시스템에 묶고, **사용자 피드백 → 평가셋 자동 합류 → 분기 SFT/DPO → 배포** 의 폐쇄 루프를 돌립니다.

**다음** → [캡스톤: Self-Improving Assistant](../capstone/self-improving.md) 로.

---

## 원전

- Rafailov et al. (2023) *Direct Preference Optimization: Your Language Model is Secretly a Reward Model*
- Ouyang et al. (2022) *InstructGPT* (RLHF 원전)
- Bai et al. (2022) *Constitutional AI* (Anthropic)
- Hinton et al. (2015) *Distilling the Knowledge in a Neural Network*
- Hugging Face TRL — *DPOTrainer* docs
- Stanford CME 295 Lec 5
