# AI Assistant Engineering

> RAG · Agents · Evaluation · Production LLM Systems 을 책처럼 읽고 실습으로 완성하는 가이드.

**📖 사이트**: https://desty.github.io/study-ai-assistant-engineering/

## 무엇인가

초보자부터 엔터프라이즈급 AI Assistant 개발·운영까지, **모델을 깊게 파기 전에 구조를 이해**하는 것을 목표로 하는 7 Part · 34 챕터 학습 가이드.

진행 구성: 개념 30% · 실습 50% · 리뷰 20% · 캡스톤 1개(Self-Improving Assistant).

## 커리큘럼

| Part | 주제 | 챕터 수 |
|---|---|:-:|
| 1 | 입문 — 왜 모델이 필요한가 | 3 |
| 2 | Python 으로 LLM 다루기 | 5 |
| 3 | RAG | 6 |
| 4 | 평가 · 추론 품질 · 디버깅 | 5 |
| 5 | Agent & LangGraph | 6 |
| 6 | 운영형 AI Assistant | 5 |
| 7 | 모델 & 파인튜닝 | 4 |
| 캡스톤 | Self-Improving Assistant | 1 |

## 로컬 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdocs serve -a 127.0.0.1:8765
```

## 빌드 / 배포

- `mkdocs build --strict` 로 경고 없이 빌드되는 게 기본 상태
- `main` 푸시 시 `.github/workflows/deploy.yml` 이 GitHub Pages 로 자동 배포

## 다이어그램

모든 SVG 는 `_tools/gen_*.py` 파이썬 제너레이터로 생성. 공용 primitives 는 `_tools/svg_prim.py`. light / dark 페어 구조.

## 라이선스

저자 학습 목적 공개. 외부 인용은 본문에 출처 표기.
