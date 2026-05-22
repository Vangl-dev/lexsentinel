import html
import platform
from pathlib import Path
from collections import defaultdict
from lexsentinel.explainer import explain_finding

import fitz
import pikepdf

from lexsentinel import __version__

LEXSENTINEL_VERSION = __version__


def risk_badge(risk: str):
    mapping = {
        "SAFE": ("🟢", "#16a34a", "Baixo risco"),
        "SUSPICIOUS": ("🟡", "#ca8a04", "Suspeito"),
        "HIGH RISK": ("🟠", "#ea580c", "Alto risco"),
        "CRITICAL": ("🔴", "#dc2626", "Crítico"),
    }
    return mapping.get(risk, ("⚪", "#64748b", risk))


def severity_badge(severity: str):
    mapping = {
        "LOW": "#0ea5e9",
        "MEDIUM": "#f59e0b",
        "HIGH": "#f97316",
        "CRITICAL": "#dc2626",
    }
    return mapping.get(severity, "#64748b")


def translate_category(category: str):
    mapping = {
        "open_action": "Ação automática ao abrir",
        "javascript": "JavaScript embarcado",
        "embedded_files": "Arquivos incorporados",
        "ocg": "Camadas opcionais (OCG)",
        "semantic_markers": "Marcadores semânticos",
        "hidden_text": "Texto oculto",
        "prompt_injection": "Prompt injection textual",
        "semantic_poisoning": "Envenenamento semântico",
        "metadata": "Metadados",
        "structure": "Estrutura PDF",
    }
    return mapping.get(category.lower(), category.replace("_", " ").title())


def group_findings(findings):
    grouped = defaultdict(list)
    for finding in findings:
        grouped[finding.category].append(finding)
    return grouped


def get_runtime_info():
    return {
        "python": platform.python_version(),
        "system": platform.system(),
        "system_release": platform.release(),
        "pymupdf": fitz.VersionBind,
        "pikepdf": pikepdf.__version__,
        "lexsentinel": LEXSENTINEL_VERSION,
    }


def count_by_severity(findings):
    buckets = defaultdict(int)
    for finding in findings:
        buckets[finding.severity] += 1
    return buckets


def html_escape(value):
    if value is None:
        return "—"
    return html.escape(str(value))


def file_size_human(size):
    if size is None:
        return "—"
    units = ["B", "KB", "MB", "GB", "TB"]
    current = float(size)
    for unit in units:
        if current < 1024:
            return f"{current:.2f} {unit}"
        current /= 1024
    return f"{current:.2f} PB"


def relative_evidence_path(output_path, evidence_path):
    if not evidence_path:
        return None
    try:
        html_dir = Path(output_path).parent.resolve()
        evidence = Path(evidence_path).resolve()
        return str(evidence.relative_to(html_dir))
    except Exception:
        return str(evidence_path)


def executive_summary(result):
    if result.risk == "SAFE":
        return (
            "Não foram identificados indícios relevantes de vetores adversariais documentais "
            "segundo a metodologia determinística aplicada."
        )
    if result.risk == "SUSPICIOUS":
        return (
            "Foram identificados elementos atípicos ou heurísticos compatíveis com comportamentos "
            "potencialmente manipulativos, recomendando-se revisão humana complementar."
        )
    if result.risk == "HIGH RISK":
        return (
            "Foram identificados múltiplos indicadores técnicos consistentes com vetores adversariais "
            "documentais que demandam cautela operacional."
        )
    if result.risk == "CRITICAL":
        return (
            "O documento apresenta artefatos altamente compatíveis com vetores adversariais potencialmente "
            "hostis, inclusive mecanismos de manipulação estrutural."
        )
    return "Classificação indeterminada."


def methodology_block():
    return """
    <ul>
        <li>Análise estrutural determinística do container PDF;</li>
        <li>Inspeção de metadados e fingerprint documental;</li>
        <li>Detecção de objetos potencialmente ativos;</li>
        <li>Varredura heurística de conteúdo textual;</li>
        <li>Identificação de indicadores de ocultação semântica;</li>
        <li>Correlação de evidências técnicas observáveis.</li>
    </ul>
    """


def disclaimer_block():
    return (
        "Este relatório possui natureza técnico-informativa preliminar. Não constitui perícia judicial, "
        "parecer conclusivo ou certificação absoluta de inocuidade documental. A metodologia empregada "
        "baseia-se em regras determinísticas e heurísticas técnicas observáveis, sujeitas a limitações "
        "inerentes ao formato PDF."
    )


def transparency_block():
    return (
        "O núcleo analítico do LexSentinel opera sem inferência generativa autônoma para classificação "
        "principal, empregando scoring técnico explícito e inspeção objetiva de artefatos detectáveis."
    )


def render_fingerprint(fp):
    if not fp:
        return "<p>Fingerprint indisponível.</p>"
    return f"""
    <table class=\"kv\">
        <tr><th>Arquivo</th><td>{html_escape(fp.filename)}</td></tr>
        <tr><th>Tamanho</th><td>{file_size_human(fp.file_size)}</td></tr>
        <tr><th>SHA256</th><td class=\"mono\">{html_escape(fp.sha256)}</td></tr>
        <tr><th>Versão PDF</th><td>{html_escape(fp.pdf_version)}</td></tr>
        <tr><th>Creator</th><td>{html_escape(fp.creator)}</td></tr>
        <tr><th>Producer</th><td>{html_escape(fp.producer)}</td></tr>
        <tr><th>Criação</th><td>{html_escape(fp.creation_date)}</td></tr>
        <tr><th>Modificação</th><td>{html_escape(fp.mod_date)}</td></tr>
        <tr><th>Criptografado</th><td>{'Sim' if fp.encrypted else 'Não'}</td></tr>
        <tr><th>Linearizado</th><td>{'Sim' if fp.linearized else 'Não'}</td></tr>
    </table>
    """


def render_metadata(metadata):
    if not metadata:
        return "<p>Metadados indisponíveis.</p>"
    rows = []
    for key, value in sorted(metadata.items()):
        rows.append(f"<tr><th>{html_escape(key)}</th><td>{html_escape(value)}</td></tr>")
    return f"<table class=\"kv\">{''.join(rows)}</table>"


def render_findings(grouped, output_path):
    if not grouped:
        return "<section class=\"card\"><h2>Achados técnicos</h2><p>Nenhum achado registrado.</p></section>"
    blocks = []
    for category, findings in grouped.items():
        items = []
        for finding in findings:
            evidence_html = ""
            if finding.evidence_path:
                rel = relative_evidence_path(output_path, finding.evidence_path)
                evidence_html = (
                    f'<div class="evidence"><img src="{html_escape(rel)}" alt="Evidência visual"></div>'
                )

            page_info = (
                f"<div><strong>Página:</strong> {finding.page}</div>"
                if finding.page else ""
            )

            confidence = (
                f"<div><strong>Confiança:</strong> {html_escape(finding.confidence)}</div>"
                if finding.confidence else ""
            )

            explanation = explain_finding(finding)

            items.append(
                f"""
                <div class="finding">
                    <div class="finding-header">
                        <span class="severity severity-{finding.severity.lower()}">
                            {html_escape(finding.severity)}
                        </span>
                        <strong>{html_escape(explanation["human_title"])}</strong>
                    </div>

                    <div><strong>O que foi encontrado:</strong>
                    {html_escape(explanation["what"])}</div>

                    <div><strong>Impacto:</strong>
                    {html_escape(explanation["impact"])}</div>

                    <div><strong>Local:</strong>
                    {html_escape(explanation["location"])}</div>

                    <div><strong>Recomendação:</strong>
                    {html_escape(explanation["recommendation"])}</div>

                    {page_info}
                    {confidence}
                    {evidence_html}
                </div>
                """
            )
        blocks.append(f"<section class=\"card\"><h2>{translate_category(category)}</h2>{''.join(items)}</section>")
    return ''.join(blocks)


def render_errors(errors):
    if not errors:
        return ""
    items = ''.join(f"<li>{html_escape(err)}</li>" for err in errors)
    return f"<section class=\"card warning\"><h2>Alertas operacionais</h2><ul>{items}</ul></section>"


def render_runtime():
    rt = get_runtime_info()
    rows = []
    for key, value in rt.items():
        rows.append(f"<tr><th>{html_escape(key)}</th><td>{html_escape(value)}</td></tr>")
    return f"<table class=\"kv\">{''.join(rows)}</table>"


def render_header(result):
    icon, color, label = risk_badge(result.risk)
    severity = count_by_severity(result.findings)
    return f"""
    <header class=\"hero\">
        <div>
            <div class=\"brand\">LexSentinel</div>
            <div class=\"subtitle\">Raio-X Forense Preliminar de PDF</div>
        </div>
        <div class=\"risk-box\" style=\"border-color:{color}\">
            <div class=\"risk-icon\">{icon}</div>
            <div>
                <div class=\"risk-title\">{label}</div>
                <div class=\"risk-score\">Score técnico: {result.total_score}</div>
            </div>
        </div>
    </header>
    <section class=\"summary-grid\">
        <div class=\"metric\"><div class=\"metric-value\">{len(result.findings)}</div><div class=\"metric-label\">Achados</div></div>
        <div class=\"metric\"><div class=\"metric-value\">{severity.get('CRITICAL', 0)}</div><div class=\"metric-label\">Críticos</div></div>
        <div class=\"metric\"><div class=\"metric-value\">{severity.get('HIGH', 0)}</div><div class=\"metric-label\">Altos</div></div>
        <div class=\"metric\"><div class=\"metric-value\">{severity.get('MEDIUM', 0)}</div><div class=\"metric-label\">Médios</div></div>
    </section>
    """


def render_styles():
    return """
    <style>
    body { margin:0; padding:0; background:#f8fafc; font-family:Inter,Segoe UI,Arial,sans-serif; color:#0f172a; }
    .container { max-width:1200px; margin:0 auto; padding:32px; }
    .hero { background:linear-gradient(135deg,#0f172a,#1e293b); color:white; padding:32px; border-radius:18px; display:flex; justify-content:space-between; align-items:center; gap:24px; box-shadow:0 10px 30px rgba(15,23,42,.25); }
    .brand { font-size:32px; font-weight:800; }
    .subtitle { margin-top:8px; font-size:15px; opacity:.9; }
    .risk-box { background:rgba(255,255,255,.08); border:2px solid; border-radius:16px; padding:18px 22px; display:flex; gap:16px; min-width:260px; }
    .risk-icon { font-size:30px; }
    .risk-title { font-size:20px; font-weight:800; }
    .risk-score { font-size:14px; opacity:.9; }
    .summary-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:18px; margin:28px 0; }
    .metric, .card { background:white; border-radius:18px; padding:24px; box-shadow:0 8px 24px rgba(15,23,42,.08); }
    .card { margin-bottom:24px; }
    .warning { border-left:6px solid #dc2626; }
    h2 { margin-top:0; }
    .kv { width:100%; border-collapse:collapse; }
    .kv th, .kv td { padding:10px; border-bottom:1px solid #e2e8f0; text-align:left; }
    .kv th { width:260px; }
    .mono { font-family:ui-monospace,SFMono-Regular,monospace; word-break:break-all; }
    .finding { border:1px solid #e2e8f0; border-radius:14px; padding:18px; margin-bottom:18px; }
    .finding-head { display:flex; justify-content:space-between; gap:12px; }
    .finding-title { font-size:18px; font-weight:700; }
    .severity { color:white; padding:6px 12px; border-radius:999px; font-size:12px; font-weight:700; }
    .finding-meta { display:flex; gap:24px; flex-wrap:wrap; margin-top:14px; font-size:14px; }
    .finding-body { margin-top:16px; line-height:1.6; white-space:pre-wrap; }
    .evidence { margin-top:18px; }
    .evidence img { max-width:100%; border-radius:12px; border:1px solid #cbd5e1; }
    .footer-note { color:#475569; line-height:1.7; }
    </style>
    """


def render(result, output_path):
    grouped = group_findings(result.findings)
    html_doc = f"""
    <!DOCTYPE html>
    <html lang=\"pt-BR\">
    <head>
        <meta charset=\"UTF-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
        <title>LexSentinel — Relatório Técnico</title>
        {render_styles()}
    </head>
    <body>
        <div class=\"container\">
            {render_header(result)}
            <section class=\"card\"><h2>Resumo executivo</h2><p class=\"footer-note\">{html_escape(executive_summary(result))}</p></section>
            {render_errors(result.errors)}
            <section class=\"card\"><h2>Fingerprint documental</h2>{render_fingerprint(result.fingerprint)}</section>
            <section class=\"card\"><h2>Metadados documentais</h2>{render_metadata(result.metadata)}</section>
            {render_findings(grouped, output_path)}
            <section class=\"card\"><h2>Metodologia</h2>{methodology_block()}</section>
            <section class=\"card\"><h2>Transparência metodológica</h2><p class=\"footer-note\">{transparency_block()}</p></section>
            <section class=\"card\"><h2>Ambiente técnico</h2>{render_runtime()}</section>
            <section class=\"card\"><h2>Disclaimer jurídico-técnico</h2><p class=\"footer-note\">{disclaimer_block()}</p></section>
        </div>
    </body>
    </html>
    """
    Path(output_path).write_text(html_doc, encoding='utf-8')
