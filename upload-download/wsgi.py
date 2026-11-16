"""
Ponto de entrada (Entrypoint) para servidores WSGI em ambiente de produção (Gunicorn, Waitress, uWSGI).
"""
import os
from app import create_app

# Obtém o ambiente a partir de FLASK_ENV (padrão: production)
env = os.getenv('FLASK_ENV', os.getenv('ENVIRONMENT', 'production'))
app = create_app(env)

if __name__ == '__main__':
    # Caso executado diretamente com python wsgi.py
    host = app.config.get('HOST', '0.0.0.0')
    port = app.config.get('PORT', 5000)
    app.run(host=host, port=port)

