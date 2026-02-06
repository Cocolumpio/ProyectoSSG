"""
Modelos Pydantic para la API de DrON Topografía
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone


# --- Modelos Base ---
class Coordinates(BaseModel):
    lat: float
    lng: float

class Volumetria(BaseModel):
    excavacion: float = 0.0
    relleno: float = 0.0
    materiales: float = 0.0


# --- Modelos de Autenticación ---
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


# --- Modelos de Avance Semanal ---
class AvanceSemanal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    proyecto_id: str
    semana: int
    fecha: str
    pix4d_url: str
    descripcion: Optional[str] = None
    porcentaje_avance: Optional[float] = None
    volumen_excavacion: Optional[float] = None  # Volumen excavado en m³
    imagenes: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AvanceSemanalCreate(BaseModel):
    semana: int
    fecha: str
    pix4d_url: str
    descripcion: Optional[str] = None
    porcentaje_avance: Optional[float] = None
    volumen_excavacion: Optional[float] = None
    imagenes: List[str] = []

class AvanceSemanalUpdate(BaseModel):
    """Modelo para actualización parcial de avance semanal"""
    semana: Optional[int] = None
    fecha: Optional[str] = None
    pix4d_url: Optional[str] = None
    descripcion: Optional[str] = None
    porcentaje_avance: Optional[float] = None
    volumen_excavacion: Optional[float] = None


# --- Modelos de Proyecto ---
class Proyecto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nombre: str
    ubicacion: str
    direccion: Optional[str] = None
    coordenadas: Coordinates
    fecha_inicio: str
    fecha_fin_planeada: str
    avance_actual: float = 0.0
    descripcion: Optional[str] = None
    pix4d_url: Optional[str] = None
    volumetria: Optional[Volumetria] = None
    capacidad_camion: float = 25.0
    costo_m3: float = 150.0
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
    volumetria: Optional[Volumetria] = None
    capacidad_camion: float = 25.0
    costo_m3: float = 150.0

class ProyectoUpdate(BaseModel):
    nombre: Optional[str] = None
    ubicacion: Optional[str] = None
    direccion: Optional[str] = None
    coordenadas: Optional[Coordinates] = None
    fecha_inicio: Optional[str] = None
    fecha_fin_planeada: Optional[str] = None
    avance_actual: Optional[float] = None
    descripcion: Optional[str] = None
    pix4d_url: Optional[str] = None
    volumetria: Optional[Volumetria] = None
    capacidad_camion: Optional[float] = None
    costo_m3: Optional[float] = None


# --- Modelos de Vuelo ---
class Vuelo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    proyecto_id: str
    fecha_vuelo: str
    duracion_minutos: int
    area_cubierta: float
    num_imagenes: int
    volumetria: Volumetria = Field(default_factory=Volumetria)
    archivo_nube_puntos: Optional[str] = None
    pix4d_url: Optional[str] = None
    notas: Optional[str] = None
    estado: str = "completado"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VueloCreate(BaseModel):
    proyecto_id: str
    fecha_vuelo: str
    duracion_minutos: int
    area_cubierta: float
    num_imagenes: int
    volumetria: Optional[Volumetria] = None
    pix4d_url: Optional[str] = None
    notas: Optional[str] = None
    estado: str = "completado"

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


# --- Modelos de Solicitud de Vuelo ---
class SolicitudVuelo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nombre_proyecto: str
    fecha_inicio_proyecto: str
    fecha_fin_proyecto: str
    fecha_vuelo_deseada: str
    hora_preferencia: Optional[str] = None
    notas: Optional[str] = None
    estado: str = "pendiente"
    cliente_id: Optional[str] = None
    cliente_email: Optional[str] = None
    cliente_nombre: Optional[str] = None
    comentario_admin: Optional[str] = None
    fecha_respuesta: Optional[str] = None
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
