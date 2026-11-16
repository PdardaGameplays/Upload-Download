import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify
from config import get_config
from database.db import init_db, check_db_connection
from routes.upload_route import upload_bp
from routes.download_route import download_bp


def configure_logging(app):
    """Configura logs estruturados para stdout e arquivo rotativo."""
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'), logging.INFO)
    log_format = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s]: %(message)s')
    
    handlers = []

    # Stream handler (Stdout) - Essencial para Docker, Kubernetes e 12-factor apps
    if app.config.get('LOG_TO_STDOUT', True):
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(log_format)
        stdout_handler.setLevel(log_level)
        handlers.append(stdout_handler)

    # Rotating File Handler - Evita que os logs consumam todo o espaço em disco
    log_file = app.config.get('LOG_FILE')
    if log_file:
        try:
            log_dir = os.path.dirname(os.path.abspath(log_file))
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8')
            file_handler.setFormatter(log_format)
            file_handler.setLevel(log_level)
            handlers.append(file_handler)
        except Exception as e:
            app.logger.warning(f"Não foi possível criar o arquivo de log '{log_file}': {e}")

    # Configuração centralizada
    logging.basicConfig(level=log_level, handlers=handlers, force=True)
    app.logger.handlers = handlers
    app.logger.setLevel(log_level)


def register_error_handlers(app):
    """Garante que todos os erros da API retornem JSON em vez de páginas HTML padrão."""
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "erro": "Requisição inválida (Bad Request)",
            "detalhes": str(error.description) if hasattr(error, 'description') else "Parâmetros incorretos",
            "status": 400
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "erro": "Recurso não encontrado",
            "status": 404
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            "erro": "Método HTTP não permitido para esta rota",
            "status": 405
        }), 405

    @app.errorhandler(413)
    def payload_too_large(error):
        max_bytes = app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
        max_mb = max_bytes / (1024 * 1024)
        return jsonify({
            "erro": f"Arquivo excede o tamanho máximo permitido de {max_mb:.1f} MB",
            "status": 413
        }), 413

    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f"Erro interno 500: {error}")
        return jsonify({
            "erro": "Erro interno no servidor. Consulte os logs para mais detalhes.",
            "status": 500
        }), 500


def register_security_headers(app):
    """Aplica cabeçalhos HTTP de segurança recomendados para produção."""
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response


def create_app(config_name=None):
    """Fábrica de aplicação (Application Factory Pattern) para isolamento e testes."""
    app = Flask(__name__)
    
    # 1. Carrega as configurações
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    config_class.init_app(app)
    
    # 2. Configura logs estruturados
    configure_logging(app)
    
    # 3. Inicializa banco de dados
    with app.app_context():
        init_db(app.config.get('DATABASE_PATH'))
    
    # 4. Registra Blueprints das Rotas
    app.register_blueprint(upload_bp, url_prefix='/uploads')
    app.register_blueprint(download_bp, url_prefix='/downloads')
    
    # 5. Registra Tratamento de Erros e Cabeçalhos de Segurança
    register_error_handlers(app)
    register_security_headers(app)

    # 6. Rotas Raiz e Healthcheck para Produção
    @app.route('/', methods=['GET'])
    def index():
        return jsonify({
            "servico": "API de Upload e Download de Arquivos",
            "versao": "2.0.0",
            "status": "online",
            "ambiente": app.config.get('ENV', 'production'),
            "rotas_disponiveis": {
                "upload": "POST /uploads/upload ou POST /uploads",
                "listar_arquivos": "GET /uploads ou GET /uploads/list",
                "download": "GET /downloads/<filename> ou GET /downloads/download/<filename>",
                "info_arquivo": "GET /downloads/info/<filename>",
                "healthcheck": "GET /health"
            }
        }), 200

    @app.route('/health', methods=['GET'])
    def health_check():
        db_ok = check_db_connection(app.config.get('DATABASE_PATH'))
        upload_folder_writable = os.access(app.config.get('UPLOAD_FOLDER'), os.W_OK)
        
        is_healthy = db_ok and upload_folder_writable
        status_code = 200 if is_healthy else 503
        
        return jsonify({
            "status": "healthy" if is_healthy else "unhealthy",
            "database": "connected" if db_ok else "disconnected",
            "storage_writable": upload_folder_writable
        }), status_code

    return app


# Instância padrão para WSGI servers (Gunicorn, Waitress, uWSGI)
app = create_app()

if __name__ == '__main__':
    host = app.config.get('HOST', '0.0.0.0')
    port = app.config.get('PORT', 5000)
    debug = app.config.get('DEBUG', False)
    app.logger.info(f"Iniciando API no endereço http://{host}:{port} (Debug: {debug})")
    app.run(host=host, port=port, debug=debug)

