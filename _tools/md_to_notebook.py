"""Convert chapter markdown -> Jupyter notebook.

Usage:
    python _tools/md_to_notebook.py docs/part5/20-what-is-agent.md notebooks/part5/ch20_what_is_agent.ipynb

Conversion rules:
    - Strip <a class="colab-badge"> block
    - !!! abstract block -> "## Abstract" + bullets
    - !!! quote / note / info / tip / warning blocks -> stripped or flattened
    - SVG image lines (![...](../assets/diagrams/...)) -> stripped
    - Code fences ```python ... ``` -> code cells (metadata stripped)
    - Other text becomes markdown cells; cells split at code block boundaries
    - Adds Dependencies + API Keys cells at top
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

DEPS = "!pip install -q anthropic openai chromadb langchain langgraph langchain-anthropic langchain-openai"
API_KEYS = """import os
from getpass import getpass

for k in ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY']:
    if not os.getenv(k):
        os.environ[k] = getpass(f'{k}: ')"""

WEB_BASE = "https://desty.github.io/study-ai-assistant-engineering"


def md_cell(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text}


def code_cell(code: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": code,
    }


def parse_md(md: str) -> tuple[str, str, list]:
    """Return (title, abstract_md, body_lines).

    body_lines is the post-frontmatter list of lines (without colab badge,
    abstract block, quote prefix block).
    """
    lines = md.splitlines()
    # Title
    title = lines[0].lstrip("# ").strip()
    rest = lines[1:]

    out: list[str] = []
    abstract_lines: list[str] = []
    i = 0
    while i < len(rest):
        line = rest[i]
        # Strip <a class="colab-badge"> block
        if '<a class="colab-badge"' in line:
            while i < len(rest) and "</a>" not in rest[i]:
                i += 1
            i += 1  # skip </a>
            continue
        # Abstract block
        if line.startswith('!!! abstract'):
            i += 1
            while i < len(rest) and (rest[i].startswith("    ") or rest[i].strip() == ""):
                if rest[i].startswith("    "):
                    abstract_lines.append(rest[i][4:])
                else:
                    abstract_lines.append("")
                i += 1
            continue
        # Quote / note / etc block
        m = re.match(r"^!!! (quote|note|info|tip|warning|danger|success|example)", line)
        if m:
            i += 1
            # skip indented body
            while i < len(rest) and (rest[i].startswith("    ") or rest[i].strip() == ""):
                i += 1
            continue
        out.append(line)
        i += 1

    # Strip SVG image lines (they don't render in colab)
    out = [ln for ln in out if not re.match(r"!\[.*\]\(\.\.?/assets/diagrams/.*\)", ln)]

    # Strip leading/trailing blank lines
    while out and out[0].strip() == "":
        out.pop(0)
    while out and out[-1].strip() == "":
        out.pop()

    abstract_md = "\n".join(abstract_lines).strip()
    return title, abstract_md, out


def build_cells(md_path: Path, web_path: str) -> list[dict]:
    md = md_path.read_text(encoding="utf-8")
    title, abstract_md, body_lines = parse_md(md)

    cells: list[dict] = []

    # Header cell
    header = (
        f"# {title}\n\n"
        f"**[원본 웹페이지]({WEB_BASE}/{web_path}/)**"
    )
    if abstract_md:
        header += f"\n\n## Abstract\n\n{abstract_md}"
    cells.append(md_cell(header))

    # Dependencies + API Keys
    cells.append(md_cell("## Dependencies"))
    cells.append(code_cell(DEPS))
    cells.append(md_cell("## API Keys"))
    cells.append(code_cell(API_KEYS))

    # Walk body, split at code fences
    buf: list[str] = []

    def flush_md():
        if not buf:
            return
        text = "\n".join(buf).strip("\n")
        if text.strip():
            cells.append(md_cell(text))
        buf.clear()

    i = 0
    in_code = False
    code_buf: list[str] = []
    for line in body_lines:
        if line.startswith("```"):
            if not in_code:
                # opening fence
                flush_md()
                in_code = True
                code_buf = []
            else:
                # closing fence -> emit code cell
                cells.append(code_cell("\n".join(code_buf)))
                in_code = False
                code_buf = []
            continue
        if in_code:
            code_buf.append(line)
        else:
            buf.append(line)
    flush_md()

    return cells


def main():
    if len(sys.argv) != 3:
        print("Usage: md_to_notebook.py <md_path> <notebook_path>")
        sys.exit(1)
    md_path = Path(sys.argv[1])
    nb_path = Path(sys.argv[2])

    # web_path = "partN/SS-slug" (no .md, no leading docs/)
    rel = md_path.relative_to("docs") if md_path.is_absolute() is False and "docs" in md_path.parts else Path(*md_path.parts[md_path.parts.index("docs") + 1:])
    web_path = str(rel.with_suffix(""))

    cells = build_cells(md_path, web_path)

    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.10.0",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    nb_path.parent.mkdir(parents=True, exist_ok=True)
    nb_path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {nb_path} ({len(cells)} cells)")


if __name__ == "__main__":
    main()
