# Ch 23. LangGraph — 상태 그래프

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part5/ch23_langgraph.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **StateGraph** — node · edge · conditional edge · reducer
    - **Checkpointer** — 매 node 실행 후 state 저장 (SqliteSaver / Postgres)
    - **Thread ID** — 대화 지속 · 재개
    - **Interrupt** — agent 일시 중지, 인간 승인 후 **resume**
    - **Streaming** — node 단위 점진적 응답 (UX 용)
    - 과설계 함정 · conditional edge 지옥 · stream 중 예외

!!! quote "전제"
    [Ch 22](22-tool-use.md) — ACI · approval queue. 이번 챕터는 그 승인 패턴을 **LangGraph 표준 방식** 으로 구현.

---

## 1. 개념 — 루프 대신 그래프

Ch 20~22 의 agent 는 **while loop**. 단순하지만 production 에선 다음이 필요합니다:

- **상태 공유**: 여러 node 가 같은 state 를 읽고 씀
- **체크포인트**: 중간 실패 · 재시작 시 복구
- **분기·병렬**: 조건부 경로 · 독립 작업 동시 실행
- **사람 게이트**: 중간에 멈춰서 사람 승인 기다림
- **스트리밍**: UI 로 진행 상황 실시간 송출

이걸 직접 짜면 금방 스파게티. **LangGraph** 는 이 패턴들의 표준 레일.

> StateGraph = **상태 스키마** + **node 함수** + **edge 연결** + **checkpointer**.

---

## 2. 왜 필요한가 — 루프 vs 그래프

**루프의 한계**:
- 상태가 암묵적 (변수 리스트로 흩어짐) → 재현·디버깅 어려움
- 실패 시 처음부터 재시작 (긴 agent 는 비용·지연 ↑)
- 사람 승인 중간에 못 끼워넣음

**그래프의 이점**:
- **state 가 명시적 TypedDict** → 타입 체크 · 이동 추적
- **매 node 후 checkpoint** → 실패 지점부터 재개
- **interrupt** 한 줄로 pause
- **trace 가 자동** (LangSmith 연동)

비용: 러닝 커브 + 라이브러리 의존. 제품 규모가 커지면 이득이 커브 초과.

---

## 3. 어디에 쓰이는가 — StateGraph 구성

![StateGraph Anatomy](../assets/diagrams/ch23-stategraph-anatomy.svg#only-light)
![StateGraph Anatomy](../assets/diagrams/ch23-stategraph-anatomy-dark.svg#only-dark)

### 3-1. 구성 요소

| 요소 | 역할 | 예 |
|---|---|---|
| **State** | 공유 메모리 (TypedDict) | `messages · intent · needs_human` |
| **Node** | state 를 읽고 **업데이트 반환** 하는 함수 | `classify_intent(state) -> {'intent': 'refund'}` |
| **Edge** | node 간 흐름 | `START → classify → respond → END` |
| **Conditional Edge** | state 보고 **다음 node 선택** | `intent == 'refund' → refund_check` |
| **Reducer** | state 병합 규칙 | `add_messages` (리스트 append) |
| **Checkpointer** | state 저장소 | SqliteSaver · PostgresSaver |
| **Thread ID** | 대화/세션 구분 | `{'configurable': {'thread_id': 'user-42'}}` |

### 3-2. 언제 StateGraph 대신 다른 걸 쓸까

- **단일 LLM 호출**: StateGraph 과함. 그냥 함수.
- **순수 chaining (A→B→C, 분기 없음)**: LCEL 이 더 간단
- **정말 자율적 agent (LLM 이 전부 결정)**: Ch 20 루프 + Ch 22 툴이면 충분
- **복잡 상태 · 승인 · 재개**: ✅ StateGraph

---

## 4. 최소 예제 — 고객 지원 3분기 그래프

의도 분류 → (FAQ / 환불 / 버그) 분기 → 응답. 환불은 interrupt.

```bash
pip install langgraph langchain-anthropic
```

```python title="support_graph.py" linenums="1" hl_lines="8 27 43"
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import Annotated
from langchain_anthropic import ChatAnthropic

class State(TypedDict):  # (1)!
    messages: Annotated[list, add_messages]
    intent: str
    response: str

llm = ChatAnthropic(model='claude-haiku-4-5-20251001')

def classify(state: State):  # (2)!
    last = state['messages'][-1].content
    prompt = f'분류: faq / refund / bug\n질문: {last}\n단어 하나만:'
    intent = llm.invoke(prompt).content.strip().lower()
    return {'intent': intent if intent in ['faq','refund','bug'] else 'faq'}

def faq_answer(state: State):
    r = llm.invoke(f'FAQ 친절히 답: {state["messages"][-1].content}')
    return {'response': r.content}

def refund_check(state: State):
    return {'response': '환불 요청 확인 중…'}  # 실전은 DB 조회

def escalate(state: State):
    return {'response': '담당자에게 전달합니다.'}

def respond(state: State):
    return {'messages': [{'role': 'assistant', 'content': state['response']}]}

def route(state: State) -> Literal['faq_answer','refund_check','escalate']:  # (3)!
    return {'faq':'faq_answer','refund':'refund_check','bug':'escalate'}[state['intent']]

# Build graph
g = StateGraph(State)
g.add_node('classify', classify)
g.add_node('faq_answer', faq_answer)
g.add_node('refund_check', refund_check)
g.add_node('escalate', escalate)
g.add_node('respond', respond)

g.add_edge(START, 'classify')
g.add_conditional_edges('classify', route)  # (4)!
for n in ['faq_answer','refund_check','escalate']:
    g.add_edge(n, 'respond')
g.add_edge('respond', END)

# Compile with checkpointer
memory = SqliteSaver.from_conn_string(':memory:')  # 실전은 파일/DB
app = g.compile(checkpointer=memory)
```

1. **State** — `Annotated[list, add_messages]` 가 핵심. reducer 가 append 처리.
2. **Node** — state 받아서 **업데이트할 필드만** 반환. 전체 state 덮어쓰기 X.
3. **Router** — conditional edge 의 판정 함수. 반환값이 다음 node 이름.
4. **add_conditional_edges** — 여러 분기 한 번에 등록.

### 실행

```python title="run_graph.py" linenums="1"
cfg = {'configurable': {'thread_id': 'user-42'}}
result = app.invoke(
    {'messages': [{'role': 'user', 'content': '주문 O-1024 환불되나요?'}]},
    config=cfg,
)
print(result['response'])
```

`thread_id` 가 같으면 **대화가 이어집니다** (state 복구).

---

## 5. 실전 튜토리얼 — Interrupt + Resume

![Interrupt Flow](../assets/diagrams/ch23-interrupt-flow.svg#only-light)
![Interrupt Flow](../assets/diagrams/ch23-interrupt-flow-dark.svg#only-dark)

### 5-1. interrupt_before 로 게이트 추가

승인 필요 node **앞에서** 그래프를 멈춘다.

```python title="interrupt_graph.py" linenums="1" hl_lines="4 14"
app = g.compile(
    checkpointer=memory,
    interrupt_before=['refund_check'],  # (1)! 이 node 들어가기 전 pause
)

cfg = {'configurable': {'thread_id': 'user-42'}}

# 1차 실행 — classify 까지만 돌고 멈춤
result = app.invoke({'messages': [{'role':'user','content':'환불해줘'}]}, cfg)

# state 확인 (운영자 UI 에 띄움)
snapshot = app.get_state(cfg)
print(snapshot.values['intent'])   # 'refund'
print(snapshot.next)                # ('refund_check',)

# 2차 실행 — 승인 후 resume. invoke(None) 이 재개 시그널
result = app.invoke(None, cfg)  # (2)!
print(result['response'])
```

1. **interrupt_before** — 진입 직전 pause. `interrupt_after` 도 있음.
2. **invoke(None, config)** — "이어서 해" 의미. checkpointer 에서 state 복구.

### 5-2. 실제 운영 패턴

```
┌─ 사용자 요청
│
▼
graph.invoke(...)  # 첫 호출
│
├─ classify 실행
│
├─ interrupt_before='refund_check'  → pause, state 저장
│
└─ return (운영자에게 알림 · Slack / 대시보드)

[~10분 후]

운영자 승인 → webhook 호출
│
▼
graph.invoke(None, {'thread_id': ...})  # 재개
│
├─ refund_check 실행
├─ respond 실행
└─ END, 사용자에게 응답 전송
```

**핵심**: thread_id 만 있으면 되고, 중간 상태가 DB 에 있어서 **재시작·복구** 가 자유롭다.

### 5-3. Streaming — 실시간 UX

```python title="stream_graph.py" linenums="1"
for chunk in app.stream(
    {'messages': [{'role':'user','content':'FAQ 질문'}]},
    config=cfg,
    stream_mode='updates',  # 'values' · 'messages' · 'updates' · 'debug'
):
    print(chunk)  # {node_name: {필드: 값}}
```

각 node 완료마다 청크 방출. UI 에 "분류 중… 답변 작성 중…" 같이 progress 표시.

### 5-4. Time Travel — 이전 상태로

```python title="time_travel.py" linenums="1"
# 모든 체크포인트 조회
for snap in app.get_state_history(cfg):
    print(snap.config['configurable']['checkpoint_id'], snap.next)

# 특정 시점 state 로 포크 후 다른 경로로 재실행
past = list(app.get_state_history(cfg))[3]
new_cfg = past.config  # 이 지점부터
app.invoke({'intent': 'faq'}, new_cfg)  # state 덮어쓰기 + 진행
```

디버깅·A/B 에 유용.

---

## 6. 자주 깨지는 포인트

### 6-1. StateGraph 과설계

3 node 면 끝날 flow 에 10 node, conditional edge 7개. **LCEL · 단순 함수** 로 풀릴 걸 LangGraph 로 만들지 말 것. 상태·체크포인트·interrupt 셋 중 **둘 이상이 필요할 때** StateGraph.

### 6-2. Conditional edge 지옥

`add_conditional_edges(X, router_fn)` 가 많아지면 **flow 를 한눈에 못 봄**. 5개 초과하면 flow 를 **2개 서브그래프** 로 쪼개세요.

### 6-3. State 를 통째로 덮어쓰기

Node 가 `return state` 하면 전체 덮어씀 (reducer 무시). 반드시 **업데이트할 필드만** 반환: `return {'intent': 'refund'}`.

### 6-4. Checkpointer 미설정

`checkpointer=None` 이면 interrupt·resume · thread 안 됨. 개발은 `SqliteSaver(':memory:')`, 운영은 `PostgresSaver`.

### 6-5. Stream 중 예외 처리 없음

Node 에서 예외 → stream 이 끊김 → UI 가 "응답 없음". 각 node 에 try/except 로 error state 필드 세팅 + 다음 node 가 분기 처리.

### 6-6. Thread ID 설계 소홀

`thread_id = user_id` 하면 **같은 사용자의 두 대화가 섞임**. `thread_id = f'{user_id}:{session_id}'` 같이 세션까지 포함.

---

## 7. 운영 시 체크할 점

- [ ] State 스키마가 **TypedDict** 로 타입 체크되는가
- [ ] Node 가 **업데이트 필드만** 반환하는가 (전체 state X)
- [ ] **Checkpointer 가 프로덕션 DB** (Postgres) 로 구성됐는가
- [ ] `thread_id` 가 **세션 단위**로 유일한가 (user_id 단일 사용 금지)
- [ ] **Interrupt 지점**이 승인 필요 node 앞에 있는가
- [ ] 각 node 에 **try/except** + error state 필드가 있는가
- [ ] Conditional edge 가 **5개 초과** 면 서브그래프 분리 검토했는가
- [ ] **Trace (LangSmith / Langfuse)** 가 붙어 있는가
- [ ] Stream 사용 시 **각 chunk 타입**(updates/values/messages) 을 UI 가 구분 처리하는가
- [ ] **Time travel** 이 필요한 이유 (A/B · 디버깅) 가 명확한가 (대부분 불필요)

---

## 8. 연습문제 & 다음 챕터

### 확인 문제

1. StateGraph 대신 "그냥 함수 체인" 으로 충분한 상황 3가지를 드세요.
2. Conditional edge 와 edge 의 차이, router 함수 반환값의 의미를 설명하세요.
3. `interrupt_before` 를 썼을 때 state 가 어디 저장되고, resume 은 어떤 API 로 하나요?
4. Thread ID 를 `user_id` 단일 사용의 위험을 구체 시나리오로 드세요.

### 실습 과제

- §4 의 support graph 를 Colab 에서 실행. `thread_id='u1'` 로 두 번 연속 호출 → state 가 이어지는지 확인.
- §5-1 의 interrupt 패턴 추가. `invoke(None, cfg)` 로 resume 시 실제 돌아가는지.
- `app.get_state_history(cfg)` 로 체크포인트 리스트 보고, 하나 골라 time travel.

### 원전

- **LangGraph 공식 문서** — Persistence · Interrupt · Time Travel. 프로젝트 `_research/langgraph-persistence.md`
- **Anthropic — Building Effective Agents** — workflow vs agent 경계. 프로젝트 `_research/anthropic-building-effective-agents.md`

---

**다음 챕터** → [Ch 24. Agent 메모리](24-agent-memory.md) — thread / cross-thread · 에피소딕 · MemGPT 계층 :material-arrow-right:
