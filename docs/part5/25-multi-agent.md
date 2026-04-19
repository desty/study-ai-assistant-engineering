# Ch 25. 멀티 에이전트와 역할 분리

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part5/ch25_multi_agent.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **Manager** vs **Decentralized** 2패턴 — 언제 어느 것
    - 역할 분리 3예시 — Planner/Executor · Researcher/Writer · Verifier/Responder
    - **언제 쪼개야 하나** 의 엄격한 기준
    - 멀티 에이전트 3대 실패 (context 누락 · 무한 토스 · 책임 불명확)
    - 쪼갠 뒤 **다시 합쳐야** 할 신호
    - **Part 5 전체 마무리** — Agent 졸업 상태 5종

!!! quote "전제"
    [Ch 20](20-what-is-agent.md)–[Ch 24](24-agent-memory.md). Single agent 루프 · tool design · state graph · memory 전부 있는 상태에서, 이제 "진짜 필요할 때만" 쪼갠다.

---

## 1. 개념 — 쪼갠다는 건 뭘 의미하나

멀티 에이전트는 "여러 LLM 호출" 이 아닙니다. 그건 Ch 21 의 **Workflow 패턴**(chaining·orchestrator).

> **Multi-Agent** = 각 agent 가 **독립된 루프·도구·시스템 프롬프트**를 가지고, 서로를 **호출**하거나 **턴을 넘기는** 구조.

OpenAI "A Practical Guide to Building Agents" 는 2패턴으로 분류:

![Manager vs Decentralized](../assets/diagrams/ch25-manager-vs-decentralized.svg#only-light)
![Manager vs Decentralized](../assets/diagrams/ch25-manager-vs-decentralized-dark.svg#only-dark)

| 패턴 | 구조 | 대표 케이스 |
|---|---|---|
| **Manager** | 중앙이 서브 agent 를 도구처럼 호출 | planner 가 researcher/writer 를 지시 |
| **Decentralized** | peer 끼리 handoff | customer-support → billing → shipping 릴레이 |

**Manager 가 기본값**. Decentralized 는 문제에 대한 확신이 있을 때만.

---

## 2. 왜 필요한가 — 쪼개는 진짜 이유

쪼개는 게 **좋아 보이는 이유** (대부분 착각):
- "Agent 가 많을수록 전문화될 것"
- "코드가 모듈화돼 관리 쉬움"
- "각자 다른 프롬프트 쓰면 품질 ↑"

쪼개는 **진짜 이유** (드물지만 확실):

**① 시스템 프롬프트가 서로 모순.** 한 프롬프트에 "창의적으로" + "엄격히 사실만" 이 공존 불가. 분리.

**② 툴 세트가 완전히 다르고 많음.** 각각 20개 툴이면 단일 agent 는 10개 초과(Ch 22). 분리.

**③ 독립 실패·재시작 필요.** researcher 가 실패해도 writer 는 기다리게 하고 재시도. 격리된 실패 경계.

**④ 서로 다른 모델 필요.** planner 는 Opus, executor 는 Haiku × 5. 비용·지연 최적화.

위 조건 **중 2개 이상** 걸리지 않으면, 쪼개지 말고 **single agent + 좋은 프롬프트** 로.

---

## 3. 어디에 쓰이는가 — 역할 분리 3예시

### 3-1. Planner / Executor

- Planner: 목표를 단계로 쪼갬 (Opus)
- Executor: 각 단계를 툴 써서 실행 (Haiku)
- Ch 21 의 Orchestrator-Workers 와 유사 · 차이는 executor 가 **자율 루프**

### 3-2. Researcher / Writer / Critic

- Researcher: 정보 수집 (검색·DB 툴)
- Writer: 문서 작성 (텍스트 생성)
- Critic: 품질 평가 (Ch 17 Judge 재활용)
- 리포트 자동 생성에 전형적

### 3-3. Verifier / Responder

- Responder: 사용자에게 답
- Verifier: 답이 내부 정책 위반인지 검사 (가드레일 · Part 6 Ch 28 예고)
- 병렬 배치 가능

---

## 4. 최소 예제 — Manager 패턴 2-agent

```python title="manager_two_agent.py" linenums="1" hl_lines="14 26"
# Manager 가 sub_agent 를 "tool" 로 호출
import anthropic
client = anthropic.Anthropic()

def researcher_agent(topic: str) -> str:  # (1)!
    # 내부에서 검색 툴 루프 돌림 (Ch 20 agent skeleton)
    r = client.messages.create(
        model='claude-haiku-4-5-20251001', max_tokens=500,
        system='당신은 researcher. 주제에 대한 핵심 3가지 사실만 반환.',
        messages=[{'role': 'user', 'content': topic}],
    )
    return r.content[0].text

SUB_AGENTS = [{  # (2)! manager 에게 이걸 tool 로 노출
    'name': 'researcher_agent',
    'description': '주제를 주면 핵심 3가지 사실을 조사해 반환한다. 리포트 작성 전 반드시 호출.',
    'input_schema': {
        'type': 'object',
        'properties': {'topic': {'type': 'string'}},
        'required': ['topic'],
    },
}]

def manager(user_msg):
    messages = [{'role': 'user', 'content': user_msg}]
    for _ in range(10):
        r = client.messages.create(
            model='claude-sonnet-4-6', max_tokens=1000,
            system='당신은 manager. 필요 시 researcher_agent 를 호출해 정보 모은 뒤 리포트 작성.',
            tools=SUB_AGENTS,
            messages=messages,
        )
        messages.append({'role':'assistant','content':r.content})
        if r.stop_reason == 'end_turn':
            return r.content[0].text
        # sub agent 호출
        results = []
        for b in r.content:
            if b.type == 'tool_use':
                out = researcher_agent(**b.input)  # (3)!
                results.append({'type':'tool_result','tool_use_id':b.id,'content':out})
        messages.append({'role':'user','content':results})
```

1. **Sub-agent 는 일반 함수** 지만 내부에 자체 루프·tool 을 가짐. Manager 에게는 **블랙박스**.
2. **Tool schema 로 노출** — manager 는 이걸 다른 tool 과 똑같이 다룸.
3. **Sub-agent 실행도 우리 코드** — Ch 22 ACI 원칙 그대로.

**핵심**: manager 입장에서 sub-agent 는 그냥 tool. 내부 복잡성은 숨김.

---

## 5. 실전 튜토리얼 — 3대 실패 시나리오

![3대 실패](../assets/diagrams/ch25-failure-modes.svg#only-light)
![3대 실패](../assets/diagrams/ch25-failure-modes-dark.svg#only-dark)

### 5-1. Context 누락

**증상**: Researcher 가 원문 10페이지 읽음 → Writer 에게 "3문장 요약" 만 넘김 → Writer 가 세부 질문에 답 못함. 요약의 요약이 됨.

**해결**:
- Manager 패턴에선 **shared state** (LangGraph `State`) 에 원문 저장 → 모든 agent 가 접근
- Handoff 시 요약뿐 아니라 **원문 참조 id** 함께 전달 → Writer 가 필요 시 재조회

### 5-2. 무한 토스 루프

**증상**: Writer → Critic "수정 요청" → Writer → Critic "또 수정" → … 10회 반복. 비용 × 10.

**해결**:
- `max_handoffs=3` 상한 필수
- Critic 에게 **"approve" 명시적 액션** · approve 아니면 Manager 로 에스컬레이트
- LangGraph `interrupt_before='critic'` 으로 **승인 대기** 에 사람 게이트

### 5-3. 책임 불명확

**증상**: Researcher "데이터 여기" · Writer "불충분, 더 줘" · Researcher "뭘 더?". 서로 미루고 응답 안 감.

**해결**:
- **Owner 지정** — 기본 Manager, decentralized 면 "end agent" 명시
- 최종 응답 node 가 **단일** 해야 (여러 곳에서 사용자에게 말하면 혼란)

### 5-4. 다시 합쳐야 할 신호

아래 중 **2개 이상** 해당하면 multi-agent 를 **단일 agent + 좋은 프롬프트** 로 합칩니다:

- 매 handoff 마다 context 가 복제·중복됨
- 실패의 50% 이상이 agent 간 전달 지점에서 발생
- 단일 agent 버전이 **같은 품질** 을 더 싸게 냄
- 디버깅 시 "어느 agent 가 잘못했는가" 를 매번 찾아야 함

---

## 6. 자주 깨지는 포인트

### 6-1. 단일 agent 실험 없이 쪼개기

"리포트 생성기 만들 건데, 3-agent 로 시작" — 최악. 먼저 **단일 agent**. 실패 모드 확인. 그 뒤 쪼갤지 판단.

### 6-2. Decentralized 를 Manager 대신

Decentralized 는 **유연**하지만 **디버깅 지옥**. 프로덕션은 80%+ Manager. peer handoff 는 도메인이 진짜 수평 (billing ↔ shipping) 일 때만.

### 6-3. max_handoffs 없음

Ch 20 의 `max_steps` 와 같은 원칙. 상한 없으면 무한 루프. `max_handoffs=3~5`.

### 6-4. 각 agent 에 다른 모델 섞어 쓰기의 부작용

Manager 는 Opus, Worker 는 Haiku — 이득은 있으나 **평가 복잡도 × 2**. "어느 모델이 병목?" 을 evalset 별도로. Part 4 에 추가 작업.

### 6-5. Sub-agent 를 인간처럼 이름 붙이기

"Alice 가 Bob 에게 말함" 식 로깅은 멋지지만 **digit한 이름** (`researcher_v2`) 이 운영·버전 관리에 유리.

---

## 7. 운영 시 체크할 점

- [ ] **단일 agent 기준선** 성능을 측정한 뒤 쪼갰는가
- [ ] 쪼갠 이유가 **§2 의 4가지 조건 중 2개 이상** 해당하는가
- [ ] **Manager 패턴을 기본**으로 선택했는가 (decentralized 선택 이유 별도 기록)
- [ ] `max_handoffs` · `max_steps` **상한**이 있는가
- [ ] Agent 간 **context 전달**이 shared state 또는 원문 참조로 보장되는가
- [ ] **최종 응답 node** 가 단일인가 (사용자 혼란 방지)
- [ ] 각 agent 의 **실패가 독립**적인가 (한 곳 실패가 전체 마비 X)
- [ ] Multi-agent 도입 후 **품질·비용·지연** 을 단일 agent 대비 측정했는가
- [ ] 다시 합칠 신호(§5-4) 를 **분기별** 체크하는가
- [ ] Trace 에 `agent_name` 필드가 있어 분리 분석 가능한가

---

## 8. 연습문제

### 확인 문제

1. Multi-agent 를 도입할 4가지 **진짜 이유** 중 2개가 해당해야 한다는 규칙의 근거를 설명하세요.
2. Manager vs Decentralized 각각의 디버깅 난이도를 비교하세요.
3. 3대 실패 (context 누락 · 무한 토스 · 책임 불명확) 각각에 대한 **예방 수단** 1개씩.
4. "단일 agent 로 합치는" 신호 4가지 중 당신의 시스템에 해당되는 것?

### 실습 과제

- §4 의 Manager 패턴으로 "리포트 생성기" 구현: Researcher + Writer 2-agent.
- 같은 문제를 **단일 agent** 로도 구현. 품질·비용·지연 비교.
- 단일 agent 로 충분하면 multi-agent 버전 **버리기** (합리적 의사결정 기록).

### 원전

- **OpenAI — A Practical Guide to Building Agents** — Manager vs Decentralized. 프로젝트 `_research/openai-practical-guide-to-agents.md`
- **Stanford CS329A Lec 7** — Open-Ended Evolution of Self-Improving Agents. 프로젝트 `_research/stanford-cs329a.md`
- **Anthropic — Building Effective Agents** — "Use agents when needed, not by default". 프로젝트 `_research/anthropic-building-effective-agents.md`

---

## 9. Part 5 마무리 — Agent 졸업 상태

Part 5 전체를 한 장으로:

| Ch | 주제 | 핵심 산출물 |
|---|---|---|
| 20 | Agent 란 무엇인가 | OpenAI 3요소 · 자율성 4단계 · 루프 5필수요소 |
| 21 | Agent 패턴 7가지 | Workflow 5 + Agent 2 · 결정 트리 · 5~15줄 스니펫 |
| 22 | Tool Use 실전 | ACI 5요소 · 3범주×위험도 · approval queue |
| 23 | LangGraph | StateGraph · checkpointer · interrupt · time travel |
| 24 | Agent 메모리 | Thread/Store 2계층 · extract/load · PII 대응 |
| 25 | 멀티 에이전트 | Manager vs Decentralized · 3대 실패 · 합치기 신호 |

### Part 5 졸업 상태

1. **단일 agent 루프** (max_steps · tool_result 에러 · trace) 을 한 번 이상 구현
2. **최소 한 가지 워크플로우 패턴** (Routing / Chaining / Evaluator-Optimizer) 을 실제 태스크에 적용
3. **LangGraph StateGraph** 를 고객 문의 같은 다분기 flow 로 구성 · checkpointer 사용
4. **Store** 에 사용자 선호 저장·조회 · PII masking 고려
5. 필요 시 **Multi-agent** 로 확장하되, 단일 agent 와 **성능 비교** 기록 있음

### 다음 — Part 6. 운영형 AI Assistant

Agent 는 됐으니, 이걸 **진짜 운영**하는 기술. 가드레일 7종, 비용·지연 최적화, 모니터링, 사용자 피드백 루프, 릴리스. Part 5 는 **기능**, Part 6 는 **안전·효율·수명**.

---

**다음 챕터** → [Ch 26. Production 아키텍처](../part6/26-prod-arch.md) :material-arrow-right:
