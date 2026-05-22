def explain_finding(finding):
    title = finding.title
    desc = finding.details
    category = finding.category

    if "OpenAction" in title:
        return {
            "human_title": "Ação automática ao abrir o PDF",
            "what": (
                "Este documento tenta executar uma ação automaticamente "
                "quando aberto."
            ),
            "impact": (
                "Pode influenciar sistemas automatizados ou acionar "
                "comportamentos inesperados."
            ),
            "location": "Estrutura interna do PDF",
            "recommendation": "Utilizar sanitização antes do compartilhamento."
        }

    if "JavaScript" in title:
        return {
            "human_title": "Código executável embutido",
            "what": (
                "O PDF contém scripts internos executáveis."
            ),
            "impact": (
                "Scripts podem alterar comportamento de leitura "
                "ou executar ações automáticas."
            ),
            "location": "Estrutura interna do PDF",
            "recommendation": "Sanitização recomendada."
        }

    if "Metadata" in title:
        return {
            "human_title": "Conteúdo oculto em metadados",
            "what": (
                "Foram encontrados dados internos invisíveis ao leitor comum."
            ),
            "impact": (
                "Ferramentas automatizadas podem acessar esse conteúdo."
            ),
            "location": "Metadados internos do PDF",
            "recommendation": "Revisar ou sanitizar."
        }

    if "prompt" in title.lower():
        return {
            "human_title": "Instrução direcionada a IA detectada",
            "what": desc,
            "impact": (
                "Esse conteúdo pode influenciar sistemas automatizados "
                "de leitura documental."
            ),
            "location": "Conteúdo textual do documento",
            "recommendation": (
                "Revisar o trecho e considerar sanitização agressiva."
            )
        }

    if "Hidden" in title or "Invisible" in title:
        return {
            "human_title": "Conteúdo oculto detectado",
            "what": (
                "Há conteúdo invisível ao leitor humano."
            ),
            "impact": (
                "Sistemas automatizados ainda podem interpretar esse conteúdo."
            ),
            "location": "Camadas internas ou objetos ocultos",
            "recommendation": "Sanitização agressiva recomendada."
        }

    return {
        "human_title": title,
        "what": desc,
        "impact": "Revisão manual recomendada.",
        "location": category,
        "recommendation": "Analisar contexto."
    }