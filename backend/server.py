from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import shutil
import laspy
import numpy as np


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProyectoCreate(BaseModel):
    nombre: str
    ubicacion: str
    coordenadas: Coordinates
    fecha_inicio: str
    fecha_fin_planeada: str
    descripcion: Optional[str] = None
    pix4d_url: Optional[str] = None
    volumetria: Optional[Volumetria] = None

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

class Volumetria(BaseModel):
    excavacion: float  # m³
    relleno: float  # m³
    materiales: float  # m³

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
    result = await db.avances.update_one(
        {"proyecto_id": proyecto_id},
        {"$set": doc},
        upsert=True
    )
    return avance

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
