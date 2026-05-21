import typer
from pathlib import Path

from lexsentinel.analyzers.core import analyze
from lexsentinel.reports.html import render
from lexsentinel.reports.json import render_json
from lexsentinel.reports.pdf import render_pdf
from lexsentinel.utils import (
    default_output_name,
    sanitized_output_name,
)
from lexsentinel.sanitizer import sanitize_pdf

app = typer.Typer(help="LexSentinel — Raio-X PDF")


@app.command("analyze")
def analyze_cmd(
    pdf: str,
    output: str = None,
):
    pdf_path = Path(pdf)

    if not pdf_path.exists():
        typer.echo(f"Arquivo não encontrado: {pdf}")
        raise typer.Exit(1)

    if output is None:
        output = str(pdf_path.parent / default_output_name(pdf))

    json_output = output.replace(".html", ".json")
    pdf_output = output.replace(".html", ".pdf")

    result = analyze(pdf, output)

    render(result, output)

    try:
        render_json(result, json_output)
    except Exception as e:
        result.errors.append(f"Falha ao gerar JSON: {e}")

    try:
        render_pdf(output, pdf_output)
    except Exception as e:
        result.errors.append(f"Falha ao gerar PDF: {e}")

    typer.echo("")
    typer.echo("LexSentinel — análise concluída")
    typer.echo(f"HTML: {output}")
    typer.echo(f"PDF: {pdf_output}")
    typer.echo(f"JSON: {json_output}")

    if result.errors:
        typer.echo("")
        typer.echo("WARNINGS:")
        for err in result.errors:
            typer.echo(f"- {err}")

    typer.echo("")


@app.command("sanitize")
def sanitize_cmd(
    pdf: str,
    output: str = None,
):
    pdf_path = Path(pdf)

    if not pdf_path.exists():
        typer.echo(f"Arquivo não encontrado: {pdf}")
        raise typer.Exit(1)

    if output is None:
        output = str(pdf_path.parent / sanitized_output_name(pdf))

    removed = sanitize_pdf(pdf, output)

    typer.echo("")
    typer.echo("LexSentinel sanitize complete")
    typer.echo("")

    if removed:
        typer.echo("Removed:")
        for item in removed:
            typer.echo(f"✓ {item}")
    else:
        typer.echo("Nenhum vetor removido.")

    typer.echo("")
    typer.echo(f"Output: {output}")
    typer.echo("")
    typer.echo("WARNING:")
    typer.echo("Preserve o documento original.")
    typer.echo("")


if __name__ == "__main__":
    app()
