# Ch 31. 모델 아키텍처 개요

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part7/ch31_model_arch.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **Transformer 블록**의 단순화된 해부 — embedding · self-attention · FFN · residual
    - **다음 토큰 예측**이라는 단일 학습 목표
    - **3 학습 단계** — Pretraining → SFT → RLHF/DPO 가 하는 일의 차이
    - **Base vs Instruct vs Chat** 모델의 의미
    - **MoE · RoPE** 같은 현대 변형의 위치 한 줄
    - **수식 깊이 빠지지 말 것** — 직관 우선
    - 운영자 관점에서 알면 도움이 되는 5가지 (컨텍스트 한도 · 토크나이저 · 양자화 · MoE · 모델 카드)

!!! quote "전제"
    Part 1·2 정도. 미적분/선형대수가 익숙하면 좋지만 필수는 아님. 이 챕터의 목적은 **외부에서 모델을 잘 다루기 위한 충분한 직관** 이지, 모델 만드는 법이 아니다.

---

## 1. 개념 — Transformer 블록 한 장

LLM 은 거의 다 **Transformer**(2017) 변형입니다. 현대 모델은 N개 (보통 24~80) 의 같은 블록을 쌓고, 각 블록은 두 가지 일만 합니다.

![Transformer 블록](../assets/diagrams/ch31-transformer-block.svg#only-light)
![Transformer 블록](../assets/diagrams/ch31-transformer-block-dark.svg#only-dark)

| 단계 | 무엇을 하나 | 역할 |
|---|---|---|
| **Tokens** | 문자열 → 정수 시퀀스 | "안녕 세계" → `[101, 5023, ...]` |
| **Token Embedding** | 정수 → 고차원 벡터 (d_model) | 의미 표현 |
| **Position (RoPE)** | 위치 정보 주입 | "어순" 을 넣음 |
| **Self-Attention** × N | 토큰끼리 정보 교환 | 문맥 의존 표현 |
| **FFN (Feed-Forward)** × N | 비선형 변환 | 표현력 |
| **LM Head + Softmax** | hidden → vocab 분포 | 다음 토큰 확률 |

**모든 LLM 의 학습 목표는 단 하나**: 다음 토큰의 확률 분포 예측. 그게 끝입니다. "안녕 ?" 다음에 "세계" 가 올 확률을 높이는 일을 수조 번 반복하면 — 문법, 사실 지식, 코드, 추론 같은 것이 부수적으로 들어옵니다.

### Self-Attention 한 줄 직관

> "각 토큰이 자기 자신을 포함해 시퀀스의 모든 토큰을 보고, **누구에게 얼마나 주목할지** 가중치를 학습한다."

수식 (Q·K·V · softmax · scale) 은 *Attention is All You Need* 원전을 참고. 운영자 관점에서 더 중요한 사실:

- **Attention 비용은 시퀀스 길이의 제곱** (O(n²)). 컨텍스트가 길어지면 비용·지연이 빠르게 폭주 — Ch 30 의 컨텍스트 압축이 왜 필요한지의 근원.
- **Multi-head**: 같은 attention 을 여러 개 (h=8~64) 병렬로. 다른 head 가 다른 종류의 관계 (구문 · 공기 · 코어퍼런스) 를 본다고 알려져 있음.

### FFN — Mixture of Experts 변형

원래 FFN 은 모든 토큰이 같은 큰 가중치 행렬을 통과. **MoE** (Mixtral · DeepSeek · GPT-4 추정) 는 FFN 자리에 여러 expert (예: 8개) 를 두고 각 토큰마다 일부 (예: 2개) 만 활성화. **총 파라미터는 크지만 활성 파라미터는 작음** — 비용·지연 효율.

### Residual + LayerNorm

`x + Attn(LN(x))` 같은 **잔차 연결**. 깊은 네트워크가 학습되게 하는 핵심 트릭. 수치 안정화는 LayerNorm (또는 RMSNorm).

---

## 2. 왜 필요한가 — 직관이 운영을 바꾼다

수식을 몰라도 LLM 을 운영할 수 있습니다. 그러나 다음 사실은 모르고 운영하면 사고가 납니다.

| 사실 | 운영 결과 |
|---|---|
| **Attention 은 O(n²)** | 컨텍스트 ×2 → 비용·지연 ≈ ×4. 무한 컨텍스트 X |
| **모델은 토큰 단위로 학습** | "글자 수 세기" 가 의외로 약함 (BPE 토큰 ≠ 글자) |
| **다음 토큰 예측이 학습 목표** | "정답을 모름" 보단 "그럴듯한 답을 만듦" 으로 기울어짐 (할루시네이션의 근원) |
| **Position 은 학습 분포 안에서만 안정** | 학습 컨텍스트보다 길게 쓰면 품질 급락 |
| **Tokenizer 는 모델별로 다름** | 같은 한글 문장도 모델에 따라 토큰 수 다름 → 비용 차이 |

이 5개를 손에 가지고 있으면 Ch 30 (비용·지연) · Ch 19 (실패 분석) 의 진단이 훨씬 빨라집니다.

---

## 3. 어디에 쓰이는가 — 3 학습 단계

같은 Transformer 모델이 **세 번** 다듬어지면서 우리가 쓰는 형태가 됩니다.

![학습 3단계](../assets/diagrams/ch31-training-stages.svg#only-light)
![학습 3단계](../assets/diagrams/ch31-training-stages-dark.svg#only-dark)

### Stage 1 — Pretraining (Base 모델)

- 데이터: 웹 + 코드 + 책 = 수T (테라) 토큰
- 목표: 다음 토큰 예측만
- 결과: **Base 모델** — 문장은 이어가지만 "질문하면 답한다" 는 행동은 없음
- 비용: 수십M~수억 달러 · GPU 수천 대
- **우리는 못 함**. 모델 회사가 한 번 한 결과를 받아 쓴다.

### Stage 2 — SFT (Supervised Fine-Tuning)

- 데이터: 사람이 쓴 (지시, 응답) 쌍 수만~수십만
- 목표: "지시받으면 응답한다" 는 행동 학습
- 결과: **Instruct 모델** (Llama-3-Instruct, Qwen-Chat 등의 첫 단계)
- 비용: 수K~수십K 달러
- **여기서부터 우리가 건드릴 수 있음** (LoRA — Ch 33)

### Stage 3 — RLHF / DPO

- 데이터: 사람이 (좋은 답, 나쁜 답) 쌍을 만듦. 수K~수만
- 목표: 안전·톤·사실성 정렬
- 결과: **Chat 모델** (ChatGPT, Claude, Llama-3-Instruct 의 최종)
- 두 방식:
  - **RLHF**: reward model 학습 → PPO 강화학습. 복잡·비쌈·불안정
  - **DPO** (2023): reward model 없이 선호 쌍에서 직접 미분. 훨씬 단순 → Ch 34
- **우리도 가능** — DPO 가 SFT 만큼 접근성이 좋아짐

---

## 4. 최소 예제 — Hugging Face 로 base 모델 추론

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

1. `Llama-3.1-8B` 가 base 모델, `Llama-3.1-8B-Instruct` 가 SFT+DPO 거친 chat 모델. base 는 "질문에 답" 이 아니라 "그냥 이어 쓰기".

**관찰**: base 가 응답 형식이 아닌 단순 문장 이어쓰기로 답하는 것을 직접 본다. SFT 가 무엇을 추가하는지 체감.

---

## 5. 실전 — 운영자가 알면 좋은 5가지

### ① Context window 의 진실

| 모델 | 광고 컨텍스트 | 실효 컨텍스트 |
|---|---|---|
| Claude Opus 4.7 | 1M tokens | 검색·요약은 OK, 깊은 추론은 200k 안쪽이 안전 |
| GPT-4 Turbo | 128k | 끝부분 (~80k 이후) 정확도 저하 보고 |
| Llama-3.1-8B | 128k | RoPE scaling 없으면 8k 안쪽이 신뢰 |

**광고 컨텍스트와 실효 컨텍스트가 다름**. RULER · Needle-in-Haystack 같은 벤치로 측정.

### ② Tokenizer — 한국어 토큰 비용

```python
from transformers import AutoTokenizer
t1 = AutoTokenizer.from_pretrained("gpt2")
t2 = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B")

s = "안녕하세요, 반갑습니다."
print(len(t1.encode(s)), len(t2.encode(s)))   # 예: 27 vs 11
```

같은 한글이라도 모델별로 토큰 수가 2~3배 차이. **비용 견적 시 주의**. Claude·GPT-4o 는 한글 토크나이저가 잘 정렬됨, 오래된 GPT 계열은 비효율.

### ③ Quantization — 같은 모델, 다른 메모리

| precision | bits/param | 8B 모델 메모리 | 품질 |
|---|---:|---:|---|
| FP32 | 32 | 32 GB | 기준 |
| BF16 | 16 | 16 GB | 거의 동일 |
| INT8 | 8 | 8 GB | 미세 저하 |
| INT4 (QLoRA bnb) | 4 | 4 GB | 작은 저하 (대부분 OK) |

소비자 GPU 에서 8B 모델을 돌리는 핵심 트릭 — Ch 33 의 QLoRA.

### ④ MoE 모델 운영 차이

총 671B 파라미터 (DeepSeek-V3) 라도 활성 파라미터 37B → **inference 비용은 작은 모델 수준**. 단 **메모리는 총 파라미터 기준** — VRAM 확보가 어려움. hosted API 로 쓰는 게 보통 합리적.

### ⑤ Model card 읽는 법

새 모델을 채택할 때 보는 항목:

- **학습 데이터 컷오프** — 우리 도메인 시점이 안에 들어있나
- **컨텍스트 길이 + 신뢰 범위** (위 ①)
- **라이선스** — 상업 사용 가능? (Llama 3 OK, 일부 제약)
- **벤치 점수** — 우리 도메인에 가까운 벤치만 신뢰
- **Tokenizer + 다국어 지원**
- **safety / refusal 정책** — 가드레일 (Ch 28) 와 충돌 가능

---

## 6. 자주 깨지는 포인트

- **수식 깊이 빠지기**. 운영자는 attention 의 직관이면 충분. Q·K·V 행렬 곱 외울 시간에 컨텍스트 한도·토크나이저·비용 모델을 먼저.
- **Base 모델로 chat 시도**. base 는 응답 안 함 — 이어쓰기만. Instruct/Chat 변형을 받아야 함. 처음 만나는 함정.
- **컨텍스트 광고 = 실효 가정**. 1M 컨텍스트라고 1M 채워 쓰면 정확도 급락. 우리 도메인 대표 작업으로 실효 한도를 측정.
- **토큰 = 글자 가정**. "글자 200자" 는 모델·언어별로 토큰 수가 다름. 비용 견적 시 토크나이저로 직접 카운트.
- **모든 모델 = 같은 tokenizer 가정**. SFT 데이터 만들 때 베이스 모델의 토크나이저 무시 → 학습이 안 되거나 효율 절반.
- **MoE 의 활성 파라미터만 보고 메모리 산정**. VRAM 은 총 파라미터 기준 — 671B MoE 는 결코 작은 모델이 아님.
- **양자화 후 평가 생략**. INT4 가 거의 동일하다는 평균치만 믿고 도메인 평가 안 돌림 → 특정 작업에서 큰 회귀.

---

## 7. 운영 체크리스트

- [ ] 운영하는 모델의 정확한 모델 ID + 버전 + 컷오프 기록
- [ ] 도메인 대표 작업으로 실효 컨텍스트 측정
- [ ] 한국어 토큰화 효율 확인 (비용 모델에 반영)
- [ ] 양자화 채택 시 도메인 평가셋 회귀 확인
- [ ] Base / Instruct / Chat 구분이 명확
- [ ] Model card 의 라이선스 · safety 정책 검토 (Ch 28 와 정합)
- [ ] MoE 모델은 hosted vs self-host 의 VRAM·비용 모델 분리

---

## 8. 연습문제 & 다음 챕터

1. Llama-3.1-8B-Base 와 Llama-3.1-8B-Instruct 에 같은 프롬프트 ("Q: 한국의 수도는? A:") 를 줘서 두 응답 차이를 관찰하라. SFT 가 무엇을 더했는지 한 줄로.
2. 한국어 문장 100개를 골라 GPT-4o · Claude · Llama-3 · GPT-2 토큰 수를 비교하라. 비용 차이를 표로.
3. Attention 이 O(n²) 인 사실에서 출발해, "컨텍스트 압축"(Ch 30 ④) 이 비용을 어떻게 줄이는지 한 단락으로 설명하라.
4. 우리 도메인에 새 모델을 채택할 때 model card 에서 봐야 할 5개 항목 우선순위를 매겨라.

**다음 챕터** — 그래서, 우리는 **언제 fine-tune 해야 하는가**. [Ch 32 파인튜닝이 필요한 경우](32-when-to-finetune.md) 로.

---

## 원전

- Vaswani et al. (2017) *Attention is All You Need*
- Touvron et al. (2023) *Llama: Open and Efficient Foundation Language Models*
- Ouyang et al. (2022) *Training language models to follow instructions with human feedback* (RLHF)
- Rafailov et al. (2023) *Direct Preference Optimization* (DPO)
- Stanford CME 295 — *Transformers and LLMs* Lec 1·2·3·4
- Hugging Face — *transformers* docs
