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
    muros_completados: Optional[float] = None  # Área de muros completados en m²
    imagenes: List[str] = []  # URLs de las imágenes del vuelo
    # ---- DEM Volumetría ----
    dem_gridfs_id: Optional[str] = None  # GridFS ID del DEM TIFF
    dem_filename: Optional[str] = None
    dem_uploaded_at: Optional[str] = None
    dem_metadata: Optional[dict] = None  # crs, bounds, resolution, etc.
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
    muros_completados: Optional[float] = None  # Área de muros completados en m²
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
    muros_completados: Optional[float] = None

class CaraExcavacion(BaseModel):
    """Configuración de una de las 4 caras de la excavación.

    Cada cara tiene su propia lista lineal de pilas y anclas, cada celda
    almacenada como booleano (True = completada, False = pendiente).
    """
    model_config = ConfigDict(extra="ignore")

    nombre: str = ""
    pilas: int = 0
    anclas: int = 0
    pilas_estados: List[bool] = []
    anclas_estados: List[bool] = []


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
    muros_planeados: float = 0  # Área total de muros planeados en m²
    anclas_planeadas: int = 0  # Número total de anclas planeadas
    # Matriz de pilas/anclas dividida en 4 caras de excavación
    caras_excavacion: List[CaraExcavacion] = []
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
    muros_planeados: float = 0
    anclas_planeadas: int = 0
    # Matriz de pilas/anclas por 4 caras de excavación
    caras_excavacion: List[CaraExcavacion] = []
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
    muros_planeados: Optional[float] = None
    anclas_planeadas: Optional[int] = None
    # Matriz de pilas/anclas por 4 caras de excavación
    caras_excavacion: Optional[List[CaraExcavacion]] = None
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


@api_router.delete("/auth/users/{user_id}")
async def eliminar_usuario(user_id: str, current_user: dict = Depends(get_current_admin)):
    """Eliminar permanentemente un usuario (solo admin).

    Reglas de seguridad:
    - El admin NO puede eliminarse a sí mismo.
    - No se permite eliminar al último administrador activo del sistema.
    - Si el usuario eliminado era cliente, se desasigna automáticamente de
      todos los proyectos donde estuviera vinculado.
    """
    user = await db.usuarios.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user_id == current_user.get("id"):
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")

    # Proteger contra dejar al sistema sin administradores
    if user.get("rol") == "admin":
        admins_activos = await db.usuarios.count_documents({"rol": "admin", "activo": True})
        if admins_activos <= 1:
            raise HTTPException(
                status_code=400,
                detail="No se puede eliminar al último administrador activo"
            )

    # Eliminar usuario
    result = await db.usuarios.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Si era cliente, desasignarlo de todos los proyectos
    if user.get("rol") == "client":
        await db.proyectos.update_many(
            {"clientes_asignados": user_id},
            {"$pull": {"clientes_asignados": user_id}}
        )

    return {
        "message": f"Usuario '{user.get('nombre')}' eliminado correctamente",
        "user_id": user_id,
        "email": user.get("email"),
    }

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



app.include_router(api_router)

# Include modular routers (refactored from monolith)
from routes import (
    comparaciones as routes_comparaciones,
    exportar as routes_exportar,
    reporte_ejecutivo as routes_reporte_ejecutivo,
    solicitudes_vuelo as routes_solicitudes_vuelo,
    cronograma as routes_cronograma,
    maquinaria_ia as routes_maquinaria_ia,
    analisis_ia as routes_analisis_ia,
    dem_volumetry as routes_dem_volumetry,
    presupuesto as routes_presupuesto,
    caras_excavacion as routes_caras_excavacion,
    comparativa_semanal as routes_comparativa_semanal,
)
app.include_router(routes_comparaciones.router)
app.include_router(routes_exportar.router)
app.include_router(routes_reporte_ejecutivo.router)
app.include_router(routes_solicitudes_vuelo.router)
app.include_router(routes_cronograma.router)
app.include_router(routes_maquinaria_ia.router)
app.include_router(routes_analisis_ia.router)
app.include_router(routes_dem_volumetry.router)
app.include_router(routes_presupuesto.router)
app.include_router(routes_caras_excavacion.router)
app.include_router(routes_comparativa_semanal.router)

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
