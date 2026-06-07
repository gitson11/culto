# Configuração do backend PHP + MySQL

Este material mostra como colocar a API mínima (`backend/api.php`) e a base de dados (`backend/schema.sql`) em funcionamento:

1. **Crie o banco de dados:** no phpMyAdmin (ou cliente MySQL), importe `backend/schema.sql`. Ajuste o nome da base de dados para `culto` ou outro preferido e certifique-se de apontar o `CREATE DATABASE` caso necessário.
2. **Configure o acesso:** copie `backend/config.sample.php` para `backend/config.php` e preencha as credenciais (`host`, `database`, `user`, `password`). Evite subir o `config.php` para repositórios públicos.
3. **Teste a API:**  
   ```bash
   php -S localhost:8000 -t backend
   curl http://localhost:8000/api.php
   ```  
   A resposta deve ser um JSON com todas as linhas da tabela `cultos`.
3.1 **Sincronize os dados do Excel:** gere `data/cultos.json` com `python scripts/export_cultos.py` e rode `python scripts/json_to_sql.py` para obter um `data/cultos-import.sql` pronto para importação (ou para verificar os inserts existentes).
4. **Integre ao front-end:** edite `web/app.js` e defina `USE_API = true` (linha no topo) e `API_URL = '../backend/api.php'` para carregar dos dados em vez do arquivo estático `data/cultos.json`.
5. **Inserções via API (opcional):**  
   ```bash
   curl -X POST http://localhost:8000/api.php \
     -H "Content-Type: application/json" \
     -d '{"data_texto":"DOMINGO...", "dirigente":"Nome"}'
   ```  
   A API validará e retornará o `id` criado.
6. **Rodando no servidor:** monte um Apache/Nginx com PHP 8, aponte o DocumentRoot para o diretório raiz (`e.g. /var/www/culto`) e deixe o `web` servido via alias ou link simbólico. Mantenha o Excel como backup e use o JSON/API para as operações online.
