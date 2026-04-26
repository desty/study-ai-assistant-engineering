"""Insert Colab badge after the H1 of a chapter md file."""
from __future__ import annotations
import sys
from pathlib import Path

BADGE = '''<a class="colab-badge" href="https://colab.research.google.com/github/desty/study-ai-assistant-engineering/blob/main/{nb}" target="_blank">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open in Colab">
</a>
'''


def main():
    md_path = Path(sys.argv[1])
    nb_rel = sys.argv[2]  # e.g. notebooks/part6/ch26_prod_arch.ipynb
    text = md_path.read_text(encoding="utf-8")
    if "colab-badge" in text:
        print(f"skip (already has badge): {md_path}")
        return
    lines = text.splitlines(keepends=True)
    # Insert after line 1 (title) + blank line
    out = [lines[0]]
    if len(lines) > 1 and lines[1].strip() == "":
        out.append(lines[1])
        rest_idx = 2
    else:
        out.append("\n")
        rest_idx = 1
    out.append(BADGE.format(nb=nb_rel) + "\n")
    out.extend(lines[rest_idx:])
    md_path.write_text("".join(out), encoding="utf-8")
    print(f"added badge: {md_path} -> {nb_rel}")


if __name__ == "__main__":
    main()
