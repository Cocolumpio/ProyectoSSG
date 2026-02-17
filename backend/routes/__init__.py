"""
Inicialización de rutas - DrON Topografía

Este módulo organiza las rutas en submódulos para mejor mantenibilidad.
Los routers individuales se pueden usar directamente o a través del router combinado.
"""
from fastapi import APIRouter

# Router principal que combina todos los sub-routers
# Nota: Por ahora el server.py contiene todas las rutas directamente.
# Esta estructura está preparada para una refactorización gradual.

# Routers disponibles:
# - auth: Autenticación y gestión de usuarios
# - proyectos: CRUD de proyectos
# - vuelos: Gestión de vuelos
# - estadisticas: Métricas y estadísticas

__all__ = ['auth', 'proyectos', 'vuelos', 'estadisticas']
