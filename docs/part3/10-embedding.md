# Ch 10. 임베딩과 벡터 검색 기초

<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/notebooks/part3/ch10_embedding.ipynb" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>

!!! abstract "이 챕터에서 배우는 것"
    - **임베딩(embedding)** — 문장을 고차원 숫자 벡터로 바꾸는 일과 왜 그게 유용한가
    - **코사인 유사도**로 "의미가 비슷하다" 를 측정
    - **벡터 DB** (Chroma · Qdrant · Pinecone) 가 하는 일
    - **ANN**(Approximate Nearest Neighbor) 의 존재 이유 (왜 완전 탐색이 아닌가)
    - 차원 불일치 · 언어 혼용 · 정규화 같은 **현실의 함정**

!!! quote "전제"
    [Ch 9](09-why-rag.md) "왜 RAG인가" 읽고 RAG 의 필요성 이해한 상태.

---

## 1. 개념 — 문장을 숫자로

사람은 "**강아지**"와 "**고양이**"가 비슷하고, "**강아지**"와 "**피자**"가 멀다는 걸 직관적으로 압니다. 컴퓨터는? **문자 자체로는** 강아지·고양이·피자가 모두 "서로 다른 문자열".

**임베딩**은 이 직관을 숫자로 바꾸는 기법:

```
"강아지" → [0.12, -0.03, 0.87, ..., 0.41]  (1536개 수)
"고양이" → [0.14, -0.01, 0.82, ..., 0.39]  (강아지와 거의 비슷한 방향)
"피자"   → [-0.40, 0.78, -0.12, ..., 0.05] (완전히 다른 방향)
```

비슷한 의미는 **가까운 벡터**로. 그게 전부입니다.

![의미 공간](../assets/diagrams/ch10-semantic-space.svg#only-light)
![의미 공간](../assets/diagrams/ch10-semantic-space-dark.svg#only-dark)

실제는 1536차원 (OpenAI `text-embedding-3-small`) 같은 고차원 공간. 위 그림은 2차원으로 축소한 개념 시각화.

---

## 2. 왜 필요한가 — 키워드 검색의 한계

전통 키워드 검색 (BM25 등) 은 **단어가 일치** 해야 찾음:

| 쿼리 | 전통 검색 결과 |
|---|---|
| "환불" | "환불" 단어 포함한 문서만 |
| "돈 돌려받기" | "환불" 문서 **못 찾음** (키워드 불일치) |
| "refund policy" | 한국어 문서 **못 찾음** |

임베딩 기반 **의미 검색**은 **같은 의미**를 찾음:

- "돈 돌려받기" ≈ "환불" → 같은 클러스터
- "refund policy" ≈ "환불 정책" (다국어 모델이면)

이게 RAG 검색의 기반입니다.

---

## 3. 어디에 쓰이는가

- **RAG 검색** — Part 3 의 본업
- **시맨틱 검색** — 사내 위키·코드 검색
- **추천** — 비슷한 상품·컨텐츠 찾기
- **중복 탐지** — 유사 문서 클러스터링
- **분류** (zero-shot) — 카테고리 레이블의 임베딩과 비교

---

## 4. 최소 예제 — 문장 3개의 유사도

```bash
pip install openai numpy
```

```python title="similarity.py" linenums="1" hl_lines="8 9 10"
from openai import OpenAI
import numpy as np

client = OpenAI()

sentences = ["강아지가 짖는다", "개가 멍멍 운다", "피자가 맛있다"]

res = client.embeddings.create(           # (1)!
    model="text-embedding-3-small",
    input=sentences,
)
vecs = np.array([d.embedding for d in res.data])

def cosine(a, b):                         # (2)!
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

print(f"강아지-개:   {cosine(vecs[0], vecs[1]):.3f}")   # 약 0.85~0.95 예상
print(f"강아지-피자: {cosine(vecs[0], vecs[2]):.3f}")   # 약 0.20~0.40 예상
```

1. OpenAI 임베딩 모델. Anthropic은 임베딩 API 가 따로 없어 **Voyage AI** 권장.
2. **코사인 유사도**: 두 벡터의 각도. -1~1 범위. 1에 가까울수록 유사.

"강아지-개" 는 0.9 근처 · "강아지-피자" 는 0.3 근처 로 나와야 **임베딩 모델이 잘 작동하는 것**. 이게 0.5 이상이면 모델이 너무 뭉툭하거나 한국어 성능이 약하다는 신호.

---

## 5. 실전 튜토리얼

### 5.1 임베딩 모델 선택

| 모델 | 차원 | 한국어 | 비용 | 메모 |
|---|:-:|:-:|:-:|---|
| **OpenAI** `text-embedding-3-small` | 1536 | △ | $ | 범용·저렴 |
| **OpenAI** `text-embedding-3-large` | 3072 | ○ | $$$ | 품질↑ |
| **Voyage** `voyage-3` | 1024 | ○ | $$ | Anthropic 추천 |
| **BGE-M3** (오픈소스) | 1024 | ○○ | 무료 (로컬 GPU) | 다국어 강함 |
| **sentence-transformers** (오픈) | 384~768 | △ | 무료 | 경량·빠름 |

**선택 기준**:
- 한국어 비중 높음 → **BGE-M3** 또는 **Voyage**
- 프로토타입 → **OpenAI small**
- GPU 있음 → **BGE-M3** 로컬
- Anthropic 생태계 고수 → **Voyage** (Anthropic 공식 권장)

### 5.2 코사인 유사도 · 정규화

```python title="cosine_math.py" linenums="1"
import numpy as np

def cosine(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# 정규화된 벡터라면 dot product = cosine similarity
def cosine_normalized(a, b):
    return np.dot(a, b)  # (1)!

# OpenAI/Voyage 임베딩은 대부분 L2 normalized (length=1) 로 옴
# → 성능 최적화를 위해 미리 정규화해 저장, 검색 시 dot product 만
```

1. **수백만 문서에서 검색할 때는** 이 최적화가 중요. `np.dot` 은 GPU/BLAS 최적화.

### 5.3 벡터 DB — Chroma 실습

수백만 문서에서 top-k 찾기는 **벡터 DB** 에 맡깁니다. **Chroma** 가 시작하기 가장 쉬움:

```bash
pip install chromadb
```

```python title="chroma_basic.py" linenums="1" hl_lines="4 12 17"
import chromadb
from openai import OpenAI

chroma = chromadb.PersistentClient(path="./chroma_db")   # (1)!
client = OpenAI()

def embed(texts: list[str]) -> list[list[float]]:
    res = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [d.embedding for d in res.data]

# 컬렉션 생성 (테이블 느낌)
col = chroma.get_or_create_collection(name="faq_kb")

docs = [
    "환불은 구매 후 7일 이내 신청 가능. 팀장 승인 필요.",
    "배송은 주문일 기준 영업일 2~3일 소요.",
    "포인트는 구매 금액의 1% 적립, 3개월 이내 사용.",
]
col.add(                                              # (2)!
    ids=[f"doc-{i}" for i in range(len(docs))],
    documents=docs,
    embeddings=embed(docs),
    metadatas=[{"source": "policy.md"} for _ in docs],
)

# 검색
query = "돈 돌려받으려면?"
q_emb = embed([query])[0]
result = col.query(query_embeddings=[q_emb], n_results=2)   # (3)!

for doc, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
    print(f"distance={dist:.3f}  [{meta['source']}]  {doc}")
```

1. 로컬 디스크에 저장 (`./chroma_db/`). 메모리 전용은 `chromadb.Client()`.
2. 문서 · 벡터 · 메타데이터 함께 저장. 메타데이터는 **필터링**·**citation** 에 씀.
3. 쿼리 벡터로 top-k. **distance** 는 거리 (낮을수록 가까움). cosine distance 면 `0 = 완전 일치`.

### 5.4 ANN — 왜 완전 탐색이 아닌가

100만 문서에서 top-10 찾으려면 **100만 번 코사인** 계산. 너무 느림.

**ANN (Approximate Nearest Neighbor)** 는 **근사 답** 을 빠르게 반환:

- **HNSW** (Hierarchical Navigable Small World) — 계층적 그래프 탐색. Chroma·Qdrant 기본
- **IVF** (Inverted File) — 클러스터 먼저 좁히기
- **PQ** (Product Quantization) — 벡터 압축으로 메모리 절약

정확도 99% 라면 **100배 빠르게** 얻음. Part 3의 이 시점에선 "ANN 이 있다" 만 알아도 OK — 벡터 DB가 알아서 씀.

### 5.5 쿼리 vs 문서 임베딩 — Asymmetric

같은 모델로 쿼리와 문서를 임베딩할 때 보통 OK. 하지만 **긴 문서 vs 짧은 쿼리** 에서는 최신 모델들이 **role 지시** 를 지원합니다.

**Voyage** 예:

```python
# 문서 임베딩 (저장용)
client.embed(texts=docs, input_type="document")

# 쿼리 임베딩 (검색용)
client.embed(texts=[query], input_type="query")
```

이걸 **symmetric vs asymmetric** 임베딩이라고 부름. 정확도 차이가 크면 쿼리/문서별로 다르게.

---

## 6. 자주 깨지는 포인트

!!! warning "실수 1. 차원 불일치"
    OpenAI small(1536) 로 임베딩한 컬렉션에 Voyage(1024) 임베딩을 추가하면 폭발. 또는 모델 업그레이드 시 차원이 바뀌면 기존 DB 무용.  
    **대응**: 컬렉션 메타데이터에 `embedding_model` 기록. 모델 변경 시 **전체 재임베딩**. 생각보다 자주 겪음.

!!! warning "실수 2. 정규화 여부 혼선"
    어떤 모델은 L2 normalized (length=1) 로 반환, 어떤 건 아님. 정규화 안 된 걸 cosine 대신 dot product 하면 값이 이상.  
    **대응**: 임베딩 직후 `vec / np.linalg.norm(vec)` 로 강제 정규화. 벡터 DB 가 cosine distance 를 쓴다면 내부적으로 처리.

!!! warning "실수 3. 언어 혼용"
    한국어 문서 + 영어 쿼리 (또는 반대) 는 **다국어 모델** 아니면 품질 급락.  
    **대응**: Voyage · BGE-M3 · OpenAI `text-embedding-3-large` 중 다국어 벤치 확인. 한국어 전용 필요 시 KURE · KoE5 류 검토.

!!! warning "실수 4. 짧은 쿼리에 과대해석"
    "환불" 한 단어 쿼리는 임베딩의 분산이 커서 노이즈. 자주 무관한 문서가 top-k 에 올라옴.  
    **대응**: (a) HyDE (Ch 13) 로 가상 답변을 임베딩, (b) 키워드 하이브리드 검색 (Ch 12), (c) 쿼리 확장 프롬프트.

!!! warning "실수 5. 메타데이터 없이 저장"
    나중에 "이 답이 어느 문서/어느 섹션에서 왔냐" 를 모름. Citation 불가, 권한 필터링 불가.  
    **대응**: **저장 시점**에 `source`, `page`, `section`, `updated_at`, `owner` 같은 메타 항상 함께.

---

## 7. 운영 시 체크할 점

- [ ] **임베딩 모델 · 차원 · 버전** 을 컬렉션 메타에 기록
- [ ] **정규화 전략** 일관성 (문서·쿼리 모두 같은 방식)
- [ ] **언어 분포** 로그 (쿼리·문서의 언어 비율) → 모델 교체 판단
- [ ] **재임베딩 스크립트** 항상 준비 (모델 변경 시 배치 실행)
- [ ] **메타데이터 필터링** 활성화 (`updated_at >= X`, `owner == Y`)
- [ ] **벡터 DB 백업** 주기 (대량 임베딩 재생성 비용 높음)
- [ ] **검색 지연** 모니터링 (p95 > 300ms면 ANN 파라미터 튜닝)
- [ ] **PII 임베딩 주의** — 개인정보가 벡터에 녹아 있을 수 있음 (복원 공격 연구 있음)

---

## 8. 확인 문제

- [ ] §4 `similarity.py` 를 한국어 · 영어 · 동의어·반의어 쌍으로 10개 돌려 유사도 분포 표 만들기
- [ ] §5.3 Chroma 예제에 자기 FAQ 5~10건 넣고 다양한 쿼리로 top-k 품질 관찰
- [ ] 같은 문서에 **OpenAI small vs Voyage-3** 를 둘 다 돌려 상위 3개 결과가 얼마나 다른지 비교
- [ ] 일부러 **정규화 안 한 벡터**로 cosine similarity 계산해 값이 어떻게 튀는지 확인
- [ ] 한국어 질문에 영어 문서 섞어 놓고 top-k 품질 측정. 다국어 모델 필요성 체감

---

## 9. 원전 · 더 읽을 거리

- **OpenAI Embeddings**: [platform.openai.com/docs/guides/embeddings](https://platform.openai.com/docs){target=_blank}
- **Voyage AI**: [docs.voyageai.com](https://docs.voyageai.com){target=_blank} — Anthropic 공식 추천
- **BGE-M3** (오픈소스 다국어): huggingface.co/BAAI/bge-m3
- **Chroma**: [docs.trychroma.com](https://docs.trychroma.com){target=_blank}
- **HNSW 논문** — Malkov & Yashunin (2018), *"Efficient and Robust ANN Search Using Hierarchical NSW Graphs"*
- **Stanford CME 295 Lec 7** — 프로젝트 `_research/stanford-cme295.md`

---

**다음 챕터** → [Ch 11. RAG 파이프라인 전체 흐름](11-pipeline.md) :material-arrow-right:  
임베딩 + 벡터 DB 는 재료. 다음은 **문서 수집부터 citation까지 end-to-end** 흐름.
