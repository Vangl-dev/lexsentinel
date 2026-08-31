import sys
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
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
    QDialog,
    QTextEdit,
    QHBoxLayout,
    QSizePolicy,
    QScrollArea,
    QFrame,
    )

from lexsentinel.analyzers.core import analyze
from lexsentinel.reports.html import render
from lexsentinel.reports.json import render_json
from lexsentinel.reports.pdf import render_pdf
from lexsentinel.sanitizer import sanitize_pdf
from lexsentinel.extractor import extract_raw_text
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

        asset_path = Path(__file__).resolve().parents[2] / "assets" / "icon.png"
        
        self.setWindowIcon(QIcon(str(asset_path)))

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

        header = QHBoxLayout()

        logo = QLabel()
        asset_path = Path(__file__).resolve().parents[2] / "assets" / "icon.png"
        pixmap = QPixmap(str(asset_path))
        logo.setPixmap(pixmap.scaled(64, 64))

        title_box = QVBoxLayout()

        title = QLabel("LexSentinel - Raio-X PDF")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")

        subtitle = QLabel("Análise defensiva de PDFs")
        subtitle.setStyleSheet("font-size: 16px;")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header.addWidget(logo)
        header.addLayout(title_box)
        header.addStretch()

        layout.addLayout(header)

        security_update = QHBoxLayout()
        security_update.setContentsMargins(0, 0, 0, 0)

        security_badge = QLabel("Atualização de segurança")
        security_badge.setStyleSheet(
            "background:#1e40af;color:white;padding:4px 10px;border-radius:6px;"
            "font-size:11px;font-weight:bold;"
        )
        security_update.addWidget(security_badge)

        security_desc = QLabel(
            "Detecção de Prompt Injection, conteúdo oculto e estruturas de PDF ampliadas."
        )
        security_desc.setStyleSheet("font-size:12px;color:#475569;")
        security_desc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        security_update.addWidget(security_desc)

        what_changed_btn = QPushButton("Ver o que mudou")
        what_changed_btn.setStyleSheet(
            "QPushButton{font-size:11px;color:#1e40af;border:1px solid #1e40af;"
            "border-radius:6px;padding:4px 10px;background:transparent;}"
            "QPushButton:hover{background:#1e40af;color:white;}"
        )
        what_changed_btn.clicked.connect(self.show_update_notes)
        security_update.addWidget(what_changed_btn)

        layout.addLayout(security_update)

        self.status = QLabel("Pronto.")
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

        self.view_text_btn = QPushButton("Ver texto extraído")
        self.view_text_btn.clicked.connect(self.view_raw_text)
        open_buttons.addWidget(self.view_text_btn)

        self.open_folder_btn = QPushButton("Abrir Pasta")
        self.open_folder_btn.clicked.connect(self.open_folder)
        self.open_folder_btn.setEnabled(False)
        open_buttons.addWidget(self.open_folder_btn)

        layout.addLayout(open_buttons)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.setLayout(layout)

    def show_update_notes(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Atualizações de segurança — LexSentinel")
        dialog.resize(620, 480)
        dialog.setMinimumSize(500, 360)

        dialog.setStyleSheet(
            "QDialog{background:#1e293b;}"
        )

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 16)
        main_layout.setSpacing(12)

        title = QLabel("Principais melhorias")
        title.setStyleSheet(
            "font-size:16px;font-weight:bold;color:#f1f5f9;"
            "margin-bottom:4px;"
        )
        main_layout.addWidget(title)

        subtitle = QLabel(
            "O mecanismo de análise recebeu melhorias nas seguintes áreas:"
        )
        subtitle.setStyleSheet("font-size:13px;color:#94a3b8;margin-bottom:8px;")
        main_layout.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{background:#334155;width:8px;margin:0;}"
            "QScrollBar::handle:vertical{background:#475569;border-radius:4px;min-height:30px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background:transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 8, 0)
        scroll_layout.setSpacing(8)

        changes = [
            ("Prompt Injection com whitespace irregular",
             "Normalização de espaços em branco antes da detecção, eliminando bypasses com tabulações, "
             "quebras de linha e espaços múltiplos."),
            ("Prompt Injection em /Alt da Structure Tree",
             "Elementos como /Standard, /Div e /P com atributo /Alt agora são analisados, "
             "não apenas /Figure."),
            ("Detecção ampliada de vetores estruturais PDF",
             "Ações identificadas pela chave /S (e não por literal), com varredura de anotações, "
             "árvore de nomes e páginas aninhadas."),
            ("Conteúdo oculto",
             "Inspeção de texto branco, camadas invisíveis e artefatos de ocultação visual."),
            ("Verificação de pacotes",
             "Checagem de versões das dependências do projeto com suporte a specifiers PEP 440."),
            ("Análise de alt-text",
             "Extração e classificação de atributos /Alt de todos os tipos de elementos da árvore de estrutura."),
            ("Análise em lote",
             "Processamento de múltiplos arquivos via CLI com suporte a diretórios e saída JSON."),
        ]

        for label, desc in changes:
            item_frame = QFrame()
            item_frame.setStyleSheet(
                "QFrame{background:#0f172a;border-radius:8px;padding:10px 14px;}"
            )
            item_layout = QVBoxLayout()
            item_layout.setContentsMargins(14, 10, 14, 10)
            item_layout.setSpacing(4)

            item_label = QLabel(label)
            item_label.setStyleSheet(
                "font-size:13px;font-weight:bold;color:#e2e8f0;"
                "background:transparent;"
            )
            item_layout.addWidget(item_label)

            item_desc = QLabel(desc)
            item_desc.setWordWrap(True)
            item_desc.setStyleSheet(
                "font-size:12px;color:#cbd5e1;"
                "background:transparent;line-height:1.4;"
            )
            item_layout.addWidget(item_desc)

            item_frame.setLayout(item_layout)
            scroll_layout.addWidget(item_frame)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

        close_btn = QPushButton("Fechar")
        close_btn.setFixedWidth(100)
        close_btn.setStyleSheet(
            "QPushButton{font-size:12px;padding:6px 18px;border-radius:6px;"
            "background:#475569;color:#f1f5f9;font-weight:bold;}"
            "QPushButton:hover{background:#64748b;}"
        )
        close_btn.clicked.connect(dialog.close)
        main_layout.addWidget(close_btn, alignment=Qt.AlignRight)

        dialog.setLayout(main_layout)
        dialog.exec()

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

            removed = sanitize_pdf(
                self.selected_pdf,
                output,
                aggressive=True,
            )

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
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_html))

    def open_pdf(self):
        if self.last_pdf:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_pdf))

    def open_sanitized(self):
        if self.last_sanitized_pdf:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_sanitized_pdf))

    def open_folder(self):
        if self.selected_pdf:
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(Path(self.selected_pdf).parent))
            )

    def view_raw_text(self):
        if not self.selected_pdf:
            QMessageBox.warning(
                self,
                "Aviso",
                "Selecione um PDF primeiro."
            )
            return

        try:
            text = extract_raw_text(self.selected_pdf)

            if not text.strip():
                text = "Nenhum texto extraível encontrado."

            dialog = QDialog(self)
            dialog.setWindowTitle("Texto extraído")
            dialog.resize(900, 650)

            layout = QVBoxLayout()

            editor = QTextEdit()
            editor.setReadOnly(True)
            editor.setPlainText(text)
            layout.addWidget(editor)

            buttons = QHBoxLayout()

            copy_btn = QPushButton("Copiar")
            save_btn = QPushButton("Salvar TXT")
            close_btn = QPushButton("Fechar")

            def copy_text():
                QApplication.clipboard().setText(text)

            def save_text():
                file_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Salvar texto extraído",
                    "texto_extraido.txt",
                    "Text Files (*.txt)"
                )

                if file_path:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(text)

            copy_btn.clicked.connect(copy_text)
            save_btn.clicked.connect(save_text)
            close_btn.clicked.connect(dialog.close)

            buttons.addWidget(copy_btn)
            buttons.addWidget(save_btn)
            buttons.addStretch()
            buttons.addWidget(close_btn)

            layout.addLayout(buttons)

            dialog.setLayout(layout)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro",
                str(e)
            )
def main():
    app = QApplication(sys.argv)
    window = LexSentinelApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()