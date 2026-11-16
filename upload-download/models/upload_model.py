import sqlite3
import logging
from database.db import get_db_connection

logger = logging.getLogger(__name__)


class UploadModel:
    """Modelo de dados para persistência e recuperação de arquivos enviados."""

    @staticmethod
    def save_file(filename, filepath, filesize=0):
        """
        Salva o registro de um arquivo enviado no banco de dados.
        Retorna o dicionário com os dados salvos ou None em caso de duplicidade/erro.
        """
        conn = get_db_connection()
        try:
            cursor = conn.execute('''
                INSERT INTO uploads (filename, filepath, filesize)
                VALUES (?, ?, ?)
            ''', (filename, filepath, filesize))
            conn.commit()
            last_id = cursor.lastrowid
            return {
                "id": last_id,
                "filename": filename,
                "filepath": filepath,
                "filesize": filesize
            }
        except sqlite3.IntegrityError as e:
            logger.warning(f"Tentativa de salvar arquivo duplicado: {filename} - {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo no banco: {filename} - {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def find_by_filename(filename):
        """Busca um arquivo pelo nome exato no banco de dados."""
        conn = get_db_connection()
        try:
            row = conn.execute(
                'SELECT id, filename, filepath, filesize, uploaded_at FROM uploads WHERE filename = ?',
                (filename,)
            ).fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    @staticmethod
    def list_all():
        """Retorna a lista de todos os arquivos cadastrados no banco."""
        conn = get_db_connection()
        try:
            rows = conn.execute(
                'SELECT id, filename, filepath, filesize, uploaded_at FROM uploads ORDER BY id DESC'
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def delete_by_filename(filename):
        """Remove o registro do arquivo do banco de dados."""
        conn = get_db_connection()
        try:
            cursor = conn.execute('DELETE FROM uploads WHERE filename = ?', (filename,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

