"""Самописный посимвольный лексер для HTML-документов и фрагментов."""

from html import unescape


current_char = None
_html_source = ""
_pos = 0
_in_tag = False
_in_string = False
_target_quote = None
_raw_text_tag = None
_tag_name = None
_closing_tag = False
_after_equals = False


def _update_current_char() -> None:
    global current_char
    current_char = _html_source[_pos] if _pos < len(_html_source) else None


def init_lexer(html_text: str) -> None:
    """Начать разбор новой HTML-строки и сбросить состояние лексера."""
    global _html_source, _pos, _in_tag, _in_string, _target_quote
    global _raw_text_tag, _tag_name, _closing_tag, _after_equals
    if not isinstance(html_text, str):
        raise TypeError("HTML должен быть строкой")
    _html_source = html_text
    _pos = 0
    _in_tag = False
    _in_string = False
    _target_quote = None
    _raw_text_tag = None
    _tag_name = None
    _closing_tag = False
    _after_equals = False
    _update_current_char()


def _advance(count: int = 1) -> None:
    global _pos
    _pos = min(_pos + count, len(_html_source))
    _update_current_char()


def _is_tag_start(position: int) -> bool:
    """Проверить, начинается ли в позиции открывающий HTML-маркер."""
    if position >= len(_html_source) or _html_source[position] != "<":
        return False
    if _html_source.startswith("<!--", position) or _html_source.startswith("<!", position):
        return True
    next_pos = position + 1
    if next_pos < len(_html_source) and _html_source[next_pos] == "/":
        next_pos += 1
    return next_pos < len(_html_source) and _html_source[next_pos].isalpha()


def _read_text() -> tuple[str, str]:
    """Считать текст до следующего распознаваемого маркера тега."""
    global _raw_text_tag
    start = _pos
    if _raw_text_tag:
        marker = "</" + _raw_text_tag
        lower_source = _html_source.lower()
        end = lower_source.find(marker, _pos)
        if end < 0:
            end = len(_html_source)
        value = _html_source[start:end]
        tag = _raw_text_tag
        if tag in {"textarea", "title"}:
            value = unescape(value)
        _advance(end - _pos)
        if end < len(_html_source):
            _raw_text_tag = None
        return "TEXT", value

    while _pos < len(_html_source) and not _is_tag_start(_pos):
        _advance()
    value = unescape(_html_source[start:_pos])
    return "TEXT", value


def get_next_token():
    """Вернуть следующий токен ``(тип, значение)`` или ``None`` в конце ввода."""
    global _in_tag, _in_string, _target_quote, _raw_text_tag
    global _tag_name, _closing_tag, _after_equals

    while _pos < len(_html_source):
        if _in_string:
            if current_char == _target_quote:
                quote = _target_quote
                _advance()
                _in_string = False
                _target_quote = None
                return "QUOTE", quote
            start = _pos
            while _pos < len(_html_source) and current_char != _target_quote:
                _advance()
            return "STRING_VAL", unescape(_html_source[start:_pos])

        if not _in_tag:
            if _html_source.startswith("<!--", _pos):
                start = _pos + 4
                end = _html_source.find("-->", start)
                if end < 0:
                    value = _html_source[start:]
                    _advance(len(_html_source) - _pos)
                else:
                    value = _html_source[start:end]
                    _advance(end + 3 - _pos)
                return "COMMENT", value

            if _html_source[_pos:_pos + 9].lower().startswith("<!doctype"):
                start = _pos + 2
                quote = None
                end = start
                while end < len(_html_source):
                    char = _html_source[end]
                    if quote:
                        if char == quote:
                            quote = None
                    elif char in ('"', "'"):
                        quote = char
                    elif char == ">":
                        break
                    end += 1
                value = _html_source[start:end]
                _advance(min(end + 1, len(_html_source)) - _pos)
                return "DOCTYPE", value

            if _html_source.startswith("<![CDATA[", _pos):
                start = _pos + 9
                end = _html_source.find("]]>", start)
                if end < 0:
                    value = _html_source[start:]
                    _advance(len(_html_source) - _pos)
                else:
                    value = _html_source[start:end]
                    _advance(end + 3 - _pos)
                return "TEXT", value

            if _is_tag_start(_pos):
                _advance()
                _in_tag = True
                _tag_name = None
                _closing_tag = False
                return "TAG_OPEN", "<"

            return _read_text()

        if current_char in " \t\r\n\f":
            _advance()
            continue
        if current_char == ">":
            _advance()
            _in_tag = False
            if not _closing_tag and _tag_name:
                name = _tag_name.lower()
                if name in {"script", "style", "textarea", "title"}:
                    _raw_text_tag = name
            return "TAG_CLOSE", ">"
        if current_char == "/" and not _after_equals:
            if not _after_equals and (_tag_name is None or (_pos + 1 < len(_html_source) and _html_source[_pos + 1] == ">")):
                if _tag_name is None:
                    _closing_tag = True
                _advance()
                return "SLASH", "/"
        if current_char == "=":
            _advance()
            _after_equals = True
            return "EQUALS", "="
        if current_char in ('"', "'"):
            _after_equals = False
            _target_quote = current_char
            _in_string = True
            quote = current_char
            _advance()
            return "QUOTE", quote

        start = _pos
        while _pos < len(_html_source):
            if current_char in " \t\r\n\f=><\"'":
                break
            if current_char == "/" and not _after_equals and _pos + 1 < len(_html_source) and _html_source[_pos + 1] == ">":
                break
            _advance()
        if start == _pos:
            # Сохраняем неожиданный символ и продолжаем, не зацикливаясь.
            value = current_char
            _advance()
            return "NAME", value

        value = _html_source[start:_pos]
        _after_equals = False
        if _tag_name is None and value != "/":
            if value:
                _tag_name = value
        return "NAME", value

    return None

