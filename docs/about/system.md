# 학습 시스템

이 사이트는 **"책처럼 읽고, 실습으로 완성"** 하는 학습 시스템입니다. 한 번 끝까지 달리면 하나의 AI 어시스턴트를 직접 만들 수 있도록 챕터가 서로 연결됩니다.

!!! abstract "설계 원칙"
    - **순서가 있는 책** — 블로그처럼 흩어진 글이 아니라, 앞 챕터가 뒤 챕터의 전제가 된다.
    - **개념은 그림 먼저** — 텍스트보다 다이어그램·표·인포그래픽이 먼저 온다.
    - **코드는 복붙 가능** — Colab 원클릭, 라인 강조, 주석 툴팁.
    - **함정을 숨기지 않는다** — 튜토리얼 끝에는 항상 "자주 하는 실수"가 붙는다.

---

## 1. 사이트 구조

![사이트 맵](../assets/diagrams/sitemap.svg#only-light)
![사이트 맵](../assets/diagrams/sitemap-dark.svg#only-dark)

Part 1 → 2 → ... → 7 은 **순차 전제**. 앞 챕터를 건너뛰면 뒤가 공중에 뜹니다.

## 2. 챕터 템플릿

모든 챕터는 아래 **8단계** 구조를 따릅니다. 한 챕터 = 한 호흡으로 읽히도록 **20~40분** 분량을 목표로 합니다.

| # | 섹션 | 목적 | 도구 |
|---|---|---|---|
| 1 | **개념 설명** | 정의와 직관 | 본문 · 비유 |
| 2 | **왜 필요한가** | 문제 맥락 | 표 · admonition |
| 3 | **어디에 쓰이는가** | 실제 유즈케이스 | 표 · 예시 |
| 4 | **최소 예제** | 가장 짧은 작동 코드 | 코드 블록 |
| 5 | **실전 튜토리얼** | 손으로 돌려보기 | Colab 배지 + 탭 + 코드 |
| 6 | **자주 깨지는 포인트** | 디버깅 포인트 | `!!! warning` |
| 7 | **운영 시 체크할 점** | 프로덕션 고려사항 | 체크리스트 |
| 8 | **연습문제 & 다음 챕터** | 손 실습 · 링크 | 태스크 리스트 |

## 3. 기술 스택

<div class="infocards" markdown>

<div class="card" markdown>
#### :material-language-python: MkDocs Material
Python 친화적인 정적 사이트 엔진. 다크모드·검색·사이드바 기본 내장.
</div>

<div class="card" markdown>
#### :material-vector-polyline: diagram-svg 스킬
챕터 대표 SVG를 Python으로 직접 생성. `rsvg-convert`로 검증. 커스텀 디자인 시스템.
</div>

<div class="card" markdown>
#### :material-shape: `.diagram` HTML 컴포넌트
인라인 짧은 플로우용. 9가지 역할 색상 · 라이트/다크 자동 전환.
</div>

<div class="card" markdown>
#### :material-function-variant: MathJax
LaTeX 수식 렌더링. 모델·파인튜닝 챕터에 필수.
</div>

<div class="card" markdown>
#### :material-google-colab: Colab 배지
모든 실습은 브라우저에서 바로. GPU도 무료.
</div>

</div>

## 4. 코드·다이어그램 규칙

=== "코드 블록"

    - 파일명은 ` ```python title="app.py"` 로 명시
    - 핵심 줄은 `hl_lines="6 10"` 으로 강조
    - 설명이 필요한 줄에는 `# (1)!` 주석 앵커로 **주석 툴팁** 사용
    - 길이 상한: **40줄**. 넘으면 단계별로 쪼갠다

=== "시각화 도구 선택"

    **세 가지로 전체를 커버**:

    1. **시퀀스·스텝** → 마크다운 **표**
    2. **비교·요약 카드** → **`.infocards`** HTML
    3. **모든 다이어그램** → **`diagram-svg` 스킬** (`.claude/skills/diagram-svg/`) → Python 제너레이터로 생성하고 `docs/assets/diagrams/*.svg` 로 저장

    9가지 역할 색상 · 동일 팔레트 · light/dark 페어를 **하나의 디자인 시스템**으로 공유합니다.

=== "SVG 다이어그램 워크플로"

    **소스**는 `_tools/gen_*.py` Python 제너레이터. **공용 모듈** `_tools/svg_prim.py` 의 primitives (node · arrow · group · legend) 를 조합해 사용.

    ```python
    from svg_prim import svg_header, svg_footer, node, arrow_line, ...

    def my_diagram(theme):
        lines = svg_header(960, 400, theme)
        # ... 노드/화살표/레전드
        lines.extend(svg_footer())
        return '\n'.join(lines)
    ```

    **light + dark 두 버전 저장 필수**:

    ```python
    with open('docs/assets/diagrams/my-thing.svg', 'w') as f:
        f.write(my_diagram('light'))
    with open('docs/assets/diagrams/my-thing-dark.svg', 'w') as f:
        f.write(my_diagram('dark'))
    ```

    **챕터에서 embed** — Material의 `#only-light` / `#only-dark` 페어:

    ```markdown
    ![alt](../assets/diagrams/my-thing.svg#only-light)
    ![alt](../assets/diagrams/my-thing-dark.svg#only-dark)
    ```

    **검증**: `rsvg-convert -w 1920 foo.svg -o foo.png` 로 실제 렌더링 확인. PNG는 verification-only — git 제외(`.gitignore`).

    자세한 규칙: [`.claude/skills/diagram-svg/SKILL.md`](https://github.com/).

=== "표"

    - 개념 4~7개 비교에만 사용
    - 첫 열은 항상 **용어/이름**, 마지막 열은 **왜 중요한가** 또는 **사용 시점**

=== "ASCII art 정렬 금지"

    `↑` · `|` · 공백으로 문자를 세로로 맞추는 의사 다이어그램은 **쓰지 않습니다**.

    한글·영문·이모지·문장부호의 **렌더링 너비가 전부 다르기** 때문. 코드블록(monospace)에서도 깨지고 본문(proportional)에서는 더 심하게 깨짐. 사용자 폰트·브라우저·OS에 따라 결과가 달라 예측 불가능.

    | 상황 | 대안 |
    |---|---|
    | 2차원 관계 (원문 ↔ 분리 ↔ 라벨) | **표(table)** |
    | 흐름·화살표·계층 | **SVG** (diagram-svg 스킬) |
    | 단일 줄 내 강조 | 인라인 코드 또는 `<mark>` |

## 5. 새 챕터 추가하기

```bash title="로컬 개발"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/mkdocs serve
```

1. `docs/partN/` 아래에 `NN-슬러그.md` 생성
2. **템플릿 8단계**를 그대로 채운다
3. 시그니처 비주얼이 필요하면 `docs/assets/diagrams/<chapter>-<purpose>.svg` 로 생성 (diagram-svg 스킬)
4. `mkdocs.yml`의 `nav:`에 추가
5. `mkdocs build --strict` 로 경고 없이 빌드되는지 확인

!!! tip "품질 체크리스트"
    - [ ] 다이어그램이 **본문 첫 스크롤** 안에 있는가
    - [ ] 코드 블록에 파일명과 라인 강조가 있는가
    - [ ] "자주 하는 실수" 한 개 이상
    - [ ] 다음 챕터로 가는 링크가 있는가

## 6. 배포

GitHub Actions 워크플로우가 준비되어 있습니다 — `main` 브랜치 push 시 자동으로:

1. `mkdocs build --strict` 로 빌드
2. `actions/upload-pages-artifact@v3` 로 아티팩트 업로드
3. `actions/deploy-pages@v4` 로 GitHub Pages 배포

로컬 미리보기는 `mkdocs serve` 로 충분합니다. 레포 Settings → Pages → Source 를 **"GitHub Actions"** 로 설정해두면 됩니다.
