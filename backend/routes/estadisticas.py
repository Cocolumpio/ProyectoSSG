"""
Rutas de Estadísticas - DrON Topografía
"""
from fastapi import APIRouter
from core.config import get_db

router = APIRouter(prefix="/estadisticas", tags=["Estadísticas"])


@router.get("/resumen")
async def obtener_resumen():
    """Obtiene un resumen de estadísticas generales"""
    db = get_db()
    
    # Contar documentos
    total_proyectos = await db.proyectos.count_documents({})
    total_vuelos = await db.vuelos.count_documents({})
    
    # Obtener proyectos para calcular promedios
    proyectos = await db.proyectos.find({}, {"_id": 0}).to_list(100)
    
    # Calcular avance promedio
    avances = [p.get('avance_actual', 0) or 0 for p in proyectos]
    avance_promedio = sum(avances) / len(avances) if avances else 0
    
    # Calcular volumen total
    volumen_total = sum(p.get('volumen_excavado_total', 0) or p.get('volumen_total_planeado', 0) or 0 for p in proyectos)
    
    return {
        "totalProyectos": total_proyectos,
        "totalVuelos": total_vuelos,
        "avancePromedio": round(avance_promedio, 1),
        "volumenTotal": volumen_total
    }
