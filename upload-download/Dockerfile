# Imagem base oficial do Python slim (leve e segura)
FROM python:3.11-slim

# Evita geração de arquivos .pyc e força saída direta para stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

# Instala curl para healthchecks e limpa o cache do apt
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root por motivos de segurança (Princípio do menor privilégio)
RUN useradd --create-home --shell /bin/bash appuser

# Diretório de trabalho
WORKDIR /app

# Instalação das dependências (aproveitando o cache de camadas do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia os arquivos da aplicação
COPY . .

# Cria os diretórios necessários e ajusta permissões para o usuário appuser
RUN mkdir -p /app/uploads /app/data && \
    chown -R appuser:appuser /app

# Configura variáveis de ambiente padrão para os volumes em produção
ENV UPLOAD_FOLDER=/app/uploads \
    DATABASE_PATH=/app/data/database.db

# Define usuário não-root
USER appuser

# Exposição da porta da aplicação
EXPOSE 5000

# Healthcheck nativo do container para verificar a integridade da API
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Comando de inicialização com servidor WSGI Gunicorn (4 workers, 2 threads por worker)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "wsgi:app"]

