# SEARCHAI

## Descrição
Agente de IA que faz pesquisas na internet e encontra resultados.

- Modelo de IA já estará carregado, não precisa se preocupar com isso.
- Se não conseguir usar a API do LMStudio, apenas imprimir um erro e morrer.
- Executar o agente com `uv run main.py`
- Criar um Makefile para executar o projeto.
- Aceitar argumentos na linha de comando para alterar o comportamento conforme a necessidade.
- Exemplos de argumentos iniciais:
  - --api-endpoint para informar o enderço para acessar o LMStudio (default http://127.0.0.1:1234)
  - Mais de um motor de busca pode ser usado ao mesmo tempo e a pesquisa será feita em todos que foram informados.
- Preparar sempre o código para receber customizações na linha de comando.

## Como funciona 
O agente abre um prompt na linha de comando e espera por palavras e expressões de busca. Ele não conversa, não precisa fazer um diálogo compreensivo, ele é simples e direto. Ao receber os termos de busca, o agente faz esta rotina:
1) Faz a pesquisa e recupera os resultados de cada motor de busca.
2) Enumera os sites encontrados e os links de cada um que foram encontrados.
3) Acessa cada link da resulta da pesquisa e junta o conteúdo de cada site (download do conteúdo).
4) Agrupa todo o download em uma pasta $HOME/searchai/${YYYY-MM-dd_HHmmss}_${search_engine}_${search_terms_slug}, em arquivos diferentes para cada busca feita.
# SEARCHAI

Agente de linha de comando que pesquisa na internet, baixa o conteúdo das páginas encontradas e usa um modelo disponível no LMStudio para preparar um resumo organizado.

## Requisitos

- Python 3.14 ou superior
- [uv](https://docs.astral.sh/uv/)
- LMStudio executando um servidor compatível com a API OpenAI
- Uma conexão com a internet

## Instalação

```bash
uv sync
```

## Configuração

Sem `--config`, o programa procura automaticamente por `./config.yaml` no diretório atual e, caso não exista, por `$HOME/.config/searchai/config.yaml`, nessa ordem. Um arquivo alternativo pode ser informado com `--config`.

Exemplo:

```yaml
api_endpoint: http://127.0.0.1:1234
max_results: 5
download_timeout: 20
max_download_bytes: 2000000
max_prompt_chars: 100000

engines:
  - duckduckgo
  - google
  - bing

engines_config:
  google:
    api_key: sua-chave-google
    search_engine_id: seu-id-cse
  bing:
    api_key: sua-chave-bing
```

Os motores disponíveis são `duckduckgo`, `google` e `bing`. Google também pode usar `GOOGLE_API_KEY` e `GOOGLE_CSE_ID`; Bing pode usar `BING_API_KEY`. Evite armazenar chaves reais em arquivos versionados.

Valores informados na linha de comando têm precedência sobre o YAML. Quando `--search-engine` não é usado, o programa utiliza a lista `engines` do arquivo. Sem arquivo e sem argumento, o padrão é `duckduckgo`.

## Uso

Antes de resumir, o programa carrega as instruções de `PROMPT.md` no diretório atual e as envia como a primeira mensagem ao LMStudio. A consulta e o conteúdo das páginas coletadas são enviados em seguida. O marcador `INCLUIR_TERMOS_DA_BUSCA_ORIGINAL`, quando presente, é substituído pelos termos reais da consulta.

Uma consulta pode ser passada diretamente:

```bash
uv run main.py --query "mudanças recentes em energia solar"
```

Ou lida de uma linha do stdin:

```bash
echo "mudanças recentes em energia solar" | uv run main.py
```

Argumentos disponíveis:

```text
--config PATH                 Arquivo YAML alternativo
--query TEXT                  Consulta; sem ele, lê stdin
--api-endpoint URL            Endpoint do LMStudio
--search-engine NOME         Pode ser repetido e substitui engines do YAML
--max-results N               Resultados por motor
--download-timeout SEGUNDOS   Timeout de cada download
--max-download-bytes N        Tamanho máximo de cada página
--max-prompt-chars N          Tamanho máximo enviado ao modelo
--model NOME                  Modelo do LMStudio; por padrão, usa o primeiro disponível
```

Também é possível executar pelo Makefile:

```bash
make run ARGS='--query "termo de busca" --search-engine duckduckgo'
```

## Saída

Cada execução cria uma pasta em `$HOME/searchai` no formato:

```text
YYYY-MM-dd_HHmmss_<motores>_<consulta>
```

A pasta contém um arquivo Markdown para cada página baixada. Cada arquivo recebe o resumo individual daquela fonte, além da URL e dos metadados. O `summary.md` é gerado em uma segunda etapa, resumindo todos os arquivos individuais. Ele também termina com uma seção `Links encontrados` com todos os resultados, usando o título de cada página como link Markdown para sua fonte.

Falhas de um motor ou de uma página são registradas e não interrompem as demais fontes. Se nenhuma página puder ser baixada, ou se o LMStudio não estiver acessível, o programa imprime um erro em stderr e termina com código diferente de zero.
5) Cria um prompt para usar a IA do LMStudio para resumir todo o conteúdo e mostrar as informações solicitadas na busca de forma organizada e estruturada.