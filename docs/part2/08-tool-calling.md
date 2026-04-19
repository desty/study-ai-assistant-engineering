# Ch 8. Tool Calling 기초

<a class="colab-badge" href="https://colab.research.google.com/" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **Tool Calling (Function Calling)** — LLM이 우리 코드의 함수를 부르게 하는 방식
    - **툴 3종류** (Data / Action / Orchestration) — OpenAI Practical Guide 분류
    - LLM과 툴 사이의 **tool_use ↔ tool_result 루프** 구조
    - **Pydantic 으로 파라미터 검증** + **승인 기반 실행** (부작용 있는 툴)
    - 무한 루프·잘못된 파라미터·부작용 처리 — 실전에서 망하는 포인트들
    - Part 5 Agent 로 가는 다리

!!! quote "전제"
    [Ch 4~7](04-api-start.md) 까지. 특히 **Ch 6 구조화 출력** — Tool 정의가 결국 JSON Schema 와 같음.

---

## 1. 개념 — LLM 에게 **손** 을 달아주기

지금까지 LLM은 **읽고 쓰기** 만 했습니다. 외부 세계(DB · API · 파일)를 조회하거나 작업을 수행하지 못했어요.

**Tool Calling** 은 LLM 에게 **손** 을 달아주는 방식:

1. 우리가 **함수 목록을 선언** (이름 · 설명 · 파라미터 스키마)
2. LLM이 사용자 요청을 읽고 **"이 툴이 필요하다"** 고 판단하면 `tool_use` 응답 반환
3. 우리 코드가 해당 함수를 **실행**
4. 결과를 `tool_result` 로 **LLM에 다시 전달**
5. LLM이 결과를 보고 이어서 추론 → 최종 답변

![Tool Calling 루프](../assets/diagrams/ch8-tool-use-loop.svg#only-light)
![Tool Calling 루프](../assets/diagrams/ch8-tool-use-loop-dark.svg#only-dark)

중요한 건 **"LLM이 직접 함수를 실행하는 게 아니다"** 라는 것. LLM 은 **"어떤 함수를 어떤 인수로 부를지만 결정"** 하고, 실행은 **언제나 우리 코드**. 이 경계가 안전성의 출발점.

---

## 2. 왜 필요한가

- **최신성** — 학습 시점 이후의 정보 (날씨·주가·재고)
- **프라이빗 데이터** — 회사 DB · 고객 주문 내역
- **액션** — 이메일 발송 · 결제 · 티켓 생성 · 예약
- **계산 정확성** — 금액·환율 계산을 모델 추론에 맡기면 틀릴 수 있음 → 계산기 툴로

!!! note "Part 5 Agent 와의 관계"
    Tool Calling 은 Agent 의 **근본 구성요소**. 이 챕터는 "한두 번의 툴 호출" 수준이고, Part 5 에서 **루프가 길어지고 · 메모리가 붙고 · 가드레일이 계층화** 됩니다.

---

## 3. 툴의 3가지 종류

![툴 3종류](../assets/diagrams/ch8-tool-three-kinds.svg#only-light)
![툴 3종류](../assets/diagrams/ch8-tool-three-kinds-dark.svg#only-dark)

OpenAI Practical Guide 의 분류([_research/openai-practical-guide-to-agents.md](#)):

| 타입 | 예시 | 안전성 관점 |
|---|---|---|
| **Data** (조회) | DB 쿼리, 문서 검색, 웹 검색, 파일 읽기 | **읽기 전용** — 상대적으로 안전 |
| **Action** (변경) | 이메일 전송, 결제, 주문 취소, 티켓 발행 | **부작용 있음** — 승인·감사 필수 |
| **Orchestration** (조합) | 다른 에이전트 호출, 서브-툴 묶음 | 복잡성 ↑, Part 5 영역 |

**초보 → 엔터프라이즈** 경로에서 중요한 구분:

- PoC 에서는 Data 중심 (안전)
- 프로덕션으로 가면 Action 이 들어옴 → **승인 큐 + 감사 로그 필수** (Part 6 Ch 29)

---

## 4. 최소 예제 — 계산기 툴

```python title="calc_tool.py" linenums="1" hl_lines="6 7 8 9 10 11 12 13 14 15 16 17 18"
from anthropic import Anthropic

client = Anthropic()

tools = [
    {
        "name": "calculate",
        "description": "간단한 산술 계산을 수행. 복잡한 금액·환율·수량 계산에 사용.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "파이썬이 평가 가능한 산술식. 예: '1000 * 1.08 / 12'"
                },
            },
            "required": ["expression"],
        },
    }
]

def run_calculate(expression: str) -> str:  # (1)!
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"error: {e}"

# 1) 첫 호출
messages = [{"role": "user", "content": "월 1,000달러 저금을 연 5%로 3년 하면 이자만 얼마?"}]
r = client.messages.create(
    model="claude-haiku-4-5", max_tokens=1024,
    tools=tools, messages=messages,
)

# 2) tool_use 응답을 받았나?
if r.stop_reason == "tool_use":
    for block in r.content:
        if block.type == "tool_use":
            print(f"LLM 요청 툴: {block.name}, 인수: {block.input}")
            tool_result = run_calculate(**block.input)  # (2)!

            # 3) tool_result 포함해 다시 호출
            messages.append({"role": "assistant", "content": r.content})
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": tool_result,
                }],
            })
            r2 = client.messages.create(
                model="claude-haiku-4-5", max_tokens=1024,
                tools=tools, messages=messages,
            )
            print("최종:", r2.content[0].text)
```

1. **실행은 우리 코드**. LLM 은 표현식만 건네줄 뿐.
2. `eval` 의 위험은 §6 실수 1에서. 실전은 `asteval` 같은 안전 평가 라이브러리.

---

## 5. 실전 튜토리얼

### 5.1 여러 툴 · Pydantic 검증

LLM이 잘못된 파라미터를 넘길 때를 대비해 **툴 입력도 Pydantic 으로 검증**합니다.

```python title="multi_tools.py" linenums="1"
from pydantic import BaseModel, Field, ValidationError

class WeatherArgs(BaseModel):
    city: str = Field(..., min_length=1)
    units: str = Field(default="metric", pattern=r"^(metric|imperial)$")

class OrderLookupArgs(BaseModel):
    order_id: str = Field(..., pattern=r"^[A-Z]-\d+$")

TOOL_SPECS = {
    "get_weather": {
        "schema": WeatherArgs,
        "tool": {
            "name": "get_weather",
            "description": "도시의 현재 날씨 조회",
            "input_schema": WeatherArgs.model_json_schema(),  # (1)!
        },
        "handler": lambda args: f"{args.city} 날씨 15도 맑음",
    },
    "lookup_order": {
        "schema": OrderLookupArgs,
        "tool": {
            "name": "lookup_order",
            "description": "주문번호로 주문 조회 (형식: A-123)",
            "input_schema": OrderLookupArgs.model_json_schema(),
        },
        "handler": lambda args: f"{args.order_id}: 배송중, ETA 2일",
    },
}

def dispatch(tool_name: str, raw_input: dict) -> str:
    spec = TOOL_SPECS[tool_name]
    try:
        args = spec["schema"].model_validate(raw_input)  # (2)!
    except ValidationError as e:
        return f"invalid_input: {e}"
    return spec["handler"](args)
```

1. Pydantic 모델에서 JSON Schema 추출 — tool 정의와 검증 로직이 **한 곳에서** 관리됨.
2. LLM 이 잘못된 입력을 줘도 ValidationError 로 fallback.

### 5.2 루프가 **여러 번** 도는 경우

한 요청에 툴이 **여러 번** 필요할 수 있습니다. LLM 이 다시 `stop_reason=="tool_use"` 로 응답하면 또 실행.

```python title="agent_loop.py" linenums="1" hl_lines="6"
def chat_with_tools(user_msg: str, max_steps: int = 5) -> str:
    messages = [{"role": "user", "content": user_msg}]
    tools = [s["tool"] for s in TOOL_SPECS.values()]

    for step in range(max_steps):  # (1)!
        r = client.messages.create(
            model="claude-haiku-4-5", max_tokens=1024,
            tools=tools, messages=messages,
        )
        messages.append({"role": "assistant", "content": r.content})

        if r.stop_reason != "tool_use":  # 최종 답변
            return "".join(b.text for b in r.content if b.type == "text")

        # tool_use 블록들 처리
        tool_results = []
        for block in r.content:
            if block.type == "tool_use":
                result = dispatch(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        messages.append({"role": "user", "content": tool_results})

    return "[max_steps 초과]"
```

1. **상한 필수**. 무한 루프 방지 (§6 실수 2).

### 5.3 승인 기반 실행 (Action 툴)

부작용 있는 툴은 실행 전에 **사람 승인** 을 받아야 합니다. 가장 단순한 패턴:

```python title="approve_gated.py" linenums="1" hl_lines="3 4 5 6 7"
RISKY_TOOLS = {"send_email", "cancel_order", "charge_card"}

def dispatch_with_approval(tool_name: str, args: dict) -> str:
    if tool_name in RISKY_TOOLS:
        print(f"⚠️  {tool_name}({args}) 승인 요청")
        if input("y/N > ").strip().lower() != "y":
            return "declined_by_user"
    return dispatch(tool_name, args)
```

**실전에선 CLI input 이 아니라**:

- Slack 버튼 (팀 내 승인)
- 사내 대시보드의 승인 큐
- LangGraph `interrupt` (Part 5 Ch 23)

### 5.4 에러·타임아웃 처리

툴 실행 자체가 실패할 수 있음 (외부 API 다운 등). LLM 에게 `tool_result` 로 에러를 전달하면 **모델이 복구 시도**:

```python title="tool_with_timeout.py" linenums="1"
import requests

def get_weather_safe(city: str) -> str:
    try:
        r = requests.get(f"https://api.weather.com/{city}", timeout=5)
        return r.json()["description"]
    except requests.Timeout:
        return "error: weather API timeout"  # (1)!
    except Exception as e:
        return f"error: {e}"
```

1. 에러 문자열 그대로 반환해도 OK — LLM이 "서버가 느리니 잠시 후 다시 알려드릴게요" 같이 **자연어로 복구**.

---

## 6. 자주 깨지는 포인트

!!! warning "실수 1. `eval` 을 그대로 씀"
    `eval(expression)` 은 **임의 코드 실행**. LLM 이 `__import__('os').system('rm -rf /')` 같은 걸 넘기면 재앙.  
    **대응**: `asteval`·`numexpr` 같은 안전 평가 라이브러리. 또는 `ast.parse + 화이트리스트 검증`. 프로덕션에선 샌드박스 (Docker·WASM).

!!! warning "실수 2. 무한 루프"
    LLM 이 같은 툴을 계속 호출 → `max_steps` 없으면 토큰·비용 폭주.  
    **대응**: 루프 상한 5~10회. 초과 시 명시적 에러 응답. 같은 툴 연속 호출 감지 시 **다른 경로 유도**.

!!! warning "실수 3. 파라미터 검증 누락"
    LLM 이 `quantity: "two"` 처럼 잘못된 타입을 넘겨도 실행. 데이터 오염.  
    **대응**: §5.1 처럼 **Pydantic** 으로 무조건 검증. 실패 시 `invalid_input` tool_result 반환 → 모델이 재시도.

!!! warning "실수 4. Action 툴을 승인 없이 실행"
    결제·삭제·발송이 **모델 판단만으로 실행**되는 시스템은 사고 대기 중.  
    **대응**: §5.3. `RISKY_TOOLS` 목록 유지, 운영에선 승인 큐로 사람 승인 후 실행.

!!! warning "실수 5. 툴 이름·설명이 모호"
    `query_data`, `do_thing` 같은 툴은 LLM 이 선택에 실패함. 겹치는 툴 (`search_db`, `lookup_db`) 도 문제.  
    **대응**: **동사 + 명확한 명사** (`create_order`, `cancel_subscription`). description 에 "언제 이걸 쓰는가"와 "언제 쓰지 말아야 하는가" 명시. OpenAI Practical Guide의 ACI 설계 원칙 참고 (§9).

!!! warning "실수 6. tool_result 를 빠뜨리고 다음 호출"
    `tool_use` 를 받고 바로 새 user 메시지를 보내면 LLM이 혼란. `assistant + tool_use` 뒤엔 **반드시** `user + tool_result` 쌍.  
    **대응**: 루프 구조 (§5.2) 를 **함수로 감싸** 실수 방지.

---

## 7. 운영 시 체크할 점

- [ ] **루프 상한** `max_steps` 5~10
- [ ] **툴 입력 전부 Pydantic 검증** · 실패 시 `invalid_input` 반환
- [ ] **Action 툴 화이트리스트** + 승인 큐 + 감사 로그
- [ ] **실행 결과에 크기 제한** — 큰 쿼리 결과를 그대로 넣으면 컨텍스트 초과
- [ ] **툴별 타임아웃** — Data 5초, Action 30초 등
- [ ] **관측성** — 어떤 툴을 · 몇 번 · 얼마나 걸려서 실행했는지 로그 (LangSmith/Langfuse)
- [ ] **비용 · 지연 모니터링** — 툴 루프가 길면 비용 빠르게 증가
- [ ] **샌드박스** — 코드 실행형 툴은 Docker 등 격리 환경

---

## 8. 확인 문제

- [ ] §4 계산기 예제를 돌리고, LLM이 어떤 expression 을 생성하는지 3가지 질문으로 관찰
- [ ] §5.1 의 `WeatherArgs` 에 일부러 잘못된 `units="centigrade"` 가 LLM 으로부터 들어오도록 유도하고 ValidationError 로 떨어지는지 확인
- [ ] §5.2 의 `max_steps=2` 로 줄여, 복잡한 요청에서 "[max_steps 초과]" 가 뜨는지 재현
- [ ] 승인 기반 실행을 Slack 또는 콘솔 input 으로 구현. 거절 시 LLM이 어떻게 응답하는지 기록
- [ ] `description` 을 일부러 모호하게 (`"something useful"`) 바꿔, LLM 의 툴 선택 실패율 관찰

---

## 9. 원전 · 더 읽을 거리

- **Anthropic Tool Use**: [docs.anthropic.com/tool-use](https://docs.anthropic.com){target=_blank}
- **OpenAI Function Calling**: [platform.openai.com/docs/guides/function-calling](https://platform.openai.com/docs){target=_blank}
- **OpenAI Practical Guide to Building Agents** — Tools 3범주 (Data / Action / Orchestration) · ACI 설계 원칙. 프로젝트 `_research/openai-practical-guide-to-agents.md` 에 요약
- **Anthropic Building Effective Agents** — Tool 명명·설명 작성의 중요성. 프로젝트 `_research/anthropic-building-effective-agents.md`

---

## 10. Part 2를 마치며

Part 2에서 배운 것 (5 챕터):

| Ch | 무엇을 | 실전 의미 |
|---|---|---|
| 4 | API 호출 · 에러·재시도 | 모든 LLM 앱의 시작점 |
| 5 | 프롬프트 · Few-shot · CoT | 모델의 행동을 "계약"으로 고정 |
| 6 | 구조화 출력 (Pydantic · tool-use schema) | 파이프라인 다음 단계가 쓸 수 있는 JSON |
| 7 | 스트리밍 · UX | 사용자 체감 속도 |
| 8 | **Tool Calling** | LLM 에게 손을 달아주기 — Agent 의 시작 |

**Part 2 졸업 상태** — 여기까지면 다음 중 하나를 **PoC 수준으로** 만들 수 있어야 합니다:

- 고객 문의 자동 분류 + 간단 응답 (구조화 출력 기반)
- 문서 + 툴 조회 봇 (Tool Calling + 간단 RAG 예고)
- 스트리밍 챗봇 웹 UI (FastAPI + SSE)

---

**다음 Part** → [Part 3. RAG — 외부 지식을 붙이는 법](../part3/09-why-rag.md) :material-arrow-right:  
여기까지는 "LLM이 학습한 것" 만 활용했습니다. 이제 **우리 회사의 문서·DB** 를 붙여 답변의 근거를 확보합니다.
