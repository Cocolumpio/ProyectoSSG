"""
Configuración de base de datos y servicios para DrON Topografía
"""
import os
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB Configuration
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME', 'drone_dashboard')

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dron-topografia-secret-key-2025-super-secure')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 días

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Resend Configuration
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'ianalejandrogn@gmail.com')

# Upload directory
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
