"""Простой интерфейс PyQt для просмотра текста локальных HTML-файлов."""

import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from html_parser import parse_html
from text_extractor import extract_text


class TextBrowserWindow(QMainWindow):
    """Окно для открытия локального HTML-файла и просмотра его текста."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Текстовый HTML-браузер")
        self.resize(900, 650)

        self.file_label = QLabel("Файл не выбран")
        self.file_label.setWordWrap(True)

        self.file_button = QPushButton("Открыть HTML-файл")
        self.file_button.clicked.connect(self.open_file)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_label, 1)
        file_layout.addWidget(self.file_button)

        self.text_view = QPlainTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setPlaceholderText(
            "Здесь появится текст выбранного HTML-файла без оформления."
        )

        layout = QVBoxLayout()
        layout.addLayout(file_layout)
        layout.addWidget(self.text_view, 1)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.statusBar().showMessage("Выберите HTML-файл на компьютере")

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть HTML-файл",
            "",
            "HTML-файлы (*.html *.htm);;Все файлы (*)",
        )
        if not path:
            return

        try:
            source = Path(path).read_text(encoding="utf-8-sig", errors="replace")
            plain_text = extract_text(parse_html(source))
        except OSError as error:
            QMessageBox.warning(self, "Не удалось открыть файл", str(error))
            self.statusBar().showMessage("Не удалось открыть файл")
            return
        except Exception as error:
            QMessageBox.warning(self, "Ошибка обработки файла", str(error))
            self.statusBar().showMessage("Ошибка обработки файла")
            return

        self.file_label.setText(path)
        self.text_view.setPlainText(plain_text)
        self.setWindowTitle(f"{Path(path).name} — Текстовый HTML-браузер")
        self.statusBar().showMessage("Файл открыт; отображается только текст", 5000)


def run() -> int:
    app = QApplication(sys.argv)
    window = TextBrowserWindow()
    window.show()
    return app.exec()
