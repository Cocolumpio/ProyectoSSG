from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from urllib.parse import quote
import shutil
import laspy
import numpy as np
import zipfile
import io
import resend

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
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'ianalejandrogn@gmail.com')

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
    pix4d_url: str  # URL del modelo 3D de Pix4D
    descripcion: Optional[str] = None
    porcentaje_avance: Optional[float] = None  # Porcentaje de avance en esa semana
    volumen_excavacion: Optional[float] = None  # Volumen quitado en m³
    imagenes: List[str] = []  # URLs de las imágenes del vuelo
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AvanceSemanalCreate(BaseModel):
    semana: int
    fecha: str
    pix4d_url: str
    descripcion: Optional[str] = None
    porcentaje_avance: Optional[float] = None
    volumen_excavacion: Optional[float] = None  # Volumen quitado en m³
    imagenes: List[str] = []  # URLs de las imágenes del vuelo

class Proyecto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str
    ubicacion: str
    coordenadas: Coordinates
    fecha_inicio: str
    fecha_fin_planeada: str
    avance_actual: float = 0.0  # Porcentaje 0-100
    descripcion: Optional[str] = None
    pix4d_url: Optional[str] = None  # URL del modelo 3D
    volumetria: Optional[Volumetria] = None  # Volumetrías del proyecto
    # Configuración de flotilla de camiones
    capacidad_camion: float = 25.0  # m³ por camión (default 25 m³)
    costo_viaje_camion: float = 2500.0  # Costo por viaje en MXN (default $2,500)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProyectoCreate(BaseModel):
    nombre: str
    ubicacion: str
    coordenadas: Coordinates
    fecha_inicio: str
    fecha_fin_planeada: str
    descripcion: Optional[str] = None
    pix4d_url: Optional[str] = None
    avance_actual: float = 0.0
    volumetria: Optional[Volumetria] = None
    # Configuración de flotilla
    capacidad_camion: float = 25.0
    costo_viaje_camion: float = 2500.0

class ProyectoUpdate(BaseModel):
    nombre: Optional[str] = None
    ubicacion: Optional[str] = None
    coordenadas: Optional[Coordinates] = None
    fecha_inicio: Optional[str] = None
    fecha_fin_planeada: Optional[str] = None
    avance_actual: Optional[float] = None
    descripcion: Optional[str] = None
    pix4d_url: Optional[str] = None
    volumetria: Optional[Volumetria] = None
    # Configuración de flotilla
    capacidad_camion: Optional[float] = None
    costo_viaje_camion: Optional[float] = None

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SolicitudVueloCreate(BaseModel):
    nombre_proyecto: str
    fecha_inicio_proyecto: str
    fecha_fin_proyecto: str
    fecha_vuelo_deseada: str
    hora_preferencia: Optional[str] = None
    notas: Optional[str] = None

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

# --- Proyectos ---
@api_router.post("/proyectos", response_model=Proyecto)
async def crear_proyecto(proyecto: ProyectoCreate):
    proyecto_obj = Proyecto(**proyecto.model_dump())
    doc = proyecto_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.proyectos.insert_one(doc)
    return proyecto_obj

@api_router.get("/proyectos", response_model=List[Proyecto])
async def listar_proyectos():
    proyectos = await db.proyectos.find({}, {"_id": 0}).to_list(1000)
    for p in proyectos:
        if isinstance(p.get('created_at'), str):
            p['created_at'] = datetime.fromisoformat(p['created_at'])
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
    
    # Retornar el proyecto actualizado
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if isinstance(proyecto.get('created_at'), str):
        proyecto['created_at'] = datetime.fromisoformat(proyecto['created_at'])
    return proyecto

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
    
    return nuevo_avance

@api_router.put("/proyectos/{proyecto_id}/avances-semanales/{avance_id}", response_model=AvanceSemanal)
async def actualizar_avance_semanal(proyecto_id: str, avance_id: str, avance: AvanceSemanalCreate):
    """Actualizar un avance semanal existente"""
    update_data = avance.model_dump()
    
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
    costo_por_viaje = proyecto.get('costo_viaje_camion', 2500.0) or 2500.0
    
    # Obtener avances semanales
    avances = await db.avances_semanales.find(
        {"proyecto_id": proyecto_id}, 
        {"_id": 0}
    ).sort("semana", 1).to_list(100)
    
    # Calcular totales
    volumen_total = sum(a.get('volumen_excavacion', 0) or 0 for a in avances)
    total_viajes = int(volumen_total / capacidad_camion) if capacidad_camion > 0 else 0
    costo_total_estimado = total_viajes * costo_por_viaje
    
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
        ["Costo por Viaje:", f"${costo_por_viaje:,.2f} MXN"],
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
            costo = viajes * costo_por_viaje
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
