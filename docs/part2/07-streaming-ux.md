# Ch 7. 스트리밍과 UX

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part2/ch07_streaming_ux.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **TTFT**(Time to First Token) 가 체감 속도의 핵심인 이유
    - SDK의 `stream()` 이벤트 흐름 — delta / start / stop
    - **취소 · 타임아웃 · 부분 응답** 처리
    - 챗봇 UI 에서 **토큰이 들어오는 대로 렌더** 하는 패턴
    - 스트림 중간 에러 · 마크다운 부분 렌더 함정

!!! quote "전제"
    [Ch 4](04-api-start.md) · [Ch 6](06-structured-output.md) 까지. 이 챕터의 코드는 모두 `async` — 파이썬 async 기본 지식 있으면 좋음.

---

## 1. 개념 — 토큰은 이미 순서대로 나온다

[Part 1 Ch 2](../part1/02-what-is-llm.md) 에서 배운 것: LLM은 **토큰을 하나씩 생성** 합니다. 응답이 5초 걸린다면, **첫 토큰은 0.3초쯤에 이미 준비**됐을 수 있어요. 남은 4.7초는 나머지 토큰을 계속 내보내는 시간.

![Blocking vs Streaming](../assets/diagrams/ch7-blocking-vs-stream.svg#only-light)
![Blocking vs Streaming](../assets/diagrams/ch7-blocking-vs-stream-dark.svg#only-dark)

Blocking 방식은 **5초 동안 사용자가 빈 화면을 봄**. Streaming 은 **0.3초 만에 첫 글자** → 나머지는 타이핑처럼 보이며 렌더.  
응답의 **총 길이는 같지만 체감 속도는 10~20배 차이**.

---

## 2. 왜 필요한가

### TTFT (Time to First Token)

- 블로킹: **TTFT = TTLC**(Time to Last Character) — 전부 끝나야 첫 글자
- 스트리밍: **TTFT ≈ 0.3~1초** — 첫 토큰만 나오면 렌더 시작

| 지표 | blocking | streaming |
|---|:-:|:-:|
| 첫 글자까지 (TTFT) | 5.0s | **0.3s** |
| 전체 완료까지 (TTLC) | 5.0s | 5.0s |
| 사용자 "작동한다" 체감 | 5.0s 후 | **즉시** |
| 취소 가능 시점 | 5.0s 후 | **언제든** |

### 그 외 이득

- **메모리 효율** — 전체 응답을 버퍼링하지 않아도 됨
- **긴 생성에 필수** — 1분짜리 요약을 동기로 받으면 타임아웃
- **에이전트의 사고 과정을 보여줌** (Part 5)

---

## 3. 어디에 쓰이는가

- **챗봇 UI** — ChatGPT·Claude.ai 처럼 타이핑되며 나오는 그것
- **긴 생성** — 요약·번역·초안 작성 (1000+ 토큰)
- **에이전트** — 추론 과정을 실시간으로 (Ch 8 · Part 5)
- **터미널 도구** — 즉각 피드백

---

## 4. 최소 예제 — 10줄 스트림

```python title="hello_stream.py" linenums="1" hl_lines="5 6 7"
from anthropic import Anthropic

client = Anthropic()

with client.messages.stream(  # (1)!
    model="claude-haiku-4-5",
    max_tokens=256,
    messages=[{"role": "user", "content": "파이썬의 매력을 3줄로 설명해줘"}],
) as stream:
    for text in stream.text_stream:  # (2)!
        print(text, end="", flush=True)  # (3)!
```

1. `messages.create()` 대신 `messages.stream()` — **컨텍스트 매니저** 로 자동 리소스 정리.
2. `text_stream` 은 **텍스트 델타**만 순서대로 주는 편의 iterator.
3. `flush=True` 는 버퍼링 없이 즉시 출력 — 스트리밍 효과 확인용.

실행하면 **타이핑처럼** 응답이 나타납니다. 동기 버전(`create`)은 5초 동안 아무 것도 없다가 한 번에 쏟아져요.

---

## 5. 실전 튜토리얼

### 5.1 스트림 이벤트 구조

SDK의 `stream()` 내부에서 실제 오가는 이벤트 타입:

| 이벤트 | 의미 | 언제 |
|---|---|---|
| `message_start` | 응답 시작 | 스트림 시작 시 1회 |
| `content_block_start` | 텍스트/툴 블록 시작 | 각 content 블록마다 |
| `content_block_delta` | **토큰 증분** | 매 토큰 (핵심) |
| `content_block_stop` | 블록 종료 | 각 블록마다 |
| `message_delta` | usage 등 메타 업데이트 | 종료 근처 |
| `message_stop` | 응답 전체 종료 | 마지막 1회 |

`text_stream` 은 위 중 `content_block_delta` 의 **텍스트만** 뽑아주는 편의. 더 세밀한 제어가 필요하면 raw event 로:

```python title="raw_events.py" linenums="1"
with client.messages.stream(model="claude-haiku-4-5", max_tokens=128,
    messages=[{"role": "user", "content": "안녕"}]) as stream:
    for event in stream:
        print(event.type)
        if event.type == "content_block_delta":
            print(" →", event.delta.text)
```

### 5.2 TTFT · TPS 측정

운영에서 반드시 잰다 — 유저 경험 = TTFT + 체감 TPS(초당 토큰).

```python title="ttft_tps.py" linenums="1" hl_lines="5 9 13"
import time

client = Anthropic()

t_start = time.perf_counter()
t_first: float | None = None
tokens = 0

with client.messages.stream(model="claude-haiku-4-5", max_tokens=512,
    messages=[{"role": "user", "content": "AI Assistant 설계 원칙 5개를 설명해줘"}]) as stream:
    for text in stream.text_stream:
        if t_first is None:
            t_first = time.perf_counter()  # 첫 토큰 순간
        tokens += 1  # 대략적 (실제로는 문자수 ≠ 토큰수)

t_end = time.perf_counter()
ttft = t_first - t_start
total = t_end - t_start
tps = tokens / (t_end - t_first) if t_first else 0

print(f"TTFT={ttft:.2f}s  total={total:.2f}s  ~chars/s={tps:.1f}")
```

기록해두면 모델 비교·네트워크 이슈 추적에 쓰임.

### 5.3 취소와 타임아웃

스트리밍은 **사용자가 언제든 중단할 수 있어야** 좋은 UX.

```python title="cancel.py" linenums="1" hl_lines="7 13"
import signal
from anthropic import Anthropic

client = Anthropic()
stop = False

def on_sigint(sig, frame):  # (1)!
    global stop
    stop = True

signal.signal(signal.SIGINT, on_sigint)

with client.messages.stream(model="claude-haiku-4-5", max_tokens=1024,
    messages=[{"role": "user", "content": "긴 이야기 하나 써줘"}]) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
        if stop:
            print("\n\n[중단됨]")
            break  # (2)!
```

1. Ctrl+C 로 `stop=True` 전환. HTTP 커넥션도 닫아야 완전 중단 → `break` 후 `with` 빠져나가며 SDK가 처리.
2. 중요: 중단 후에도 `stream.final_message` 로 지금까지 모인 응답 조회 가능.

**타임아웃**은 Ch 4의 `Anthropic(timeout=30.0)` 과 같게 적용. 스트림도 마찬가지.

### 5.4 부분 응답 로깅 & 에러 복구

스트림 중간에 네트워크가 끊기면 **지금까지 받은 토큰을 버리지 말 것**.

```python title="partial_log.py" linenums="1" hl_lines="7 15"
buffer = []

try:
    with client.messages.stream(model="claude-haiku-4-5", max_tokens=512,
        messages=[{"role": "user", "content": "..."}]) as stream:
        for text in stream.text_stream:
            buffer.append(text)  # 받은 즉시 버퍼링
            print(text, end="", flush=True)
        final = stream.get_final_message()
        # 정상 종료: final 그대로 사용
except Exception as e:
    partial = "".join(buffer)
    # DB/로그에 partial 기록 — 나중에 분석
    log.warning("stream_failed", error=str(e), partial_len=len(partial))
```

### 5.5 UI 통합 패턴 — SSE · WebSocket · React

브라우저에서 LLM 응답을 스트리밍하는 실전 스택 3가지:

| 스택 | 서버 | 브라우저 | 언제 |
|---|---|---|---|
| **SSE (Server-Sent Events)** | FastAPI `StreamingResponse` | `EventSource` API | 단방향, 단순 (대부분) |
| **WebSocket** | FastAPI `WebSocket` | `WebSocket` API | 양방향 (사용자 취소 등) |
| **Fetch + ReadableStream** | 동일 | `fetch().body.getReader()` | 플레인 HTTP 유지 |

**FastAPI SSE 예시**:

```python title="server_sse.py" linenums="1"
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from anthropic import Anthropic

app = FastAPI()
client = Anthropic()

@app.get("/stream")
def stream_chat(q: str):
    def gen():
        with client.messages.stream(model="claude-haiku-4-5", max_tokens=512,
            messages=[{"role": "user", "content": q}]) as s:
            for text in s.text_stream:
                yield f"data: {text}\n\n"  # (1)!
        yield "event: done\ndata: ok\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")
```

1. SSE 포맷: `data: <payload>\n\n`.

**브라우저 React 예시**:

```jsx title="ChatStream.jsx"
const [text, setText] = useState("");

useEffect(() => {
  const es = new EventSource(`/stream?q=${encodeURIComponent(query)}`);
  es.onmessage = (e) => setText(prev => prev + e.data);
  es.addEventListener("done", () => es.close());
  return () => es.close();  // 언마운트 시 정리
}, [query]);
```

!!! tip "마크다운 실시간 렌더의 함정"
    토큰이 하나씩 들어올 때 **매 토큰마다 마크다운 파싱**은 비쌈. 또 `**강조 중...` 처럼 **미완성 마크다운**이 이상하게 렌더됨.  
    **대응**: 일정 간격(100ms)으로만 파싱 · 스트리밍 중엔 **코드펜스 외에는 원문 그대로**.

---

## 6. 자주 깨지는 포인트

!!! warning "실수 1. 스트림 중 JSON 을 부분 파싱"
    `{"item": "운동` 까지 받은 시점에 `json.loads` 하면 에러. 구조화 출력 + 스트리밍은 위험.  
    **대응**: 구조화 출력(Ch 6)은 **비스트리밍** 으로. 스트리밍이 꼭 필요하면 `content_block_stop` 기다린 뒤 한꺼번에 파싱.

!!! warning "실수 2. 스트림 중단 시 부분 응답을 버림"
    네트워크 에러 한 번에 지금까지 받은 300토큰이 사라짐. 비용만 냈고 분석도 못 함.  
    **대응**: §5.4 패턴 — **받는 즉시 버퍼에 누적**. 예외 catch 에서 partial 로깅.

!!! warning "실수 3. 마크다운 미완성 렌더"
    `**굵게` 까지 온 시점에 렌더하면 이상해짐.  
    **대응**: 스트리밍 중엔 원문 `<pre>`로, 완료 후 마크다운 렌더. 또는 안전 파서 (incomplete markdown 지원) 사용.

!!! warning "실수 4. Ctrl+C 후 커넥션이 열려있음"
    `break` 만 하고 `with` 밖으로 안 나가면 소켓이 열려 있을 수 있음.  
    **대응**: `with` 블록 전체를 `try/except KeyboardInterrupt` 로 감싸거나, 위 §5.3 처럼 `stop` 플래그로 루프 탈출.

!!! warning "실수 5. 스트림 lifetime 을 DB/파일에 안 맞춤"
    각 토큰을 DB에 쓰려 하면 토큰당 쿼리 500회 → DB 폭발.  
    **대응**: 메모리 버퍼 → 일정 주기(1초 · 200자)로 flush, 또는 **종료 시 한 번만** 저장.

---

## 7. 운영 시 체크할 점

- [ ] **TTFT · TPS 지표** 매 호출 기록 → p50 / p95 대시보드
- [ ] **최대 응답 시간** 상한 (예: 60초). 초과 시 **강제 종료**
- [ ] **사용자 취소** 경로 보장 (브라우저 EventSource.close, 서버 HTTP cancel)
- [ ] **부분 응답 저장** — 실패·취소여도 토큰은 이미 비용 발생
- [ ] **서버 동시 스트림 수** 제한 (커넥션 풀)
- [ ] 브라우저에서 **reconnect 로직** (SSE는 자동이지만 WebSocket은 수동)
- [ ] **구조화 출력과 스트리밍 분리 정책** 명시 (동시에 쓰지 말 것)

---

## 8. 확인 문제

- [ ] §4 `hello_stream.py` 와 §2의 blocking 버전(`messages.create`) 을 같은 프롬프트로 돌려 TTFT 측정
- [ ] §5.2 의 TPS 측정을 `claude-haiku` 와 `claude-opus` 로 각 3회씩 — 평균 TPS 차이 정리
- [ ] `max_tokens=4096` 긴 생성 중 Ctrl+C 로 중단 시 `stream.get_final_message()` 로 partial 얻기
- [ ] 일부러 서버 에러 상황 유도 (잘못된 모델명) + 스트림 실패 시 버퍼에 뭐가 남는지 확인
- [ ] 간단한 FastAPI SSE 서버 + `<pre>` 텍스트 렌더하는 HTML 하나로 **브라우저에서 스트리밍 체험**

---

## 9. 원전 · 더 읽을 거리

- **Anthropic Streaming**: [docs.anthropic.com/streaming](https://docs.anthropic.com){target=_blank}
- **OpenAI Streaming**: [platform.openai.com/docs/api-reference/streaming](https://platform.openai.com/docs){target=_blank}
- **Server-Sent Events (MDN)**: [developer.mozilla.org/SSE](https://developer.mozilla.org){target=_blank}
- **FastAPI StreamingResponse**: [fastapi.tiangolo.com/StreamingResponse](https://fastapi.tiangolo.com){target=_blank}

---

**다음 챕터** → [Ch 8. Tool Calling 기초](08-tool-calling.md) :material-arrow-right:  
지금까지는 **LLM이 텍스트만 반환**. 다음은 LLM 이 **외부 함수를 부르게** 하기 — Agent(Part 5)의 기초.
