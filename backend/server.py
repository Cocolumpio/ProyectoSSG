from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Depends, Form
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
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
from jose import JWTError, jwt
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# PDF Generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Excel processing
from openpyxl import load_workbook, Workbook

# Import shared configuration
from core.config import (
    get_db, get_client, get_database, UPLOAD_DIR, ROOT_DIR,
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
    RESEND_API_KEY, ADMIN_EMAIL, EMERGENT_LLM_KEY,
    verify_password, get_password_hash, create_access_token,
    get_current_user, get_current_admin, get_optional_user,
    pwd_context, security, logger
)

# Import shared services
from services.helpers import recalcular_avance_proyecto, generar_google_calendar_link, obtener_metricas_proyecto
from services.email import enviar_alerta_discrepancia, enviar_notificacion_solicitud_vuelo, enviar_actualizacion_solicitud

# Thread pool for CPU-intensive tasks
thumbnail_executor = ThreadPoolExecutor(max_workers=2)

# Scheduler for weekly reports
scheduler = AsyncIOScheduler()

# Resend configuration
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

# Database reference (for backwards compatibility)
db = get_db()
client = get_client()

# Thumbnail generation function
def generate_ply_thumbnail(ply_path: str, output_path: str, width: int = 400, height: int = 300) -> bool:
    """
    Genera una miniatura de una nube de puntos PLY con vista superior (planta).
    Usa matplotlib y plyfile. Maneja tanto formato ASCII como binario.
    """
    try:
        import matplotlib
        matplotlib.use('Agg')  # Backend sin GUI
        import matplotlib.pyplot as plt
        from plyfile import PlyData
        
        # Leer el archivo PLY con plyfile (maneja ASCII y binario)
        plydata = PlyData.read(ply_path)
        vertex = plydata['vertex']
        
        # Extraer coordenadas
        x = np.array(vertex['x'])
        y = np.array(vertex['y'])
        z = np.array(vertex['z'])
        
        num_points = len(x)
        logging.info(f"Archivo PLY tiene {num_points} puntos")
        
        # Submuestrear si hay muchos puntos (máximo 50,000 para el thumbnail)
        indices = None
        if num_points > 50000:
            indices = np.random.choice(num_points, 50000, replace=False)
            x = x[indices]
            y = y[indices]
            z = z[indices]
        
        # Extraer colores si existen
        colors = None
        try:
            r = np.array(vertex['red']) / 255.0
            g = np.array(vertex['green']) / 255.0
            b = np.array(vertex['blue']) / 255.0
            if indices is not None:
                r = r[indices]
                g = g[indices]
                b = b[indices]
            colors = np.column_stack([r, g, b])
        except Exception:
            pass
        
        # Centrar los puntos
        x = x - np.mean(x)
        y = y - np.mean(y)
        z = z - np.mean(z)
        
        # Crear la figura con solo vista superior
        fig = plt.figure(figsize=(width/100, height/100), dpi=100)
        fig.patch.set_facecolor('#1a1a2e')
        
        # Vista Superior (planta) - vista desde arriba
        ax = fig.add_subplot(111, projection='3d')
        ax.set_facecolor('#1a1a2e')
        if colors is not None:
            ax.scatter(x, y, z, c=colors, s=0.3, alpha=0.9)
        else:
            ax.scatter(x, y, z, c='#994B49', s=0.3, alpha=0.9)
        ax.view_init(elev=90, azim=0)  # Vista desde arriba
        ax.set_axis_off()
        
        # Ajustar límites
        max_range = max(np.max(np.abs(x)), np.max(np.abs(y)), np.max(np.abs(z))) * 1.1
        ax.set_xlim([-max_range, max_range])
        ax.set_ylim([-max_range, max_range])
        ax.set_zlim([-max_range, max_range])
        
        plt.tight_layout(pad=0)
        plt.savefig(output_path, dpi=100, bbox_inches='tight', 
                   facecolor='#1a1a2e', edgecolor='none')
        plt.close(fig)
        
        logging.info(f"Thumbnail generado: {output_path} ({len(x)} puntos)")
        return True
        
    except Exception as e:
        logging.error(f"Error generando thumbnail: {e}")
        import traceback
        traceback.print_exc()
        return False

async def generate_thumbnail_async(ply_path: str, output_path: str) -> bool:
    """Wrapper async para generar thumbnail en thread pool"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        thumbnail_executor, 
        generate_ply_thumbnail, 
        ply_path, 
        output_path
    )

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
    thumbnail_url: Optional[str] = None  # URL de la miniatura del modelo 3D
    descripcion: Optional[str] = None
    porcentaje_avance: Optional[float] = None  # Porcentaje de avance en esa semana
    volumen_excavacion: Optional[float] = None  # Volumen quitado en m³
    pilas_completadas: Optional[int] = None  # Pilas completadas en esta semana
    anclas_instaladas: Optional[int] = None  # Anclas instaladas en esta semana
    muros_completados: Optional[int] = None  # Muros completados en esta semana
    imagenes: List[str] = []  # URLs de las imágenes del vuelo
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AvanceSemanalCreate(BaseModel):
    semana: int
    fecha: str
    pix4d_url: Optional[str] = None  # Ahora opcional
    descripcion: Optional[str] = None
    porcentaje_avance: Optional[float] = None
    volumen_excavacion: Optional[float] = None  # Volumen quitado en m³
    pilas_completadas: Optional[int] = None  # Pilas completadas
    anclas_instaladas: Optional[int] = None  # Anclas instaladas
    muros_completados: Optional[int] = None  # Muros completados
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
    pilas_completadas: Optional[int] = None
    anclas_instaladas: Optional[int] = None
    muros_completados: Optional[int] = None

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
    # Tipos de actividades del proyecto
    actividades_tipo: List[str] = []  # ["excavacion", "pilas", "muros", "anclas", "cimentacion"]
    # Métricas planeadas
    volumen_total_planeado: float = 0.0  # Volumen total estimado a excavar en m³
    pilas_planeadas: int = 0  # Número total de pilas planeadas
    muros_planeados: int = 0  # Número total de muros planeados
    anclas_planeadas: int = 0  # Número total de anclas planeadas
    # Métricas ejecutadas
    volumen_ejecutado: float = 0.0  # Volumen excavado en m³
    pilas_ejecutadas: int = 0  # Pilas completadas
    muros_ejecutados: int = 0  # Muros completados
    anclas_ejecutadas: int = 0  # Anclas instaladas
    # Cronograma
    semanas_planeadas: int = 0  # Número de semanas planeadas de trabajo según cronograma
    semanas_excavacion: int = 0  # Semanas dedicadas a excavación
    semanas_pilas: int = 0  # Semanas dedicadas a pilas
    semanas_muros: int = 0  # Semanas dedicadas a muros
    descripcion: Optional[str] = None
    pix4d_url: Optional[str] = None  # URL del modelo 3D
    volumetria: Optional[Volumetria] = None  # Volumetrías del proyecto
    # Configuración de flotilla de camiones
    capacidad_camion: float = 25.0  # m³ por camión (default 25 m³)
    costo_m3: float = 150.0  # Costo por metro cúbico en MXN (default $150)
    # Parámetros del terreno
    area_terreno: float = 0.0  # m²
    espacio_maniobra: float = 0.0  # m²
    distancia_pilas: float = 3.0  # metros
    # Catálogo de maquinaria
    catalogo_maquinaria: List[dict] = []
    analisis_maquinaria_ia: Optional[dict] = None
    parametros_proyecto: Optional[dict] = None
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
    # Tipos de actividades
    actividades_tipo: List[str] = []  # ["excavacion", "pilas", "muros", "anclas", "cimentacion"]
    # Métricas planeadas
    volumen_total_planeado: float = 0.0
    pilas_planeadas: int = 0
    muros_planeados: int = 0
    anclas_planeadas: int = 0
    # Cronograma
    semanas_planeadas: int = 0
    semanas_excavacion: int = 0
    semanas_pilas: int = 0
    semanas_muros: int = 0
    volumetria: Optional[Volumetria] = None
    # Configuración de flotilla
    capacidad_camion: float = 25.0
    costo_m3: float = 150.0
    # Parámetros del terreno
    area_terreno: float = 0.0
    espacio_maniobra: float = 0.0
    distancia_pilas: float = 3.0
    # Catálogo de maquinaria
    catalogo_maquinaria: List[dict] = []
    analisis_maquinaria_ia: Optional[dict] = None
    parametros_proyecto: Optional[dict] = None
    clientes_asignados: List[str] = []

class ProyectoUpdate(BaseModel):
    nombre: Optional[str] = None
    ubicacion: Optional[str] = None
    direccion: Optional[str] = None
    coordenadas: Optional[Coordinates] = None
    fecha_inicio: Optional[str] = None
    fecha_fin_planeada: Optional[str] = None
    avance_actual: Optional[float] = None
    # Tipos de actividades
    actividades_tipo: Optional[List[str]] = None
    # Métricas planeadas
    volumen_total_planeado: Optional[float] = None
    pilas_planeadas: Optional[int] = None
    muros_planeados: Optional[int] = None
    anclas_planeadas: Optional[int] = None
    # Métricas ejecutadas
    volumen_ejecutado: Optional[float] = None
    pilas_ejecutadas: Optional[int] = None
    muros_ejecutados: Optional[int] = None
    anclas_ejecutadas: Optional[int] = None
    # Cronograma
    semanas_planeadas: Optional[int] = None
    semanas_excavacion: Optional[int] = None
    semanas_pilas: Optional[int] = None
    semanas_muros: Optional[int] = None
    descripcion: Optional[str] = None
    pix4d_url: Optional[str] = None
    volumetria: Optional[Volumetria] = None
    capacidad_camion: Optional[float] = None
    costo_m3: Optional[float] = None
    # Parámetros del terreno
    area_terreno: Optional[float] = None
    espacio_maniobra: Optional[float] = None
    distancia_pilas: Optional[float] = None
    # Catálogo de maquinaria
    catalogo_maquinaria: Optional[List[dict]] = None
    analisis_maquinaria_ia: Optional[dict] = None
    parametros_proyecto: Optional[dict] = None
    clientes_asignados: Optional[List[str]] = None

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
    archivo_nube_puntos: Optional[str] = None
    pix4d_url: Optional[str] = None  # URL del iframe de Pix4D
    estado: str = "completado"  # completado, procesando, fallido
    notas: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VueloCreate(BaseModel):
    proyecto_id: str
    fecha_vuelo: str
    duracion_minutos: int
    area_cubierta: float
    num_imagenes: int
    pix4d_url: Optional[str] = None
    notas: Optional[str] = None

class VueloUpdate(BaseModel):
    proyecto_id: Optional[str] = None
    fecha_vuelo: Optional[str] = None
    duracion_minutos: Optional[int] = None
    area_cubierta: Optional[float] = None
    num_imagenes: Optional[int] = None
    pix4d_url: Optional[str] = None
    notas: Optional[str] = None
    estado: Optional[str] = None

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


# --- Notificaciones ---
@api_router.get("/notificaciones")
async def listar_notificaciones(
    current_user: dict = Depends(get_current_user),
    solo_no_leidas: bool = False,
    limite: int = 50
):
    """
    Lista las notificaciones del usuario actual.
    - Admins: ven notificaciones globales y las dirigidas a ellos
    - Clientes: ven solo notificaciones dirigidas a ellos
    """
    user_id = current_user.get("id")
    is_admin = current_user.get("rol") == "admin"
    
    if is_admin:
        # Admins ven notificaciones globales (usuario_id=None) y las suyas
        query = {"$or": [{"usuario_id": None}, {"usuario_id": user_id}]}
    else:
        # Clientes solo ven las suyas
        query = {"usuario_id": user_id}
    
    if solo_no_leidas:
        query["leida"] = False
    
    notificaciones = await db.notificaciones.find(
        query, 
        {"_id": 0}
    ).sort("fecha", -1).limit(limite).to_list(limite)
    
    # Contar no leídas
    count_query = {"$or": [{"usuario_id": None}, {"usuario_id": user_id}]} if is_admin else {"usuario_id": user_id}
    count_query["leida"] = False
    no_leidas = await db.notificaciones.count_documents(count_query)
    
    return {
        "notificaciones": notificaciones,
        "total_no_leidas": no_leidas
    }


@api_router.post("/notificaciones")
async def crear_notificacion(
    notificacion: dict,
    current_user: dict = Depends(get_current_admin)
):
    """Crear una nueva notificación (solo admins)"""
    notif_data = {
        "id": str(uuid.uuid4()),
        "tipo": notificacion.get("tipo", "info"),
        "titulo": notificacion.get("titulo", "Notificación"),
        "mensaje": notificacion.get("mensaje", ""),
        "proyecto_id": notificacion.get("proyecto_id"),
        "proyecto_nombre": notificacion.get("proyecto_nombre"),
        "usuario_id": notificacion.get("usuario_id"),
        "leida": False,
        "fecha": datetime.now(timezone.utc).isoformat(),
        "link": notificacion.get("link"),
        "metadata": notificacion.get("metadata")
    }
    
    await db.notificaciones.insert_one(notif_data)
    return {"success": True, "notificacion": notif_data}


@api_router.put("/notificaciones/{notificacion_id}/leer")
async def marcar_como_leida(
    notificacion_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Marcar una notificación como leída"""
    result = await db.notificaciones.update_one(
        {"id": notificacion_id},
        {"$set": {"leida": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    return {"success": True, "mensaje": "Notificación marcada como leída"}


@api_router.put("/notificaciones/leer-todas")
async def marcar_todas_como_leidas(
    current_user: dict = Depends(get_current_user)
):
    """Marcar todas las notificaciones del usuario como leídas"""
    user_id = current_user.get("id")
    is_admin = current_user.get("rol") == "admin"
    
    if is_admin:
        query = {"$or": [{"usuario_id": None}, {"usuario_id": user_id}], "leida": False}
    else:
        query = {"usuario_id": user_id, "leida": False}
    
    result = await db.notificaciones.update_many(query, {"$set": {"leida": True}})
    
    return {"success": True, "notificaciones_actualizadas": result.modified_count}


@api_router.delete("/notificaciones/{notificacion_id}")
async def eliminar_notificacion(
    notificacion_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Eliminar una notificación"""
    result = await db.notificaciones.delete_one({"id": notificacion_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    
    return {"success": True, "mensaje": "Notificación eliminada"}


async def crear_notificacion_sistema(
    tipo: str,
    titulo: str,
    mensaje: str,
    proyecto_id: str = None,
    proyecto_nombre: str = None,
    usuario_id: str = None,
    link: str = None,
    metadata: dict = None
):
    """Función helper para crear notificaciones desde cualquier parte del sistema"""
    notif_data = {
        "id": str(uuid.uuid4()),
        "tipo": tipo,
        "titulo": titulo,
        "mensaje": mensaje,
        "proyecto_id": proyecto_id,
        "proyecto_nombre": proyecto_nombre,
        "usuario_id": usuario_id,
        "leida": False,
        "fecha": datetime.now(timezone.utc).isoformat(),
        "link": link,
        "metadata": metadata
    }
    
    await db.notificaciones.insert_one(notif_data)
    return notif_data

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
async def listar_proyectos(
    cliente_id: Optional[str] = None,
    current_user: dict = Depends(get_optional_user)
):
    """
    Listar proyectos. 
    - Si el usuario es 'client', solo muestra proyectos asignados a él.
    - Si el usuario es 'admin', muestra todos los proyectos.
    - Si se proporciona cliente_id explícito (admin), filtra por ese cliente.
    """
    query = {}
    
    # Si hay usuario autenticado y es cliente, filtrar automáticamente
    if current_user and current_user.get("rol") == "client":
        query = {"clientes_asignados": current_user.get("id")}
    elif cliente_id:
        # Admin puede filtrar por cliente específico
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
    """Crear un nuevo registro de vuelo (bitácora)"""
    vuelo_obj = Vuelo(**vuelo.model_dump())
    doc = vuelo_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
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
    """Actualizar un registro de vuelo existente"""
    update_data = {k: v for k, v in vuelo_update.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")
    
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
    
    # Si se actualizó el volumen de excavación o pilas/anclas, recalcular el avance del proyecto
    if any(key in update_data for key in ['volumen_excavacion', 'pilas_completadas', 'anclas_instaladas', 'muros_completados']):
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

# Sistema de subida por chunks para archivos grandes
@api_router.post("/proyectos/{proyecto_id}/avances-semanales/{avance_id}/modelo3d/init-upload")
async def iniciar_upload_modelo_3d(
    proyecto_id: str, 
    avance_id: str,
    filename: str,
    total_size: int,
    total_chunks: int
):
    """
    Inicia una subida de archivo grande por chunks.
    Retorna un upload_id para identificar la sesión de subida.
    """
    # Verificar que el avance existe
    avance = await db.avances_semanales.find_one({"id": avance_id, "proyecto_id": proyecto_id})
    if not avance:
        raise HTTPException(status_code=404, detail="Avance semanal no encontrado")
    
    # Verificar extensión del archivo
    file_extension = Path(filename).suffix.lower()
    allowed_extensions = ['.ply', '.xyz', '.pts', '.pcd']
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Formato no soportado. Use: {', '.join(allowed_extensions)}"
        )
    
    # Crear sesión de upload
    upload_id = str(uuid.uuid4())
    
    await db.uploads_temp.insert_one({
        "upload_id": upload_id,
        "proyecto_id": proyecto_id,
        "avance_id": avance_id,
        "filename": filename,
        "total_size": total_size,
        "total_chunks": total_chunks,
        "received_chunks": [],
        "chunk_ids": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "in_progress"
    })
    
    return {
        "upload_id": upload_id,
        "message": "Upload iniciado",
        "total_chunks": total_chunks
    }


@api_router.post("/proyectos/{proyecto_id}/avances-semanales/{avance_id}/modelo3d/upload-chunk")
async def subir_chunk_modelo_3d(
    proyecto_id: str,
    avance_id: str,
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    chunk: UploadFile = File(...)
):
    """
    Sube un chunk individual del archivo directamente a GridFS.
    """
    from services.storage import get_storage
    
    # Verificar sesión de upload
    upload_session = await db.uploads_temp.find_one({"upload_id": upload_id})
    if not upload_session:
        raise HTTPException(status_code=404, detail="Sesión de upload no encontrada")
    
    if upload_session.get("status") != "in_progress":
        raise HTTPException(status_code=400, detail="Upload ya completado o cancelado")
    
    try:
        # Leer chunk
        chunk_data = await chunk.read()
        
        # Guardar chunk directamente en GridFS
        storage = get_storage(db)
        chunk_filename = f"chunk_{upload_id}_{chunk_index}"
        chunk_gridfs_id = await storage.save_file(
            content=chunk_data,
            filename=chunk_filename,
            content_type="application/octet-stream",
            metadata={
                "upload_id": upload_id,
                "chunk_index": chunk_index,
                "is_chunk": True
            }
        )
        
        # Actualizar sesión con el ID del chunk en GridFS
        await db.uploads_temp.update_one(
            {"upload_id": upload_id},
            {
                "$push": {"received_chunks": chunk_index},
                "$set": {f"chunk_ids.{chunk_index}": chunk_gridfs_id}
            }
        )
        
        return {
            "success": True,
            "chunk_index": chunk_index,
            "chunk_size": len(chunk_data)
        }
        
    except Exception as e:
        logging.error(f"Error subiendo chunk {chunk_index}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/proyectos/{proyecto_id}/avances-semanales/{avance_id}/modelo3d/complete-upload")
async def completar_upload_modelo_3d(proyecto_id: str, avance_id: str, upload_id: str):
    """
    Completa la subida, ensamblando todos los chunks usando streaming directo a GridFS.
    Optimizado para archivos grandes sin cargar todo en memoria.
    """
    from services.storage import get_storage
    
    # Obtener sesión de upload
    upload_session = await db.uploads_temp.find_one({"upload_id": upload_id})
    if not upload_session:
        raise HTTPException(status_code=404, detail="Sesión de upload no encontrada")
    
    storage = get_storage(db)
    
    try:
        total_chunks = upload_session.get("total_chunks", 0)
        received_chunks = upload_session.get("received_chunks", [])
        chunk_ids = upload_session.get("chunk_ids", {})
        
        # Verificar que todos los chunks fueron recibidos
        if len(received_chunks) != total_chunks:
            missing = set(range(total_chunks)) - set(received_chunks)
            raise HTTPException(
                status_code=400, 
                detail=f"Faltan chunks: {missing}"
            )
        
        filename = upload_session.get("filename", "model.ply")
        file_extension = Path(filename).suffix.lower()
        unique_id = str(uuid.uuid4())
        unique_filename = f"{unique_id}{file_extension}"
        
        # Preparar lista ordenada de chunk IDs
        ordered_chunk_ids = [chunk_ids.get(str(i)) for i in range(total_chunks)]
        
        # Eliminar modelo anterior de GridFS si existe
        avance = await db.avances_semanales.find_one({"id": avance_id, "proyecto_id": proyecto_id})
        if avance:
            old_file_id = avance.get('modelo_3d_gridfs_id')
            if old_file_id:
                try:
                    await storage.delete_file(old_file_id)
                except Exception as e:
                    logging.warning(f"Error eliminando modelo anterior: {e}")
        
        # Ensamblar chunks usando streaming (más eficiente en memoria)
        logging.info(f"Ensamblando {total_chunks} chunks para upload {upload_id}")
        file_id, total_size = await storage.assemble_chunks_to_file(
            chunk_ids=ordered_chunk_ids,
            filename=unique_filename,
            content_type="application/octet-stream",
            metadata={
                "proyecto_id": proyecto_id,
                "avance_id": avance_id,
                "original_filename": filename,
                "extension": file_extension
            }
        )
        
        file_size_mb = round(total_size / (1024 * 1024), 2)
        model_url = f"/api/modelos3d/gridfs/{file_id}"
        preview_url = None
        preview_gridfs_id = None
        model_metadata = {"original_points": 0, "simplified": False}
        
        # Crear versión preview si el archivo es grande (>10MB)
        if total_size > 10 * 1024 * 1024:
            try:
                logging.info(f"Creando versión preview del modelo ({file_size_mb} MB)...")
                
                # Leer el archivo original desde GridFS
                original_content, _ = await storage.get_file(file_id)
                
                if original_content:
                    from services.model3d_processor import create_preview_ply
                    import asyncio
                    
                    # Crear preview en un thread separado para no bloquear
                    loop = asyncio.get_event_loop()
                    preview_content, model_metadata = await loop.run_in_executor(
                        None,
                        lambda: asyncio.run(create_preview_ply(original_content))
                    )
                    
                    if preview_content:
                        # Guardar la versión preview
                        preview_filename = f"preview_{unique_filename}"
                        preview_gridfs_id = await storage.save_file(
                            content=preview_content,
                            filename=preview_filename,
                            content_type="application/octet-stream",
                            metadata={
                                "proyecto_id": proyecto_id,
                                "avance_id": avance_id,
                                "is_preview": True,
                                "original_file_id": file_id,
                                **model_metadata
                            }
                        )
                        preview_url = f"/api/modelos3d/gridfs/{preview_gridfs_id}"
                        preview_size_mb = round(len(preview_content) / (1024 * 1024), 2)
                        logging.info(f"Preview creado: {preview_gridfs_id} ({preview_size_mb} MB, {model_metadata.get('preview_points', 0):,} puntos)")
            except Exception as e:
                logging.warning(f"Error creando preview (continuando sin preview): {e}")
        
        # Actualizar el avance
        update_data = {
            "modelo_3d_url": model_url,
            "modelo_3d_gridfs_id": file_id,
            "modelo_3d_filename": unique_filename,
            "modelo_3d_original_name": filename,
            "modelo_3d_tipo": "gridfs",
            "modelo_3d_size_mb": file_size_mb,
            "modelo_3d_points": model_metadata.get("original_points", 0)
        }
        
        if preview_url:
            update_data["modelo_3d_preview_url"] = preview_url
            update_data["modelo_3d_preview_id"] = preview_gridfs_id
            update_data["modelo_3d_preview_points"] = model_metadata.get("preview_points", 0)
        
        await db.avances_semanales.update_one(
            {"id": avance_id},
            {"$set": update_data}
        )
        
        # Eliminar chunks temporales de GridFS en background
        for chunk_id in ordered_chunk_ids:
            if chunk_id:
                try:
                    await storage.delete_file(chunk_id)
                except Exception as e:
                    logging.warning(f"Error eliminando chunk temporal {chunk_id}: {e}")
        
        # Limpiar sesión de upload
        await db.uploads_temp.delete_one({"upload_id": upload_id})
        
        logging.info(f"Modelo 3D guardado en GridFS: {file_id} ({file_size_mb} MB)")
        
        response_data = {
            "success": True,
            "url": model_url,
            "filename": unique_filename,
            "original_name": filename,
            "size_mb": file_size_mb,
            "gridfs_id": file_id,
            "points": model_metadata.get("original_points", 0)
        }
        
        if preview_url:
            response_data["preview_url"] = preview_url
            response_data["preview_gridfs_id"] = preview_gridfs_id
            response_data["preview_points"] = model_metadata.get("preview_points", 0)
            response_data["has_preview"] = True
        else:
            response_data["has_preview"] = False
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error completando upload: {e}")
        # Marcar como fallido
        await db.uploads_temp.update_one(
            {"upload_id": upload_id},
            {"$set": {"status": "failed", "error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint original para archivos pequeños (menos de 50MB)
@api_router.post("/proyectos/{proyecto_id}/avances-semanales/{avance_id}/modelo3d")
async def subir_modelo_3d(proyecto_id: str, avance_id: str, file: UploadFile = File(...)):
    """Subir un modelo 3D (nube de puntos PLY) a un avance semanal"""
    from services.storage import get_storage
    
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
    
    try:
        # Leer contenido del archivo
        content = await file.read()
        file_size = len(content)
        file_size_mb = round(file_size / (1024 * 1024), 2)
        
        # Generar nombre único
        unique_id = str(uuid.uuid4())
        unique_filename = f"{unique_id}{file_extension}"
        
        # Eliminar modelo anterior de GridFS si existe
        old_file_id = avance.get('modelo_3d_gridfs_id')
        if old_file_id:
            try:
                storage = get_storage(db)
                await storage.delete_file(old_file_id)
            except Exception as e:
                logging.warning(f"Error eliminando modelo anterior: {e}")
        
        # Guardar en GridFS
        storage = get_storage(db)
        file_id = await storage.save_file(
            content=content,
            filename=unique_filename,
            content_type="application/octet-stream",
            metadata={
                "proyecto_id": proyecto_id,
                "avance_id": avance_id,
                "original_filename": file.filename,
                "extension": file_extension,
                "size_bytes": file_size
            }
        )
        
        # Generar URL del modelo
        model_url = f"/api/modelos3d/gridfs/{file_id}"
        
        # Actualizar el avance con la referencia al archivo
        update_data = {
            "modelo_3d_url": model_url,
            "modelo_3d_gridfs_id": file_id,
            "modelo_3d_filename": unique_filename,
            "modelo_3d_original_name": file.filename,
            "modelo_3d_tipo": "gridfs",
            "modelo_3d_size_mb": file_size_mb
        }
        
        await db.avances_semanales.update_one(
            {"id": avance_id},
            {"$set": update_data}
        )
        
        logging.info(f"Modelo 3D guardado en GridFS: {file_id} ({file_size_mb} MB)")
        
        return {
            "url": model_url,
            "filename": unique_filename,
            "original_name": file.filename,
            "size_mb": file_size_mb,
            "tipo": "gridfs",
            "gridfs_id": file_id
        }
        
    except Exception as e:
        logging.error(f"Error subiendo modelo 3D: {e}")
        raise HTTPException(status_code=500, detail=f"Error al subir el modelo: {str(e)}")


@api_router.get("/modelos3d/gridfs/{file_id}")
async def obtener_modelo_3d_gridfs(file_id: str):
    """Obtener un modelo 3D desde GridFS usando streaming"""
    from services.storage import get_storage
    from bson import ObjectId
    
    try:
        storage = get_storage(db)
        
        # Verificar que el archivo existe consultando fs.files directamente
        try:
            file_doc = await db.fs.files.find_one({"_id": ObjectId(file_id)})
            if not file_doc:
                raise HTTPException(status_code=404, detail="Modelo no encontrado")
            
            metadata = file_doc.get("metadata", {}) or {}
            file_length = file_doc.get("length", 0)
        except Exception as e:
            logging.error(f"Error buscando archivo en GridFS: {e}")
            raise HTTPException(status_code=404, detail="Modelo no encontrado")
        
        # Determinar content-type
        extension = metadata.get("extension", ".ply")
        content_types = {
            '.ply': 'application/octet-stream',
            '.xyz': 'text/plain',
            '.pts': 'text/plain',
            '.pcd': 'application/octet-stream'
        }
        content_type = content_types.get(extension, 'application/octet-stream')
        filename = metadata.get("original_filename", "model.ply")
        
        # Crear generador de streaming desde GridFS
        async def stream_from_gridfs():
            grid_out = await storage.fs.open_download_stream(ObjectId(file_id))
            chunk_size = 1024 * 1024  # 1MB chunks for streaming
            while True:
                chunk = await grid_out.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        
        return StreamingResponse(
            stream_from_gridfs(),
            media_type=content_type,
            headers={
                "Content-Disposition": f"inline; filename={filename}",
                "Content-Length": str(file_length),
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error obteniendo modelo 3D de GridFS: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener el modelo")


@api_router.post("/proyectos/{proyecto_id}/avances-semanales/{avance_id}/modelo3d/generar-preview")
async def generar_preview_modelo_3d(proyecto_id: str, avance_id: str):
    """
    Genera una versión preview optimizada de un modelo 3D existente.
    Soporta tanto modelos en GridFS como modelos legacy en filesystem.
    """
    from services.storage import get_storage
    from services.model3d_processor import create_preview_ply
    import asyncio
    
    # Verificar que el avance existe y tiene modelo
    avance = await db.avances_semanales.find_one({"id": avance_id, "proyecto_id": proyecto_id})
    if not avance:
        raise HTTPException(status_code=404, detail="Avance no encontrado")
    
    # Verificar que tiene algún modelo 3D
    modelo_url = avance.get("modelo_3d_url")
    gridfs_id = avance.get("modelo_3d_gridfs_id")
    
    if not modelo_url and not gridfs_id:
        raise HTTPException(status_code=400, detail="Este avance no tiene modelo 3D")
    
    if avance.get("modelo_3d_preview_url"):
        return {
            "success": True,
            "message": "El modelo ya tiene una versión preview",
            "preview_url": avance["modelo_3d_preview_url"],
            "preview_points": avance.get("modelo_3d_preview_points", 0)
        }
    
    try:
        storage = get_storage(db)
        original_content = None
        
        # Intentar leer desde GridFS primero
        if gridfs_id:
            logging.info(f"Leyendo modelo desde GridFS: {gridfs_id}")
            original_content, _ = await storage.get_file(gridfs_id)
        
        # Si no hay GridFS, intentar leer desde filesystem (modelos legacy)
        if not original_content and modelo_url:
            # Extraer la ruta del archivo del URL
            if modelo_url.startswith("/api/modelos3d/") and "/gridfs/" not in modelo_url:
                # Es un modelo legacy en filesystem
                file_path = f"uploads/{modelo_url.replace('/api/modelos3d/', '')}"
                logging.info(f"Leyendo modelo desde filesystem: {file_path}")
                
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        original_content = f.read()
                else:
                    # Intentar ruta alternativa
                    alt_path = modelo_url.replace('/api/modelos3d/', 'uploads/')
                    if os.path.exists(alt_path):
                        with open(alt_path, 'rb') as f:
                            original_content = f.read()
        
        if not original_content:
            raise HTTPException(status_code=500, detail="No se pudo leer el modelo original. El archivo puede no existir en el servidor.")
        
        # Crear preview en un thread separado
        loop = asyncio.get_event_loop()
        preview_content, model_metadata = await loop.run_in_executor(
            None,
            lambda: asyncio.run(create_preview_ply(original_content))
        )
        
        if not preview_content:
            # No necesita preview o hubo error
            return {
                "success": True,
                "message": "El modelo no requiere simplificación",
                "original_points": model_metadata.get("original_points", 0),
                "simplified": False
            }
        
        # Guardar la versión preview
        original_filename = avance.get("modelo_3d_filename", "model.ply")
        preview_filename = f"preview_{original_filename}"
        preview_gridfs_id = await storage.save_file(
            content=preview_content,
            filename=preview_filename,
            content_type="application/octet-stream",
            metadata={
                "proyecto_id": proyecto_id,
                "avance_id": avance_id,
                "is_preview": True,
                "original_file_id": file_id,
                **model_metadata
            }
        )
        preview_url = f"/api/modelos3d/gridfs/{preview_gridfs_id}"
        
        # Actualizar el avance con la info del preview
        await db.avances_semanales.update_one(
            {"id": avance_id},
            {"$set": {
                "modelo_3d_preview_url": preview_url,
                "modelo_3d_preview_id": preview_gridfs_id,
                "modelo_3d_preview_points": model_metadata.get("preview_points", 0),
                "modelo_3d_points": model_metadata.get("original_points", 0)
            }}
        )
        
        preview_size_mb = round(len(preview_content) / (1024 * 1024), 2)
        logging.info(f"Preview generado: {preview_gridfs_id} ({preview_size_mb} MB)")
        
        return {
            "success": True,
            "message": "Preview generado exitosamente",
            "preview_url": preview_url,
            "preview_gridfs_id": preview_gridfs_id,
            "preview_points": model_metadata.get("preview_points", 0),
            "original_points": model_metadata.get("original_points", 0),
            "reduction_ratio": model_metadata.get("reduction_ratio", 1),
            "preview_size_mb": preview_size_mb
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error generando preview: {e}")
        raise HTTPException(status_code=500, detail=f"Error generando preview: {str(e)}")


# Mantener endpoint legacy para archivos ya guardados en filesystem
@api_router.get("/modelos3d/{proyecto_id}/{avance_id}/{filename}")
async def obtener_modelo_3d_legacy(proyecto_id: str, avance_id: str, filename: str):
    """Obtener un modelo 3D o thumbnail de un avance semanal"""
    file_path = UPLOAD_DIR / "modelos3d" / proyecto_id / avance_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    # Determinar el content-type basado en la extensión
    extension = Path(filename).suffix.lower()
    content_types = {
        '.ply': 'application/octet-stream',
        '.xyz': 'text/plain',
        '.pts': 'text/plain',
        '.pcd': 'application/octet-stream',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg'
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

@api_router.post("/proyectos/{proyecto_id}/avances-semanales/{avance_id}/regenerar-thumbnail")
async def regenerar_thumbnail(proyecto_id: str, avance_id: str):
    """Regenerar thumbnail para un modelo 3D existente"""
    avance = await db.avances_semanales.find_one({"id": avance_id, "proyecto_id": proyecto_id})
    if not avance:
        raise HTTPException(status_code=404, detail="Avance semanal no encontrado")
    
    model_url = avance.get('modelo_3d_url')
    if not model_url:
        raise HTTPException(status_code=400, detail="No hay modelo 3D para este avance")
    
    # Obtener la ruta del archivo PLY
    filename = model_url.split("/")[-1]
    models_dir = UPLOAD_DIR / "modelos3d" / proyecto_id / avance_id
    file_path = models_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo del modelo no encontrado")
    
    # Solo generar thumbnail para archivos PLY
    if not filename.lower().endswith('.ply'):
        raise HTTPException(status_code=400, detail="Solo se pueden generar thumbnails para archivos PLY")
    
    # Generar thumbnail
    unique_id = filename.replace('.ply', '').replace('.PLY', '')
    thumbnail_filename = f"{unique_id}_thumb.png"
    thumbnail_path = models_dir / thumbnail_filename
    
    success = await generate_thumbnail_async(str(file_path), str(thumbnail_path))
    
    if not success:
        raise HTTPException(status_code=500, detail="Error generando thumbnail")
    
    thumbnail_url = f"/api/modelos3d/{proyecto_id}/{avance_id}/{thumbnail_filename}"
    
    # Actualizar en la base de datos
    await db.avances_semanales.update_one(
        {"id": avance_id},
        {"$set": {"thumbnail_url": thumbnail_url}}
    )
    
    return {"thumbnail_url": thumbnail_url, "message": "Thumbnail regenerado exitosamente"}


# --- Comparación de Avances con IA ---
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType


@api_router.post("/proyectos/{proyecto_id}/comparar-avance")
async def comparar_avance_con_residente(
    proyecto_id: str,
    file: UploadFile = File(...)
):
    """
    Sube un PDF del reporte del residente de obra y lo compara con los datos del dron.
    Usa Gemini Vision para extraer las métricas del PDF y genera un análisis comparativo.
    """
    # Verificar que el proyecto existe
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Verificar que es un PDF
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")
    
    # Guardar el PDF
    pdfs_dir = UPLOAD_DIR / "reportes_residente" / proyecto_id
    pdfs_dir.mkdir(parents=True, exist_ok=True)
    
    unique_id = str(uuid.uuid4())
    pdf_filename = f"{unique_id}_{file.filename}"
    pdf_path = pdfs_dir / pdf_filename
    
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    pdf_url = f"/api/reportes-residente/{proyecto_id}/{pdf_filename}"
    
    # Obtener datos acumulados del dron (sistema)
    avances = await db.avances_semanales.find(
        {"proyecto_id": proyecto_id}, 
        {"_id": 0}
    ).to_list(100)
    
    # Calcular totales acumulados del sistema
    volumen_excavado_dron = sum((a.get('volumen_excavacion', 0) or 0) for a in avances)
    pilas_completadas_dron = sum((a.get('pilas_completadas', 0) or 0) for a in avances)
    anclas_instaladas_dron = sum((a.get('anclas_instaladas', 0) or 0) for a in avances)
    muros_completados_dron = sum((a.get('muros_completados', 0) or 0) for a in avances)
    
    # Obtener metas del proyecto
    volumen_total_planeado = proyecto.get('volumen_total_planeado', 0) or 0
    pilas_planeadas = proyecto.get('pilas_planeadas', 0) or 0
    anclas_planeadas = proyecto.get('anclas_planeadas', 0) or 0
    muros_planeados = proyecto.get('muros_planeados', 0) or 0
    
    # Calcular porcentajes de avance del dron
    avance_excavacion_dron = (volumen_excavado_dron / volumen_total_planeado * 100) if volumen_total_planeado > 0 else 0
    avance_pilas_dron = (pilas_completadas_dron / pilas_planeadas * 100) if pilas_planeadas > 0 else 0
    avance_anclas_dron = (anclas_instaladas_dron / anclas_planeadas * 100) if anclas_planeadas > 0 else 0
    avance_muros_dron = (muros_completados_dron / muros_planeados * 100) if muros_planeados > 0 else 0
    
    metricas_dron = {
        "volumen_excavado": volumen_excavado_dron,
        "volumen_planeado": volumen_total_planeado,
        "avance_excavacion_pct": round(avance_excavacion_dron, 2),
        "pilas_completadas": pilas_completadas_dron,
        "pilas_planeadas": pilas_planeadas,
        "avance_pilas_pct": round(avance_pilas_dron, 2),
        "anclas_instaladas": anclas_instaladas_dron,
        "anclas_planeadas": anclas_planeadas,
        "avance_anclas_pct": round(avance_anclas_dron, 2),
        "muros_completados": muros_completados_dron,
        "muros_planeados": muros_planeados,
        "avance_muros_pct": round(avance_muros_dron, 2),
        "semanas_registradas": len(avances)
    }
    
    # Analizar el PDF con Gemini
    try:
        emergent_key = os.environ.get('EMERGENT_LLM_KEY')
        if not emergent_key:
            raise HTTPException(status_code=500, detail="EMERGENT_LLM_KEY no configurada")
        
        chat = LlmChat(
            api_key=emergent_key,
            session_id=f"comparacion-{proyecto_id}-{unique_id}",
            system_message="""Eres un experto en análisis de reportes de avance de construcción.
Tu tarea es extraer las métricas de avance del PDF del residente de obra y compararlas con los datos del dron.

IMPORTANTE: Debes responder ÚNICAMENTE en formato JSON válido, sin texto adicional.
El JSON debe tener esta estructura exacta:
{
    "metricas_extraidas": {
        "excavacion_m3": número o null,
        "excavacion_porcentaje": número o null,
        "pilas_perforadas": número o null,
        "pilas_porcentaje": número o null,
        "anclas_tensadas": número o null,
        "anclas_porcentaje": número o null,
        "muros_m2": número o null,
        "muros_porcentaje": número o null,
        "avance_general_porcentaje": número o null
    },
    "discrepancias": ["lista de discrepancias encontradas"],
    "analisis": "análisis detallado de la comparación",
    "recomendaciones": ["lista de recomendaciones"],
    "confianza": "ALTA" | "MEDIA" | "BAJA"
}"""
        ).with_model("gemini", "gemini-2.5-flash")
        
        pdf_file = FileContentWithMimeType(
            file_path=str(pdf_path),
            mime_type="application/pdf"
        )
        
        prompt = f"""Analiza el PDF adjunto que es un reporte de avance de obra del residente.

DATOS DEL SISTEMA DE DRONES (referencia para comparar):
- Excavación: {volumen_excavado_dron:,.2f} m³ ejecutados de {volumen_total_planeado:,.2f} m³ planeados ({avance_excavacion_dron:.1f}%)
- Pilas: {pilas_completadas_dron} ejecutadas de {pilas_planeadas} planeadas ({avance_pilas_dron:.1f}%)
- Anclas: {anclas_instaladas_dron} instaladas de {anclas_planeadas} planeadas ({avance_anclas_dron:.1f}%)
- Muros: {muros_completados_dron} completados de {muros_planeados} planeados ({avance_muros_dron:.1f}%)

Extrae las métricas del PDF y compáralas con los datos del dron.
Identifica discrepancias significativas (diferencias > 5%) y explica posibles razones.
Responde SOLO con el JSON especificado, sin texto adicional."""
        
        user_message = UserMessage(
            text=prompt,
            file_contents=[pdf_file]
        )
        
        response = await chat.send_message(user_message)
        
        # Parsear respuesta JSON
        import json
        # Limpiar la respuesta (quitar posibles marcadores de código)
        response_clean = response.strip()
        if response_clean.startswith("```json"):
            response_clean = response_clean[7:]
        if response_clean.startswith("```"):
            response_clean = response_clean[3:]
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]
        response_clean = response_clean.strip()
        
        analisis_ia = json.loads(response_clean)
        
        metricas_residente = analisis_ia.get("metricas_extraidas", {})
        
        # Crear comparaciones detalladas
        comparaciones = []
        
        # Excavación
        if metricas_residente.get("excavacion_m3") is not None:
            diff = metricas_residente["excavacion_m3"] - volumen_excavado_dron
            diff_pct = (diff / volumen_excavado_dron * 100) if volumen_excavado_dron > 0 else 0
            estado = "coincide" if abs(diff_pct) < 5 else ("discrepancia_menor" if abs(diff_pct) < 15 else "discrepancia_mayor")
            comparaciones.append({
                "nombre": "Excavación",
                "unidad": "m³",
                "valor_dron": volumen_excavado_dron,
                "valor_residente": metricas_residente["excavacion_m3"],
                "diferencia": round(diff, 2),
                "diferencia_porcentaje": round(diff_pct, 2),
                "estado": estado
            })
        
        # Pilas
        if metricas_residente.get("pilas_perforadas") is not None:
            diff = metricas_residente["pilas_perforadas"] - pilas_completadas_dron
            diff_pct = (diff / pilas_completadas_dron * 100) if pilas_completadas_dron > 0 else 0
            estado = "coincide" if abs(diff_pct) < 5 else ("discrepancia_menor" if abs(diff_pct) < 15 else "discrepancia_mayor")
            comparaciones.append({
                "nombre": "Pilas Perforadas",
                "unidad": "pzas",
                "valor_dron": pilas_completadas_dron,
                "valor_residente": metricas_residente["pilas_perforadas"],
                "diferencia": round(diff, 2),
                "diferencia_porcentaje": round(diff_pct, 2),
                "estado": estado
            })
        
        # Anclas
        if metricas_residente.get("anclas_tensadas") is not None:
            diff = metricas_residente["anclas_tensadas"] - anclas_instaladas_dron
            diff_pct = (diff / anclas_instaladas_dron * 100) if anclas_instaladas_dron > 0 else 0
            estado = "coincide" if abs(diff_pct) < 5 else ("discrepancia_menor" if abs(diff_pct) < 15 else "discrepancia_mayor")
            comparaciones.append({
                "nombre": "Anclas Tensadas",
                "unidad": "pzas",
                "valor_dron": anclas_instaladas_dron,
                "valor_residente": metricas_residente["anclas_tensadas"],
                "diferencia": round(diff, 2),
                "diferencia_porcentaje": round(diff_pct, 2),
                "estado": estado
            })
        
        # Muros
        if metricas_residente.get("muros_m2") is not None:
            diff = metricas_residente["muros_m2"] - muros_completados_dron
            diff_pct = (diff / muros_completados_dron * 100) if muros_completados_dron > 0 else 0
            estado = "coincide" if abs(diff_pct) < 5 else ("discrepancia_menor" if abs(diff_pct) < 15 else "discrepancia_mayor")
            comparaciones.append({
                "nombre": "Muros/Lanzado",
                "unidad": "m²",
                "valor_dron": muros_completados_dron,
                "valor_residente": metricas_residente["muros_m2"],
                "diferencia": round(diff, 2),
                "diferencia_porcentaje": round(diff_pct, 2),
                "estado": estado
            })
        
        # Crear registro de comparación
        comparacion = {
            "id": unique_id,
            "proyecto_id": proyecto_id,
            "semana": len(avances),
            "fecha_comparacion": datetime.now(timezone.utc).isoformat(),
            "pdf_url": pdf_url,
            "pdf_nombre": file.filename,
            "metricas_residente": metricas_residente,
            "metricas_dron": metricas_dron,
            "comparaciones": comparaciones,
            "resumen_ia": analisis_ia.get("analisis", ""),
            "discrepancias_detectadas": analisis_ia.get("discrepancias", []),
            "recomendaciones": analisis_ia.get("recomendaciones", []),
            "estado_comparacion": "analizado",
            "avance_general_residente": metricas_residente.get("avance_general_porcentaje", 0) or 0,
            "avance_general_dron": proyecto.get('avance_actual', 0) or 0,
            "confianza": analisis_ia.get("confianza", "MEDIA")
        }
        
        # Guardar en la base de datos
        await db.comparaciones_avance.insert_one(comparacion)
        
        # Eliminar _id de MongoDB para la respuesta
        comparacion.pop('_id', None)
        
        # Verificar si hay discrepancias críticas (>15%) y enviar alerta
        discrepancias_criticas = [c for c in comparaciones if c.get("estado") == "discrepancia_mayor"]
        if discrepancias_criticas and ADMIN_EMAIL and resend.api_key:
            try:
                await enviar_alerta_discrepancia(
                    proyecto_nombre=proyecto.get("nombre", "Proyecto"),
                    proyecto_id=proyecto_id,
                    discrepancias=discrepancias_criticas,
                    resumen_ia=analisis_ia.get("analisis", ""),
                    pdf_nombre=file.filename
                )
                comparacion["alerta_enviada"] = True
                logging.info(f"Alerta de discrepancia enviada para proyecto {proyecto_id}")
            except Exception as email_err:
                logging.error(f"Error enviando alerta de discrepancia: {email_err}")
                comparacion["alerta_enviada"] = False
        
        return comparacion
        
    except json.JSONDecodeError as e:
        logging.error(f"Error parseando respuesta de IA: {e}")
        logging.error(f"Respuesta recibida: {response}")
        raise HTTPException(status_code=500, detail=f"Error procesando respuesta de IA: {str(e)}")
    except Exception as e:
        logging.error(f"Error en análisis de PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error analizando PDF: {str(e)}")


@api_router.get("/proyectos/{proyecto_id}/comparaciones")
async def obtener_comparaciones(proyecto_id: str):
    """Obtener historial de comparaciones de un proyecto"""
    comparaciones = await db.comparaciones_avance.find(
        {"proyecto_id": proyecto_id},
        {"_id": 0}
    ).sort("fecha_comparacion", -1).to_list(50)
    
    return comparaciones


@api_router.get("/reportes-residente/{proyecto_id}/{filename}")
async def obtener_reporte_residente(proyecto_id: str, filename: str):
    """Obtener un PDF de reporte del residente"""
    file_path = UPLOAD_DIR / "reportes_residente" / proyecto_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Content-Disposition": f"inline; filename={filename}"
        }
    )


@api_router.delete("/proyectos/{proyecto_id}/comparaciones/{comparacion_id}")
async def eliminar_comparacion(proyecto_id: str, comparacion_id: str):
    """Eliminar una comparación de avance"""
    # Obtener la comparación para eliminar el PDF
    comparacion = await db.comparaciones_avance.find_one({
        "id": comparacion_id,
        "proyecto_id": proyecto_id
    })
    
    if not comparacion:
        raise HTTPException(status_code=404, detail="Comparación no encontrada")
    
    # Eliminar el PDF si existe
    pdf_url = comparacion.get("pdf_url", "")
    if pdf_url:
        try:
            filename = pdf_url.split("/")[-1]
            file_path = UPLOAD_DIR / "reportes_residente" / proyecto_id / filename
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logging.error(f"Error eliminando PDF: {e}")
    
    # Eliminar de la base de datos
    await db.comparaciones_avance.delete_one({
        "id": comparacion_id,
        "proyecto_id": proyecto_id
    })
    
    return {"message": "Comparación eliminada"}


# --- Endpoint para enviar reporte semanal manualmente ---
@api_router.post("/admin/enviar-reporte-semanal")
async def enviar_reporte_semanal_manual(current_user: dict = Depends(get_current_admin)):
    """
    Envía el reporte semanal manualmente (solo admin).
    Útil para testing o para enviar reportes fuera del horario programado.
    """
    try:
        await generar_reporte_semanal()
        return {
            "success": True,
            "message": f"Reporte semanal enviado a {ADMIN_EMAIL}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enviando reporte: {str(e)}")


# --- Exportación de Métricas Históricas ---
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows

@api_router.get("/exportar/metricas-excel")
async def exportar_metricas_excel():
    """
    Exporta las métricas históricas de todos los proyectos a Excel.
    Incluye hojas separadas para: Resumen, Detalle por Proyecto, y Avances Semanales.
    """
    try:
        # Obtener todos los proyectos
        proyectos = await db.proyectos.find({}, {"_id": 0}).to_list(100)
        
        # Crear workbook
        wb = Workbook()
        
        # Estilos
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="994B49", end_color="994B49", fill_type="solid")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # --- Hoja 1: Resumen General ---
        ws_resumen = wb.active
        ws_resumen.title = "Resumen General"
        
        # Headers
        headers_resumen = ["Proyecto", "Ubicación", "Avance %", "Excavación (m³)", "Vol. Planeado (m³)", 
                         "Pilas", "Pilas Plan.", "Anclas", "Anclas Plan.", "Muros", "Muros Plan.", 
                         "Costo Flotilla", "Semanas"]
        
        for col, header in enumerate(headers_resumen, 1):
            cell = ws_resumen.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = border
        
        # Datos de proyectos
        total_volumen = 0
        total_pilas = 0
        total_anclas = 0
        total_muros = 0
        total_costo = 0
        
        for row_num, proyecto in enumerate(proyectos, 2):
            proyecto_id = proyecto.get('id')
            
            # Obtener avances
            avances = await db.avances_semanales.find(
                {"proyecto_id": proyecto_id}, {"_id": 0}
            ).to_list(100)
            
            volumen = sum((a.get('volumen_excavacion', 0) or 0) for a in avances)
            pilas = sum((a.get('pilas_completadas', 0) or 0) for a in avances)
            anclas = sum((a.get('anclas_instaladas', 0) or 0) for a in avances)
            muros = sum((a.get('muros_completados', 0) or 0) for a in avances)
            costo = volumen * (proyecto.get('costo_m3', 150) or 150)
            
            total_volumen += volumen
            total_pilas += pilas
            total_anclas += anclas
            total_muros += muros
            total_costo += costo
            
            row_data = [
                proyecto.get('nombre', ''),
                proyecto.get('ubicacion', ''),
                proyecto.get('avance_actual', 0) or 0,
                volumen,
                proyecto.get('volumen_total_planeado', 0) or 0,
                pilas,
                proyecto.get('pilas_planeadas', 0) or 0,
                anclas,
                proyecto.get('anclas_planeadas', 0) or 0,
                muros,
                proyecto.get('muros_planeados', 0) or 0,
                costo,
                len(avances)
            ]
            
            for col, value in enumerate(row_data, 1):
                cell = ws_resumen.cell(row=row_num, column=col, value=value)
                cell.border = border
                if col == 3:  # Avance %
                    cell.number_format = '0.0%'
                    cell.value = value / 100
                elif col in [12]:  # Costo
                    cell.number_format = '$#,##0.00'
        
        # Fila de totales
        total_row = len(proyectos) + 2
        ws_resumen.cell(row=total_row, column=1, value="TOTALES").font = Font(bold=True)
        ws_resumen.cell(row=total_row, column=4, value=total_volumen).font = Font(bold=True)
        ws_resumen.cell(row=total_row, column=6, value=total_pilas).font = Font(bold=True)
        ws_resumen.cell(row=total_row, column=8, value=total_anclas).font = Font(bold=True)
        ws_resumen.cell(row=total_row, column=10, value=total_muros).font = Font(bold=True)
        ws_resumen.cell(row=total_row, column=12, value=total_costo).number_format = '$#,##0.00'
        
        # Ajustar anchos
        for col in ws_resumen.columns:
            max_length = max(len(str(cell.value or '')) for cell in col)
            ws_resumen.column_dimensions[col[0].column_letter].width = min(max_length + 2, 20)
        
        # --- Hoja 2: Avances Semanales ---
        ws_avances = wb.create_sheet("Avances Semanales")
        
        headers_avances = ["Proyecto", "Semana", "Fecha", "Volumen (m³)", "Pilas", "Anclas", "Muros", "Descripción"]
        for col, header in enumerate(headers_avances, 1):
            cell = ws_avances.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = border
        
        row_num = 2
        for proyecto in proyectos:
            proyecto_id = proyecto.get('id')
            proyecto_nombre = proyecto.get('nombre', '')
            
            avances = await db.avances_semanales.find(
                {"proyecto_id": proyecto_id}, {"_id": 0}
            ).sort("semana", 1).to_list(100)
            
            for avance in avances:
                row_data = [
                    proyecto_nombre,
                    avance.get('semana', 0),
                    avance.get('fecha', ''),
                    avance.get('volumen_excavacion', 0) or 0,
                    avance.get('pilas_completadas', 0) or 0,
                    avance.get('anclas_instaladas', 0) or 0,
                    avance.get('muros_completados', 0) or 0,
                    avance.get('descripcion', '')
                ]
                
                for col, value in enumerate(row_data, 1):
                    cell = ws_avances.cell(row=row_num, column=col, value=value)
                    cell.border = border
                
                row_num += 1
        
        # Ajustar anchos
        for col in ws_avances.columns:
            max_length = max(len(str(cell.value or '')) for cell in col)
            ws_avances.column_dimensions[col[0].column_letter].width = min(max_length + 2, 25)
        
        # --- Hoja 3: Comparaciones con Residente ---
        ws_comparaciones = wb.create_sheet("Comparaciones Residente")
        
        headers_comp = ["Proyecto", "Fecha", "PDF", "Avance Dron %", "Avance Residente %", 
                       "Discrepancias", "Alerta Enviada"]
        for col, header in enumerate(headers_comp, 1):
            cell = ws_comparaciones.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = border
        
        comparaciones = await db.comparaciones_avance.find({}, {"_id": 0}).to_list(200)
        
        for row_num, comp in enumerate(comparaciones, 2):
            proyecto = next((p for p in proyectos if p.get('id') == comp.get('proyecto_id')), {})
            row_data = [
                proyecto.get('nombre', 'Desconocido'),
                comp.get('fecha_comparacion', '')[:10] if comp.get('fecha_comparacion') else '',
                comp.get('pdf_nombre', ''),
                comp.get('avance_general_dron', 0),
                comp.get('avance_general_residente', 0),
                len(comp.get('discrepancias_detectadas', [])),
                'Sí' if comp.get('alerta_enviada') else 'No'
            ]
            
            for col, value in enumerate(row_data, 1):
                cell = ws_comparaciones.cell(row=row_num, column=col, value=value)
                cell.border = border
        
        # Guardar a buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        fecha_actual = datetime.now(timezone.utc).strftime('%Y%m%d')
        filename = f"DrON_Metricas_Historicas_{fecha_actual}.xlsx"
        
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except Exception as e:
        logging.error(f"Error exportando a Excel: {e}")
        raise HTTPException(status_code=500, detail=f"Error generando Excel: {str(e)}")


@api_router.get("/exportar/metricas-pdf")
async def exportar_metricas_pdf():
    """
    Exporta las métricas históricas de todos los proyectos a PDF.
    Incluye resumen ejecutivo, gráficos y tablas detalladas.
    """
    try:
        # Obtener todos los proyectos
        proyectos = await db.proyectos.find({}, {"_id": 0}).to_list(100)
        
        # Calcular totales
        total_volumen = 0
        total_pilas = 0
        total_anclas = 0
        total_muros = 0
        total_costo = 0
        proyectos_data = []
        
        for proyecto in proyectos:
            proyecto_id = proyecto.get('id')
            
            avances = await db.avances_semanales.find(
                {"proyecto_id": proyecto_id}, {"_id": 0}
            ).to_list(100)
            
            volumen = sum((a.get('volumen_excavacion', 0) or 0) for a in avances)
            pilas = sum((a.get('pilas_completadas', 0) or 0) for a in avances)
            anclas = sum((a.get('anclas_instaladas', 0) or 0) for a in avances)
            muros = sum((a.get('muros_completados', 0) or 0) for a in avances)
            costo = volumen * (proyecto.get('costo_m3', 150) or 150)
            
            total_volumen += volumen
            total_pilas += pilas
            total_anclas += anclas
            total_muros += muros
            total_costo += costo
            
            proyectos_data.append({
                'nombre': proyecto.get('nombre', ''),
                'ubicacion': proyecto.get('ubicacion', ''),
                'avance': proyecto.get('avance_actual', 0) or 0,
                'volumen': volumen,
                'volumen_plan': proyecto.get('volumen_total_planeado', 0) or 0,
                'pilas': pilas,
                'pilas_plan': proyecto.get('pilas_planeadas', 0) or 0,
                'anclas': anclas,
                'anclas_plan': proyecto.get('anclas_planeadas', 0) or 0,
                'muros': muros,
                'muros_plan': proyecto.get('muros_planeados', 0) or 0,
                'costo': costo,
                'semanas': len(avances)
            })
        
        # Crear PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        styles = getSampleStyleSheet()
        
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
            textColor=colors.HexColor('#994B49'),
            spaceBefore=20,
            spaceAfter=10
        )
        
        story = []
        
        # Título
        story.append(Paragraph("📊 Reporte de Métricas Históricas", title_style))
        story.append(Paragraph(f"DrON Topografía - {datetime.now(timezone.utc).strftime('%d/%m/%Y')}", 
                              ParagraphStyle('Date', parent=styles['Normal'], alignment=TA_CENTER, textColor=colors.gray)))
        story.append(Spacer(1, 30))
        
        # KPIs Resumen
        story.append(Paragraph("Resumen Ejecutivo", subtitle_style))
        
        kpi_data = [
            ["Métrica", "Total"],
            ["Proyectos Activos", str(len(proyectos))],
            ["Excavación Total", f"{total_volumen:,.0f} m³"],
            ["Pilas Completadas", f"{total_pilas:,}"],
            ["Anclas Instaladas", f"{total_anclas:,}"],
            ["Muros Construidos", f"{total_muros:,}"],
            ["Inversión Flotillas", f"${total_costo:,.2f}"]
        ]
        
        kpi_table = Table(kpi_data, colWidths=[200, 150])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#994B49')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FDF2F2')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#994B49')),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 30))
        
        # Tabla de proyectos
        story.append(Paragraph("Detalle por Proyecto", subtitle_style))
        
        proj_headers = ["Proyecto", "Avance", "Excavación", "Pilas", "Anclas", "Muros"]
        proj_data = [proj_headers]
        
        for p in proyectos_data:
            proj_data.append([
                p['nombre'][:20] + '...' if len(p['nombre']) > 20 else p['nombre'],
                f"{p['avance']:.1f}%",
                f"{p['volumen']:,.0f} m³",
                f"{p['pilas']}/{p['pilas_plan']}",
                f"{p['anclas']}/{p['anclas_plan']}",
                f"{p['muros']}/{p['muros_plan']}"
            ])
        
        proj_table = Table(proj_data, colWidths=[120, 60, 80, 60, 60, 60])
        proj_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#994B49')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
        ]))
        story.append(proj_table)
        story.append(Spacer(1, 30))
        
        # Costos de Flotilla
        story.append(Paragraph("Desglose de Costos de Flotilla", subtitle_style))
        
        costo_headers = ["Proyecto", "Volumen", "Viajes Est.", "Costo Total"]
        costo_data = [costo_headers]
        
        for p in proyectos_data:
            viajes = int(p['volumen'] / 25) if p['volumen'] > 0 else 0
            costo_data.append([
                p['nombre'][:25] + '...' if len(p['nombre']) > 25 else p['nombre'],
                f"{p['volumen']:,.0f} m³",
                f"{viajes:,}",
                f"${p['costo']:,.2f}"
            ])
        
        # Fila de totales
        costo_data.append([
            "TOTAL",
            f"{total_volumen:,.0f} m³",
            "-",
            f"${total_costo:,.2f}"
        ])
        
        costo_table = Table(costo_data, colWidths=[150, 100, 80, 100])
        costo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#994B49')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FEE2E2')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        story.append(costo_table)
        
        # Footer
        story.append(Spacer(1, 40))
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.gray, alignment=TA_CENTER)
        story.append(Paragraph(f"Generado por DrON Topografía - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC", footer_style))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        fecha_actual = datetime.now(timezone.utc).strftime('%Y%m%d')
        filename = f"DrON_Metricas_Historicas_{fecha_actual}.pdf"
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except Exception as e:
        logging.error(f"Error exportando a PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")


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
async def obtener_estadisticas(current_user: dict = Depends(get_optional_user)):
    """
    Obtiene estadísticas generales.
    - Para clientes: Solo estadísticas de sus proyectos asignados
    - Para admins: Estadísticas de todos los proyectos
    """
    query = {}
    
    # Si es cliente, filtrar solo sus proyectos
    if current_user and current_user.get("rol") == "client":
        query = {"clientes_asignados": current_user.get("id")}
    
    total_proyectos = await db.proyectos.count_documents(query)
    
    # Obtener IDs de proyectos filtrados
    proyectos = await db.proyectos.find(query, {"id": 1, "avance_actual": 1, "_id": 0}).to_list(1000)
    proyecto_ids = [p.get("id") for p in proyectos]
    
    # Contar vuelos solo de esos proyectos
    if proyecto_ids:
        vuelos_query = {"proyecto_id": {"$in": proyecto_ids}}
    else:
        vuelos_query = {} if not query else {"proyecto_id": {"$in": []}}
    
    total_vuelos = await db.vuelos.count_documents(vuelos_query)
    
    # Calcular avance promedio
    avance_promedio = sum(p.get('avance_actual', 0) for p in proyectos) / max(total_proyectos, 1)
    
    # Volumetría total
    vuelos = await db.vuelos.find(vuelos_query, {"volumetria": 1, "_id": 0}).to_list(1000)
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

# --- Cronograma y Frentes ---
@api_router.post("/proyectos/importar-cronograma")
async def importar_cronograma(file: UploadFile = File(...)):
    """
    Importa un archivo Excel con el cronograma del proyecto.
    Parsea automáticamente los frentes y actividades.
    """
    from services.cronograma_ai import parse_excel_cronograma
    
    # Verificar extensión
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)")
    
    # Leer contenido
    content = await file.read()
    
    # Parsear cronograma
    resultado = parse_excel_cronograma(content)
    
    if not resultado.get("success"):
        raise HTTPException(status_code=400, detail=resultado.get("error", "Error parseando archivo"))
    
    return resultado


@api_router.get("/plantilla-cronograma")
async def descargar_plantilla_cronograma():
    """Descarga la plantilla de Excel para cronogramas"""
    plantilla_path = UPLOAD_DIR / "plantilla_cronograma.xlsx"
    if not plantilla_path.exists():
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    
    return FileResponse(
        plantilla_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="plantilla_cronograma_dron.xlsx"
    )


@api_router.post("/proyectos/crear-desde-cronograma")
async def crear_proyecto_desde_cronograma(data: dict):
    """
    Crea un proyecto completo a partir de datos de cronograma parseados.
    """
    try:
        # Crear proyecto
        proyecto_id = str(uuid.uuid4())
        resumen = data.get("resumen", {})
        
        proyecto = {
            "id": proyecto_id,
            "nombre": data.get("nombre", "Nuevo Proyecto"),
            "ubicacion": data.get("ubicacion", ""),
            "direccion": data.get("direccion", ""),
            "coordenadas": data.get("coordenadas", {"lat": 0, "lng": 0}),
            "fecha_inicio": resumen.get("fecha_inicio", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            "fecha_fin_planeada": resumen.get("fecha_fin", ""),
            "avance_actual": 0.0,
            # Tipos de actividades detectadas
            "actividades_tipo": resumen.get("tipos_actividades", ["pilas"]),
            # Métricas planeadas
            "volumen_total_planeado": resumen.get("total_excavacion", 0),
            "pilas_planeadas": resumen.get("total_pilas", 0),
            "muros_planeados": resumen.get("total_muros", 0),
            "anclas_planeadas": resumen.get("total_anclas", 0),
            # Métricas ejecutadas (inician en 0)
            "volumen_ejecutado": 0,
            "pilas_ejecutadas": 0,
            "muros_ejecutados": 0,
            "anclas_ejecutadas": 0,
            # Cronograma
            "semanas_planeadas": resumen.get("semanas_estimadas", 0),
            "semanas_excavacion": resumen.get("semanas_excavacion", 0),
            "semanas_pilas": resumen.get("semanas_pilas", 0),
            "semanas_muros": resumen.get("semanas_muros", 0),
            "descripcion": data.get("descripcion", ""),
            "capacidad_camion": 25.0,
            "costo_m3": 150.0,
            "clientes_asignados": [],
            "created_at": datetime.now(timezone.utc)
        }
        
        await db.proyectos.insert_one(proyecto)
        
        # Crear frentes
        frentes_data = data.get("frentes", [])
        for idx, frente_data in enumerate(frentes_data):
            frente = {
                "id": str(uuid.uuid4()),
                "proyecto_id": proyecto_id,
                "nombre": frente_data.get("nombre", f"Frente {idx + 1}"),
                "descripcion": frente_data.get("descripcion", ""),
                "actividades": frente_data.get("actividades", []),
                "orden": idx + 1,
                "created_at": datetime.now(timezone.utc)
            }
            await db.frentes.insert_one(frente)
        
        # Crear avances semanales vacíos para cada semana planeada
        semanas = resumen.get("semanas_estimadas", 12)
        fecha_inicio = datetime.strptime(resumen.get("fecha_inicio", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d")
        
        for semana in range(1, semanas + 1):
            fecha_semana = fecha_inicio + timedelta(weeks=semana - 1)
            avance = {
                "id": str(uuid.uuid4()),
                "proyecto_id": proyecto_id,
                "semana": semana,
                "fecha": fecha_semana.strftime("%Y-%m-%d"),
                "descripcion": f"Semana {semana}",
                "volumen_excavacion": 0,
                "pilas_planeadas": 0,
                "pilas_completadas": 0,
                "anclas_planeadas": 0,
                "anclas_instaladas": 0,
                "imagenes": [],
                "created_at": datetime.now(timezone.utc)
            }
            await db.avances_semanales.insert_one(avance)
        
        return {
            "success": True,
            "proyecto_id": proyecto_id,
            "mensaje": f"Proyecto creado con {len(frentes_data)} frentes y {semanas} semanas de avance"
        }
        
    except Exception as e:
        logging.error(f"Error creando proyecto desde cronograma: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/proyectos/{proyecto_id}/actualizar-cronograma")
async def actualizar_cronograma_proyecto(proyecto_id: str, file: UploadFile = File(...)):
    """
    Actualiza el cronograma de un proyecto existente desde un archivo Excel.
    Permite subir o actualizar el programa de obra.
    """
    from services.cronograma_ai import parse_excel_cronograma
    
    # Verificar que el proyecto existe
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Validar tipo de archivo
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos Excel (.xlsx, .xls)")
    
    try:
        content = await file.read()
        
        # Parsear cronograma
        resultado = parse_excel_cronograma(content)
        
        if resultado.get("error"):
            raise HTTPException(status_code=400, detail=resultado["error"])
        
        resumen = resultado.get("resumen", {})
        frentes_data = resultado.get("frentes", [])
        
        # Actualizar datos del proyecto con el nuevo cronograma
        update_data = {
            "cronograma_archivo": file.filename,
            "cronograma_fecha_carga": datetime.now(timezone.utc).isoformat(),
            "actividades_tipo": resumen.get("tipos_actividades", proyecto.get("actividades_tipo", [])),
            "semanas_planeadas": resumen.get("semanas_estimadas", proyecto.get("semanas_planeadas", 0)),
            "semanas_excavacion": resumen.get("semanas_excavacion", 0),
            "semanas_pilas": resumen.get("semanas_pilas", 0),
            "semanas_muros": resumen.get("semanas_muros", 0),
            "cronograma_resumen": resumen,
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Actualizar métricas planeadas si vienen en el cronograma
        if resumen.get("total_pilas", 0) > 0:
            update_data["pilas_planeadas"] = resumen["total_pilas"]
        if resumen.get("total_anclas", 0) > 0:
            update_data["anclas_planeadas"] = resumen["total_anclas"]
        if resumen.get("total_muros", 0) > 0:
            update_data["muros_planeados"] = resumen["total_muros"]
        if resumen.get("total_excavacion", 0) > 0:
            update_data["volumen_total_planeado"] = resumen["total_excavacion"]
        
        # Actualizar fechas si vienen en el cronograma y tienen sentido
        if resumen.get("fecha_inicio"):
            update_data["fecha_inicio"] = resumen["fecha_inicio"]
        if resumen.get("fecha_fin"):
            update_data["fecha_fin_planeada"] = resumen["fecha_fin"]
        
        await db.proyectos.update_one({"id": proyecto_id}, {"$set": update_data})
        
        # Eliminar frentes anteriores y crear nuevos
        await db.frentes.delete_many({"proyecto_id": proyecto_id})
        
        for idx, frente_data in enumerate(frentes_data):
            frente = {
                "id": str(uuid.uuid4()),
                "proyecto_id": proyecto_id,
                "nombre": frente_data.get("nombre", f"Frente {idx + 1}"),
                "descripcion": frente_data.get("descripcion", ""),
                "actividades": frente_data.get("actividades", []),
                "orden": idx + 1,
                "created_at": datetime.now(timezone.utc)
            }
            await db.frentes.insert_one(frente)
        
        return {
            "success": True,
            "mensaje": f"Cronograma actualizado: {len(frentes_data)} frentes, {resumen.get('semanas_estimadas', 0)} semanas",
            "resumen": resumen,
            "frentes_creados": len(frentes_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error actualizando cronograma: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error procesando archivo: {str(e)}")


@api_router.get("/proyectos/{proyecto_id}/cronograma")
async def obtener_cronograma_proyecto(proyecto_id: str):
    """Obtiene información del cronograma cargado para un proyecto"""
    proyecto = await db.proyectos.find_one(
        {"id": proyecto_id}, 
        {"_id": 0, "cronograma_archivo": 1, "cronograma_fecha_carga": 1, "cronograma_resumen": 1, 
         "semanas_planeadas": 1, "fecha_inicio": 1, "fecha_fin_planeada": 1, "nombre": 1}
    )
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Obtener frentes del proyecto
    frentes = await db.frentes.find({"proyecto_id": proyecto_id}, {"_id": 0}).to_list(100)
    frentes = sorted(frentes, key=lambda x: x.get("orden", 0))
    
    return {
        "proyecto_nombre": proyecto.get("nombre", ""),
        "tiene_cronograma": bool(proyecto.get("cronograma_archivo")),
        "cronograma_archivo": proyecto.get("cronograma_archivo"),
        "cronograma_fecha_carga": proyecto.get("cronograma_fecha_carga"),
        "cronograma_resumen": proyecto.get("cronograma_resumen"),
        "semanas_planeadas": proyecto.get("semanas_planeadas", 0),
        "fecha_inicio": proyecto.get("fecha_inicio"),
        "fecha_fin_planeada": proyecto.get("fecha_fin_planeada"),
        "frentes": frentes
    }


@api_router.post("/proyectos/{proyecto_id}/analizar-desviacion")
async def analizar_desviacion_cronograma(proyecto_id: str):
    """
    Analiza la desviación entre el progreso real y el cronograma planificado.
    Envía alerta por email si la desviación es significativa (>20%).
    """
    from services.email import enviar_alerta_desviacion_cronograma
    
    # Obtener proyecto
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Verificar que tiene cronograma
    if not proyecto.get("cronograma_resumen"):
        raise HTTPException(status_code=400, detail="El proyecto no tiene cronograma cargado")
    
    cronograma = proyecto.get("cronograma_resumen", {})
    fecha_inicio_str = proyecto.get("fecha_inicio")
    
    if not fecha_inicio_str:
        raise HTTPException(status_code=400, detail="El proyecto no tiene fecha de inicio definida")
    
    # Calcular semana actual del proyecto
    try:
        fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d")
        dias_transcurridos = (datetime.now() - fecha_inicio).days
        semana_actual = max(1, dias_transcurridos // 7 + 1)
    except:
        semana_actual = 1
    
    semanas_planeadas = proyecto.get("semanas_planeadas", 12)
    progreso_esperado = min(100, (semana_actual / semanas_planeadas) * 100) if semanas_planeadas > 0 else 0
    
    # Obtener progreso real por tipo de actividad
    desviaciones = []
    
    # Excavación
    vol_planeado = proyecto.get("volumen_total_planeado", 0)
    vol_real = proyecto.get("volumen_ejecutado", 0)
    if vol_planeado > 0:
        progreso_real_exc = (vol_real / vol_planeado) * 100
        desviacion_exc = progreso_real_exc - progreso_esperado
        desviaciones.append({
            "fase": "Excavación",
            "planeado": progreso_esperado,
            "real": progreso_real_exc,
            "desviacion_porcentaje": desviacion_exc,
            "unidades": f"{vol_real:,.0f} / {vol_planeado:,.0f} m³"
        })
    
    # Pilas
    pilas_planeadas = proyecto.get("pilas_planeadas", 0)
    pilas_real = proyecto.get("pilas_ejecutadas", 0)
    if pilas_planeadas > 0:
        progreso_real_pilas = (pilas_real / pilas_planeadas) * 100
        desviacion_pilas = progreso_real_pilas - progreso_esperado
        desviaciones.append({
            "fase": "Pilas / Cimentación",
            "planeado": progreso_esperado,
            "real": progreso_real_pilas,
            "desviacion_porcentaje": desviacion_pilas,
            "unidades": f"{pilas_real} / {pilas_planeadas} pilas"
        })
    
    # Anclas
    anclas_planeadas = proyecto.get("anclas_planeadas", 0)
    anclas_real = proyecto.get("anclas_ejecutadas", 0)
    if anclas_planeadas > 0:
        progreso_real_anclas = (anclas_real / anclas_planeadas) * 100
        desviacion_anclas = progreso_real_anclas - progreso_esperado
        desviaciones.append({
            "fase": "Anclas",
            "planeado": progreso_esperado,
            "real": progreso_real_anclas,
            "desviacion_porcentaje": desviacion_anclas,
            "unidades": f"{anclas_real} / {anclas_planeadas} anclas"
        })
    
    # Muros
    muros_planeados = proyecto.get("muros_planeados", 0)
    muros_real = proyecto.get("muros_ejecutados", 0)
    if muros_planeados > 0:
        progreso_real_muros = (muros_real / muros_planeados) * 100
        desviacion_muros = progreso_real_muros - progreso_esperado
        desviaciones.append({
            "fase": "Muros / Estructura",
            "planeado": progreso_esperado,
            "real": progreso_real_muros,
            "desviacion_porcentaje": desviacion_muros,
            "unidades": f"{muros_real} / {muros_planeados} muros"
        })
    
    # Determinar si hay desviaciones críticas (>20% de retraso)
    hay_desviacion_critica = any(d["desviacion_porcentaje"] < -20 for d in desviaciones)
    hay_desviacion_moderada = any(d["desviacion_porcentaje"] < -10 for d in desviaciones)
    
    # Generar resumen
    if hay_desviacion_critica:
        resumen = f"""⚠️ ALERTA CRÍTICA: El proyecto muestra retrasos significativos.

Situación actual:
- Semana {semana_actual} de {semanas_planeadas} planeadas
- Progreso esperado según cronograma: {progreso_esperado:.1f}%
- Se detectaron fases con retraso mayor al 20%

Recomendaciones inmediatas:
1. Convocar reunión de emergencia con el equipo de obra
2. Revisar disponibilidad de maquinaria y recursos
3. Evaluar posibles causas del retraso (clima, suministros, etc.)
4. Considerar ajustes al cronograma o recursos adicionales"""
    elif hay_desviacion_moderada:
        resumen = f"""📊 ALERTA MODERADA: Algunas fases muestran desviaciones.

Situación actual:
- Semana {semana_actual} de {semanas_planeadas} planeadas
- Progreso esperado según cronograma: {progreso_esperado:.1f}%
- Se detectaron desviaciones entre 10-20%

Recomendaciones:
1. Monitorear de cerca las actividades con retraso
2. Verificar si hay obstáculos que resolver
3. Mantener comunicación con el equipo de obra"""
    else:
        resumen = f"""✅ El proyecto avanza dentro de los parámetros esperados.

Situación actual:
- Semana {semana_actual} de {semanas_planeadas} planeadas
- Progreso esperado según cronograma: {progreso_esperado:.1f}%
- Las desviaciones están dentro del rango aceptable (±10%)"""
    
    # Enviar alerta por email si hay desviación significativa
    email_enviado = False
    if hay_desviacion_critica or hay_desviacion_moderada:
        email_enviado = await enviar_alerta_desviacion_cronograma(
            proyecto_nombre=proyecto.get("nombre", "Sin nombre"),
            proyecto_id=proyecto_id,
            desviaciones=desviaciones,
            resumen=resumen,
            fecha_analisis=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        )
        
        # Crear notificación en el sistema
        tipo_notif = "error" if hay_desviacion_critica else "warning"
        titulo_notif = "Alerta Crítica de Desviación" if hay_desviacion_critica else "Desviación Detectada"
        await crear_notificacion_sistema(
            tipo=tipo_notif,
            titulo=titulo_notif,
            mensaje=f"Semana {semana_actual}/{semanas_planeadas} - Progreso esperado: {progreso_esperado:.1f}%",
            proyecto_id=proyecto_id,
            proyecto_nombre=proyecto.get("nombre"),
            link=f"/proyectos?id={proyecto_id}",
            metadata={
                "semana_actual": semana_actual,
                "progreso_esperado": progreso_esperado,
                "hay_desviacion_critica": hay_desviacion_critica,
                "desviaciones_count": len(desviaciones)
            }
        )
    
    # Guardar el análisis en el proyecto
    await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": {
            "ultimo_analisis_desviacion": {
                "fecha": datetime.now(timezone.utc).isoformat(),
                "semana_actual": semana_actual,
                "progreso_esperado": progreso_esperado,
                "desviaciones": desviaciones,
                "hay_desviacion_critica": hay_desviacion_critica,
                "hay_desviacion_moderada": hay_desviacion_moderada,
                "email_enviado": email_enviado
            }
        }}
    )
    
    return {
        "success": True,
        "proyecto": proyecto.get("nombre"),
        "semana_actual": semana_actual,
        "semanas_planeadas": semanas_planeadas,
        "progreso_esperado": round(progreso_esperado, 1),
        "desviaciones": desviaciones,
        "hay_desviacion_critica": hay_desviacion_critica,
        "hay_desviacion_moderada": hay_desviacion_moderada,
        "resumen": resumen,
        "alerta_enviada": email_enviado
    }


@api_router.get("/proyectos/{proyecto_id}/frentes")
async def obtener_frentes(proyecto_id: str):
    """Obtiene todos los frentes de un proyecto"""
    frentes = await db.frentes.find({"proyecto_id": proyecto_id}, {"_id": 0}).to_list(100)
    return sorted(frentes, key=lambda x: x.get("orden", 0))


@api_router.post("/proyectos/{proyecto_id}/frentes")
async def crear_frente(proyecto_id: str, frente: dict):
    """Crea un nuevo frente para el proyecto"""
    frente_data = {
        "id": str(uuid.uuid4()),
        "proyecto_id": proyecto_id,
        "nombre": frente.get("nombre", "Nuevo Frente"),
        "descripcion": frente.get("descripcion", ""),
        "actividades": frente.get("actividades", []),
        "orden": frente.get("orden", 1),
        "created_at": datetime.now(timezone.utc)
    }
    await db.frentes.insert_one(frente_data)
    frente_data.pop("_id", None)
    return frente_data


# --- Catálogo de Maquinaria con IA ---
@api_router.post("/proyectos/analizar-catalogo-maquinaria")
async def analizar_catalogo_maquinaria(
    file: UploadFile = File(...),
    area_terreno: float = 0,
    volumen_excavacion: float = 0,
    num_pilas: int = 0,
    distancia_pilas: float = 0,
    espacio_maniobra: float = 0
):
    """
    Analiza un catálogo de maquinaria en Excel y usa IA para:
    1. Extraer información de las máquinas
    2. Buscar especificaciones técnicas
    3. Proponer distribución óptima para el proyecto
    """
    import json as json_module
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)")
    
    # Leer el archivo Excel
    content = await file.read()
    wb = load_workbook(filename=io.BytesIO(content))
    ws = wb.active
    
    # Extraer datos de las máquinas
    maquinas = []
    headers = []
    header_row_found = False
    
    # Mapeo flexible de nombres de columnas
    column_mappings = {
        'tipo': ['TIPO DE MAQUINA', 'TIPO', 'TIPO_MAQUINA', 'MAQUINA', 'EQUIPO', 'TIPO DE EQUIPO'],
        'marca': ['MARCA', 'FABRICANTE', 'MANUFACTURER'],
        'modelo': ['MODELO', 'MODEL', 'NUMERO DE MODELO'],
        'estatus': ['ESTATUS', 'STATUS', 'ESTADO', 'CONDICION', 'FECHA APROX TERMINO PROYECTO A INICIAR'],
        'operador': ['OPERADOR', 'OPERATOR', 'CONDUCTOR'],
        'obra': ['OBRA', 'PROYECTO', 'SITE', 'OBRA ACTUAL'],
        'ubicacion': ['UBICACIÓN', 'UBICACION', 'LOCATION', 'SITIO']
    }
    
    def find_column_value(row_dict, key_names):
        """Busca el valor usando múltiples posibles nombres de columna"""
        for key in key_names:
            if key in row_dict and row_dict[key]:
                return row_dict[key]
        return ''
    
    def is_header_row(row):
        """Detecta si una fila parece ser la fila de headers"""
        row_values = [str(v).strip().upper() if v else '' for v in row]
        # Buscar palabras clave de headers
        keywords = ['TIPO', 'MARCA', 'MODELO', 'MAQUINA', 'EQUIPO']
        matches = sum(1 for kw in keywords for val in row_values if kw in val)
        return matches >= 2  # Al menos 2 coincidencias
    
    for idx, row in enumerate(ws.iter_rows(values_only=True)):
        # Saltar filas completamente vacías
        if not any(row):
            continue
        
        # Buscar la fila de headers
        if not header_row_found:
            if is_header_row(row):
                # Normalizar headers: quitar espacios, convertir a mayúsculas
                headers = []
                for i, h in enumerate(row):
                    if h:
                        cleaned = str(h).strip().upper().replace('  ', ' ')
                        headers.append(cleaned)
                    else:
                        headers.append(f"COL_{i}")
                logging.info(f"Headers encontrados en fila {idx}: {headers}")
                header_row_found = True
            continue
        
        # Procesar filas de datos
        row_dict = {}
        for i, value in enumerate(row):
            if i < len(headers):
                row_dict[headers[i]] = value
        
        # Extraer campos clave usando el mapeo flexible
        tipo = find_column_value(row_dict, column_mappings['tipo'])
        marca = find_column_value(row_dict, column_mappings['marca'])
        modelo = find_column_value(row_dict, column_mappings['modelo'])
        estatus = find_column_value(row_dict, column_mappings['estatus'])
        operador = find_column_value(row_dict, column_mappings['operador'])
        obra = find_column_value(row_dict, column_mappings['obra'])
        ubicacion = find_column_value(row_dict, column_mappings['ubicacion'])
        
        if tipo and str(tipo).strip():
            maquinas.append({
                "tipo": str(tipo).strip(),
                "marca": str(marca).strip() if marca else "",
                "modelo": str(modelo).strip() if modelo else "",
                "estatus": str(estatus).strip() if estatus else "",
                "operador": str(operador).strip() if operador else "",
                "obra_actual": str(obra).strip() if obra else "",
                "ubicacion": str(ubicacion).strip() if ubicacion else ""
            })
    
    logging.info(f"Máquinas encontradas: {len(maquinas)}")
    
    if not maquinas:
        # Dar más información sobre el problema
        raise HTTPException(
            status_code=400, 
            detail=f"No se encontraron máquinas. Headers encontrados: {headers}. Se esperan columnas como: TIPO DE MAQUINA, MARCA, MODELO, ESTATUS"
        )
    
    # Filtrar máquinas disponibles (OPTIMA, SATISFACTORIO, sin estado definido)
    maquinas_disponibles = [
        m for m in maquinas 
        if m.get('estatus', '').upper() not in ['DESHABILITADA', 'EN REPARACION']
    ]
    
    # Categorizar máquinas
    excavadoras = [m for m in maquinas_disponibles if 'EXCAVADORA' in m['tipo'].upper()]
    perforadoras = [m for m in maquinas_disponibles if 'PERFORADORA' in m['tipo'].upper() and 'ANCLA' not in m['tipo'].upper()]
    perforadoras_anclas = [m for m in maquinas_disponibles if 'PERFORADORA ANCLAS' in m['tipo'].upper() or 'ANCLA' in m['tipo'].upper()]
    gruas = [m for m in maquinas_disponibles if 'GRUA' in m['tipo'].upper()]
    manipuladores = [m for m in maquinas_disponibles if 'MANIPULADOR' in m['tipo'].upper()]
    
    # Preparar prompt para IA
    maquinas_texto = ""
    for m in maquinas_disponibles:
        maquinas_texto += f"- {m['tipo']}: {m['marca']} {m['modelo']} (Estado: {m['estatus'] or 'Disponible'})\n"
    
    prompt = f"""Eres un experto en maquinaria de construcción y planificación de obras.

CATÁLOGO DE MAQUINARIA DISPONIBLE:
{maquinas_texto}

DATOS DEL PROYECTO:
- Área del terreno: {area_terreno} m²
- Volumen de excavación: {volumen_excavacion} m³
- Número de pilas a perforar: {num_pilas}
- Distancia entre pilas: {distancia_pilas} m
- Espacio de maniobra disponible: {espacio_maniobra} m²

TAREA:
1. Para cada máquina del catálogo, proporciona las especificaciones técnicas aproximadas:
   - Dimensiones (largo x ancho x altura en metros)
   - Radio de giro
   - Rendimiento estimado (m³/hora para excavadoras, pilas/día para perforadoras)
   - Peso operativo

2. Analiza qué máquinas son más adecuadas para este proyecto considerando:
   - Espacio disponible para maniobras
   - Volumen de trabajo
   - Eficiencia esperada

3. Propón un PLAN DE EJECUCIÓN ÓPTIMO:
   - FASE 1 EXCAVACIÓN: Qué excavadoras usar y en qué orden
   - FASE 2 PERFORACIÓN DE PILAS: Qué perforadoras usar
   - FASE 3 ANCLAS: Qué perforadoras de anclas usar
   - Distribución espacial recomendada

4. Calcula:
   - Tiempo estimado para excavación
   - Tiempo estimado para perforación de pilas
   - Tiempo estimado para anclas
   - Recomendaciones para optimizar el uso del espacio

Responde en formato JSON con esta estructura:
{{
    "maquinas_con_specs": [
        {{
            "tipo": "...",
            "marca": "...",
            "modelo": "...",
            "dimensiones": {{"largo": 0, "ancho": 0, "altura": 0}},
            "radio_giro": 0,
            "rendimiento": "...",
            "peso_operativo": 0,
            "adecuada_para_proyecto": true/false,
            "razon": "..."
        }}
    ],
    "plan_excavacion": {{
        "maquinas_recomendadas": ["..."],
        "estrategia": "...",
        "tiempo_estimado_dias": 0,
        "rendimiento_esperado_m3_dia": 0
    }},
    "plan_pilas": {{
        "maquinas_recomendadas": ["..."],
        "estrategia": "...",
        "tiempo_estimado_dias": 0,
        "pilas_por_dia": 0
    }},
    "plan_anclas": {{
        "maquinas_recomendadas": ["..."],
        "estrategia": "...",
        "tiempo_estimado_dias": 0,
        "anclas_por_dia": 0
    }},
    "distribucion_espacial": {{
        "recomendacion": "...",
        "zonas_trabajo": ["..."],
        "consideraciones_seguridad": ["..."]
    }},
    "resumen_ejecutivo": "..."
}}
"""
    
    try:
        from emergentintegrations.llm.chat import UserMessage
        
        # Crear chat con Gemini
        llm = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"catalogo-maquinaria-{uuid.uuid4()}",
            system_message="Eres un experto en maquinaria de construcción y planificación de obras. Siempre respondes en formato JSON válido."
        ).with_model("gemini", "gemini-2.0-flash")
        
        # Enviar mensaje
        user_message = UserMessage(text=prompt)
        response = await llm.send_message(user_message)
        
        logging.info(f"Respuesta IA recibida: {len(response)} caracteres")
        
        # Parsear respuesta JSON
        response_text = response.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        # Intentar extraer JSON de la respuesta
        import re
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            resultado_ia = json_module.loads(json_match.group())
        else:
            resultado_ia = json_module.loads(response_text.strip())
        
        return {
            "success": True,
            "total_maquinas": len(maquinas),
            "maquinas_disponibles": len(maquinas_disponibles),
            "resumen_catalogo": {
                "excavadoras": len(excavadoras),
                "perforadoras": len(perforadoras),
                "perforadoras_anclas": len(perforadoras_anclas),
                "gruas": len(gruas),
                "manipuladores": len(manipuladores)
            },
            "maquinas_raw": maquinas_disponibles,
            "analisis_ia": resultado_ia
        }
    except json_module.JSONDecodeError as e:
        logging.warning(f"Error parseando JSON de IA: {e}")
        # Si no puede parsear JSON, devolver texto plano
        return {
            "success": True,
            "total_maquinas": len(maquinas),
            "maquinas_disponibles": len(maquinas_disponibles),
            "resumen_catalogo": {
                "excavadoras": len(excavadoras),
                "perforadoras": len(perforadoras),
                "perforadoras_anclas": len(perforadoras_anclas),
                "gruas": len(gruas),
                "manipuladores": len(manipuladores)
            },
            "maquinas_raw": maquinas_disponibles,
            "analisis_ia_texto": response if 'response' in locals() else "Error procesando respuesta de IA",
            "mensaje": "Catálogo procesado. El análisis de IA está disponible como texto."
        }
    except Exception as e:
        logging.error(f"Error analizando catálogo con IA: {e}")
        import traceback
        traceback.print_exc()
        # Devolver éxito parcial - tenemos las máquinas pero no el análisis IA
        return {
            "success": True,
            "error_ia": str(e),
            "total_maquinas": len(maquinas),
            "maquinas_disponibles": len(maquinas_disponibles),
            "maquinas_raw": maquinas_disponibles,
            "resumen_catalogo": {
                "excavadoras": len(excavadoras),
                "perforadoras": len(perforadoras),
                "perforadoras_anclas": len(perforadoras_anclas),
                "gruas": len(gruas),
                "manipuladores": len(manipuladores)
            },
            "mensaje": f"Catálogo procesado exitosamente ({len(maquinas_disponibles)} máquinas disponibles). El análisis con IA no está disponible temporalmente."
        }


@api_router.post("/proyectos/{proyecto_id}/guardar-catalogo-maquinaria")
async def guardar_catalogo_maquinaria(proyecto_id: str, data: dict):
    """
    Guarda el catálogo de maquinaria y el análisis de IA en el proyecto.
    """
    proyecto = await db.proyectos.find_one({"id": proyecto_id})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    await db.proyectos.update_one(
        {"id": proyecto_id},
        {"$set": {
            "catalogo_maquinaria": data.get("maquinas", []),
            "analisis_maquinaria_ia": data.get("analisis_ia", {}),
            "parametros_proyecto": data.get("parametros", {}),
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    return {"success": True, "message": "Catálogo guardado correctamente"}


@api_router.get("/proyectos/{proyecto_id}/catalogo-maquinaria")
async def obtener_catalogo_maquinaria(proyecto_id: str):
    """Obtiene el catálogo de maquinaria de un proyecto"""
    proyecto = await db.proyectos.find_one(
        {"id": proyecto_id}, 
        {"_id": 0, "catalogo_maquinaria": 1, "analisis_maquinaria_ia": 1, "parametros_proyecto": 1}
    )
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    return {
        "catalogo": proyecto.get("catalogo_maquinaria", []),
        "analisis_ia": proyecto.get("analisis_maquinaria_ia", {}),
        "parametros": proyecto.get("parametros_proyecto", {})
    }


# --- Comparación de Plan IA vs Cronograma del Usuario ---
@api_router.post("/proyectos/{proyecto_id}/comparar-plan-ia")
async def comparar_plan_ia_vs_cronograma(proyecto_id: str):
    """
    Compara el plan generado por IA vs el cronograma planificado por el usuario.
    Usa IA para analizar y determinar si el plan propuesto es mejor, igual o peor.
    """
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import json as json_module
    
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    analisis_ia = proyecto.get("analisis_maquinaria_ia", {})
    if not analisis_ia:
        raise HTTPException(status_code=400, detail="No hay análisis de IA para este proyecto. Primero sube el catálogo de maquinaria.")
    
    # Obtener datos del cronograma del usuario
    semanas_excavacion = proyecto.get("semanas_excavacion", 0)
    semanas_pilas = proyecto.get("semanas_pilas", 0)
    semanas_muros = proyecto.get("semanas_muros", 0)
    semanas_planeadas = proyecto.get("semanas_planeadas", 0)
    volumen_total = proyecto.get("volumen_total_planeado", 0)
    pilas_planeadas = proyecto.get("pilas_planeadas", 0)
    anclas_planeadas = proyecto.get("anclas_planeadas", 0)
    
    # Obtener datos del avance real
    avances = await db.avances_semanales.find({"proyecto_id": proyecto_id}, {"_id": 0}).to_list(100)
    semanas_reales = len(avances)
    volumen_real = sum((a.get("volumen_excavacion", 0) or 0) for a in avances)
    pilas_real = sum((a.get("pilas_completadas", 0) or 0) for a in avances)
    anclas_real = sum((a.get("anclas_instaladas", 0) or 0) for a in avances)
    
    # Datos del plan de IA
    plan_excavacion_ia = analisis_ia.get("plan_excavacion", {})
    plan_pilas_ia = analisis_ia.get("plan_pilas", {})
    plan_anclas_ia = analisis_ia.get("plan_anclas", {})
    
    dias_excavacion_ia = plan_excavacion_ia.get("tiempo_estimado_dias", 0)
    dias_pilas_ia = plan_pilas_ia.get("tiempo_estimado_dias", 0)
    dias_anclas_ia = plan_anclas_ia.get("tiempo_estimado_dias", 0)
    
    # Convertir días a semanas (5 días laborales = 1 semana)
    semanas_excavacion_ia = round(dias_excavacion_ia / 5, 1) if dias_excavacion_ia else 0
    semanas_pilas_ia = round(dias_pilas_ia / 5, 1) if dias_pilas_ia else 0
    semanas_anclas_ia = round(dias_anclas_ia / 5, 1) if dias_anclas_ia else 0
    
    # Crear prompt para análisis comparativo
    prompt = f"""Eres un experto en planificación de obras de construcción.

DATOS DEL PROYECTO: {proyecto.get('nombre', 'Sin nombre')}

CRONOGRAMA PLANIFICADO POR EL USUARIO:
- Semanas para excavación: {semanas_excavacion} semanas
- Semanas para pilas: {semanas_pilas} semanas
- Semanas para anclas/muros: {semanas_muros} semanas
- Total semanas planeadas: {semanas_planeadas} semanas
- Volumen a excavar: {volumen_total} m³
- Pilas a perforar: {pilas_planeadas}
- Anclas a instalar: {anclas_planeadas}

PLAN GENERADO POR IA:
- Semanas para excavación: {semanas_excavacion_ia} semanas ({dias_excavacion_ia} días)
- Semanas para pilas: {semanas_pilas_ia} semanas ({dias_pilas_ia} días)  
- Semanas para anclas: {semanas_anclas_ia} semanas ({dias_anclas_ia} días)
- Rendimiento excavación: {plan_excavacion_ia.get('rendimiento_esperado_m3_dia', 0)} m³/día
- Rendimiento pilas: {plan_pilas_ia.get('pilas_por_dia', 0)} pilas/día
- Rendimiento anclas: {plan_anclas_ia.get('anclas_por_dia', 0)} anclas/día
- Máquinas recomendadas excavación: {plan_excavacion_ia.get('maquinas_recomendadas', [])}
- Máquinas recomendadas pilas: {plan_pilas_ia.get('maquinas_recomendadas', [])}

AVANCE REAL HASTA AHORA (Semana {semanas_reales}):
- Volumen excavado: {volumen_real} m³
- Pilas completadas: {pilas_real}
- Anclas instaladas: {anclas_real}

TAREA:
1. Compara los tres escenarios: Plan del Usuario, Plan IA, y Avance Real
2. Determina cuál plan es más realista y eficiente
3. Analiza si el avance real va acorde a alguno de los planes
4. Proporciona recomendaciones para optimizar

Responde en formato JSON:
{{
    "comparacion_general": {{
        "plan_usuario_dias_total": <número>,
        "plan_ia_dias_total": <número>,
        "diferencia_dias": <número positivo si IA es más rápido>,
        "porcentaje_mejora": <porcentaje de mejora del plan IA vs usuario>
    }},
    "evaluacion_excavacion": {{
        "usuario_semanas": {semanas_excavacion},
        "ia_semanas": {semanas_excavacion_ia},
        "mejor_plan": "<usuario | ia | similar>",
        "razon": "<explicación>"
    }},
    "evaluacion_pilas": {{
        "usuario_semanas": {semanas_pilas},
        "ia_semanas": {semanas_pilas_ia},
        "mejor_plan": "<usuario | ia | similar>",
        "razon": "<explicación>"
    }},
    "evaluacion_anclas": {{
        "usuario_semanas": {semanas_muros},
        "ia_semanas": {semanas_anclas_ia},
        "mejor_plan": "<usuario | ia | similar>",
        "razon": "<explicación>"
    }},
    "estado_avance_real": {{
        "porcentaje_excavacion": <% completado>,
        "porcentaje_pilas": <% completado>,
        "porcentaje_anclas": <% completado>,
        "alineado_con": "<plan_usuario | plan_ia | retrasado | adelantado>",
        "semanas_restantes_estimadas": <número>
    }},
    "veredicto": "<PLAN_IA_MEJOR | PLAN_USUARIO_MEJOR | SIMILAR>",
    "confianza": "<ALTA | MEDIA | BAJA>",
    "resumen": "<resumen ejecutivo de 2-3 oraciones>",
    "recomendaciones": ["<recomendación 1>", "<recomendación 2>", ...]
}}"""
    
    try:
        llm = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"comparacion-plan-{proyecto_id}-{uuid.uuid4()}",
            system_message="Eres un experto en planificación de obras de construcción. Siempre respondes en JSON válido."
        ).with_model("gemini", "gemini-2.0-flash")
        
        user_message = UserMessage(text=prompt)
        response = await llm.send_message(user_message)
        
        # Parsear respuesta
        response_text = response.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        import re
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            comparacion_ia = json_module.loads(json_match.group())
        else:
            comparacion_ia = json_module.loads(response_text.strip())
        
        # Guardar comparación en el proyecto
        comparacion_completa = {
            "fecha_comparacion": datetime.now(timezone.utc).isoformat(),
            "datos_usuario": {
                "semanas_excavacion": semanas_excavacion,
                "semanas_pilas": semanas_pilas,
                "semanas_anclas": semanas_muros,
                "semanas_total": semanas_planeadas,
                "volumen_total": volumen_total,
                "pilas_planeadas": pilas_planeadas,
                "anclas_planeadas": anclas_planeadas
            },
            "datos_ia": {
                "semanas_excavacion": semanas_excavacion_ia,
                "semanas_pilas": semanas_pilas_ia,
                "semanas_anclas": semanas_anclas_ia,
                "semanas_total": semanas_excavacion_ia + semanas_pilas_ia + semanas_anclas_ia,
                "rendimiento_excavacion_m3_dia": plan_excavacion_ia.get("rendimiento_esperado_m3_dia", 0),
                "rendimiento_pilas_dia": plan_pilas_ia.get("pilas_por_dia", 0),
                "rendimiento_anclas_dia": plan_anclas_ia.get("anclas_por_dia", 0)
            },
            "datos_reales": {
                "semanas_transcurridas": semanas_reales,
                "volumen_excavado": volumen_real,
                "pilas_completadas": pilas_real,
                "anclas_instaladas": anclas_real
            },
            "analisis_ia": comparacion_ia
        }
        
        await db.proyectos.update_one(
            {"id": proyecto_id},
            {"$set": {
                "comparacion_planes": comparacion_completa,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        return {
            "success": True,
            "comparacion": comparacion_completa
        }
        
    except Exception as e:
        logging.error(f"Error comparando planes: {e}")
        import traceback
        traceback.print_exc()
        
        # Devolver comparación básica sin IA
        comparacion_basica = {
            "fecha_comparacion": datetime.now(timezone.utc).isoformat(),
            "datos_usuario": {
                "semanas_excavacion": semanas_excavacion,
                "semanas_pilas": semanas_pilas,
                "semanas_anclas": semanas_muros,
                "semanas_total": semanas_planeadas
            },
            "datos_ia": {
                "semanas_excavacion": semanas_excavacion_ia,
                "semanas_pilas": semanas_pilas_ia,
                "semanas_anclas": semanas_anclas_ia,
                "semanas_total": semanas_excavacion_ia + semanas_pilas_ia + semanas_anclas_ia
            },
            "datos_reales": {
                "semanas_transcurridas": semanas_reales,
                "volumen_excavado": volumen_real,
                "pilas_completadas": pilas_real,
                "anclas_instaladas": anclas_real
            },
            "error_ia": str(e)
        }
        
        await db.proyectos.update_one(
            {"id": proyecto_id},
            {"$set": {
                "comparacion_planes": comparacion_basica,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        return {
            "success": True,
            "comparacion": comparacion_basica,
            "mensaje": "Comparación guardada. El análisis de IA no está disponible."
        }


@api_router.get("/proyectos/{proyecto_id}/comparacion-planes")
async def obtener_comparacion_planes(proyecto_id: str):
    """Obtiene la comparación de planes guardada para un proyecto"""
    proyecto = await db.proyectos.find_one(
        {"id": proyecto_id},
        {"_id": 0, "comparacion_planes": 1, "nombre": 1}
    )
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    return {
        "proyecto_nombre": proyecto.get("nombre", ""),
        "comparacion": proyecto.get("comparacion_planes", None)
    }


@api_router.get("/dashboard/comparaciones-resumen")
async def obtener_comparaciones_dashboard():
    """Obtiene un resumen de comparaciones de todos los proyectos para el dashboard"""
    proyectos = await db.proyectos.find(
        {"comparacion_planes": {"$exists": True}},
        {"_id": 0, "id": 1, "nombre": 1, "comparacion_planes": 1, "avance_actual": 1}
    ).to_list(100)
    
    resumen = []
    for p in proyectos:
        comp = p.get("comparacion_planes", {})
        if comp:
            resumen.append({
                "proyecto_id": p["id"],
                "proyecto_nombre": p.get("nombre", ""),
                "avance_actual": p.get("avance_actual", 0),
                "datos_usuario": comp.get("datos_usuario", {}),
                "datos_ia": comp.get("datos_ia", {}),
                "datos_reales": comp.get("datos_reales", {}),
                "veredicto": comp.get("analisis_ia", {}).get("veredicto", "NO_ANALIZADO"),
                "fecha_comparacion": comp.get("fecha_comparacion", "")
            })
    
    return {"proyectos": resumen}


@api_router.post("/analisis/foto-avance")
async def analizar_foto_para_avance(imagen: UploadFile = File(...), proyecto_info: str = Form("{}")):
    """
    Analiza una foto de obra para detectar avances antes de crear el registro.
    Retorna las cantidades detectadas para pre-rellenar el formulario.
    """
    from emergentintegrations.llm.gemini import GeminiChat
    
    try:
        # Parsear info del proyecto
        info = json.loads(proyecto_info)
        tiene_excavacion = info.get("tiene_excavacion", True)
        tiene_cimentacion = info.get("tiene_cimentacion", False)
        tiene_edificacion = info.get("tiene_edificacion", False)
        pilas_planeadas = info.get("pilas_planeadas", 0)
        anclas_planeadas = info.get("anclas_planeadas", 0)
        muros_planeados = info.get("muros_planeados", 0)
        
        # Leer y convertir imagen a base64
        content = await imagen.read()
        import base64
        imagen_base64 = base64.b64encode(content).decode('utf-8')
        
        # Crear prompt para análisis
        prompt = f"""Analiza esta foto de una obra de construcción y detecta los elementos visibles.

El proyecto tiene las siguientes fases activas:
{f"- EXCAVACIÓN: Detecta si hay trabajo de excavación visible y estima el volumen" if tiene_excavacion else ""}
{f"- CIMENTACIÓN: Detecta pilas (meta: {pilas_planeadas}) y anclas (meta: {anclas_planeadas})" if tiene_cimentacion else ""}
{f"- EDIFICACIÓN: Detecta muros completados (meta: {muros_planeados})" if tiene_edificacion else ""}

Responde SOLO en formato JSON con esta estructura exacta:
{{
    "volumen_excavacion": <número estimado de m³ excavados, 0 si no aplica o no visible>,
    "pilas_detectadas": <número de pilas completadas visibles, 0 si no aplica>,
    "anclas_detectadas": <número de anclas instaladas visibles, 0 si no aplica>,
    "muros_detectados": <número de muros completados visibles, 0 si no aplica>,
    "descripcion_ia": "<descripción breve del estado de la obra en 1-2 oraciones>",
    "confianza": "<ALTA|MEDIA|BAJA - qué tan seguro estás de los números>"
}}

IMPORTANTE:
- Si no puedes ver claramente algo, pon 0
- Sé conservador en las estimaciones
- La descripción debe ser concisa y profesional
"""

        chat = GeminiChat(gemini_key=EMERGENT_LLM_KEY)
        
        response = await asyncio.to_thread(
            chat.send_message_with_image,
            prompt,
            imagen_base64,
            image_type="image/jpeg"
        )
        
        # Parsear respuesta JSON
        response_text = response.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        resultado = json.loads(response_text)
        
        return {
            "success": True,
            "resultado": {
                "volumen_excavacion": resultado.get("volumen_excavacion", 0),
                "pilas_detectadas": resultado.get("pilas_detectadas", 0),
                "anclas_detectadas": resultado.get("anclas_detectadas", 0),
                "muros_detectados": resultado.get("muros_detectados", 0),
                "descripcion_ia": resultado.get("descripcion_ia", ""),
                "confianza": resultado.get("confianza", "MEDIA")
            }
        }
        
    except json.JSONDecodeError as e:
        logging.error(f"Error parseando respuesta IA: {e}")
        return {
            "success": False,
            "error": "La IA no pudo analizar correctamente la imagen",
            "resultado": {
                "volumen_excavacion": 0,
                "pilas_detectadas": 0,
                "anclas_detectadas": 0,
                "muros_detectados": 0,
                "descripcion_ia": "",
                "confianza": "BAJA"
            }
        }
    except Exception as e:
        logging.error(f"Error analizando foto: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/avances/{avance_id}/analizar-foto")
async def analizar_foto_avance(avance_id: str, data: dict):
    """
    Analiza una foto de avance usando IA para detectar pilas y anclas.
    """
    from services.cronograma_ai import analizar_foto_avance as analizar_ia
    
    avance = await db.avances_semanales.find_one({"id": avance_id})
    if not avance:
        raise HTTPException(status_code=404, detail="Avance no encontrado")
    
    imagen_base64 = data.get("imagen_base64")
    if not imagen_base64:
        raise HTTPException(status_code=400, detail="Se requiere imagen en base64")
    
    # Obtener imagen de semana anterior para comparación
    imagen_anterior = None
    if avance.get("semana", 1) > 1:
        avance_anterior = await db.avances_semanales.find_one({
            "proyecto_id": avance["proyecto_id"],
            "semana": avance["semana"] - 1
        })
        if avance_anterior and avance_anterior.get("imagenes"):
            # Podríamos cargar la imagen anterior aquí
            pass
    
    # Obtener proyecto para pilas planeadas
    proyecto = await db.proyectos.find_one({"id": avance["proyecto_id"]})
    pilas_planeadas = proyecto.get("total_pilas_planeadas", 0) if proyecto else 0
    
    # Analizar con IA
    resultado = await analizar_ia(
        imagen_base64=imagen_base64,
        imagen_anterior_base64=imagen_anterior,
        pilas_planeadas=pilas_planeadas,
        semana_actual=avance.get("semana", 1)
    )
    
    if resultado.get("success"):
        # Guardar análisis
        analisis = {
            "id": str(uuid.uuid4()),
            "proyecto_id": avance["proyecto_id"],
            "avance_id": avance_id,
            "semana": avance.get("semana", 1),
            "fecha_analisis": datetime.now(timezone.utc),
            "pilas_detectadas": resultado.get("pilas_detectadas", 0),
            "anclas_detectadas": resultado.get("anclas_detectadas", 0),
            "pilas_en_proceso": resultado.get("pilas_en_proceso", 0),
            "porcentaje_avance_estimado": resultado.get("porcentaje_avance_estimado", 0),
            "estado_proyecto": resultado.get("estado_proyecto", "EN_TIEMPO"),
            "confianza_deteccion": resultado.get("confianza_deteccion", "MEDIA"),
            "observaciones": resultado.get("observaciones", ""),
            "recomendaciones": resultado.get("recomendaciones", "")
        }
        await db.analisis_fotos.insert_one(analisis)
        
        # Actualizar avance con datos detectados
        await db.avances_semanales.update_one(
            {"id": avance_id},
            {"$set": {
                "pilas_detectadas_ia": resultado.get("pilas_detectadas", 0),
                "anclas_detectadas_ia": resultado.get("anclas_detectadas", 0),
                "estado_ia": resultado.get("estado_proyecto", "EN_TIEMPO")
            }}
        )
    
    return resultado


@api_router.get("/proyectos/{proyecto_id}/analisis-ia")
async def obtener_analisis_ia(proyecto_id: str):
    """Obtiene todos los análisis de IA de un proyecto"""
    analisis = await db.analisis_fotos.find(
        {"proyecto_id": proyecto_id}, 
        {"_id": 0}
    ).sort("semana", 1).to_list(100)
    return analisis


@api_router.post("/proyectos/{proyecto_id}/generar-reporte-ia")
async def generar_reporte_ia(proyecto_id: str):
    """Genera un reporte de progreso usando IA"""
    from services.cronograma_ai import generar_reporte_progreso
    
    proyecto = await db.proyectos.find_one({"id": proyecto_id})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Obtener último análisis
    ultimo_analisis = await db.analisis_fotos.find_one(
        {"proyecto_id": proyecto_id},
        sort=[("semana", -1)]
    )
    
    # Obtener historial
    historial = await db.analisis_fotos.find(
        {"proyecto_id": proyecto_id},
        {"_id": 0, "semana": 1, "pilas_detectadas": 1, "anclas_detectadas": 1}
    ).sort("semana", 1).to_list(100)
    
    resultado = await generar_reporte_progreso(
        proyecto_nombre=proyecto.get("nombre", "Proyecto"),
        semana_actual=ultimo_analisis.get("semana", 1) if ultimo_analisis else 1,
        pilas_planeadas=proyecto.get("total_pilas_planeadas", 0),
        pilas_detectadas=ultimo_analisis.get("pilas_detectadas", 0) if ultimo_analisis else 0,
        anclas_planeadas=proyecto.get("total_anclas_planeadas", 0),
        anclas_detectadas=ultimo_analisis.get("anclas_detectadas", 0) if ultimo_analisis else 0,
        historial_semanas=historial
    )
    
    return resultado


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Análisis Automático de Desviación Semanal ---
async def analizar_desviaciones_todos_proyectos():
    """
    Analiza la desviación de todos los proyectos con cronograma cargado.
    Se ejecuta automáticamente cada lunes a las 9:00.
    Envía alertas por email solo para proyectos con desviaciones significativas.
    """
    from services.email import enviar_alerta_desviacion_cronograma
    
    if not ADMIN_EMAIL or not RESEND_API_KEY:
        logging.warning("No se puede enviar alertas: ADMIN_EMAIL o RESEND_API_KEY no configurados")
        return
    
    try:
        logging.info("Iniciando análisis automático de desviaciones...")
        
        # Obtener proyectos con cronograma
        proyectos = await db.proyectos.find(
            {"cronograma_resumen": {"$exists": True, "$ne": None}},
            {"_id": 0}
        ).to_list(100)
        
        if not proyectos:
            logging.info("No hay proyectos con cronograma para analizar")
            return
        
        alertas_enviadas = 0
        proyectos_analizados = 0
        
        for proyecto in proyectos:
            proyecto_id = proyecto.get("id")
            fecha_inicio_str = proyecto.get("fecha_inicio")
            
            if not fecha_inicio_str:
                continue
            
            try:
                # Calcular semana actual del proyecto
                fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d")
                dias_transcurridos = (datetime.now() - fecha_inicio).days
                semana_actual = max(1, dias_transcurridos // 7 + 1)
                
                semanas_planeadas = proyecto.get("semanas_planeadas", 12)
                progreso_esperado = min(100, (semana_actual / semanas_planeadas) * 100) if semanas_planeadas > 0 else 0
                
                # Calcular desviaciones por fase
                desviaciones = []
                
                # Excavación
                vol_planeado = proyecto.get("volumen_total_planeado", 0)
                vol_real = proyecto.get("volumen_ejecutado", 0)
                if vol_planeado > 0:
                    progreso_real = (vol_real / vol_planeado) * 100
                    desviaciones.append({
                        "fase": "Excavación",
                        "planeado": progreso_esperado,
                        "real": progreso_real,
                        "desviacion_porcentaje": progreso_real - progreso_esperado
                    })
                
                # Pilas
                pilas_planeadas = proyecto.get("pilas_planeadas", 0)
                pilas_real = proyecto.get("pilas_ejecutadas", 0)
                if pilas_planeadas > 0:
                    progreso_real = (pilas_real / pilas_planeadas) * 100
                    desviaciones.append({
                        "fase": "Pilas / Cimentación",
                        "planeado": progreso_esperado,
                        "real": progreso_real,
                        "desviacion_porcentaje": progreso_real - progreso_esperado
                    })
                
                # Anclas
                anclas_planeadas = proyecto.get("anclas_planeadas", 0)
                anclas_real = proyecto.get("anclas_ejecutadas", 0)
                if anclas_planeadas > 0:
                    progreso_real = (anclas_real / anclas_planeadas) * 100
                    desviaciones.append({
                        "fase": "Anclas",
                        "planeado": progreso_esperado,
                        "real": progreso_real,
                        "desviacion_porcentaje": progreso_real - progreso_esperado
                    })
                
                # Muros
                muros_planeados = proyecto.get("muros_planeados", 0)
                muros_real = proyecto.get("muros_ejecutados", 0)
                if muros_planeados > 0:
                    progreso_real = (muros_real / muros_planeados) * 100
                    desviaciones.append({
                        "fase": "Muros / Estructura",
                        "planeado": progreso_esperado,
                        "real": progreso_real,
                        "desviacion_porcentaje": progreso_real - progreso_esperado
                    })
                
                proyectos_analizados += 1
                
                # Verificar si hay desviaciones críticas (>20%)
                hay_desviacion_critica = any(d["desviacion_porcentaje"] < -20 for d in desviaciones)
                hay_desviacion_moderada = any(d["desviacion_porcentaje"] < -10 for d in desviaciones)
                
                # Solo enviar alerta si hay desviación significativa
                if hay_desviacion_critica or hay_desviacion_moderada:
                    resumen = f"Análisis automático semanal - Semana {semana_actual} de {semanas_planeadas}"
                    if hay_desviacion_critica:
                        resumen += "\n⚠️ Se detectaron retrasos críticos (>20%) que requieren atención inmediata."
                    else:
                        resumen += "\n📊 Se detectaron desviaciones moderadas (10-20%) que deben monitorearse."
                    
                    email_enviado = await enviar_alerta_desviacion_cronograma(
                        proyecto_nombre=proyecto.get("nombre", "Sin nombre"),
                        proyecto_id=proyecto_id,
                        desviaciones=desviaciones,
                        resumen=resumen,
                        fecha_analisis=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
                    )
                    
                    if email_enviado:
                        alertas_enviadas += 1
                    
                    # Guardar resultado del análisis
                    await db.proyectos.update_one(
                        {"id": proyecto_id},
                        {"$set": {
                            "ultimo_analisis_desviacion": {
                                "fecha": datetime.now(timezone.utc).isoformat(),
                                "semana_actual": semana_actual,
                                "progreso_esperado": progreso_esperado,
                                "desviaciones": desviaciones,
                                "hay_desviacion_critica": hay_desviacion_critica,
                                "email_enviado": email_enviado,
                                "automatico": True
                            }
                        }}
                    )
                    
            except Exception as e:
                logging.error(f"Error analizando proyecto {proyecto_id}: {e}")
                continue
        
        logging.info(f"Análisis automático completado: {proyectos_analizados} proyectos analizados, {alertas_enviadas} alertas enviadas")
        
    except Exception as e:
        logging.error(f"Error en análisis automático de desviaciones: {e}")


# --- Reporte Semanal Automático ---
async def generar_reporte_semanal():
    """
    Genera y envía un reporte semanal con el resumen de avance de todos los proyectos.
    Se ejecuta automáticamente cada viernes a las 18:00.
    """
    if not ADMIN_EMAIL or not RESEND_API_KEY:
        logging.warning("No se puede enviar reporte semanal: ADMIN_EMAIL o RESEND_API_KEY no configurados")
        return
    
    try:
        logging.info("Iniciando generación de reporte semanal...")
        
        # Obtener todos los proyectos activos
        proyectos = await db.proyectos.find({}, {"_id": 0}).to_list(100)
        
        if not proyectos:
            logging.info("No hay proyectos para incluir en el reporte")
            return
        
        # Calcular métricas por proyecto
        proyectos_data = []
        total_costo_flotilla = 0
        total_volumen_excavado = 0
        total_pilas = 0
        total_anclas = 0
        total_muros = 0
        
        for proyecto in proyectos:
            proyecto_id = proyecto.get('id')
            tipos_actividades = proyecto.get('tipos_actividades', [])
            
            # Obtener avances semanales del proyecto
            avances = await db.avances_semanales.find(
                {"proyecto_id": proyecto_id},
                {"_id": 0}
            ).to_list(100)
            
            # Calcular totales
            volumen_excavado = sum((a.get('volumen_excavacion', 0) or 0) for a in avances)
            pilas_completadas = sum((a.get('pilas_completadas', 0) or 0) for a in avances)
            anclas_instaladas = sum((a.get('anclas_instaladas', 0) or 0) for a in avances)
            muros_completados = sum((a.get('muros_completados', 0) or 0) for a in avances)
            
            # Calcular costo de flotilla
            costo_m3 = proyecto.get('costo_m3', 150.0) or 150.0
            capacidad_camion = proyecto.get('capacidad_camion', 25.0) or 25.0
            costo_flotilla = volumen_excavado * costo_m3
            viajes_totales = int(volumen_excavado / capacidad_camion) if capacidad_camion > 0 else 0
            
            total_costo_flotilla += costo_flotilla
            total_volumen_excavado += volumen_excavado
            total_pilas += pilas_completadas
            total_anclas += anclas_instaladas
            total_muros += muros_completados
            
            # Obtener avances de esta semana (últimos 7 días)
            hace_7_dias = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            avances_semana = [a for a in avances if a.get('fecha', '') >= hace_7_dias[:10]]
            volumen_semana = sum((a.get('volumen_excavacion', 0) or 0) for a in avances_semana)
            pilas_semana = sum((a.get('pilas_completadas', 0) or 0) for a in avances_semana)
            anclas_semana = sum((a.get('anclas_instaladas', 0) or 0) for a in avances_semana)
            muros_semana = sum((a.get('muros_completados', 0) or 0) for a in avances_semana)
            costo_semana = volumen_semana * costo_m3
            
            # Metas del proyecto
            pilas_planeadas = proyecto.get('pilas_planeadas', 0) or 0
            anclas_planeadas = proyecto.get('anclas_planeadas', 0) or 0
            muros_planeados = proyecto.get('muros_planeados', 0) or 0
            volumen_planeado = proyecto.get('volumen_total_planeado', 0) or 0
            
            proyectos_data.append({
                'nombre': proyecto.get('nombre', 'Sin nombre'),
                'avance': proyecto.get('avance_actual', 0) or 0,
                'volumen_total': volumen_excavado,
                'volumen_planeado': volumen_planeado,
                'volumen_semana': volumen_semana,
                'pilas': pilas_completadas,
                'pilas_planeadas': pilas_planeadas,
                'pilas_semana': pilas_semana,
                'anclas': anclas_instaladas,
                'anclas_planeadas': anclas_planeadas,
                'anclas_semana': anclas_semana,
                'muros': muros_completados,
                'muros_planeados': muros_planeados,
                'muros_semana': muros_semana,
                'costo_flotilla_total': costo_flotilla,
                'costo_flotilla_semana': costo_semana,
                'viajes_totales': viajes_totales,
                'semanas_registradas': len(avances),
                'ubicacion': proyecto.get('ubicacion', 'N/A'),
                'tipos_actividades': tipos_actividades
            })
        
        # Ordenar por avance descendente
        proyectos_data.sort(key=lambda x: x['avance'], reverse=True)
        
        # Generar HTML del reporte
        fecha_reporte = datetime.now(timezone.utc).strftime('%d/%m/%Y')
        semana_num = datetime.now(timezone.utc).isocalendar()[1]
        
        # Tabla de proyectos
        proyectos_rows = ""
        for p in proyectos_data:
            avance_color = "#22c55e" if p['avance'] >= 75 else ("#eab308" if p['avance'] >= 50 else "#ef4444")
            
            # Construir métricas adicionales según el tipo de proyecto
            metricas_extra = []
            if p['pilas_planeadas'] > 0:
                metricas_extra.append(f"🔵 Pilas: {p['pilas']}/{p['pilas_planeadas']} (+{p['pilas_semana']} sem)")
            if p['anclas_planeadas'] > 0:
                metricas_extra.append(f"⚓ Anclas: {p['anclas']}/{p['anclas_planeadas']} (+{p['anclas_semana']} sem)")
            if p['muros_planeados'] > 0:
                metricas_extra.append(f"🧱 Muros: {p['muros']}/{p['muros_planeados']} (+{p['muros_semana']} sem)")
            
            metricas_html = "<br>".join(metricas_extra) if metricas_extra else ""
            
            proyectos_rows += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #e5e5e5;">
                    <strong>{p['nombre']}</strong>
                    <br><span style="font-size: 12px; color: #6b7280;">{p['ubicacion']}</span>
                    {f'<br><span style="font-size: 11px; color: #4b5563; margin-top: 4px; display: block;">{metricas_html}</span>' if metricas_html else ''}
                </td>
                <td style="padding: 12px; border-bottom: 1px solid #e5e5e5; text-align: center;">
                    <span style="background: {avance_color}; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold;">
                        {p['avance']:.1f}%
                    </span>
                </td>
                <td style="padding: 12px; border-bottom: 1px solid #e5e5e5; text-align: right; font-family: monospace;">
                    {p['volumen_semana']:,.0f} m³
                </td>
                <td style="padding: 12px; border-bottom: 1px solid #e5e5e5; text-align: right; font-family: monospace;">
                    ${p['costo_flotilla_semana']:,.2f}
                </td>
                <td style="padding: 12px; border-bottom: 1px solid #e5e5e5; text-align: right; font-family: monospace;">
                    ${p['costo_flotilla_total']:,.2f}
                </td>
            </tr>
            """
        
        # Tabla de desglose de flotillas
        flotilla_rows = ""
        for p in proyectos_data:
            if p['volumen_total'] > 0:
                flotilla_rows += f"""
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e5e5;">{p['nombre']}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e5e5; text-align: right;">{p['volumen_total']:,.0f} m³</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e5e5; text-align: right;">{p['viajes_totales']:,}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #e5e5e5; text-align: right; font-weight: bold;">${p['costo_flotilla_total']:,.2f}</td>
                </tr>
                """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #994B49 0%, #B85C5A 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">📊 Reporte Semanal</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 16px;">
                    DrON Topografía - Semana {semana_num} ({fecha_reporte})
                </p>
            </div>
            
            <div style="background: #fff; padding: 30px; border: 1px solid #e5e5e5; border-top: none;">
                
                <!-- KPIs Principales - Primera fila -->
                <div style="display: flex; gap: 15px; margin-bottom: 15px;">
                    <div style="flex: 1; background: #f0fdf4; padding: 15px; border-radius: 10px; text-align: center;">
                        <div style="font-size: 28px; font-weight: bold; color: #16a34a;">{len(proyectos_data)}</div>
                        <div style="color: #166534; font-size: 12px;">Proyectos</div>
                    </div>
                    <div style="flex: 1; background: #fef3c7; padding: 15px; border-radius: 10px; text-align: center;">
                        <div style="font-size: 28px; font-weight: bold; color: #d97706;">{total_volumen_excavado:,.0f}</div>
                        <div style="color: #92400e; font-size: 12px;">m³ Excavados</div>
                    </div>
                    <div style="flex: 1; background: #fee2e2; padding: 15px; border-radius: 10px; text-align: center;">
                        <div style="font-size: 28px; font-weight: bold; color: #dc2626;">${total_costo_flotilla:,.0f}</div>
                        <div style="color: #991b1b; font-size: 12px;">Gasto Flotillas</div>
                    </div>
                </div>
                
                <!-- KPIs Secundarios - Segunda fila (Pilas, Anclas, Muros) -->
                <div style="display: flex; gap: 15px; margin-bottom: 30px;">
                    <div style="flex: 1; background: #dbeafe; padding: 15px; border-radius: 10px; text-align: center;">
                        <div style="font-size: 28px; font-weight: bold; color: #2563eb;">{total_pilas:,}</div>
                        <div style="color: #1e40af; font-size: 12px;">🔵 Pilas Totales</div>
                    </div>
                    <div style="flex: 1; background: #ccfbf1; padding: 15px; border-radius: 10px; text-align: center;">
                        <div style="font-size: 28px; font-weight: bold; color: #0d9488;">{total_anclas:,}</div>
                        <div style="color: #115e59; font-size: 12px;">⚓ Anclas Totales</div>
                    </div>
                    <div style="flex: 1; background: #f3e8ff; padding: 15px; border-radius: 10px; text-align: center;">
                        <div style="font-size: 28px; font-weight: bold; color: #9333ea;">{total_muros:,}</div>
                        <div style="color: #6b21a8; font-size: 12px;">🧱 Muros Totales</div>
                    </div>
                </div>
                
                <!-- Tabla de Proyectos -->
                <h2 style="color: #994B49; border-bottom: 2px solid #994B49; padding-bottom: 10px;">
                    📋 Resumen por Proyecto
                </h2>
                
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
                    <thead>
                        <tr style="background: #f3f4f6;">
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e5e5e5;">Proyecto</th>
                            <th style="padding: 12px; text-align: center; border-bottom: 2px solid #e5e5e5;">Avance</th>
                            <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e5e5;">Vol. Semana</th>
                            <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e5e5;">Costo Semana</th>
                            <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e5e5e5;">Costo Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {proyectos_rows}
                    </tbody>
                </table>
                
                <!-- Desglose de Flotillas -->
                <h2 style="color: #994B49; border-bottom: 2px solid #994B49; padding-bottom: 10px;">
                    🚛 Desglose de Costos de Flotilla
                </h2>
                
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <thead>
                        <tr style="background: #fef2f2;">
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #fecaca;">Proyecto</th>
                            <th style="padding: 10px; text-align: right; border-bottom: 2px solid #fecaca;">Volumen</th>
                            <th style="padding: 10px; text-align: right; border-bottom: 2px solid #fecaca;">Viajes</th>
                            <th style="padding: 10px; text-align: right; border-bottom: 2px solid #fecaca;">Costo Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {flotilla_rows}
                        <tr style="background: #fee2e2; font-weight: bold;">
                            <td style="padding: 10px;">TOTAL</td>
                            <td style="padding: 10px; text-align: right;">{total_volumen_excavado:,.0f} m³</td>
                            <td style="padding: 10px; text-align: right;">-</td>
                            <td style="padding: 10px; text-align: right; color: #dc2626;">${total_costo_flotilla:,.2f}</td>
                        </tr>
                    </tbody>
                </table>
                
                <div style="margin-top: 30px; padding: 15px; background: #f9fafb; border-radius: 8px; border-left: 4px solid #994B49;">
                    <p style="margin: 0; color: #6b7280; font-size: 12px;">
                        Este reporte se genera automáticamente cada viernes a las 18:00 hrs.
                        Los costos de flotilla se calculan con base en el volumen excavado y el costo por m³ configurado en cada proyecto.
                    </p>
                </div>
            </div>
            
            <div style="text-align: center; padding: 20px; color: #6b7280; font-size: 12px;">
                <p>DrON Topografía © 2025</p>
            </div>
        </body>
        </html>
        """
        
        # Enviar email
        params = {
            "from": "DrON Topografía <onboarding@resend.dev>",
            "to": [ADMIN_EMAIL],
            "subject": f"📊 Reporte Semanal - Semana {semana_num} - DrON Topografía",
            "html": html_content
        }
        
        await asyncio.to_thread(resend.Emails.send, params)
        logging.info(f"Reporte semanal enviado exitosamente a {ADMIN_EMAIL}")
        
    except Exception as e:
        logging.error(f"Error generando reporte semanal: {e}")
        import traceback
        traceback.print_exc()


@app.on_event("startup")
async def startup_event():
    """Inicia el scheduler para reportes automáticos"""
    # Programar reporte semanal cada viernes a las 18:00
    scheduler.add_job(
        generar_reporte_semanal,
        CronTrigger(day_of_week='fri', hour=18, minute=0),
        id='reporte_semanal',
        replace_existing=True
    )
    
    # Programar análisis de desviaciones cada lunes a las 9:00
    scheduler.add_job(
        analizar_desviaciones_todos_proyectos,
        CronTrigger(day_of_week='mon', hour=9, minute=0),
        id='analisis_desviaciones',
        replace_existing=True
    )
    
    scheduler.start()
    logging.info("Scheduler iniciado - Reporte semanal (viernes 18:00) y Análisis de desviaciones (lunes 9:00)")


@app.on_event("shutdown")
async def shutdown_db_client():
    scheduler.shutdown()
    client.close()
