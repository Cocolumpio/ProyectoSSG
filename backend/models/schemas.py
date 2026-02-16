"""
Modelos Pydantic para DrON Topografía
"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone


# --- Auth Models ---
class UserRole:
    ADMIN = "admin"
    CLIENT = "client"


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    nombre: str
    password_hash: str
    rol: str = "client"
    activo: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserCreate(BaseModel):
    email: EmailStr
    nombre: str
    password: str
    rol: str = "client"


class UserResponse(BaseModel):
    id: str
    email: str
    nombre: str
    rol: str
    activo: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
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
    semana: int
    fecha: str
    pix4d_url: Optional[str] = None
    modelo_3d_url: Optional[str] = None
    modelo_3d_tipo: Optional[str] = None
    thumbnail_url: Optional[str] = None
    descripcion: Optional[str] = None
    porcentaje_avance: Optional[float] = None
    volumen_excavacion: Optional[float] = None
    imagenes: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AvanceSemanalCreate(BaseModel):
    semana: int
    fecha: str
    pix4d_url: Optional[str] = None
    descripcion: Optional[str] = None
    porcentaje_avance: Optional[float] = None
    volumen_excavacion: Optional[float] = None
    imagenes: List[str] = []


class AvanceSemanalUpdate(BaseModel):
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
    direccion: Optional[str] = None
    coordenadas: Coordinates
    fecha_inicio: str
    fecha_fin_planeada: str
    avance_actual: float = 0.0
    volumen_total_planeado: Optional[float] = None
    semanas_planeadas: int = 0
    descripcion: Optional[str] = None
    pix4d_url: Optional[str] = None
    volumetria: Optional[Volumetria] = None
    capacidad_camion: Optional[float] = 25.0
    costo_m3: Optional[float] = 150.0
    clientes_asignados: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProyectoCreate(BaseModel):
    nombre: str
    ubicacion: str
    direccion: Optional[str] = None
    coordenadas: Coordinates
    fecha_inicio: str
    fecha_fin_planeada: str
    avance_actual: float = 0.0
    volumen_total_planeado: Optional[float] = None
    semanas_planeadas: int = 0
    descripcion: Optional[str] = None
    pix4d_url: Optional[str] = None
    volumetria: Optional[Volumetria] = None
    capacidad_camion: Optional[float] = 25.0
    costo_m3: Optional[float] = 150.0


class ProyectoUpdate(BaseModel):
    nombre: Optional[str] = None
    ubicacion: Optional[str] = None
    direccion: Optional[str] = None
    coordenadas: Optional[Coordinates] = None
    fecha_inicio: Optional[str] = None
    fecha_fin_planeada: Optional[str] = None
    avance_actual: Optional[float] = None
    volumen_total_planeado: Optional[float] = None
    semanas_planeadas: Optional[int] = None
    descripcion: Optional[str] = None
    pix4d_url: Optional[str] = None
    volumetria: Optional[Volumetria] = None
    capacidad_camion: Optional[float] = None
    costo_m3: Optional[float] = None


# --- Frentes y Cronograma Models ---
class Actividad(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    descripcion: str
    num_pilas: int = 0
    num_anclas: int = 0
    fecha_inicio: str
    fecha_fin: str
    fecha_descabece: Optional[str] = None
    dias: int = 0
    pilas_completadas: int = 0
    anclas_instaladas: int = 0
    estado: str = "pendiente"  # pendiente, en_progreso, completada


class Frente(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    proyecto_id: str
    nombre: str
    descripcion: Optional[str] = None
    actividades: List[Actividad] = []
    orden: int = 1
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FrenteCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    actividades: List[Actividad] = []
    orden: int = 1


class AnalisisFotoIA(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    proyecto_id: str
    avance_id: str
    semana: int
    fecha_analisis: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pilas_detectadas: int = 0
    anclas_detectadas: int = 0
    pilas_en_proceso: int = 0
    porcentaje_avance_estimado: float = 0.0
    estado_proyecto: str = "EN_TIEMPO"  # EN_TIEMPO, ADELANTADO, RETRASADO
    confianza_deteccion: str = "MEDIA"  # ALTA, MEDIA, BAJA
    observaciones: Optional[str] = None
    recomendaciones: Optional[str] = None
    imagen_url: Optional[str] = None




# --- Flight Models ---
class Vuelo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    proyecto_id: str
    fecha_vuelo: str
    duracion_minutos: int
    area_cubierta: Optional[float] = None
    num_imagenes: Optional[int] = None
    estado: str = "completado"
    notas: Optional[str] = None
    semana_vinculada: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VueloCreate(BaseModel):
    proyecto_id: str
    fecha_vuelo: str
    duracion_minutos: int
    area_cubierta: Optional[float] = None
    num_imagenes: Optional[int] = None
    estado: str = "completado"
    notas: Optional[str] = None
    semana_vinculada: Optional[int] = None


class VueloUpdate(BaseModel):
    proyecto_id: Optional[str] = None
    fecha_vuelo: Optional[str] = None
    duracion_minutos: Optional[int] = None
    area_cubierta: Optional[float] = None
    num_imagenes: Optional[int] = None
    estado: Optional[str] = None
    notas: Optional[str] = None
    semana_vinculada: Optional[int] = None


# --- Flight Request Models ---
class SolicitudVuelo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cliente_id: str
    cliente_email: str
    cliente_nombre: str
    proyecto_nombre: str
    ubicacion: str
    coordenadas: Optional[Coordinates] = None
    fecha_preferida: str
    hora_preferida: Optional[str] = None
    notas: Optional[str] = None
    estado: str = "pendiente"
    admin_notas: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SolicitudVueloCreate(BaseModel):
    proyecto_nombre: str
    ubicacion: str
    coordenadas: Optional[Coordinates] = None
    fecha_preferida: str
    hora_preferida: Optional[str] = None
    notas: Optional[str] = None


class SolicitudVueloUpdate(BaseModel):
    estado: Optional[str] = None
    admin_notas: Optional[str] = None
