# Ch 15. 무엇을 평가해야 하는가

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part4/ch15_what_to_evaluate.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **평가 없는 AI 시스템은 신뢰할 수 없다** — 왜 숫자가 있어야 하는가
    - 평가의 **3층 구조** — Retrieval · Generation · End-to-End
    - **Offline**(배포 전) vs **Online**(배포 후) — 같은 지표라도 역할이 다름
    - 메트릭 카탈로그 — 어떤 상황에 어떤 지표를 쓸지 매핑
    - 단일 메트릭 몰빵 · "큰 모델이면 OK" 같은 대표적 함정

!!! quote "전제"
    Part 2([Ch 4](../part2/04-api-start.md)–[Ch 8](../part2/08-tool-calling.md))와 Part 3([Ch 9](../part3/09-why-rag.md)–[Ch 14](../part3/14-langchain-multimodal.md)). 프로토타입 수준의 RAG / Tool-calling 시스템을 한 번 조립해본 상태.

---

## 1. 개념 — "잘 돌아간다"는 착각

당신이 만든 챗봇에 "환불 정책 알려줘" 를 던졌더니 그럴듯한 답이 나왔습니다. 세 번 더 해봤습니다. 다 그럴듯합니다. **배포합시다**.

이게 함정입니다. LLM 응답은 **확률적**이고 **입력에 민감**합니다. 몇 번 수동 테스트로 찍은 "그럴듯함"은 다음 사실들을 가립니다:

- 특정 질문 유형에서만 환각이 나는지
- 검색이 엉뚱한 문서를 가져오는데 LLM이 감춰주고 있는지
- 숫자·날짜가 미묘하게 틀리는지
- 프롬프트를 한 번 수정한 뒤 다른 케이스에서 품질이 **떨어졌는지**

**평가(Evaluation)** 는 이 모든 걸 **재현 가능한 숫자**로 바꾸는 작업입니다. 코드로 치면 테스트, 제품으로 치면 A/B 실험. 이게 없으면 시스템은 "운 좋게 돌아가는 상태" 에서 벗어나지 못합니다.

---

## 2. 왜 필요한가 — 3가지 실제 이유

**① 회귀 방지 (Regression).** 프롬프트 한 줄·모델 버전·retriever 파라미터를 바꿀 때마다, 이전에 잘 풀던 케이스가 깨지는지 알아야 합니다. 수동 테스트로는 10개도 힘듭니다. 평가셋과 스크립트가 있으면 100개를 30초에 돌립니다.

**② 의사결정 (Decision).** "Haiku 로 내릴까, Sonnet 유지할까?" "Reranker 를 붙일까?" 이런 선택은 **숫자 없이 하면 다 감(感)** 입니다. Recall@5 가 0.62 → 0.81 로 오르는 걸 보고 결정하는 것과, "왠지 좋아진 것 같아" 는 다릅니다.

**③ 신뢰 (Trust).** 기업 환경에서 LLM 시스템을 운영하려면 법무·보안·현업이 "이건 얼마나 틀리냐"를 물어봅니다. `Faithfulness 0.93` 같은 답이 있어야 대화가 됩니다. "잘 돼요" 는 답이 아닙니다.

---

## 3. 어디에 쓰이는가 — 평가의 3층

![평가의 3층](../assets/diagrams/ch15-eval-3layers.svg#only-light)
![평가의 3층](../assets/diagrams/ch15-eval-3layers-dark.svg#only-dark)

RAG 시스템은 최소 두 블록(검색·생성)으로 이뤄지고, 사용자 체감은 이 둘의 합입니다. 그래서 **세 개의 시점**에서 봐야 합니다.

### 3-1. Retrieval 층 — 필요한 문서를 가져왔는가

이 층은 LLM 이전에 끝납니다. 질문 → 문서 k개 가져오기까지.

| 지표 | 의미 | 언제 쓰나 |
|---|---|---|
| **Recall@k** | 정답 문서가 top-k 안에 들어 있는 비율 | 검색 커버리지 확인 |
| **Precision@k** | top-k 중 관련 있는 문서 비율 | top-k 가 너무 넓을 때 |
| **MRR** (Mean Reciprocal Rank) | 정답의 순위 역수 평균 | 정답이 **맨 위**에 오는지 중요할 때 |
| **nDCG** | 관련도를 가중한 랭킹 점수 | 관련도가 연속값일 때 (매우·조금) |

### 3-2. Generation 층 — 그 문서로 올바른 답을 만들었나

Retrieval 결과(ground truth 문서)를 **고정**한 상태로, 생성만 본다.

| 지표 | 의미 | 언제 쓰나 |
|---|---|---|
| **Faithfulness** | 답변이 제시 문서에 근거하는 비율 | 환각 탐지 (RAG 의 핵심) |
| **Correctness** | 정답과 의미상 일치 | 정답이 명확한 QA |
| **Coherence** | 앞뒤 맥락·가독성 | 요약·긴 응답 |
| **Groundedness** | Faithfulness 의 엄격 버전 — 문장 단위 | 의료·법률처럼 정확성 크리티컬 |

### 3-3. End-to-End 층 — 사용자가 실제로 만족했나

검색 + 생성 전체를 한 덩어리로 보고, **결과물**만 평가한다.

| 지표 | 의미 | 언제 쓰나 |
|---|---|---|
| **Helpfulness** | 유용성 (judge or 사람 점수) | 가장 흔한 E2E 지표 |
| **Task Success** | 의도한 과제 완수율 | 에이전트·워크플로우 |
| **Safety** | 유해·차별·거부 실패율 | 운영 필수 |
| **User Feedback** | 👍/👎 · 재질문율 | 온라인 피드백 |

!!! tip "3층을 왜 나누냐"
    E2E 점수만 낮다면 원인이 어디인지 모릅니다. Retrieval 은 0.85인데 E2E 는 0.40이라면 → **생성 프롬프트가 문제**. Retrieval 이 0.30이라면 → **reranker 붙여야 할 때**. 층별로 봐야 **어디를 고칠지** 보입니다.

---

## 4. 최소 예제 — Retrieval recall@k 재보기

먼저 "평가는 거창하지 않다"는 감각부터. 30줄로 retrieval 평가셋을 돌려봅시다.

```python title="eval_retrieval.py" linenums="1" hl_lines="14 23"
import chromadb
from openai import OpenAI

oai = OpenAI()
client = chromadb.PersistentClient(path='./chroma')
col = client.get_collection('docs')

# (1)! 평가셋: 질문과 정답 문서 id
dataset = [
    ('환불 정책은?', 'doc-refund-01'),
    ('배송은 몇 일?', 'doc-shipping-02'),
    ('쿠폰 적용 방법?', 'doc-coupon-03'),
]

def embed(text):
    return oai.embeddings.create(
        model='text-embedding-3-small', input=text
    ).data[0].embedding

def recall_at_k(k=5):  # (2)!
    hits = 0
    for q, gold_id in dataset:
        res = col.query(query_embeddings=[embed(q)], n_results=k)
        retrieved_ids = res['ids'][0]
        if gold_id in retrieved_ids:
            hits += 1
    return hits / len(dataset)

print(f'Recall@5 = {recall_at_k(5):.2f}')
print(f'Recall@3 = {recall_at_k(3):.2f}')
```

1. **gold set** — 질문 × 정답 문서 id 페어. 지금은 3개지만 Ch 16에서 30~100건으로 늘립니다.
2. **recall@k** — "top-k 안에 정답이 들어 있는가" 의 비율. 순위는 안 봄. 순위까지 보려면 MRR.

이게 전부입니다. 3줄의 평가 함수 하나가 "프롬프트 바꾸면 품질이 어떻게 변하나" 라는 질문에 **숫자로** 답해줍니다.

---

## 5. 실전 튜토리얼 — Offline vs Online 두 축

![Offline vs Online](../assets/diagrams/ch15-offline-vs-online.svg#only-light)
![Offline vs Online](../assets/diagrams/ch15-offline-vs-online-dark.svg#only-dark)

평가에는 **두 축**이 있습니다. 둘 중 하나만 하면 반드시 구멍이 납니다.

### 5-1. Offline — 배포 전, 고정 데이터로

**언제**: 프롬프트·모델·파라미터를 바꿀 때마다. 이상적으로는 CI/CD 게이트.

**데이터**: **고정된 gold set** (Ch 16). 바뀌면 비교가 안 되므로 버전 관리.

```python title="offline_ci.py" linenums="1"
# 실제 CI 에서 돌릴 법한 최소 골격
THRESHOLDS = {
    'recall@5': 0.80,
    'faithfulness': 0.85,
}

def run_eval():
    scores = {
        'recall@5': evaluate_retrieval(gold_set),
        'faithfulness': evaluate_faithfulness(gold_set),
    }
    for name, score in scores.items():
        assert score >= THRESHOLDS[name], f'{name} regressed: {score:.2f}'
    return scores

if __name__ == '__main__':
    print(run_eval())
```

**장점**: 재현 가능, 빠르고 싸다. 한 번 짜두면 수백 번 돌림.  
**한계**: 평가셋 밖에서 일어나는 실제 사용 케이스를 못 본다.

### 5-2. Online — 배포 후, 실사용자로

**언제**: 카나리(5% 트래픽)·A/B 테스트·상시 모니터링.

**데이터**: 실사용자 로그와 피드백. 샘플링해서 본다.

| 신호 | 의미 |
|---|---|
| 👍/👎 | 직관적이지만 응답률 낮음 (5~15%) |
| 재질문율 | 사용자가 바로 다시 묻는 비율 — 낮을수록 좋음 |
| 세션 길이 | 에이전트가 한 과제 해결까지 걸린 턴 수 |
| 포기율 (abandonment) | 응답 중간에 나간 비율 |
| 수동 검토 샘플 | 하루 100건 샘플링 → 사람이 3점 척도로 |

**장점**: 진짜 사용성 · 장기 트렌드 포착.  
**한계**: 노이즈 크고, 원인 분리 어렵고, 반영 지연.

### 5-3. 두 축은 루프로 연결

온라인에서 발견된 **실패 케이스**를 오프라인 gold set 에 **추가**합니다. 이게 Ch 16 에서 다룰 핵심 운영 루프.

```
실사용 로그 → 실패 샘플링 → 레이블링 → gold set 갱신 → 다음 offline 라운드
```

---

## 6. 자주 깨지는 포인트

### 6-1. 단일 메트릭 몰빵

"우리 Faithfulness 0.91 나옵니다!" 를 자랑하는 팀이 있는데, Recall@5 는 0.30 입니다. LLM 이 **엉뚱한 문서로 성실하게 답했을 뿐**. 층별로 최소 각 1개 지표는 있어야 합니다.

### 6-2. "큰 모델이면 된다" 맹신

Sonnet 이 Haiku 보다 Faithfulness 가 **더 낮게** 나오는 경우가 있습니다. 대형 모델이 자신감 있게 추론으로 메꾸기 때문. 평가 없이 "비싼 게 좋겠지" 는 실제로는 거꾸로일 수 있습니다.

### 6-3. 평가셋 누출 (Test set leak)

프롬프트를 평가셋에 맞춰 조금씩 손보다 보면, 모델이 아니라 **당신이** 평가셋에 과적합합니다. 해결: **hold-out** 셋(본 적 없는 30~50건) 을 따로 둡니다.

### 6-4. Offline 점수만 보고 배포

Offline 에서 0.92 가 나와도, 실사용자는 다른 질문을 합니다. Canary 배포로 소규모 실트래픽에서 **최소 3일** 은 모니터링. Offline·Online 지표가 어긋나면 그게 시그널입니다.

---

## 7. 운영 시 체크할 점

- [ ] **3층 × 각 1개 이상** 지표를 정해뒀는가 (Retrieval · Generation · E2E)
- [ ] Gold set 이 **버전 관리**되고 (git/DVC), 레이블링 가이드가 문서화됐는가
- [ ] 평가 스크립트가 **CI 에서 자동 실행**되고, 임계값을 넘으면 머지 차단되는가
- [ ] Canary 배포 기간 동안 볼 **온라인 지표**가 대시보드에 있는가 (Grafana/Langfuse 등)
- [ ] **실패 케이스 수집 루프**가 있는가 — 👎 · 낮은 judge 점수 → 주간 리뷰 → gold set 갱신
- [ ] 평가 실행에 걸리는 **API 비용**이 예산 안에 있는가 (LLM judge 는 비쌈)
- [ ] **Hold-out 셋**을 따로 뒀는가 (평가셋에 대한 과적합 방어)
- [ ] 새 기능 추가 시 "어떻게 평가할 것인가" 가 **PR 설명에 포함**되는가

---

## 8. 연습문제 & 다음 챕터

### 확인 문제

1. 평가의 3층(Retrieval · Generation · E2E) 각각에 최소 1개 지표를 고르고, 왜 그걸 골랐는지 한 줄로 설명하세요.
2. 당신이 만든 시스템에서 E2E 만 낮고 Retrieval·Generation 개별 점수는 괜찮다면, 원인이 어디일 가능성이 큽니까?
3. Offline 점수는 그대로인데 Online 지표가 떨어집니다. 가능한 원인 3가지를 드세요.
4. 단일 메트릭(예: Faithfulness 만)을 보는 것이 왜 위험한지, 구체적 예시로 설명하세요.

### 실습 과제

- [4번](../part2/05-prompt-cot.md)에서 만든 QA 프롬프트에 질문 10개를 골라 **gold answer** 를 손으로 달고, `correctness` 를 LLM judge(Claude Haiku) 로 채점해보세요. 프롬프트를 한 번 수정하고 점수 변화를 기록.

### 원전

- **Stanford CS329A Lec 17** — Agentic Evaluations · Long-Horizon Tasks. 프로젝트 `_research/stanford-cs329a.md`
- **Stanford CME 295 Lec 8** — Evaluation & LLM-as-a-Judge. 프로젝트 `_research/stanford-cme295.md`
- Ragas 공식 문서의 metric 카탈로그 (faithfulness · answer_relevancy · context_precision)

---

**다음 챕터** → [Ch 16. 평가셋 만들기](16-evalset.md) — 방금 얘기한 gold set 을 어떻게 **실제로** 30~100건 구축하고 관리하는가 :material-arrow-right:
