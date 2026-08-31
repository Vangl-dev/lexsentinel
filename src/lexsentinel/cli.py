import json
from typing import List

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
from lexsentinel.packages import check_packages, format_check_results
from lexsentinel.batch import analyze_batch

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


@app.command("check-packages")
def check_packages_cmd():
    results = check_packages()

    typer.echo("")
    typer.echo("LexSentinel — Verificação de Pacotes")
    typer.echo("")

    typer.echo(format_check_results(results))

    has_issues = any(
        r.status in ("vulnerable", "missing", "version_mismatch")
        for r in results
    )

    typer.echo("")
    if has_issues:
        typer.echo("Status: AÇÕES NECESSÁRIAS")
    else:
        typer.echo("Status: OK")

    typer.echo("")


@app.command("batch")
def batch_cmd(
    paths: List[str] = typer.Argument(..., help="PDF files or directories to analyze"),
    output_dir: str = typer.Option(None, help="Directory for individual JSON results"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Scan directories recursively"),
    json_output: str = typer.Option(None, "--json", "-j", help="Save aggregated results to JSON file"),
):
    result = analyze_batch(
        paths=paths,
        output_dir=output_dir,
        recursive=recursive,
    )

    typer.echo("")
    typer.echo("LexSentinel — Análise em Lote")
    typer.echo("")
    typer.echo(f"Total: {result['total']}")
    typer.echo(f"Sucesso: {result['successful']}")
    typer.echo(f"Falhas: {result['failed']}")
    typer.echo("")

    for r in result["results"]:
        status = "✓" if r["success"] else "✗"
        file_path = Path(r["file_path"]).name
        if r["success"]:
            typer.echo(f"  {status} {file_path} — {r['risk']} (score: {r['total_score']})")
        else:
            typer.echo(f"  {status} {file_path} — ERRO: {r['error']}")

    if json_output:
        out_path = Path(json_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        typer.echo("")
        typer.echo(f"JSON agregado: {json_output}")

    typer.echo("")


if __name__ == "__main__":
    app()
