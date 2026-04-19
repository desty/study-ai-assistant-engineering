# Ch 6. 구조화 출력

<a class="colab-badge" href="https://colab.research.google.com/" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - 자유 텍스트 응답이 **파이프라인의 적**인 이유
    - **세 가지 구조화 출력 방법** — 프롬프트 힌트 / Tool-use 스키마 / Native JSON mode
    - **Pydantic** 으로 검증 + 실패 시 **자동 재프롬프트**
    - Nested · Optional · Enum · List 등 실전 스키마 패턴
    - 큰따옴표 이스케이프 · 날짜·통화 포맷 · 필드 누락 — 자주 터지는 파싱 지옥

!!! quote "전제"
    [Ch 5 프롬프트 + CoT](05-prompt-cot.md) 에서 "JSON 힌트 프롬프트"까지 돌려본 상태.

---

## 1. 개념 — 왜 구조화 출력이 필요한가

앞 챕터까지는 모델이 **자유 텍스트**로 답했습니다. 이게 파이프라인에서 문제가 됩니다.

```python
# ❌ 자유 텍스트를 후처리하는 코드
text = response.content[0].text  # "주문번호는 A-123, 수량 2개, 주소 서울 강남구입니다."
# ... 정규식? 문자열 파싱? 다음 단계에 이걸 어떻게 넘기지?
```

```python
# ✅ 구조화된 JSON
data = {"order_id": "A-123", "quantity": 2, "address": "서울 강남구"}
# 바로 DB에 저장 · API에 전달 · 조건 분기 가능
```

LLM이 **말을 잘하는** 것과 **프로그램이 쓰기 좋은 형식을 출력하는** 것은 다른 능력. 이 챕터는 후자를 확실히 확보하는 법.

---

## 2. 왜 필요한가 — 파이프라인 관점

Part 1 Ch 3의 8블록 구조를 다시 보면, **이해 → 검색 → 생성 → 검증 → 저장** 모든 단계가 **객체 단위의 데이터**를 주고받습니다. 자유 텍스트면:

- **이해 블록**: 의도·엔티티를 추출했는데 format이 흔들려 파싱 실패
- **검증 블록**: 스키마 체크 불가능
- **저장 블록**: DB에 넣을 컬럼을 어떻게 잡나
- **툴 호출** (Ch 8): 파라미터 추출 실패 → 툴 실행 불가

> 구조화 출력이 **없으면** 이후 모든 블록의 안정성이 낮아진다.

---

## 3. 어디에 쓰이는가

| 유즈케이스 | 출력 스키마 |
|---|---|
| 주문 정보 추출 | `{item, quantity, address, request_date}` |
| 이메일 분류 + 우선순위 | `{category: "refund"\|"shipping"\|..., priority: 1-5}` |
| 문서에서 엔티티 | `{people: [...], dates: [...], amounts: [...]}` |
| 사용자 의도 분석 | `{intent, confidence, needs_human}` |
| 툴 호출 파라미터 (Ch 8) | 툴이 정의한 파라미터 스키마 |

---

## 4. 최소 예제 — Pydantic 모델로 추출

```bash
pip install anthropic pydantic
```

```python title="extract_order.py" linenums="1" hl_lines="4 5 6 7 8"
from anthropic import Anthropic
from pydantic import BaseModel

class Order(BaseModel):
    item: str
    quantity: int
    address: str

SYSTEM = """주문 텍스트에서 정보를 추출해 **오직 JSON만** 반환하세요.
스키마: {"item": str, "quantity": int, "address": str}
JSON 외 다른 텍스트 금지."""

client = Anthropic()
r = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=256,
    system=SYSTEM,
    messages=[{"role": "user", "content": "빨간 운동화 2켤레 서울 강남구로 보내주세요"}],
)

order = Order.model_validate_json(r.content[0].text)  # (1)!
print(order.item, order.quantity, order.address)
```

1. Pydantic이 JSON을 파싱하고 타입까지 검증. `quantity` 가 "two" 같은 문자열로 오면 `ValidationError`.

이게 기본형. 하지만 LLM이 **가끔 말을 섞어** 반환하면 (`"여기 JSON입니다: {...}"`) 파싱 실패. 그걸 막는 게 §5.

---

## 5. 실전 튜토리얼

### 5.1 세 가지 방법 비교

![구조화 출력의 3가지 방법](../assets/diagrams/ch6-methods-comparison.svg#only-light)
![구조화 출력의 3가지 방법](../assets/diagrams/ch6-methods-comparison-dark.svg#only-dark)

| 방법 | 구현 | 적중률 | 권장 시점 |
|---|---|:-:|---|
| **프롬프트 힌트** | 시스템 프롬프트에 스키마·예시 | 70~90% | 초기 프로토타입 |
| **Tool-use 스키마** | Anthropic `tools` 파라미터 | 95~99% | 프로덕션 권장 |
| **Native JSON mode** | OpenAI `response_format={json_schema}` | ~100% | OpenAI 쓸 때 |

실전은 **프롬프트 힌트부터 → 실패율이 크면 tool-use로 올림** 순서.

### 5.2 Tool-use로 구조화 출력 (Anthropic 방식)

Anthropic의 **tool_use** 기능은 원래 "툴 호출"을 위한 것이지만, **스키마를 강제하는 용도**로도 쓰입니다. 이때는 실제 툴 실행 없이 **구조화된 JSON 입력을 끌어내는** 용도.

```python title="tool_use_extract.py" linenums="1" hl_lines="5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20"
from anthropic import Anthropic
client = Anthropic()

tools = [{
    "name": "record_order",
    "description": "고객 주문을 기록한다",
    "input_schema": {  # (1)!
        "type": "object",
        "properties": {
            "item":     {"type": "string", "description": "제품명"},
            "quantity": {"type": "integer", "minimum": 1},
            "address":  {"type": "string"},
        },
        "required": ["item", "quantity", "address"],
    },
}]

r = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=1024,
    tools=tools,
    tool_choice={"type": "tool", "name": "record_order"},  # (2)!
    messages=[{"role": "user", "content": "빨간 운동화 2켤레 서울 강남구로 보내주세요"}],
)

# tool_use 응답에서 input 을 꺼냄
for block in r.content:
    if block.type == "tool_use":
        data = block.input  # 이미 dict
        print(data)
```

1. **JSON Schema** 표준. `type` · `properties` · `required` 필수.
2. `tool_choice` 로 **반드시 이 툴을 쓰게** 강제. 이렇게 하면 모델이 거의 100% 스키마를 따름.

### 5.3 Pydantic 검증 + 자동 재프롬프트

![구조화 출력 파이프라인](../assets/diagrams/ch6-structured-output-flow.svg#only-light)
![구조화 출력 파이프라인](../assets/diagrams/ch6-structured-output-flow-dark.svg#only-dark)

프롬프트 힌트 방식에서 가장 자주 깨지는 건 **JSON 앞뒤에 말이 섞이는 것**. 이를 막는 3단계:

```python title="validated_extract.py" linenums="1"
import json
from pydantic import BaseModel, ValidationError
from anthropic import Anthropic

class Order(BaseModel):
    item: str
    quantity: int
    address: str

SYSTEM = """주문 정보를 JSON 으로만 반환하세요.
스키마: {"item": str, "quantity": int, "address": str}
다른 텍스트 절대 금지."""

def extract_order(text: str, retries: int = 2) -> Order | None:
    client = Anthropic()
    messages = [{"role": "user", "content": text}]
    last_error = None

    for attempt in range(retries + 1):
        r = client.messages.create(
            model="claude-haiku-4-5", max_tokens=256,
            system=SYSTEM, messages=messages,
        )
        raw = r.content[0].text.strip()

        # 1) JSON 추출: 중괄호로 감싸진 첫 덩어리만
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start < 0 or end <= 0:
            last_error = "JSON 블록을 찾을 수 없음"
        else:
            # 2) 파싱 + 검증
            try:
                return Order.model_validate_json(raw[start:end])
            except (json.JSONDecodeError, ValidationError) as e:
                last_error = str(e)

        # 3) 에러 메시지를 다음 프롬프트에 포함해 재시도
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content":
            f"이전 응답이 스키마를 어겼습니다: {last_error}\n다시 올바른 JSON만 반환하세요."})

    return None  # 최종 실패 — fallback 담당이 규칙/기본값
```

**핵심 패턴**:

1. **원본에서 JSON 블록만 추출** (앞뒤 말 섞임 방어)
2. **Pydantic으로 검증** (타입·필수 필드·제약)
3. **실패 시 에러 메시지 포함해 재질의** — 모델이 스스로 수정

!!! tip "Tool-use 쓰면 §5.3의 1·2 단계가 거의 불필요"
    Tool-use 로 가면 JSON 블록 추출 문제가 사라짐 (Anthropic SDK가 이미 파싱). 그래도 Pydantic 검증은 유지 권장 — 모델이 필수 필드를 빠뜨리는 경우가 있음.

### 5.4 실전 스키마 패턴

```python title="advanced_schemas.py" linenums="1"
from pydantic import BaseModel, Field
from typing import Literal
from datetime import date

class Address(BaseModel):
    street: str
    city: str
    postal_code: str | None = None  # Optional

class Order(BaseModel):
    order_id: str = Field(..., pattern=r"^[A-Z]-\d+$")  # (1)!
    items: list[str]                                     # List
    quantity: int = Field(..., ge=1, le=100)             # 범위 제약
    priority: Literal["low", "normal", "high"]           # Enum
    ship_date: date                                      # ISO-8601 자동 파싱
    address: Address                                     # Nested
    notes: str | None = None                              # Optional
```

1. `Field(..., pattern=...)` — 정규식 제약.

**주의**: LLM에게 이 스키마 전부를 전달할 땐 `model.model_json_schema()` 로 JSON Schema 를 뽑아 프롬프트나 tool_use에 주면 됩니다.

```python
schema = Order.model_json_schema()
print(json.dumps(schema, ensure_ascii=False, indent=2))
```

---

## 6. 자주 깨지는 포인트

!!! warning "실수 1. 큰따옴표 이스케이프 누락"
    모델이 텍스트 안에 큰따옴표가 있으면 `"content": "그가 "안녕"이라 말했다"` 같은 **잘못된 JSON**을 만들기도. `json.JSONDecodeError`.  
    **대응**: 시스템 프롬프트에 `"쌍따옴표는 반드시 \\\" 로 이스케이프"` 명시. 또는 tool-use 방식 사용 (SDK가 처리).

!!! warning "실수 2. 날짜·통화 포맷 혼란"
    `"ship_date": "다음주 월요일"` 이나 `"price": "₩15,000"` 같은 자연어가 섞여 들어옴.  
    **대응**: 스키마에 **예시값** 명시 (`"예: 2026-04-18"`), Pydantic Field description 적극 활용, 실패 시 §5.3 재프롬프트.

!!! warning "실수 3. 필수 필드 누락"
    모델이 가끔 어떤 필드를 빼먹음 (특히 Optional과 Required가 섞인 스키마).  
    **대응**: Pydantic 에서 `...` 로 명확히 Required 지정, tool-use의 `required` 배열 명시, 검증 실패 시 재프롬프트에 **어느 필드가 빠졌는지** 에러 메시지에 포함.

!!! warning "실수 4. 스키마가 너무 깊고 복잡"
    5단계 이상 nested 스키마는 모델도 사람도 헷갈림. 재시도해도 개선 안 됨.  
    **대응**: 스키마를 **2~3단계로 flat 하게** 설계. 복잡한 구조는 **여러 번 호출로 쪼개기** (각 호출당 하나의 작은 스키마).

!!! warning "실수 5. 재시도 무한 루프"
    검증 실패할 때마다 재질의. 키 요금 폭주.  
    **대응**: 재시도 상한 2~3회. 초과 시 **fallback 경로** (규칙 기반 파서 · 기본값 · 사람 에스컬레이션).

---

## 7. 운영 시 체크할 점

- [ ] **Pydantic 모델을 단일 모듈**에 집중 (`schemas.py`) — 파이프라인 전체가 공유
- [ ] **tool-use 방식 기본** — 프롬프트 힌트만 쓰는 구간 있으면 마이그레이션 계획
- [ ] **검증 실패율** 로깅 — 5% 이상이면 스키마/프롬프트 재설계 신호
- [ ] **재시도 상한** 2~3회 + fallback 경로 필수
- [ ] 스키마 변경 시 **하위 호환** 고려 — Pydantic validator로 구버전 받아들이기
- [ ] LLM 응답 샘플을 **테스트 fixture** 로 저장 (파서·검증 회귀 테스트용)
- [ ] **민감 정보 필드** (주민번호·카드번호 등)는 스키마 레벨에서 거부 (Part 6 Ch 28)

---

## 8. 확인 문제

- [ ] §4의 `Order` 스키마에 `color: str` 필드를 추가하고, 프롬프트도 업데이트해 성공적으로 추출되는지 확인
- [ ] 일부러 잘못된 입력 (`"그냥 뭐든 보내주세요"`) 으로 호출해 Pydantic `ValidationError` 가 어떻게 뜨는지 기록
- [ ] §5.2 tool-use 방식으로 Ch 5 few-shot 감정 분류 예제를 **적중률 100%** 로 만들기
- [ ] §5.3 재시도 로직에 일부러 잘못된 스키마 힌트를 줘 2회 재시도 후 `None` 반환 확인
- [ ] §5.4 nested Address 를 포함한 Order 를 추출. 모델이 `address.city` 를 빠뜨렸을 때 어느 메시지가 뜨는지

---

## 9. 원전 · 더 읽을 거리

- **Anthropic Tool Use**: [docs.anthropic.com/tool-use](https://docs.anthropic.com){target=_blank} — `tools` · `tool_choice` · JSON Schema 규격
- **OpenAI Structured Outputs**: [platform.openai.com/docs/guides/structured-outputs](https://platform.openai.com/docs){target=_blank}
- **Pydantic v2** 공식: [docs.pydantic.dev](https://docs.pydantic.dev){target=_blank}
- **JSON Schema** 스펙: [json-schema.org](https://json-schema.org){target=_blank}

---

**다음 챕터** → [Ch 7. 스트리밍과 UX](07-streaming-ux.md) :material-arrow-right:  
지금까지 **한 번에 전체 응답**을 받았습니다. 사용자 체감 속도를 올리는 **토큰 단위 스트리밍** 으로.
