# 캡스톤 — Self-Improving Assistant

!!! abstract "이 캡스톤에서 만드는 것"
    - **Part 1~7 의 모든 조각** 을 한 시스템에 통합
    - 사용자 피드백이 **자동으로 평가셋 + 학습 데이터** 가 되는 폐쇄 루프
    - 8 단계 파이프라인 — 사용자 → Assistant → Trace → 분류기 → DPO 데이터 → 재학습 → Eval Gate → 배포
    - **8 주 진행 가이드** 와 제출물 9 항목 체크리스트
    - 흔한 5 사고 (루프 안 닫힘 · 평가셋 누출 · 자기 강화 편향 · ROI 음수 · 안전 회귀)

!!! quote "전제"
    Part 1~6 본 챕터 완료. Part 7 Ch 32·33 손맛이면 충분. **Part 7 Ch 34 의 DPO 는 개념 수준**으로도 시작 가능.

---

## 1. 개념 — 왜 "Self-Improving" 인가

대부분 LLM 제품은 한 번 배포되면 **정지**합니다. 모델은 그대로, 프롬프트는 그대로, 사용자 패턴만 바뀜 → 시간이 갈수록 답이 더 자주 틀림.

캡스톤의 목표: **루프를 닫아서 시간이 갈수록 좋아지는 시스템**.

![Self-improving loop](../assets/diagrams/capstone-self-improving-loop.svg#only-light)
![Self-improving loop](../assets/diagrams/capstone-self-improving-loop-dark.svg#only-dark)

| 단계 | 무엇 | 어디서 왔나 |
|---|---|---|
| ① **User** | 👍/👎 + 자유 코멘트 + 자동 신호 (재질문률) | Ch 29 |
| ② **Assistant** | RAG + Agent + 가드레일 | Part 3·5 |
| ③ **Trace + Log** | trace_id · cost · score 박힘 | Ch 27 |
| ④ **Failure Classifier** | 5층 택소노미 + Judge 점수 | Ch 17·19 |
| ⑤ **DPO Data** | (q, ✓, ✗) 쌍 자동 생성 | Ch 34 |
| ⑥ **Retrain (LoRA)** | 주간 스케줄 + 작은 어댑터 | Ch 33 |
| ⑦ **Eval Gate** | baseline + Δ 통과해야 진행 | Ch 16 |
| ⑧ **Deploy** | adapter swap + 카나리 | Ch 26·30 |

**한 단계만 빠져도 자기 개선이 정지** 합니다. 핵심은 모듈 품질이 아니라 **루프가 닫혀있는가**.

---

## 2. 왜 필요한가 — Static deployment 의 3가지 부패

**① 데이터 분포 drift**. 사용자가 묻는 질문 분포가 매주 바뀜 → 학습 분포에서 멀어짐 → 정확도 감소.

**② 새 사실 등장**. 도메인의 신상품·정책 변경이 RAG 코퍼스에 늦게 반영되면 답이 stale.

**③ 알려진 실패 패턴 누적**. 같은 유형의 잘못된 답을 매주 같은 사용자에게 → 운영팀에 컴플레인 폭주.

루프가 있으면 위 3가지가 **자동 신호** (Ch 27 메트릭) 로 잡혀서 ⑤⑥ 단계에서 데이터에 합류합니다.

---

## 3. 어디에 쓰이는가 — 통합 아키텍처

![캡스톤 아키텍처](../assets/diagrams/capstone-architecture.svg#only-light)
![캡스톤 아키텍처](../assets/diagrams/capstone-architecture-dark.svg#only-dark)

4 레인:

| 레인 | 모듈 | 핵심 챕터 |
|---|---|---|
| **Serving** | API Gateway · Guardrails · Session · Approval Queue | 26 · 28 · 29 |
| **Agent** | LangGraph · Tools · Memory · Model Router | 22~24 · 30 |
| **Knowledge** | Hybrid Retrieval · Reranker · Vector · Citation | 10~12 |
| **Eval · Learn** | Trace · Failure Classifier · Eval Set · LoRA/DPO | 16~19 · 27 · 33·34 |

**한 모듈 = 한 챕터** 로 추적 가능. 전체 모듈을 다 쓸 필요는 없음 — 자기 도메인에 맞춰 선택.

### 유즈케이스 후보 (선택 1)

| 후보 | 데이터 | 자기 개선 신호 |
|---|---|---|
| 사내 IT 헬프데스크 | 위키 · 티켓 로그 | 티켓 재오픈률 |
| 회의록 요약 봇 | 음성·메모 | 사용자 수정 비율 |
| 코드 리뷰 도우미 | git log · PR | comment 채택률 |
| FAQ 자동 응답 | 고객 문의 | 재질문 / 사람 이관 |

**위키·티켓이 있는 사내 IT 헬프데스크가 데이터 가장 풍부** — 추천 시작점.

---

## 4. 최소 예제 — 1주차 골격 (200줄)

```python title="capstone/app.py" linenums="1" hl_lines="11 22 32 38"
from fastapi import FastAPI, HTTPException, Header
from langfuse import observe
import uuid

app = FastAPI()

@app.post("/chat")
@observe()
async def chat(req: ChatRequest, idempotency_key: str = Header(...)):
    trace_id = str(uuid.uuid4())
    if not (await guardrails_input(req.text)):                          # (1)!
        return reject("guardrail")

    history = await session_load(req.user_id)
    docs = await retrieve(req.text, top_k=5)                            # (2)!
    answer = await agent_loop(req.text, history, docs, trace_id)        # (3)!

    if not await guardrails_output(answer):
        return reject("output_policy")
    await session_append(req.user_id, req.text, answer)
    return {"answer": answer, "trace_id": trace_id}

@app.post("/feedback")                                                  # (4)!
async def feedback(req: FeedbackRequest):
    await fb_store.save({
        "trace_id": req.trace_id,
        "thumbs": req.thumbs,        # +1 / -1
        "comment": req.comment,
        "ts": time.time(),
    })
    return {"ok": True}

# 주간 cron
async def weekly_loop():                                                # (5)!
    bad_cases = await classify_failures(window="7d", threshold=-1)
    pairs = await build_dpo_pairs(bad_cases)                            # (6)!
    if len(pairs) < 200:
        return                                                          # 데이터 부족 → 다음 주
    adapter = await train_lora_dpo(pairs)
    score = await eval_against(adapter, eval_set="hold_out_v3")
    if score >= baseline + 0.03:                                        # (7)!
        await deploy_canary(adapter, percent=10)
```

1. 입력 가드레일 (Ch 28). hard fail (안전·moderation) 직렬, 나머지 optimistic 병렬.
2. RAG hybrid retrieval (Ch 12) + reranker.
3. LangGraph state machine (Ch 23). interrupt_before 로 high-risk 액션 게이트.
4. 사용자 피드백을 trace_id 와 묶어 저장 — 루프의 시작점.
5. 주간 cron. 실패 케이스 모음 → DPO 쌍 → 학습 → 평가 게이트.
6. (q, ✓, ✗) 쌍 생성: 👎 받은 답 = rejected, Judge 가 다시 생성한 좋은 답 = chosen.
7. **+3pt 미달이면 배포 안 함**. 회귀 방지의 핵심 게이트.

---

## 5. 실전 — 8주 진행 가이드

| 주 | 활동 | 산출물 |
|---|---|---|
| 1 | 유즈케이스 결정 · 데이터 수집 · 8블록 구조도 | 문제 정의서 + 아키텍처 SVG |
| 2 | RAG 파이프라인 (Ch 11~14) | mini_rag.py + 평가셋 100건 (Ch 16) |
| 3 | LangGraph Agent + 가드레일 7종 | 첫 동작 데모 |
| 4 | Observability 연결 + 첫 사용자 5명 배포 | Langfuse 대시보드 |
| 5 | 피드백 endpoint + 실패 분류기 (Ch 19) | 1주 로그 분석 보고 |
| 6 | DPO 데이터 생성 + LoRA 첫 학습 (Ch 33) | adapter v1 + eval 점수 |
| 7 | 주간 자동화 (cron + eval gate) | 자동 배포 워크플로우 |
| 8 | 1주 추가 사용자 테스트 + 회고 | 최종 보고서 |

**5명의 실사용자** 가 1주 사용 = 보통 200~500 trace. DPO 학습에 필요한 (✓, ✗) 쌍 100~300 만들기에 충분.

### 평가 — baseline · 개선 후 · 회귀

| 메트릭 | 측정 | 목표 |
|---|---|---|
| Domain accuracy | hold-out 100건 (Ch 16) | baseline +3pt |
| Latency p95 | Ch 27 메트릭 | baseline 이하 |
| Cost / req | Ch 27 메트릭 | baseline ±10% |
| Guardrail trigger | Ch 28 | 회귀 없음 |
| Regression set | 이전 통과 케이스 | 100% 유지 |
| User CSAT | 👍 / (👍+👎) | baseline +5% |

**6 메트릭 모두 통과** 해야 새 adapter 배포. 한 메트릭이라도 회귀하면 보류.

### DPO 데이터 자동 생성 패턴

```python title="capstone/build_pairs.py"
async def build_dpo_pairs(bad_cases):
    pairs = []
    for case in bad_cases:
        rejected = case["answer"]                       # 👎 받은 답
        # Judge LLM 으로 더 좋은 답 생성
        chosen = await call_llm("claude-opus-4-7",
            prompt=f"다음 질문에 더 정확하고 정중하게:\n{case['q']}")
        # 검증: rejected 와 의미 차이 있나?
        if similarity(rejected, chosen) > 0.9:           # 너무 비슷하면 학습 신호 약함
            continue
        pairs.append({
            "prompt": case["q"],
            "chosen": chosen,
            "rejected": rejected,
        })
    return pairs
```

---

## 6. 자주 깨지는 포인트

- **루프가 안 닫힘**. 피드백은 모았는데 학습 단계가 수동 → 한 달 뒤 잊혀짐. **주간 cron + 알람** 까지 자동화해야 진짜 self-improving.
- **평가셋 누출**. 학습 데이터에 평가셋이 섞여 들어감 → 학습 점수만 좋고 실전 회귀. 학습 시작 전 hash 비교 자동.
- **자기 강화 편향**. Judge LLM 으로 ✓ 를 만들면 Judge 의 편향이 학습됨 → 한 방향으로 편향 강화. **사람 검수 sample 5%** 로 견제.
- **ROI 음수**. 라벨링·GPU·운영 비용 vs 절감이 안 맞으면 멈춰야 함. Ch 32 ROI 계산 분기마다 재검토.
- **안전 회귀**. DPO 후 거절 정책이 약해짐 → 가드레일 우회 답변 출현. **safety regression 별도 평가셋** 필수 (Ch 28).
- **adapter 누적**. 매주 새 adapter → 1년이면 52개. 어느 게 최선인지 추적 불가. **버전 관리 + 자동 롤백 정책**.
- **5명 사용자 데이터로 일반화 가정**. 5명 패턴이 100명 패턴이 아님. 조심스러운 배포 (10% 카나리) 후 점진 확대.
- **Judge 가 문제이지만 무시**. Failure classifier 정확도가 60% 면 학습 데이터 40% 가 노이즈. Judge 정확도 별도 평가셋 (Ch 17).

---

## 7. 운영 체크리스트

- [ ] 폐쇄 루프 8 단계 모두 자동화 (수동 단계 0)
- [ ] 모든 trace 가 trace_id · user_id · model_version · adapter_version 박힘
- [ ] 학습 데이터 ↔ 평가셋 누출 자동 감지
- [ ] DPO chosen 의 Judge 정확도 별도 측정 (목표 80%+)
- [ ] 6 메트릭 (정확도 · p95 · cost · guardrail · regression · CSAT) 통과 게이트
- [ ] safety regression 평가셋 (가드레일 7종 포함)
- [ ] adapter 버전 관리 + 즉시 롤백 가능
- [ ] 카나리 배포 (10% → 50% → 100%) + 단계별 알람
- [ ] 주간 메트릭 리포트 (자동 발송)
- [ ] 1년 ROI 양수 유지 · 분기마다 재검토

---

## 8. 제출물 체크리스트

| # | 항목 | 어디 |
|---|---|---|
| ① | **문제 정의서** — 어떤 Assistant · 누구에게 · 왜 | 1주차 |
| ② | **아키텍처 SVG** — 모듈 → 챕터 매핑 | 1주차 |
| ③ | **데이터 구성** — RAG 코퍼스 · 평가셋 100+ | 2주차 |
| ④ | **Prompt/RAG/Agent 전략** — 각 블록 구현 코드 | 2~3주차 |
| ⑤ | **가드레일 7종 적용 표** | 3주차 |
| ⑥ | **평가 결과** — baseline vs after-DPO 비교 | 7주차 |
| ⑦ | **실패 케이스 분석 20건+** — taxonomy 분류 | 5주차 |
| ⑧ | **운영 고려사항** — 비용 · 지연 · 안전 분석 | 4·6주차 |
| ⑨ | **자기 개선 루프 설계** — 주기 · 트리거 · 게이트 · 롤백 | 7주차 |

**8주차 발표 (30분)**:
- 데모 5분 (실시간)
- 아키텍처 5분
- 평가 결과 10분 (회귀 포함)
- 회고 10분 (무엇이 안 됐고 다음 분기에 무엇을)

---

## 책 마무리 — 어디로 가는가

캡스톤을 완주하면 다음 단계는 본인의 도메인입니다.

**확장 방향**:

- **멀티 에이전트** (Ch 25) 로 분기 — 한 agent 가 24/7 운영, 다른 agent 가 retraining
- **Constitutional AI** (Ch 34) 로 라벨 비용 ↓ — 단 인간 검수 유지
- **Online learning** — 주간 → 일간 → 실시간 (위험·비용 ↑)
- **Multi-modal** — 이미지·음성·문서 (Ch 14)

**책에서 다루지 않은 것**:
- 분산 학습 (수십~수백 GPU)
- 자체 Pretraining
- Agent simulation environments (CS329A 의 본격 영역)
- AGI 토론

이 책의 가정은 **"외부 모델을 잘 쓰는 엔지니어"** 입니다. 그 자리에서 운영 가능한 가장 깊은 곳까지 왔다고 생각하고, 다음 모험은 본인의 도메인 데이터 + 사용자 피드백 + 끊임없는 측정으로.

> "The best way to predict the future is to build it."

---

## 원전

- Stanford CS329A — *Self-Improving AI Agents* Final Project (영감)
- Stanford CS329A Lec 7 — *Open-Ended Evolution of Self-Improving Agents*
- Stanford CS329A Lec 13 — *Agentic Frameworks for SWE* (CodeMonkeys 등)
- Rafailov et al. (2023) *DPO*
- Bai et al. (2022) *Constitutional AI*
- 책 전체 Ch 1~34
