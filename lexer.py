"""
Модуль: lexer.py
Описание: Лексический анализатор HTML для учебного проекта браузера.
Реализует посимвольный разбор с использованием глобальной переменной
для текущего символа (lookahead) и выдачу токенов по одному за вызов.
"""

# 6. Глобальная переменная для хранения текущего (последнего прочитанного) символа
current_char = None

# Внутренние служебные переменные модуля
_html_source = ""
_pos = 0
_length = 0
_in_tag = False
_in_string = False
_target_quote = None


def init_lexer(html_text: str) -> None:
    """
    Инициализирует лексер новой HTML-строкой.
    Сбрасывает указатель и читает первый символ (смотрит на 1 символ вперед).
    """
    global _html_source, _pos, _length, current_char, _in_tag, _in_string, _target_quote
    _html_source = html_text
    _pos = 0
    _length = len(html_text)
    _in_tag = False
    _in_string = False
    _target_quote = None

    # 5. Смотрим на 1 символ вперед при старте
    if _length > 0:
        current_char = _html_source[_pos]
        _pos += 1
    else:
        current_char = None


def _advance() -> None:
    """
    Сдвигает указатель на 1 символ вперед и обновляет глобальную переменную current_char.
    """
    global _pos, current_char, _length
    if _pos < _length:
        current_char = _html_source[_pos]
        _pos += 1
    else:
        current_char = None


def _is_stop_char(ch: str) -> bool:
    """
    Проверяет, является ли переданный символ разделителем (стоп-символом)
    для имен тегов и атрибутов.
    """
    return ch in ' \t\r\n=/><"\''


def get_next_token():
    """
    3. Возвращает ровно ОДНУ лексему за один вызов.
    Использует глобальную переменную current_char.
    Возвращает пару (тип_токена, значение) или None, если текст закончился.
    """
    global _in_tag, _in_string, _target_quote, current_char

    while current_char is not None:
        # Если мы внутри кавычек (значение атрибута)
        if _in_string:
            if current_char == _target_quote:
                _in_string = False
                q = _target_quote
                _target_quote = None
                _advance()
                return ("QUOTE", q)
            else:
                val = ""
                while current_char is not None and current_char != _target_quote:
                    val += current_char
                    _advance()
                return ("STRING_VAL", val)

        # Пропускаем пробелы и переносы вне тегов
        if not _in_tag and current_char in ' \t\r\n':
            _advance()
            continue

        # Пропускаем пробелы внутри тегов
        if _in_tag and current_char in ' \t\r\n':
            _advance()
            continue

        if not _in_tag:
            # 1. Комментарии <!-- ... -->
            if current_char == '<' and _html_source.startswith("<!--", _pos - 1):
                comment_text = "<!--"
                _advance()
                _advance()
                _advance()
                _advance()
                while current_char is not None:
                    comment_text += current_char
                    if comment_text.endswith("-->"):
                        _advance()
                        break
                    _advance()
                return ("COMMENT", comment_text)

            # 2. Открывающий тег <
            if current_char == '<':
                _advance()
                _in_tag = True
                return ("TAG_OPEN", "<")

            # 3. Текст между тегами
            text_val = ""
            while current_char is not None and current_char != '<':
                text_val += current_char
                _advance()

            cleaned = text_val.strip()
            if cleaned:
                return ("TEXT", cleaned)
            continue

        else:
            # Внутри тега
            # 4. Слэш /
            if current_char == '/':
                _advance()
                return ("SLASH", "/")

            # 5. Закрывающая скобка >
            if current_char == '>':
                _advance()
                _in_tag = False
                return ("TAG_CLOSE", ">")

            # 6. Знак равенства =
            if current_char == '=':
                _advance()
                return ("EQUALS", "=")

            # 7. Кавычки (" или ')
            if current_char in ('"', "'"):
                _target_quote = current_char
                _in_string = True
                q = current_char
                _advance()
                return ("QUOTE", q)

            # 8. Имена тегов или атрибутов
            name_val = ""
            while current_char is not None and not _is_stop_char(current_char):
                name_val += current_char
                _advance()

            if name_val:
                return ("NAME", name_val)

    return None
