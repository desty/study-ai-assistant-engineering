# 학습 내용 — v2

**AI Assistant Engineering** — LLM을 "API로 호출하는 법"을 넘어, **스스로 추론하고 도구를 쓰고 개선되는 어시스턴트**를 기획·구현·운영하는 전 과정. 대상은 **초보부터 엔터프라이즈 프로덕션**까지.

!!! quote "커리큘럼의 축"
    Stanford **CME 295**(LLM 이론) + Stanford **CS329A**(Self-Improving Agents 연구 프런티어) + **Anthropic / OpenAI / LangGraph** 공식 엔지니어링 가이드를 하나의 흐름으로 엮습니다. 각 챕터 끝에는 원전 링크 — 이 책은 요약본이 아니라 **읽는 순서의 내비게이션**.

## v1 → v2 변경점

`_research/` 아카이브를 기반으로 공백을 메우고 순서를 바로잡은 개정판.

| # | 변경 | 근거 |
|---|---|---|
| 1 | Ch "임베딩과 검색" **Part 1 → Part 3**로 이동 | API 호출도 안 해본 상태에서 임베딩은 추상적. RAG 직전이 자연스러움 |
| 2 | **스트리밍 · UX** 챕터 신설 (Part 2) | 챗봇 체감 품질의 핵심. 공백이었음 |
| 3 | **Advanced RAG** 챕터 신설 (Part 3) | HyDE · Self-RAG · GraphRAG · Agentic RAG — 업계 표준으로 올라옴 |
| 4 | **멀티모달 RAG** 절 신설 (Part 3) | 문서 레이아웃·비전이 RAG 품질에 직결 |
| 5 | **LLM-as-a-Judge** 챕터 신설 (Part 4) | CME 295 Lec 8. v1에 누락 |
| 6 | **추론 품질 높이기** 챕터 신설 (Part 4) | CoT · self-consistency · best-of-N · verifier. CS329A Lec 2–3 |
| 7 | **Agent 메모리** 챕터 신설 (Part 5) | CS329A Lec 14 + LangGraph thread/cross-thread. v1에 없었음 |
| 8 | **Agent 패턴** 챕터 강화 (Part 5) | Anthropic 5패턴 + OpenAI 매니저/탈중앙 — 업계 표준 어휘 |
| 9 | **가드레일 7종** 챕터 (Part 6) | OpenAI 가이드 표를 엔터프라이즈 체크리스트로 이식 |
| 10 | **비용 · 지연 최적화** 챕터 신설 (Part 6) | 프롬프트 캐싱 · 모델 라우팅 · 배치 — 프로덕션 필수 |

**총 챕터 수**: v1 26 → **v2 34**. 12주 과정은 14주로 확장 권장 (§8).

---

## 1. 학습 로드맵

![7부 + 캡스톤 로드맵](../assets/diagrams/roadmap.svg#only-light)
![7부 + 캡스톤 로드맵](../assets/diagrams/roadmap-dark.svg#only-dark)

!!! info "순서의 의미"
    **평가(Part 4)를 Agent(Part 5) 앞에** 두는 건 의도적입니다. Anthropic 가이드의 권고 — *"단순 프롬프트에서 시작해 평가로 최적화하고, 단순 해결책으로 안 될 때만 에이전트로 올려라"* — 와 정확히 일치합니다.

---

## 2. 전체 목차 (34챕터)

### Part 1. 입문 — LLM과 AI Assistant의 기초 *(3장)*

| # | 챕터 | 핵심 | 참고 |
|---|---|---|---|
| 1 | 왜 모델이 필요한가 | 규칙 vs 모델. **OpenAI의 3판단 기준** (복잡 결정 · 유지 어려운 규칙 · 비정형 데이터) | OpenAI Practical Guide |
| 2 | LLM이란 무엇인가 | 토큰·컨텍스트·next-token·hallucination | CME 295 Lec 1–3 |
| 3 | AI Assistant 시스템 개요 | 입력→이해→검색→생성→검증→저장→모니터링→휴먼 핸드오프 | — |

**산출물**: 용어집 · 코드 vs 모델 판단표 · Assistant 구조도 1장

---

### Part 2. Python으로 LLM 다루기 *(5장)*

| # | 챕터 | 핵심 |
|---|---|---|
| 4 | OpenAI / Anthropic API 시작 | 기본 호출, system/user, 에러·재시도 |
| 5 | 프롬프트 엔지니어링 + CoT 기초 | 역할 부여, few-shot, **Chain-of-Thought**, 모르면 모른다 |
| 6 | 구조화 출력 | JSON Schema · Pydantic · 검증 · fallback |
| 7 | **스트리밍과 UX** 🆕 | 토큰 스트림 · 부분 렌더링 · 취소 · 타임아웃 |
| 8 | Tool Calling 기초 | function calling · 파라미터 생성 · 안전 실행 |

**산출물**: Python 예제 모음 · 구조화 출력 PoC · 첫 Tool Calling 예제

---

### Part 3. RAG — 외부 지식을 붙이는 법 *(6장)*

| # | 챕터 | 핵심 |
|---|---|---|
| 9 | 왜 RAG가 필요한가 | 최신성 · grounding · 파인튜닝과의 차이 |
| 10 | **임베딩과 벡터 검색 기초** ← Part 1에서 이동 | 코사인 · MMR · 벡터DB의 역할 |
| 11 | RAG 파이프라인 전체 흐름 | 수집·chunking·embedding·retrieval·generation·citation |
| 12 | 검색 품질 개선 | chunk size · top-k · metadata filter · **hybrid (BM25 + dense)** · reranking |
| 13 | **Advanced RAG** 🆕 | **HyDE · Self-RAG · GraphRAG · Agentic RAG** |
| 14 | LangChain 실전 + 멀티모달 RAG 🆕 | retriever·chain·prompt template. **PDF 레이아웃·비전 임베딩** 짧게 |

**산출물**: 문서 QA RAG PoC · 검색 실패 분석표 · 파이프라인 다이어그램

---

### Part 4. 평가 · 추론 품질 · 디버깅 *(5장)*

| # | 챕터 | 핵심 |
|---|---|---|
| 15 | 무엇을 평가해야 하는가 | retrieval · generation · end-to-end · 오프라인 vs 온라인 |
| 16 | 평가셋 만들기 | gold set · edge cases · coverage · 분류 |
| 17 | **LLM-as-a-Judge** 🆕 | 심판 모델 설계 · **편향과 보정** · 휴먼 캘리브레이션 |
| 18 | **추론 품질 높이기** 🆕 | **Chain-of-Thought 심화 · Self-Consistency · Best-of-N · Verifier 모델** |
| 19 | 실패 분석과 디버깅 | prompt/retrieval/data/ranking/generation/tool 실패 유형 분리 |

**산출물**: 평가 기준서 · 평가셋 초안 · 실패 분석 리포트

---

### Part 5. Agent & LangGraph *(6장)*

| # | 챕터 | 핵심 |
|---|---|---|
| 20 | Agent란 무엇인가 | **Model · Tool · Instruction 3요소** (OpenAI). LLM app과 Agent 구분 |
| 21 | **Agent 패턴** 🆕 | **Anthropic 5패턴** (chaining · routing · parallelization · orchestrator-workers · evaluator-optimizer) + **OpenAI 2패턴** (manager · decentralized) |
| 22 | Tool Use 실전 | Data · Action · Orchestration 툴 · **ACI(Agent-Computer Interface) 설계** · 승인 기반 실행 |
| 23 | LangGraph — 상태 그래프 | StateGraph · node · edge · conditional edge · reducer · checkpointer · interrupt |
| 24 | **Agent 메모리** 🆕 | **thread-scoped / cross-thread store** · MemGPT · 에피소딕 · KV 캐시 |
| 25 | 멀티 에이전트와 역할 분리 | planner/executor · researcher/writer · verifier/responder · 과도한 복잡성의 위험 |

**산출물**: Tool-using Assistant PoC · LangGraph flow diagram · Agent 실패 시나리오 문서

---

### Part 6. 운영형 AI Assistant — 프로덕션 *(5장)*

| # | 챕터 | 핵심 |
|---|---|---|
| 26 | Production 아키텍처 | 요청 흐름 · 모델/검색 분리 · 세션·메모리 · sync/async · rate limit |
| 27 | 관측성과 운영 | logging · tracing · **prompt/데이터셋 버전 관리** · latency/cost/quality 지표 · LangSmith/Langfuse |
| 28 | **가드레일 7종** 🆕 | **relevance · safety · PII · moderation · tool · rules-based · output validation** (OpenAI 표) |
| 29 | 휴먼 개입 설계 | **실패 임계치** · **고위험 액션** · escalation · 감사 로그 |
| 30 | **비용 · 지연 최적화** 🆕 | **프롬프트 캐싱** · 모델 라우팅(Haiku↔Sonnet↔Opus) · 배치 API · 컨텍스트 압축 |

**산출물**: 운영 아키텍처 문서 · 관측성 지표표 · 안전성/보안 가이드 · 비용 시뮬레이터

---

### Part 7. 모델 & 파인튜닝 *(4장)*

| # | 챕터 | 핵심 |
|---|---|---|
| 31 | 모델 아키텍처 개요 | Transformer · attention · instruction tuning · base vs chat · open vs hosted |
| 32 | 파인튜닝이 필요한 경우와 아닌 경우 | Prompt / RAG / 구조화 출력이 먼저. 데이터 요구량과 품질 |
| 33 | LoRA / QLoRA 실전 (Colab) | PEFT · QLoRA · 데이터 포맷 · 학습 루프 |
| 34 | 소형모델 · 증류 · DPO 개요 | latency/cost · distillation · **DPO** (SFT→DPO→RLHF 맥락) |

**산출물**: 파인튜닝 필요성 검토서 · Colab 노트북 · 소형모델 적용 아이디어

---

### 캡스톤 — Self-Improving Assistant

사용자 피드백 로그 수집 → 실패 케이스 자동 분류 → **DPO 데이터로 변환 → 주간 재학습 루프**. CS329A 최종 프로젝트의 미니어처.

**제출물**: 문제 정의 · 아키텍처 · 데이터 구성 · Prompt/RAG/Agent 전략 · 평가 결과 · 실패 분석 · 운영 고려사항 · 자기 개선 루프 설계

---

## 3. 참고 자료 지도

=== "대학 강의"

    - [CS329A — Self-Improving AI Agents (Stanford)](https://cs329a.stanford.edu/){ target=_blank } — 에이전트 연구 프런티어
    - [CME 295 — Transformers & LLMs (Stanford)](https://cme295.stanford.edu/syllabus/){ target=_blank } — 이론 골격

=== "벤더 엔지니어링 가이드"

    - **Anthropic** [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents){ target=_blank } — 5패턴
    - **OpenAI** [A Practical Guide to Building Agents (PDF)](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf){ target=_blank } — 3요소·가드레일 7종
    - **LangGraph** 공식 docs — StateGraph·checkpointer·memory
    - Claude Cookbook · OpenAI Cookbook · LangSmith/Langfuse 튜토리얼

=== "최신 논문 (챕터에서 합류)"

    - **RAG**: Self-RAG · HyDE · GraphRAG
    - **Reasoning**: Chain-of-Thought · Self-Consistency · Tree of Thoughts · Let's Verify Step by Step · Archon
    - **Alignment**: InstructGPT(RLHF) · DPO · Constitutional AI
    - **Agents**: ReAct · Reflexion · Voyager · SWE-agent · MemGPT · CodeMonkeys
    - **Efficient FT**: LoRA · QLoRA

!!! note "원전 우선 원칙"
    이 책은 요약을 복붙하지 않습니다. 각 챕터 끝에 원전 링크 — 이 책은 **"어떤 순서로 · 어떻게 읽을지"** 의 내비게이션.

## 4. Stanford 강의와의 상세 매핑

| CME 295 | 우리 챕터 |
|---|---|
| Lec 1–3 (Transformer·LLM) | Part 1 Ch 2, Part 7 Ch 31 |
| Lec 3 (prompting/ICL) | Part 2 Ch 5 |
| Lec 4 (training, quantization, LoRA) | Part 7 Ch 33 |
| Lec 5 (tuning, RLHF, DPO) | Part 7 Ch 34 |
| Lec 6 (reasoning) | Part 4 Ch 18 |
| Lec 7 (RAG, function calling, ReAct) | Part 3 · Part 5 |
| Lec 8 (LLM-as-a-Judge) | **Part 4 Ch 17** |

| CS329A | 우리 챕터 |
|---|---|
| Lec 2–3 (test-time compute, verification) | **Part 4 Ch 18** |
| Lec 4–5 (ReAct, multi-step) | Part 5 Ch 20–22 |
| Lec 14 (memory) | **Part 5 Ch 24** |
| Lec 13 (SWE agents, CodeMonkeys) | Part 5 Ch 25 + 캡스톤 |
| Lec 17 (long-horizon eval) | Part 4 Ch 15 |
| Lec 7 (self-evolution) · Final project | **캡스톤** |

---

## 5. 선수 지식

<div class="infocards" markdown>

<div class="card" markdown>
#### :material-language-python: Python
함수·클래스·async 기본. 가상환경·pip.
</div>

<div class="card" markdown>
#### :material-console: Shell
기본 명령어·환경변수. Colab만 쓸 거면 생략 가능.
</div>

<div class="card" markdown>
#### :material-function: 수식 읽기
행렬 곱·확률·softmax 수준. Part 7 전에 Part 1로 충분.
</div>

<div class="card" markdown>
#### :material-brain: ML 기초
있으면 빠르게 읽히지만 **필수 아님**.
</div>

</div>

## 6. 완주 후 가질 능력

체크리스트로 확인:

- [ ] 문제를 받고 **코드 / Prompt / RAG / Agent / Fine-tuning** 중 무엇으로 풀지 판단한다
- [ ] Assistant를 **입력·이해·검색·생성·검증·저장·모니터링·휴먼 핸드오프** 블록으로 분해·설계한다
- [ ] RAG 파이프라인의 **실패 원인**을 prompt/retrieval/data/ranking/generation 레벨에서 분리 진단한다
- [ ] **Anthropic 5패턴·OpenAI 2패턴**을 현실 문제에 대응시킨다
- [ ] **LangGraph**로 영속·인터럽트·메모리가 있는 멀티 스텝 워크플로우를 만든다
- [ ] **LLM-as-a-Judge**와 **self-consistency·best-of-N·verifier**로 출력 품질을 올린다
- [ ] **가드레일 7종**을 체크리스트로 운영 시스템에 적용한다
- [ ] **프롬프트 캐싱·모델 라우팅·배치**로 비용·지연을 체계적으로 낮춘다
- [ ] 파인튜닝이 진짜 필요한지 판단하고, 필요하면 **LoRA/QLoRA**를 Colab에서 돌린다
- [ ] 사용자 피드백 로그 → 실패 분류 → **DPO 데이터 → 재학습**의 자기 개선 루프를 설계한다

## 7. 평가 비중 (권장)

- 주간 과제 30% · 실습 PoC 30% · 중간 설계 리뷰 15% · 최종 프로젝트 25%

**통과 기준**:

- **입문**: 구조도·용어 설명 가능
- **기본**: RAG · 구조화 출력 · 평가셋 제출
- **심화**: Agent · 운영 설계 · 가드레일 · 개선 리포트
- **엔터프라이즈**: 캡스톤(Self-Improving Assistant) 완성

## 8. 14주 운영 예시 (v2)

v1의 12주에서 2주 추가. 신설 챕터 수용.

| 주 | 내용 |
|---|---|
| 1 | Ch 1–2: 왜 모델 · LLM 기초 |
| 2 | Ch 3 · 4: Assistant 구조 · API 첫 호출 |
| 3 | Ch 5 · 6: 프롬프트+CoT · 구조화 출력 |
| 4 | Ch 7 · 8: **스트리밍·UX** · Tool Calling |
| 5 | Ch 9 · 10: RAG 필요성 · **임베딩·벡터검색** |
| 6 | Ch 11 · 12: 파이프라인 · 검색 품질 |
| 7 | Ch 13 · 14: **Advanced RAG** · LangChain+멀티모달 |
| 8 | Ch 15 · 16: 평가 기준 · 평가셋 |
| 9 | Ch 17 · 18: **LLM-as-Judge** · **추론 품질** |
| 10 | Ch 19 · 20: 실패 분석 · Agent란 |
| 11 | Ch 21 · 22: **Agent 패턴** · Tool Use |
| 12 | Ch 23 · 24: LangGraph · **Agent 메모리** |
| 13 | Ch 25 · 26 · 27: 멀티 에이전트 · 운영 아키텍처 · 관측성 |
| 14 | Ch 28 · 29 · 30 · 31–34 개요 · 캡스톤 리뷰 |

Part 7(파인튜닝)은 수강생 필요에 따라 **심화 옵션**으로 분리하고, 14주 본과정은 Part 6까지 다루는 것을 기본으로 한다. 전체 34챕터를 다 돌리려면 16–18주 권장.

## 9. 우선순위 가이드

**반드시 먼저** · 코드 vs 모델 · LLM 기초 · 구조화 출력 · RAG · 평가 · **Agent 패턴·가드레일**

**그다음** · Agent 고도화 · 운영 아키텍처 · 관측성 · **비용·지연 최적화** · **Agent 메모리**

**나중** · 파인튜닝 · 증류 · 소형모델

## 10. 한 줄 요약

> 모델을 깊게 연구하는 것보다, 실제 업무용 AI Assistant를 이루는 블록을 이해하고  
> **Prompt / RAG / Agent / 평가 / 운영 / 가드레일**을 구분해서 설계할 수 있게 만드는 것.

---

[:material-arrow-right-box: Part 1 시작하기](../part1/01-why-model.md){ .md-button .md-button--primary }
[:material-cog: 학습 시스템 보기](system.md){ .md-button }
