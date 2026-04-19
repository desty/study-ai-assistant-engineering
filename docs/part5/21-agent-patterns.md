# Ch 21. Agent 패턴 7가지

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part5/ch21_agent_patterns.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **Anthropic 5 워크플로우 패턴** — Prompt Chaining · Routing · Parallelization · Orchestrator-Workers · Evaluator-Optimizer
    - **OpenAI 2 에이전트 패턴** — Single-Agent · Multi-Agent
    - **패턴 결정 트리** — 어느 상황에 어느 패턴인지 위에서 아래로 질문
    - 각 패턴 **5~15줄 최소 구현** 스니펫
    - "패턴 이름 외우기" 의 덫 · 기본은 항상 단일 LLM + RAG

!!! quote "전제"
    [Ch 20](20-what-is-agent.md) — App vs Agent 경계, 루프의 5가지 필수요소. 이 챕터는 "루프가 필요하다면, 어떻게 짤까" 의 카탈로그.

---

## 1. 개념 — 패턴은 어휘다

Agent / 워크플로우를 논의할 때 **공통 어휘**가 없으면 설계 논의가 성립하지 않습니다.

- "LLM 을 여러 번 부를 건데…" → 얼마나? 순차? 병렬? 누가 결정?
- "에이전트로 하자" → single? multi? manager? decentralized?

**Anthropic 의 "Building Effective Agents"** (2024) 는 이걸 5+2 로 정리했습니다:

| 범주 | 패턴 | 출처 | 제어자 |
|---|---|---|---|
| **Workflow** (결정론적) | ① Prompt Chaining | Anthropic | 개발자 |
| | ② Routing | Anthropic | 개발자 |
| | ③ Parallelization | Anthropic | 개발자 |
| | ④ Orchestrator-Workers | Anthropic | 개발자 (+LLM 서브 결정) |
| | ⑤ Evaluator-Optimizer | Anthropic | 개발자 |
| **Agent** (자율) | ⑥ Single-Agent | OpenAI/Anthropic | LLM |
| | ⑦ Multi-Agent | OpenAI | LLM × N |

핵심: **워크플로우는 개발자가 경로를 지정**하고, **에이전트는 LLM 이 결정**. 뭐가 더 "agentic" 한지 스펙트럼이 달라집니다(Ch 20).

---

## 2. 왜 필요한가 — 패턴 없이 설계하면

"LLM 을 2번 호출하고, 결과 보고 다른 걸 호출…" 같이 **즉흥적으로** 구조를 짜면 코드가 다음처럼 됩니다:

- `if` 가 깊어지고, 각 가지마다 특수 케이스
- 병렬 처리 기회를 놓침 (순차만)
- 실패 시 어디서 재시도할지 일관성 없음
- 팀원이 "이거 왜 이 구조야?" 에 답 못함

패턴 이름을 쓰면:
- "이거 **routing + orchestrator-workers** 조합" → 5초에 이해
- 각 패턴에 맞는 **실패 대응·평가 전략**이 따로 있음 (Ch 19)
- 코드 구조가 예측 가능 → 인계·유지보수↑

---

## 3. 7패턴 한 장 요약

![7 패턴](../assets/diagrams/ch21-seven-patterns.svg#only-light)
![7 패턴](../assets/diagrams/ch21-seven-patterns-dark.svg#only-dark)

각 패턴을 한 줄씩:

### ⓪ 기본 — 단일 LLM + RAG

패턴 도입 **전** 먼저 시도. Part 3 로 대부분 커버.

### ① Prompt Chaining — LLM → LLM → LLM

한 출력이 다음 입력. 초안 → 교정 → 요약처럼 **단계별 변환**. 간단하고 강력.

### ② Routing — Classifier → 전문 LLM

입력 유형 분류 후 **적합한 경로**로. FAQ·결제·버그를 각각 다른 프롬프트로.

### ③ Parallelization — N 호출 병렬

독립 작업 동시에 → **합침**(voting/가중평균). Part 4 의 Self-Consistency 가 이 패턴의 예.

### ④ Orchestrator-Workers — Planner → Worker × N

상위 LLM 이 작업을 **쪼개서 지시**. 서브 워커가 각자 수행. 복잡 리서치·멀티스텝 코딩.

### ⑤ Evaluator-Optimizer — Gen ↔ Critic 루프

생성 → 평가 → **재생성**. 품질 수렴까지. 번역·코드 개선·글쓰기.

### ⑥ Single Agent — LLM + Tools loop

Ch 20 의 기본 agent. 하나의 LLM 이 **루프 주도**. 고객지원·데이터 탐색.

### ⑦ Multi-Agent — Manager / Decentralized

여러 agent 역할 분담. Ch 25 에서 자세히.

---

## 4. 최소 예제 — 5~15줄 스니펫

각 패턴의 가장 작은 구현. 실제론 에러 처리·trace 가 붙지만 **구조만**.

### 4-1. Prompt Chaining

```python title="chaining.py" linenums="1"
def outline(topic):   return call('개요를 5불릿으로: ' + topic)
def draft(outline):   return call('이 개요로 초안 작성:\n' + outline)
def polish(draft):    return call('문장 다듬고 길이 반으로:\n' + draft)

result = polish(draft(outline('리포트 작성 가이드')))
```

### 4-2. Routing

```python title="routing.py" linenums="1"
def router(q):
    cat = call(f'분류: faq / refund / bug\n질문: {q}\n출력은 단어 하나만').strip()
    return {'faq': faq_handler, 'refund': refund_handler, 'bug': bug_handler}[cat](q)
```

### 4-3. Parallelization

```python title="parallel.py" linenums="1"
from concurrent.futures import ThreadPoolExecutor

def multi_review(text):
    prompts = ['문법·어색한 표현', '사실 정확성', '논리 흐름']
    with ThreadPoolExecutor() as ex:
        reviews = list(ex.map(lambda p: call(f'{p} 관점 리뷰:\n{text}'), prompts))
    return call(f'다음 3개 리뷰 종합:\n' + '\n---\n'.join(reviews))
```

### 4-4. Orchestrator-Workers

```python title="orchestrator.py" linenums="1"
def orchestrate(task):
    plan = call(f'이 작업을 서브태스크 3개로 쪼개 JSON list 로: {task}')
    subtasks = json.loads(plan)
    results = [call(f'서브태스크 수행: {st}') for st in subtasks]  # 병렬 가능
    return call(f'결과 통합:\n' + '\n'.join(results))
```

### 4-5. Evaluator-Optimizer

```python title="evaluator_optimizer.py" linenums="1"
def gen_with_critique(topic, max_rounds=3):
    draft = call(f'초안: {topic}')
    for _ in range(max_rounds):
        feedback = call(f'평가 + 수정 지시:\n{draft}')
        if 'OK' in feedback[:20]:
            return draft
        draft = call(f'피드백 반영 재작성:\n{draft}\n---\n{feedback}')
    return draft
```

### 4-6. Single Agent

Ch 20 의 agent 루프 스켈레톤이 이것. 생략 (Ch 20 §5 참조).

### 4-7. Multi-Agent

Ch 25 에서 상세. 여기선 Manager 스니펫만:

```python title="multi_agent_manager.py" linenums="1"
def manager(task):
    plan = planner_agent(task)         # agent 1: 계획
    research = researcher_agent(plan)  # agent 2: 리서치
    draft = writer_agent(research)     # agent 3: 작성
    return critic_agent(draft)         # agent 4: 검증
```

각 서브 함수가 내부적으로 Ch 20 의 agent 루프를 돌린다.

---

## 5. 실전 튜토리얼 — 어느 패턴을 쓸까

![패턴 결정 트리](../assets/diagrams/ch21-pattern-decision.svg#only-light)
![패턴 결정 트리](../assets/diagrams/ch21-pattern-decision-dark.svg#only-dark)

**위에서 아래로** 질문을 따라갑니다. YES 에서 멈추면 그 패턴.

### 5-1. 실제 적용 사례 3가지

**사례 A: 고객 문의 봇 (FAQ + 환불 + 버그)**

- Q1: 단일 LLM + RAG 로 풀리나? → **NO** (FAQ/환불/버그 처리가 완전히 다름)
- Q2: 입력 유형별 분기만? → **YES**
- ✅ **Routing**

**사례 B: 리서치 → 리포트 작성**

- Q1: 단일 LLM + RAG → NO (단계 많음)
- Q2: 유형별 분기 → NO
- Q3: 단계별 파이프? → **YES** (조사 → 개요 → 초안 → 교정)
- ✅ **Prompt Chaining**

**사례 C: 코드 자동 리뷰**

- Q1–4 → NO
- Q5: 생성 → 평가 → 재생성? → **YES**
- ✅ **Evaluator-Optimizer**

### 5-2. 조합해서 쓰기

실제 제품은 **여러 패턴 조합**:
- Routing(유형 분류) → 각 카테고리마다 Chaining 또는 Agent
- Multi-Agent 안의 각 agent 가 Evaluator-Optimizer 로 품질 수렴
- Parallelization 으로 N 후보 → Evaluator 가 최고점 선택

"한 가지만" 규칙은 없음. 단, **왜 이 조합인가** 를 설명할 수 있어야 함.

---

## 6. 자주 깨지는 포인트

### 6-1. 패턴 이름 외우기 끝

"우리는 Orchestrator-Workers 씁니다" 라고 자랑하지만 **왜 그게 필요했는지** 답 못함. 패턴은 **문제의 해결책**이지 정체성이 아님.

원칙: 문제 먼저 → 어휘는 나중.

### 6-2. Baseline 스킵

대부분의 "우리한테 agent 가 필요해" 는 **단일 LLM + 좋은 RAG + 좋은 프롬프트** 로 풀립니다. Ch 21 의 패턴을 도입하기 전에 Part 3 를 제대로 했는지 먼저.

### 6-3. Orchestrator-Workers 과설계

3단계면 될 걸 planner 가 5단계로 쪼갬. 토큰·지연 ×5, 정확도 변화 없음. **Planner 가 계획 세울 때 max_subtasks 상한** 을 주세요.

### 6-4. Evaluator 가 Gen 과 같은 모델

자기 결과물을 비판 못함 (Ch 17 self-preference). Evaluator 는 **다른 계열 / 다른 크기** 로.

### 6-5. Multi-Agent 로 도망가기

Single agent 로 안 풀리는 문제를 "에이전트 4개로 쪼개면 되겠지" 로 해결? 보통 **복잡도 4배 + 디버깅 지옥**. Ch 25 에서 왜 이게 함정인지 상세.

---

## 7. 운영 시 체크할 점

- [ ] 우리가 쓰는 패턴 1~2개를 **문서에 이름으로** 기록했는가 (설계 리뷰 용)
- [ ] Baseline (단일 LLM + RAG) 성능을 **먼저 측정**한 뒤에 패턴을 도입했는가
- [ ] 각 패턴의 **실패 모드**를 분류하는 failure taxonomy (Ch 19) 가 있는가
- [ ] Orchestrator-Workers / Multi-Agent 에 **max_subtasks / max_agents 상한**이 있는가
- [ ] Evaluator 와 Generator 가 **다른 모델**인가
- [ ] 조합 패턴일 때 **경계**가 명확한가 (routing 후 chaining 의 경계 code 주석)
- [ ] 각 패턴 단위로 **trace 를 분리**해 측정 가능한가 (LangSmith/Langfuse tag)
- [ ] 패턴 변경을 **평가셋**(Part 4) 으로 측정하는가

---

## 8. 연습문제 & 다음 챕터

### 확인 문제

1. Workflow 5패턴과 Agent 2패턴의 핵심 차이(제어자 기준)는?
2. 당신 프로토타입에 적용할 수 있는 패턴 1개를 §5 결정 트리로 도출하세요.
3. "Multi-Agent 로 쪼개면 좋아질 것 같다" 는 직관이 왜 자주 틀린지 2문장으로.
4. Evaluator 와 Generator 를 **같은 모델** 로 쓰면 어떤 편향이 나올까요 (Ch 17 참조)?

### 실습 과제

- 당신의 문제에 §4 스니펫 중 하나를 **10줄 이내**로 구현.
- 같은 문제에 단일 LLM 호출 vs 패턴 적용 결과를 평가셋 10건에서 비교.

### 원전

- **Anthropic — Building Effective Agents** (Schluntz & Zhang 2024) — 5 패턴 원전. 프로젝트 `_research/anthropic-building-effective-agents.md`
- **OpenAI — A Practical Guide to Building Agents** — Single vs Multi · Manager/Decentralized. 프로젝트 `_research/openai-practical-guide-to-agents.md`

---

**다음 챕터** → [Ch 22. Tool Use 실전](22-tool-use.md) — Data · Action · Orchestration 툴 · ACI 설계 :material-arrow-right:
