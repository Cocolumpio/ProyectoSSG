"""
Servicios para DrON Topografía
"""
from .database import (
    db,
    client,
    usuarios_collection,
    proyectos_collection,
    vuelos_collection,
    avances_collection,
    solicitudes_collection,
    get_db,
    init_db,
    cleanup_obsolete_collections,
)
from .auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    require_admin,
    authenticate_user,
    security,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from .thumbnails import (
    generate_ply_thumbnail,
    generate_thumbnail_async,
    thumbnail_executor,
)

__all__ = [
    # Database
    "db",
    "client",
    "usuarios_collection",
    "proyectos_collection",
    "vuelos_collection",
    "avances_collection",
    "solicitudes_collection",
    "get_db",
    "init_db",
    "cleanup_obsolete_collections",
    # Auth
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "get_current_user",
    "require_admin",
    "authenticate_user",
    "security",
    "SECRET_KEY",
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    # Thumbnails
    "generate_ply_thumbnail",
    "generate_thumbnail_async",
    "thumbnail_executor",
]
