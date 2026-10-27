# LexSentinel - Raio-X PDF

<p align="center">
  <img src="assets/icon.png" width="140" alt="LexSentinel">
</p>

<p align="center">
  <strong>Ferramenta defensiva para análise de PDFs.</strong>
</p>

<p align="center">
  Identifica estruturas, conteúdo oculto, ações, scripts, prompt injection e outros elementos que possam representar risco para processamento automatizado e sistemas de IA.
</p>

---

## O que é o LexSentinel

O LexSentinel é uma ferramenta de **análise defensiva** de documentos PDF. Seu objetivo é auxiliar na identificação de artefatos potencialmente capazes de:

- ocultar conteúdo relevante;
- manipular interpretação automatizada de documentos;
- incorporar elementos ativos ou suspeitos;
- introduzir vetores de prompt injection;
- mascarar comandos ou instruções invisíveis.

**O LexSentinel não é um antivírus nem uma garantia de PDF "seguro".** Ele sinaliza e analisa elementos suspeitos, funcionando como uma camada defensiva complementar. Os resultados devem ser interpretados por um profissional qualificado.

---

## Detecção de Prompt Injection

O LexSentinel detecta marcadores de Prompt Injection em texto extraído de PDFs, incluindo:

- instruções direcionadas a sistemas de IA (em português e inglês);
- marcadores como `ignore previous instructions`, `ignore instruções`, `aja como`, entre outros;
- preservação do texto original no achado para inspeção manual.

**Onde o texto é procurado:**

- texto de todas as páginas, analisado de forma contínua: uma instrução dividida em trechos diferentes (por exemplo, `ignore previous` + `instructions` com formatação distinta) também é identificada;
- metadados do documento (dicionário Info: Título, Autor, Assunto, Palavras-chave e campos personalizados);
- metadados XMP;
- comentários e anotações;
- campos de formulário (valor, rótulo e nome);
- marcadores do sumário (bookmarks);
- texto alternativo (`/Alt`) da árvore de estrutura.

**Normalização antes da comparação:**

- espaços irregulares (múltiplos, tabs, quebras de linha);
- caracteres invisíveis de formatação, como espaço de largura zero (`U+200B`) e hífen invisível (`U+00AD`);
- variantes Unicode de letras (letras de largura total, ligaduras), via NFKC;
- acentuação: `instrucoes` é reconhecido como `instruções`.

**Comportamento importante:**

- Prompt Injection detectado é classificado como **CRITICAL** (score 100);
- contexto acadêmico **não** faz downgrade de um injection detectado;
- o contexto acadêmico é registrado no título do achado para informação, mas a severidade permanece CRITICAL;
- Prompt Injection também é analisado em **alt-text** da Structure Tree;
- alt-text em qualquer tipo de elemento (`/Standard`, `/Div`, `/P`, `/Span`, etc.) é inspecionado, não apenas `/Figure`, `/Formula` ou `/Form`.

---

## Conteúdo oculto

Detecção de:

- **texto branco/suspeito**: textos com cor `#FFFFFF` (visíveis apenas por seleção);
- **camadas e estruturas de ocultação**: elementos com tamanhos ou posições anômalas;
- **elementos relevantes** identificados pelos analyzers existentes.

---

## Sanitização PDF

O LexSentinel oferece dois modos de sanitização:

### Sanitização estrutural

Remove ou neutraliza vetores estruturais do PDF, incluindo:

- **OpenAction** — ação executada ao abrir o documento;
- **Additional Actions (/AA)** — ações adicionais em documento, páginas e anotações;
- **Launch** — execução de programas externos;
- **ImportData** — importação de dados externos;
- **JavaScript** — código executável embutido;
- **EmbeddedFiles** — arquivos incorporados;
- **AcroForm** — formulários interativos;
- **RichMediaExecute** — conteúdo multimídia interativo;
- **Sound/Movie em anotações** — anotações de áudio/vídeo;
- **Metadata** — metadados XMP estruturais;
- **OCProperties** — camadas opcionais (OCG);
- **SubmitForm** — envio de formulários.

A detecção de ações utiliza a chave `/S` (tipo de ação), não literais de string, o que permite identificar vetores mesmo quando renomeados.

**Limitação conhecida:** `/JBIG2Decode` **não é removido** automaticamente pela sanitização estrutural. É um filtro legítimo de compressão de imagens e sua remoção indiscriminada pode destruir conteúdo do documento.

### Sanitização agressiva (flattening)

Converte cada página do PDF em imagem de alta resolução (2x), eliminando todo o conteúdo vetorial, scripts, camadas ocultas e elementos interativos. O resultado é um PDF "plano" contendo apenas imagens.

---

## Alt-text (Structure Tree)

O LexSentinel inspeciona o atributo `/Alt` da árvore de estrutura do PDF:

- extração de `/Alt` de todos os tipos de elementos (`/Figure`, `/Formula`, `/Form`, `/Standard`, `/Div`, `/P`, `/Span`, etc.);
- análise do conteúdo para Prompt Injection — injection em alt-text é **CRITICAL**;
- alt-text normal em `/Figure`, `/Formula` ou `/Form` aparece como informação (INFO);
- **não há OCR** — apenas texto estrutural é analisado.

---

## Análise em lote

```bash
lexsentinel batch <paths...>
```

Permite análise de múltiplos arquivos PDF de uma vez.

**Opções:**

| Opção | Descrição |
|-------|-----------|
| `--recursive`, `-r` | Busca recursiva em diretórios |
| `--json`, `-j` | Salva resultados agregados em JSON |
| `--output-dir` | Diretório para JSONs individuais por arquivo |

**Comportamento:**

- aceita arquivos e diretórios como argumentos;
- diretórios são varridos por arquivos `.pdf`;
- erros são tratados individualmente (um arquivo com erro não interrompe o lote);
- processamento atualmente é sequencial.

---

## Verificação de pacotes

```bash
lexsentinel check-packages
```

Verifica as dependências instaladas do projeto:

- compara versões instaladas com os requisitos do pacote;
- suporta version specifiers (`>=`, `<=`, `==`, `!=`, `~=`);
- reporta pacotes ausentes ou com versão incompatível;
- **pip-audit é opcional**: se não estiver instalado, a verificação de vulnerabilidades não é executada (não deve ser confundida com "nenhuma vulnerabilidade encontrada").

---

## Relatórios

Geração de relatórios nos seguintes formatos:

| Formato | Descrição |
|---------|-----------|
| **HTML** | Laudo técnico completo em arquivo único (imagens de evidência embutidas), pronto para envio |
| **JSON** | Dados estruturados dos resultados, com data da análise e versão, para integração com outras ferramentas |
| **PDF** | Laudo em A4, com numeração de páginas e nº do laudo no rodapé (gerado a partir do HTML) |

O laudo é organizado em seções numeradas:

- **cabeçalho**: nº do laudo, data e hora da análise (com fuso horário), versão da ferramenta e classificação de risco;
- **1. Conclusão**: texto em linguagem clara com os principais achados e a recomendação, e contagem por gravidade;
- **2. Documento analisado**: nome, hash SHA-256, tamanho, nº de páginas, versão do formato e metadados declarados;
- **3. Quadro de achados**: tabela resumida, ordenada por gravidade;
- **4. Detalhamento dos achados**: para cada achado, o que foi encontrado, o trecho exato, por que importa, localização, confiança da detecção, recomendação e evidência visual recortada em volta do trecho;
- **5. Metodologia e limitações**: o que foi verificado e, de forma explícita, o que não foi;
- **anexo**: ambiente técnico e ressalva.

As imagens de evidência também são salvas na pasta `evidencias/`, com o nome do PDF analisado no nome do arquivo, para que análises de documentos diferentes na mesma pasta não se sobrescrevam.

---

## GUI (Interface gráfica)

A interface gráfica permite:

- selecionar PDFs (clique ou arrastar);
- executar análise e visualizar resultados;
- sanitizar documentos;
- abrir relatórios HTML, PDF e pasta de destino;
- visualizar texto extraído;
- verificar atualizações de segurança.

**Executar a partir do código-fonte:**

```bash
lexsentinel-gui
```

---

## Instalação

### Flatpak

Baixe o arquivo `.flatpak` na aba Releases do GitHub.

```bash
flatpak install LexSentinel.flatpak
flatpak run io.github.VanglDev.LexSentinel
```

### Código-fonte (desenvolvimento)

```bash
git clone https://github.com/Vangl-dev/lexsentinel.git
cd lexsentinel

python -m venv .venv
source .venv/bin/activate

pip install -e .

# Interface gráfica
lexsentinel-gui

# Interface de linha de comando
lexsentinel analyze <arquivo.pdf>
```

**Dependências:** Python >= 3.11, pymupdf, pikepdf, weasyprint, PySide6, typer, rich.

---

## Público-alvo

- advogados;
- peritos;
- analistas forenses;
- profissionais de compliance;
- pesquisadores de segurança;
- equipes de segurança documental.

---

## Limitações conhecidas

- `/JBIG2Decode` não é removido pela sanitização estrutural (filtro legítimo de compressão);
- alt-text depende da Structure Tree e não faz OCR;
- pip-audit é opcional — sua ausência não significa que a auditoria de vulnerabilidades foi executada;
- análise em lote é atualmente sequencial;
- detecção de Prompt Injection é baseada nos marcadores implementados e não deve ser apresentada como detector semântico universal; variações de redação não previstas (como `ignore todas as instruções anteriores`) podem não ser identificadas;
- texto posicionado fora da área visível da página não é analisado;
- o conteúdo de arquivos anexados ao PDF não é analisado;
- a sanitização agressiva converte páginas em imagens, perdendo texto pesquisável;
- PDFs protegidos por senha não podem ser analisados.

---

## Segurança e responsabilidade

O LexSentinel realiza **triagem técnica preliminar automatizada**. Não substitui:

- perícia forense completa;
- auditoria especializada;
- análise humana contextual;
- validação pericial formal.

A ferramenta **identifica**, **sinaliza** e **analisa** elementos suspeitos, **reduzindo risco** como parte de uma estratégia defensiva. Não deve ser interpretada como solução definitiva de segurança documental.

---

## Estado do projeto

**Release Candidate / Beta** — projeto em evolução ativa.

Empacotamento Flatpak em andamento. AppImage experimental foi descontinuado.

Roadmap:

- refinamento de sanitização;
- melhorias de UX;
- novas heurísticas;
- maior granularidade de explicações;
- expansão da análise estrutural.

---

## Licença

MIT
