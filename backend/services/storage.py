"""
Servicio de almacenamiento de archivos usando MongoDB GridFS.
Permite almacenar archivos grandes de forma persistente en Kubernetes.
"""
import logging
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from bson import ObjectId
import io
from typing import Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class GridFSStorage:
    """Clase para manejar almacenamiento de archivos en MongoDB GridFS"""
    
    def __init__(self, db):
        self.db = db
        self.fs = AsyncIOMotorGridFSBucket(db)
    
    async def save_file(
        self, 
        content: bytes, 
        filename: str, 
        content_type: str = "application/octet-stream",
        metadata: dict = None
    ) -> str:
        """
        Guarda un archivo en GridFS y retorna el file_id como string.
        
        Args:
            content: Bytes del archivo
            filename: Nombre del archivo
            content_type: Tipo MIME del archivo
            metadata: Metadatos adicionales (proyecto_id, avance_id, etc.)
        
        Returns:
            String con el ID del archivo en GridFS
        """
        try:
            file_metadata = {
                "contentType": content_type,
                "uploadDate": datetime.now(timezone.utc).isoformat(),
                **(metadata or {})
            }
            
            file_id = await self.fs.upload_from_stream(
                filename,
                io.BytesIO(content),
                metadata=file_metadata
            )
            
            logger.info(f"Archivo guardado en GridFS: {filename} ({len(content)} bytes)")
            return str(file_id)
            
        except Exception as e:
            logger.error(f"Error guardando archivo en GridFS: {e}")
            raise
    
    async def get_file(self, file_id: str) -> Tuple[Optional[bytes], Optional[dict]]:
        """
        Obtiene un archivo de GridFS por su ID.
        
        Args:
            file_id: ID del archivo como string
        
        Returns:
            Tuple de (contenido del archivo, metadatos) o (None, None) si no existe
        """
        try:
            grid_out = await self.fs.open_download_stream(ObjectId(file_id))
            content = await grid_out.read()
            metadata = grid_out.metadata
            
            return content, metadata
            
        except Exception as e:
            logger.error(f"Error obteniendo archivo de GridFS ({file_id}): {e}")
            return None, None
    
    async def delete_file(self, file_id: str) -> bool:
        """
        Elimina un archivo de GridFS.
        
        Args:
            file_id: ID del archivo como string
        
        Returns:
            True si se eliminó correctamente, False si hubo error
        """
        try:
            await self.fs.delete(ObjectId(file_id))
            logger.info(f"Archivo eliminado de GridFS: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando archivo de GridFS ({file_id}): {e}")
            return False
    
    async def file_exists(self, file_id: str) -> bool:
        """
        Verifica si un archivo existe en GridFS.
        
        Args:
            file_id: ID del archivo como string
        
        Returns:
            True si existe, False si no
        """
        try:
            cursor = self.fs.find({"_id": ObjectId(file_id)})
            files = await cursor.to_list(1)
            return len(files) > 0
        except Exception as e:
            logger.error(f"Error verificando archivo en GridFS: {e}")
            return False


# Instancia global del storage (se inicializa con la DB)
_storage: Optional[GridFSStorage] = None


def get_storage(db) -> GridFSStorage:
    """Obtiene la instancia del storage, creándola si no existe"""
    global _storage
    if _storage is None:
        _storage = GridFSStorage(db)
    return _storage
