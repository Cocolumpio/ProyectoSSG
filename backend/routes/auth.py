"""
Rutas de Autenticación - DrON Topografía
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import List
import uuid

from core.config import (
    get_db, verify_password, get_password_hash, 
    create_access_token, get_current_user, get_current_admin,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from models.schemas import UserCreate, LoginRequest, Token, UserResponse

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", response_model=Token)
async def register(user_data: UserCreate):
    """Registra un nuevo usuario"""
    db = get_db()
    
    # Verificar si el email ya existe
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Crear usuario
    user_dict = user_data.model_dump()
    user_dict["id"] = str(uuid.uuid4())
    user_dict["password"] = get_password_hash(user_data.password)
    user_dict["created_at"] = datetime.now(timezone.utc).isoformat()
    user_dict["is_active"] = True
    
    await db.users.insert_one(user_dict)
    
    # Generar token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_dict["id"], "email": user_dict["email"], "rol": user_dict["rol"]},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_dict["id"],
            "email": user_dict["email"],
            "nombre": user_dict["nombre"],
            "rol": user_dict["rol"],
            "is_active": user_dict["is_active"]
        }
    }


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Inicia sesión y devuelve un token JWT"""
    db = get_db()
    
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    if not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Usuario desactivado")
    
    # Generar token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"], "email": user["email"], "rol": user["rol"]},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "nombre": user["nombre"],
            "rol": user["rol"],
            "is_active": user.get("is_active", True)
        }
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Obtiene los datos del usuario actual"""
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "nombre": current_user["nombre"],
        "rol": current_user["rol"],
        "is_active": current_user.get("is_active", True)
    }


@router.get("/users", response_model=List[UserResponse])
async def list_users(current_user: dict = Depends(get_current_admin)):
    """Lista todos los usuarios (solo admin)"""
    db = get_db()
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(100)
    return users


@router.put("/users/{user_id}/toggle-active")
async def toggle_user_active(user_id: str, current_user: dict = Depends(get_current_admin)):
    """Activa/desactiva un usuario (solo admin)"""
    db = get_db()
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    new_status = not user.get("is_active", True)
    await db.users.update_one({"id": user_id}, {"$set": {"is_active": new_status}})
    
    return {"id": user_id, "is_active": new_status}
