# SEARCHAI

Ferramenta de linha de comando para pesquisar na web, baixar o conteudo das fontes encontradas e gerar um resumo com IA.

## O que o projeto faz

- Pesquisa no duckduckgo.
- Baixa o conteudo das URLs encontradas.
- Resume cada fonte individualmente em formato Markdown.
- Gera um resumo final consolidado em formato Markdown.
- Salva tudo em uma pasta de saida com manifesto e links.

## Provedores de IA suportados

- lmstudio ou ollama (padrao local)

## Requisitos

- Python 3.14+
- uv
- Acesso a internet

## Instalacao

1. Clonar o repositorio.
2. Instalar dependencias:

uv sync

## Inicio rapido

1. Rode uma busca simples (usa configuracao padrao):

uv run main.py energia solar brasil

2. Ou passe via stdin:

echo "energia solar brasil" | uv run main.py

## Configuracao

Sem --config, o programa procura nesta ordem:

1. ./config.yaml
2. $HOME/.config/searchai/config.yaml

Exemplo de config.yaml:

```yaml
api_endpoint: http://127.0.0.1:1234
ai_provider: lmstudio
api_key: null
max_results: 5
download_timeout: 20
max_download_bytes: 2000000
max_prompt_chars: 100000
model_timeout: 30m

engines:
  - duckduckgo
```

### Campos importantes

- ai_provider: lmstudio, chatgpt ou gemini.
- api_endpoint: url do seu provedor de IA local, ex: http://127.0.0.1:1234
- model_timeout:
  - aceita numero em segundos (ex.: 600)
  - aceita formato amigavel (ex.: 45s, 10m, 4h, 2d)

## Uso

Busca com termos posicionais:

```
uv run main.py mudancas climatica transicao energetica
```

## Saida gerada

Cada execucao cria uma pasta em $HOME/searchai no formato:

YYYY-MM-dd_HHmmss_<motores>_<consulta>

Arquivos principais:

- 001_*.md, 002_*.md...: resumo por fonte
- manifest.json: rastreabilidade dos resultados, downloads e falhas
- summary.md: resumo final com links encontrados

## Solucao de problemas

### Nenhum conteudo foi baixado

- Confira os limites da API do DuckDuckGo, você pode estar sendo limitado.
- Verifique conectividade de rede.
- Tente aumentar download_timeout e max_download_bytes.
- Reduza max_results para validar o fluxo.

### Falha ao acessar provedor de IA

- Confirme ai_provider.
- Verifique api_endpoint quando nao usar o endpoint padrao.

### DuckDuckGo sem resultados

Esse motor pode oscilar por limite pratico anti-abuso. Tente repetir a busca com menos volume.
