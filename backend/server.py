from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
import shutil
import laspy
import numpy as np
import zipfile
import io
import resend
from passlib.context import CryptContext
from jose import JWTError, jwt

# PDF Generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Resend configuration
resend.api_key = os.environ.get('RESEND_API_KEY')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 días

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create uploads directory
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# ==================== MODELS ====================

# --- Auth Models ---
class UserRole(str):
    ADMIN = "admin"
    CLIENT = "client"

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    password_hash: str
    nombre: str
    rol: str = "client"  # admin o client
    activo: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: str
    password: str
    nombre: str
    rol: str = "client"

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    nombre: str
    rol: str
    activo: bool

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# --- Auth Helper Functions ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Obtener usuario actual desde el token JWT"""
    credentials_exception = HTTPException(
        status_code=401,
        detail="No se pudo validar las credenciales",
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
    
    user = await db.usuarios.find_one({"id": user_id}, {"_id": 0})
    if user is None:
        raise credentials_exception
    if not user.get("activo", True):
        raise HTTPException(status_code=403, detail="Usuario desactivado")
    return user

async def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Verificar que el usuario actual es admin"""
    if current_user.get("rol") != "admin":
        raise HTTPException(status_code=403, detail="Se requieren permisos de administrador")
    return current_user

# --- Project Models ---

class Coordinates(BaseModel):
    lat: float
    lng: float

class Volumetria(BaseModel):
    excavacion: float = 0.0  # m³
    relleno: float = 0.0  # m³
    materiales: float = 0.0  # m³

class AvanceSemanal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    proyecto_id: str
    semana: int  # Número de semana (1, 2, 3, etc.)
    fecha: str  # Fecha del avance
    pix4d_url: Optional[str] = None  # URL del modelo 3D de Pix4D (opcional ahora)
    modelo_3d_url: Optional[str] = None  # URL del modelo 3D local (PLY)
    modelo_3d_tipo: Optional[str] = None  # 'local' o 'pix4d'
    descripcion: Optional[str] = None
    porcentaje_avance: Optional[float] = None  # Porcentaje de avance en esa semana
    volumen_excavacion: Optional[float] = None  # Volumen quitado en m³
    imagenes: List[str] = []  # URLs de las imágenes del vuelo
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AvanceSemanalCreate(BaseModel):
    semana: int
    fecha: str
    pix4d_url: Optional[str] = None  # Ahora opcional
    descripcion: Optional[str] = None
    porcentaje_avance: Optional[float] = None
    volumen_excavacion: Optional[float] = None  # Volumen quitado en m³
    imagenes: List[str] = []  # URLs de las imágenes del vuelo

class AvanceSemanalUpdate(BaseModel):
    """Modelo para actualización parcial de avance semanal"""
    semana: Optional[int] = None
    fecha: Optional[str] = None
    pix4d_url: Optional[str] = None
    modelo_3d_url: Optional[str] = None
    modelo_3d_tipo: Optional[str] = None
    descripcion: Optional[str] = None
    porcentaje_avance: Optional[float] = None
    volumen_excavacion: Optional[float] = None

class Proyecto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str
    ubicacion: str
    direccion: Optional[str] = None  # Dirección completa de la obra
    coordenadas: Coordinates
    fecha_inicio: str
    fecha_fin_planeada: str
    avance_actual: float = 0.0  # Porcentaje 0-100 (calculado automáticamente)
    volumen_total_planeado: float = 0.0  # Volumen total estimado a excavar en m³
    descripcion: Optional[str] = None
    pix4d_url: Optional[str] = None  # URL del modelo 3D
    volumetria: Optional[Volumetria] = None  # Volumetrías del proyecto
    # Configuración de flotilla de camiones
    capacidad_camion: float = 25.0  # m³ por camión (default 25 m³)
    costo_m3: float = 150.0  # Costo por metro cúbico en MXN (default $150)
    clientes_asignados: List[str] = []  # Lista de IDs de clientes asignados
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProyectoCreate(BaseModel):
    nombre: str
    ubicacion: str
    direccion: Optional[str] = None
    coordenadas: Coordinates
    fecha_inicio: str
    fecha_fin_planeada: str
    descripcion: Optional[str] = None
    pix4d_url: Optional[str] = None
    avance_actual: float = 0.0
    volumen_total_planeado: float = 0.0  # Volumen total estimado a excavar en m³
    volumetria: Optional[Volumetria] = None
    # Configuración de flotilla
    capacidad_camion: float = 25.0
    costo_m3: float = 150.0  # Costo por metro cúbico en MXN
    clientes_asignados: List[str] = []  # Lista de IDs de clientes asignados

class ProyectoUpdate(BaseModel):
    nombre: Optional[str] = None
    ubicacion: Optional[str] = None
    direccion: Optional[str] = None
    coordenadas: Optional[Coordinates] = None
    fecha_inicio: Optional[str] = None
    fecha_fin_planeada: Optional[str] = None
    avance_actual: Optional[float] = None
    volumen_total_planeado: Optional[float] = None
    descripcion: Optional[str] = None
    pix4d_url: Optional[str] = None
    volumetria: Optional[Volumetria] = None
    # Configuración de flotilla
    capacidad_camion: Optional[float] = None
    costo_m3: Optional[float] = None
    clientes_asignados: Optional[List[str]] = None  # Lista de IDs de clientes asignados

# Modelo para solicitud de vuelo programado
class SolicitudVuelo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nombre_proyecto: str
    fecha_inicio_proyecto: str
    fecha_fin_proyecto: str
    fecha_vuelo_deseada: str
    hora_preferencia: Optional[str] = None
    notas: Optional[str] = None
    estado: str = "pendiente"  # pendiente, confirmado, completado, cancelado
    cliente_id: Optional[str] = None  # ID del usuario cliente que hizo la solicitud
    cliente_email: Optional[str] = None  # Email del cliente
    cliente_nombre: Optional[str] = None  # Nombre del cliente
    comentario_admin: Optional[str] = None  # Comentario del admin al aprobar/rechazar
    fecha_respuesta: Optional[str] = None  # Fecha cuando el admin respondió
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SolicitudVueloCreate(BaseModel):
    nombre_proyecto: str
    fecha_inicio_proyecto: str
    fecha_fin_proyecto: str
    fecha_vuelo_deseada: str
    hora_preferencia: Optional[str] = None
    notas: Optional[str] = None

class SolicitudVueloUpdate(BaseModel):
    estado: str
    comentario_admin: Optional[str] = None

class Vuelo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    proyecto_id: str
    fecha_vuelo: str
    duracion_minutos: int
    area_cubierta: float  # m²
    num_imagenes: int
    volumetria: Volumetria
    archivo_nube_puntos: Optional[str] = None
    pix4d_url: Optional[str] = None  # URL del iframe de Pix4D
    estado: str = "completado"  # completado, procesando, fallido
    notas: Optional[str] = None
    semana: Optional[int] = None  # Número de semana relacionada
    avance_semanal_id: Optional[str] = None  # ID del avance semanal relacionado
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VueloCreate(BaseModel):
    proyecto_id: str
    fecha_vuelo: str
    duracion_minutos: int
    area_cubierta: float
    num_imagenes: int
    volumetria: Volumetria
    pix4d_url: Optional[str] = None
    notas: Optional[str] = None
    semana: Optional[int] = None  # Número de semana relacionada

class VueloUpdate(BaseModel):
    proyecto_id: Optional[str] = None
    fecha_vuelo: Optional[str] = None
    duracion_minutos: Optional[int] = None
    area_cubierta: Optional[float] = None
    num_imagenes: Optional[int] = None
    volumetria: Optional[Volumetria] = None
    pix4d_url: Optional[str] = None
    notas: Optional[str] = None
    estado: Optional[str] = None
    semana: Optional[int] = None  # Número de semana relacionada

class AvanceHito(BaseModel):
    nombre: str
    porcentaje_planeado: float
    porcentaje_real: float
    fecha_planeada: str
    fecha_real: Optional[str] = None
    completado: bool = False

class Avance(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    proyecto_id: str
    hitos: List[AvanceHito]
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==================== HELPER FUNCTIONS ====================

async def recalcular_avance_proyecto(proyecto_id: str):
    """
    Recalcula el porcentaje de avance de un proyecto basándose en:
    - Volumen total planeado (estimado por el cliente)
    - Suma de volúmenes excavados en los avances semanales
    
    Fórmula: avance_actual = (volumen_excavado_total / volumen_total_planeado) * 100
    """
    # Obtener el proyecto
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        return
    
    volumen_total_planeado = proyecto.get('volumen_total_planeado', 0) or 0
    
    # Si no hay volumen planeado, no se puede calcular el avance
    if volumen_total_planeado <= 0:
        return
    
    # Sumar todos los volúmenes de excavación de los avances semanales
    avances = await db.avances_semanales.find(
        {"proyecto_id": proyecto_id}, 
        {"volumen_excavacion": 1}
    ).to_list(1000)
    
    volumen_excavado_total = sum(
        (a.get('volumen_excavacion', 0) or 0) for a in avances
    )
    
    # Calcular el porcentaje de avance (máximo 100%)
    nuevo_avance = min((volumen_excavado_total / volumen_total_planeado) * 100, 100)
    nuevo_avance = round(nuevo_avance, 2)
    
    # Actualizar el proyecto
    await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": {"avance_actual": nuevo_avance}}
    )
    
    return nuevo_avance


# ==================== ROUTES ====================

@api_router.get("/")
async def root():
    return {"message": "API de Gestión de Construcción con Drones"}

# --- Auth Routes ---
@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    """Registrar un nuevo usuario"""
    # Verificar si el email ya existe
    existing_user = await db.usuarios.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Crear usuario
    new_user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        nombre=user_data.nombre,
        rol=user_data.rol
    )
    
    user_dict = new_user.model_dump()
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    await db.usuarios.insert_one(user_dict)
    
    # Crear token
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

@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    """Iniciar sesión"""
    user = await db.usuarios.find_one({"email": credentials.email}, {"_id": 0})
    
    if not user:
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    
    if not verify_password(credentials.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    
    if not user.get("activo", True):
        raise HTTPException(status_code=403, detail="Usuario desactivado")
    
    # Crear token
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

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Obtener información del usuario actual"""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        nombre=current_user["nombre"],
        rol=current_user["rol"],
        activo=current_user.get("activo", True)
    )

@api_router.get("/auth/users", response_model=List[UserResponse])
async def list_users(current_user: dict = Depends(get_current_admin)):
    """Listar todos los usuarios (solo admin)"""
    users = await db.usuarios.find({}, {"_id": 0, "password_hash": 0}).to_list(100)
    return [UserResponse(**u) for u in users]

@api_router.put("/auth/users/{user_id}/toggle-active")
async def toggle_user_active(user_id: str, current_user: dict = Depends(get_current_admin)):
    """Activar/desactivar un usuario (solo admin)"""
    user = await db.usuarios.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    new_status = not user.get("activo", True)
    await db.usuarios.update_one({"id": user_id}, {"$set": {"activo": new_status}})
    
    return {"message": f"Usuario {'activado' if new_status else 'desactivado'}", "activo": new_status}

# --- Proyectos ---
@api_router.post("/proyectos", response_model=Proyecto)
async def crear_proyecto(proyecto: ProyectoCreate):
    proyecto_obj = Proyecto(**proyecto.model_dump())
    doc = proyecto_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.proyectos.insert_one(doc)
    return proyecto_obj

@api_router.get("/proyectos", response_model=List[Proyecto])
async def listar_proyectos(cliente_id: Optional[str] = None):
    """
    Listar proyectos. Si se proporciona cliente_id, filtra por proyectos asignados a ese cliente.
    """
    query = {}
    if cliente_id:
        # Filtrar proyectos donde el cliente está en la lista de asignados
        query = {"clientes_asignados": cliente_id}
    
    proyectos = await db.proyectos.find(query, {"_id": 0}).to_list(1000)
    for p in proyectos:
        if isinstance(p.get('created_at'), str):
            p['created_at'] = datetime.fromisoformat(p['created_at'])
        # Asegurar que clientes_asignados existe
        if 'clientes_asignados' not in p:
            p['clientes_asignados'] = []
    return proyectos

@api_router.get("/proyectos/{proyecto_id}", response_model=Proyecto)
async def obtener_proyecto(proyecto_id: str):
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    if isinstance(proyecto.get('created_at'), str):
        proyecto['created_at'] = datetime.fromisoformat(proyecto['created_at'])
    return proyecto

@api_router.put("/proyectos/{proyecto_id}/avance")
async def actualizar_avance(proyecto_id: str, avance: float):
    result = await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": {"avance_actual": avance}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return {"message": "Avance actualizado", "avance": avance}

@api_router.put("/proyectos/{proyecto_id}", response_model=Proyecto)
async def actualizar_proyecto(proyecto_id: str, proyecto_update: ProyectoUpdate):
    """Actualizar un proyecto existente con todos sus campos"""
    # Obtener solo los campos que se proporcionaron (no None)
    update_data = {k: v for k, v in proyecto_update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")
    
    # Convertir volumetria a dict si existe
    if 'volumetria' in update_data and update_data['volumetria']:
        update_data['volumetria'] = update_data['volumetria'] if isinstance(update_data['volumetria'], dict) else update_data['volumetria']
    
    result = await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Recalcular el avance si se actualizó el volumen planeado
    if 'volumen_total_planeado' in update_data:
        await recalcular_avance_proyecto(proyecto_id)
    
    # Retornar el proyecto actualizado
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if isinstance(proyecto.get('created_at'), str):
        proyecto['created_at'] = datetime.fromisoformat(proyecto['created_at'])
    return proyecto

@api_router.post("/proyectos/{proyecto_id}/asignar-clientes")
async def asignar_clientes_proyecto(proyecto_id: str, cliente_ids: List[str]):
    """Asignar una lista de clientes a un proyecto"""
    # Verificar que el proyecto existe
    proyecto = await db.proyectos.find_one({"id": proyecto_id})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Verificar que todos los clientes existen
    for cliente_id in cliente_ids:
        cliente = await db.usuarios.find_one({"id": cliente_id})
        if not cliente:
            raise HTTPException(status_code=404, detail=f"Cliente {cliente_id} no encontrado")
    
    # Actualizar la lista de clientes asignados
    await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": {"clientes_asignados": cliente_ids}}
    )
    
    return {"message": f"Proyecto asignado a {len(cliente_ids)} cliente(s)", "clientes_asignados": cliente_ids}

@api_router.get("/proyectos/{proyecto_id}/clientes-asignados")
async def obtener_clientes_asignados(proyecto_id: str):
    """Obtener la lista de clientes asignados a un proyecto"""
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    clientes_ids = proyecto.get('clientes_asignados', [])
    
    # Obtener información de los clientes
    clientes = []
    for cliente_id in clientes_ids:
        cliente = await db.usuarios.find_one({"id": cliente_id}, {"_id": 0, "password_hash": 0})
        if cliente:
            clientes.append(cliente)
    
    return clientes

@api_router.delete("/proyectos/{proyecto_id}")
async def eliminar_proyecto(proyecto_id: str):
    result = await db.proyectos.delete_one({"id": proyecto_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    # También eliminar vuelos asociados
    await db.vuelos.delete_many({"proyecto_id": proyecto_id})
    await db.avances.delete_many({"proyecto_id": proyecto_id})
    return {"message": "Proyecto eliminado"}

# --- Vuelos ---
@api_router.post("/vuelos", response_model=Vuelo)
async def crear_vuelo(vuelo: VueloCreate):
    vuelo_obj = Vuelo(**vuelo.model_dump())
    doc = vuelo_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    # Si se especifica una semana, buscar o crear el avance semanal correspondiente
    if vuelo.semana and vuelo.proyecto_id:
        avance = await db.avances_semanales.find_one({
            "proyecto_id": vuelo.proyecto_id,
            "semana": vuelo.semana
        })
        
        if avance:
            # Vincular el vuelo con el avance existente
            doc['avance_semanal_id'] = avance['id']
            # Actualizar el volumen del avance con el del vuelo
            volumen_excavacion = vuelo.volumetria.volumen_excavado if vuelo.volumetria else 0
            await db.avances_semanales.update_one(
                {"id": avance['id']},
                {"$set": {"volumen_excavacion": volumen_excavacion}}
            )
            # Recalcular el avance del proyecto
            await recalcular_avance_proyecto(vuelo.proyecto_id)
        else:
            # Crear un nuevo avance semanal
            nuevo_avance_id = str(uuid.uuid4())
            nuevo_avance = {
                "id": nuevo_avance_id,
                "proyecto_id": vuelo.proyecto_id,
                "semana": vuelo.semana,
                "fecha": vuelo.fecha_vuelo,
                "volumen_excavacion": vuelo.volumetria.volumen_excavado if vuelo.volumetria else 0,
                "pix4d_url": vuelo.pix4d_url,
                "descripcion": f"Avance creado desde vuelo del {vuelo.fecha_vuelo}",
                "imagenes": [],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.avances_semanales.insert_one(nuevo_avance)
            doc['avance_semanal_id'] = nuevo_avance_id
            # Recalcular el avance del proyecto
            await recalcular_avance_proyecto(vuelo.proyecto_id)
    
    await db.vuelos.insert_one(doc)
    return vuelo_obj

@api_router.get("/vuelos", response_model=List[Vuelo])
async def listar_vuelos(proyecto_id: Optional[str] = None):
    query = {"proyecto_id": proyecto_id} if proyecto_id else {}
    vuelos = await db.vuelos.find(query, {"_id": 0}).to_list(1000)
    for v in vuelos:
        if isinstance(v.get('created_at'), str):
            v['created_at'] = datetime.fromisoformat(v['created_at'])
    return vuelos

@api_router.get("/vuelos/{vuelo_id}", response_model=Vuelo)
async def obtener_vuelo(vuelo_id: str):
    vuelo = await db.vuelos.find_one({"id": vuelo_id}, {"_id": 0})
    if not vuelo:
        raise HTTPException(status_code=404, detail="Vuelo no encontrado")
    if isinstance(vuelo.get('created_at'), str):
        vuelo['created_at'] = datetime.fromisoformat(vuelo['created_at'])
    return vuelo

@api_router.put("/vuelos/{vuelo_id}", response_model=Vuelo)
async def actualizar_vuelo(vuelo_id: str, vuelo_update: VueloUpdate):
    """Actualizar un vuelo existente"""
    update_data = {k: v for k, v in vuelo_update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")
    
    # Convertir volumetria a dict si existe
    if 'volumetria' in update_data and update_data['volumetria']:
        if hasattr(update_data['volumetria'], 'model_dump'):
            update_data['volumetria'] = update_data['volumetria'].model_dump()
    
    result = await db.vuelos.update_one(
        {"id": vuelo_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vuelo no encontrado")
    
    vuelo = await db.vuelos.find_one({"id": vuelo_id}, {"_id": 0})
    if isinstance(vuelo.get('created_at'), str):
        vuelo['created_at'] = datetime.fromisoformat(vuelo['created_at'])
    return vuelo

@api_router.delete("/vuelos/{vuelo_id}")
async def eliminar_vuelo(vuelo_id: str):
    result = await db.vuelos.delete_one({"id": vuelo_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Vuelo no encontrado")
    return {"message": "Vuelo eliminado"}

# --- Upload de archivos ---
@api_router.post("/upload/nube-puntos/{vuelo_id}")
async def upload_nube_puntos(vuelo_id: str, file: UploadFile = File(...)):
    # Validar extensión
    allowed_extensions = ['.las', '.laz', '.ply', '.xyz', '.txt']
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no permitido. Use: {', '.join(allowed_extensions)}"
        )
    
    # Guardar archivo
    file_path = UPLOAD_DIR / f"{vuelo_id}{file_ext}"
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Actualizar vuelo con ruta del archivo
    result = await db.vuelos.update_one(
        {"id": vuelo_id},
        {"$set": {"archivo_nube_puntos": str(file_path.name)}}
    )
    
    if result.matched_count == 0:
        file_path.unlink()  # Eliminar archivo si el vuelo no existe
        raise HTTPException(status_code=404, detail="Vuelo no encontrado")
    
    return {
        "message": "Archivo subido exitosamente",
        "filename": file_path.name,
        "vuelo_id": vuelo_id
    }

@api_router.get("/download/nube-puntos/{filename}")
async def download_nube_puntos(filename: str):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(file_path)

@api_router.get("/process/nube-puntos/{vuelo_id}")
async def process_nube_puntos(vuelo_id: str, max_points: int = 100000):
    """
    Procesa un archivo LAZ/LAS y extrae puntos para visualización 3D
    
    Args:
        vuelo_id: ID del vuelo
        max_points: Número máximo de puntos a devolver (para optimización)
    
    Returns:
        JSON con array de puntos [x, y, z, color]
    """
    # Obtener vuelo
    vuelo = await db.vuelos.find_one({"id": vuelo_id}, {"_id": 0})
    if not vuelo:
        raise HTTPException(status_code=404, detail="Vuelo no encontrado")
    
    archivo_nombre = vuelo.get('archivo_nube_puntos')
    if not archivo_nombre:
        raise HTTPException(status_code=404, detail="No hay archivo de nube de puntos asociado")
    
    file_path = UPLOAD_DIR / archivo_nombre
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado en servidor")
    
    try:
        # Leer archivo LAZ/LAS
        las = laspy.read(file_path)
        
        # Obtener coordenadas
        x = np.array(las.x)
        y = np.array(las.y)
        z = np.array(las.z)
        
        total_points = len(x)
        
        # Downsampling si hay demasiados puntos
        if total_points > max_points:
            # Muestreo aleatorio uniforme
            indices = np.random.choice(total_points, max_points, replace=False)
            x = x[indices]
            y = y[indices]
            z = z[indices]
        else:
            indices = np.arange(total_points)
        
        # Normalizar coordenadas (centrar en origen)
        x_center = (x.max() + x.min()) / 2
        y_center = (y.max() + y.min()) / 2
        z_center = (z.max() + z.min()) / 2
        
        x_norm = x - x_center
        y_norm = y - y_center
        z_norm = z - z_center
        
        # Calcular colores basados en altura (z)
        z_min = z_norm.min()
        z_max = z_norm.max()
        z_range = z_max - z_min if z_max != z_min else 1
        
        # Normalizar altura a rango 0-1
        z_normalized = (z_norm - z_min) / z_range
        
        # Crear colores: gradiente de azul (bajo) a rojo (alto)
        colors = []
        for z_val in z_normalized:
            if z_val < 0.33:
                # Azul a verde
                r = 0
                g = z_val * 3
                b = 1 - z_val * 3
            elif z_val < 0.66:
                # Verde a amarillo
                r = (z_val - 0.33) * 3
                g = 1
                b = 0
            else:
                # Amarillo a rojo
                r = 1
                g = 1 - (z_val - 0.66) * 3
                b = 0
            
            colors.append([r, g, b])
        
        # Convertir a lista de diccionarios
        points_data = []
        for i in range(len(x_norm)):
            points_data.append({
                "x": float(x_norm[i]),
                "y": float(y_norm[i]),
                "z": float(z_norm[i]),
                "color": colors[i]
            })
        
        # Información adicional
        metadata = {
            "total_points": int(total_points),
            "displayed_points": len(points_data),
            "bounds": {
                "x": {"min": float(x.min()), "max": float(x.max())},
                "y": {"min": float(y.min()), "max": float(y.max())},
                "z": {"min": float(z.min()), "max": float(z.max())}
            },
            "center": {
                "x": float(x_center),
                "y": float(y_center),
                "z": float(z_center)
            }
        }
        
        return JSONResponse({
            "success": True,
            "vuelo_id": vuelo_id,
            "metadata": metadata,
            "points": points_data
        })
        
    except Exception as e:
        logger.error(f"Error procesando nube de puntos: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando archivo: {str(e)}"
        )

# --- Avances ---
@api_router.post("/avances", response_model=Avance)
async def crear_avance(avance: Avance):
    doc = avance.model_dump()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.avances.insert_one(doc)
    return avance

@api_router.get("/avances/{proyecto_id}", response_model=Avance)
async def obtener_avance(proyecto_id: str):
    avance = await db.avances.find_one({"proyecto_id": proyecto_id}, {"_id": 0})
    if not avance:
        raise HTTPException(status_code=404, detail="Avance no encontrado")
    if isinstance(avance.get('updated_at'), str):
        avance['updated_at'] = datetime.fromisoformat(avance['updated_at'])
    return avance

@api_router.put("/avances/{proyecto_id}", response_model=Avance)
async def actualizar_avance_hitos(proyecto_id: str, avance: Avance):
    doc = avance.model_dump()
    doc['updated_at'] = datetime.now(timezone.utc).isoformat()
    await db.avances.update_one(
        {"proyecto_id": proyecto_id},
        {"$set": doc},
        upsert=True
    )
    return avance

# --- Avances Semanales (Modelos 3D por semana) ---
@api_router.get("/proyectos/{proyecto_id}/avances-semanales", response_model=List[AvanceSemanal])
async def listar_avances_semanales(proyecto_id: str):
    """Obtener todos los avances semanales de un proyecto ordenados por semana"""
    avances = await db.avances_semanales.find(
        {"proyecto_id": proyecto_id}, 
        {"_id": 0}
    ).sort("semana", 1).to_list(100)
    
    for avance in avances:
        if isinstance(avance.get('created_at'), str):
            avance['created_at'] = datetime.fromisoformat(avance['created_at'])
    
    return avances

@api_router.post("/proyectos/{proyecto_id}/avances-semanales", response_model=AvanceSemanal)
async def crear_avance_semanal(proyecto_id: str, avance: AvanceSemanalCreate):
    """Crear un nuevo avance semanal con su modelo 3D"""
    # Verificar que el proyecto existe
    proyecto = await db.proyectos.find_one({"id": proyecto_id})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Verificar que no exista ya un avance para esa semana
    existente = await db.avances_semanales.find_one({
        "proyecto_id": proyecto_id,
        "semana": avance.semana
    })
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe un avance para la semana {avance.semana}")
    
    nuevo_avance = AvanceSemanal(
        proyecto_id=proyecto_id,
        **avance.model_dump()
    )
    
    doc = nuevo_avance.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.avances_semanales.insert_one(doc)
    
    # Recalcular el porcentaje de avance del proyecto
    await recalcular_avance_proyecto(proyecto_id)
    
    return nuevo_avance

@api_router.put("/proyectos/{proyecto_id}/avances-semanales/{avance_id}", response_model=AvanceSemanal)
async def actualizar_avance_semanal(proyecto_id: str, avance_id: str, avance: AvanceSemanalUpdate):
    """Actualizar un avance semanal existente (actualización parcial)"""
    # Solo incluir campos que fueron proporcionados (no None)
    update_data = {k: v for k, v in avance.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    result = await db.avances_semanales.update_one(
        {"id": avance_id, "proyecto_id": proyecto_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Avance semanal no encontrado")
    
    avance_actualizado = await db.avances_semanales.find_one(
        {"id": avance_id}, 
        {"_id": 0}
    )
    if isinstance(avance_actualizado.get('created_at'), str):
        avance_actualizado['created_at'] = datetime.fromisoformat(avance_actualizado['created_at'])
    
    # Si se actualizó el volumen de excavación, recalcular el avance del proyecto
    if 'volumen_excavacion' in update_data:
        await recalcular_avance_proyecto(proyecto_id)
    
    return avance_actualizado

@api_router.delete("/proyectos/{proyecto_id}/avances-semanales/{avance_id}")
async def eliminar_avance_semanal(proyecto_id: str, avance_id: str):
    """Eliminar un avance semanal"""
    result = await db.avances_semanales.delete_one({
        "id": avance_id,
        "proyecto_id": proyecto_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Avance semanal no encontrado")
    
    # Recalcular el porcentaje de avance del proyecto
    await recalcular_avance_proyecto(proyecto_id)
    
    return {"message": "Avance semanal eliminado"}

@api_router.post("/proyectos/{proyecto_id}/avances-semanales/{avance_id}/imagenes")
async def subir_imagen_avance(proyecto_id: str, avance_id: str, file: UploadFile = File(...)):
    """Subir una imagen a un avance semanal"""
    # Verificar que el avance existe
    avance = await db.avances_semanales.find_one({"id": avance_id, "proyecto_id": proyecto_id})
    if not avance:
        raise HTTPException(status_code=404, detail="Avance semanal no encontrado")
    
    # Crear directorio para imágenes si no existe
    images_dir = UPLOAD_DIR / "imagenes" / proyecto_id / avance_id
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # Generar nombre único para la imagen
    file_extension = Path(file.filename).suffix or ".jpg"
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = images_dir / unique_filename
    
    # Guardar el archivo
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Generar URL de la imagen
    image_url = f"/api/imagenes/{proyecto_id}/{avance_id}/{unique_filename}"
    
    # Agregar URL a la lista de imágenes del avance
    await db.avances_semanales.update_one(
        {"id": avance_id},
        {"$push": {"imagenes": image_url}}
    )
    
    return {"url": image_url, "filename": unique_filename}

@api_router.get("/imagenes/{proyecto_id}/{avance_id}/{filename}")
async def obtener_imagen(proyecto_id: str, avance_id: str, filename: str):
    """Obtener una imagen de un avance semanal"""
    file_path = UPLOAD_DIR / "imagenes" / proyecto_id / avance_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    return FileResponse(file_path)

@api_router.delete("/proyectos/{proyecto_id}/avances-semanales/{avance_id}/imagenes")
async def eliminar_imagen_avance(proyecto_id: str, avance_id: str, image_url: str):
    """Eliminar una imagen de un avance semanal"""
    # Eliminar de la base de datos
    await db.avances_semanales.update_one(
        {"id": avance_id, "proyecto_id": proyecto_id},
        {"$pull": {"imagenes": image_url}}
    )
    
    # Intentar eliminar el archivo físico
    try:
        filename = image_url.split("/")[-1]
        file_path = UPLOAD_DIR / "imagenes" / proyecto_id / avance_id / filename
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        logging.error(f"Error eliminando archivo: {e}")
    
    return {"message": "Imagen eliminada"}

@api_router.get("/proyectos/{proyecto_id}/avances-semanales/{avance_id}/imagenes/zip")
async def descargar_imagenes_zip(proyecto_id: str, avance_id: str):
    """Descargar todas las imágenes de un avance semanal en formato ZIP"""
    # Verificar que el avance existe
    avance = await db.avances_semanales.find_one({"id": avance_id, "proyecto_id": proyecto_id}, {"_id": 0})
    if not avance:
        raise HTTPException(status_code=404, detail="Avance semanal no encontrado")
    
    imagenes = avance.get('imagenes', [])
    if not imagenes:
        raise HTTPException(status_code=404, detail="No hay imágenes para descargar")
    
    # Obtener info del proyecto para el nombre del archivo
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    proyecto_nombre = proyecto.get('nombre', 'Proyecto').replace(' ', '_') if proyecto else 'Proyecto'
    semana = avance.get('semana', 0)
    
    # Crear ZIP en memoria
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for idx, image_url in enumerate(imagenes, 1):
            try:
                filename = image_url.split("/")[-1]
                file_path = UPLOAD_DIR / "imagenes" / proyecto_id / avance_id / filename
                if file_path.exists():
                    # Nombre descriptivo para la imagen en el ZIP
                    extension = Path(filename).suffix
                    zip_filename = f"{proyecto_nombre}_Semana{semana}_Foto{idx}{extension}"
                    zip_file.write(file_path, zip_filename)
            except Exception as e:
                logging.error(f"Error agregando imagen al ZIP: {e}")
                continue
    
    zip_buffer.seek(0)
    
    # Nombre del archivo ZIP
    zip_filename = f"{proyecto_nombre}_Semana{semana}_Fotos.zip"
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
    )

# --- Modelos 3D (Nubes de Puntos) ---
@api_router.post("/proyectos/{proyecto_id}/avances-semanales/{avance_id}/modelo3d")
async def subir_modelo_3d(proyecto_id: str, avance_id: str, file: UploadFile = File(...)):
    """Subir un modelo 3D (nube de puntos PLY) a un avance semanal"""
    # Verificar que el avance existe
    avance = await db.avances_semanales.find_one({"id": avance_id, "proyecto_id": proyecto_id})
    if not avance:
        raise HTTPException(status_code=404, detail="Avance semanal no encontrado")
    
    # Verificar extensión del archivo
    file_extension = Path(file.filename).suffix.lower()
    allowed_extensions = ['.ply', '.xyz', '.pts', '.pcd']
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Formato no soportado. Use: {', '.join(allowed_extensions)}"
        )
    
    # Crear directorio para modelos 3D si no existe
    models_dir = UPLOAD_DIR / "modelos3d" / proyecto_id / avance_id
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Eliminar modelo anterior si existe
    old_model = avance.get('modelo_3d_url')
    if old_model:
        try:
            old_filename = old_model.split("/")[-1]
            old_file_path = models_dir / old_filename
            if old_file_path.exists():
                old_file_path.unlink()
        except Exception as e:
            logging.error(f"Error eliminando modelo anterior: {e}")
    
    # Generar nombre único para el modelo
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = models_dir / unique_filename
    
    # Guardar el archivo
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Generar URL del modelo
    model_url = f"/api/modelos3d/{proyecto_id}/{avance_id}/{unique_filename}"
    
    # Actualizar el avance con la URL del modelo
    await db.avances_semanales.update_one(
        {"id": avance_id},
        {"$set": {"modelo_3d_url": model_url, "modelo_3d_tipo": "local"}}
    )
    
    # Obtener tamaño del archivo
    file_size = file_path.stat().st_size
    file_size_mb = round(file_size / (1024 * 1024), 2)
    
    return {
        "url": model_url, 
        "filename": unique_filename,
        "size_mb": file_size_mb,
        "tipo": "local"
    }

@api_router.get("/modelos3d/{proyecto_id}/{avance_id}/{filename}")
async def obtener_modelo_3d(proyecto_id: str, avance_id: str, filename: str):
    """Obtener un modelo 3D de un avance semanal"""
    file_path = UPLOAD_DIR / "modelos3d" / proyecto_id / avance_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Modelo 3D no encontrado")
    
    # Determinar el content-type basado en la extensión
    extension = Path(filename).suffix.lower()
    content_types = {
        '.ply': 'application/octet-stream',
        '.xyz': 'text/plain',
        '.pts': 'text/plain',
        '.pcd': 'application/octet-stream'
    }
    content_type = content_types.get(extension, 'application/octet-stream')
    
    return FileResponse(
        file_path,
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=3600"
        }
    )

@api_router.delete("/proyectos/{proyecto_id}/avances-semanales/{avance_id}/modelo3d")
async def eliminar_modelo_3d(proyecto_id: str, avance_id: str):
    """Eliminar el modelo 3D de un avance semanal"""
    # Obtener el avance para encontrar el archivo
    avance = await db.avances_semanales.find_one({"id": avance_id, "proyecto_id": proyecto_id})
    if not avance:
        raise HTTPException(status_code=404, detail="Avance semanal no encontrado")
    
    model_url = avance.get('modelo_3d_url')
    if model_url and '/api/modelos3d/' in model_url:
        try:
            filename = model_url.split("/")[-1]
            file_path = UPLOAD_DIR / "modelos3d" / proyecto_id / avance_id / filename
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logging.error(f"Error eliminando modelo 3D: {e}")
    
    # Actualizar la base de datos
    await db.avances_semanales.update_one(
        {"id": avance_id, "proyecto_id": proyecto_id},
        {"$set": {"modelo_3d_url": None, "modelo_3d_tipo": None}}
    )
    
    return {"message": "Modelo 3D eliminado"}

# --- Reporte Ejecutivo PDF ---
@api_router.get("/proyectos/{proyecto_id}/reporte-ejecutivo")
async def generar_reporte_ejecutivo(proyecto_id: str):
    """
    Genera un reporte ejecutivo en PDF para un proyecto.
    Usa la configuración de flotilla guardada en el proyecto.
    
    Returns:
        PDF con el reporte ejecutivo
    """
    # Obtener datos del proyecto
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Obtener configuración de flotilla del proyecto
    capacidad_camion = proyecto.get('capacidad_camion', 25.0) or 25.0
    costo_por_m3 = proyecto.get('costo_m3', 150.0) or 150.0
    
    # Obtener avances semanales
    avances = await db.avances_semanales.find(
        {"proyecto_id": proyecto_id}, 
        {"_id": 0}
    ).sort("semana", 1).to_list(100)
    
    # Calcular totales
    volumen_total = sum(a.get('volumen_excavacion', 0) or 0 for a in avances)
    total_viajes = int(volumen_total / capacidad_camion) if capacidad_camion > 0 else 0
    costo_total_estimado = volumen_total * costo_por_m3  # Cálculo basado en m³
    
    # Crear PDF en memoria
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#994B49'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#666666'),
        spaceAfter=15,
        alignment=TA_CENTER
    )
    
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#994B49'),
        spaceBefore=20,
        spaceAfter=10
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8
    )
    
    # Contenido del PDF
    story = []
    
    # --- ENCABEZADO ---
    story.append(Paragraph("REPORTE EJECUTIVO", title_style))
    story.append(Paragraph("Gestión de Construcción con Drones", subtitle_style))
    story.append(Spacer(1, 20))
    
    # --- INFORMACIÓN DEL PROYECTO ---
    story.append(Paragraph("📋 INFORMACIÓN DEL PROYECTO", section_style))
    
    proyecto_info = [
        ["Nombre del Proyecto:", proyecto.get('nombre', 'N/A')],
        ["Ubicación:", proyecto.get('ubicacion', 'N/A')],
        ["Coordenadas:", f"Lat: {proyecto.get('coordenadas', {}).get('lat', 'N/A')}, Lng: {proyecto.get('coordenadas', {}).get('lng', 'N/A')}"],
        ["Fecha de Inicio:", proyecto.get('fecha_inicio', 'N/A')],
        ["Fecha Fin Planeada:", proyecto.get('fecha_fin_planeada', 'N/A')],
        ["Descripción:", proyecto.get('descripcion', 'Sin descripción')[:100] + '...' if proyecto.get('descripcion') and len(proyecto.get('descripcion', '')) > 100 else proyecto.get('descripcion', 'Sin descripción')],
    ]
    
    info_table = Table(proyecto_info, colWidths=[150, 350])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#994B49')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # --- AVANCE DE OBRA ---
    story.append(Paragraph("📊 AVANCE DE OBRA", section_style))
    
    avance_actual = proyecto.get('avance_actual', 0)
    avance_color = colors.HexColor('#10B981') if avance_actual >= 75 else colors.HexColor('#F59E0B') if avance_actual >= 50 else colors.HexColor('#EF4444')
    
    avance_data = [
        ["Avance Actual:", f"{avance_actual}%"],
        ["Estado:", "En Progreso" if avance_actual < 100 else "Completado"],
        ["Semanas Registradas:", str(len(avances))],
    ]
    
    avance_table = Table(avance_data, colWidths=[150, 350])
    avance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#994B49')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, 0), 14),
        ('TEXTCOLOR', (1, 0), (1, 0), avance_color),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(avance_table)
    story.append(Spacer(1, 20))
    
    # --- VOLUMETRÍA POR SEMANA ---
    story.append(Paragraph("🚛 VOLUMETRÍA DE EXCAVACIÓN POR SEMANA", section_style))
    
    if avances:
        # Tabla de volúmenes por semana
        vol_headers = ["Semana", "Fecha", "Volumen (m³)", "Viajes Estimados", "Avance (%)"]
        vol_data = [vol_headers]
        
        for avance in avances:
            volumen = avance.get('volumen_excavacion', 0) or 0
            viajes = int(volumen / capacidad_camion) if capacidad_camion > 0 else 0
            porcentaje = avance.get('porcentaje_avance', 0) or 0
            vol_data.append([
                f"Semana {avance.get('semana', '?')}",
                avance.get('fecha', 'N/A'),
                f"{volumen:,.1f}",
                str(viajes),
                f"{porcentaje}%"
            ])
        
        # Fila de totales
        vol_data.append([
            "TOTAL",
            "-",
            f"{volumen_total:,.1f}",
            str(total_viajes),
            f"{avance_actual}%"
        ])
        
        vol_table = Table(vol_data, colWidths=[80, 90, 100, 110, 80])
        vol_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#994B49')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            # Body
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F8F9FA')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#994B49')),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(vol_table)
    else:
        story.append(Paragraph("No hay datos de volumetría registrados.", normal_style))
    
    story.append(Spacer(1, 20))
    
    # --- RESUMEN PARA LOGÍSTICA DE TRANSPORTE ---
    story.append(Paragraph("🚚 RESUMEN PARA LOGÍSTICA DE TRANSPORTE", section_style))
    
    # Los valores vienen del proyecto (ya calculados arriba)
    logistica_data = [
        ["Capacidad por Camión:", f"{capacidad_camion:,.1f} m³"],
        ["Volumen Total Excavado:", f"{volumen_total:,.1f} m³"],
        ["Total de Viajes Requeridos:", f"{total_viajes:,} viajes"],
        ["Costo por m³:", f"${costo_por_m3:,.2f} MXN"],
        ["Costo Total Estimado:", f"${costo_total_estimado:,.2f} MXN"],
    ]
    
    logistica_table = Table(logistica_data, colWidths=[180, 320])
    logistica_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#994B49')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        # Destacar costo total
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (1, -1), (1, -1), 12),
        ('TEXTCOLOR', (1, -1), (1, -1), colors.HexColor('#994B49')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FEF3C7')),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(logistica_table)
    story.append(Spacer(1, 20))
    
    # --- DESGLOSE POR SEMANA PARA PRESUPUESTO ---
    if avances:
        story.append(Paragraph("💰 DESGLOSE DE COSTOS POR SEMANA", section_style))
        
        costo_headers = ["Semana", "Volumen (m³)", "Viajes", "Costo Estimado"]
        costo_data = [costo_headers]
        
        for avance in avances:
            volumen = avance.get('volumen_excavacion', 0) or 0
            viajes = int(volumen / capacidad_camion) if capacidad_camion > 0 else 0
            costo = volumen * costo_por_m3  # Costo basado en volumen
            costo_data.append([
                f"Semana {avance.get('semana', '?')}",
                f"{volumen:,.1f}",
                str(viajes),
                f"${costo:,.2f}"
            ])
        
        costo_data.append([
            "TOTAL",
            f"{volumen_total:,.1f}",
            str(total_viajes),
            f"${costo_total_estimado:,.2f}"
        ])
        
        costo_table = Table(costo_data, colWidths=[100, 120, 100, 140])
        costo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#D1FAE5')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#059669')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(costo_table)
    
    story.append(Spacer(1, 30))
    
    # --- PIE DE PÁGINA ---
    fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M")
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#9CA3AF'),
        alignment=TA_CENTER
    )
    story.append(Paragraph(f"Reporte generado el {fecha_generacion} | DrON Topografía - Gestión de Construcción con Drones", footer_style))
    story.append(Paragraph("* Los costos son estimados y pueden variar según las condiciones del mercado y la distancia de transporte.", footer_style))
    
    # Generar PDF
    doc.build(story)
    buffer.seek(0)
    
    # Nombre del archivo
    proyecto_nombre = proyecto.get('nombre', 'Proyecto').replace(' ', '_')
    fecha_archivo = datetime.now().strftime("%Y%m%d")
    pdf_filename = f"Reporte_Ejecutivo_{proyecto_nombre}_{fecha_archivo}.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={pdf_filename}"}
    )

# --- Solicitudes de Vuelo ---
def generar_google_calendar_link(titulo, fecha, hora, descripcion, ubicacion=""):
    """Genera un link para agregar evento a Google Calendar"""
    # Formatear fecha y hora para Google Calendar
    fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
    
    if hora:
        try:
            hora_dt = datetime.strptime(hora, "%H:%M")
            fecha_inicio = fecha_dt.replace(hour=hora_dt.hour, minute=hora_dt.minute)
            fecha_fin = fecha_inicio.replace(hour=hora_dt.hour + 2)  # 2 horas de duración
        except:
            fecha_inicio = fecha_dt.replace(hour=9, minute=0)
            fecha_fin = fecha_dt.replace(hour=11, minute=0)
    else:
        fecha_inicio = fecha_dt.replace(hour=9, minute=0)
        fecha_fin = fecha_dt.replace(hour=11, minute=0)
    
    # Formato para Google Calendar: YYYYMMDDTHHmmSS
    fecha_inicio_str = fecha_inicio.strftime("%Y%m%dT%H%M%S")
    fecha_fin_str = fecha_fin.strftime("%Y%m%dT%H%M%S")
    
    # Construir URL
    base_url = "https://calendar.google.com/calendar/render"
    params = {
        "action": "TEMPLATE",
        "text": titulo,
        "dates": f"{fecha_inicio_str}/{fecha_fin_str}",
        "details": descripcion,
        "location": ubicacion
    }
    
    query_string = "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])
    return f"{base_url}?{query_string}"

@api_router.post("/solicitudes-vuelo", response_model=dict)
async def crear_solicitud_vuelo(solicitud: SolicitudVueloCreate, credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    """Crear una solicitud de vuelo y enviar notificación por email"""
    
    # Obtener info del cliente si está autenticado
    cliente_id = None
    cliente_email = None
    cliente_nombre = None
    
    if credentials:
        try:
            token = credentials.credentials
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                user = await db.usuarios.find_one({"id": user_id}, {"_id": 0})
                if user:
                    cliente_id = user["id"]
                    cliente_email = user["email"]
                    cliente_nombre = user["nombre"]
        except Exception:
            pass  # Si hay error con el token, continuar sin datos de cliente
    
    # Crear la solicitud
    nueva_solicitud = SolicitudVuelo(
        nombre_proyecto=solicitud.nombre_proyecto,
        fecha_inicio_proyecto=solicitud.fecha_inicio_proyecto,
        fecha_fin_proyecto=solicitud.fecha_fin_proyecto,
        fecha_vuelo_deseada=solicitud.fecha_vuelo_deseada,
        hora_preferencia=solicitud.hora_preferencia,
        notas=solicitud.notas,
        cliente_id=cliente_id,
        cliente_email=cliente_email,
        cliente_nombre=cliente_nombre
    )
    
    solicitud_dict = nueva_solicitud.model_dump()
    solicitud_dict['created_at'] = solicitud_dict['created_at'].isoformat()
    
    # Guardar en base de datos
    await db.solicitudes_vuelo.insert_one(solicitud_dict)
    
    # Generar link de Google Calendar
    titulo_evento = f"🚁 Vuelo DrON - {solicitud.nombre_proyecto}"
    descripcion_evento = f"""Solicitud de vuelo de dron

Proyecto: {solicitud.nombre_proyecto}
Fecha del proyecto: {solicitud.fecha_inicio_proyecto} al {solicitud.fecha_fin_proyecto}
Fecha solicitada: {solicitud.fecha_vuelo_deseada}
Hora preferida: {solicitud.hora_preferencia or 'Sin preferencia'}

Notas del cliente:
{solicitud.notas or 'Sin notas adicionales'}
"""
    
    google_calendar_link = generar_google_calendar_link(
        titulo=titulo_evento,
        fecha=solicitud.fecha_vuelo_deseada,
        hora=solicitud.hora_preferencia,
        descripcion=descripcion_evento
    )
    
    # Construir email HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa;">
        <div style="background-color: #994B49; color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">🚁 Nueva Solicitud de Vuelo</h1>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">DrON Topografía</p>
        </div>
        
        <div style="background-color: white; padding: 25px; border: 1px solid #e5e7eb; border-top: none;">
            <h2 style="color: #994B49; margin-top: 0;">Detalles del Proyecto</h2>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; color: #6b7280; width: 40%;">Nombre del Proyecto:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; font-weight: bold;">{solicitud.nombre_proyecto}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; color: #6b7280;">Fecha Inicio:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{solicitud.fecha_inicio_proyecto}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; color: #6b7280;">Fecha Fin:</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{solicitud.fecha_fin_proyecto}</td>
                </tr>
            </table>
            
            <h2 style="color: #994B49;">📅 Fecha Solicitada para el Vuelo</h2>
            
            <div style="background-color: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 15px; margin-bottom: 20px;">
                <p style="margin: 0; font-size: 18px; font-weight: bold; color: #92400e;">
                    {solicitud.fecha_vuelo_deseada}
                    {f' a las {solicitud.hora_preferencia}' if solicitud.hora_preferencia else ''}
                </p>
            </div>
            
            {f'''
            <h3 style="color: #374151;">📝 Notas del Cliente:</h3>
            <div style="background-color: #f3f4f6; border-radius: 8px; padding: 15px; margin-bottom: 20px;">
                <p style="margin: 0; color: #4b5563;">{solicitud.notas}</p>
            </div>
            ''' if solicitud.notas else ''}
            
            <div style="text-align: center; margin-top: 25px;">
                <a href="{google_calendar_link}" 
                   style="display: inline-block; background-color: #994B49; color: white; padding: 15px 30px; 
                          text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
                    📅 Agregar a Google Calendar
                </a>
            </div>
            
            <p style="color: #9ca3af; font-size: 12px; text-align: center; margin-top: 25px;">
                Este correo fue generado automáticamente desde DrON Topografía.
            </p>
        </div>
        
        <div style="background-color: #994B49; color: white; padding: 15px; border-radius: 0 0 10px 10px; text-align: center;">
            <p style="margin: 0; font-size: 12px; opacity: 0.8;">
                © {datetime.now().year} DrON Topografía - Gestión de Construcción con Drones
            </p>
        </div>
    </body>
    </html>
    """
    
    # Enviar email
    try:
        params = {
            "from": "DrON Topografía <onboarding@resend.dev>",
            "to": [ADMIN_EMAIL],
            "subject": f"🚁 Nueva Solicitud de Vuelo - {solicitud.nombre_proyecto}",
            "html": html_content
        }
        
        email_result = await asyncio.to_thread(resend.Emails.send, params)
        logging.info(f"Email enviado: {email_result}")
        
        return {
            "status": "success",
            "message": "Solicitud de vuelo creada y notificación enviada",
            "solicitud_id": nueva_solicitud.id,
            "email_sent": True
        }
    except Exception as e:
        logging.error(f"Error enviando email: {e}")
        # Aún así guardamos la solicitud
        return {
            "status": "partial",
            "message": "Solicitud creada pero hubo un error al enviar el email",
            "solicitud_id": nueva_solicitud.id,
            "email_sent": False,
            "error": str(e)
        }

@api_router.get("/solicitudes-vuelo")
async def listar_solicitudes_vuelo(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    """Listar solicitudes de vuelo - Admin ve todas, Cliente ve solo las suyas"""
    user = None
    if credentials:
        try:
            token = credentials.credentials
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                user = await db.usuarios.find_one({"id": user_id}, {"_id": 0})
        except Exception:
            pass
    
    # Si es admin o no hay usuario, mostrar todas
    if not user or user.get("rol") == "admin":
        solicitudes = await db.solicitudes_vuelo.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    else:
        # Cliente solo ve sus solicitudes
        solicitudes = await db.solicitudes_vuelo.find(
            {"cliente_id": user["id"]}, 
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
    
    return solicitudes

@api_router.put("/solicitudes-vuelo/{solicitud_id}/estado")
async def actualizar_estado_solicitud(solicitud_id: str, update_data: SolicitudVueloUpdate, current_user: dict = Depends(get_current_admin)):
    """Actualizar el estado de una solicitud de vuelo (solo admin) y notificar al cliente"""
    estados_validos = ["pendiente", "confirmado", "completado", "cancelado"]
    if update_data.estado not in estados_validos:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Debe ser uno de: {estados_validos}")
    
    # Obtener la solicitud actual
    solicitud = await db.solicitudes_vuelo.find_one({"id": solicitud_id}, {"_id": 0})
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    # Actualizar estado y comentario
    update_fields = {
        "estado": update_data.estado,
        "fecha_respuesta": datetime.now(timezone.utc).isoformat()
    }
    if update_data.comentario_admin:
        update_fields["comentario_admin"] = update_data.comentario_admin
    
    await db.solicitudes_vuelo.update_one(
        {"id": solicitud_id},
        {"$set": update_fields}
    )
    
    # Enviar notificación por email al cliente si tiene email
    cliente_email = solicitud.get("cliente_email")
    if cliente_email and update_data.estado in ["confirmado", "cancelado"]:
        try:
            estado_texto = "CONFIRMADO ✅" if update_data.estado == "confirmado" else "CANCELADO ❌"
            estado_color = "#059669" if update_data.estado == "confirmado" else "#DC2626"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="utf-8"></head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8f9fa;">
                <div style="background-color: #994B49; color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center;">
                    <h1 style="margin: 0; font-size: 24px;">🚁 Actualización de Solicitud</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">DrON Topografía</p>
                </div>
                
                <div style="background-color: white; padding: 25px; border: 1px solid #e5e7eb; border-top: none;">
                    <h2 style="color: {estado_color}; margin-top: 0; text-align: center;">{estado_texto}</h2>
                    
                    <p>Hola <strong>{solicitud.get('cliente_nombre', 'Cliente')}</strong>,</p>
                    
                    <p>Tu solicitud de vuelo para el proyecto <strong>{solicitud.get('nombre_proyecto')}</strong> ha sido <strong style="color: {estado_color};">{update_data.estado}</strong>.</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; color: #6b7280;">Fecha solicitada:</td>
                            <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; font-weight: bold;">{solicitud.get('fecha_vuelo_deseada')}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border-bottom: 1px solid #e5e7eb; color: #6b7280;">Hora preferida:</td>
                            <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{solicitud.get('hora_preferencia', 'Sin preferencia')}</td>
                        </tr>
                    </table>
                    
                    {f'<div style="background-color: #f3f4f6; border-radius: 8px; padding: 15px; margin: 20px 0;"><strong>Comentario del administrador:</strong><p style="margin: 10px 0 0 0;">{update_data.comentario_admin}</p></div>' if update_data.comentario_admin else ''}
                    
                    <p style="color: #6b7280; font-size: 14px; margin-top: 20px;">
                        Si tienes alguna pregunta, no dudes en contactarnos.
                    </p>
                </div>
                
                <div style="background-color: #994B49; color: white; padding: 15px; border-radius: 0 0 10px 10px; text-align: center;">
                    <p style="margin: 0; font-size: 12px; opacity: 0.8;">© {datetime.now().year} DrON Topografía</p>
                </div>
            </body>
            </html>
            """
            
            params = {
                "from": "DrON Topografía <onboarding@resend.dev>",
                "to": [cliente_email],
                "subject": f"🚁 Tu solicitud ha sido {update_data.estado} - {solicitud.get('nombre_proyecto')}",
                "html": html_content
            }
            
            await asyncio.to_thread(resend.Emails.send, params)
            logging.info(f"Email de notificación enviado a {cliente_email}")
        except Exception as e:
            logging.error(f"Error enviando email de notificación: {e}")
    
    return {"message": "Estado actualizado", "estado": update_data.estado, "notificacion_enviada": bool(cliente_email)}

# --- Estadísticas ---
@api_router.get("/estadisticas/resumen")
async def obtener_estadisticas():
    total_proyectos = await db.proyectos.count_documents({})
    total_vuelos = await db.vuelos.count_documents({})
    
    # Calcular avance promedio
    proyectos = await db.proyectos.find({}, {"avance_actual": 1, "_id": 0}).to_list(1000)
    avance_promedio = sum(p.get('avance_actual', 0) for p in proyectos) / max(total_proyectos, 1)
    
    # Volumetría total
    vuelos = await db.vuelos.find({}, {"volumetria": 1, "_id": 0}).to_list(1000)
    vol_total = {
        "excavacion": sum(v.get('volumetria', {}).get('excavacion', 0) for v in vuelos),
        "relleno": sum(v.get('volumetria', {}).get('relleno', 0) for v in vuelos),
        "materiales": sum(v.get('volumetria', {}).get('materiales', 0) for v in vuelos)
    }
    
    return {
        "total_proyectos": total_proyectos,
        "total_vuelos": total_vuelos,
        "avance_promedio": round(avance_promedio, 1),
        "volumetria_total": vol_total
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
