from __future__ import annotations

from pydantic import BaseModel
from typing import Optional, Iterable
import html
import re
from datetime import datetime


class JSONLItem(BaseModel):
    id: str
    latex: str
    inline: bool = False
    caption: Optional[str] = None


_BANNED_CMDS = re.compile(r"\\(write|input|include|openout|read|file|loop|repeat|csname|immediate)\b")


def _strip_wrappers(latex: str) -> str:
    s = latex.strip()
    # remove $ wrappers and display math brackets \[ \]
    s = s.replace("\\[", "").replace("\\]", "")
    s = s.replace("$", "")
    return s.strip()


def _normalize_macros(latex: str) -> str:
    s = latex
    s = s.replace("\\dfrac", "\\frac")
    # Minimize \left \right (simple removal; not perfect but preferred in spec)
    s = s.replace("\\left", "").replace("\\right", "")
    return s


def _check_brackets(s: str) -> None:
    # lightweight bracket balance check for {}, (), []
    pairs = {')': '(', ']': '[', '}': '{'}
    stack: list[str] = []
    for ch in s:
        if ch in '([{':
            stack.append(ch)
        elif ch in ')]}':
            if not stack or stack[-1] != pairs[ch]:
                raise ValueError("Unbalanced brackets")
            stack.pop()
    if stack:
        raise ValueError("Unbalanced brackets")


def sanitize_item(item: JSONLItem) -> JSONLItem:
    if _BANNED_CMDS.search(item.latex):
        raise ValueError("Contains banned TeX command")
    body = _strip_wrappers(item.latex)
    body = _normalize_macros(body)
    _check_brackets(body)
    return JSONLItem(id=item.id, latex=body, inline=item.inline, caption=item.caption)


def _tex_preamble() -> str:
    return r"""\documentclass[11pt]{article}
\usepackage{amsmath,amssymb}
\usepackage[margin=1in]{geometry}
\setlength{\parskip}{0.5em}
\setlength{\parindent}{0pt}
\begin{document}
"""


def _tex_postamble() -> str:
    return r"""\end{document}
"""


def build_tex_from_items(items: Iterable[JSONLItem], batch_title: str = "Batch Summary") -> str:
    items = list(items)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = []
    lines.append(_tex_preamble())

    # Batch summary (H1 equivalent)
    lines.append(f"\\section*{{{batch_title}}}")
    lines.append(f"Total: {len(items)}\\\\ Generated at: {now}")

    # Body
    for it in items:
        safe_id = it.id
        lines.append(f"\\section*{{{safe_id}}}")
        if it.inline:
            # inline math in a paragraph (no numbering)
            lines.append(f"$ {it.latex} $")
        else:
            lines.append(f"\\begin{{equation}}\\label{{{safe_id}}}")
            lines.append(it.latex)
            lines.append("\\end{equation}")
        if it.caption:
            # small italic caption
            lines.append(f"\\par\\small\\textit{{{it.caption}}}")

    lines.append(_tex_postamble())
    return "\n".join(lines)

