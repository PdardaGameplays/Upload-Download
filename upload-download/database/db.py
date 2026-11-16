import os
import sqlite3
import logging

logger = logging.getLogger(__name__)


def resolve_db_path(db_path=None):
    """Obtém o caminho do banco de dados a partir da configuração da aplicação ou do ambiente."""
    if db_path:
        return db_path
    
    # Tenta obter a partir do contexto do Flask
    try:
        from flask import current_app
        if current_app and 'DATABASE_PATH' in current_app.config:
            return current_app.config['DATABASE_PATH']
    except Exception:
        pass

    # Tenta obter a partir da variável de ambiente ou configuração padrão
    try:
        from config import Config
        return Config.DATABASE_PATH
    except ImportError:
        return os.getenv('DATABASE_PATH', 'database.db')


def get_db_connection(db_path=None):
    """
    Cria e retorna uma conexão com o banco de dados SQLite.
    Configurado com timeout para evitar travamentos sob concorrência em produção.
    """
    path = resolve_db_path(db_path)
    
    # Garante que a pasta pai exista se não for em memória
    if path != ':memory:':
        parent_dir = os.path.dirname(os.path.abspath(path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
            
    conn = sqlite3.connect(path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=None):
    """Inicializa as tabelas do banco de dados caso não existam."""
    conn = get_db_connection(db_path)
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                filepath TEXT NOT NULL,
                filesize INTEGER DEFAULT 0,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Garante retrocompatibilidade se a tabela já existia sem as novas colunas
        cursor = conn.execute("PRAGMA table_info(uploads)")
        columns = [col['name'] for col in cursor.fetchall()]
        if 'filesize' not in columns:
            conn.execute('ALTER TABLE uploads ADD COLUMN filesize INTEGER DEFAULT 0')
        if 'uploaded_at' not in columns:
            conn.execute('ALTER TABLE uploads ADD COLUMN uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            
        conn.commit()
    except Exception as e:
        logger.error(f"Erro ao inicializar o banco de dados: {e}")
        raise
    finally:
        conn.close()


def check_db_connection(db_path=None):
    """Testa a conectividade com o banco de dados para health checks."""
    try:
        conn = get_db_connection(db_path)
        cursor = conn.execute('SELECT 1')
        result = cursor.fetchone()
        conn.close()
        return result is not None and result[0] == 1
    except Exception as e:
        logger.error(f"Falha no healthcheck do banco de dados: {e}")
        return False

