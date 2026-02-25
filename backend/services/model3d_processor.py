"""
Servicio para procesar modelos 3D PLY y crear versiones preview optimizadas.
"""
import logging
import tempfile
import os
import numpy as np
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Límite de puntos para la versión preview (200K para evitar crashes)
PREVIEW_MAX_POINTS = 200000


async def create_preview_ply(
    original_content: bytes,
    max_points: int = PREVIEW_MAX_POINTS
) -> Tuple[Optional[bytes], dict]:
    """
    Crea una versión simplificada de un archivo PLY para visualización rápida.
    
    Args:
        original_content: Contenido del archivo PLY original
        max_points: Número máximo de puntos en la versión preview
        
    Returns:
        Tuple de (contenido del preview PLY, metadata)
    """
    try:
        import open3d as o3d
        
        # Guardar temporalmente para que open3d lo pueda leer
        with tempfile.NamedTemporaryFile(suffix='.ply', delete=False) as tmp_in:
            tmp_in.write(original_content)
            tmp_in_path = tmp_in.name
        
        try:
            # Leer la nube de puntos
            pcd = o3d.io.read_point_cloud(tmp_in_path)
            original_points = len(pcd.points)
            
            logger.info(f"PLY original: {original_points:,} puntos")
            
            if original_points <= max_points:
                # No necesita simplificación
                logger.info("No se requiere simplificación")
                return None, {"original_points": original_points, "simplified": False}
            
            # Calcular el ratio de submuestreo
            ratio = max_points / original_points
            
            # Usar submuestreo uniforme
            pcd_simplified = pcd.uniform_down_sample(every_k_points=int(1/ratio))
            
            simplified_points = len(pcd_simplified.points)
            logger.info(f"PLY simplificado: {simplified_points:,} puntos (de {original_points:,})")
            
            # Guardar la versión simplificada
            with tempfile.NamedTemporaryFile(suffix='.ply', delete=False) as tmp_out:
                tmp_out_path = tmp_out.name
            
            o3d.io.write_point_cloud(tmp_out_path, pcd_simplified, write_ascii=False)
            
            # Leer el contenido del archivo simplificado
            with open(tmp_out_path, 'rb') as f:
                simplified_content = f.read()
            
            # Limpiar archivo temporal de salida
            os.unlink(tmp_out_path)
            
            metadata = {
                "original_points": original_points,
                "preview_points": simplified_points,
                "simplified": True,
                "reduction_ratio": round(original_points / simplified_points, 2)
            }
            
            return simplified_content, metadata
            
        finally:
            # Limpiar archivo temporal de entrada
            if os.path.exists(tmp_in_path):
                os.unlink(tmp_in_path)
                
    except ImportError:
        logger.warning("open3d no está disponible, no se puede crear preview")
        return None, {"error": "open3d not available", "simplified": False}
    except Exception as e:
        logger.error(f"Error creando preview PLY: {e}")
        return None, {"error": str(e), "simplified": False}


def get_ply_point_count(content: bytes) -> int:
    """
    Obtiene el número de puntos de un archivo PLY leyendo solo el header.
    Más eficiente que cargar todo el archivo.
    """
    try:
        # Buscar el header
        header_end = content.find(b'end_header')
        if header_end == -1:
            return 0
        
        header = content[:header_end].decode('ascii', errors='ignore')
        
        # Buscar "element vertex NNNN"
        for line in header.split('\n'):
            if line.strip().startswith('element vertex'):
                parts = line.strip().split()
                if len(parts) >= 3:
                    return int(parts[2])
        
        return 0
    except Exception as e:
        logger.error(f"Error leyendo count de puntos PLY: {e}")
        return 0
