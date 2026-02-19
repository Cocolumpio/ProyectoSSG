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
    email: str
    nombre: str
    password_hash: str
    rol: str = "client"
    activo: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserCreate(BaseModel):
    email: str
    nombre: str
    password: str
    rol: str = "client"


class UserResponse(BaseModel):
    id: str
    email: str
    nombre: str
    rol: str
    activo: bool = True


class UserLogin(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
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
    excavacion: float = 0.0
    relleno: float = 0.0
    materiales: float = 0.0


class AvanceSemanal(BaseModel):
    model_config = ConfigDict(extra="ignore")
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
    pilas_completadas: Optional[int] = None
    anclas_instaladas: Optional[int] = None
    muros_completados: Optional[int] = None
    imagenes: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AvanceSemanalCreate(BaseModel):
    semana: int
    fecha: str
    pix4d_url: Optional[str] = None
    descripcion: Optional[str] = None
    porcentaje_avance: Optional[float] = None
    volumen_excavacion: Optional[float] = None
    pilas_completadas: Optional[int] = None
    anclas_instaladas: Optional[int] = None
    muros_completados: Optional[int] = None
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
    pilas_completadas: Optional[int] = None
    anclas_instaladas: Optional[int] = None
    muros_completados: Optional[int] = None


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
    # Tipos de actividades del proyecto
    actividades_tipo: List[str] = []
    # Métricas planeadas
    volumen_total_planeado: float = 0.0
    pilas_planeadas: int = 0
    muros_planeados: int = 0
    anclas_planeadas: int = 0
    # Métricas ejecutadas
    volumen_ejecutado: float = 0.0
    pilas_ejecutadas: int = 0
    muros_ejecutados: int = 0
    anclas_ejecutadas: int = 0
    # Cronograma
    semanas_planeadas: int = 0
    semanas_excavacion: int = 0
    semanas_pilas: int = 0
    semanas_muros: int = 0
    descripcion: Optional[str] = None
    pix4d_url: Optional[str] = None
    volumetria: Optional[Volumetria] = None
    # Configuración de flotilla de camiones
    capacidad_camion: float = 25.0
    costo_m3: float = 150.0
    clientes_asignados: List[str] = []
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
    actividades_tipo: List[str] = []
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
    clientes_asignados: Optional[List[str]] = None


# --- Flight Request Models ---
class SolicitudVuelo(BaseModel):
    model_config = ConfigDict(extra="ignore")
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


# --- Vuelos Models ---
class Vuelo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    proyecto_id: str
    fecha_vuelo: str
    duracion_minutos: int
    area_cubierta: float = 0.0
    num_imagenes: int = 0
    archivo_nube_puntos: Optional[str] = None
    pix4d_url: Optional[str] = None
    estado: str = "completado"
    notas: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VueloCreate(BaseModel):
    proyecto_id: str
    fecha_vuelo: str
    duracion_minutos: int
    area_cubierta: float = 0.0
    num_imagenes: int = 0
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


# --- Avances Hitos Models ---
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


# --- Frentes y Actividades Models ---
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
    estado: str = "pendiente"


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


# --- Análisis IA Models ---
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
    estado_proyecto: str = "EN_TIEMPO"
    confianza_deteccion: str = "MEDIA"
    observaciones: Optional[str] = None
    recomendaciones: Optional[str] = None
    imagen_url: Optional[str] = None


# --- Comparación de Avances con Residente ---
class MetricaComparacion(BaseModel):
    nombre: str
    unidad: str
    valor_dron: float = 0.0
    valor_residente: float = 0.0
    diferencia: float = 0.0
    diferencia_porcentaje: float = 0.0
    estado: str = "coincide"


class ComparacionAvance(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    proyecto_id: str
    semana: int
    fecha_comparacion: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pdf_url: str
    pdf_nombre: str
    metricas_residente: dict = {}
    metricas_dron: dict = {}
    comparaciones: List[MetricaComparacion] = []
    resumen_ia: str = ""
    discrepancias_detectadas: List[str] = []
    recomendaciones: List[str] = []
    estado_comparacion: str = "pendiente"
    avance_general_residente: float = 0.0
    avance_general_dron: float = 0.0
    confianza: str = "MEDIA"
    alerta_enviada: bool = False


class ComparacionAvanceCreate(BaseModel):
    semana: int
    pdf_nombre: str


# --- Notificaciones ---
class NotificationType:
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    ALERT = "alert"


class Notificacion(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tipo: str = "info"  # info, warning, error, success, alert
    titulo: str
    mensaje: str
    proyecto_id: Optional[str] = None
    proyecto_nombre: Optional[str] = None
    usuario_id: Optional[str] = None  # None = para todos los admins
    leida: bool = False
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    link: Optional[str] = None  # Link opcional para navegar
    metadata: Optional[dict] = None  # Datos adicionales


class NotificacionCreate(BaseModel):
    tipo: str = "info"
    titulo: str
    mensaje: str
    proyecto_id: Optional[str] = None
    proyecto_nombre: Optional[str] = None
    usuario_id: Optional[str] = None
    link: Optional[str] = None
    metadata: Optional[dict] = None
