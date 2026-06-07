# Ch 13. Advanced RAG

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part3/ch13_advanced_rag.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **HyDE** (Hypothetical Document Embeddings) — 쿼리 대신 가상 답변을 임베딩
    - **Self-RAG** — LLM이 **검색 필요성·결과 품질** 을 스스로 판단
    - **GraphRAG** — 엔티티 그래프 기반 추론 (개념 소개)
    - **Agentic RAG** — Part 5 에이전트 루프 안에 검색 도구
    - **Sufficient Context** (2026 추가) — '관련성' 이 아니라 '충분성' 으로 멈춤·기권 판단
    - Query Rewriting · Multi-query · Recursive retrieval
    - "Advanced 라고 다 좋은 건 아니다" — 비용·지연·복잡도 트레이드오프

!!! quote "전제"
    [Ch 12](12-retrieval-quality.md) 까지 — hybrid · reranker · metadata filter 익숙해진 상태.

---

## 1. 개념 — Basic RAG 로 안 되는 케이스

Ch 11~12 의 파이프라인은 **80%의 케이스**를 커버합니다. 하지만 다음은 기본 RAG 로 어려움:

| 실패 케이스 | 예시 | 해결 변형 |
|---|---|---|
| **짧고 모호한 쿼리** | "AI는?" · "정책?" | **HyDE** · Query Rewriting |
| **검색 없이 답할 수 있는 질문도 전부 검색함** | "안녕" → RAG 낭비 | **Self-RAG** |
| **여러 정보를 엮어야 하는 질문** | "A 팀 × B 프로젝트의 예산 담당자는?" | **GraphRAG** |
| **검색 + 계산 + 재검색 필요** | "작년 매출 대비 올해 성장률?" | **Agentic RAG** |

각 변형은 **한 지점의 한계** 를 풀려는 것. **조합해서** 쓰는 경우가 많습니다.

![Advanced RAG 4 변형](../assets/diagrams/ch13-rag-variants.svg#only-light)
![Advanced RAG 4 변형](../assets/diagrams/ch13-rag-variants-dark.svg#only-dark)

---

## 2. 왜 필요한가 — 기본 RAG 의 3가지 구조적 한계

1. **쿼리 ↔ 문서 표현 차이** — 사용자는 짧은 쿼리("환불?") 쓰고 문서는 긴 설명. 임베딩 거리가 멀어짐
2. **검색이 항상 필요하다는 가정** — 잡담·수식 계산·단순 인사는 검색 낭비
3. **한 번의 검색으로 끝난다는 가정** — 복합 질문은 단일 검색으로 부족

각 변형은 이 중 하나를 건드립니다.

---

## 3. 어디에 쓰이는가

| 기법 | 가장 큰 효과 | 비용 |
|---|---|---|
| **HyDE** | 짧은 쿼리 · 전문 도메인 | LLM 호출 1회 추가 |
| **Self-RAG** | 일반 챗봇 · 불필요한 검색 줄임 | LLM 호출 1~2회 추가 |
| **GraphRAG** | 다중 엔티티 질문 · 요약 | 그래프 인덱스 구축 큼 |
| **Agentic RAG** | 복합 질문 · 외부 툴 필요 | 여러 루프 (Part 5) |

---

## 4. HyDE — 최소 예제

**아이디어**: 짧은 쿼리 임베딩은 노이즈가 큼. **가짜 답변** 을 LLM 으로 만들어 그 긴 텍스트를 임베딩 → 정확한 문서를 더 잘 찾음.

![HyDE 상세](../assets/diagrams/ch13-hyde-detail.svg#only-light)
![HyDE 상세](../assets/diagrams/ch13-hyde-detail-dark.svg#only-dark)

```python title="hyde.py" linenums="1" hl_lines="7 8 9 10 11 12"
from anthropic import Anthropic
from openai import OpenAI

anthropic = Anthropic()
openai = OpenAI()

def hyde_search(query: str, col, k: int = 5):
    # 1) LLM에 가상 답변 생성 요청
    r = anthropic.messages.create(
        model="claude-haiku-4-5", max_tokens=256,
        system="다음 질문에 대한 답변을 사실 기반으로 작성하세요. 정확하지 않아도 괜찮습니다. 4문장 이내.",
        messages=[{"role": "user", "content": query}],
    )
    hypothetical = r.content[0].text

    # 2) 가상 답변을 임베딩
    emb = openai.embeddings.create(
        model="text-embedding-3-small",
        input=[hypothetical],
    ).data[0].embedding

    # 3) 가상 답변의 임베딩으로 실제 문서 검색
    res = col.query(query_embeddings=[emb], n_results=k)
    return res

# 사용
results = hyde_search("환불 정책?", col)
```

**효과**: 짧은 쿼리보다 **20~40% recall 향상** (도메인 따라 다름).

**함정**: LLM 이 **틀린 답을 만들어내면** 엉뚱한 방향으로 검색 → §6 참고.

---

## 5. 실전 튜토리얼

### 5.1 Query Rewriting / Expansion

HyDE의 사촌: 쿼리를 LLM 으로 **확장·변형** 후 multi-query 검색.

```python title="query_expansion.py" linenums="1"
def expand_query(q: str) -> list[str]:
    r = anthropic.messages.create(
        model="claude-haiku-4-5", max_tokens=256,
        system="사용자 쿼리를 의미가 같은 다른 표현 3개로 다시 써주세요. JSON 배열만.",
        messages=[{"role": "user", "content": q}],
    )
    import json
    return json.loads(r.content[0].text)

# 각 변형으로 검색 후 RRF 병합
variants = [query] + expand_query(query)
ranked_lists = [search(v) for v in variants]
final = rrf_merge(ranked_lists)   # Ch 12의 RRF 재사용
```

### 5.2 Self-RAG — 검색 필요성 판단

```python title="self_rag.py" linenums="1" hl_lines="4 16"
def self_rag(query: str) -> str:
    # 1) 검색이 필요한지 LLM에 판단
    decision = anthropic.messages.create(
        model="claude-haiku-4-5", max_tokens=10,
        system="""사용자 질문에 답하기 위해 외부 문서 검색이 필요한가?
YES 또는 NO만 답하세요.""",
        messages=[{"role": "user", "content": query}],
    ).content[0].text.strip()

    context = ""
    if decision.startswith("YES"):
        # 2) 검색 + 결과 품질 평가
        retrieved = search(query, k=5)
        context = format_context(retrieved)

        # 3) LLM이 스스로 결과가 충분한지 평가
        quality = anthropic.messages.create(
            model="claude-haiku-4-5", max_tokens=10,
            system=f"""아래 검색 결과로 질문에 답할 수 있나?
{context}
YES/NO""",
            messages=[{"role": "user", "content": query}],
        ).content[0].text.strip()
        if quality.startswith("NO"):
            # 추가 전략: query rewrite 후 재검색, 또는 "모른다" 응답
            return "검색 결과가 충분치 않아 담당자에게 연결드리겠습니다."

    # 4) 최종 답 생성 (context 유무에 따라)
    r = anthropic.messages.create(
        model="claude-haiku-4-5", max_tokens=512,
        system=(context or "일반 상식 기반으로 답하세요."),
        messages=[{"role": "user", "content": query}],
    )
    return r.content[0].text
```

**이득**: "안녕" 같은 잡담에 RAG 낭비 안 함. 검색 결과 부족 시 담당자 연결.

**비용**: LLM 호출 2~3배. **지연·비용 증가** — 모든 쿼리에 쓰지 말고 **게이트 조건** 을 명확히.

### 5.3 Multi-step / Recursive Retrieval

복합 질문은 **한 번 검색 + 추가 검색** 으로 나눔:

```
Q: "작년 매출 대비 올해 성장률?"

1단계: "작년 매출" 검색 → 10B원 찾음
2단계: "올해 매출" 검색 → 13B원 찾음
3단계: LLM이 계산 → 30%
```

구현은 **Part 5 Agent** 의 영역. 여기선 개념만.

### 5.4 GraphRAG — 개념 소개

Microsoft (2024) 의 GraphRAG:

1. 문서에서 **엔티티·관계** 를 먼저 추출 (LLM으로)
2. **지식 그래프** 로 저장 (Neo4j · NetworkX)
3. 질문 시 **그래프 탐색 + 벡터 검색** 병행
4. 다중 홉 질문 ("X의 상사의 상사는?") 에 강함

**장점**: 구조적 질문에 뛰어남.  
**단점**: **인덱스 구축 비용** 이 Basic RAG 의 10~100배. 엔티티 추출 LLM 호출이 대규모.

**권장**: 소규모 도메인 (수천 문서) · 요약 · 다중홉 질문이 핵심 유즈케이스일 때만. 일반 FAQ 봇은 오버킬.

### 5.5 Agentic RAG — Part 5 로의 다리

에이전트(Part 5) 가 **검색을 툴로 갖고** 여러 번 반복 호출:

```
Agent 루프:
  1. 사용자 질문 받음
  2. "이걸 답하려면 뭘 알아야 하지?" 판단
  3. search_policy(query="환불") 툴 호출
  4. 결과 보고 "아직 부족" 판단 → search_database(...)
  5. 충분하면 최종 답변 생성
```

Part 2 Ch 8 Tool Calling + Part 5 Agent 패턴의 조합. **복합 질문** · **다중 도메인** 에 강함.

### 5.6 Sufficient Context — '충분한가' 를 멈춤 신호로

§5.2 Self-RAG 는 "검색 결과로 답할 수 있나?" 를 LLM 에게 즉석에서 물었습니다. 구글 연구([Sufficient Context, ICLR 2025](https://arxiv.org/abs/2411.06037){target=_blank})는 이 직관을 **별도의 신호** 로 떼어내 형식화합니다.

핵심은 **relevant ≠ sufficient** 의 구분입니다.

- **관련 있음(relevant)** — 검색된 문서가 주제와 관련됨
- **충분함(sufficient)** — 그 문서만으로 **확정적 답이 가능함**

관련 문서를 찾아도 핵심 사실이 빠져 있으면 그건 충분하지 않습니다. (HTTP 404 일반 설명은 "Room 404 가 어느 연구소에 있었나" 에 관련은 있지만 불충분.)

!!! danger "RAG 의 역설 — 컨텍스트가 기권을 망친다"
    컨텍스트를 붙이면 모델이 **과신** 해서, 모를 때 기권(abstain) 하는 대신 자신있게 환각합니다. 한 실험에서 **Claude 3.5 Sonnet 의 기권율이 RAG 적용 시 84% → 52% 로 떨어졌습니다.** 검색을 더 줬더니 "모른다" 고 말할 능력이 오히려 약해진 것 — 위 실수 3 의 Self-RAG 오판과 같은 뿌리입니다.

이를 보정하는 게 **selective generation** 입니다. 두 신호를 묶어 답할지·기권할지 결정합니다.

1. **자기평가 confidence** — 답을 여러 번 샘플링한 뒤 모델이 정오를 스스로 평가(`P(True)`)
2. **sufficient context 라벨** — 충분성 판정기(autorater)의 이진 신호. 구글은 Gemini 1.5 Pro 프롬프팅만으로 **~93% 정확도** 를 얻었습니다(파인튜닝 불필요).

두 신호를 로지스틱 회귀로 결합해 "환각 확률" 을 예측하고, 임계값을 넘으면 기권합니다. **정답 라벨 없이** 학습되고, 답한 문항의 정답 비율을 2~10% 끌어올립니다.

**제품화 (2026)**: 구글은 이 판정기를 [Gemini Enterprise 의 Agentic RAG 루프 정지조건](https://research.google/blog/unlocking-dependable-responses-with-gemini-enterprise-agent-platforms-agentic-rag/){target=_blank}(Sufficient Context Agent)으로 넣었습니다. §5.5 의 "충분하면 답변 / 부족하면 재검색" 판단을, 즉석 YES/NO 대신 **학습된 신호** 로 바꾼 셈입니다.

---

## 6. 자주 깨지는 포인트

!!! warning "실수 1. 'Advanced' 무조건 적용"
    HyDE · Self-RAG 는 **LLM 호출을 추가** 합니다. 기본 RAG 가 잘 되는 쿼리에 쓰면 **비용·지연만** 늘고 품질은 동일.  
    **대응**: A/B 평가 (Part 4) 로 **실제 개선 측정**. 개선 < 5% 면 보류.

!!! warning "실수 2. HyDE 의 환각 쿼리"
    가상 답변이 **틀리면** 엉뚱한 방향으로 검색 → **오답으로 잘못 유도**.  
    **대응**: (a) 가상 답변 길이 짧게 (2~3문장), (b) 원 쿼리 임베딩과 **함께** 검색 (dense + HyDE RRF), (c) 실패율 주기적 측정.

!!! warning "실수 3. Self-RAG 의 오판"
    모델이 "검색 필요 없다" 판단하고는 **학습 지식으로 잘못 답변** (hallucination 위험 복원).  
    **대응**: 보수적 프롬프트 ("조금이라도 회사 정보가 필요하면 YES"). 또는 Self-RAG 에도 **항상 검색** 하되 결과 품질 평가만.

!!! warning "실수 4. GraphRAG 인덱스 비용 과소평가"
    10만 문서 → 엔티티 추출 LLM 호출 10만 회. 수백만 원 쉽게.  
    **대응**: 파일럿 (1000건) 으로 비용 추정 · 점진적 확장. Haiku 같은 싸고 빠른 모델로.

!!! warning "실수 5. 여러 기법을 한꺼번에 도입"
    HyDE + Self-RAG + Rerank + Multi-query = 쿼리당 LLM 호출 5~7회, 지연 3~5초, 비용 10배.  
    **대응**: **하나씩** 도입 · 각 단계의 이득 측정. 이득 < 비용이면 제거.

---

## 7. 운영 시 체크할 점

- [ ] Advanced 기법은 **평가셋 기반 A/B** 로 선택 (Part 4)
- [ ] **쿼리당 LLM 호출 수 · 비용 · 지연** 추적 대시보드
- [ ] HyDE 사용 시 **환각 가상답변 비율** 모니터링
- [ ] Self-RAG **게이트 정확도** (검색 필요 YES/NO 의 TP·FP) 측정
- [ ] GraphRAG 인덱스 **구축·업데이트 비용** 별도 예산
- [ ] **복합 기법의 순서** 문서화 (Query rewrite → HyDE → hybrid search → rerank …)
- [ ] Agentic RAG 는 Part 5의 Agent 운영 가이드라인 함께 적용

---

## 8. 확인 문제

- [ ] §4 `hyde.py` 를 돌리고, 같은 쿼리를 basic RAG 과 비교 — top-5 의 관련 문서 비율 측정
- [ ] §5.2 Self-RAG 를 10가지 쿼리 (절반 RAG 필요, 절반 잡담) 로 평가 — 판단 정확도
- [ ] Query Rewriting 을 다국어 쿼리 ("refund policy" + 한국어 문서) 로 돌려 recall 변화 기록
- [ ] HyDE + Rerank 조합 vs Basic + Rerank 비교 — 지연·정확도
- [ ] GraphRAG 은 **구현 말고 개념 문서화** — 내 프로젝트에 적합한지 결정 트리 쓰기

---

## 9. 원전 · 더 읽을 거리

- **HyDE**: Gao et al. (2022), *"Precise Zero-Shot Dense Retrieval without Relevance Labels"*
- **Self-RAG**: Asai et al. (2023), *"Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection"*
- **GraphRAG**: Edge et al. Microsoft (2024), *"From Local to Global: A Graph RAG Approach to Query-Focused Summarization"* · [github.com/microsoft/graphrag](https://github.com/microsoft/graphrag){target=_blank}
- **Agentic RAG**: LangChain · LlamaIndex 튜토리얼 다수
- **Sufficient Context**: Joren et al. (2024), *"Sufficient Context: A New Lens on Retrieval Augmented Generation Systems"* (ICLR 2025) · [arXiv 2411.06037](https://arxiv.org/abs/2411.06037){target=_blank} · 제품화: [Google Research (2026)](https://research.google/blog/unlocking-dependable-responses-with-gemini-enterprise-agent-platforms-agentic-rag/){target=_blank}
- **Stanford CME 295 Lec 7** — 프로젝트 `_research/stanford-cme295.md`

---

**다음 챕터** → [Ch 14. LangChain 실전 + 멀티모달 RAG](14-langchain-multimodal.md) :material-arrow-right:  
프레임워크로 RAG 파이프라인 빠르게 조립 + **PDF 레이아웃 · 이미지** 기반 멀티모달 RAG.
