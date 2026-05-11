"""
Routers modulares - DrON Topografía

Cada submódulo expone su propio `router: APIRouter(prefix="/api")` y es
incluído en `server.py` vía `app.include_router(...)`.

Submódulos disponibles:
- comparaciones: Comparación de avances con PDF del residente (Gemini Vision)
- exportar: Exportación de métricas a Excel y PDF
- reporte_ejecutivo: Reporte ejecutivo PDF por proyecto
- solicitudes_vuelo: Solicitudes de vuelo (clientes) + emails (admin)
- cronograma: Importación/actualización de cronograma + frentes
- maquinaria_ia: Análisis IA del catálogo de maquinaria + comparación de planes
- analisis_ia: Análisis IA de fotos y generación de reportes IA
"""

__all__ = [
    "comparaciones",
    "exportar",
    "reporte_ejecutivo",
    "solicitudes_vuelo",
    "cronograma",
    "maquinaria_ia",
    "analisis_ia",
]
