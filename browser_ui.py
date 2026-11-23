"""Простой интерфейс PyQt для вывода текста HTML-страниц."""

import sys
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from html_parser import parse_html
from text_extractor import extract_text


def _normalize_address(value: str) -> str:
    address = value.strip()
    if not address:
        raise ValueError("Введите адрес страницы или выберите HTML-файл.")

    local_path = Path(address).expanduser()
    if local_path.is_file():
        return local_path.resolve().as_uri()

    parsed = urlsplit(address)
    if parsed.scheme:
        if parsed.scheme.lower() not in {"http", "https", "file"}:
            raise ValueError("Поддерживаются только адреса HTTP, HTTPS и локальные файлы.")
        return address

    return "https://" + address


def _load_page(address: str) -> tuple[str, str]:
    request = Request(address, headers={"User-Agent": "TextOnlyHTMLBrowser/1.0"})
    with urlopen(request, timeout=20) as response:
        data = response.read()
        final_address = response.geturl()
        charset = response.headers.get_content_charset() or "utf-8"
    try:
        source = data.decode(charset, errors="replace")
    except LookupError:
        source = data.decode("utf-8", errors="replace")
    return source, final_address


class TextBrowserWindow(QMainWindow):
    """Окно для загрузки страницы и просмотра её текста без оформления."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Текстовый HTML-браузер")
        self.resize(900, 650)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Введите URL или путь к HTML-файлу")
        self.address_input.returnPressed.connect(self.open_page)

        self.open_button = QPushButton("Открыть")
        self.open_button.clicked.connect(self.open_page)

        self.file_button = QPushButton("Выбрать файл")
        self.file_button.clicked.connect(self.choose_file)

        address_layout = QHBoxLayout()
        address_layout.addWidget(self.address_input, 1)
        address_layout.addWidget(self.open_button)
        address_layout.addWidget(self.file_button)

        self.text_view = QPlainTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setPlaceholderText("Здесь появится текст страницы без оформления.")

        layout = QVBoxLayout()
        layout.addLayout(address_layout)
        layout.addWidget(self.text_view, 1)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.statusBar().showMessage("Откройте веб-адрес или HTML-файл")

    def choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть HTML-файл",
            "",
            "HTML-файлы (*.html *.htm);;Все файлы (*)",
        )
        if path:
            self.address_input.setText(path)
            self.open_page()

    def open_page(self) -> None:
        try:
            address = _normalize_address(self.address_input.text())
            source, final_address = _load_page(address)
            plain_text = extract_text(parse_html(source))
        except (OSError, URLError, ValueError) as error:
            QMessageBox.warning(self, "Не удалось открыть страницу", str(error))
            self.statusBar().showMessage("Не удалось открыть страницу")
            return
        except Exception as error:
            QMessageBox.warning(self, "Ошибка обработки страницы", str(error))
            self.statusBar().showMessage("Ошибка обработки страницы")
            return

        self.address_input.setText(final_address)
        self.text_view.setPlainText(plain_text)
        self.setWindowTitle(final_address + " — Текстовый HTML-браузер")
        self.statusBar().showMessage("Страница загружена; отображается только текст", 5000)


def run() -> int:
    app = QApplication(sys.argv)
    window = TextBrowserWindow()
    window.show()
    return app.exec()

