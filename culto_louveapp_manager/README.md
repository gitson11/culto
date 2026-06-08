# Ordem Liturgica

**Gestao de boletins, escalas e repertorios do culto.**

Ordem Liturgica e um aplicativo desktop em Python para organizar a preparacao do culto: cadastro de boletins, importacao de dados do Excel legado, gestao de integrantes do ministerio, importacao de escalas do LouveApp, exportacao para Excel/CSV e geracao de boletins ou repertorios em DOCX.

> Decencia e ordem no servico cristao. Referencia conceitual: 1 Corintios 14:40.

## Tecnologias

- Python 3.10+
- CustomTkinter para interface desktop
- SQLite para banco local
- Playwright para automacao do LouveApp
- pandas e openpyxl para exportacoes Excel/CSV
- python-docx para documentos Word
- python-dotenv para variaveis de ambiente

## Instalacao

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Depois instale as dependencias:

```bash
pip install -r requirements.txt
playwright install chromium
```

## Configuracao do .env

O app abre sem `.env`. O arquivo so e obrigatorio quando voce clicar para importar escalas do LouveApp.

Crie uma copia de `.env.example` chamada `.env`:

```env
LOUVEAPP_EMAIL=rubemacesso@gmail.com
LOUVEAPP_PASSWORD=coloque_sua_senha_aqui
HEADLESS=false
SLOW_MO_MS=150
```

Troque `LOUVEAPP_PASSWORD` pela senha real. A senha nao e salva no banco, nao e impressa no terminal e nao deve ser commitada.

## Como rodar

Entre na pasta do aplicativo:

```bash
cd culto_louveapp_manager
python main.py
```

## Identidade visual e icone

A pasta de identidade visual fica em:

```text
assets/
```

O sistema procura automaticamente um icone em:

```text
assets/ordem_liturgica.ico
assets/app.ico
```

Se um desses arquivos existir, ele sera usado como icone da janela no Windows.

## Banco de dados

Na primeira abertura, o banco SQLite e criado automaticamente em:

```text
data/ordem_liturgica.sqlite3
```

Para preservar compatibilidade, se ja existir o banco antigo abaixo, o sistema continuara usando ele:

```text
data/culto_louveapp.sqlite3
```

## Modelos de boletim

Os modelos oficiais de boletim ficam em:

```text
templates/
```

O sistema aceita multiplos arquivos `.docx`. Cada arquivo pode representar um tipo diferente de culto, por exemplo:

```text
templates/modelo de boletim comum.docx
templates/modelo de boletim ceia.docx
```

Na aba **Boletins** e na aba **Exportacoes**, escolha o modelo desejado antes de gerar o boletim. Se houver mais de um modelo e nenhum for escolhido, o sistema solicitara a escolha do tipo de culto.

Para alterar o visual do boletim, edite o arquivo Word do modelo. O Python apenas substitui os placeholders.

A lista completa de placeholders aceitos fica em:

```text
templates/PLACEHOLDERS.md
```

A substituicao ocorre no corpo do documento, tabelas, cabecalhos e rodapes.

## Importar o XLSM legado

1. Coloque o arquivo real em `legacy/BOLETIM_VBA_CORRIGIDO.xlsm` ou selecione o arquivo pela aba **Excel Legado**.
2. Clique em **Inspecionar** para confirmar abas, cabecalhos e resumo VBA.
3. Clique em **Importar boletins** para ler a aba `Planilha1`.
4. Clique em **Importar integrantes** para ler a aba `LOUVOR`.

O sistema nunca executa macros VBA. Ele apenas le dados da planilha.

## Importar do LouveApp

1. Garanta que `.env` exista com email e senha.
2. Abra a aba **Escalas**.
3. Clique em **Importar LouveApp**.
4. O app abre o navegador, acessa `https://app.louveapp.com.br/#/login`, tenta os seletores conhecidos de login e procura escalas em menus e rotas provaveis.

A importacao roda em thread separada para a interface continuar responsiva. Se nenhuma escala for encontrada, o app salva HTML e screenshot em `data/debug/` e mostra mensagem amigavel.

## Boletins

Na aba **Boletins** voce pode:

- criar novo boletim
- salvar
- editar
- excluir com confirmacao
- limpar o formulario
- pesquisar por data
- escolher o modelo de boletim
- gerar boletim DOCX a partir do modelo escolhido
- gerar repertorio DOCX

## Ministerio

A aba **Ministerio** permite adicionar, editar, buscar e inativar integrantes. Integrantes inativos permanecem no banco para historico.

## Exportacoes

A aba **Exportacoes** gera:

- `output/boletins_*.xlsx`
- `output/boletins_*.csv`
- `output/escalas_louveapp_*.xlsx`
- `output/escalas_louveapp_*.csv`
- `output/boletim_*.docx`
- `output/repertorio_*.docx`

Os arquivos Excel possuem data de geracao, cabecalho congelado, filtro e largura de colunas ajustada.

## Logs e debug

Logs ficam em:

```text
data/app.log
```

Arquivos de debug da automacao web ficam em:

```text
data/debug/
```

A aba **Logs** mostra os ultimos logs e abre as pastas `data/debug`, `templates` e `output`.

## Solucao de problemas

**O app abre, mas a importacao LouveApp falha por .env ausente**

Crie `.env` a partir de `.env.example`. O `.env` so e necessario para importar do LouveApp.

**Falha ao abrir navegador**

Execute:

```bash
playwright install chromium
```

**Campos de login nao encontrados**

O LouveApp pode ter mudado a interface. Veja os arquivos em `data/debug/` para ajustar seletores em `src/louveapp_browser.py`.

**Nenhuma escala encontrada**

Veja HTML e screenshot em `data/debug/`. O scraper foi feito para tentar menus, rotas e fallback por texto, mas pode precisar de ajuste se a estrutura da pagina mudar.

**Arquivo XLSM nao encontrado**

Coloque `BOLETIM_VBA_CORRIGIDO.xlsm` em `legacy/` ou selecione o arquivo manualmente na interface.

**Aba Planilha1 ou LOUVOR nao encontrada**

Confira se o arquivo selecionado e o boletim legado correto.

**Nenhum modelo de boletim aparece**

Coloque os arquivos `.docx` dos modelos dentro da pasta `templates/` e clique em **Atualizar modelos**.

**Erro ao exportar**

Confira se as dependencias foram instaladas com `pip install -r requirements.txt` e se a pasta `output/` tem permissao de escrita.
