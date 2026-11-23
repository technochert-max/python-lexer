"""Самописное построение упрощённого дерева из HTML-токенов."""

from dataclasses import dataclass, field
import re
from typing import Dict, List, Optional

from lexer import get_next_token, init_lexer


@dataclass
class Node:
    """Узел документа, элемента, текста, комментария или doctype."""

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
_P_CLOSERS = {
    "address", "article", "aside", "blockquote", "div", "dl", "fieldset",
    "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header",
    "hr", "main", "nav", "ol", "p", "pre", "section", "table", "ul",
}


def _read_tag():
    """Считать содержимое тега до закрывающей скобки и разделить его части."""
    tokens = []
    while True:
        token = get_next_token()
        if token is None or token[0] == "TAG_CLOSE":
            break
        tokens.append(token)

    closing = bool(tokens and tokens[0] == ("SLASH", "/"))
    if closing:
        tokens.pop(0)
    name = None
    if tokens and tokens[0][0] == "NAME":
        name = tokens.pop(0)[1]
    return closing, name, tokens


def _read_attributes(tokens):
    """Собрать пары имя-значение из токенов атрибутов."""
    attributes = {}
    index = 0
    while index < len(tokens):
        if tokens[index][0] != "NAME":
            index += 1
            continue

        name = tokens[index][1]
        index += 1
        value = None
        if index < len(tokens) and tokens[index][0] == "EQUALS":
            index += 1
            if index < len(tokens) and tokens[index][0] == "QUOTE":
                index += 1
                value = ""
                if index < len(tokens) and tokens[index][0] == "STRING_VAL":
                    value = tokens[index][1]
                    index += 1
                if index < len(tokens) and tokens[index][0] == "QUOTE":
                    index += 1
            elif index < len(tokens) and tokens[index][0] == "NAME":
                value = tokens[index][1]
                index += 1
        attributes[name] = value
    return attributes


def _parse_doctype(value: str) -> Node:
    """Преобразовать объявление doctype в отдельный узел."""
    match = re.match(r"!\s*doctype\s+([^\s>]+)(.*)", value, re.IGNORECASE | re.DOTALL)
    if not match:
        return Node(kind="doctype", name="html")
    name, rest = match.groups()
    quoted = re.findall(r"(['\"])(.*?)\1", rest)
    attributes = {}
    if "public" in rest.lower() and quoted:
        attributes["public"] = quoted[0][1]
        if len(quoted) > 1:
            attributes["system"] = quoted[1][1]
    elif "system" in rest.lower() and quoted:
        attributes["system"] = quoted[0][1]
    return Node(kind="doctype", name=name.lower(), attributes=attributes)


def _close_open_element(stack, names) -> None:
    """Закрыть открытый элемент из набора, если он есть на стеке."""
    for index in range(len(stack) - 1, 0, -1):
        if (stack[index].name or "").lower() in names:
            del stack[index:]
            return


def parse_html(html_text: str) -> Node:
    """Разобрать HTML собственным лексером и построить дерево узлов.

    Поддерживаются типовые теги, атрибуты, сущности, комментарии, doctype,
    пустые элементы и часть правил исправления ошибочной вложенности.
    Это не полная реализация стандарта HTML для браузеров.
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
            if value:
                stack[-1].add_child(Node(kind="text", text=value))
        elif token_type == "COMMENT":
            stack[-1].add_child(Node(kind="comment", text=value))
        elif token_type == "DOCTYPE":
            document.add_child(_parse_doctype(value))
        elif token_type == "TAG_OPEN":
            closing, name, body = _read_tag()
            if not name:
                continue
            normalized_name = name.lower()

            if closing:
                matching_index = next(
                    (i for i in range(len(stack) - 1, 0, -1)
                     if (stack[i].name or "").lower() == normalized_name),
                    None,
                )
                if matching_index is not None:
                    del stack[matching_index:]
                continue

            if normalized_name == "li":
                _close_open_element(stack, {"li"})
            elif normalized_name in {"dt", "dd"}:
                _close_open_element(stack, {"dt", "dd"})
            elif normalized_name == "option":
                _close_open_element(stack, {"option"})
            elif normalized_name == "optgroup":
                _close_open_element(stack, {"option", "optgroup"})
            elif normalized_name in {"td", "th"}:
                _close_open_element(stack, {"td", "th"})
            elif normalized_name == "tr":
                _close_open_element(stack, {"td", "th", "tr"})
            elif normalized_name in {"thead", "tbody", "tfoot"}:
                _close_open_element(stack, {"td", "th", "tr", "thead", "tbody", "tfoot"})
            if normalized_name in _P_CLOSERS:
                _close_open_element(stack, {"p"})

            element = Node(
                kind="element",
                name=normalized_name,
                attributes=_read_attributes(body),
            )
            stack[-1].add_child(element)
            self_closing = bool(body and body[-1] == ("SLASH", "/"))
            if not self_closing and normalized_name not in _VOID_ELEMENTS:
                stack.append(element)

    return document


def format_tree(node: Node, indent: int = 0) -> str:
    """Вернуть дерево документа в виде текста с отступами."""
    prefix = "  " * indent
    if node.kind == "document":
        label = "#document"
    elif node.kind == "doctype":
        label = f"<!DOCTYPE {node.name}"
        if "public" in node.attributes:
            label += f' PUBLIC "{node.attributes["public"]}"'
        if "system" in node.attributes:
            if "public" in node.attributes:
                label += f' "{node.attributes["system"]}"'
            else:
                label += f' SYSTEM "{node.attributes["system"]}"'
        label += ">"
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

