# Ch 17. LLM-as-a-Judge

<a class="colab-badge" href="https://colab.research.google.com/" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **Judge**(심판 LLM) 설계 — pairwise 비교 vs rubric 스코어링
    - 4가지 **편향** — position · length · self-preference · verbosity
    - **Human calibration** — 합의율(agreement) 로 Judge 신뢰도 검증
    - Claude 로 Judge 를 짜고 A/B 뒤집기로 편향 측정
    - Judge 를 "단독 진실" 로 믿지 않는 태도

!!! quote "전제"
    [Ch 15](15-what-to-evaluate.md)–[Ch 16](16-evalset.md). Gold set 이 있고, 그 위에서 답변을 얼마나 **비슷한지** 채점할 방법이 필요한 상태.

---

## 1. 개념 — 누가 채점할 것인가

Gold set 에 정답이 있다고 해도, LLM 응답은 **정확히 같은 문자열**이 나오지 않습니다. 의미는 같은데 표현이 다른 답. 이걸 어떻게 채점하죠?

- **Exact match** — 거의 무의미. "2024년 3월" vs "2024/03" 불일치 처리 불가
- **BLEU/ROUGE** — n-gram 겹침. 의미보다 표현 우연에 의존
- **임베딩 유사도** — 주제는 맞지만 사실성은 모름
- **사람** — 정확하지만 느리고 비쌈

**LLM-as-a-Judge** 는 네 번째 옵션을 자동화하는 것. "다른 LLM 에게 두 답변 중 더 좋은 걸 고르게" 하거나 "1~5점으로 매기게" 합니다.

```
Judge(question, answer_A, answer_B, rubric) → 'A' or 'B' or 'tie'
Judge(question, answer, rubric) → score: 1..5
```

핵심은 이게 **가짜 정답**을 만드는 게 아니라, **사람 평가를 근사**한다는 점. 그래서 신뢰도 검증이 필수입니다.

---

## 2. 왜 필요한가

- **스케일**: 사람 평가 100건 = 몇 시간. Judge 100건 = 몇 분 · $0.5
- **일관성**: 사람은 기분·피로에 따라 흔들림. Judge 는 같은 입력에 비슷한 출력
- **빠른 반복**: 프롬프트 한 줄 수정 → 바로 점수 확인

한계도 있습니다. Judge 는 **사람보다 편향이 더 강한** 영역이 있고, 같은 계열 모델을 **편애**합니다(§5). 그래서 "Judge + 주기적 human sample" 이 표준 패턴.

---

## 3. 어디에 쓰이는가 — 2가지 방식

### 3-1. Pairwise (쌍대 비교)

"A 와 B 중 어느 게 더 나은가?" 단일 의사결정이라 **일관성 높음**. 모델 A/B 테스트에 최적.

### 3-2. Rubric Scoring (루브릭 점수)

"이 답이 정확성·완전성·간결성 각 1~5점?" 절대평가. 회귀 테스트·시계열 추적에 좋음.

| 방식 | 장점 | 단점 | 언제 |
|---|---|---|---|
| Pairwise | 인간 판단과 정렬 높음 · 단순 | 모든 쌍 비교 O(N²) | 모델 · 프롬프트 비교 |
| Rubric | O(N) · 절대 점수 · 축별 분석 | Judge 의 기준 drift | 회귀 · 운영 모니터링 |

실전에서는 **둘 다** 씁니다. 메인은 rubric, 중요한 의사결정은 pairwise 로 이중 확인.

---

## 4. 최소 예제 — Claude 로 pairwise judge

![Judge workflow](../assets/diagrams/ch17-judge-workflow.svg#only-light)
![Judge workflow](../assets/diagrams/ch17-judge-workflow-dark.svg#only-dark)

```python title="judge_pairwise.py" linenums="1" hl_lines="10 28"
import anthropic
import json

client = anthropic.Anthropic()

JUDGE_PROMPT = """당신은 한국어 고객지원 챗봇 응답을 평가하는 심사위원입니다.

## 평가 기준 (rubric)  
1. 정확성 — 제공된 문서에 근거하는가
2. 완전성 — 질문의 모든 부분에 답했는가
3. 간결성 — 불필요한 반복·장황함이 없는가

질문, 참조 문서, 두 응답을 보고 어느 쪽이 더 나은지 판단하세요.
편향 주의: 위치·길이에 휘둘리지 말 것. 내용만 보세요.

출력은 반드시 JSON:
{"winner": "A" | "B" | "tie", "reason": "…", "scores": {"A": {...}, "B": {...}}}
"""

def judge(question, doc, answer_a, answer_b):  # (1)!
    msg = client.messages.create(
        model='claude-haiku-4-5-20251001',  # (2)! Judge 는 싸도 됨
        max_tokens=400,
        system=JUDGE_PROMPT,
        messages=[{
            'role': 'user',
            'content': f'질문: {question}\n\n문서:\n{doc}\n\n'
                       f'응답 A:\n{answer_a}\n\n응답 B:\n{answer_b}',
        }],
    )
    return json.loads(msg.content[0].text)
```

1. **Judge 함수 시그니처** — 질문·참조 문서·두 응답 입력 → 판정 JSON.
2. **Haiku 로 충분** — Judge 태스크는 비교 판단이라 경량 모델로 시작. 합의율이 낮으면 Sonnet 으로 승급.

---

## 5. 실전 튜토리얼 — 편향 측정과 보정

![Judge 의 4편향](../assets/diagrams/ch17-judge-biases.svg#only-light)
![Judge 의 4편향](../assets/diagrams/ch17-judge-biases-dark.svg#only-dark)

### 5-1. Position bias 측정 — A/B 뒤집기

가장 중요한 검증. 같은 A·B 를 **순서만 바꿔** 두 번 돌려, 결과 일치율을 본다.

```python title="measure_position_bias.py" linenums="1"
def measure_position_bias(samples):
    """samples = [{'q', 'doc', 'a', 'b'}, ...]"""
    agree = 0
    for s in samples:
        r1 = judge(s['q'], s['doc'], s['a'], s['b'])  # A · B 순서
        r2 = judge(s['q'], s['doc'], s['b'], s['a'])  # B · A 순서 (뒤집음)

        # r2 의 winner 를 원래 라벨 관점으로 변환
        inverted = {'A': 'B', 'B': 'A', 'tie': 'tie'}[r2['winner']]

        if r1['winner'] == inverted:
            agree += 1
    rate = agree / len(samples)
    print(f'Position consistency: {rate:.2f}  (목표 ≥ 0.85)')
    return rate
```

**0.85 미만이면** Judge rubric 에 "위치 무관하게 내용만" 을 더 강조하거나, Judge 모델을 업그레이드합니다.

### 5-2. Length bias 측정

응답 길이 × Judge 점수의 상관을 본다. 상관계수 0.3 이상이면 "긴 걸 잘한다고 착각 중" 의심.

```python title="length_correlation.py" linenums="1"
from scipy.stats import pearsonr

def length_vs_score(samples, judge_scores):
    lens = [len(s['answer']) for s in samples]
    r, _ = pearsonr(lens, judge_scores)
    print(f'length~score correlation: {r:.2f}')
    return r
```

완화책: rubric 에 "간결성 1~5" 를 **명시적 축**으로 넣고, 총점에 가중.

### 5-3. Human calibration — 합의율

주기적으로 (주 10~20건) **사람이 독립적으로** 평가하고, Judge 결과와 얼마나 일치하는지 계산.

```python title="human_agreement.py" linenums="1"
def agreement(judge_verdicts, human_verdicts):
    """둘 다 ['A', 'B', 'tie', ...]"""
    match = sum(1 for j, h in zip(judge_verdicts, human_verdicts) if j == h)
    return match / len(human_verdicts)
```

- **≥ 0.80**: Judge 점수를 offline 지표로 쓸 만함
- **0.60~0.80**: 주의. 상위 의사결정은 human 필요
- **< 0.60**: Judge 재설계. rubric 명료화 · Judge 모델 교체

### 5-4. Self-preference 방어

Claude Judge 가 Claude 응답을 편애하는 경향. 완화:

- 평가 대상 모델과 **다른 계열** Judge (예: 응답이 Claude · Judge 는 GPT)
- 또는 2개 Judge 로 이중 평가 → 불일치 건만 human

---

## 6. 자주 깨지는 포인트

### 6-1. Judge 를 "진실" 로 믿기

흔한 실수: Judge 점수가 올라갔다고 "품질이 향상됐다"고 **보고서에 쓴다**. Human calibration 없이는 **Judge 의 편향이 점수가 된 것**일 수 있음.

원칙: **Judge 점수 + 합의율** 을 함께 보고. 합의율이 떨어지면 Judge 결과도 의심.

### 6-2. Rubric 이 추상적

"답이 좋은가요?" 같은 rubric 은 편향 투성이. 구체적 축을 쪼개야:

- 나쁨: "응답 품질 1~5"
- 좋음: "정확성 1~5, 완전성 1~5, 간결성 1~5" 각 축별 · 평균

### 6-3. 같은 모델 Judge

`claude-opus` 를 `claude-opus` 응답 Judge 로 쓰면 self-preference. 운영에서 둘 다 Claude 계열일 수밖에 없다면 **2계열 ensemble** 로 완화.

### 6-4. Judge 비용 폭주

Evalset 100건 × 파라미터 변경 20회 = 2000 Judge 호출. Sonnet 으로 하면 수십 $. **Haiku 부터** 시작. Haiku 합의율이 0.75 이상이면 그대로, 미만이면 Sonnet 으로 **일부**만.

---

## 7. 운영 시 체크할 점

- [ ] Rubric 이 구체적 축(정확성·완전성·간결성…)으로 쪼개졌는가
- [ ] **A/B 뒤집기 일관성 ≥ 0.85** 를 배포 전 체크하는 스크립트가 있는가
- [ ] **주간 human sample (≥10건)** 로 Judge 합의율을 추적하는가
- [ ] Judge 모델이 **평가 대상 모델과 다른 계열** 인가 (최소한 다른 크기)
- [ ] Rubric 에 **간결성** 점수가 포함돼 length bias 를 완화하는가
- [ ] Judge 호출 **비용 예산**이 있는가 (모델 × 호출 수 × 토큰)
- [ ] 합의율 하락 시 **알림**이 오는가 (Slack · 대시보드)
- [ ] Pairwise 판정 결과를 **시계열**로 저장해 drift 를 볼 수 있는가

---

## 8. 연습문제 & 다음 챕터

### 확인 문제

1. Pairwise vs Rubric 의 장단점을 상황 2가지로 구분해 설명하세요 (모델 A/B 선택 / 운영 모니터링).
2. Position bias 를 측정하는 식을 쓰고, 0.85 가 목표인 이유를 설명하세요.
3. Judge 합의율이 0.55 로 낮게 나왔습니다. 가능한 원인 3가지와 각각의 대응을 드세요.
4. "Judge 점수만 보고 릴리스를 결정" 이 왜 위험한지 2문단으로 설명하세요.

### 실습 과제

- Ch 16 에서 만든 QA gold set 10건에 두 가지 프롬프트 버전(기본 · CoT) 응답을 각각 생성 → Claude Haiku Judge 로 pairwise 비교. A/B 뒤집기 일관성도 측정.
- 같은 응답에 Claude Judge · GPT Judge 를 각각 돌려 **Self-preference** 를 정량화.

### 원전

- **Stanford CME 295 Lec 8** — LLM-as-a-Judge · 편향 · calibration. 프로젝트 `_research/stanford-cme295.md`
- **MT-Bench / Chatbot Arena** 논문 (Zheng et al.) — pairwise judge 의 표준 레퍼런스
- **Anthropic Building Effective Agents** — 평가 루프 디자인. 프로젝트 `_research/anthropic-building-effective-agents.md`

---

**다음 챕터** → [Ch 18. 추론 품질 높이기](18-reasoning-quality.md) — CoT · self-consistency · best-of-N · verifier 로 **답 자체**를 개선 :material-arrow-right:
