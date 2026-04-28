import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    # --- Configurações de Autenticação ---
    # Pegamos do .env para segurança
    API_EMAIL = os.getenv("API_EMAIL")
    API_PASS = os.getenv("API_PASS")
    
    # Endpoints
    BASE_URL = os.getenv("BASE_URL")

    if not BASE_URL:
        raise ValueError("ERROR CRÍTICO: BASE_URL não encontrada no ambiente")
    
    LOGIN_URL = f"{BASE_URL}/api/conta/login"
    VENDAS_URL = f"{BASE_URL}/api/import/vendas"

    # --- IDs e Campos Fixos ---
    DISTRIBUIDOR_ID = os.getenv("DISTRIBUIDOR_ID")
    REPRESENTANTE_ID = os.getenv("REPRESENTANTE_ID")
    FIELD_ARQUIVO = "arquivo"
    FIELD_DISTRIBUIDOR = "distribuidorId"
    FIELD_REPRESENTANTE = "representanteId"

    # --- Caminhos ---
    IMPORTS_DIR = BASE_DIR / "imports"
    OUTPUT_DIR = BASE_DIR / "output"
    NETWORK_TIMEOUT = 60

    # Extraímos do .env conforme o seu arquivo configurado anteriormente
    FTP_HOST = os.getenv("FTP_HOST")
    FTP_PORT = int(os.getenv("FTP_PORT", 21))
    FTP_USER = os.getenv("FTP_USER")
    FTP_PASS = os.getenv("FTP_PASS")

    # --- Configurações de Armazenamento ---
    # Limite de arquivos para manter nas pastas (conforme sua solicitação)
    MAX_FILES_RETAINED = 3

    @classmethod
    def create_dirs(cls):
        cls.IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

Settings.create_dirs()