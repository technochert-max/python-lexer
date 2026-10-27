from html_parser import format_tree, parse_html

# Тестовый HTML-код
html_code = """
<div class="card">
    <p>Привет, мир!</p>
    <br />
</div>
"""

tree = parse_html(html_code)
print(format_tree(tree))

