# Ch 22. Tool Use 실전 — ACI 설계

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part5/ch22_tool_use.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **ACI** (Agent-Computer Interface) — LLM 이 툴을 이해하는 5가지 요소
    - **Data / Action / Orchestration** 3 범주와 **위험도** 매핑
    - **Human-in-loop 승인 큐** — 고위험 Action 툴의 실행 게이트
    - 툴 이름 겹침 · 설명 모호 · 에러 raise — 3대 파라미터 오류 원인
    - 왜 "많은 툴 = 좋은 agent" 가 아닌가

!!! quote "전제"
    [Ch 8 (Tool Calling)](../part2/08-tool-calling.md) — 기본 tool_use 루프 · 3범주 소개. [Ch 20·21](20-what-is-agent.md) — agent 와 패턴. 여기서는 **production 품질** 로 끌어올린다.

---

## 1. 개념 — ACI 는 API 와 다르다

API 는 프로그래머가 읽고 씁니다. **ACI (Agent-Computer Interface)** 는 **LLM 이 읽고** 결정합니다. 같은 함수라도 ACI 로 쓰면 설계가 달라야 합니다.

![ACI Anatomy](../assets/diagrams/ch22-aci-anatomy.svg#only-light)
![ACI Anatomy](../assets/diagrams/ch22-aci-anatomy-dark.svg#only-dark)

LLM 은 툴을 **5개 필드**로만 이해합니다:

| # | 필드 | 역할 | 흔한 실수 |
|---|---|---|---|
| ① | **Name** | 툴 식별자 (snake_case) | `get_data` 같은 모호함 · 다른 툴과 겹침 |
| ② | **Description** | 언제·왜 쓰는지 | "주문 조회" 1줄 — 선택 기준이 없음 |
| ③ | **Input Schema** | 파라미터 JSON Schema | `type` 만 쓰고 `pattern`·`enum` 생략 |
| ④ | **Return Shape** | 결과 형태 | 거대한 dict 통째 반환 → 토큰 낭비 |
| ⑤ | **Error Contract** | 실패 시 반환 | `raise` 해서 루프 중단 |

이 5개가 탄탄해야 LLM 이 **올바른 툴을 올바른 파라미터로** 부릅니다.

---

## 2. 왜 필요한가 — 3대 실패 모드

Agent 가 멍청해 보이는 대부분의 경우는 **모델 문제가 아니라 ACI 문제**입니다.

**① 툴 선택 오류.** "이 툴이 필요한지 저 툴이 필요한지" 모름.

→ 원인: description 이 모호하거나 두 툴 이름이 비슷함 (`search_orders`, `find_order`)

**② 파라미터 오류.** 툴은 맞게 골랐는데 인자를 잘못 줌.

→ 원인: input_schema 에 `pattern` · `enum` · `example` 부족. LLM 이 추측함

**③ 에러 루프 깨짐.** 툴 실행 중 에러 → `raise` → 전체 agent 중단.

→ 원인: error contract 없음. 에러를 `tool_result` 로 돌려주지 않음

**해결**: 이 챕터의 5요소 원칙을 지키면 이 3개가 드라마틱하게 줄어듭니다.

---

## 3. 툴 3범주 — Data · Action · Orchestration

Ch 8 에서 간단히 소개. 여기선 **위험도·승인·모니터링** 관점에서 재구성.

| 범주 | 예시 | 부작용 | 자동 실행? | 실패 시 |
|---|---|---|---|---|
| **Data** | get_order · search_docs · read_file | 읽기만 | ✅ Yes | 다시 시도 · 대안 툴 |
| **Action** | send_email · refund · delete_record · post_slack | **외부 상태 변경** | ❌ No — 승인 필요 | 롤백 or 사람에게 |
| **Orchestration** | invoke_agent · start_workflow · schedule_task | 다른 agent/flow 실행 | 상황에 따라 | trace · 상위 에이전트에 전달 |

**핵심 구분**: **되돌릴 수 있는가.** 되돌릴 수 없는 건 기본적으로 승인 대상.

---

## 4. 최소 예제 — 잘 설계된 툴 하나

```python title="well_designed_tool.py" linenums="1" hl_lines="6 15 28"
TOOL_GET_ORDER = {
    'name': 'get_order',  # (1)!
    'description': (
        '주문 id 로 주문 상세 정보(상태 · 일수 · 사용 여부)를 조회한다. '
        '환불 가능 여부 판단, 배송 상태 확인, 결제 정보 조회 시 사용. '
        '예: 사용자가 "주문 O-1024 환불되나?" 라고 물을 때.'
    ),
    'input_schema': {
        'type': 'object',
        'properties': {
            'order_id': {
                'type': 'string',
                'pattern': '^O-[0-9]{4}$',  # (2)! 형식 강제
                'description': '주문 식별자. O- 접두사 + 4자리 숫자 (예: O-1024)',
            }
        },
        'required': ['order_id'],
    },
}

def get_order(order_id: str) -> dict:
    try:
        row = db.query('SELECT ... FROM orders WHERE id = ?', (order_id,))
        if not row:
            return {'error': f'주문 {order_id} 없음'}  # (3)! dict 로 반환
        return {  # (4)! 필요한 필드만
            'id': row['id'],
            'days_since': (today() - row['created_at']).days,
            'used': row['fulfilled'],
        }
    except Exception as e:
        return {'error': f'DB 오류: {type(e).__name__}: {e}'}  # (5)! raise 금지
```

1. **Name** — 동사_명사. `get_order_detail_by_id` 는 과함. `get_order` 충분.
2. **Pattern** — "O-" 빠뜨림 방지. LLM 이 `1024` 나 `order-1024` 를 주는 걸 막음.
3. **에러도 정상 반환** — LLM 이 "없네, 다른 id 로 시도" 가능.
4. **Return 정제** — 100필드 dict 던지지 말고 3~5개로.
5. **Exception 도 문자열화** — agent 루프 유지.

---

## 5. 실전 튜토리얼 — 고위험 Action 툴 + 승인 큐

![Approval Flow](../assets/diagrams/ch22-approval-flow.svg#only-light)
![Approval Flow](../assets/diagrams/ch22-approval-flow-dark.svg#only-dark)

환불 · 삭제 · 전송 같은 Action 툴은 **LLM 결정만으로 실행 금지**. 승인 게이트가 있어야.

### 5-1. 패턴 — "요청 → 큐 → 사람 → 실행"

```python title="approval_queue.py" linenums="1"
import uuid

PENDING = {}  # 실전은 Redis / DB

def request_refund(order_id: str, amount: int, reason: str) -> dict:
    """Action 툴 — 승인 필요. 즉시 실행 X."""
    req_id = str(uuid.uuid4())[:8]
    PENDING[req_id] = {
        'order_id': order_id,
        'amount': amount,
        'reason': reason,
        'status': 'pending',
    }
    # LLM 이 볼 응답: "승인 대기 중" 이라는 명확한 시그널
    return {
        'status': 'pending_approval',
        'request_id': req_id,
        'message': f'환불 요청 {req_id} 생성. 운영자 승인 대기 중.',
    }

def admin_approve(req_id: str, approved: bool):
    """운영자 UI 에서 호출"""
    r = PENDING[req_id]
    if approved:
        stripe_refund(r['order_id'], r['amount'])  # 실제 실행
        r['status'] = 'approved'
    else:
        r['status'] = 'rejected'
```

### 5-2. LLM 이 이 결과를 읽으면

Agent 는 tool_result 로 `status: pending_approval` 을 보고:

- 사용자에게 "운영자 승인을 요청했습니다. 곧 처리됩니다." 응답
- 또는 LangGraph `interrupt()` 로 **agent 자체를 일시 중지** (Ch 23)

**절대 하지 말 것**: 승인 대기 중에 LLM 이 "그럼 제가 다른 방법으로…" 하면서 다른 툴로 우회. 이걸 막으려면 system prompt 에 **명시**:

> "승인 대기(pending_approval) 응답이 오면, 반드시 사용자에게 그 사실만 전달하고 대기하세요. 다른 툴을 시도하지 마세요."

### 5-3. 툴 메타데이터에 risk 박기

```python title="tool_registry.py" linenums="1"
TOOLS = [
    {'schema': TOOL_GET_ORDER,     'impl': get_order,     'risk': 'low'},   # Data
    {'schema': TOOL_SEARCH_DOCS,   'impl': search_docs,   'risk': 'low'},   # Data
    {'schema': TOOL_REQUEST_REFUND,'impl': request_refund,'risk': 'high'},  # Action
    {'schema': TOOL_SEND_EMAIL,    'impl': send_email,    'risk': 'high'},  # Action
]

def execute_tool(name, args):
    tool = next(t for t in TOOLS if t['schema']['name'] == name)
    if tool['risk'] == 'high':
        log_audit(name, args)  # 감사 로그 (Part 6)
    return tool['impl'](**args)
```

`risk='high'` 면 **별도 허용 목록** 을 system prompt 에 노출 여부까지 제어 가능.

---

## 6. 자주 깨지는 포인트

### 6-1. 툴 이름 겹침

`search_customers` 와 `find_customer` 가 같이 있으면 LLM 이 어느 걸 쓸지 **일관되게** 고르지 못함. 하나로 통일하거나 description 에 **"이것 대신 다른 것을 쓸 조건"** 을 명시.

### 6-2. "많은 툴 = 좋은 agent" 착각

툴 20개 이상이면 정확도가 **떨어지는** 경우가 많음 (Anthropic 보고). 이유: 프롬프트 길이 증가 + 유사 툴 혼동. **10개 이하** 유지. 많이 필요하면 routing (Ch 21) 으로 서브셋만 노출.

### 6-3. Description 에 "무엇을" 만 · "언제" 없음

나쁨: `"주문을 조회한다"`
좋음: `"주문 상세 조회. 환불 가능 여부·배송 상태 확인 시 필수."`

**언제 쓸지**가 결정적. LLM 은 이걸로 고름.

### 6-4. Schema 에 example 없음

```json
"order_id": {"type": "string"}          // 약함
"order_id": {"type": "string",
             "pattern": "^O-[0-9]{4}$",
             "description": "예: O-1024"}  // 강함
```

### 6-5. Error 를 raise

`raise ValueError(...)` → agent 루프 중단 → "오류가 발생했습니다" 로 끝. LLM 에게 **수정 기회** 를 줘야 함: `return {"error": "..."}`.

### 6-6. 거대 return

`get_order` 가 주문 + 고객 + 상품 + 로그 100KB 를 전부 반환 → 컨텍스트 한 번에 폭발. **필요한 필드만** + 크기 제한 (2KB 내외).

---

## 7. 운영 시 체크할 점

- [ ] 각 툴이 **5요소 (Name · Description · Schema · Return · Error)** 를 명시했는가
- [ ] Description 에 **"언제 쓰는지"** 가 1~2문장 이상 있는가
- [ ] Input schema 에 `pattern` · `enum` · `example` 이 적절히 있는가
- [ ] **툴 개수가 10개 이하** 인가 (routing 으로 서브셋 노출 포함)
- [ ] 이름 · description 이 **다른 툴과 겹치지 않는가** (PR 시 diff 리뷰)
- [ ] Action 툴에 **risk 메타데이터 + 승인 큐** 가 있는가
- [ ] 모든 툴이 **에러를 dict/str 로 반환** (raise 없음) 하는가
- [ ] Return 크기가 **2KB 내외** 로 제한되는가
- [ ] 툴 호출·실패가 **trace 로 기록** 되는가 (Part 4 Ch 19)
- [ ] 고위험 툴은 **감사 로그(audit log)** 도 쓰는가

---

## 8. 연습문제 & 다음 챕터

### 확인 문제

1. ACI 와 API 의 차이를 한 줄로 설명하고, ACI 에 필요한 5요소를 드세요.
2. 당신의 도메인에서 Data / Action / Orchestration 툴을 각 1개씩 나열하세요.
3. 툴 20개가 10개보다 왜 나쁠 수 있는지, 정확도·토큰·디버깅 관점에서 각 1줄씩.
4. "에러를 raise 하지 말고 tool_result 로 돌려줘라" 의 이유를 agent loop 동작으로 설명하세요.

### 실습 과제

- 당신 프로토타입의 툴 1개를 골라 **5요소 체크리스트** 에 대입. 부족한 필드 보강.
- `risk='high'` 툴 하나를 승인 큐 패턴으로 감쌈. `status: pending_approval` 반환이 LLM 에 어떻게 읽히는지 trace.

### 원전

- **Anthropic — Building Effective Agents** — ACI · tool design 섹션. 프로젝트 `_research/anthropic-building-effective-agents.md`
- **OpenAI — A Practical Guide to Building Agents** — Tool 3범주 (Data / Action / Orchestration). 프로젝트 `_research/openai-practical-guide-to-agents.md`

---

**다음 챕터** → [Ch 23. LangGraph — 상태 그래프](23-langgraph.md) — 루프 대신 **state graph** 로 · checkpointer · interrupt :material-arrow-right:
