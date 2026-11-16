import os
import logging
from flask import jsonify, send_from_directory, current_app, request
from werkzeug.utils import secure_filename
from werkzeug.exceptions import NotFound
from models.download_model import DownloadModel

logger = logging.getLogger(__name__)


def format_size(bytes_size):
    """Auxiliar para formatar tamanho em KB ou MB legíveis."""
    if not bytes_size:
        return "0 KB"
    if bytes_size >= 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    return f"{bytes_size / 1024:.1f} KB"


class DownloadController:
    """Controlador responsável por processar o download e consulta de arquivos."""

    @staticmethod
    def get_upload_folder():
        """Obtém o diretório configurado de uploads."""
        return current_app.config.get('UPLOAD_FOLDER', 'uploads')

    @classmethod
    def download_file(cls, filename):
        """
        Envia o arquivo solicitado para download como anexo.
        Trata adequadamente ausência do arquivo e sanitiza o parâmetro recebido.
        """
        # 1. Sanitização para evitar Directory Traversal
        sanitized_filename = secure_filename(filename)
        if not sanitized_filename:
            logger.warning(f"Download rejeitado: nome de arquivo inseguro ou vazio '{filename}' | IP: {request.remote_addr}")
            return jsonify({"erro": "Nome de arquivo inválido"}), 400

        upload_folder = cls.get_upload_folder()
        caminho_completo = os.path.join(upload_folder, sanitized_filename)

        # 2. Validação rigorosa de Path Traversal
        upload_folder_abs = os.path.abspath(upload_folder)
        caminho_completo_abs = os.path.abspath(caminho_completo)
        if not caminho_completo_abs.startswith(upload_folder_abs):
            logger.error(f"Tentativa de Directory Traversal no download: '{filename}' | IP: {request.remote_addr}")
            return jsonify({"erro": "Acesso não autorizado ao caminho informado"}), 403

        # 3. Verifica se o arquivo existe fisicamente no disco
        if not os.path.isfile(caminho_completo_abs):
            logger.warning(f"Download não encontrado: {sanitized_filename} | IP: {request.remote_addr}")
            return jsonify({"erro": "Arquivo não encontrado"}), 404

        # 4. Transmissão segura do arquivo como attachment
        try:
            logger.info(f"Download realizado com sucesso: {sanitized_filename} | IP: {request.remote_addr}")
            return send_from_directory(upload_folder_abs, sanitized_filename, as_attachment=True)
        except (FileNotFoundError, NotFound):
            logger.warning(f"Arquivo não localizado pelo send_from_directory: {sanitized_filename}")
            return jsonify({"erro": "Arquivo não encontrado"}), 404
        except Exception as e:
            logger.exception(f"Erro inesperado no download do arquivo {sanitized_filename}: {e}")
            return jsonify({"erro": "Erro interno ao processar download do arquivo"}), 500

    @classmethod
    def get_file_info(cls, filename):
        """Retorna os metadados de um arquivo cadastrado."""
        sanitized_filename = secure_filename(filename)
        if not sanitized_filename:
            return jsonify({"erro": "Nome de arquivo inválido"}), 400

        registro = DownloadModel.find_by_filename(sanitized_filename)
        upload_folder = cls.get_upload_folder()
        caminho_fisico = os.path.join(upload_folder, sanitized_filename)
        existe_em_disco = os.path.isfile(caminho_fisico)

        if not registro and not existe_em_disco:
            return jsonify({"erro": "Arquivo não encontrado"}), 404

        tamanho = registro.get("filesize", 0) if registro else (os.path.getsize(caminho_fisico) if existe_em_disco else 0)

        return jsonify({
            "arquivo": {
                "id": registro.get("id") if registro else None,
                "nome": sanitized_filename,
                "tamanho_bytes": tamanho,
                "tamanho_formatado": format_size(tamanho),
                "data_upload": registro.get("uploaded_at") if registro else None,
                "disponivel_em_disco": existe_em_disco,
                "url_download": f"/downloads/{sanitized_filename}"
            }
        }), 200

