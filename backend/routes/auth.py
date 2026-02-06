"""
Rutas de autenticación para DrON Topografía
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List

from models import User, UserCreate, UserLogin, UserResponse, Token
from services import (
    db, verify_password, get_password_hash, create_access_token,
    get_current_user, get_current_admin
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", response_model=Token)
async def register(user_data: UserCreate):
    """Registrar un nuevo usuario"""
    existing_user = await db.usuarios.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    new_user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        nombre=user_data.nombre,
        rol=user_data.rol
    )
    
    user_dict = new_user.model_dump()
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    await db.usuarios.insert_one(user_dict)
    
    access_token = create_access_token(data={"sub": new_user.id})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=new_user.id,
            email=new_user.email,
            nombre=new_user.nombre,
            rol=new_user.rol,
            activo=new_user.activo
        )
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Iniciar sesión"""
    user = await db.usuarios.find_one({"email": credentials.email}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    
    if not verify_password(credentials.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    
    if not user.get("activo", True):
        raise HTTPException(status_code=403, detail="Usuario desactivado")
    
    access_token = create_access_token(data={"sub": user["id"]})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            nombre=user["nombre"],
            rol=user["rol"],
            activo=user.get("activo", True)
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Obtener información del usuario actual"""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        nombre=current_user["nombre"],
        rol=current_user["rol"],
        activo=current_user.get("activo", True)
    )


@router.get("/users", response_model=List[UserResponse])
async def list_users(current_user: dict = Depends(get_current_admin)):
    """Listar todos los usuarios (solo admin)"""
    users = await db.usuarios.find({}, {"_id": 0, "password_hash": 0}).to_list(100)
    return [UserResponse(**u) for u in users]


@router.put("/users/{user_id}/toggle-active")
async def toggle_user_active(user_id: str, current_user: dict = Depends(get_current_admin)):
    """Activar/desactivar un usuario (solo admin)"""
    user = await db.usuarios.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    new_status = not user.get("activo", True)
    await db.usuarios.update_one({"id": user_id}, {"$set": {"activo": new_status}})
    
    return {"message": f"Usuario {'activado' if new_status else 'desactivado'}", "activo": new_status}
