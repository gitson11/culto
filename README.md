# Boletins do Culto

## Visão geral
- NOVOS BOLETINS e NOVOS BOLETINS EM PDF: origem manual mantida como referência histórica (Word/PDF) para cada culto.
- backend/: API PHP, templates HTML e CSS e o schema MySQL preparados para substituir a rotina do Excel.
- web/: painel Bootstrap com filtros, cards e agora um formulário para registrar cultos diretamente via API.
- scripts/: utilitários Python que exportam o Excel, validam placeholders, geram SQL e convertem HTML em PDF.

## Preparação via XAMPP (Windows)
1. Inicie Apache e MySQL no XAMPP Control Panel; o DocumentRoot deve seguir em F:\Xampp\htdocs e o projeto ficará acessível como http://localhost/CULTO.
2. Copie backend/config.sample.php para backend/config.php e atualize host, database, user e password com as credenciais que funcionam no seu phpMyAdmin.
3. Em http://localhost/phpmyadmin crie (ou selecione) o banco culto e importe backend/schema.sql.
4. No terminal em F:\Xampp\htdocs\CULTO execute:
   - python scripts/export_cultos.py para gerar data/cultos.json a partir do BOLETIM.xlsm.
   - python scripts/json_to_sql.py para produzir data/cultos-import.sql com os inserts prontos.
   - Importe data/cultos-import.sql no phpMyAdmin para popular a tabela cultos.

## Testando o backend e os boletins
- http://localhost/CULTO/backend/boletim.php?data=YYYY-MM-DD (ou ?data_texto=...) mostra o boletim HTML e alimenta relatórios em PDF via wkhtmltopdf ou dompdf.
- http://localhost/CULTO/backend/api.php lista cultos (GET) e aceita novos registros (POST com JSON); use esse endpoint para integrações ou testes manuais.

## Interface web e formulário
- Abra http://localhost/CULTO/web/index.html: o painel consome backend/api.php (USE_API = true) e mostra cards com dirigente, pregador, músicas, referência e resumo da Ceia.
- A nova seção Registrar um novo culto envia datas, músicas, oração/ofertas e informações da Ceia direto para a API. Após salvar, a lista, os cards e o boletim HTML são atualizados automaticamente.
- Esse formulário substitui o fluxo manual do Excel; mantenha o BOLETIM.xlsm apenas como backup e consulte docs/boletim-vba.md quando precisar rever macros.

## Scripts auxiliares
- scripts/export_cultos.py: extrai o formulário CULTOS do Excel e gera o JSON data/cultos.json.
- scripts/json_to_sql.py: mapeia o JSON nas colunas ampliadas do schema (orações, ofertas, intercessão e músicas) e produz SQL para importar no MySQL.
- scripts/validate_placeholders.py: garante que os #TAGs dos templates Word coincidem com o template HTML/PHP e com a API.
- scripts/generate_pdfs.py: transforma boletins HTML em PDFs usando wkhtmltopdf (o script pode ser adaptado com scripts/config.yml).
- scripts/bulletin_index.py: gera bulletin-index.json com inventário atualizado dos .docx e .pdf.

## Próximos passos
- Revise docs/checklist.md periodicamente para manter macros, placeholders e novos campos em sincronia.
- Quando precisar registrar outros detalhes (observações, responsáveis, status), estenda backend/schema.sql, backend/api.php, backend/boletim.php, scripts/json_to_sql.py e o formulário em web/index.html em conjunto.
- Versione o projeto no Git; confie no fluxo Excel -> JSON -> MySQL -> HTML/PDF para as operações regulares.
