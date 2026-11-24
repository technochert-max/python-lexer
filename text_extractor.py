"""Извлечение обычного текста из дерева HTML проекта."""

import re

from html_parser import Node


_BLOCK_ELEMENTS = {
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl",
    "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2",
    "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol",
    "p", "pre", "section", "table", "tbody", "td", "tfoot", "th", "thead",
    "tr", "ul",
}
_IGNORED_ELEMENTS = {"head", "script", "style", "template"}


def extract_text(root: Node) -> str:
    """Вернуть видимый текст страницы без CSS, скриптов и HTML-разметки."""
    pieces = []

    def visit(node: Node) -> None:
        if node.kind == "text":
            pieces.append(node.text or "")
            return
        if node.kind not in {"document", "element"}:
            return

        name = (node.name or "").lower() if node.kind == "element" else ""
        if name in _IGNORED_ELEMENTS:
            return
        if name in _BLOCK_ELEMENTS:
            pieces.append("\n")
        for child in node.children:
            visit(child)
        if name in _BLOCK_ELEMENTS:
            pieces.append("\n")

    visit(root)
    raw_text = "".join(pieces).replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in raw_text.split("\n"):
        cleaned = re.sub(r"[\t\f\v ]+", " ", line).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)

