# DrON Topografía - Product Requirements Document

## Estado Actual (Actualizado: 2025-12-17)
- **Sistema Funcional**: Dashboard multi-fase completamente operativo
- **Bug Fix**: Corregido bug de selección de proyectos (P0)
- **Nueva Funcionalidad**: Comparación de Avances Dron vs Residente con IA
- **Testing**: 100% de pruebas pasadas

## Nueva Funcionalidad: Comparación de Avances con IA

### Descripción
Permite comparar automáticamente los avances registrados por el sistema de drones con los reportes PDF del residente de obra, usando Gemini (IA) para extraer y analizar métricas.

### Flujo de Usuario
1. Abrir modal "Avances Semanales" de un proyecto
2. Click en botón "Comparar con Residente" en el header
3. Subir PDF del reporte del residente
4. El sistema analiza automáticamente con IA y muestra:
   - Avance general: Dron vs Residente
   - Tabla comparativa por métrica (excavación, anclas, muros)
   - Discrepancias detectadas (>5%)
   - Análisis y recomendaciones de IA
5. Historial de comparaciones guardado

### Métricas Comparadas
| Métrica | Unidad | Fuente Dron | Fuente PDF |
|---------|--------|-------------|------------|
| Excavación | m³ | volumen_excavacion | Excavación M3 |
| Pilas | pzas | pilas_completadas | Perforación PZA |
| Anclas | pzas | anclas_instaladas | Tensado PZA |
| Muros | m² | muros_completados | Lanzado M2 |

### Endpoints API
- `POST /api/proyectos/{id}/comparar-avance` - Subir y analizar PDF
- `GET /api/proyectos/{id}/comparaciones` - Historial de comparaciones
- `DELETE /api/proyectos/{id}/comparaciones/{id}` - Eliminar comparación

## Sistema de Fases de Construcción

### Fases Implementadas
- **Excavación**: Volumen total en m³
- **Cimentación**: Pilas + Anclas  
- **Edificación**: Muros

### Formulario de Nuevo Proyecto
- Checkboxes para seleccionar fases (pueden ser múltiples)
- Campos condicionales que aparecen al seleccionar cada fase:
  - Excavación → Volumen Total (m³)
  - Cimentación → Pilas Planeadas + Anclas Planeadas
  - Edificación → Muros Planeados

### Dashboard - Resumen del Proyecto
- **Avance Total**: Promedio de todas las fases activas
- **Avance por Fase**: Barras de progreso individuales para cada fase
- **Proyección de semanas**: Si no hay cronograma, calcula "~X sem restantes" basado en ritmo

### Avances Semanales - Campos Editables
- Pilas Completadas (azul)
- Anclas Instaladas (teal)
- Muros Completados (púrpura)
- Volumen Excavado (naranja)
- Los campos solo se muestran si el proyecto tiene esa fase configurada

### Cálculo de Avance
- Backend recalcula automáticamente al guardar cualquier métrica
- Avance TOTAL = promedio de todas las fases activas
- Ejemplo: Torre Corporativa Demo
  - Excavación: 84% (21,000/25,000 m³)
  - Cimentación: 69% (promedio pilas+anclas)
  - Edificación: 11% (5/45 muros)
  - **TOTAL: 52.3%**

## Proyectos de Demo

| Proyecto | Fases | Métricas | Avance |
|----------|-------|----------|--------|
| Torre Corporativa Demo | Excavación + Cimentación + Edificación | 25K m³, 120 pilas, 240 anclas, 45 muros | 52.26% |
| Proyecto Pilas Demo | Cimentación | 576 pilas, 464 anclas | 5.21% |
| Acuarela | Excavación | 50,000 m³ | 100% |

## Credenciales
- **Admin:** admin@dron.mx / admin123
- **Cliente:** cliente@test.com / cliente123

## Stack Tecnológico
- Frontend: React, TailwindCSS, Recharts, Three.js
- Backend: FastAPI, Pydantic, Motor (MongoDB)
- IA: Gemini Vision via emergentintegrations (Emergent LLM Key)

## Integraciones
- **Gemini Vision**: Análisis de PDFs para comparación de avances
- **Resend**: Notificaciones por email (pendiente implementación)
- **OpenStreetMap**: Geocodificación de ubicaciones

## Tareas Completadas (2025-12-17)
- ✅ Bug de selección de proyectos en Dashboard
- ✅ Funcionalidad de Comparación de Avances Dron vs Residente
- ✅ Análisis automático de PDFs con Gemini
- ✅ UI de comparación con métricas, discrepancias y análisis IA

## Tareas Pendientes
- (P1) Prueba E2E completa del sistema de 3 fases con nuevo proyecto
- (P1) Probar funcionalidad de análisis de fotos con AI
- (P2) Refactorización del archivo `server.py` monolítico
- (P2) Implementar notificaciones por email con Resend
- (P3) Clarificar requisito de archivos `.laz`

## Notas Técnicas
- La comparación de avances usa comparación ACUMULADA del proyecto
- El nivel de confianza (ALTA/MEDIA/BAJA) indica qué tan seguro está el modelo de la extracción
- Los PDFs se guardan en `/app/backend/uploads/reportes_residente/`
