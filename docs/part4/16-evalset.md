# Ch 16. 평가셋 만들기

<a class="colab-badge" href="https://colab.research.google.com/" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **Gold set**(정답 포함 평가셋) 을 **30~100건** 규모로 실제 만들기
    - **대표성 있는 샘플링** — 난이도 × 도메인 coverage
    - **Synthetic vs Human** 레이블링 — 언제 LLM 을 믿고 언제 사람이 필요한가
    - 평가셋 **운영** — 버전 관리 · hold-out · 실사용 실패로 갱신
    - 평가셋 누출 · 편향 · "너무 쉬운 문제만" 3대 함정

!!! quote "전제"
    [Ch 15](15-what-to-evaluate.md) — 어떤 지표를 쓸지 결정한 상태. 여기선 그 지표가 소비할 **데이터**를 만든다.

---

## 1. 개념 — 평가는 데이터가 절반이다

Ch 15 에서 정한 지표(Recall@5 · Faithfulness · Helpfulness …)는 계산식일 뿐입니다. 실제 숫자가 나오려면 **질문 + 정답** 페어가 필요합니다. 이걸 **평가셋(evaluation set)** 또는 **gold set** 이라고 합니다.

```
gold set = [(질문, 정답 문서 id, 정답 답변, 메타)] × N건
```

평가의 품질은 **이 데이터의 품질**을 절대 넘을 수 없습니다. 아무리 좋은 Judge·Metric 도 엉성한 평가셋 위에서는 엉성한 신호만 냅니다.

### 왜 "gold" 라고 부르나

답이 **확정된(ground truth)** 데이터라는 의미. 일반 학습 데이터와 달리, 여기 있는 답은 사람이 검토해 "이게 옳다"고 인정한 것입니다. 그래서 비쌉니다. 그래서 **많이 만들 수 없습니다**. 그래서 **잘** 만들어야 합니다.

---

## 2. 왜 필요한가 — 수동 테스트의 3가지 한계

**① 확장 불가.** 수동으로 질문 10개 돌려보고 "잘 된다"는 판단은, 그 10개가 실사용 분포를 대표하지 않으면 의미가 없습니다. 100건을 자동으로 돌릴 수 있어야 회귀 테스트가 됩니다.

**② 재현 불가.** "지난주엔 이 질문에 답 잘하던데" 는 기억에 남은 편향. 스크립트화된 평가셋은 **같은 입력에 같은 수치** 를 내서 주간 비교가 가능합니다.

**③ 편향된 테스트.** 개발자가 떠올리는 질문은 이미 잘 풀 질문들입니다. 실사용자는 **당신이 상상 못 한** 질문을 합니다. 평가셋은 이 gap 을 메워야 합니다.

---

## 3. 어디서 데이터를 가져오나 — 4가지 소스

### 3-1. 실사용 로그 (최우선)

이미 운영 중이면 **실트래픽 질문**이 최고의 소스. 분포가 실제 그대로이기 때문.

- 위험: 개인정보(PII) · 민감 정보 노출 → **마스킹 필수**
- 대안: 사내 QA 로그 · 파일럿 사용자 로그

### 3-2. 기존 문서에서 역생성

문서를 LLM 에 주고 "이 문서로 답할 수 있는 질문 3개 만들어줘" — synthetic. **빠르지만 실사용 분포와 다름**.

### 3-3. 도메인 전문가 브레인스토밍

현업·CS 팀이 "이런 거 자주 물어본다" 를 받는다. 노동집약적이지만 **edge case** 발굴에 좋음.

### 3-4. 공개 벤치마크 (보조)

MMLU · TriviaQA · KoBEST 등. 당신 도메인에 맞는 게 거의 없으므로 **warm-up** 용도만.

!!! tip "권장 믹스"
    실사용 로그 60% + 전문가 브레인스토밍 30% + 합성/공개 10%. 실데이터 없는 초기에는 합성 비중을 높이되, **배포 즉시 실로그로 대체**.

---

## 4. 최소 예제 — QA 10건으로 시작

어려워 보이지만 **10건으로 시작** 이 정답입니다. 완벽한 100건 기다리다 한 건도 못 만듭니다.

```python title="build_evalset_v1.py" linenums="1" hl_lines="6 20"
import json
from pathlib import Path

# (1)! 최초 10건 — 손으로 쓴다. 질문 + 정답 문서 id + 모범 답변
SEED = [
    {
        'id': 'q001',
        'question': '환불 정책은 어떻게 되나요?',
        'gold_doc_ids': ['doc-refund-01'],
        'gold_answer': '구매 후 7일 이내 미사용 상품에 한해 환불 가능. 자세한 절차는 마이페이지 > 환불 신청.',
        'difficulty': 'easy',
        'domain': 'policy',
    },
    # ... 나머지 9건 동일 형식
]

def save_evalset(items, path='evalset/qa_v1.jsonl'):  # (2)!
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

save_evalset(SEED)
```

1. **최소 필드 5개** — id · question · gold_doc_ids (검색 평가용) · gold_answer (생성 평가용) · difficulty/domain (샘플링 · 분석용). 더 늘리는 건 나중.
2. **JSONL 포맷** — 한 줄 한 건. git diff 에서 변경이 명확하고, stream 처리 가능.

이 10건만 있으면 Ch 15 의 `recall@k` 스크립트가 **돌아갑니다**. 나머지는 점진적으로 추가.

---

## 5. 실전 튜토리얼 — 100건 gold set 운영

![Evalset 파이프라인](../assets/diagrams/ch16-evalset-pipeline.svg#only-light)
![Evalset 파이프라인](../assets/diagrams/ch16-evalset-pipeline-dark.svg#only-dark)

### 5-1. Coverage matrix 먼저 설계

100건을 "되는대로" 모으면 특정 영역에 편중됩니다. **어떤 샘플이 얼마나** 필요한지 **표로 먼저** 정합니다.

![난이도 × 도메인 coverage](../assets/diagrams/ch16-coverage-matrix.svg#only-light)
![난이도 × 도메인 coverage](../assets/diagrams/ch16-coverage-matrix-dark.svg#only-dark)

난이도 × 도메인 매트릭스에 **목표 건수**를 미리 채워둡니다. 채워지지 않은 셀은 의식적으로 찾아냅니다.

### 5-2. 샘플링 — stratified

실로그에서 무작위 추출은 쉬운 질문 편향이 큽니다. **계층화 샘플링(stratified)** 을 씁니다.

```python title="sample_stratified.py" linenums="1"
import random
from collections import defaultdict

def stratified_sample(logs, matrix):
    """logs = [{'question', 'difficulty', 'domain'}, ...]
       matrix = {('easy','faq'): 10, ('hard','numeric'): 16, ...}
    """
    buckets = defaultdict(list)
    for log in logs:
        key = (log['difficulty'], log['domain'])
        buckets[key].append(log)

    sampled = []
    for key, target in matrix.items():
        pool = buckets.get(key, [])
        if len(pool) < target:
            print(f'⚠ {key}: 풀 부족 ({len(pool)}/{target}) — 합성으로 보강 필요')
        sampled.extend(random.sample(pool, min(target, len(pool))))
    return sampled
```

부족한 셀은 합성(§3-2)이나 브레인스토밍으로 **메꿉니다**.

### 5-3. 레이블링 — Human × LLM 하이브리드

**LLM draft → Human review** 가 비용 대비 품질이 좋습니다.

| 단계 | 누가 | 무엇을 |
|---|---|---|
| 1. Draft | LLM (Claude Haiku) | 문서에서 gold_answer 후보 생성 |
| 2. Review | 도메인 담당자 | 사실성·완전성 확인·수정 |
| 3. 2차 검수 | 다른 사람 | 10~20% 샘플 이중 체크 |
| 4. 승인 | PM / Tech Lead | 최종 merge |

**레이블링 가이드 문서** 를 1페이지 만들어 두세요. "무엇을 정답으로 볼 것인가" 의 기준이 사람마다 다르면 수치가 흔들립니다.

### 5-4. Hold-out 분리

평가셋의 **20~30%** 는 **숨겨 둡니다** (hold-out).

- 일반 evalset: 프롬프트 수정 시마다 매번 돌림 → 과적합됨
- Hold-out: 분기에 한 번만 돌려 **진짜 품질** 확인

둘의 점수가 크게 벌어지면 = **평가셋에 과적합 중** 이라는 신호.

### 5-5. 버전 관리

```
evalset/
  qa_v1.jsonl          # 초안 10건
  qa_v2.jsonl          # 30건 확장
  qa_v3.jsonl          # 100건 · coverage matrix 충족
  qa_holdout.jsonl     # hold-out 30건 (별도)
  CHANGELOG.md         # 무엇을 왜 바꿨는지
  labeling_guide.md
```

git 로 충분합니다 (jsonl 은 diff-friendly). 대용량이면 DVC.

---

## 6. 자주 깨지는 포인트

### 6-1. 평가셋 누출 (Test set leak)

가장 흔하고 가장 치명적. 증상: "프롬프트 수정할수록 점수가 오르는데 사용자 피드백은 정체."

원인: 개발자가 평가셋 오답을 보고 → 그 케이스를 풀도록 프롬프트 튜닝 → **평가셋에만** 과적합.

해결: **Hold-out** 을 열지 않기. CI 는 일반 셋으로, 분기 리뷰는 hold-out 으로.

### 6-2. 편향된 gold

"이 답이 맞다" 의 기준이 레이블러마다 다르면, gold 자체가 흔들립니다.

- 요약 태스크: "요약이 짧아야 정답인가 길어야 정답인가"
- 생성 태스크: "어디까지가 hallucination 인가"

레이블링 **가이드 문서 + 이중 검수 10~20%** 로 완화.

### 6-3. "쉬운 문제만" 의 함정

개발자는 실패하는 질문을 **피하려는** 본능이 있습니다. 결과: evalset 이 모범생 집합이 됨. 운영에선 어려운 질문이 실패.

방어: **어려움 비중 ≥ 30%** 를 coverage matrix 에 강제. 온라인에서 👎 나온 질문은 **자동 수집**.

### 6-4. 한 번 만들고 멈추기

"작년에 만든 evalset" 은 유물입니다. 도메인·사용자·모델이 다 바뀌었는데 수치만 그대로. **분기마다** 실로그에서 신규 샘플 추가 + 낡은 샘플 정리.

---

## 7. 운영 시 체크할 점

- [ ] 최소 30건 (QA) · 30건 (요약) · 100건 (분류) 의 초기 gold set 이 있는가
- [ ] **Coverage matrix** 로 난이도·도메인 balance 가 시각화됐는가
- [ ] **레이블링 가이드 문서** (1~2페이지) 가 있고 팀에 공유됐는가
- [ ] **Hold-out 20~30%** 가 별도 파일로 분리돼 CI 에서 **안 돌아가는가**
- [ ] `evalset/CHANGELOG.md` 에 "언제 · 왜 · 몇 건" 추가됐는지 기록되는가
- [ ] **분기 1회** 실로그에서 신규 샘플 수집·레이블링 사이클이 정착됐는가
- [ ] PII · 민감 정보 **마스킹** 정책이 있는가 (이름·전화번호·주소·카드번호)
- [ ] 👎 피드백이 온 질문이 **자동으로 샘플 풀**에 들어가는가

---

## 8. 연습문제 & 다음 챕터

### 확인 문제

1. 당신의 도메인(쇼핑·의료·인사 등)을 정하고, Coverage matrix 3×4 를 채워보세요. 각 셀에 목표 건수를 쓰세요.
2. 평가셋이 누출됐다는 **의심 신호** 3가지를 드세요.
3. LLM draft → Human review 하이브리드 레이블링이, 순수 human 보다 왜 **더 나은** 경우가 있는지 설명하세요.
4. 평가셋에 "어려움 30% 이상" 을 강제하는 것이 왜 중요한가요?

### 실습 과제

- 당신의 프로토타입에 **QA 10건 gold set** 을 만들고, [Ch 15](15-what-to-evaluate.md) §4 의 `recall_at_k` 를 돌려 첫 숫자를 기록하세요.
- 같은 10건에 LLM draft(Haiku) 로 `gold_answer` 를 뽑아보고, 당신이 직접 쓴 것과 비교 — 얼마나 다른가?

### 원전

- **Stanford CS329A HW** — Agent evaluation set 구축 가이드. 프로젝트 `_research/stanford-cs329a.md`
- **Ragas 문서** — `testset generation` 모듈 (synthetic testset) 참고
- **Anthropic Building Effective Agents** — 평가 데이터 수집 패턴. 프로젝트 `_research/anthropic-building-effective-agents.md`

---

**다음 챕터** → [Ch 17. LLM-as-a-Judge](17-llm-as-judge.md) — gold set 은 있는데 "얼마나 비슷한가"를 **누가 채점**할 것인가 :material-arrow-right:
