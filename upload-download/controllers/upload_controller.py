import os
import logging
from flask import jsonify, request, current_app
from werkzeug.utils import secure_filename
from models.upload_model import UploadModel

logger = logging.getLogger(__name__)


def format_size(bytes_size):
    """Auxiliar para formatar tamanho em KB ou MB legíveis."""
    if bytes_size >= 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    return f"{bytes_size / 1024:.1f} KB"


class UploadController:
    """Controlador responsável por processar o envio e validação de arquivos."""

    @staticmethod
    def get_allowed_extensions():
        """Obtém as extensões permitidas da configuração ativa."""
        return current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt'})

    @staticmethod
    def get_upload_folder():
        """Obtém o diretório configurado para uploads."""
        folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(folder, exist_ok=True)
        return folder

    @staticmethod
    def get_max_size():
        """Obtém o tamanho máximo permitido para arquivos em bytes."""
        return current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)

    @classmethod
    def arquivo_permitido(cls, nome_arquivo):
        """Verifica se a extensão do arquivo é permitida."""
        if '.' not in nome_arquivo:
            return False
        ext = nome_arquivo.rsplit('.', 1)[1].lower()
        return ext in cls.get_allowed_extensions()

    @classmethod
    def upload_file(cls):
        """Recebe, valida e processa o upload de um arquivo."""
        # 1. Verifica se o campo 'file' está presente no formulário multipart
        if 'file' not in request.files:
            logger.warning(f"Falha no upload: campo 'file' ausente no payload | IP: {request.remote_addr}")
            return jsonify({"erro": "Nenhum arquivo enviado. Utilize o campo 'file' no formulário multipart/form-data."}), 400

        arquivo = request.files['file']

        # 2. Verifica se o nome do arquivo está vazio
        if not arquivo or arquivo.filename == '':
            logger.warning(f"Falha no upload: Nome do arquivo vazio | IP: {request.remote_addr}")
            return jsonify({"erro": "Nome do arquivo vazio"}), 400

        # 3. Sanitiza o nome do arquivo para mitigar vulnerabilidades de Path Traversal
        nome_arquivo = secure_filename(arquivo.filename)
        if not nome_arquivo:
            logger.warning(f"Falha no upload: Nome de arquivo inválido ({arquivo.filename}) | IP: {request.remote_addr}")
            return jsonify({"erro": "Nome de arquivo inválido após sanitização"}), 400

        # 4. Validação da extensão permitida
        if not cls.arquivo_permitido(nome_arquivo):
            permitidos = sorted(list(cls.get_allowed_extensions()))
            logger.warning(f"Falha no upload: {nome_arquivo} possui tipo não permitido | IP: {request.remote_addr}")
            return jsonify({
                "erro": "Tipo de arquivo não permitido!",
                "tipos_permitidos": permitidos
            }), 400

        # 5. Validação antecipada de tamanho com base no cabeçalho Content-Length
        max_size = cls.get_max_size()
        if request.content_length and request.content_length > max_size:
            limite_formatado = format_size(max_size)
            logger.warning(f"Falha no upload: {nome_arquivo} excede limite ({request.content_length} bytes > {max_size} bytes)")
            return jsonify({
                "erro": f"Arquivo excede o tamanho máximo permitido ({limite_formatado})"
            }), 413

        # 6. Prevenção de sobrescrita e validação de duplicidade
        pasta_upload = cls.get_upload_folder()
        caminho_arquivo = os.path.join(pasta_upload, nome_arquivo)
        
        # Proteção adicional de path traversal
        pasta_upload_abs = os.path.abspath(pasta_upload)
        caminho_arquivo_abs = os.path.abspath(caminho_arquivo)
        if not caminho_arquivo_abs.startswith(pasta_upload_abs):
            logger.error(f"Tentativa de Directory Traversal detectada: {nome_arquivo} | IP: {request.remote_addr}")
            return jsonify({"erro": "Caminho de arquivo inválido"}), 400

        if os.path.exists(caminho_arquivo_abs) or UploadModel.find_by_filename(nome_arquivo):
            logger.warning(f"Falha no upload: arquivo '{nome_arquivo}' já existe")
            return jsonify({
                "erro": f"Já existe um arquivo salvo com o nome '{nome_arquivo}'. Por favor, renomeie o arquivo antes de enviar."
            }), 409

        # 7. Salva o arquivo no disco de forma segura
        try:
            arquivo.save(caminho_arquivo_abs)
            tamanho_real = os.path.getsize(caminho_arquivo_abs)

            # Valida tamanho real em disco (caso o cabeçalho Content-Length não tenha sido enviado)
            if tamanho_real > max_size:
                os.remove(caminho_arquivo_abs)
                limite_formatado = format_size(max_size)
                logger.warning(f"Upload cancelado: tamanho real de {nome_arquivo} ({tamanho_real} bytes) excede {max_size}")
                return jsonify({
                    "erro": f"Arquivo excede o tamanho máximo permitido ({limite_formatado})"
                }), 413

            # 8. Registra metadados no banco de dados SQLite
            registro = UploadModel.save_file(nome_arquivo, caminho_arquivo, tamanho_real)
            if not registro:
                if os.path.exists(caminho_arquivo_abs):
                    os.remove(caminho_arquivo_abs)
                logger.error(f"Falha ao persistir metadados de {nome_arquivo} no banco de dados")
                return jsonify({"erro": "Falha ao registrar arquivo no banco de dados"}), 500

            ip_usuario = request.remote_addr
            logger.info(f"Upload bem-sucedido: {nome_arquivo} ({format_size(tamanho_real)}) | IP: {ip_usuario}")

            return jsonify({
                "mensagem": "Arquivo salvo com sucesso!",
                "arquivo": {
                    "id": registro["id"],
                    "nome": nome_arquivo,
                    "tamanho_bytes": tamanho_real,
                    "tamanho_formatado": format_size(tamanho_real),
                    "url_download": f"/downloads/{nome_arquivo}"
                }
            }), 201

        except Exception as e:
            if os.path.exists(caminho_arquivo_abs):
                os.remove(caminho_arquivo_abs)
            logger.exception(f"Erro inesperado durante upload de {nome_arquivo}: {e}")
            return jsonify({"erro": "Erro interno ao processar o upload do arquivo"}), 500

    @classmethod
    def list_files(cls):
        """Lista todos os arquivos cadastrados e disponíveis para download."""
        try:
            arquivos = UploadModel.list_all()
            for arq in arquivos:
                arq["url_download"] = f"/downloads/{arq['filename']}"
                if arq.get("filesize"):
                    arq["tamanho_formatado"] = format_size(arq["filesize"])
            return jsonify({
                "total": len(arquivos),
                "arquivos": arquivos
            }), 200
        except Exception as e:
            logger.exception(f"Erro ao listar arquivos: {e}")
            return jsonify({"erro": "Erro ao consultar lista de arquivos"}), 500

