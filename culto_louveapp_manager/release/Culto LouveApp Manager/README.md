# Culto LouveApp Manager

Aplicativo desktop em Python para substituir e evoluir a logica do arquivo `BOLETIM_VBA_CORRIGIDO.xlsm`. Ele permite cadastrar boletins de culto, importar dados do Excel legado, manter a lista de pessoas do louvor, importar escalas do LouveApp com Playwright, exportar dados para Excel/CSV e gerar boletim ou repertorio em DOCX.

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
LOUVEAPP_EMAIL=seumaillouveapp
LOUVEAPP_PASSWORD=coloque_sua_senha_aqui
HEADLESS=false
SLOW_MO_MS=150
```

Troque `LOUVEAPP_PASSWORD` pela senha real. A senha nao e salva no banco, nao e impressa no terminal e nao deve ser commitada.

## Como rodar

```bash
python main.py
```

## Como abrir sem terminal

Foi gerado um pacote Windows em:

```text
release/Culto LouveApp Manager/
```

Para abrir sem PowerShell ou terminal, clique duas vezes em:

```text
release/Culto LouveApp Manager/Culto LouveApp Manager.exe
```

Mantenha o `.exe` dentro dessa pasta, junto da pasta `_internal`. O arquivo `.env` fica fora do executavel, na mesma pasta do `.exe`, para nao embutir senha no programa.

Na primeira abertura, o banco SQLite e criado automaticamente em:

```text
data/culto_louveapp.sqlite3
```

## Importar o XLSM legado

1. Coloque o arquivo real em `legacy/BOLETIM_VBA_CORRIGIDO.xlsm` ou selecione o arquivo pela aba **Importar Excel Legado**.
2. Clique em **Inspecionar arquivo** para confirmar abas, cabecalhos e resumo VBA.
3. Clique em **Importar boletins** para ler a aba `Planilha1`.
4. Clique em **Importar pessoas do louvor** para ler a aba `LOUVOR`.

O sistema nunca executa macros VBA. Ele apenas le dados da planilha.

## Importar do LouveApp

1. Garanta que `.env` exista com email e senha.
2. Clique em **Importar escalas do LouveApp**.
3. O app abre o navegador, acessa `https://app.louveapp.com.br/#/login`, tenta os seletores conhecidos de login e procura escalas em menus e rotas provaveis.

A importacao roda em thread separada para a interface continuar responsiva. Se nenhuma escala for encontrada, o app salva HTML e screenshot em `data/debug/` e mostra mensagem amigavel.

## Cadastro de boletins

Na aba **Boletins** voce pode:

- criar novo boletim
- salvar
- editar
- excluir com confirmacao
- limpar o formulario
- pesquisar por data
- gerar boletim DOCX
- gerar repertorio DOCX

### Uso com escala do LouveApp

No topo do formulario de boletim existe o campo **Escala LouveApp**. Ao escolher uma escala, os campos de musica do boletim passam a abrir uma lista com apenas as musicas daquela escala.

O sistema nao distribui as musicas automaticamente entre preludio, louvor, ofertas ou ceia, porque o LouveApp nao informa em qual momento cada musica sera tocada. A escolha de cada campo continua manual e filtrada pela escala selecionada. Quando a musica importada tem cantor/grupo e tom, os campos correspondentes sao preenchidos automaticamente.

## Pessoas do Louvor

A aba **Pessoas do Louvor** permite adicionar, editar, buscar e inativar nomes. Pessoas inativas permanecem no banco para historico.

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

A aba **Debug/Logs** mostra os ultimos logs e abre as pastas `data/debug` e `output`.

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

**Erro ao exportar**

Confira se as dependencias foram instaladas com `pip install -r requirements.txt` e se a pasta `output/` tem permissao de escrita.
