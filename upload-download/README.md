# 🚀 API de Upload e Download de Arquivos (Production-Ready)

API RESTful em Python/Flask para gerenciamento seguro e de alta performance de upload e download de arquivos, com persistência em banco de dados SQLite, conteinerização via Docker e suporte completo a servidores WSGI de produção.

---

## 📋 Índice

1. [Visão Geral](#-visão-geral)
2. [Ajustes e Melhorias para Produção](#-ajustes-e-melhorias-para-produção)
3. [Estrutura do Projeto](#-estrutura-do-projeto)
4. [Variáveis de Ambiente](#-variáveis-de-ambiente)
5. [Instalação e Execução](#-instalação-e-execução)
   - [Opção 1: Produção com Docker e Docker Compose (Recomendado)](#opção-1-produção-com-docker-e-docker-compose-recomendado)
   - [Opção 2: Produção em Linux com Gunicorn](#opção-2-produção-em-linux-com-gunicorn)
   - [Opção 3: Produção em Windows com Waitress](#opção-3-produção-em-windows-com-waitress)
   - [Opção 4: Desenvolvimento Local](#opção-4-desenvolvimento-local)
6. [Documentação dos Endpoints](#-documentação-dos-endpoints)
7. [Testes Automatizados](#-testes-automatizados)
8. [Segurança e Boas Práticas](#-segurança-e-boas-práticas)

---

## 🌟 Visão Geral

A API foi desenvolvida utilizando o padrão arquitetural **MVC** (Model-View-Controller) com o padrão **Application Factory** do Flask. Ela permite o envio de arquivos de extensões autorizadas, armazenamento local estruturado, registro de metadados no SQLite e download protegido com sanitização contra ataques de travessia de diretório (*Path Traversal*).

---

## 🔧 Ajustes e Melhorias para Produção

O projeto recebeu uma ampla refatoração para adequação aos padrões industriais de segurança, confiabilidade e operabilidade (baseado nas diretrizes do *The Twelve-Factor App*):

| Categoria | Problema Original Encontrado | Solução / Ajuste Implementado |
|---|---|---|
| **Segurança** | `debug=True` ativado no código (`app.run(debug=True)`), expondo console interativo em caso de falha. | Debug desativado por padrão em produção; configuração controlada estritamente via variável de ambiente `FLASK_ENV`. |
| **Servidor WSGI** | Execução direta via servidor de desenvolvimento do Flask (inapropriado para produção). | Criado `wsgi.py` com suporte pronto para **Gunicorn** (Linux/Containers) e **Waitress** (Windows). |
| **Persistência / Models** | `UploadModel.save_file` existia mas **nunca** era chamado no controller; o banco ficava vazio. | O `UploadController` agora registra o arquivo, caminho, tamanho em bytes e data no banco SQLite. |
| **Integridade de Dados** | Sobrescrita silenciosa de arquivos caso outro upload usasse o mesmo nome. | Validação prévia de duplicidade: se já existir arquivo com mesmo nome, retorna `409 Conflict`. |
| **Rollback de Arquivos** | Se houvesse erro na persistência do banco, o arquivo ficava órfão no disco. | Implementado mecanismo de compensação: se o banco falhar, o arquivo recém-salvo é removido imediatamente do disco. |
| **Tratamento de Erros** | No download, `except FileNotFoundError` não capturava o erro `NotFound` do Werkzeug, gerando páginas HTML 404. | Tratamento de `NotFound` e `FileNotFoundError`, além de manipuladores globais (`@app.errorhandler`) retornando JSON padronizado para 400, 404, 405, 413 e 500. |
| **Tamanho de Arquivo** | `request.content_length` causava `TypeError` quando ausente (`None`), e havia divergência entre código (30KB) e logs (15KB). | Limite configurável centralmente via `MAX_CONTENT_LENGTH_MB`, validação do cabeçalho e validação do tamanho real gravado em disco. |
| **Sanitização** | Se `secure_filename` retornasse string vazia (ex: `...`), ocorria exceção de diretório no `save()`. | Validação pós-sanitização impedindo caminhos nulos ou vazios e verificação contra Path Traversal via `os.path.abspath`. |
| **Logging** | Log único em arquivo estático sem rotação (`uploads.log`), com risco de esgotar o disco. | Dual logging: saída para `stdout` (padrão Docker/K8s/CloudWatch) e `RotatingFileHandler` com tamanho máximo de 10MB e 5 backups. |
| **Configuração** | Valores hardcoded (`uploads`, `database.db`) espalhados por controllers e rotas. | Centralização em `config.py` com suporte ao `.env` através do `python-dotenv`. |
| **Confiabilidade SQLite** | Conexão sem timeout podia gerar travamentos `database is locked` sob concorrência. | Adicionado `timeout=15.0` no `sqlite3.connect` e verificação de integridade da pasta de dados. |
| **Health Check** | Ausência de endpoint para liveness e readiness probes. | Criado endpoint `/health` que valida conectividade do banco e permissão de escrita em disco. |
| **Conteinerização** | Não havia suporte a Docker. | Adicionado `Dockerfile` multi-etapa/slim com usuário não-root (`appuser`), healthcheck e `docker-compose.yml`. |

---

## 📁 Estrutura do Projeto

```text
upload+download/
├── controllers/
│   ├── download_controller.py  # Regras de negócio de download e consulta de metadados
│   └── upload_controller.py    # Validações, upload, persistência e auditoria
├── database/
│   └── db.py                   # Gerenciamento de conexão SQLite e inicialização
├── models/
│   ├── download_model.py       # Consultas de arquivos para download
│   └── upload_model.py         # Inserção, listagem e exclusão de registros
├── routes/
│   ├── download_route.py       # Endpoints GET para arquivos e metadados
│   └── upload_route.py         # Endpoints POST e GET para uploads e listagem
├── tests/
│   ├── __init__.py
│   └── test_api.py             # Suíte de testes automatizados de integração
├── uploads/
│   └── .gitkeep                # Pasta padrão para armazenamento dos arquivos
├── .dockerignore               # Arquivos ignorados no build da imagem Docker
├── .env.example                # Modelo com todas as variáveis de ambiente
├── .env                        # Variáveis locais de desenvolvimento
├── .gitignore                  # Arquivos ignorados pelo controle de versão Git
├── app.py                      # Application Factory e inicialização do Flask
├── config.py                   # Configurações por ambiente (Dev, Prod, Test)
├── docker-compose.yml          # Orquestração de containers com volumes persistentes
├── Dockerfile                  # Imagem Docker otimizada para produção
├── requirements.txt            # Dependências com versões fixadas
├── wsgi.py                     # Entrypoint para servidores WSGI (Gunicorn / Waitress)
└── README.md                   # Documentação completa do projeto
```

---

## ⚙️ Variáveis de Ambiente

Crie ou edite o arquivo `.env` na raiz do projeto com base no arquivo `.env.example`:

| Variável | Padrão | Descrição |
|---|---|---|
| `FLASK_ENV` | `production` | Ambiente de execução: `production`, `development` ou `testing`. |
| `SECRET_KEY` | *(requerido)* | Chave criptográfica da aplicação. **Obrigatório alterar em produção**. |
| `HOST` | `0.0.0.0` | IP de escuta do servidor. |
| `PORT` | `5000` | Porta TCP do servidor. |
| `UPLOAD_FOLDER` | `uploads` | Diretório no disco onde os arquivos físicos serão salvos. |
| `DATABASE_PATH` | `database.db` | Caminho do arquivo de banco de dados SQLite. |
| `MAX_CONTENT_LENGTH_MB` | `16` | Limite máximo por arquivo em Megabytes. |
| `ALLOWED_EXTENSIONS` | `png,jpg,jpeg,gif,pdf,txt` | Extensões permitidas separadas por vírgula. |
| `LOG_LEVEL` | `INFO` | Nível mínimo de log: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `LOG_TO_STDOUT` | `true` | Ativa envio de logs para stdout (ideal para containers). |
| `LOG_FILE` | `app.log` | Arquivo para registro dos logs rotativos. |

> [!TIP]
> Para gerar uma chave forte para a `SECRET_KEY` em produção, execute:
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

---

## 🚀 Instalação e Execução

### Opção 1: Produção com Docker e Docker Compose (Recomendado)

A forma mais simples e segura de rodar em produção. Os arquivos e banco de dados são persistidos em volumes do Docker:

1. **Subir os containers em background:**
   ```bash
   docker compose up -d --build
   ```

2. **Verificar os logs em tempo real:**
   ```bash
   docker compose logs -f
   ```

3. **Verificar o status e integridade do container:**
   ```bash
   docker compose ps
   ```

4. **Parar a aplicação:**
   ```bash
   docker compose down
   ```

---

### Opção 2: Produção em Linux com Gunicorn

Em servidores Linux dedicados (Ubuntu, Debian, CentOS, etc.):

1. **Crie e ative o ambiente virtual:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Instale as dependências:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Inicie o Gunicorn com workers e threads:**
   ```bash
   gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 60 wsgi:app
   ```

> [!NOTE]
> Recomenda-se configurar um serviço do `systemd` para inicialização automática e um proxy reverso com **Nginx** à frente do Gunicorn para terminação SSL/TLS e buffer de arquivos estáticos.

---

### Opção 3: Produção em Windows com Waitress

Em servidores Windows Server ou estações de trabalho:

1. **Crie e ative o ambiente virtual no PowerShell:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. **Instale as dependências:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Inicie a aplicação utilizando o Waitress (WSGI multi-threaded de produção para Windows):**
   ```powershell
   waitress-serve --host=0.0.0.0 --port=5000 wsgi:app
   ```

---

### Opção 4: Desenvolvimento Local

Para desenvolvimento e depuração:

1. Configure `FLASK_ENV=development` no arquivo `.env`.
2. Execute diretamente:
   ```bash
   python app.py
   ```

---

## 📡 Documentação dos Endpoints

A URL base padrão da API é `http://localhost:5000`.

### Resumo dos Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Informações da API e mapa de rotas. |
| `GET` | `/health` | Health Check (conectividade do banco e permissões de escrita). |
| `POST` | `/uploads` ou `/uploads/upload` | Envio de novo arquivo (multipart/form-data). |
| `GET` | `/uploads` ou `/uploads/list` | Listagem de todos os arquivos cadastrados. |
| `GET` | `/downloads/<filename>` | Download do arquivo binário como anexo. |
| `GET` | `/downloads/info/<filename>` | Metadados e status de disponibilidade do arquivo. |

---

### 1. Healthcheck

Verifica a saúde operacional da aplicação, banco de dados e armazenamento.

- **Método:** `GET`
- **Rota:** `/health`
- **Exemplo com cURL:**
  ```bash
  curl -X GET http://localhost:5000/health
  ```
- **Resposta Sucesso (`200 OK`):**
  ```json
  {
    "status": "healthy",
    "database": "connected",
    "storage_writable": true
  }
  ```
- **Resposta Falha (`503 Service Unavailable`):**
  ```json
  {
    "status": "unhealthy",
    "database": "disconnected",
    "storage_writable": false
  }
  ```

---

### 2. Upload de Arquivo

Envia um novo arquivo para armazenamento e registro no banco de dados.

- **Método:** `POST`
- **Rotas:** `/uploads` ou `/uploads/upload`
- **Content-Type:** `multipart/form-data`
- **Campo obrigatório:** `file` (arquivo binário)
- **Exemplo com cURL:**
  ```bash
  curl -X POST http://localhost:5000/uploads/upload \
    -F "file=@/caminho/do/seu/documento.pdf"
  ```
- **Resposta Sucesso (`201 Created`):**
  ```json
  {
    "mensagem": "Arquivo salvo com sucesso!",
    "arquivo": {
      "id": 1,
      "nome": "documento.pdf",
      "tamanho_bytes": 1048576,
      "tamanho_formatado": "1.0 MB",
      "url_download": "/downloads/documento.pdf"
    }
  }
  ```
- **Respostas de Erro:**
  - `400 Bad Request` (Nenhum arquivo ou extensão não permitida):
    ```json
    {
      "erro": "Tipo de arquivo não permitido!",
      "tipos_permitidos": ["gif", "jpeg", "jpg", "pdf", "png", "txt"]
    }
    ```
  - `409 Conflict` (Arquivo com mesmo nome já existente):
    ```json
    {
      "erro": "Já existe um arquivo salvo com o nome 'documento.pdf'. Por favor, renomeie o arquivo antes de enviar."
    }
    ```
  - `413 Payload Too Large` (Arquivo excede o limite configurado):
    ```json
    {
      "erro": "Arquivo excede o tamanho máximo permitido (16.0 MB)"
    }
    ```

---

### 3. Listar Arquivos

Retorna a lista completa de arquivos armazenados e persistidos no banco de dados.

- **Método:** `GET`
- **Rotas:** `/uploads` ou `/uploads/list`
- **Exemplo com cURL:**
  ```bash
  curl -X GET http://localhost:5000/uploads
  ```
- **Resposta Sucesso (`200 OK`):**
  ```json
  {
    "total": 2,
    "arquivos": [
      {
        "id": 2,
        "filename": "imagem.png",
        "filepath": "uploads/imagem.png",
        "filesize": 45056,
        "tamanho_formatado": "44.0 KB",
        "uploaded_at": "2026-11-16 10:45:00",
        "url_download": "/downloads/imagem.png"
      },
      {
        "id": 1,
        "filename": "documento.pdf",
        "filepath": "uploads/documento.pdf",
        "filesize": 1048576,
        "tamanho_formatado": "1.0 MB",
        "uploaded_at": "2026-11-16 10:40:00",
        "url_download": "/downloads/documento.pdf"
      }
    ]
  }
  ```

---

### 4. Download de Arquivo

Baixa o arquivo binário diretamente como anexo (`Content-Disposition: attachment`).

- **Método:** `GET`
- **Rotas:** `/downloads/<filename>` ou `/downloads/download/<filename>`
- **Exemplo com cURL:**
  ```bash
  curl -O -J http://localhost:5000/downloads/documento.pdf
  ```
- **Resposta Sucesso (`200 OK`):**
  Stream binário do arquivo com headers apropriados para download imediato.
- **Resposta Arquivo Não Encontrado (`404 Not Found`):**
  ```json
  {
    "erro": "Arquivo não encontrado"
  }
  ```

---

### 5. Consultar Metadados de um Arquivo

Retorna informações detalhadas do arquivo sem realizar o download binário.

- **Método:** `GET`
- **Rota:** `/downloads/info/<filename>`
- **Exemplo com cURL:**
  ```bash
  curl -X GET http://localhost:5000/downloads/info/documento.pdf
  ```
- **Resposta Sucesso (`200 OK`):**
  ```json
  {
    "arquivo": {
      "id": 1,
      "nome": "documento.pdf",
      "tamanho_bytes": 1048576,
      "tamanho_formatado": "1.0 MB",
      "data_upload": "2026-11-16 10:40:00",
      "disponivel_em_disco": true,
      "url_download": "/downloads/documento.pdf"
    }
  }
  ```

---

## 🧪 Testes Automatizados

O projeto acompanha uma suíte de testes de integração automatizados em `tests/test_api.py`.

Para executar os testes:

```bash
# Executando com unittest padrão do Python:
python -m unittest discover tests

# Ou utilizando pytest:
pytest tests/ -v
```

Cenários cobertos pelos testes:
- Inicialização correta e endpoint de status.
- Health Check operacional.
- Upload de arquivos válidos e validação no banco de dados SQLite.
- Rejeição de extensões proibidas (.exe, etc.).
- Rejeição e código `409 Conflict` para uploads de nomes duplicados.
- Tratamento de erro 400 para requisições vazias ou sem o campo `file`.
- Download bem-sucedido de arquivos gravados.
- Retorno de JSON 404 para arquivos não localizados.
- Listagem e paginação dos arquivos disponíveis.

---

## 🔒 Segurança e Boas Práticas

1. **Proteção contra Path Traversal:**
   Todos os parâmetros de arquivo são sanitizados com `werkzeug.utils.secure_filename` e o caminho resultante é validado com `os.path.abspath` para garantir que permaneça estritamente contido no diretório `UPLOAD_FOLDER`.
2. **Execução Segura em Containers (Non-Root User):**
   O `Dockerfile` executa a aplicação sob o usuário sem privilégios `appuser`, mitigando riscos de escalonamento de privilégios no host.
3. **Cabeçalhos HTTP de Segurança:**
   A API injeta automaticamente em todas as respostas:
   - `X-Content-Type-Options: nosniff` (impede MIME-sniffing)
   - `X-Frame-Options: DENY` (previne ataques de Clickjacking)
   - `X-XSS-Protection: 1; mode=block`
   - `Referrer-Policy: strict-origin-when-cross-origin`
4. **Respostas Estritamente em JSON:**
   Erros 400, 404, 405, 413 e 500 são capturados e devolvidos em formato JSON estruturado, impedindo vazamento de stack traces e informações internas do servidor.
5. **Prevenção de Ataques de Negação de Serviço (DoS):**
   O tamanho máximo do arquivo é validado em duas etapas: no cabeçalho HTTP `Content-Length` e no tamanho real dos bytes gravados em disco.

