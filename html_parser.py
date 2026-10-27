"""Построение простого дерева документа по токенам модуля :mod:`lexer`."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from lexer import get_next_token, init_lexer


@dataclass
class Node:
    """Узел документа, элемента, текста или комментария."""

    kind: str
    name: Optional[str] = None
    text: Optional[str] = None
    attributes: Dict[str, Optional[str]] = field(default_factory=dict)
    children: List["Node"] = field(default_factory=list)

    def add_child(self, node: "Node") -> None:
        self.children.append(node)


_VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


def _read_tag():
    """Считать токены после TAG_OPEN до TAG_CLOSE и вернуть части тега."""
    body = []
    while True:
        token = get_next_token()
        if token is None or token[0] == "TAG_CLOSE":
            break
        body.append(token)

    closing = bool(body and body[0] == ("SLASH", "/"))
    if closing:
        body = body[1:]

    name = None
    if body and body[0][0] == "NAME":
        name = body[0][1]
        body = body[1:]
    return closing, name, body


def _read_attributes(tokens):
    attributes = {}
    index = 0
    while index < len(tokens):
        token_type, name = tokens[index]
        if token_type != "NAME":
            index += 1
            continue

        value = None  # Логический атрибут без значения, например disabled.
        if index + 1 < len(tokens) and tokens[index + 1][0] == "EQUALS":
            index += 2
            if index < len(tokens) and tokens[index][0] == "QUOTE":
                index += 1
                value = ""
                if index < len(tokens) and tokens[index][0] == "STRING_VAL":
                    value = tokens[index][1]
                    index += 1
                if index < len(tokens) and tokens[index][0] == "QUOTE":
                    index += 1
            elif index < len(tokens):
                # Лексер распознаёт значение без кавычек как NAME.
                value = tokens[index][1]
                index += 1
        else:
            index += 1

        attributes[name] = value
    return attributes


def parse_html(html_text: str) -> Node:
    """Преобразовать HTML-строку в простое дерево документа.
    """
    init_lexer(html_text)
    document = Node(kind="document", name="#document")
    stack = [document]

    while True:
        token = get_next_token()
        if token is None:
            break

        token_type, value = token
        if token_type == "TEXT":
            stack[-1].add_child(Node(kind="text", text=value))
        elif token_type == "COMMENT":
            stack[-1].add_child(Node(kind="comment", text=value))
        elif token_type == "TAG_OPEN":
            closing, name, body = _read_tag_tokens()
            if not name:
                continue

            if closing:
                matching_index = next(
                    (i for i in range(len(stack) - 1, 0, -1)
                     if stack[i].name == name),
                    None,
                )
                if matching_index is not None:
                    del stack[matching_index:]
                continue

            attributes = _read_attributes(body)
            element = Node(kind="element", name=name, attributes=attributes)
            stack[-1].add_child(element)
            self_closing = bool(body and body[-1] == ("SLASH", "/"))
            if not self_closing and name.lower() not in _VOID_ELEMENTS:
                stack.append(element)

    return document


def _read_tag_tokens():
    """Считать оставшиеся токены тега после открывающего символа '<'."""
    return _read_tag()


def format_tree(node: Node, indent: int = 0) -> str:
    """Вернуть дерево документа в виде удобного для чтения текста с отступами."""
    prefix = "  " * indent
    if node.kind == "document":
        label = "#document"
    elif node.kind == "element":
        attrs = "".join(
            f' {name}' if value is None else f' {name}="{value}"'
            for name, value in node.attributes.items()
        )
        label = f"<{node.name}{attrs}>"
    elif node.kind == "text":
        label = f"#text {node.text!r}"
    else:
        label = f"#comment {node.text!r}"

    lines = [prefix + label]
    lines.extend(format_tree(child, indent + 1) for child in node.children)
    return "\n".join(lines)

