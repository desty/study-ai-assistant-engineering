# Ch 14. LangChain 실전 + 멀티모달 RAG

<a class="colab-badge" href="https://colab.research.google.com/" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **LangChain** 의 RAG 컴포넌트 (Loader · Splitter · Embeddings · VectorStore · Retriever · Chain)
    - **LCEL** (LangChain Expression Language) 로 파이프라인을 한 줄로 조립
    - **대화형 RAG** — 이전 대화를 고려한 검색·응답
    - **멀티모달 RAG** — PDF 레이아웃·이미지까지 검색 대상
    - LangChain 버전 불안정성 · OCR 품질 · 테이블 파싱 — 실전 3대 함정
    - Part 3 마무리 · Part 4 로의 다리

!!! quote "전제"
    [Ch 11](11-pipeline.md) · [Ch 12](12-retrieval-quality.md) · [Ch 13](13-advanced-rag.md). 지금까지 RAG 파이프라인을 **손으로** 조립해본 상태 (중요).

---

## 1. 개념 — 프레임워크를 왜 지금?

Ch 11~13 까지 우리는 **수동** 으로 RAG를 조립했습니다. `openai.embeddings.create(...)`, `col.query(...)`, `client.messages.create(...)` 를 하나씩.

**LangChain** 은 이걸 **레고 블록** 처럼 묶는 프레임워크. 순서가 역전돼서는 안 됩니다: 수동을 먼저 알고 나서 프레임워크를 써야 **디버깅·커스터마이징** 이 가능합니다.

> LangChain 은 **생산성 도구** 이지 **이해의 지름길** 이 아닙니다.

---

## 2. LangChain RAG 컴포넌트

![LangChain 컴포넌트 관계](../assets/diagrams/ch14-langchain-components.svg#only-light)
![LangChain 컴포넌트 관계](../assets/diagrams/ch14-langchain-components-dark.svg#only-dark)

| 영역 | 컴포넌트 | 우리가 Ch 11에서 직접 쓴 것 |
|---|---|---|
| **Indexing** | `DocumentLoader` | PyPDF · `Path.read_text` |
| | `TextSplitter` | 간단 분할 (또는 `RecursiveCharacterTextSplitter`) |
| | `Embeddings` | `openai.embeddings.create(...)` |
| | `VectorStore` | Chroma 직접 클라이언트 |
| **Query** | `Retriever` | `col.query(...)` |
| | `PromptTemplate` | f-string |
| | `ChatModel` | `anthropic.Anthropic().messages.create` |
| | `OutputParser` | `response.content[0].text` |

LangChain 의 가치는 **이 컴포넌트들이 표준 인터페이스**를 따라서, 한 줄로 바꿔치기 가능하다는 것 (예: Chroma → Pinecone).

---

## 3. 왜 직접 구현 대신 프레임워크?

### 직접 구현의 장점 (Ch 11~13 방식)

- **완전한 제어·디버깅 가능**
- 의존성 최소
- 성능 튜닝 자유도↑

### LangChain 의 장점

- **표준 컴포넌트**로 빠른 프로토타이핑
- 공식 retriever 구현체 다수 (MultiQuery · ParentDocument · SelfQuery 등)
- **LangGraph** (Part 5) 와 자연스러운 연결
- **LangSmith** 로 tracing·eval 통합 (Part 4·6)

### 추천 사용법

- **학습·설계**: 직접 구현 (Ch 11~13)
- **프로토타입**: LangChain (이 챕터)
- **프로덕션**: 하이브리드 — 핵심 블록은 직접 · 주변은 LangChain

---

## 4. 최소 예제 — Ch 11의 mini_rag 를 LangChain 으로

```bash
pip install langchain langchain-community langchain-anthropic langchain-openai langchain-chroma
```

```python title="langchain_rag.py" linenums="1" hl_lines="10 13 19"
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# 1) 벡터스토어
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = Chroma(collection_name="policies", embedding_function=embeddings, persist_directory="./lc_db")

# 2) 문서 추가 (이미 Ch 11의 docs 가 있다고 가정)
docs = ["환불은 7일 이내...", "배송은 2~3일..."]
vectorstore.add_texts(docs)

# 3) Retriever
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 4) 프롬프트 + 모델 + 파서 = Chain (LCEL)
prompt = ChatPromptTemplate.from_template("""다음 문서만 근거로 답하세요. 문서에 없으면 "문서에 없습니다".

{context}

질문: {question}""")

model = ChatAnthropic(model="claude-haiku-4-5", max_tokens=512)

chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | model
    | StrOutputParser()
)

print(chain.invoke("환불하고 싶은데"))
```

Ch 11의 ~40줄이 **15줄 내외**로 줄어듭니다. 이게 LangChain 의 이득.

---

## 5. 실전 튜토리얼

### 5.1 LCEL — Chain 조립

`|` 연산자로 **파이프라인** 을 표현:

```python title="lcel_basics.py"
chain = prompt | model | parser     # 단순 체인

# 병렬 (map): 같은 입력을 여러 체인에 보내고 결과 합침
from langchain_core.runnables import RunnableParallel

chain = RunnableParallel(
    answer = retriever | prompt | model | parser,
    sources = retriever,            # 원본 문서도 반환
)
```

LCEL 의 3가지 이득:

1. **비동기 자동 지원** (`ainvoke`, `astream`)
2. **스트리밍 내장** (`.stream(...)`)
3. **병렬성** (RunnableParallel)

### 5.2 대화형 RAG — History 반영

이전 대화까지 고려하는 검색·응답:

```python title="conversational_rag.py" linenums="1"
from langchain_core.prompts import MessagesPlaceholder
from langchain.chains import create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain

# history 고려해 쿼리를 재작성하는 retriever
contextualize_prompt = ChatPromptTemplate.from_messages([
    ("system", "이전 대화를 고려해 현재 질문을 자립형 질문으로 재작성하세요."),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

history_aware_retriever = create_history_aware_retriever(model, retriever, contextualize_prompt)

# 실제 답변 생성
qa_prompt = ChatPromptTemplate.from_messages([
    ("system", "아래 문서만 근거로 답하세요.\n\n{context}"),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])
qa_chain = create_stuff_documents_chain(model, qa_prompt)
rag_chain = create_retrieval_chain(history_aware_retriever, qa_chain)

# 사용
history = []
r1 = rag_chain.invoke({"input": "환불하려고", "chat_history": history})
history.extend([("human", "환불하려고"), ("assistant", r1["answer"])])
r2 = rag_chain.invoke({"input": "승인 누가 해?", "chat_history": history})  # (1)!
```

1. "**승인 누가 해?**" 가 "**환불 승인 누가 해?**" 로 재작성돼 정확히 검색.

### 5.3 멀티모달 RAG — 텍스트 + 이미지

PDF 에는 **표·다이어그램·스크린샷** 이 있습니다. 텍스트만 추출하면 의미 손실.

![멀티모달 RAG](../assets/diagrams/ch14-multimodal-rag.svg#only-light)
![멀티모달 RAG](../assets/diagrams/ch14-multimodal-rag-dark.svg#only-dark)

**두 가지 접근**:

1. **이미지를 직접 임베딩** — CLIP · Voyage `voyage-multimodal-3`
2. **이미지를 LLM 으로 설명** — Claude/GPT-4o 로 설명 텍스트 생성 후 텍스트 임베딩

**방법 2가 실전 권장** — 한국어·도메인 특화 검색에서 정확도↑, 관리 쉬움.

```python title="multimodal_simple.py" linenums="1"
import fitz  # PyMuPDF
from anthropic import Anthropic
import base64

anthropic = Anthropic()
pdf = fitz.open("report.pdf")

for page_num in range(len(pdf)):
    page = pdf[page_num]
    # 텍스트 추출
    text = page.get_text()
    if text.strip():
        index_text_chunk(text, source=f"report.pdf#p={page_num}")

    # 이미지 추출 → Claude Vision 으로 설명
    pix = page.get_pixmap(dpi=150)
    img_bytes = pix.tobytes("png")
    img_b64 = base64.b64encode(img_bytes).decode()

    r = anthropic.messages.create(
        model="claude-haiku-4-5", max_tokens=512,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": "image/png", "data": img_b64
                }},
                {"type": "text", "text": "이 페이지의 표·다이어그램·차트를 한국어로 설명하세요. 숫자는 정확히."},
            ],
        }],
    )
    caption = r.content[0].text
    index_text_chunk(caption, source=f"report.pdf#p={page_num}#visual")   # (1)!
```

1. 이미지 캡션을 **텍스트** 로 인덱싱 — 일반 RAG 파이프라인에 그대로 합류.

### 5.4 PDF 레이아웃 심화

표·제목·바디 텍스트를 **구분해서 파싱**:

```python title="layout_parsing.py"
# 옵션 1: unstructured (고품질, 유료 API 옵션 있음)
from unstructured.partition.pdf import partition_pdf

elements = partition_pdf(
    filename="report.pdf",
    strategy="hi_res",                 # 느림·정확
    infer_table_structure=True,        # 표 구조 보존
    extract_images_in_pdf=True,        # 이미지도 꺼냄
)

for el in elements:
    if el.category == "Table":
        # 표는 마크다운 등으로 특별 취급
        index_text_chunk(el.metadata.text_as_html, source=..., doc_type="table")
    elif el.category == "Title":
        # 섹션 제목으로 청크 경계
        ...
    else:
        index_text_chunk(str(el), source=...)
```

다른 옵션:

- **docling** (IBM, 2024) — 빠르고 정확, 오픈소스
- **PyMuPDF (fitz)** — 가볍고 빠름, 레이아웃 인식은 약함
- **Amazon Textract · Azure Document Intelligence** — 유료 · 한국어 가능

---

## 6. 자주 깨지는 포인트

!!! warning "실수 1. LangChain 버전 불안정성"
    LangChain 은 API 가 **자주 바뀝니다**. 몇 달 전 튜토리얼 코드가 import 부터 깨지는 경우 흔함.  
    **대응**: `requirements.txt` 에 **정확한 버전 pin**. 최신은 `langchain-community` · `langchain-{vendor}` 로 분리된 구조.

!!! warning "실수 2. OCR 품질이 검색 품질의 상한"
    한국어 PDF · 스캔 문서 · 오래된 PDF 는 OCR 오류가 많음. 그 오류가 그대로 임베딩·검색에 반영.  
    **대응**: (a) 문서 품질 검증 (임의 샘플 수동 확인), (b) 중요 문서는 **원본 텍스트 확보** (Markdown 변환), (c) OCR 엔진 비교 (Tesseract · Google · Azure).

!!! warning "실수 3. 표 파싱 실패"
    `pypdf` 는 표를 **행 무시하고 텍스트만** 뽑음 → "A B C D 1 2 3 4" 처럼 뒤섞인 텍스트.  
    **대응**: `unstructured` · `docling` 의 `infer_table_structure=True` · 표는 **별도 chunk·doc_type** 로 관리.

!!! warning "실수 4. 멀티모달 비용 폭주"
    모든 페이지를 Vision LLM 에 돌리면 **페이지당 $0.01~0.05**. 1000페이지면 $50.  
    **대응**: (a) 이미지가 있는 페이지만 선별, (b) Haiku 같은 **저가 Vision 모델**, (c) **증분 처리** (새 문서만).

!!! warning "실수 5. LangChain 으로 마법 기대"
    컴포넌트가 많아 "대충 엮으면 된다" 생각. 내부 동작 모르면 **버그·성능 문제 진단 불가**.  
    **대응**: Ch 11~13 의 수동 구현 경험을 **반드시** 먼저. LangSmith 로 tracing 걸어 내부 흐름 관찰.

---

## 7. 운영 시 체크할 점

- [ ] `langchain*` 패키지 **버전 pin** (`==` 또는 `~=`)
- [ ] LangChain API **deprecation warning** 주기적 체크
- [ ] PDF 파이프라인에 **품질 스팟체크** (월 1회 샘플 수동 검증)
- [ ] OCR · 표 파싱 실패율 로깅
- [ ] 멀티모달은 **페이지 선별** 규칙 (이미지 있는 페이지만)
- [ ] **LangSmith/Langfuse** 트레이싱 (Part 6 Ch 27 과 연계)
- [ ] Vendor lock-in 경계 — 핵심 RAG 블록은 직접 구현 유지

---

## 8. 확인 문제

- [ ] Ch 11의 `mini_rag.py` 와 §4의 LangChain 버전을 같은 문서에 돌려 **결과 동일성** 확인
- [ ] §5.2 대화형 RAG 로 3턴 대화 — 2턴째 "그럼 그거 언제까지 가능해?" 같은 대명사 질문이 잘 처리되는지
- [ ] 이미지 포함 PDF 1개에 §5.3 멀티모달 적용 → 이미지 기반 질문 ("저 차트의 3분기 매출은?") 이 답해지는지
- [ ] `unstructured` 와 `pypdf` 로 같은 PDF 처리 — 표가 포함된 페이지에서 차이 관찰
- [ ] LangChain 패키지를 **마이너 버전 낮춘** `requirements.txt` 로 새 venv 에서 돌려 import 오류 경험

---

## 9. 원전 · 더 읽을 거리

- **LangChain**: [python.langchain.com](https://python.langchain.com){target=_blank} — 공식 문서
- **LangSmith**: [smith.langchain.com](https://smith.langchain.com){target=_blank} — tracing · eval
- **unstructured**: [docs.unstructured.io](https://docs.unstructured.io){target=_blank}
- **docling** (IBM): [github.com/DS4SD/docling](https://github.com/DS4SD/docling){target=_blank}
- **Voyage Multimodal 3**: [docs.voyageai.com/docs/multimodal-embeddings](https://docs.voyageai.com){target=_blank}
- **Stanford CME 295 Lec 7** — 프로젝트 `_research/stanford-cme295.md`

---

## 10. Part 3를 마치며

Part 3 에서 배운 것 (6 챕터):

| Ch | 핵심 |
|---|---|
| 9 | **왜 RAG** — 컷오프·프라이빗·최신성 |
| 10 | 임베딩·벡터검색·Chroma |
| 11 | end-to-end 파이프라인 (8단계) |
| 12 | Hybrid·Reranker·Metadata |
| 13 | HyDE·Self-RAG·GraphRAG·Agentic |
| 14 | LangChain·멀티모달 |

**Part 3 졸업 상태** — 다음을 만들 수 있어야 합니다:

- 회사 문서 기반 QA 봇 (citation 포함)
- 파라미터 튜닝된 hybrid 검색 파이프라인
- 최소 한 개의 Advanced 기법 적용 + 효과 측정
- LangChain 으로 대화형 RAG 프로토타입
- PDF 레이아웃·이미지까지 검색하는 멀티모달 RAG (선택)

---

**다음 Part** → [Part 4. 평가 · 추론 품질 · 디버깅](../part4/15-what-to-evaluate.md) :material-arrow-right:  
RAG 는 만들었습니다. 그런데 **정말 잘 작동하는가** 는 어떻게 확인하나?  
평가셋 · LLM-as-a-Judge · self-consistency · 실패 분류 — 품질의 과학.
