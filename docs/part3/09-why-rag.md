# Ch 9. 왜 RAG가 필요한가

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part3/ch09_why_rag.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - LLM이 **학습한 것만 안다** 는 근본 한계 — 지식 컷오프 · 프라이빗 데이터 · 최신성
    - **RAG (Retrieval-Augmented Generation, 검색 증강 생성)** 의 개념과 필요 이유
    - **LLM 단독 응답 vs LLM + RAG 응답** 직접 비교
    - **파인튜닝 vs RAG** — 언제 뭘 선택하나
    - RAG 도입 전 반드시 생각해야 할 **3가지 함정**

!!! quote "전제"
    Part 2까지 완료. [Ch 4](../part2/04-api-start.md) API 호출 + [Ch 5](../part2/05-prompt-cot.md) 프롬프트에 익숙.

---

## 1. 개념 — LLM 은 학습한 것만 안다

Claude · GPT 모델은 **학습 시점까지의 데이터** 로만 만들어집니다. 그래서 아래 셋은 **원리적으로** 모릅니다.

| 모르는 것 | 왜 |
|---|---|
| **컷오프 이후 정보** | 학습 데이터에 없음 (예: 오늘 주가) |
| **프라이빗 데이터** | 공개 인터넷에 없는 것 (우리 회사 문서·DB) |
| **자주 바뀌는 데이터** | 모델 재학습 주기 ≫ 데이터 변경 주기 (재고·이벤트·정책) |

이 문제는 **프롬프트를 아무리 잘 써도** 안 풀립니다. Part 2 Ch 5 "모르면 모른다고" 지시는 **거짓말 억제** 에 도움되지만, **정답을 알려주진 않아요**.

!!! quote "핵심 비유"
    "모델이 학습한 건 **5년 전에 읽은 책**. 오늘 뉴스·우리 회사 매뉴얼은 읽은 적 없음."  
    → **읽을 거리를 그때그때 손에 쥐여주자** = RAG.

---

## 2. RAG 는 한 문장

> **RAG** = 질문과 관련된 **문서를 먼저 찾아서**, 그 문서를 **프롬프트에 넣어** 답하게 하는 기법.

![LLM 단독 vs LLM + RAG](../assets/diagrams/ch9-llm-vs-rag.svg#only-light)
![LLM 단독 vs LLM + RAG](../assets/diagrams/ch9-llm-vs-rag-dark.svg#only-dark)

그게 전부입니다. 복잡해 보이는 건 "**문서를 찾는** 방법" 이 정교해지는 부분 (Part 3의 나머지 챕터).

**RAG 의 3가지 이득**:

1. **최신성** — 문서 업데이트만 하면 모델 재학습 없이 최신 정보 반영
2. **프라이빗 지식 활용** — 회사 정책·매뉴얼·코드베이스 기반 답변
3. **추적 가능성 (citation)** — 답변이 어느 문서의 어느 부분을 근거로 했는지 표시 가능

---

## 3. 어디에 쓰이는가

### 대표 유즈케이스

| 유즈케이스 | 검색 대상 | 예시 |
|---|---|---|
| **고객 지원 봇** | FAQ · 정책 문서 | "환불 정책이 어떻게 되나요?" → 정책 A4의 3.2절 |
| **사내 지식 검색** | 위키 · 회의록 · 온보딩 자료 | "신규 입사자 온보딩 프로세스는?" |
| **제품 메뉴얼 QA** | 제품 가이드 | "X 기능 설정 방법?" |
| **코드베이스 QA** | 소스코드 + 커밋 히스토리 | "결제 모듈의 인증 로직 어디 있나?" |
| **법률·의료 지원** | 판례·논문 (출처 필수) | "최근 판례에 따르면..." |

### Part 1 Ch 3의 8블록에서의 위치

Part 1 Ch 3에서 본 **8블록 중 "검색(Retrieve)"** 이 바로 RAG의 자리. Part 3 전체는 이 블록을 **어떻게 만드나** 를 다룹니다.

---

## 4. 최소 예제 — 같은 질문, 두 경로 직접 비교

```python title="llm_vs_rag_compare.py" linenums="1" hl_lines="15 22 23"
from anthropic import Anthropic
client = Anthropic()

question = "우리 회사의 연차 신청 절차는?"

# 1) LLM 단독 — 모델은 우리 회사를 모름
r1 = client.messages.create(
    model="claude-haiku-4-5", max_tokens=256,
    messages=[{"role": "user", "content": question}],
)
print("=== LLM 단독 ===\n", r1.content[0].text, "\n")

# 2) LLM + 수동 RAG — 우리 회사 문서를 프롬프트에 직접 주입 (단순 버전)
COMPANY_DOC = """
## 연차 신청 절차 (2026 개정)
1. 사내 포털 → 휴가 > 연차 신청
2. 최소 2주 전 신청, 팀장 승인 필요
3. 연속 5일 이상은 임원 결재 추가
4. 긴급 사유는 이메일로 사전 통보 후 사후 신청 가능
"""

r2 = client.messages.create(
    model="claude-haiku-4-5", max_tokens=256,
    system=f"아래 회사 문서를 바탕으로만 답하세요. 문서에 없으면 '문서에 없습니다' 라고 답하세요.\n\n{COMPANY_DOC}",  # (1)!
    messages=[{"role": "user", "content": question}],
)
print("=== LLM + RAG(수동) ===\n", r2.content[0].text)
```

1. 가장 단순한 RAG — 관련 문서를 프롬프트에 **통째로 주입**. 문서가 작으면 이 방식도 유효.

**관찰 포인트**:

- 1번 응답은 **일반론** ("2주 전 신청…" 같은 흔한 회사 규정 추측) 또는 **거절** ("회사마다 달라서 모릅니다")
- 2번 응답은 **문서 그대로** — "최소 2주 전 신청, 팀장 승인 필요 · 5일 이상은 임원 결재"

이 예제는 **문서가 작을 때** 만 작동. 문서가 수백 페이지면 컨텍스트 초과 → Part 3의 나머지 챕터가 **검색** 으로 "관련 부분만 찾아내는 법" 을 가르칩니다.

---

## 5. 실전 튜토리얼

### 5.1 지식 컷오프 실험

모델이 뭘 모르는지 확인하는 게 RAG 설계의 출발:

```python title="knowledge_cutoff_probe.py" linenums="1"
questions = [
    "어제 나온 뉴스를 요약해줘",                        # 최신성
    "우리 회사의 개인정보 보호 정책 3조는?",            # 프라이빗
    "2026년 4월 현재 서울의 미세먼지는?",               # 실시간
    "파이썬 list 의 append 메서드 사용법은?",          # 학습된 공개 지식
]

for q in questions:
    r = client.messages.create(
        model="claude-haiku-4-5", max_tokens=200,
        messages=[{"role": "user", "content": q}],
    )
    print(f"\nQ: {q}\nA: {r.content[0].text[:200]}...")
```

대개:

- 1, 2, 3번 → **"모른다"** 또는 **부정확한 추측** (hallucination 위험)
- 4번 → 잘 답함 (공개된 학습 데이터)

1, 2, 3번이 **RAG 후보** 입니다.

### 5.2 Fine-tune 이 필요한 것과 구분하기

![Fine-tune vs RAG](../assets/diagrams/ch9-finetune-vs-rag.svg#only-light)
![Fine-tune vs RAG](../assets/diagrams/ch9-finetune-vs-rag-dark.svg#only-dark)

RAG 와 파인튜닝은 **서로 다른 문제** 를 푸는 도구:

| | **RAG** | **Fine-tune** (Part 7) |
|---|---|---|
| 해결하는 문제 | **지식 부족** | **행동·스타일 부족** |
| 예시 | "우리 회사 정책은?" | "우리 회사 톤으로 답하기" |
| 변경 주기 | 수시 (문서만 갱신) | 드물게 (재학습 필요) |
| 비용 | 검색 인프라 | GPU · 데이터 준비 |
| 추적 가능성 | **높음** (citation) | 낮음 |
| 초기 도입 난이도 | 낮음 | 높음 |

**실전 권장 순서**: 프롬프트 → RAG → 파인튜닝. 대부분의 문제는 RAG 에서 해결되고, 파인튜닝은 **RAG 로 도저히 안 되는** 말투·포맷·특화 분류에만 씁니다.

### 5.3 RAG 파이프라인 미리보기

Part 3 앞으로의 내용을 한눈에:

| Ch | 내용 | 해결하는 문제 |
|---|---|---|
| **9 (지금)** | 왜 RAG 인가 | 필요성 · 판단 |
| 10 | 임베딩과 벡터 검색 기초 | 문서를 "찾는" 수학적 기반 |
| 11 | RAG 파이프라인 전체 흐름 | end-to-end 구현 |
| 12 | 검색 품질 개선 | hybrid · rerank |
| 13 | Advanced RAG (HyDE · GraphRAG 등) | 복잡한 케이스 |
| 14 | LangChain 실전 + 멀티모달 | 프로덕션 · PDF·이미지 |

지금 챕터는 "**RAG 를 할지 말지**"의 판단. 할 결정이 섰다면 Ch 10부터.

---

## 6. 자주 깨지는 포인트

!!! warning "실수 1. 'RAG 면 hallucination 0' 미신"
    문서에 정답이 있어도 모델은 **엉뚱한 재해석** · **검색 결과 + 자기 추측 섞기** 가능. RAG 는 **발생률을 낮출 뿐** 완전 방지 불가.  
    **대응**: (1) 시스템 프롬프트에 "문서 근거가 없으면 모른다고 답하라", (2) Part 4의 **LLM-as-Judge** 로 검증, (3) citation 강제 → 사용자가 원문 확인.

!!! warning "실수 2. 검색 실패를 무시"
    사용자 질문이 문서 코퍼스 밖이면 **검색 결과가 0** 또는 **무관한 문서만** 옴. 이걸 그대로 프롬프트에 넣으면 모델이 **무관한 문서 기반으로 추측**.  
    **대응**: 검색 점수 임계치 아래면 **"정보 부족 - 담당자에게 연결"** 플로우. Part 1 Ch 3의 휴먼 핸드오프 블록.

!!! warning "실수 3. 문서에 잘못된 내용이 있으면 그대로 전파"
    RAG 는 **문서의 진실성을 검증하지 않음**. 낡은 매뉴얼 · 잘못 작성된 FAQ → 틀린 답을 **자신 있게** 뱉음.  
    **대응**: (1) 문서 큐레이션·버전 관리, (2) 답변에 **"문서 최종 수정일"** 함께 표시, (3) 주기적 평가셋 (Part 4) 으로 오답 발견·수정.

!!! warning "실수 4. 모든 문제를 RAG 로 풀려고 함"
    "우리 회사 톤으로 답해줘" 같은 **행동 문제**는 RAG 로 안 풀림. 톤·포맷·복잡한 분류는 **프롬프트 + 파인튜닝** 영역.  
    **대응**: §5.2 의 결정 트리. RAG 는 **지식 문제** 전용.

---

## 7. 운영 시 체크할 점

- [ ] **지식 컷오프 감사** — 분기별 "모델이 모를 만한 최신 질문" 20개로 확인
- [ ] **문서 최신성** — 각 문서의 "최종 수정일" 메타데이터 필수
- [ ] **검색 실패 로그** — "검색 결과 0건" 케이스를 별도 수집 → 문서 부족 영역 식별
- [ ] **hallucination 모니터링** — 사용자 피드백 (👎) 중 "사실 오류" 카테고리 추적
- [ ] **citation 의무화** — 모든 답변에 출처 문서명·섹션 포함
- [ ] **민감 문서 분리** — PII·내부 기밀 문서는 RAG 코퍼스에서 별도 관리 (권한 체크)
- [ ] **RAG vs 파인튜닝** 분기별 재평가 — "이걸 RAG 로 계속 할 가치가 있나"

---

## 8. 확인 문제

- [ ] §4 `llm_vs_rag_compare.py` 를 내 회사 문서 (또는 임의 문서) 로 돌려 응답 차이 한 문단 정리
- [ ] §5.1 지식 컷오프 탐침을 5가지 질문으로 실행. 어떤 질문이 "모른다"로, 어떤 질문이 "추측"으로 오는지 분류
- [ ] §5.2 의 결정 트리로 **내 프로젝트의 3가지 문제**를 RAG / Fine-tune 중 어디로 보낼지 정하기
- [ ] RAG 로 "**무관한 문서**"를 일부러 주입해 모델이 어떻게 반응하는지 관찰. "문서 근거가 없으면 모른다" 시스템 프롬프트의 효과 측정
- [ ] "RAG로 이걸 풀면 안 되는" 케이스를 1개 찾아 파인튜닝·프롬프트 중 뭐가 맞는지 논거 쓰기

---

## 9. 원전 · 더 읽을 거리

- **RAG 원조 논문**: Lewis et al. (2020), *"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"*
- **Stanford CME 295 Lec 7** — RAG · function calling · ReAct. 프로젝트 `_research/stanford-cme295.md` 요약
- **Anthropic**: "Adding context with RAG" (docs.anthropic.com)
- **LangChain RAG Tutorial**: [python.langchain.com/docs/tutorials/rag](https://python.langchain.com/docs/tutorials/rag){target=_blank}

---

**다음 챕터** → [Ch 10. 임베딩과 벡터 검색 기초](10-embedding.md) :material-arrow-right:  
"**관련 문서를 찾는**" 이 어떻게 수학적으로 되는가 — 임베딩 · 코사인 유사도 · 벡터DB.
