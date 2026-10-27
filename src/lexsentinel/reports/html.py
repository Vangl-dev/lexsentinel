import base64
import html
import platform
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import fitz
import pikepdf

from lexsentinel import __version__
from lexsentinel.explainer import explain_finding

LEXSENTINEL_VERSION = __version__

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]

SEVERITY_LABELS = {
    "CRITICAL": ("Crítica", "Críticos"),
    "HIGH": ("Alta", "Altos"),
    "MEDIUM": ("Média", "Médios"),
    "LOW": ("Baixa", "Baixos"),
    "INFO": ("Informativa", "Informativos"),
}

CONFIDENCE_LABELS = {
    "HIGH": "Alta",
    "MEDIUM": "Média",
    "LOW": "Baixa",
}

RISK_LABELS = {
    "SAFE": "Sem indícios relevantes",
    "SUSPICIOUS": "Suspeito",
    "HIGH RISK": "Risco alto",
    "CRITICAL": "Risco crítico",
}

METADATA_LABELS = {
    "title": "Título",
    "author": "Autor",
    "subject": "Assunto",
    "keywords": "Palavras-chave",
    "creator": "Aplicativo de criação",
    "producer": "Gerador do PDF",
    "creationDate": "Data de criação",
    "modDate": "Data de modificação",
    "format": "Formato",
    "encryption": "Criptografia",
    "trapped": "Trapped",
}

CATEGORY_LABELS = {
    "prompt_injection": "Instrução a IA",
    "hidden_text": "Conteúdo oculto",
    "javascript": "Elemento ativo",
    "embedded": "Anexo",
    "metadata": "Metadados",
    "alt_text": "Texto alternativo",
    "structure": "Estrutura do PDF",
    "semantic": "Marcador estrutural",
    "engine": "Ocorrência técnica",
}

ANALYSIS_SCOPE = [
    "Texto de todas as páginas, analisado de forma contínua (instruções "
    "divididas em trechos diferentes também são identificadas), em busca de "
    "instruções dirigidas a sistemas de IA em português e inglês.",
    "Normalização antes da comparação: espaços irregulares, caracteres "
    "invisíveis (como espaço de largura zero), variantes Unicode de letras e "
    "acentuação.",
    "Metadados do documento (dicionário Info e bloco XMP), comentários e "
    "anotações, campos de formulário e marcadores do sumário.",
    "Texto em cor branca, incluindo fontes com tamanho inferior a 1 ponto.",
    "Texto alternativo (/Alt) de todos os elementos da árvore de estrutura.",
    "Elementos ativos e estruturais: ação de abertura (/OpenAction), "
    "JavaScript, formulários, camadas opcionais e arquivos anexados.",
    "Identificação do arquivo por hash SHA-256 e registro dos metadados "
    "declarados.",
]

ANALYSIS_LIMITS = [
    "Não há reconhecimento óptico (OCR): texto contido em imagens não é lido.",
    "O conteúdo de arquivos anexados não é analisado.",
    "Texto posicionado fora da área visível da página não é analisado; texto "
    "com modo de renderização invisível e texto coberto por outros elementos "
    "são varridos em busca de instruções, mas não são classificados como "
    "conteúdo oculto.",
    "A detecção de instruções a IA baseia-se em uma lista de expressões; "
    "variações de redação não previstas podem não ser identificadas.",
]

DISCLAIMER = (
    "Este laudo tem natureza técnica e preliminar e foi gerado por análise "
    "automatizada baseada em regras determinísticas, sem uso de inteligência "
    "artificial na classificação. Não constitui perícia judicial nem atesta a "
    "inocuidade do documento. A ausência de achados indica apenas que os testes "
    "descritos na seção de metodologia não identificaram indícios, e os "
    "resultados devem ser interpretados por profissional qualificado."
)


def embedded_logo():
    logo_path = Path(__file__).resolve().parents[3] / "assets" / "icon.png"

    if not logo_path.exists():
        return ""

    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def html_escape(value):
    if value is None or value == "":
        return "—"
    return html.escape(str(value))


def file_size_human(size):
    if size is None:
        return "—"
    units = ["bytes", "KB", "MB", "GB", "TB"]
    current = float(size)
    for unit in units:
        if current < 1024:
            if unit == "bytes":
                return f"{int(current)} bytes"
            return f"{current:.1f} {unit}".replace(".", ",")
        current /= 1024
    return f"{current:.1f} PB".replace(".", ",")


_PDF_DATE_RE = re.compile(
    r"^D:(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?([Z+\-])?(\d{2})?'?(\d{2})?"
)


def format_pdf_date(value):
    if not value:
        return None
    match = _PDF_DATE_RE.match(str(value))
    if not match:
        return str(value)
    year, month, day, hour, minute, second, tz, tz_h, tz_m = match.groups()
    text = f"{day or '01'}/{month or '01'}/{year}"
    if hour:
        text += f" {hour}:{minute or '00'}:{second or '00'}"
    if tz == "Z":
        text += " (UTC)"
    elif tz and tz_h:
        text += f" (UTC{tz}{tz_h}:{tz_m or '00'})"
    return text


def format_analysis_date(value):
    if not value:
        return "—"
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return value
    offset = moment.strftime("%z")
    tz = f" (UTC{offset[:3]}:{offset[3:]})" if offset else ""
    return moment.strftime("%d/%m/%Y às %H:%M:%S") + tz


def report_id(result):
    digest = result.fingerprint.sha256[:8].upper() if result.fingerprint else "SEMHASH"
    stamp = ""
    if result.analyzed_at:
        try:
            stamp = datetime.fromisoformat(result.analyzed_at).strftime("-%Y%m%d-%H%M%S")
        except ValueError:
            pass
    return f"LS-{digest}{stamp}"


def severity_rank(severity):
    try:
        return SEVERITY_ORDER.index(severity)
    except ValueError:
        return len(SEVERITY_ORDER)


def sorted_findings(findings):
    return sorted(findings, key=lambda f: (severity_rank(f.severity), f.page or 0))


def severity_tag(severity):
    label = SEVERITY_LABELS.get(severity, (severity, severity))[0]
    css = severity.lower() if severity in SEVERITY_LABELS else "info"
    return f'<span class="tag tag-{css}">{html_escape(label)}</span>'


def finding_location(finding, explanation):
    if finding.page:
        return f"Página {finding.page}"
    return explanation["location"]


def get_runtime_info():
    return {
        "LexSentinel": LEXSENTINEL_VERSION,
        "Python": platform.python_version(),
        "Sistema operacional": f"{platform.system()} {platform.release()}",
        "PyMuPDF": fitz.VersionBind,
        "pikepdf": pikepdf.__version__,
    }


def evidence_src(output_path, evidence_path):
    path = Path(evidence_path)
    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except OSError:
        pass
    try:
        return str(path.resolve().relative_to(Path(output_path).parent.resolve()))
    except ValueError:
        return str(path)


def conclusion_text(result, findings):
    counts = Counter(f.severity for f in findings)
    relevant = [f for f in findings if f.severity in ("CRITICAL", "HIGH")]

    if result.risk == "SAFE":
        text = (
            "Os testes aplicados não identificaram indícios relevantes de "
            "manipulação dirigida a sistemas de IA, conteúdo oculto ou "
            "elementos ativos. Esse resultado não garante a inocuidade do "
            "documento; consulte as limitações descritas na seção 5."
        )
        if counts:
            text += (
                " Os registros listados abaixo têm caráter informativo ou de "
                "baixa gravidade."
            )
        return text

    parts = []
    for severity in SEVERITY_ORDER:
        n = counts.get(severity, 0)
        if not n:
            continue
        if severity == "CRITICAL":
            label = "crítico" if n == 1 else "críticos"
        elif severity == "INFO":
            label = "informativo" if n == 1 else "informativos"
        else:
            label = f"de gravidade {SEVERITY_LABELS[severity][0].lower()}"
        parts.append(f"{n} {'achado' if n == 1 else 'achados'} {label}")

    summary = ", ".join(parts[:-1]) + (" e " if len(parts) > 1 else "") + parts[-1]
    text = f"A análise registrou {summary}."

    if relevant:
        highlights = []
        for finding in relevant:
            title = explain_finding(finding)["human_title"]
            where = f" (página {finding.page})" if finding.page else ""
            item = f"{title[:1].lower()}{title[1:]}{where}"
            if item not in highlights:
                highlights.append(item)
        text += " Destaques: " + "; ".join(highlights[:4]) + "."

    if result.risk == "CRITICAL":
        text += (
            " Recomenda-se não submeter o documento a ferramentas de IA nem "
            "utilizá-lo em fluxos automatizados antes da revisão humana dos "
            "trechos indicados."
        )
    elif result.risk == "HIGH RISK":
        text += " Recomenda-se revisão humana antes de qualquer processamento automatizado."
    else:
        text += " Recomenda-se revisão humana dos itens apontados."

    return text


def render_header(result, rid):
    logo = embedded_logo()
    logo_html = f'<img src="{logo}" alt="" class="logo">' if logo else ""
    risk = result.risk if result.risk in RISK_LABELS else "SUSPICIOUS"
    return f"""
    <header class="hero">
        <div class="hero-top">
            <div class="brand">
                {logo_html}
                <div>
                    <div class="brand-name">LexSentinel</div>
                    <div class="brand-sub">Laudo técnico de análise de PDF</div>
                </div>
            </div>
            <div class="verdict verdict-{risk.lower().replace(' ', '-')}">
                <span class="verdict-dot"></span>
                <div>
                    <div class="verdict-value">{html_escape(RISK_LABELS[risk])}</div>
                    <div class="verdict-score">Pontuação técnica: {result.total_score}</div>
                </div>
            </div>
        </div>
        <div class="hero-meta">
            <div><span>Laudo nº</span>{html_escape(rid)}</div>
            <div><span>Data da análise</span>{html_escape(format_analysis_date(result.analyzed_at))}</div>
            <div><span>Versão</span>LexSentinel {html_escape(LEXSENTINEL_VERSION)}</div>
        </div>
    </header>
    """


def render_conclusion(result, findings):
    counts = Counter(f.severity for f in findings)
    metrics = "".join(
        f'<div class="metric metric-{sev.lower()}"><div class="metric-value">{counts.get(sev, 0)}</div>'
        f'<div class="metric-label">{SEVERITY_LABELS[sev][1]}</div></div>'
        for sev in SEVERITY_ORDER
    )
    return f"""
    <div class="metrics">{metrics}</div>
    <section class="card">
        <h2><span class="num">1</span>Conclusão</h2>
        <p class="conclusion">{html_escape(conclusion_text(result, findings))}</p>
        <p class="note">A pontuação técnica é a soma dos pesos atribuídos a cada achado e determina
        a classificação (crítico a partir de 90; risco alto a partir de 60; suspeito a partir de 25).
        Esta análise verifica instruções dirigidas a sistemas de IA (prompt injection), conteúdo
        oculto e elementos ativos.</p>
    </section>
    """


def render_document(result):
    fp = result.fingerprint
    if not fp:
        body = "<p>Não foi possível identificar o arquivo.</p>"
    else:
        rows = [
            ("Arquivo", html_escape(fp.filename)),
            ("SHA-256", f'<span class="mono">{html_escape(fp.sha256)}</span>'),
            ("Tamanho", f"{file_size_human(fp.file_size)}"),
            ("Páginas", html_escape(fp.page_count)),
            ("Versão do formato", html_escape(fp.pdf_version and f"PDF {fp.pdf_version}")),
            ("Criptografado", "Sim" if fp.encrypted else "Não"),
            ("Linearizado", "Sim" if fp.linearized else "Não"),
        ]
        body = "<table class=\"kv\">" + "".join(
            f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows
        ) + "</table>"
        body += (
            '<p class="note">O hash SHA-256 identifica de forma única o arquivo analisado. '
            "Qualquer alteração no arquivo, por menor que seja, produz um hash diferente.</p>"
        )

    metadata = result.metadata or {}
    if metadata:
        rows = []
        for key, value in metadata.items():
            label = METADATA_LABELS.get(key, key)
            shown = format_pdf_date(value) if key in ("creationDate", "modDate") else value
            rows.append(f"<tr><th>{html_escape(label)}</th><td>{html_escape(shown)}</td></tr>")
        meta_html = f"<table class=\"kv\">{''.join(rows)}</table>"
    else:
        meta_html = "<p>O documento não declara metadados.</p>"

    return f"""
    <section class="card">
        <h2><span class="num">2</span>Documento analisado</h2>
        {body}
        <h3>Metadados declarados</h3>
        {meta_html}
        <p class="note">Metadados são informados por quem gerou o arquivo e podem ser alterados livremente.</p>
    </section>
    """


def render_summary_table(findings):
    if not findings:
        body = "<p>Nenhum achado registrado.</p>"
    else:
        rows = []
        for i, finding in enumerate(findings, start=1):
            explanation = explain_finding(finding)
            rows.append(
                f"<tr><td class=\"c\">{i}</td><td>{severity_tag(finding.severity)}</td>"
                f"<td><a href=\"#achado-{i}\">{html_escape(explanation['human_title'])}</a></td>"
                f"<td>{html_escape(CATEGORY_LABELS.get(finding.category, finding.category))}</td>"
                f"<td>{html_escape(finding_location(finding, explanation))}</td></tr>"
            )
        body = (
            "<table class=\"grid\"><thead><tr><th class=\"c\">Nº</th><th>Gravidade</th>"
            "<th>Achado</th><th>Tipo</th><th>Localização</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )
    return f"""
    <section class="card">
        <h2><span class="num">3</span>Quadro de achados</h2>
        {body}
    </section>
    """


def render_finding(i, finding, output_path):
    explanation = explain_finding(finding)
    details = finding.details or ""
    if len(details) > 1200:
        details = details[:1200] + " […]"

    evidence_html = ""
    if finding.evidence_path:
        note = explanation.get("evidence_note") or "A área destacada em vermelho indica a posição do achado."
        evidence_html = f"""
        <figure>
            <img src="{html_escape(evidence_src(output_path, finding.evidence_path))}"
                 alt="Página {finding.page} com a área do achado destacada">
            <figcaption>Figura {i}: página {finding.page}. {html_escape(note)}</figcaption>
        </figure>
        """

    confidence = CONFIDENCE_LABELS.get(finding.confidence, finding.confidence)

    return f"""
    <article class="finding finding-{finding.severity.lower()}" id="achado-{i}">
        <header>
            <span class="finding-num">Achado {i}</span>
            {severity_tag(finding.severity)}
            <h3>{html_escape(explanation['human_title'])}</h3>
        </header>
        <dl>
            <dt>O que foi encontrado</dt><dd>{html_escape(explanation['what'])}</dd>
            <dt>Conteúdo identificado</dt><dd><pre>{html_escape(details)}</pre></dd>
            <dt>Por que importa</dt><dd>{html_escape(explanation['impact'])}</dd>
            <dt>Localização</dt><dd>{html_escape(finding_location(finding, explanation))}</dd>
            <dt>Confiança da detecção</dt><dd>{html_escape(confidence)}</dd>
            <dt>Recomendação</dt><dd>{html_escape(explanation['recommendation'])}</dd>
        </dl>
        {evidence_html}
    </article>
    """


def render_findings(findings, output_path):
    if not findings:
        body = (
            "<p>Nenhum achado a detalhar. Os testes aplicados estão descritos na seção 5.</p>"
        )
    else:
        body = "".join(
            render_finding(i, finding, output_path)
            for i, finding in enumerate(findings, start=1)
        )
    return f"""
    <section class="card">
        <h2><span class="num">4</span>Detalhamento dos achados</h2>
        {body}
    </section>
    """


def render_errors(errors):
    if not errors:
        return ""
    items = "".join(f"<li>{html_escape(err)}</li>" for err in errors)
    return f"""
    <div class="alert">
        <strong>Ocorrências durante a análise.</strong>
        Parte da análise pode não ter sido concluída. Os resultados devem ser lidos com essa ressalva.
        <ul>{items}</ul>
    </div>
    """


def render_methodology():
    scope = "".join(f"<li>{html_escape(item)}</li>" for item in ANALYSIS_SCOPE)
    limits = "".join(f"<li>{html_escape(item)}</li>" for item in ANALYSIS_LIMITS)
    return f"""
    <section class="card">
        <h2><span class="num">5</span>Metodologia e limitações</h2>
        <p>A análise é automatizada e determinística: as mesmas regras, aplicadas ao mesmo
        arquivo, produzem o mesmo resultado. Nenhum sistema de IA é usado para classificar
        o documento.</p>
        <h3>O que foi verificado</h3>
        <ul>{scope}</ul>
        <h3>O que não foi verificado</h3>
        <ul>{limits}</ul>
    </section>
    """


def render_appendix():
    rows = "".join(
        f"<tr><th>{html_escape(k)}</th><td>{html_escape(v)}</td></tr>"
        for k, v in get_runtime_info().items()
    )
    return f"""
    <section class="card appendix">
        <h2>Anexo: ambiente técnico</h2>
        <table class="kv">{rows}</table>
        <h2>Ressalva</h2>
        <p class="disclaimer">{html_escape(DISCLAIMER)}</p>
    </section>
    """


def render_styles(rid):
    return """
    <style>
    @page {
        size: A4;
        margin: 16mm 14mm 18mm 14mm;
        background: #f1f5f9;
        @bottom-left { content: "LexSentinel · Laudo nº __RID__"; font: 8pt "Liberation Sans", Arial, sans-serif; color: #64748b; }
        @bottom-right { content: "Página " counter(page) " de " counter(pages); font: 8pt "Liberation Sans", Arial, sans-serif; color: #64748b; }
    }
    :root {
        --ink: #0f172a; --muted: #475569; --line: #e2e8f0; --soft: #f8fafc; --bg: #f1f5f9;
        --navy: #0f172a; --navy-2: #1e293b; --accent: #1e3a5f;
        --critical: #dc2626; --high: #ea580c; --medium: #ca8a04; --low: #0284c7; --info: #64748b;
        --safe: #16a34a;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--ink);
           font: 10.5pt/1.6 "Inter", "Segoe UI", "Liberation Sans", "DejaVu Sans", Arial, sans-serif; }
    .page { max-width: 210mm; margin: 0 auto; padding: 28px 20px; }
    @media print { .page { padding: 0; max-width: none; } }

    .hero { background: linear-gradient(135deg, var(--navy), var(--navy-2)); color: white;
            border-radius: 16px; padding: 24px 26px 18px; break-inside: avoid; }
    .hero-top { display: flex; justify-content: space-between; align-items: center; gap: 18px; flex-wrap: wrap; }
    .brand { display: flex; align-items: center; gap: 14px; flex: 1; min-width: 280px; }
    .logo { width: 56px; height: 56px; }
    .brand-name { font-size: 22pt; font-weight: 800; line-height: 1.1; }
    .brand-sub { font-size: 10pt; opacity: .85; margin-top: 4px; }
    .verdict { display: flex; align-items: center; gap: 12px; padding: 12px 18px; border-radius: 12px;
               border: 2px solid var(--info); background: rgba(255,255,255,.07); min-width: 220px; }
    .verdict-dot { width: 16px; height: 16px; border-radius: 50%; background: var(--info); flex-shrink: 0; }
    .verdict-value { font-size: 14pt; font-weight: 800; line-height: 1.2; }
    .verdict-score { font-size: 8.5pt; opacity: .8; }
    .verdict-critical { border-color: var(--critical); } .verdict-critical .verdict-dot { background: var(--critical); }
    .verdict-high-risk { border-color: var(--high); } .verdict-high-risk .verdict-dot { background: var(--high); }
    .verdict-suspicious { border-color: var(--medium); } .verdict-suspicious .verdict-dot { background: var(--medium); }
    .verdict-safe { border-color: var(--safe); } .verdict-safe .verdict-dot { background: var(--safe); }
    .hero-meta { display: flex; gap: 8px 28px; flex-wrap: wrap; margin-top: 18px; padding-top: 12px;
                 border-top: 1px solid rgba(255,255,255,.15); font-size: 8.5pt; }
    .hero-meta span { display: block; opacity: .6; font-size: 7.5pt; text-transform: uppercase; letter-spacing: .06em; }

    .metrics { display: flex; gap: 10px; margin: 14px 0; }
    .metric { flex: 1; background: white; border-radius: 12px; padding: 10px 12px; border-top: 4px solid var(--info);
              text-align: center; }
    .metric-value { font-size: 18pt; font-weight: 800; line-height: 1.2; }
    .metric-label { font-size: 8pt; color: var(--muted); }
    .metric-critical { border-top-color: var(--critical); } .metric-critical .metric-value { color: var(--critical); }
    .metric-high { border-top-color: var(--high); } .metric-high .metric-value { color: var(--high); }
    .metric-medium { border-top-color: var(--medium); } .metric-medium .metric-value { color: var(--medium); }
    .metric-low { border-top-color: var(--low); } .metric-low .metric-value { color: var(--low); }
    @media (max-width: 640px) { .metrics { flex-wrap: wrap; } .metric { flex-basis: 30%; } }

    .card { background: white; border-radius: 14px; padding: 18px 22px; margin-bottom: 14px; }
    h2 { font-size: 13pt; margin: 0 0 12px; display: flex; align-items: center; gap: 10px; break-after: avoid; }
    h2 .num { display: inline-block; width: 24px; height: 24px; border-radius: 50%; background: var(--accent);
              color: white; font-size: 10pt; line-height: 24px; text-align: center; flex-shrink: 0; }
    h3 { font-size: 10.5pt; margin: 16px 0 6px; break-after: avoid; }
    .conclusion { margin: 0; font-size: 11pt; }
    .note { font-size: 8.5pt; color: var(--muted); margin: 8px 0 0; }
    .mono, pre { font-family: "DejaVu Sans Mono", "Liberation Mono", ui-monospace, monospace; }
    .mono { word-break: break-all; font-size: 9pt; }
    a { color: inherit; text-decoration: none; }

    table.kv, table.grid { width: 100%; border-collapse: collapse; font-size: 9.5pt; }
    .kv th, .kv td, .grid th, .grid td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line);
                                         vertical-align: top; }
    .kv th { width: 34%; font-weight: 600; color: var(--muted); }
    .kv td { word-break: break-word; }
    .grid thead th { font-size: 8pt; text-transform: uppercase; letter-spacing: .05em; color: var(--muted);
                     border-bottom: 2px solid var(--line); }
    .grid tr { break-inside: avoid; }
    .c { text-align: center !important; width: 3em; }

    .tag { display: inline-block; font-size: 7.5pt; font-weight: 700; text-transform: uppercase;
           letter-spacing: .05em; padding: 2px 9px; border-radius: 999px; color: white; white-space: nowrap; }
    .tag-critical { background: var(--critical); } .tag-high { background: var(--high); }
    .tag-medium { background: var(--medium); } .tag-low { background: var(--low); } .tag-info { background: var(--info); }

    .finding { border: 1px solid var(--line); border-radius: 12px; margin: 0 0 14px; overflow: hidden; }
    .finding header { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 10px 14px;
                      background: var(--soft); border-bottom: 1px solid var(--line); break-inside: avoid; }
    .finding-critical header { background: #fef2f2; border-bottom-color: #fecaca; }
    .finding-high header { background: #fff7ed; border-bottom-color: #fed7aa; }
    .finding-medium header { background: #fefce8; border-bottom-color: #fef08a; }
    .finding-low header { background: #f0f9ff; border-bottom-color: #bae6fd; }
    .finding-num { font-size: 8.5pt; color: var(--muted); font-weight: 700; }
    .finding h3 { margin: 0; flex-basis: 100%; font-size: 11pt; }
    .finding dl { display: grid; grid-template-columns: 30% 1fr; gap: 6px 14px; margin: 0; padding: 12px 14px;
                  font-size: 9.5pt; break-inside: avoid; }
    .finding dt { color: var(--muted); font-weight: 600; }
    .finding dd { margin: 0; }
    .finding pre { margin: 0; padding: 7px 10px; background: var(--navy); color: #f8fafc; border-radius: 8px;
                   white-space: pre-wrap; word-break: break-word; font-size: 8.5pt; }
    figure { margin: 0 14px 14px; border: 1px solid var(--line); border-radius: 8px; break-inside: avoid; overflow: hidden; }
    figure img { width: 100%; height: auto; display: block; }
    figcaption { font-size: 8pt; color: var(--muted); padding: 5px 10px; border-top: 1px solid var(--line); background: var(--soft); }

    .alert { background: #fef2f2; border: 1px solid #fecaca; border-radius: 12px; padding: 12px 16px;
             margin: 14px 0; font-size: 9.5pt; }
    .alert ul { margin: 6px 0 0; }
    ul { padding-left: 18px; margin: 4px 0; }
    li { margin-bottom: 3px; }
    .appendix h2 + table { margin-bottom: 18px; }
    .disclaimer { font-size: 9pt; color: var(--muted); text-align: justify; margin: 0; }
    </style>
    """.replace("__RID__", rid)


def render(result, output_path):
    findings = sorted_findings(result.findings)
    rid = report_id(result)
    html_doc = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Laudo {html_escape(rid)} · LexSentinel</title>
    {render_styles(rid)}
</head>
<body>
<main class="page">
    {render_header(result, rid)}
    {render_errors(result.errors)}
    {render_conclusion(result, findings)}
    {render_document(result)}
    {render_summary_table(findings)}
    {render_findings(findings, output_path)}
    {render_methodology()}
    {render_appendix()}
</main>
</body>
</html>
"""
    Path(output_path).write_text(html_doc, encoding="utf-8")
