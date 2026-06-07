# Resumo dos macros do `BOLETIM.xlsm`

Este arquivo automação combina um formulário principal, uma planilha central (`CULTOS`) e várias rotinas VBA para cadastrar, editar, excluir e exportar cultos (ceia e celebração). A seguir, o que já existe e o que vale a pena revisar:

## Componentes principais

- **Planilha `CULTOS`** é a tabela mestra (46 colunas) que guarda: data, dirigente, prelúdio, referências bíblicas, textos, músicas (até 5 escolhas), ofertas, intercessões, pregador, elementos da ceia (pão, vinho) e música final. As macros referenciam colunas fixas para alimentar o formulário e gerar o boletim.
- **Planilha `INTEGRANTES`** apenas lista nomes; não tem macros associadas visíveis no código fonte atual.

## Formulários e fluxos

- `UserForm1`: tela inicial com botões de rádio para escolher entre Ceia e Celebração; chama `Módulo1.Escolha` quando você pressiona “Abrir”.
- `Ceia` (UserForm principal):
  - Possui botões para cadastro (`btnsalvar`), edição (`btneditar`), exclusão (`btnexcluir`), limpeza (`btnlimpar`) e abertura do boletim (`btnboletim`).
  - `btnboletim_Click` instancia o Word, abre o arquivo `MODELO DE BOLETIM.docx`, procura placeholders como `#DATA`, `#PBANDA`, `#PREFACEO` etc., e substitui cada bloco com os valores atuais do formulário.
  - Os campos de texto são habilitados/desabilitados pelos procedimentos `HabilitaTextoCeia` / `DesabilitaTextoCeia`, e `LimparTextoCeia` reseta inputs após salvar/excluir.
  - `btnpesquisar` localiza uma data na planilha (`Cells.Find`) e puxa todas as colunas correspondentes para o formulário para edição/visualização; também habilita os botões adequados.

- `Celebracao` (userform secundário): apenas mostra o formulário e, ao fechar, volta para `UserForm1`.

## Módulos e rotina de dados

- `Módulo1` contém:
  - Variáveis globais (`Tecla`, `Arr`, etc.) que não são usadas de forma evidente na versão atual, mas podem ter sido prepósitos de um menu dinâmico mais antigo.
  - `Escolha`: checa qual opção foi marcada e exibe o formulário correspondente (`Ceia.Show` ou `Celebracao.Show`).
  - `SalvarCeia`: verifica duplicados (CountIf na coluna de datas), insere a nova linha no fim da tabela e chama `Call LimparTextoCeia`.
  - `EditarCeia`: localiza a data e substitui cada coluna pela nova entrada (agenda 1:1 com `SalvarCeia`), com tratamento de erros genérico e mensagens padrão (`MsgBox`).
  - `ExcluirCeia`: pede confirmação e apaga a linha inteira.
  - Rotinas auxiliares (`LimparTextoCeia`, `HabilitaTextoCeia`, `DesabilitaTextoCeia`) limpam e controlam o estado dos campos do formulário.

## Observações e próximos passos

1. **Acoplamento forte com Word:** os macros usam `CreateObject("Word.Application")` e `Selection.Find` para substituir placeholders. Essa técnica funciona, mas é frágil (dependências de caminho, placeholders sensíveis a capitalização e falta de tratamento de erros se o Word não estiver instalado). Ao migrar para web/API, essa etapa pode virar uma exportação via template HTML+CSS ou gerar PDFs a partir de HTML.
2. **Validação mínima:** os formulários dependem de `CountIf`/`Cells.Find`, mas não há controle de duplicação por ID nem transações. Um backend baseado em banco de dados permitiria constraints mais rígidas e versionamento por linha.
3. **Formulários inchados:** `Ceia` controla diretamente dezenas de campos e colunas; isso pode ser parametrizado via metadados (por exemplo, uma lista de seções ou um arquivo JSON que identifica os campos). Para a web, o mesmo componente pode renderizar seções recorrentes em um loop, reduzindo código repetido.
4. **Formulário `UserForm_Resize`:** reescala controles manualmente — na web podemos replicar o efeito com CSS responsivo e componentes Bootstrap.
5. **Sugestão (médio prazo):** exportar os dados da planilha para um JSON estruturado e servir via API, mantendo o Excel apenas como repositório de backup. A interface web que veremos nos próximos passos pode consumir esse JSON para pesquisas/edições e usar endpoints PHP/Python para CRUD.

## Material de referência

- `MODELO DE BOLETIM.docx` / `MODELO DE BOLETIM CEIA.docx`: arquivos usados pelo botão `btnboletim` (você pode migrar a lógica de placeholders para um motor de templates atual como Jinja2, PHP/Twig ou Handlebars).
- `scripts/bulletin_index.py` (novo): gera o índice geral, útil para saber quais datas já existem.
- Sugestão: mantenha esse documento atualizado para que qualquer nova macro ou formulário seja documentado em texto legível.
