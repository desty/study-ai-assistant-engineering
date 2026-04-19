# Ch 24. Agent 메모리

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part5/ch24_agent_memory.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **메모리 4계층** — Sensory · Working · Episodic · Semantic
    - LangGraph 의 **Thread** (세션 내) 와 **Store** (세션 간) 2계층 매핑
    - **사용자 선호 자동 추출** → Store 저장 패턴
    - **MemGPT 계층적 메모리** 개념 — 컨텍스트 초과 시 교환
    - 메모리 **오염** · PII 축적 · 잘못된 자동 요약 — 3대 위험

!!! quote "전제"
    [Ch 23](23-langgraph.md) — StateGraph · checkpointer · thread_id. 이번 챕터는 그 thread 상태 **너머**로.

---

## 1. 개념 — 메모리는 한 덩어리가 아니다

Agent 에 "기억을 주자" 는 말은 너무 모호합니다. 사람의 기억 구조를 빌려와서 **4계층**으로 분리하면 설계가 명확해집니다.

![메모리 4계층](../assets/diagrams/ch24-memory-hierarchy.svg#only-light)
![메모리 4계층](../assets/diagrams/ch24-memory-hierarchy-dark.svg#only-dark)

| 계층 | 보존 | 크기 | 예시 | LLM 구현 |
|---|---|---|---|---|
| ① Sensory | ~초 | 원시 입력 | 방금 발화 · 툴 결과 | 컨텍스트 직전 토큰 |
| ② Working | 세션 | 수 KB~ | 현재 대화 · scratchpad | **LangGraph thread state** |
| ③ Episodic | 수 주~수 개월 | 이벤트당 | 과거 대화 · 특정 사건 | **Store · vectorstore** |
| ④ Semantic | 영구 | 지식·선호 | "사용자 한국어 선호" · 도메인 규칙 | **Store key-value · 프로필** |

핵심은 **각 계층의 저장·검색 전략이 다르다**는 것. 같은 DB 에 다 넣으면 검색도 삭제 정책도 엉킴.

---

## 2. 왜 필요한가

**① 컨텍스트 창 한계.** 대화가 길어지면 전부 못 담음. Working 을 **요약 + Episodic 으로 아카이빙** 해야.

**② 사용자 맞춤 경험.** "지난번에 말했잖아" 를 반복하지 않는 UX. Semantic 메모리로 선호 저장.

**③ 학습 · 개선.** 자주 실패하는 패턴을 Episodic 에 남겨 **failure 분석**(Ch 19) 소스로.

**④ 비용 · 지연.** 매 턴마다 전체 history 를 프롬프트에 넣으면 토큰 × N. 요약 + 관련 조회로 최소화.

---

## 3. 어디에 쓰이는가 — LangGraph 2계층

![Thread vs Store](../assets/diagrams/ch24-thread-vs-store.svg#only-light)
![Thread vs Store](../assets/diagrams/ch24-thread-vs-store-dark.svg#only-dark)

LangGraph 는 4계층을 **Thread** 와 **Store** 2가지 API 로 추상화합니다.

### 3-1. Thread — Working memory

- Ch 23 의 `thread_id` 로 구분
- 세션 시작 ~ 종료까지의 state
- Checkpointer 에 저장 (interrupt/resume 지원)
- 세션 끝나면 보통 **요약 후 Store 로 이관**

### 3-2. Store — Episodic + Semantic

- `namespace` (예: `('user', '42')`) 로 구분
- 여러 세션·여러 thread 가 공유
- Key-value (semantic) 또는 vectorstore (episodic search) 둘 다 가능
- LangGraph `BaseStore` 인터페이스: `put` · `get` · `search` · `delete`

### 3-3. 언제 무엇을 쓰나

| 정보 | 계층 | 저장처 |
|---|---|---|
| 현재 대화의 이전 턴 | Working | Thread state (자동) |
| "한국어로 답하는 걸 선호" | Semantic | Store `preferences` |
| "2026-04-10 환불 문의" | Episodic | Store `past_events` |
| 하루 지난 잡담 | → 버림 | Store 비저장 |

---

## 4. 최소 예제 — Store 에 사용자 선호 저장·조회

```bash
pip install langgraph
```

```python title="store_basic.py" linenums="1" hl_lines="9 20"
from langgraph.store.memory import InMemoryStore  # 실전은 PostgresStore

store = InMemoryStore()  # (1)!
ns = ('user', '42')

# 저장
store.put(ns, 'profile', {'lang': 'ko', 'tier': 'premium'})
store.put(ns, 'preferences', {'tone': 'formal', 'reply_length': 'short'})

# 조회
profile = store.get(ns, 'profile').value
print(profile)  # {'lang': 'ko', 'tier': 'premium'}

# 검색 (vectorstore-backed store 면 의미 검색도 가능)
results = store.search(ns)  # (2)! 해당 namespace 전부
for item in results:
    print(item.key, item.value)
```

1. **InMemoryStore** 는 테스트 용. 운영은 `PostgresStore` · `RedisStore`.
2. **namespace 설계** — `('user', uid)` 처럼 계층. 같은 프리픽스로 batch 조회 가능.

### Graph 안에서 쓰기

```python title="graph_with_store.py" linenums="1"
from langgraph.graph import StateGraph, START, END

def greet(state, config, *, store):  # (1)!
    uid = config['configurable']['user_id']
    profile = store.get(('user', uid), 'profile')
    lang = (profile.value if profile else {}).get('lang', 'en')
    greeting = '안녕하세요' if lang == 'ko' else 'Hello'
    return {'response': f'{greeting}, {uid}'}

g = StateGraph(State)
g.add_node('greet', greet)
g.add_edge(START, 'greet'); g.add_edge('greet', END)

app = g.compile(checkpointer=checkpointer, store=store)  # (2)!
app.invoke({}, config={'configurable': {'thread_id':'t1','user_id':'42'}})
```

1. **Node 시그니처에 `store` 주입** — LangGraph 가 자동 전달.
2. **compile 시 `store=` 전달** — checkpointer 와 별개.

---

## 5. 실전 튜토리얼 — 사용자 선호 자동 추출

대화 중 "저는 한국어로 답해주세요" 같은 발언을 **자동 감지 → Store 업데이트** 하는 패턴.

```python title="extract_preferences.py" linenums="1" hl_lines="10 21"
EXTRACT_PROMPT = """다음 대화에서 사용자의 장기 선호·프로필 정보만 JSON 으로 추출.
변경할 키만 포함. 없으면 빈 dict. 추출 대상: lang, tone, reply_length, domain_of_interest.
대화:
{conversation}
"""

def extract_preferences(state, config, *, store):
    uid = config['configurable']['user_id']
    convo = '\n'.join(m.content for m in state['messages'][-6:])  # 최근만
    import json
    r = llm.invoke(EXTRACT_PROMPT.format(conversation=convo))
    try:
        updates = json.loads(r.content)
    except Exception:
        return {}
    if not updates:
        return {}

    # 기존 profile 과 병합
    existing = store.get(('user', uid), 'preferences')
    merged = {**(existing.value if existing else {}), **updates}
    store.put(('user', uid), 'preferences', merged)  # (1)!
    return {'preferences_updated': list(updates.keys())}
```

1. **Merge 후 저장** — 덮어쓰기 X, 기존 필드 보존.

### 다음 대화에서 자동 로드

```python title="load_preferences.py" linenums="1"
def load_preferences(state, config, *, store):
    uid = config['configurable']['user_id']
    prefs = store.get(('user', uid), 'preferences')
    if prefs:
        # system prompt 에 프리펜드
        ctx = f'[사용자 선호] {prefs.value}'
        return {'messages': [{'role': 'system', 'content': ctx}]}
    return {}
```

**flow**: `load_preferences → classify → ... → extract_preferences → END`

### MemGPT 식 계층 (개념)

대화 history 가 컨텍스트 초과:
1. 오래된 턴을 **요약**해 Store 에 push
2. 현재 working 에서 제거
3. 필요 시 `retrieve_old_context` 툴로 다시 불러옴

LangGraph 순정은 아니고 **직접 구현**. 연구 참조 CS329A Lec 14.

---

## 6. 자주 깨지는 포인트

### 6-1. 전부 Working 에 몰아넣기

대화 1,000턴을 thread state 에 쌓음 → 컨텍스트 overflow → 비용·지연 폭발. **요약 + Store 이관** 루틴이 필수.

### 6-2. Store 에 개인정보 무자각 축적

"이메일 · 주민번호 · 카드번호" 가 자동 추출로 Store 에 저장되면 GDPR·PIPA 위반. Extract 프롬프트에 **"민감정보 제외"** 명시 + 저장 전 PII masking.

### 6-3. 잘못된 자동 요약이 장기기억에 박힘

한 번 틀린 요약이 Store 에 저장 → 이후 모든 세션에서 **잘못된 전제**로 답변. 해결:
- 요약을 **사용자에게 확인** 받은 뒤 저장 (human-in-loop)
- Store 에 `confidence` 필드 · 낮은 건 주기 재검증
- 편집·삭제 API 사용자에게 노출 ("내 기억 관리")

### 6-4. Namespace 충돌

`('user', uid)` 만 쓰다가 다른 agent 도 같은 키 씀 → 덮어쓰기. `('user', uid, 'support_agent')` 처럼 **앱·기능까지 계층**.

### 6-5. Vectorstore vs key-value 혼동

"과거 사건 중 환불 관련" 같은 **의미 검색** 은 vectorstore. "현재 선호 언어" 는 key-value. 둘 다 필요하면 store 2개.

### 6-6. TTL · 삭제 정책 부재

6개월 된 에피소드 메모리가 계속 쌓임 → DB 팽창 · 검색 노이즈. Store 에 `expires_at` + 배치 삭제 job.

---

## 7. 운영 시 체크할 점

- [ ] 메모리 **4계층 중 어떤 것을 쓰는지** 설계 문서에 명시했는가
- [ ] Working (thread) 와 Store (namespace) **경계**가 분리됐는가
- [ ] PII **추출 방지 프롬프트** + **저장 전 masking** 이 있는가
- [ ] Store 저장 전 **사용자 확인** 루틴이 있는가 (특히 요약 기반)
- [ ] Namespace 가 **앱·기능 레벨까지** 계층화됐는가 (충돌 방지)
- [ ] **삭제·편집 API** 를 사용자에게 노출하는가 ("내 기억 관리")
- [ ] Episodic 에 **TTL · 배치 삭제** 있는가
- [ ] Vectorstore / key-value 중 **적합한 쪽**을 골랐는가
- [ ] 세션 종료 시 **Thread → Store 이관** 루틴이 있는가
- [ ] **비용**: 세션당 Store 호출 수 · 토큰 영향 측정

---

## 8. 연습문제 & 다음 챕터

### 확인 문제

1. 메모리 4계층 각각에 당신 프로토타입의 정보 1개씩을 분류하세요.
2. Thread 와 Store 의 차이를 **저장처·수명·범위** 3축으로 설명하세요.
3. 자동 요약이 Store 에 들어간 뒤 틀렸다는 걸 발견. 어떻게 대응할까요 (사용자 · 시스템 · 다음 릴리스 3단계)?
4. Namespace 설계에 `user_id` 만 넣는 것이 왜 위험한가요?

### 실습 과제

- §4 의 Graph 에 `extract_preferences` node 추가. "한국어로 답해줘" 발화 후 Store 에 저장 확인.
- 다음 세션(새 thread) 을 열어 `load_preferences` 가 자동으로 system prompt 에 주입하는지 확인.
- `store.delete` 로 특정 선호 삭제 → 그 뒤 대화에 영향 없는지.

### 원전

- **Stanford CS329A Lec 14** — Augmenting Agents with Memory (Cartridges · MemGPT · CacheBlend). 프로젝트 `_research/stanford-cs329a.md`
- **LangGraph 공식 문서** — Store · Long-term memory. 프로젝트 `_research/langgraph-persistence.md`

---

**다음 챕터** → [Ch 25. 멀티 에이전트와 역할 분리](25-multi-agent.md) — Planner/Executor · 언제 쪼개야 하나 :material-arrow-right:
