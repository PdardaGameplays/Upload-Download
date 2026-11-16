from flask import Blueprint
from controllers.upload_controller import UploadController

upload_bp = Blueprint('upload_bp', __name__)


@upload_bp.route('', methods=['POST'])
@upload_bp.route('/', methods=['POST'])
@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """Rota para envio de novos arquivos."""
    return UploadController.upload_file()


@upload_bp.route('', methods=['GET'])
@upload_bp.route('/', methods=['GET'])
@upload_bp.route('/list', methods=['GET'])
def list_files():
    """Rota para listar todos os arquivos cadastrados."""
    return UploadController.list_files()

