import os
from pathlib import Path

# Tenta carregar variáveis do arquivo .env caso a biblioteca python-dotenv esteja instalada
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configurações base da aplicação."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-insecure-secret-key-change-in-production')
    
    # Diretório para armazenamento dos arquivos
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'uploads'))
    
    # Caminho do banco de dados SQLite
    DATABASE_PATH = os.getenv('DATABASE_PATH', os.path.join(BASE_DIR, 'database.db'))
    
    # Tamanho máximo do arquivo para upload (padrão 16 MB em bytes)
    MAX_CONTENT_LENGTH_MB = int(os.getenv('MAX_CONTENT_LENGTH_MB', '16'))
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(MAX_CONTENT_LENGTH_MB * 1024 * 1024)))
    
    # Extensões de arquivos permitidas (separadas por vírgula no .env)
    _extensions = os.getenv('ALLOWED_EXTENSIONS', 'png,jpg,jpeg,gif,pdf,txt')
    ALLOWED_EXTENSIONS = {ext.strip().lower().lstrip('.') for ext in _extensions.split(',') if ext.strip()}
    
    # Rede e Servidor
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', '5000'))
    
    # Configurações de Log
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    LOG_FILE = os.getenv('LOG_FILE', os.path.join(BASE_DIR, 'app.log'))
    LOG_TO_STDOUT = os.getenv('LOG_TO_STDOUT', 'true').lower() in ('true', '1', 'yes')
    
    # Segurança
    DEBUG = False
    TESTING = False

    @classmethod
    def init_app(cls, app):
        """Inicializa e garante que os diretórios necessários existam."""
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        db_dir = os.path.dirname(os.path.abspath(cls.DATABASE_PATH))
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)


class DevelopmentConfig(Config):
    """Configurações específicas para ambiente de Desenvolvimento."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Configurações específicas para ambiente de Produção."""
    DEBUG = False
    TESTING = False
    # Em produção, o SECRET_KEY deve vir obrigatoriamente do ambiente
    SECRET_KEY = os.getenv('SECRET_KEY', 'prod-secret-must-be-configured')


class TestingConfig(Config):
    """Configurações específicas para execução de Testes."""
    TESTING = True
    DEBUG = True
    DATABASE_PATH = ':memory:'
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'test_uploads')


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': ProductionConfig
}


def get_config(env_name=None):
    """Retorna a classe de configuração correspondente ao ambiente informado."""
    if not env_name:
        env_name = os.getenv('FLASK_ENV', os.getenv('ENVIRONMENT', 'production')).lower()
    return config_by_name.get(env_name, ProductionConfig)

