# Ch 18. 추론 품질 높이기

<a class="colab-badge" href="https://colab.research.google.com/" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **같은 모델**에서 추론 **전략**을 바꿔 품질을 올리는 4가지 방법
    - **CoT** 심화 · **Self-Consistency** · **Best-of-N** · **Verifier**
    - **Test-time compute** — 비용을 더 써서 품질을 사는 트레이드오프
    - 수학 문제로 self-consistency · 코드 문제로 best-of-N + pytest verifier 구현
    - N 을 늘리다가 터지는 비용·지연·verifier 품질 3대 병목

!!! quote "전제"
    [Ch 15](15-what-to-evaluate.md)–[Ch 17](17-llm-as-judge.md). 평가 기준과 Judge 가 있으니, 이제 **답 자체의 품질**을 끌어올리는 전략으로 넘어간다.

---

## 1. 개념 — 한 번 묻지 말고, 여러 번 제대로 묻자

LLM 에 같은 질문을 5번 던지면 5개의 다른 답이 나옵니다. 이 **확률성**을 약점이 아니라 **자산**으로 바꾸는 게 이 챕터의 핵심 아이디어입니다.

![4가지 추론 기법](../assets/diagrams/ch18-reasoning-4methods.svg#only-light)
![4가지 추론 기법](../assets/diagrams/ch18-reasoning-4methods-dark.svg#only-dark)

네 가지 전략을 한 장으로:

| 기법 | 아이디어 | 대표 장점 |
|---|---|---|
| ① Single | 직접 답 하나 | 빠르고 싸다 |
| ② **CoT** | "단계별로 생각해" → 추론 trace 유도 | 토큰만 늘리면 됨 |
| ③ **Self-Consistency** | N개 샘플 → 다수결 | 수학·다지선다 QA 에 강력 |
| ④ **Best-of-N + Verifier** | N개 생성 → verifier 가 선택 | 코드·검증 가능 태스크에 최강 |

공통 원리: **test-time compute** — 학습은 고정, **추론 시점**에 계산을 더 써서 품질을 산다.

---

## 2. 왜 필요한가

**① 모델을 교체할 수 없을 때.** Opus 로 올릴 예산이 없는데 Sonnet 으로 정확도 70% → 85% 가 필요하다. 추론 전략으로 메꿀 수 있음.

**② 도메인이 확률적 오답을 감당 못할 때.** 수학·코드·금액 계산은 한 번 틀리면 치명적. N=5 의 다수결·검증으로 방어율↑.

**③ Judge 친화적 세팅이 이미 있을 때.** Ch 17 의 Judge 를 verifier 로 재활용 가능. 기존 인프라 위에 얹기 좋음.

단, **비용·지연 ×N** 은 고정 비용. §6 에서 다룸.

---

## 3. 어디에 쓰이는가 — 기법별 적합 도메인

### 3-1. CoT 심화

- **수학·논리**: "단계별로" 한 줄이 정확도 20~40% 끌어올림 (Wei 2022)
- **복잡한 분류**: 판단 근거를 쓰게 하면 쉬운 패턴 매칭 오류가 줄어듦
- **한계**: 잘못된 추론이 그럴듯하게 길어질 수 있음 — Ch 19 에서 다룰 failure mode

### 3-2. Self-Consistency

- **정답이 이산(discrete)**: 숫자 · 카테고리 · 객관식
- 원리: 여러 CoT 경로를 샘플링 → 최종 답만 추출 → **최빈값**
- 연속 답(요약·글쓰기)에는 부적합 (다수결 자체가 안 됨)

### 3-3. Best-of-N + Verifier

- **검증 가능한 태스크**: 코드(실행) · SQL(DB 검증) · 수학(역대입)
- 원리: N 개 후보 → verifier 가 각각 점수/합격 판정 → 최고점 선택
- Verifier 종류:
    - **Deterministic**: pytest · DB 쿼리 실행 · 정규식
    - **LLM-as-verifier**: Judge 재활용 (rubric 기반)
    - **Reward model**: 학습된 scorer (논문 수준)

### 3-4. Tree of Thoughts (맥락만)

분기를 트리로 탐색. 구현 복잡도 ↑ · 비용 ↑. 본 책에선 개념만 언급. 궁금하면 Yao et al. 2023.

---

## 4. 최소 예제 — Self-Consistency 로 수학 문제 풀기

```python title="self_consistency.py" linenums="1" hl_lines="11 25"
import anthropic
from collections import Counter
import re

client = anthropic.Anthropic()

COT_SYS = """문제를 단계별로 풀고, 마지막 줄에 반드시 다음 형식으로 최종 답을 쓰세요.
ANSWER: <숫자만>"""

def sample_one(question, temperature=0.7):  # (1)!
    msg = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=500,
        system=COT_SYS,
        messages=[{'role': 'user', 'content': question}],
        # Anthropic SDK: temperature 파라미터
    )
    text = msg.content[0].text
    m = re.search(r'ANSWER:\s*([-\d.]+)', text)
    return m.group(1) if m else None

def self_consistency(question, n=5):  # (2)!
    answers = [sample_one(question) for _ in range(n)]
    answers = [a for a in answers if a is not None]
    if not answers:
        return None, 0
    most_common, cnt = Counter(answers).most_common(1)[0]
    return most_common, cnt / n  # 답 + 신뢰도 (일치 비율)

q = '한 상자에 24개의 사과가 있고 3명이 똑같이 나눴습니다. 한 명당 몇 개?'
ans, conf = self_consistency(q, n=5)
print(f'답: {ans}, 신뢰도: {conf:.0%}')
```

1. **단일 샘플러** — temperature 를 높여 다양성 확보. CoT 시스템 프롬프트로 추론 유도.
2. **다수결** — 가장 많이 나온 답 + 그 비율(신뢰도). 100% 일치 = 매우 확신. 40% = 경계.

**신뢰도를 활용**: 0.8 이상만 신뢰, 그 아래는 사람/다른 모델로 에스컬레이션.

---

## 5. 실전 튜토리얼 — Best-of-N + pytest verifier (코드 문제)

코드 생성에 **결정적 verifier**(pytest) 를 붙이면 품질이 극적으로 오릅니다.

### 5-1. 구조

```
Q: "두 정수 합 함수 add(a,b) 작성"
  ↓
N=5 generations (temperature=0.8)
  ↓
각 후보를 sandbox 에서 테스트 실행
  ↓
pass 한 후보 중 첫 번째 (또는 judge 로 최고점)
```

### 5-2. 코드

```python title="best_of_n_code.py" linenums="1" hl_lines="12 32"
import subprocess, tempfile, os, textwrap
import anthropic

client = anthropic.Anthropic()

def generate_candidates(prompt, n=5):
    results = []
    for _ in range(n):
        msg = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=400,
            messages=[{'role': 'user', 'content': prompt}],
        )
        results.append(msg.content[0].text)
    return results

TEST_CODE = """
def test_add():
    from solution import add
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
"""

def verify(code):  # (1)!
    with tempfile.TemporaryDirectory() as td:
        with open(f'{td}/solution.py', 'w') as f:
            f.write(code)
        with open(f'{td}/test_solution.py', 'w') as f:
            f.write(TEST_CODE)
        r = subprocess.run(
            ['pytest', '-q', td], capture_output=True, text=True, timeout=15
        )
        return r.returncode == 0

def best_of_n(prompt, n=5):  # (2)!
    for i, cand in enumerate(generate_candidates(prompt, n)):
        code = extract_python(cand)  # 코드블록만 뽑기
        if verify(code):
            return code, i  # 첫 번째 통과
    return None, -1
```

1. **Verifier** — pytest 가 결정적으로 pass/fail 판정. LLM 의존이 0.
2. **Best-of-N 루프** — 첫 통과 즉시 반환(조기 종료). 모두 실패면 `None`.

### 5-3. 기대 효과

- N=1: 정확도 60%
- N=5 + verifier: **90%+**  
비용은 평균 ~2~3× (조기 종료 덕분에 5× 안 됨).

![Cost vs Quality](../assets/diagrams/ch18-cost-vs-quality.svg#only-light)
![Cost vs Quality](../assets/diagrams/ch18-cost-vs-quality-dark.svg#only-dark)

---

## 6. 자주 깨지는 포인트

### 6-1. 토큰·비용 ×N

Self-Consistency N=5 = 비용 × 5 · 지연 × 5(동시 호출 안 하면). **반드시** 평가셋에서 품질 이득을 측정하고, "그만큼의 비용 가치" 가 있는지 결정.

### 6-2. Verifier 가 병목

Best-of-N 품질은 verifier 품질을 **초과할 수 없음**. LLM-as-verifier 의 합의율이 0.7 이면, N 을 아무리 늘려도 품질 상한이 있음. Ch 17 의 calibration 필수.

### 6-3. 다양성 부족

Temperature 가 0.3 인데 N=20 을 돌리면 거의 같은 답 20개. 의미 없음. Self-Consistency 는 **temperature ≥ 0.7** 권장.

### 6-4. 연속 답에 self-consistency

"요약 써주세요" 에 다수결이 안 됨. N=5 요약 중 하나를 고르려면 **Judge 기반 best-of-N** 을 써야지 voting 이 아님.

### 6-5. Early stopping 함정

Best-of-N 에서 첫 통과 즉시 반환하면 **품질은 동일하지만 평균 비용만** 감소. 품질 최대화를 원하면 N 개 모두 생성 후 judge 로 최고점. 목적에 따라 선택.

---

## 7. 운영 시 체크할 점

- [ ] Self-Consistency / Best-of-N 을 쓸 **태스크 유형**을 명시했는가 (수학·코드·분류만)
- [ ] N 값을 **평가셋에서 측정**해 결정했는가 (관성적으로 5 쓰지 말 것)
- [ ] Verifier 가 **결정적(pytest·regex)** 인가, **LLM 기반** 인가, 후자라면 합의율 추적하는가
- [ ] 토큰·지연 **×N** 이 운영 SLO 안에 들어오는가
- [ ] 병렬 호출로 지연 상쇄되는가 (순차 N=5 는 지연 5× · 병렬 N=5 는 1×)
- [ ] Self-Consistency **신뢰도(일치율)** 를 로깅해, 낮은 건 자동 에스컬레이션 하는가
- [ ] 조기 종료(Early stopping)의 품질 영향을 측정했는가
- [ ] 추론 비용 상승 시 **한 단계 작은 모델 + 추론 전략** vs **큰 모델 단일** 비교를 주기적으로 하는가

---

## 8. 연습문제 & 다음 챕터

### 확인 문제

1. Self-Consistency 가 "요약 태스크" 에 부적합한 이유를 설명하고 대안(best-of-N+judge)이 왜 작동하는지 비교하세요.
2. Best-of-N 에서 verifier 가 LLM Judge 일 때 생기는 추가 리스크 2가지를 드세요 (Ch 17 참조).
3. N=1(Single) 과 N=5(Self-Consistency) 의 **기대 비용·지연·품질** 을 수식으로 비교하세요.
4. Test-time compute 를 늘리는 것보다 **모델을 업그레이드**하는 게 나은 경우는 언제인가요?

### 실습 과제

- GSM8K 같은 수학 데이터 10문제에 Haiku 단일 vs Haiku + Self-Consistency(N=5) 정확도 비교.
- LeetCode Easy 10문제에 Haiku Best-of-N + pytest verifier 를 구현 · N=1/3/5 정확도 기록.

### 원전

- **Wei et al. 2022** — Chain-of-Thought Prompting
- **Wang et al. 2022** — Self-Consistency
- **Cobbe et al. 2021** — Verifier / reward model
- **Stanford CS329A Lec 2–3** — Test-time compute · Archon · "Let's Verify Step by Step". 프로젝트 `_research/stanford-cs329a.md`

---

**다음 챕터** → [Ch 19. 실패 분석과 디버깅](19-failure-analysis.md) — 숫자가 나왔으면, 이제 **왜 틀렸는지** 원인을 층별로 분리 :material-arrow-right:
