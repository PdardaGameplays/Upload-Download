from database.db import get_db_connection


class DownloadModel:
    """Modelo para consulta de arquivos para download."""

    @staticmethod
    def find_by_filename(filename):
        """Busca um arquivo pelo nome no banco de dados."""
        conn = get_db_connection()
        try:
            row = conn.execute(
                'SELECT id, filename, filepath, filesize, uploaded_at FROM uploads WHERE filename = ?',
                (filename,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

