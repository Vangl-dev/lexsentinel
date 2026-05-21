import sys
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox,
    QTextEdit,
)

from lexsentinel.analyzers.core import analyze
from lexsentinel.reports.html import render
from lexsentinel.reports.json import render_json
from lexsentinel.reports.pdf import render_pdf
from lexsentinel.sanitizer import sanitize_pdf
from lexsentinel.utils import default_output_name, sanitized_output_name


RISK_STYLES = {
    "SAFE": "background:#166534;color:white;padding:8px;border-radius:10px;font-weight:bold;",
    "SUSPICIOUS": "background:#ca8a04;color:white;padding:8px;border-radius:10px;font-weight:bold;",
    "HIGH RISK": "background:#ea580c;color:white;padding:8px;border-radius:10px;font-weight:bold;",
    "CRITICAL": "background:#dc2626;color:white;padding:8px;border-radius:10px;font-weight:bold;",
}


class LexSentinelApp(QWidget):
    def __init__(self):
        super().__init__()

        self.selected_pdf = None
        self.last_html = None
        self.last_pdf = None
        self.last_sanitized_pdf = None

        self.setWindowTitle("LexSentinel — Raio-X PDF")
        self.resize(760, 620)
        self.setAcceptDrops(True)

        self.setStyleSheet("""
            QTextEdit {
                padding: 6px;
            }
        """)    

        layout = QVBoxLayout()

        title = QLabel("LexSentinel")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("Análise defensiva de PDFs")
        layout.addWidget(subtitle)

        self.status = QLabel("Selecione ou arraste um PDF.")
        layout.addWidget(self.status)

        self.risk_badge = QLabel("SEM ANÁLISE")
        self.risk_badge.setStyleSheet(
            "background:#64748b;color:white;padding:8px;border-radius:10px;font-weight:bold;"
        )
        layout.addWidget(self.risk_badge)

        top_buttons = QHBoxLayout()

        self.select_btn = QPushButton("Selecionar PDF")
        self.select_btn.clicked.connect(self.select_pdf)
        top_buttons.addWidget(self.select_btn)

        self.analyze_btn = QPushButton("Analisar")
        self.analyze_btn.clicked.connect(self.run_analysis)
        top_buttons.addWidget(self.analyze_btn)

        self.sanitize_btn = QPushButton("Sanitizar")
        self.sanitize_btn.clicked.connect(self.run_sanitize)
        top_buttons.addWidget(self.sanitize_btn)

        layout.addLayout(top_buttons)

        open_buttons = QHBoxLayout()

        self.open_html_btn = QPushButton("Abrir HTML")
        self.open_html_btn.clicked.connect(self.open_html)
        self.open_html_btn.setEnabled(False)
        open_buttons.addWidget(self.open_html_btn)

        self.open_pdf_btn = QPushButton("Abrir PDF")
        self.open_pdf_btn.clicked.connect(self.open_pdf)
        self.open_pdf_btn.setEnabled(False)
        open_buttons.addWidget(self.open_pdf_btn)

        self.open_sanitized_btn = QPushButton("Abrir Sanitizado")
        self.open_sanitized_btn.clicked.connect(self.open_sanitized)
        self.open_sanitized_btn.setEnabled(False)
        open_buttons.addWidget(self.open_sanitized_btn)

        self.open_folder_btn = QPushButton("Abrir Pasta")
        self.open_folder_btn.clicked.connect(self.open_folder)
        self.open_folder_btn.setEnabled(False)
        open_buttons.addWidget(self.open_folder_btn)

        layout.addLayout(open_buttons)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.setLayout(layout)

    def reset_outputs(self):
        self.last_html = None
        self.last_pdf = None
        self.last_sanitized_pdf = None

        self.open_html_btn.setEnabled(False)
        self.open_pdf_btn.setEnabled(False)
        self.open_sanitized_btn.setEnabled(False)
        self.open_folder_btn.setEnabled(False)

        self.risk_badge.setText("SEM ANÁLISE")
        self.risk_badge.setStyleSheet(
            "background:#64748b;color:white;padding:8px;border-radius:10px;font-weight:bold;"
        )

    def log_message(self, msg):
        self.log.append(msg)

    def select_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar PDF",
            "",
            "PDF Files (*.pdf)"
        )

        if file_path:
            self.selected_pdf = file_path
            self.reset_outputs()
            self.status.setText(f"Selecionado: {Path(file_path).name}")
            self.log_message(f"PDF selecionado: {file_path}")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(".pdf"):
                self.selected_pdf = file_path
                self.reset_outputs()
                self.status.setText(f"Selecionado: {Path(file_path).name}")
                self.log_message(f"PDF arrastado: {file_path}")

    def run_analysis(self):
        if not self.selected_pdf:
            QMessageBox.warning(self, "Aviso", "Selecione um PDF primeiro.")
            return

        try:
            pdf_path = Path(self.selected_pdf)

            html_output = str(pdf_path.parent / default_output_name(self.selected_pdf))
            json_output = html_output.replace(".html", ".json")
            pdf_output = html_output.replace(".html", ".pdf")

            self.log_message("Iniciando análise...")

            result = analyze(self.selected_pdf, html_output)
            render(result, html_output)
            render_json(result, json_output)

            try:
                render_pdf(html_output, pdf_output)
            except Exception as e:
                result.errors.append(f"Falha PDF: {e}")

            self.last_html = html_output
            self.last_pdf = pdf_output

            self.open_html_btn.setEnabled(True)
            self.open_pdf_btn.setEnabled(True)
            self.open_folder_btn.setEnabled(True)

            self.risk_badge.setText(result.risk)
            self.risk_badge.setStyleSheet(
                RISK_STYLES.get(result.risk, RISK_STYLES["SUSPICIOUS"])
            )

            self.status.setText("Análise concluída.")
            self.log_message(f"Risco: {result.risk}")

            for err in result.errors:
                self.log_message(f"AVISO: {err}")

        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

    def run_sanitize(self):
        if not self.selected_pdf:
            QMessageBox.warning(self, "Aviso", "Selecione um PDF primeiro.")
            return

        try:
            output = str(
                Path(self.selected_pdf).parent / sanitized_output_name(self.selected_pdf)
            )

            removed = sanitize_pdf(self.selected_pdf, output)

            self.last_sanitized_pdf = output
            self.open_sanitized_btn.setEnabled(True)
            self.open_folder_btn.setEnabled(True)

            self.log_message("Sanitização concluída.")

            if removed:
                for item in removed:
                    self.log_message(f"Removido: {item}")
            else:
                self.log_message("Nenhum vetor removido.")

        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))

    def open_html(self):
        if self.last_html:
            subprocess.run(["xdg-open", self.last_html])

    def open_pdf(self):
        if self.last_pdf:
            subprocess.run(["xdg-open", self.last_pdf])

    def open_sanitized(self):
        if self.last_sanitized_pdf:
            subprocess.run(["xdg-open", self.last_sanitized_pdf])

    def open_folder(self):
        if self.selected_pdf:
            subprocess.run(["xdg-open", str(Path(self.selected_pdf).parent)])


def main():
    app = QApplication(sys.argv)
    window = LexSentinelApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()