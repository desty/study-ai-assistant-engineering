# Ch 11. RAG 파이프라인 전체 흐름

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part3/ch11_pipeline.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - RAG 의 두 단계 — **Indexing** (문서 준비) + **Query** (실행)
    - 문서 수집 · chunking · 임베딩 · 저장 · 검색 · augmentation · 생성 · **citation**
    - 작은 PDF셋으로 **end-to-end 작동 시스템** 한 번 만들기
    - chunk 경계 잘림 · citation 환각 · 컨텍스트 초과 — 3대 함정

!!! quote "전제"
    [Ch 9](09-why-rag.md) · [Ch 10](10-embedding.md) 필수. Colab + OpenAI/Anthropic 키.

---

## 1. 개념 — RAG 는 두 단계

RAG를 "문서를 넣으면 답이 나오는 블랙박스" 로 보지 말고 **두 단계**로 분해하는 게 첫 번째.

![RAG 파이프라인 두 단계](../assets/diagrams/ch11-rag-pipeline.svg#only-light)
![RAG 파이프라인 두 단계](../assets/diagrams/ch11-rag-pipeline-dark.svg#only-dark)

| | **Indexing (준비)** | **Query (실행)** |
|---|---|---|
| 언제 | 문서 추가/수정 시 **한 번** | 사용자 질문마다 **매번** |
| 비용 | 배치 (오프라인 OK) | 실시간 (p95 < 1~2초 목표) |
| 단계 | 로드 → chunking → 임베딩 → 저장 | 쿼리 임베딩 → 검색 → 프롬프트 증강 → 생성 |
| 연결점 | **벡터 DB** — 같은 임베딩 공간을 공유 |

이걸 명확히 분리하면 **배치 파이프라인** (Indexing) 과 **실시간 서비스** (Query) 가 독립적으로 최적화 가능.

---

## 2. 왜 이렇게 분해하나

실제 버그는 **단계 사이** 에서 주로 발생:

- 문서 로드가 **이상한 포맷** (PDF 표 · 이미지 OCR) → chunking 실패 → 빈 임베딩
- 임베딩 모델을 **바꿨는데** 벡터 DB 는 그대로 → 차원 불일치
- Retrieval 은 잘 되는데 **augment 단계** 에서 토큰 초과

단계마다 **관측 가능** 해야 고칠 수 있습니다.

---

## 3. 어디에 쓰이는가

실전 예:

- **사내 지식 QA 봇** — Notion/Confluence/Google Drive 문서 전체
- **고객 지원 봇** — FAQ · 제품 매뉴얼 · 정책 문서
- **코드베이스 QA** — 소스 + README + 커밋 메시지
- **법률·의료 검색** — 판례·논문 (citation 필수)

---

## 4. 최소 예제 — 8단계 end-to-end

```bash
pip install anthropic openai chromadb pypdf
```

작은 정책 문서 2개로 시작:

```python title="mini_rag.py" linenums="1" hl_lines="16 22 29 39 48"
from anthropic import Anthropic
from openai import OpenAI
import chromadb

anthropic = Anthropic()
openai = OpenAI()

# ---------- INDEXING ----------

# 1) 문서 로드 (여기선 문자열로 직접)
docs = [
    {
        "id": "refund_policy",
        "text": """[환불 정책]
구매 후 7일 이내, 팀장 승인 필요.
5일 이상 연속 사용 제품은 임원 승인 추가.
긴급 사유는 이메일 사전 통보 후 사후 신청 가능.""",
        "source": "policy.md#refund",
    },
    {
        "id": "shipping_policy",
        "text": """[배송 정책]
주문일 기준 영업일 2~3일 소요.
도서산간은 +2일 추가.
5만원 이상 구매 시 무료 배송.""",
        "source": "policy.md#shipping",
    },
]

# 2) Chunking — 여기선 짧아서 그대로 통째 chunk
chunks = docs  # 실전은 §5.2 분할

def embed(texts):
    res = openai.embeddings.create(model="text-embedding-3-small", input=texts)
    return [d.embedding for d in res.data]

# 3) 임베딩 + 4) 저장
chroma = chromadb.PersistentClient(path="./mini_rag_db")
col = chroma.get_or_create_collection(name="policies")
col.upsert(
    ids=[c["id"] for c in chunks],
    documents=[c["text"] for c in chunks],
    embeddings=embed([c["text"] for c in chunks]),
    metadatas=[{"source": c["source"]} for c in chunks],
)

# ---------- QUERY ----------

def rag_answer(question: str, k: int = 2) -> str:
    # 5) 쿼리 임베딩 + 6) 검색
    q_emb = embed([question])[0]
    res = col.query(query_embeddings=[q_emb], n_results=k)
    retrieved = [
        (doc, meta["source"]) for doc, meta
        in zip(res["documents"][0], res["metadatas"][0])
    ]

    # 7) Augment — 검색 결과를 프롬프트에 붙임
    context = "\n\n".join(f"[{src}]\n{doc}" for doc, src in retrieved)
    system = f"""아래 회사 문서를 근거로만 답하세요.
문서에 없는 내용은 "문서에 없습니다" 라고 답하세요.
답변 끝에 반드시 참고한 [source] 를 나열하세요.

{context}"""

    # 8) 생성
    r = anthropic.messages.create(
        model="claude-haiku-4-5", max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": question}],
    )
    return r.content[0].text

print(rag_answer("구매한 물건을 환불하고 싶어요"))
```

기대 출력:

```
환불은 구매 후 7일 이내 신청 가능하며 팀장 승인이 필요합니다.
5일 이상 연속 사용하신 제품은 임원 승인이 추가로 필요합니다.

참고: [policy.md#refund]
```

**이게 전부입니다.** 나머지 Part 3은 각 단계의 품질·성능·확장성을 올리는 내용.

---

## 5. 실전 튜토리얼

### 5.1 문서 수집 — 포맷별 로더

```python title="loaders.py" linenums="1"
from pypdf import PdfReader
from pathlib import Path

def load_pdf(path: str) -> list[dict]:
    """페이지 단위로 분리 · 메타데이터에 페이지 번호 포함."""
    reader = PdfReader(path)
    return [
        {"text": p.extract_text() or "", "source": f"{path}#page={i+1}"}
        for i, p in enumerate(reader.pages)
    ]

def load_markdown(path: str) -> list[dict]:
    text = Path(path).read_text()
    # 헤딩으로 분리
    sections = []
    current = {"title": "intro", "text": ""}
    for line in text.split("\n"):
        if line.startswith("## "):
            if current["text"].strip():
                sections.append(current)
            current = {"title": line[3:].strip(), "text": ""}
        else:
            current["text"] += line + "\n"
    if current["text"].strip():
        sections.append(current)
    return [{"text": s["text"], "source": f"{path}#{s['title']}"} for s in sections]
```

!!! tip "PDF 함정"
    `pypdf` 는 텍스트만 잘 뽑음. **표·이미지·수식**은 망가짐. 실전에선 `unstructured` · `docling` · `PyMuPDF (fitz)` 같은 라이브러리 비교.

### 5.2 Chunking 전략

![Chunking 전략 비교](../assets/diagrams/ch11-chunking.svg#only-light)
![Chunking 전략 비교](../assets/diagrams/ch11-chunking-dark.svg#only-dark)

**실전 권장**:

| 방식 | 설명 | 언제 |
|---|---|---|
| **Fixed size** | N토큰씩 자르고 overlap | 범용 시작점 (권장) |
| **By section** | 헤딩·문단 경계로 | 구조화된 문서 (MD·HTML) |
| **Semantic** | 의미 변곡점에서 자름 | 품질이 중요한 경우 |
| **Sliding window** | 작은 chunk + 겹침 | 검색 recall 우선 |

**LangChain으로**:

```python title="chunker.py" linenums="1"
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,         # 토큰이 아닌 "문자" 기준 (대략 512자 ≈ 150~300 토큰)
    chunk_overlap=50,        # 경계 잘림 방지용 겹침
    separators=["\n\n", "\n", ". ", " ", ""],  # (1)!
)

def chunk_docs(docs: list[dict]) -> list[dict]:
    out = []
    for d in docs:
        for i, chunk in enumerate(splitter.split_text(d["text"])):
            out.append({
                "text": chunk,
                "source": f"{d['source']}#chunk={i}",
            })
    return out
```

1. 우선순위: 문단 → 줄 → 문장 → 공백. 경계 존중해 잘라 **의미 손실 최소화**.

### 5.3 저장 + Citation 용 메타데이터

검색해서 answering 할 때 **어디서 온 정보인지** 추적하려면 메타데이터 설계가 중요.

```python title="metadata_schema.py" linenums="1"
# 권장 메타 스키마
{
    "source": "policy.md#refund",       # 원 문서 + 앵커
    "chunk_id": 3,                       # 문서 내 chunk 순서
    "updated_at": "2026-04-15",          # 갱신일 (stale 체크)
    "owner": "legal-team",               # 소유 팀 (권한 체크)
    "doc_type": "policy",                # 필터용 (policy | faq | wiki)
    "lang": "ko",                        # 언어 (다국어 필터)
}
```

검색 시 metadata filter 활용:

```python
col.query(
    query_embeddings=[q_emb],
    n_results=5,
    where={"doc_type": "policy", "lang": "ko"},
)
```

### 5.4 Augmentation — 프롬프트에 넣는 법

검색 결과를 어떻게 프롬프트에 넣느냐가 생성 품질을 좌우.

```python title="augment.py" linenums="1" hl_lines="6 7 8"
def build_prompt(question: str, retrieved: list[dict]) -> str:
    # 토큰 초과 방어 — 상위 k 만
    retrieved = retrieved[:5]
    context = "\n\n".join(
        f"<doc source=\"{c['source']}\" updated=\"{c.get('updated_at', 'N/A')}\">\n"
        f"{c['text']}\n"
        f"</doc>"
        for c in retrieved
    )
    return f"""<context>
{context}
</context>

위 문서만 근거로 답하세요. 문서에 없으면 "문서에 없습니다" 라고 답하세요.
모든 주장은 [source] 인용을 붙이세요."""
```

XML 태그로 감싸 **경계 명확히** — LLM이 문서 내용과 사용자 질문을 헷갈리지 않음 (프롬프트 인젝션 대비).

### 5.5 Citation 강제

답변이 인용 없이 오면 **자동 재프롬프트**:

```python title="citation_enforce.py" linenums="1"
import re

def has_citation(text: str) -> bool:
    return bool(re.search(r"\[[\w\-\.#=]+\]", text))

def answer_with_citation(question, retrieved, retries=1):
    for attempt in range(retries + 1):
        r = anthropic.messages.create(
            model="claude-haiku-4-5", max_tokens=512,
            system=build_prompt(question, retrieved),
            messages=[{"role": "user", "content": question}],
        )
        text = r.content[0].text
        if has_citation(text):
            return text
    # 최종 실패 — 인용 없이 반환하되 경고 로그
    return text + "\n\n[경고: 인용 없음]"
```

### 5.6 토큰 예산 관리

`max_tokens` + 컨텍스트 예산 관리 필수:

```python title="token_budget.py" linenums="1"
# 예: Claude Haiku 컨텍스트 200K
# 시스템 프롬프트 500 + 사용자 질문 100 + 검색 문서 N + 응답 2048 <= 200K
#   → 검색 문서 최대 약 197K
# 실전은 훨씬 타이트: 빠른 응답 위해 검색 chunk 를 5~10개로 제한
```

---

## 6. 자주 깨지는 포인트

!!! warning "실수 1. Chunk 경계에서 문장 잘림"
    고정 길이로 자르면 **한 문장 중간** 에서 끊기기 십상. 임베딩 품질 · 답변 정확도 하락.  
    **대응**: `RecursiveCharacterTextSplitter` 처럼 **문단 → 줄 → 문장** 경계 존중. overlap 50~100자 넣어 경계 문맥 보존.

!!! warning "실수 2. Citation 환각"
    프롬프트에 "[source] 를 인용하라" 했는데 모델이 **존재하지 않는 source** 를 만들어냄.  
    **대응**: (a) 프롬프트에서 허용 source 목록 명시, (b) 응답 후 **source 유효성 검증** (실제 검색된 것 중 하나인지), (c) LangChain `citations` 기능 활용.

!!! warning "실수 3. 컨텍스트 초과"
    top-10 을 그대로 다 넣어 프롬프트가 모델 컨텍스트 초과 → 에러.  
    **대응**: top-k 제한 (5~10) + chunk 당 토큰 상한 + **예산 계산**. 초과 시 요약하거나 drop.

!!! warning "실수 4. 문서 업데이트가 반영 안 됨"
    PDF/MD 만 바꿨다고 안 됨. **재임베딩** 해서 벡터 DB 에 upsert 필요.  
    **대응**: 파일 해시 비교 → 변경된 것만 재임베딩하는 **증분 인덱싱** 파이프라인. cron 또는 Git hook.

!!! warning "실수 5. 민감 문서가 인덱스에 섞임"
    급여 테이블·개인정보 문서가 RAG 코퍼스에 들어가면 **누구나 검색 가능**.  
    **대응**: 문서 분류 → 민감 등급에 따라 **별도 컬렉션** + 권한 기반 메타 필터링. 가장 안전한 건 **아예 인덱싱하지 않기**.

---

## 7. 운영 시 체크할 점

- [ ] **Indexing 파이프라인** 자동화 (문서 변경 감지 → 재임베딩 → upsert)
- [ ] **증분 업데이트** — 전체 재임베딩은 비쌈. 변경분만
- [ ] **Chunking 파라미터** 기록 (size, overlap, separator) — 재현성
- [ ] **메타데이터 스키마** 문서화 (source · updated_at · owner · doc_type · lang)
- [ ] **Citation 유효성 검증** — 응답의 [source] 가 실제 검색 결과에 있나
- [ ] **토큰 예산 대시보드** — 시스템/검색/질문/응답 분해 · 초과율
- [ ] **검색 실패 로그** — top-k score 낮은 케이스 별도 수집 (문서 부족 영역 식별)
- [ ] **권한 필터링** — 사용자 그룹별 접근 가능 컬렉션 분리

---

## 8. 확인 문제

- [ ] §4 `mini_rag.py` 를 실제로 돌리고, 회사/내 문서 5~10개로 RAG 봇 만들기
- [ ] §5.2 의 4가지 chunking 전략 중 2개를 같은 문서에 적용해 검색 품질 비교
- [ ] Citation 환각을 일부러 유도 (허구 source 요구) 하고 §5.5 검증 로직이 잡아내는지 확인
- [ ] 문서 업데이트 시나리오 — 원본 수정 후 증분 재임베딩 코드 작성
- [ ] top-k=1 / 5 / 20 으로 바꿔가며 답변 품질·토큰 사용량·latency 비교

---

## 9. 원전 · 더 읽을 거리

- **LangChain RAG Tutorial**: [python.langchain.com/docs/tutorials/rag](https://python.langchain.com/docs/tutorials/rag){target=_blank}
- **LlamaIndex** (RAG 전문 프레임워크): [docs.llamaindex.ai](https://docs.llamaindex.ai){target=_blank}
- **Anthropic "Adding context with RAG"**: docs.anthropic.com
- **Chunking 전략 비교**: Pinecone 블로그 "Chunking Strategies for LLM Applications"
- **Stanford CME 295 Lec 7** — 프로젝트 `_research/stanford-cme295.md`

---

**다음 챕터** → [Ch 12. 검색 품질 개선](12-retrieval-quality.md) :material-arrow-right:  
기본 파이프라인은 완성. 이제 **검색이 실패하는 케이스를 분석** 하고 hybrid · reranker 로 답변 품질을 끌어올립니다.
