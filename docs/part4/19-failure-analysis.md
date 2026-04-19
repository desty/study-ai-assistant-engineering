# Ch 19. 실패 분석과 디버깅

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part4/ch19_failure_analysis.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - 실패를 **5층 택소노미**로 분리 — Prompt · Retrieval · Data · Generation · Tool/Flow
    - **Trace** 기반 재현 가능한 디버깅 — LangSmith · Langfuse
    - 실패 → 분류 → 수정 → 회귀 방지로 이어지는 **debug loop**
    - "한 실패가 여러 층에 걸치는" 복합 케이스 다루기
    - **Part 4 전체 마무리** — 14주 운영 루틴 제안

!!! quote "전제"
    [Ch 15](15-what-to-evaluate.md)–[Ch 18](18-reasoning-quality.md). 숫자가 있고, Judge 가 있고, 추론 전략까지 있다. 이제 **틀린 건에 대해 무엇을 고칠지** 를 체계화.

---

## 1. 개념 — 증상 vs 원인

"환각이 났다" 는 **증상**입니다. 원인은 어디냐:

- 프롬프트가 명확하지 않아서?
- 검색이 엉뚱한 문서를 가져와서?
- 원래 문서에 오타가 있어서?
- 문서는 맞는데 LLM 이 왜곡해서?
- tool 호출 결과를 잘못 해석해서?

증상만 보고 "Sonnet 으로 바꿔" 하면 **돈만 쓰고 문제는 안 풀립니다**. 원인 층을 지목해야 **근본 수정**이 가능.

![실패 분류 taxonomy](../assets/diagrams/ch19-failure-taxonomy.svg#only-light)
![실패 분류 taxonomy](../assets/diagrams/ch19-failure-taxonomy-dark.svg#only-dark)

이 챕터의 **5층 택소노미**가 본 책에서 반복 사용될 공통 언어입니다.

---

## 2. 왜 필요한가

**① 수정 비용 편차가 크다.** 프롬프트 수정은 30분, reranker 도입은 1주, 문서 재정제는 한 달. **층을 지목하지 않으면 우선순위**가 안 섭니다.

**② 성급한 LLM 교체는 돈만 든다.** "품질이 안 나오니 Opus 로 올리자" 가 증상을 20% 완화해도, 실제 원인이 retrieval 이면 비용만 ×3 · 문제는 그대로. Layer-aware 디버깅이 없으면 이 실수를 반복.

**③ 회귀(regression) 예방.** 한 번 고친 케이스를 gold set 에 추가(Ch 16)해야, 다음 리팩토링에서 또 깨지지 않음. Debug loop 는 영구 개선.

---

## 3. 5층 택소노미 — 분류 기준

| # | 층 | 대표 증상 | 대표 수정 | Ch 참조 |
|---|---|---|---|---|
| 1 | **Prompt** | 지시 모호 · few-shot 부족 · 형식 이탈 | 프롬프트 재설계 · few-shot 추가 | Ch 5 |
| 2 | **Retrieval** | top-k 에 정답 문서 없음 | reranker · hybrid · 임베딩 교체 | Ch 12 · 13 |
| 3 | **Data** | chunk 경계 잘림 · 문서 오타 · 결측 | chunking 재설정 · 문서 정제 | Ch 11 |
| 4 | **Generation** | 문서 있는데 답 왜곡 · hallucination | temperature↓ · CoT · verifier | Ch 5 · 18 |
| 5 | **Tool / Flow** | tool call 인자 오류 · 상태 전이 오류 | tool description · ACI · 상태기계 | Ch 8 · Part 5 |

### 분류 진단 질문

1. **정답 문서가 top-k 에 있었나?** → 없으면 Retrieval(2). 있으면 3~5.
2. **문서에 정답이 실제로 있나?** → 없으면 Data(3).
3. **문서 있는데 답이 틀렸나?** → Generation(4). CoT/verifier 로 보강.
4. **추론 체인에서 엉뚱한 tool 이 호출됐나?** → Tool/Flow(5).
5. **위 다 통과했는데 여전히 틀렸다면?** → Prompt(1) 로 회귀.

---

## 4. 최소 예제 — 실패 1건 분류

실제 실패 사례를 5층 중 하나에 분류해 봅니다.

```python title="classify_failure.py" linenums="1" hl_lines="10 19"
from dataclasses import dataclass

@dataclass
class Trace:
    question: str
    retrieved_doc_ids: list[str]
    gold_doc_ids: list[str]
    answer: str
    gold_answer: str

def classify(trace: Trace) -> str:
    # (1)! Retrieval 체크 — 정답 문서가 top-k 에 있는가
    if not set(trace.gold_doc_ids) & set(trace.retrieved_doc_ids):
        return 'retrieval'

    # Data 체크 — gold doc 에 정답이 실제로 있는가 (수동 확인 필요)
    # 여기선 생략, 실무에선 문서 조회

    # (2)! Generation 체크 — 답이 gold 와 많이 다른가
    sim = similarity(trace.answer, trace.gold_answer)  # 임베딩 cosine
    if sim < 0.6:
        # 문서는 맞는데 답이 다름 → Generation 문제 의심
        return 'generation'

    # Prompt/Tool 체크 — 형식 이탈이나 tool call 오류
    if not trace.answer.strip():
        return 'prompt'

    return 'uncertain'  # 사람 검토 필요
```

1. **1차 분기 — Retrieval** 이 가장 빠르게 배제 가능. `set intersection` 만으로 판정.
2. **2차 분기 — Generation** 은 의미 유사도로 판정. 0.6 미만 = "문서 줬는데 다르게 답함".

이 함수 하나로 **실패 100건을 5분류로 정리** 가능. 이게 주간 리뷰의 출발점.

---

## 5. 실전 튜토리얼 — Trace 기반 Debug Loop

![Debug Loop](../assets/diagrams/ch19-debug-loop.svg#only-light)
![Debug Loop](../assets/diagrams/ch19-debug-loop-dark.svg#only-dark)

### 5-1. Trace 수집 — LangSmith / Langfuse

프로덕션에서 **입력·검색 결과·프롬프트·출력·지연·비용** 을 한 trace 로 저장. 이게 없으면 디버깅 불가.

```python title="trace_setup.py" linenums="1"
# Langfuse 예시 (LangSmith 도 거의 동일)
from langfuse import Langfuse
from langfuse.decorators import observe

lf = Langfuse()

@observe()
def rag_answer(question: str):
    docs = retrieve(question)
    prompt = build_prompt(question, docs)
    answer = generate(prompt)
    return answer, docs
```

데코레이터 한 줄로 모든 호출이 자동 기록. 👎 를 받은 trace id 만 골라 다음 단계로.

### 5-2. 주간 리뷰 루틴 — 20건 분류

```
월: 지난주 👎 + low judge score 에서 20건 샘플 (층별 균형)
화: classify() 로 1차 분류 → 사람 확인 → 확정
수: 층별로 가장 많은 1~2개 원인을 fix 후보로
목: 수정 · eval 돌려 regression 체크
금: 고친 케이스를 gold set 에 추가 · 다음주 회귀 테스트에 포함
```

이걸 **4주만 돌려도** failure mode 분포가 바뀝니다. "어, 이제 retrieval 문제는 거의 없고 generation 남았네" → 집중 영역 이동.

### 5-3. 복합 실패 — 여러 층에 걸칠 때

한 실패가 2~3개 층에 걸치는 경우가 많습니다. 예: "검색이 부족한 문서 2개 + 프롬프트가 CoT 유도 안 함 → 생성이 헷갈려 환각".

처리 원칙:

1. **원인을 하나씩** 분리해 테스트. 프롬프트만 CoT 로 바꿨을 때 해결? 아니면 검색 보강 먼저?
2. **가장 값싼 층부터 수정**. 프롬프트(30분) → 파라미터 튜닝(2시간) → retrieval(며칠) → 모델 교체(마지막).
3. **한 번에 한 축만**. 두 개 동시에 바꾸면 어느 게 효과인지 모름.

### 5-4. 회귀 방지 — Gold set 편입

```python title="add_to_gold.py" linenums="1"
def promote_to_gold(trace, fix_description):
    """수정 완료된 실패 케이스를 평가셋에 영구 편입"""
    entry = {
        'id': f'regr-{trace.id}',
        'question': trace.question,
        'gold_doc_ids': trace.gold_doc_ids,
        'gold_answer': trace.gold_answer_corrected,
        'source': 'production_failure',
        'fix': fix_description,
        'added_at': '2026-04-19',
    }
    append_jsonl(entry, 'evalset/regression.jsonl')
```

**핵심**: 고친 케이스는 `regression.jsonl` 에 넣어 다음 CI 에서 자동 검증. "같은 실수 두 번" 방지.

---

## 6. 자주 깨지는 포인트

### 6-1. LLM 교체로 증상만 숨기기

Opus 로 올려 정확도 70→78% 가 돼도, 원인이 retrieval 이면 **실패 mode 는 그대로**. 3배 비싼 돈으로 약간의 얼버무림만 산 것. 층 분류 없이 모델 업그레이드는 금지.

### 6-2. 분류를 안 하고 "잘못된 것들" 뭉뚱그리기

"실패 50건 있네, 프롬프트 다시 짤게" 는 산탄총. 50건 중 40건이 retrieval 이면 프롬프트 수정은 **0% 효과**.

### 6-3. Trace 저장 안 함

"재현이 안 돼요" = trace 없음. 디버깅 불가 → 감으로 수정 → 운에 맡긴 품질. LangSmith / Langfuse / 자체 로그 중 뭐든 **반드시 설치**.

### 6-4. 한 번 고치고 끝

고친 케이스가 evalset 에 없으면, 3개월 뒤 다른 변경에서 같은 케이스 깨짐. Regression set 편입이 루프를 닫는 최후 단계.

### 6-5. 복합 실패를 한번에 수정

프롬프트 + retrieval + 모델 동시 변경 → 품질은 올랐는데 **무엇이 효과인지 불명**. A/B 분리해 한 축씩.

---

## 7. 운영 시 체크할 점

- [ ] 모든 요청이 **trace 저장** 되는가 (LangSmith/Langfuse/자체)
- [ ] `classify()` 로직이 자동 1차 분류를 하는가
- [ ] **주간 20건 리뷰** 루틴이 팀 캘린더에 있는가
- [ ] 고친 실패가 **regression.jsonl** 에 편입되고 CI 에서 돌아가는가
- [ ] 실패 5층 **분포 추이**를 대시보드로 볼 수 있는가 (월간)
- [ ] 복합 실패 시 "가장 값싼 층부터" 원칙이 PR 설명에 반영되는가
- [ ] **모델 업그레이드 의사결정** 전에 층 분석이 먼저 있는가
- [ ] 실패 원인을 **Slack/Notion 문서**로 짧게라도 기록하는가 (조직 학습)

---

## 8. 연습문제

### 확인 문제

1. 5층 택소노미의 각 층에 대해 **진단 질문 1개씩** 을 당신 말로 다시 쓰세요.
2. "LLM 모델 교체" 가 답이 되는 상황 vs 되지 **않는** 상황의 예를 각 1개씩 드세요.
3. 복합 실패에서 "가장 값싼 층부터 수정" 원칙의 근거를 수정 비용 × 효과 관점에서 설명하세요.
4. Regression.jsonl 편입 없이 실패 수정만 하면 어떤 문제가 반복되나요?

### 실습 과제

- 당신 프로토타입의 실패 20건을 수집 → `classify()` 로 1차 분류 → 표로 정리. 상위 1개 원인을 30분 안에 수정할 수 있는 가장 작은 변화를 적용 → 재평가.
- LangSmith 또는 Langfuse 를 설치해 Ch 11 의 mini_rag 에 붙이고, trace 하나를 화면에서 확인해보세요.

### 원전

- **LangSmith / Langfuse 공식 문서** — Trace 설치 가이드
- **Stanford CS329A HW** — 실패 분류 과제 · Agent 디버깅 루틴. 프로젝트 `_research/stanford-cs329a.md`

---

## 9. Part 4 마무리 — 평가 · 추론 · 디버깅 루프

Part 4 전체를 한 장으로:

| Ch | 주제 | 핵심 산출물 |
|---|---|---|
| 15 | 무엇을 평가 | 3층(Retrieval·Generation·E2E) + Offline/Online |
| 16 | 평가셋 만들기 | 30~100건 gold · coverage matrix · hold-out 20% |
| 17 | LLM-as-a-Judge | Pairwise/Rubric + A/B 뒤집기 ≥0.85 · human agreement ≥0.8 |
| 18 | 추론 품질 | Self-Consistency · Best-of-N + verifier (test-time compute) |
| 19 | 실패 분석 | 5층 택소노미 · Debug loop · Regression 편입 |

### Part 4 졸업 상태

1. **gold set 30건 이상** 이 버전 관리되고 CI 에서 자동 평가된다
2. **Judge 설계 + A/B 뒤집기 일관성** 가 측정된다
3. 한 번이라도 **Self-Consistency 또는 Best-of-N** 을 실제 태스크에 실험했다
4. **Trace 가 저장되고 failure 분류** 가 가능하다
5. **Regression.jsonl** 에 최소 1건의 실패가 편입됐다

### 다음으로 — Part 5. Agent & LangGraph

평가 인프라가 있으니, 이제 **복잡한 워크플로** 로 넘어갑니다. 단일 LLM 호출이 아니라 **여러 단계 추론 · tool 사용 · 상태 관리**. Part 5 전체가 이 위에서 펼쳐집니다.

---

**다음 챕터** → [Ch 20. 에이전트란 무엇인가](../part5/20-what-is-agent.md) :material-arrow-right:
