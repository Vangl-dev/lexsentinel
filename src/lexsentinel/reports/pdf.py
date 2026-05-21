from pathlib import Path
from weasyprint import HTML


def render_pdf(html_path: str, output_path: str):
    html_file = Path(html_path)

    HTML(filename=str(html_file)).write_pdf(output_path)