# Ch 4. OpenAI / Anthropic API 시작하기

<a class="colab-badge" href="https://colab.research.google.com/" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **API 호출 = HTTPS로 멀리 있는 모델을 부르는 일** 이라는 직관
    - **SDK**(Python 라이브러리)로 Anthropic · OpenAI 첫 10줄 호출
    - 메시지의 **세 가지 역할** (`system` · `user` · `assistant`) 이 왜 분리되어 있나
    - **핵심 파라미터 4개** (`model` · `max_tokens` · `temperature` · `stop_sequences`) 의 감각
    - **에러 · 재시도 · 타임아웃 · 비용** — 한 줄짜리 실험을 운영형 코드로 올리는 최소 습관

!!! quote "전제"
    [Part 1 Ch 2 — LLM이란 무엇인가](../part1/02-what-is-llm.md) 읽고 "LLM이 토큰을 한 번에 하나씩 고른다"는 감각 잡은 상태. Colab 또는 로컬 Python 3.10+.

---

## 1. 개념 — API는 "멀리 있는 모델을 부르는" 방법

우리는 모델 파일을 노트북에 다운받아 쓰지 않습니다. Claude 같은 큰 모델은 수십 GB, 돌리려면 GPU가 필요해요. 대신 **Anthropic이나 OpenAI가 운영하는 서버에 요청을 보내고, 응답을 받습니다.** 그게 API(Application Programming Interface) 호출입니다.

![API 요청 한 번의 흐름](../assets/diagrams/ch4-api-pipeline.svg#only-light)
![API 요청 한 번의 흐름](../assets/diagrams/ch4-api-pipeline-dark.svg#only-dark)

- **SDK(Software Development Kit)** 는 이 HTTPS 요청을 파이썬 함수처럼 감싸주는 라이브러리. `anthropic.Anthropic()` · `openai.OpenAI()` 가 그것.
- 요청은 항상 **HTTPS POST** — 텍스트는 암호화되어 전송됩니다.
- 응답은 **JSON** — SDK가 파이썬 객체로 변환해줍니다.

---

## 2. 왜 API로 쓰는가 (로컬 대신)

| | API (이 책의 기본) | 로컬 모델 |
|---|---|---|
| 준비 | `pip install anthropic` 끝 | GPU · 모델 다운 · CUDA 설정 |
| 최신 모델 | 즉시 사용 (Opus 4.7 등) | 오픈 모델만 (Llama 3 · Qwen 등) |
| 비용 | **토큰 단위 과금** | 하드웨어 초기비용 + 전기 |
| 데이터 | 서버로 전송됨 (프라이버시 이슈 가능) | 내 컴퓨터에만 |
| 지연 | 네트워크 + 서버 처리 | GPU만 좋으면 더 빠를 수도 |

**이 책은 기본적으로 API**. 로컬 파인튜닝은 Part 7에서 다룹니다.

---

## 3. 어디에 쓰이는가

첫 API 호출 한 줄이 다음 전부의 출발점:

- **챗봇 · 고객 지원 어시스턴트** — Part 5의 Agent 기반
- **문서 요약 · 분류 · 추출** — 배치 스크립트
- **자동화 도우미** — CLI로 메시지 초안 생성, 코드 리뷰, 회의록 요약
- **RAG 파이프라인의 "생성" 단계** — Part 3에서 다시 만남

---

## 4. 최소 예제 — 10줄

### 준비

=== "Colab"

    1. 상단의 **"Open in Colab"** 배지 클릭
    2. **Secrets** (자물쇠 아이콘) → `ANTHROPIC_API_KEY` 추가 (값은 콘솔에서 발급받은 키)
    3. 첫 셀부터 순서대로 실행

=== "로컬"

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install anthropic
    export ANTHROPIC_API_KEY="sk-ant-..."
    ```

### 코드

```python title="hello.py" linenums="1" hl_lines="3 8"
from anthropic import Anthropic

client = Anthropic()  # (1)!

response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=256,
    messages=[{"role": "user", "content": "LLM API를 한 문장으로 설명해줘"}],
)

print(response.content[0].text)
```

1. 환경변수 `ANTHROPIC_API_KEY` 에서 키를 **자동으로** 읽어옵니다. 코드에 `api_key="sk-..."` 로 박아넣지 마세요 (§6 실수 1).

**실행**: `python hello.py` 또는 Colab에서 셀 실행. 2~5초 뒤 응답.

---

## 5. 실전 튜토리얼

### 5.1 메시지 배열 — 세 역할

API의 핵심은 **메시지 배열**입니다. 세 종류:

| role | 누가 말하나 | 언제 |
|---|---|---|
| `system` | 개발자 (상시 지침) | 대화 시작 시 1회 (보통) |
| `user` | 최종 사용자 | 매 턴 |
| `assistant` | 모델 (이전 응답) | 이전 응답을 다시 보낼 때 |

**다중 턴 대화** 는 이 배열을 **매번 전체** 로 보냅니다. LLM은 **stateless** — 과거 대화를 기억 못함.

```python title="multi_turn.py" linenums="1"
history = [
    {"role": "user",      "content": "안녕, 내 이름은 desty야."},
    {"role": "assistant", "content": "반가워요, desty님!"},
    {"role": "user",      "content": "내 이름이 뭐였지?"},  # (1)!
]

response = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=64,
    system="당신은 친절한 한국어 도우미입니다.",
    messages=history,
)
print(response.content[0].text)
```

1. 이 시점에 `history` 전체를 보내야 모델이 "desty"를 기억합니다. 세 번째 user 메시지만 보내면 모델은 이름을 모릅니다.

### 5.2 핵심 파라미터 4개

```python title="params.py" linenums="1" hl_lines="2 3 4 5"
response = client.messages.create(
    model="claude-opus-4-7",        # 1. 어느 모델을 쓸지
    max_tokens=256,                 # 2. 응답의 최대 길이 (토큰)
    temperature=0.3,                # 3. 0~1.0 — 창의성 다이얼
    stop_sequences=["\n\n---\n\n"], # 4. 이 문자열 나오면 즉시 중단
    system="당신은 전문가입니다.",
    messages=[{"role": "user", "content": "..."}],
)
```

| 파라미터 | 의미 | 권장 |
|---|---|---|
| `model` | 모델 이름 (Opus · Sonnet · Haiku) | 분류·간단 → `haiku`, 복잡한 판단 → `opus` |
| `max_tokens` | **출력 상한**. 입력 상한 아님 | 짧은 답변 64 · 요약 512 · 긴 글 2048 |
| `temperature` | 확률 분포 뾰족함 | 분류 0.0, 요약 0.5, 창작 0.8~1.2 |
| `stop_sequences` | 특정 문자열에서 자르기 | 포맷 제어에 유용 (예: `"\n사용자:"`) |

!!! tip "이 파라미터들의 이론은 Part 1 Ch 2"
    `temperature` 수식, `max_tokens` 작동 방식, 왜 stateless 인지 — 전부 [Part 1 Ch 2](../part1/02-what-is-llm.md)에서 다뤘습니다.

### 5.3 응답 객체 해부

```python
response = client.messages.create(...)

response.content[0].text           # 실제 텍스트
response.content[0].type           # "text" · "tool_use" · ...
response.stop_reason               # "end_turn" · "max_tokens" · "stop_sequence"
response.usage.input_tokens        # 과금되는 입력 토큰
response.usage.output_tokens       # 과금되는 출력 토큰
response.model                     # 실제로 응답한 모델 (버전 고정 확인용)
```

**비용 계산**:

```python title="cost.py" linenums="1"
# 2026-04 기준 대략 단가 (공식 사이트에서 최신 확인)
PRICE_PER_M_INPUT  = {"opus": 15.0, "sonnet": 3.0, "haiku": 0.25}  # 달러 / 100만 토큰
PRICE_PER_M_OUTPUT = {"opus": 75.0, "sonnet": 15.0, "haiku": 1.25}

def estimate_cost(resp, tier="opus") -> float:
    ip = resp.usage.input_tokens
    op = resp.usage.output_tokens
    return (ip * PRICE_PER_M_INPUT[tier] + op * PRICE_PER_M_OUTPUT[tier]) / 1_000_000

print(f"${estimate_cost(response, 'opus'):.6f}")
```

!!! warning "단가는 수시로 바뀝니다"
    위 값은 참고용. 실제는 [Anthropic 공식 가격표](https://www.anthropic.com/pricing){target=_blank}에서 확인.

### 5.4 에러 · 재시도 · 타임아웃

네트워크는 항상 깨집니다. 운영 코드는 반드시 세 가지를 챙겨야 합니다.

![에러 처리와 재시도 전략](../assets/diagrams/ch4-retry-flow.svg#only-light)
![에러 처리와 재시도 전략](../assets/diagrams/ch4-retry-flow-dark.svg#only-dark)

**흔한 에러 상황**:

| HTTP 코드 | 원인 | 대응 |
|---|---|---|
| `401` | API 키 잘못됨 | 고정 실패 — 키 확인 |
| `429` | Rate limit 초과 | **backoff 후 재시도** |
| `500/502/503` | 서버 일시 장애 | **backoff 후 재시도** |
| `overloaded_error` | 서버 포화 | 재시도 (Anthropic 특화) |

**재시도 래퍼** — [`tenacity`](https://tenacity.readthedocs.io/){target=_blank} 로 5줄:

```python title="retry_wrapper.py" linenums="1" hl_lines="4 5 6 11"
from anthropic import Anthropic, APIStatusError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=16),  # 1s, 2s, 4s... 최대 16s
    retry=retry_if_exception_type(APIStatusError),
)
def ask(prompt: str, model: str = "claude-haiku-4-5") -> str:
    client = Anthropic(timeout=30.0)  # (1)!
    r = client.messages.create(
        model=model,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return r.content[0].text
```

1. **타임아웃 30초**. 기본값은 `None` 일 수 있어 영원히 기다릴 수도 있음 — 명시 필수.

이제 `ask("안녕")` 한 줄로 재시도까지 포함된 호출.

---

## 6. 자주 깨지는 포인트

!!! warning "실수 1. API 키를 코드에 하드코딩"
    `client = Anthropic(api_key="sk-ant-xxxxx")` — 절대 금지. Git에 올리면 1초 만에 봇이 발견해 비용 폭주.  
    **대응**: 환경변수 · `.env` + `python-dotenv` · Colab Secrets · AWS Secrets Manager 등. 키가 실수로 커밋되면 **즉시 Anthropic 콘솔에서 revoke**.

!!! warning "실수 2. `max_tokens` 를 **입력 상한** 으로 착각"
    `max_tokens=256` 은 **출력** 길이 상한. 입력(프롬프트)은 모델의 컨텍스트 윈도우에 따름. 긴 요약을 256으로 잡으면 중간에 뚝 잘립니다.  
    **대응**: 예상 출력의 **1.5~2배** 로 설정. 모르면 일단 `1024`.

!!! warning "실수 3. 타임아웃·재시도 없이 호출"
    네트워크 이슈 한 번에 프로그램이 죽음. Rate limit 한 번에 모든 요청이 실패.  
    **대응**: §5.4의 `tenacity` 래퍼 + `timeout=30` 기본. Circuit breaker는 Part 6.

!!! warning "실수 4. `assistant` 역할에 내 생각을 박기"
    `{"role": "assistant", "content": "나는 예의 바르게 답해야지"}` 같은 건 **모델이 이미 말한 것처럼** 취급됨. 실제 모델 응답이 아니면 넣지 말 것.  
    **대응**: 지시·규칙은 `system` 에, 예시는 few-shot 패턴으로 (Part 2 Ch 5).

!!! warning "실수 5. Rate limit 도달 시 무한 재시도 루프"
    재시도 상한(`stop_after_attempt(3)`) 없이 돌리면 429 상태에서 무한 타격 → 키 정지.  
    **대응**: 지수 backoff + 최대 재시도 3~5회.

---

## 7. 운영 시 체크할 점

프로덕션 전 반드시:

- [ ] **API 키** 환경변수 또는 시크릿 매니저 (코드·로그·에러 메시지에 절대 노출 X)
- [ ] **비용 상한** — Anthropic 콘솔에서 월 한도 설정
- [ ] **타임아웃** — 30초 이내 (긴 요청은 별도 전략)
- [ ] **재시도** — `tenacity` 3~5회 exponential backoff
- [ ] **모델 버전 pin** — `"claude-haiku-4-5"` 처럼 마이너까지 고정
- [ ] **토큰 · 비용 로깅** — 매 호출 `usage.input_tokens`, `usage.output_tokens`, 예상 비용 기록
- [ ] **Latency 측정** — p50 / p95 / p99 추적
- [ ] **PII 마스킹** — 전송 전 개인정보 제거·익명화 (Part 6 Ch 28)

!!! note "관측성 프레임워크는 Part 6에서"
    LangSmith · Langfuse 같은 트레이싱 도구는 Ch 27에서.

---

## 8. 확인 문제

손으로 돌려봐야 다음 챕터가 편합니다.

- [ ] §4의 `hello.py` 를 **성공적으로 실행** (응답 본문 스크린샷)
- [ ] 같은 프롬프트에 `model` 만 `claude-haiku-4-5` → `claude-opus-4-7` 로 바꿨을 때 **응답 품질과 지연 비교**
- [ ] `max_tokens=20` 으로 줄여 응답이 **잘리는 지점** 과 `stop_reason="max_tokens"` 확인
- [ ] `temperature=0.0` vs `1.2` 로 같은 질문 3회씩 호출, 결과 차이 정리
- [ ] 일부러 **잘못된 모델 이름** (`"claude-xxx"`) 을 줘서 에러 메시지 확인 → 이때 발생한 예외 타입과 HTTP 코드 기록
- [ ] `tenacity` 래퍼를 적용하고, 잘못된 API 키로 호출 시 **재시도가 돌지 않고 바로 실패** 하는지 확인 (401은 재시도 대상 아님)

---

## 9. 원전 · 더 읽을 거리

- **Anthropic Python SDK**: [docs.anthropic.com](https://docs.anthropic.com){target=_blank}
- **OpenAI Python SDK**: [platform.openai.com/docs](https://platform.openai.com/docs){target=_blank}
- **OpenAI "A Practical Guide to Building Agents"** — "Agent의 3요소: Model · Tool · Instruction" (Part 5 예고). 프로젝트 `_research/openai-practical-guide-to-agents.md` 에 요약 있음

---

**다음 챕터** → [Ch 5. 프롬프트 엔지니어링 + CoT 기초](05-prompt-cot.md) :material-arrow-right:  
지금은 질문 하나 던지고 답을 받았지만, **system 프롬프트를 잘 쓰면 모델이 완전히 다른 어시스턴트가 됩니다**. 다음 챕터에서.
