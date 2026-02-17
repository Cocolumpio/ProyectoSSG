"""
Configuración compartida y dependencias para DrON Topografía
"""
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timezone, timedelta
from typing import Optional
import os
import logging

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 días

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Database connection - will be set by main server
db = None
client = None

def init_database():
    """Inicializa la conexión a la base de datos"""
    global db, client
    MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME = os.environ.get('DB_NAME', 'dron_topografia')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    logger.info(f"Connected to MongoDB database: {DB_NAME}")
    return db, client

def get_db():
    """Retorna la referencia a la base de datos"""
    return db

# Auth helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Obtiene el usuario actual desde el token JWT"""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user is None:
        raise credentials_exception
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Usuario desactivado")
    return user

async def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Verifica que el usuario actual sea administrador"""
    if current_user.get("rol") != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Se requieren permisos de administrador"
        )
    return current_user
