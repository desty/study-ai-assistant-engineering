# Ch 20. Agent 란 무엇인가

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part5/ch20_what_is_agent.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **LLM App** 과 **Agent** 의 명확한 경계
    - OpenAI 의 **Agent 3요소** — Model · Tool · Instruction
    - **자율성 스펙트럼** 4단계 (rule-based → LLM call → workflow → agent)
    - 단일 호출 vs 루프형 agent 를 **30줄씩** 비교 구현
    - "Agent 라고 부를 수 있는가" 과장 피하기 · 결정론으로 풀릴 문제에 agent 쓰지 않기

!!! quote "전제"
    Part 2 전체 (Ch 4~8, 특히 **tool calling**) + Part 3 RAG 기본 흐름. 단일 LLM 호출과 tool_use 루프를 한 번은 손으로 조립해본 상태.

---

## 1. 개념 — Agent 는 "LLM + 루프 + 도구"

뉴스·블로그·LinkedIn 에서 "**Agent**" 는 거의 모든 LLM 기반 앱을 의미합니다. 이 책에서는 훨씬 좁게 씁니다.

![App vs Agent](../assets/diagrams/ch20-app-vs-agent.svg#only-light)
![App vs Agent](../assets/diagrams/ch20-app-vs-agent-dark.svg#only-dark)

> **Agent** = LLM 이 **스스로 도구를 골라 호출**하고, **결과를 보고 다음 행동을 결정**하는 루프 구조.

반면 **LLM App** 은 "입력 → 단일 호출 → 출력" 선형 구조. 둘 다 LLM 을 쓰지만 **누가 제어 흐름을 쥐고 있는가** 가 다릅니다.

### OpenAI 의 Agent 3요소

OpenAI "A Practical Guide to Building Agents" 는 agent 를 3가지로 정의합니다:

1. **Model** — 의사결정하는 LLM
2. **Tool** — LLM 이 호출할 수 있는 외부 함수·API·DB
3. **Instruction** — system prompt + 정책 + 종료 조건

이 3가지가 **루프 안에서 돌아야** agent 입니다. 셋 중 하나라도 빠지면 그건 그냥 app.

---

## 2. 왜 필요한가 — 루프가 주는 것

**① 결정론으로 풀기 어려운 문제.** "고객 문의 받아서 상황에 따라 다른 DB 조회 → 필요하면 환불 진행 → 안 되면 사람에게 이관". 경로가 매번 다르면 if-else 로 쓰기 힘듭니다.

**② 도구를 조합해 써야 할 때.** 5개 tool 중 어느 걸 몇 번째 순서로 쓸지 **입력 따라 다르게**. 개발자가 미리 flow 를 그릴 수 없을 때.

**③ 탐색·시행착오.** "SQL 쿼리 써봤는데 에러 → 수정 후 재시도" 같은 자기교정 루프.

반대로 **agent 를 쓰지 말아야 할 경우**:
- 입력 형태가 정해져 있고 경로가 1~3개로 커버됨 → workflow
- 실패 비용이 매우 크다 (의료·결제) → 결정론적 + human gate
- 비용·지연이 엄격 (chat UX SLO 2초) → 단일 호출 + RAG

---

## 3. 어디에 쓰이는가 — 자율성 스펙트럼

![자율성 스펙트럼](../assets/diagrams/ch20-autonomy-levels.svg#only-light)
![자율성 스펙트럼](../assets/diagrams/ch20-autonomy-levels-dark.svg#only-dark)

자율성은 이진(0/1) 이 아니라 **스펙트럼**입니다.

| 단계 | 예시 | 특성 |
|---|---|---|
| ① Rule-based | 챗봇 FAQ 트리, 파이썬 함수 | 완전 결정론 · 디버깅 최강 |
| ② LLM Call | Ch 4 "요약해줘" · RAG | 프롬프트=로직 · 결과 확률적 |
| ③ Workflow | Ch 21 패턴 (chaining·routing) | LLM 여러 번이지만 **개발자가 경로 지정** |
| ④ **Agent** | ReAct · tool-use 루프 | **LLM 이 경로 결정** · 비결정적 |

**진짜 agent 는 ④**. 실무에서는 ②③ 조합이 압도적으로 많고 대부분 충분합니다.

!!! tip "의사결정 규칙"
    "이 문제를 ③ workflow 로 풀 수 있는가?" 를 먼저 물으세요. Yes 면 ③. 정말 No 일 때만 ④.

---

## 4. 최소 예제 — 같은 문제를 App / Agent 로

"주문번호 `O-1024` 의 환불 가능 여부를 알려줘" 라는 질문을 두 방식으로.

### 4-1. App 방식 — 단일 호출 + 프리로드 데이터

```python title="app_style.py" linenums="1" hl_lines="8"
import anthropic
client = anthropic.Anthropic()

ORDER = {'id': 'O-1024', 'days_since': 5, 'used': False}  # 미리 조회된 상태

resp = client.messages.create(
    model='claude-haiku-4-5-20251001',
    max_tokens=200,
    system='환불 정책: 7일 이내 미사용만 가능. 주문 상태를 보고 답하세요.',
    messages=[{
        'role': 'user',
        'content': f"주문 {ORDER}: 환불 가능한가?"
    }],
)
print(resp.content[0].text)
```

**특징**: 주문 데이터를 **먼저 코드로** 조회해서 프롬프트에 넣음. LLM 은 판단만. 1 호출 · 비용 예측 가능.

### 4-2. Agent 방식 — LLM 이 툴을 골라 호출

```python title="agent_style.py" linenums="1" hl_lines="13 34"
import anthropic
client = anthropic.Anthropic()

def get_order(order_id: str) -> dict:  # (1)!
    # 실제로는 DB 조회
    return {'id': order_id, 'days_since': 5, 'used': False}

TOOLS = [{
    'name': 'get_order',
    'description': '주문 id 로 주문 상세(일수·사용 여부) 조회',
    'input_schema': {
        'type': 'object',
        'properties': {'order_id': {'type': 'string'}},
        'required': ['order_id'],
    },
}]

messages = [{'role': 'user', 'content': '주문 O-1024 환불 가능한가?'}]

for step in range(5):  # (2)! 최대 5턴 제한
    resp = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=400,
        system='환불 정책: 7일 이내 미사용만 가능. 필요시 툴을 호출해 주문 정보를 얻어라.',
        tools=TOOLS,
        messages=messages,
    )
    messages.append({'role': 'assistant', 'content': resp.content})

    if resp.stop_reason == 'end_turn':
        print(resp.content[0].text); break

    # tool_use 블록 처리
    tool_results = []
    for block in resp.content:
        if block.type == 'tool_use':
            result = get_order(**block.input)  # (3)! 실제 실행은 우리 코드
            tool_results.append({
                'type': 'tool_result', 'tool_use_id': block.id,
                'content': str(result),
            })
    messages.append({'role': 'user', 'content': tool_results})
```

1. **Tool 함수** — LLM 은 호출할지 결정만. 실행은 우리 코드.
2. **루프 상한** — 무한 루프 방지. 5턴 안에 못 풀면 포기.
3. **tool_use → tool_result 교환** — Anthropic 포맷. OpenAI 는 `function_call`.

**특징**: 주문을 조회할지 말지를 **LLM 이 결정**. 1~3 호출 (데이터에 따라). 비용·지연 비결정적.

### 두 방식의 차이

| 축 | App | Agent |
|---|---|---|
| 호출 수 | 1 (고정) | 1~N (가변) |
| 제어 | 코드 | LLM |
| 디버깅 | 쉬움 | trace 필수 |
| 추가 질문 | 새 flow 코딩 | 툴만 늘리면 자연스러운 경우 있음 |

---

## 5. 실전 튜토리얼 — Agent 기본 루프 5가지 요소

production 급 agent 루프는 단순 `for` 가 아니라 다음 5가지가 필요합니다:

```python title="agent_loop_skeleton.py" linenums="1" hl_lines="18 26"
def run_agent(user_msg, tools, tool_impls, max_steps=10):
    messages = [{'role': 'user', 'content': user_msg}]
    for step in range(max_steps):
        resp = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=600,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )
        messages.append({'role': 'assistant', 'content': resp.content})

        # 종료 조건
        if resp.stop_reason == 'end_turn':
            return extract_text(resp)

        # tool 실행
        tool_results = []
        for block in resp.content:
            if block.type != 'tool_use':
                continue
            try:
                result = tool_impls[block.name](**block.input)
            except Exception as e:
                result = f'ERROR: {e}'  # (1)! 에러도 컨텍스트로 돌려줌
            tool_results.append({
                'type': 'tool_result',
                'tool_use_id': block.id,
                'content': str(result)[:2000],  # (2)! 길이 제한
            })
        messages.append({'role': 'user', 'content': tool_results})

    return 'MAX_STEPS_EXCEEDED'  # (3)! 사용자에게 제어 반환
```

1. **에러 자체를 tool_result 로** — LLM 이 보고 재시도할 수 있게. `raise` 하지 말 것.
2. **길이 제한** — 툴 결과가 거대하면 컨텍스트 터짐. 2KB 내외로 자르거나 요약.
3. **max_steps 초과 시 사용자에게 제어 반환** — 무한 루프·비용 폭주 방지. "진행 안 됨 — 도와주세요" 로 fallback.

5가지 핵심:
1. **종료 조건** (`end_turn` · max_steps · 사용자 개입)
2. **에러 처리** (ERROR 도 메시지로)
3. **툴 결과 크기 제한**
4. **Trace 저장** (Part 4 Ch 19 · LangSmith / Langfuse)
5. **사람에게 제어 반환** — 실패·불확실 시

---

## 6. 자주 깨지는 포인트

### 6-1. 단일 호출 app 을 "Agent" 로 부르기

"Claude 로 분류하는 기능 만들었습니다 — agent 입니다" 는 과장. 루프 없으면 agent 아님. 용어를 정확히 써야 **팀에서 설계 논의**가 성립합니다.

### 6-2. 결정론으로 풀리는 문제에 agent

"이메일 감지 → 분류 → DB 저장" 은 workflow. 이걸 agent 로 만들면:
- 비용 3~10×
- 지연 3~10×
- 디버깅 지옥
- 가끔 엉뚱한 툴 호출

**결정론으로 안 풀리는 이유가 명확해야** agent 로 갑니다.

### 6-3. max_steps 없음

무한 루프 = 무한 비용. `max_steps=10` 같은 하드 상한 필수.

### 6-4. 에러 `raise` 로 터뜨리기

Tool 실행 에러를 raise 하면 루프가 끊김. LLM 은 에러를 **보고 수정**할 수 있어야 하므로 에러 메시지를 `tool_result` 로 돌려줘야.

### 6-5. 비용·지연 무관심

Agent 는 **N=1~20 호출**. 평균/최악 지연·비용을 측정하지 않으면 프로덕션에서 터짐. SLO 있는 제품이면 Part 6 로 선행.

---

## 7. 운영 시 체크할 점

- [ ] 문제를 agent 로 풀기로 한 **근거**가 문서화됐는가 (결정론으로 왜 안 되는지)
- [ ] 루프에 **max_steps 상한**이 있는가
- [ ] **Tool 실행 에러가 tool_result 로** 돌려지는가 (raise 금지)
- [ ] **툴 결과 크기 제한**(truncate/summarize) 이 걸려 있는가
- [ ] 매 호출이 **Trace 로 저장**되는가 (LangSmith/Langfuse/자체)
- [ ] **종료 조건** 이 명시적인가 (`end_turn` + max_steps + 사용자 개입)
- [ ] 평균/최악 **비용·지연** 을 evalset 에서 측정하는가
- [ ] 실패 시 **사람에게 제어 반환** 경로가 있는가 (fallback UX)

---

## 8. 연습문제 & 다음 챕터

### 확인 문제

1. "LLM App" 과 "Agent" 를 한 문장씩으로 구분하세요. 핵심 차이 단어는?
2. OpenAI 의 Agent 3요소를 당신의 프로토타입에 매핑하세요 (Model 은 무엇, Tool 은 무엇, Instruction 은 무엇).
3. 자율성 스펙트럼 4단계에서 당신 제품은 어느 단계인가요? 왜?
4. "Agent 로 풀어야 할" 문제 1개와 "Workflow 로 충분한" 문제 1개를 구체적으로 드세요.

### 실습 과제

- §4-1 의 app 스타일 코드를 실행해 기본 동작 확인.
- §4-2 agent 스타일로 바꾸면서, LLM 이 실제로 `get_order` 를 호출하는지 trace.
- 주문 id 를 **존재하지 않는** 값으로 바꿨을 때 agent 가 어떻게 반응하는지 관찰 (에러 tool_result 처리).

### 원전

- **Anthropic — Building Effective Agents** (Schluntz & Zhang 2024) — "Agent = LLM in a loop with tools" 정의. 프로젝트 `_research/anthropic-building-effective-agents.md`
- **OpenAI — A Practical Guide to Building Agents** — 3요소 (Model · Tool · Instruction) · 단일 vs 멀티. 프로젝트 `_research/openai-practical-guide-to-agents.md`

---

**다음 챕터** → [Ch 21. Agent 패턴 7가지](21-agent-patterns.md) — Anthropic 5 + OpenAI 2 를 어휘로 :material-arrow-right:
