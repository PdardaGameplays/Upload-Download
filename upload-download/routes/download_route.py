from flask import Blueprint
from controllers.download_controller import DownloadController

download_bp = Blueprint('download_bp', __name__)


@download_bp.route('/<filename>', methods=['GET'])
@download_bp.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """Rota para baixar um arquivo pelo nome."""
    return DownloadController.download_file(filename)


@download_bp.route('/info/<filename>', methods=['GET'])
def file_info(filename):
    """Rota para consultar informações e metadados de um arquivo."""
    return DownloadController.get_file_info(filename)

