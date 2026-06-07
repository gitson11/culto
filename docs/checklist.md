# Checklist de migração e publicação

1. **Configuração do backend**
   - Copie `backend/config.sample.php` para `backend/config.php` e preencha host, usuário, senha e nome da base.
   - Importe `backend/schema.sql` no MySQL/phpMyAdmin e execute `python scripts/export_cultos.py` + `python scripts/json_to_sql.py` para gerar os dados.
   - Importe `data/cultos-import.sql` para manter a tabela `cultos` sincronizada com o Excel.

2. **Validação de boletins**
   - Rode `php -S localhost:8000 -t backend` em `F:\Xampp\htdocs\CULTO`.
   - Acesse `http://localhost:8000/api.php` e `http://localhost:8000/boletim.php?data=YYYY-MM-DD` para verificar JSON/HTML.
   - Use `wkhtmltopdf` ou DomPDF sobre o mesmo endpoint para gerar a versão PDF.

3. **Template + placeholders**
   - Atualize `backend/templates/boletim-template.html` com as seções extras (oração, ofertas/intercessão e ceia).
   - O backend PHP (`backend/boletim.php`) já preenche `{{oracao}}`, `{{ofertas_ref}}`, `{{musica_pao}}`, etc.; garanta que novos campos sejam mapeados na planilha.
   - Rode `PYTHONIOENCODING=utf-8 python scripts/validate_placeholders.py` para checar quais `#PLACEHOLDER`s do Word ainda faltam no template/PHP.

4. **Front-end**
   - Defina `USE_API = true` em `web/app.js` e sirva `web/index.html` no mesmo host (ou via proxy) para consumir os dados reais.
   - Teste filtros, cartões, links e sincronize novos cultos executando `python scripts/export_cultos.py`.

5. **Operação contínua**
   - Reexecute os exportadores sempre que o Excel for atualizado.
   - Mantenha o índice (`scripts/bulletin_index.py`) e `data/cultos.json` versionados para situações de auditoria.
