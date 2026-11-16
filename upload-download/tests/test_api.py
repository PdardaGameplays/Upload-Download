import os
import io
import shutil
import tempfile
import unittest

# Importa a fábrica da aplicação e banco
from app import create_app
from database.db import init_db, get_db_connection


class ApiTestCase(unittest.TestCase):
    """Testes de integração para os endpoints da API."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.upload_dir = os.path.join(self.test_dir, 'uploads')
        os.makedirs(self.upload_dir, exist_ok=True)
        self.db_path = os.path.join(self.test_dir, 'test.db')

        # Cria a aplicação configurada para testes
        self.app = create_app('testing')
        self.app.config.update({
            'TESTING': True,
            'UPLOAD_FOLDER': self.upload_dir,
            'DATABASE_PATH': self.db_path,
            'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'pdf', 'txt'},
            'MAX_CONTENT_LENGTH': 1024 * 1024  # 1 MB para testes
        })
        
        with self.app.app_context():
            init_db(self.db_path)

        self.client = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_root_endpoint(self):
        """Verifica se o endpoint raiz responde com status 200 e informações do serviço."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("servico", data)
        self.assertEqual(data["status"], "online")

    def test_healthcheck_endpoint(self):
        """Verifica se o healthcheck retorna status healthy e conectividade."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")
        self.assertTrue(data["storage_writable"])

    def test_upload_success(self):
        """Testa o envio com sucesso de um arquivo válido (.txt)."""
        data = {
            'file': (io.BytesIO(b"Conteudo de teste do arquivo"), 'teste_upload.txt')
        }
        response = self.client.post('/uploads/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 201)
        res_data = response.get_json()
        self.assertIn("mensagem", res_data)
        self.assertEqual(res_data["arquivo"]["nome"], "teste_upload.txt")
        self.assertTrue(os.path.exists(os.path.join(self.upload_dir, 'teste_upload.txt')))

        # Valida se foi salvo no banco de dados SQLite
        conn = get_db_connection(self.db_path)
        row = conn.execute('SELECT * FROM uploads WHERE filename = ?', ('teste_upload.txt',)).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row['filename'], 'teste_upload.txt')

    def test_upload_duplicate_file(self):
        """Testa a rejeição (409 Conflict) ao tentar enviar arquivo com mesmo nome."""
        data1 = {'file': (io.BytesIO(b"Primeiro envio"), 'duplicado.txt')}
        res1 = self.client.post('/uploads/upload', data=data1, content_type='multipart/form-data')
        self.assertEqual(res1.status_code, 201)

        data2 = {'file': (io.BytesIO(b"Segundo envio"), 'duplicado.txt')}
        res2 = self.client.post('/uploads/upload', data=data2, content_type='multipart/form-data')
        self.assertEqual(res2.status_code, 409)
        self.assertIn("erro", res2.get_json())

    def test_upload_invalid_extension(self):
        """Testa a rejeição de extensões não permitidas (ex: .exe)."""
        data = {'file': (io.BytesIO(b"Arquivo malicioso"), 'perigo.exe')}
        response = self.client.post('/uploads/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)
        self.assertIn("Tipo de arquivo não permitido", response.get_json()["erro"])

    def test_upload_missing_file_field(self):
        """Testa o envio sem o campo 'file'."""
        response = self.client.post('/uploads/upload', data={}, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)
        self.assertIn("erro", response.get_json())

    def test_download_success(self):
        """Testa o download de um arquivo previamente gravado."""
        # Cria arquivo na pasta de upload
        caminho = os.path.join(self.upload_dir, 'download_teste.txt')
        with open(caminho, 'wb') as f:
            f.write(b"Texto para download")

        # Salva registro no banco
        conn = get_db_connection(self.db_path)
        conn.execute('INSERT INTO uploads (filename, filepath, filesize) VALUES (?, ?, ?)',
                     ('download_teste.txt', caminho, 19))
        conn.commit()
        conn.close()

        response = self.client.get('/downloads/download_teste.txt')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"Texto para download")

    def test_download_not_found(self):
        """Testa o comportamento de erro 404 em JSON quando o arquivo não existe."""
        response = self.client.get('/downloads/arquivo_inexistente.txt')
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIn("erro", data)

    def test_list_files(self):
        """Testa o endpoint de listagem de arquivos."""
        data = {'file': (io.BytesIO(b"Arquivo 1"), 'item1.txt')}
        self.client.post('/uploads/upload', data=data, content_type='multipart/form-data')

        response = self.client.get('/uploads')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["arquivos"][0]["filename"], "item1.txt")


if __name__ == '__main__':
    unittest.main()

