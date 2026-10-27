import re


def _explain(human_title, what, impact, location, recommendation, evidence_note=None):
    return {
        "human_title": human_title,
        "what": what,
        "impact": impact,
        "location": location,
        "recommendation": recommendation,
        "evidence_note": evidence_note,
    }


def explain_finding(finding):
    title = finding.title
    category = finding.category

    if category == "prompt_injection":
        if "alt-text" in title.lower():
            return _explain(
                "Instrução direcionada a IA em texto alternativo",
                "O texto alternativo (/Alt) de um elemento do documento contém "
                "um padrão típico de instrução dirigida a sistemas de IA. Esse "
                "campo não aparece na leitura normal, mas é lido por leitores de "
                "tela e por ferramentas de extração.",
                "Um sistema de IA que processe o documento pode receber essa "
                "instrução como se fosse parte do pedido do usuário e alterar "
                "resumos, classificações ou pareceres.",
                "Árvore de estrutura do PDF (atributo /Alt)",
                "Não submeter o documento a ferramentas de IA sem antes remover "
                "o conteúdo. Preservar o original como prova e usar a "
                "sanitização agressiva para obter uma cópia de trabalho.",
            )
        hidden_sources = [
            ("metadados xmp", "Instrução direcionada a IA nos metadados XMP",
             "O bloco de metadados XMP", "Metadados XMP do PDF"),
            ("metadados", "Instrução direcionada a IA nos metadados",
             "Um campo de metadados do documento", "Metadados do PDF (dicionário Info)"),
            ("anotação", "Instrução direcionada a IA em comentário",
             "Um comentário ou anotação do documento", "Anotação do PDF"),
            ("formulário", "Instrução direcionada a IA em campo de formulário",
             "Um campo de formulário (valor, rótulo ou nome)", "Campo de formulário do PDF"),
            ("marcador", "Instrução direcionada a IA no sumário",
             "Um marcador do sumário (bookmarks)", "Sumário do PDF (bookmarks)"),
        ]
        for key, human_title, where, location in hidden_sources:
            if key in title.lower():
                field = re.search(r"\(([^)]+)\)$", title)
                if key == "metadados" and field:
                    human_title += f" ({field.group(1)})"
                return _explain(
                    human_title,
                    f"{where} contém um padrão típico de instrução dirigida a "
                    "sistemas de IA (prompt injection). Esse conteúdo não faz "
                    "parte do texto exibido nas páginas, mas é lido por "
                    "ferramentas de extração.",
                    "Um sistema de IA que processe o documento pode receber "
                    "essa instrução como se fosse parte do pedido do usuário e "
                    "alterar resumos, classificações ou pareceres, sem que o "
                    "leitor humano perceba.",
                    location,
                    "Tratar como tentativa deliberada de manipulação: preservar "
                    "o original como prova e não submeter o documento a "
                    "ferramentas de IA. A sanitização agressiva remove esse "
                    "conteúdo na cópia de trabalho.",
                    "A área destacada em vermelho indica a posição do elemento "
                    "na página.",
                )

        academic = (
            " O trecho contém termos de contexto acadêmico, o que pode indicar "
            "citação legítima; ainda assim, a gravidade foi mantida."
            if "acadêmico" in title else ""
        )
        return _explain(
            "Instrução direcionada a IA no texto",
            "O texto do documento contém um padrão típico de instrução dirigida "
            "a sistemas de IA (prompt injection)." + academic,
            "Um sistema de IA que leia o documento pode obedecer a essa "
            "instrução e produzir resumos, classificações ou pareceres "
            "distorcidos, sem que o leitor humano perceba.",
            "Conteúdo textual da página",
            "Verificar se o trecho está visível na leitura normal. Se não "
            "estiver, tratar como tentativa deliberada de manipulação: "
            "preservar o original e usar cópia sanitizada para qualquer "
            "processamento automatizado.",
            "A área destacada em vermelho indica a posição do trecho na página. "
            "Se o texto estiver oculto, a área pode parecer vazia.",
        )

    if category == "hidden_text":
        return _explain(
            "Texto em cor branca",
            "Há texto na cor branca, que normalmente não é visto sobre fundo "
            "branco, mas é extraído por ferramentas automatizadas.",
            "Conteúdo invisível ao leitor humano pode ser lido e interpretado "
            "por sistemas de IA. Também pode ser recurso legítimo de "
            "diagramação, por isso a confiança deste achado é indicada abaixo.",
            "Conteúdo textual da página",
            "Selecionar o trecho no leitor de PDF (Ctrl+A) para confirmar se "
            "está oculto e avaliar se o conteúdo tem relação com o documento.",
            "O texto destacado é branco e por isso não aparece na imagem. O "
            "conteúdo extraído está transcrito acima.",
        )

    if category == "javascript":
        return _explain(
            "Código JavaScript embutido",
            "O PDF contém scripts registrados na sua estrutura interna.",
            "Scripts podem executar ações ao abrir ou interagir com o "
            "documento, como abrir endereços externos ou alterar campos.",
            "Estrutura interna do PDF (árvore de nomes /JavaScript)",
            "Abrir apenas em leitor com JavaScript desativado e usar cópia "
            "sanitizada.",
        )

    if category == "embedded":
        return _explain(
            "Arquivos anexados ao PDF",
            "O documento traz arquivos incorporados dentro dele.",
            "Anexos não são analisados por esta ferramenta e podem conter "
            "qualquer tipo de conteúdo, inclusive instruções ou executáveis.",
            "Estrutura interna do PDF (árvore de nomes /EmbeddedFiles)",
            "Extrair e verificar cada anexo separadamente antes de usá-lo.",
        )

    if category == "metadata":
        return _explain(
            "Metadados XMP presentes",
            "O documento possui um bloco de metadados XMP. Isso é comum e, por "
            "si só, não indica problema.",
            "Metadados não aparecem na leitura, mas são lidos por sistemas "
            "automatizados e podem carregar texto arbitrário.",
            "Metadados internos do PDF",
            "Consultar a tabela de metadados deste laudo e verificar se há "
            "conteúdo estranho ao documento.",
        )

    if category == "alt_text":
        return _explain(
            "Texto alternativo de imagem",
            "Uma imagem ou elemento do documento possui descrição alternativa "
            "(/Alt). O conteúdo não apresentou padrão de instrução a IA.",
            "Registro informativo: o texto alternativo é lido por ferramentas "
            "automatizadas, mas não pelo leitor comum.",
            "Árvore de estrutura do PDF (atributo /Alt)",
            "Nenhuma providência necessária, salvo se o conteúdo for estranho "
            "ao documento.",
        )

    if category == "structure":
        if "OpenAction" in title:
            return _explain(
                "Ação automática ao abrir o PDF",
                "O documento define uma ação executada automaticamente quando "
                "é aberto.",
                "Pode ser apenas um comando de navegação (abrir em determinada "
                "página), mas também pode disparar scripts ou abrir endereços "
                "externos.",
                "Catálogo do PDF (/OpenAction)",
                "Verificar o tipo de ação no detalhe técnico. Em caso de "
                "dúvida, usar cópia sanitizada.",
            )
        if "AcroForm" in title:
            return _explain(
                "Formulário interativo",
                "O documento contém campos de formulário preenchíveis.",
                "Campos de formulário podem guardar valores e ações não "
                "visíveis na leitura normal.",
                "Catálogo do PDF (/AcroForm)",
                "Verificar se o formulário é esperado para este tipo de "
                "documento.",
            )
        if "Optional Content" in title:
            return _explain(
                "Camadas opcionais",
                "O documento possui camadas que podem ser exibidas ou ocultadas "
                "pelo leitor de PDF.",
                "Uma camada oculta pode conter texto que não aparece na tela, "
                "mas é lido por ferramentas automatizadas.",
                "Catálogo do PDF (/OCProperties)",
                "Exibir todas as camadas no leitor de PDF e comparar com a "
                "versão visível.",
            )

    if category == "semantic":
        return _explain(
            title,
            "A estrutura do PDF contém um marcador associado a conteúdo oculto "
            "ou ativo.",
            "Indicador de baixa especificidade, a ser lido em conjunto com os "
            "demais achados.",
            "Estrutura interna do PDF",
            "Revisar em conjunto com os demais achados.",
        )

    return _explain(
        title,
        "Elemento registrado pela análise automatizada.",
        "Revisão manual recomendada.",
        "Estrutura interna do PDF",
        "Analisar o detalhe técnico e o contexto do documento.",
    )
