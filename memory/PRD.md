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
- ✅ Alertas automáticas por email (Resend) cuando discrepancias >15%
- ✅ Prueba E2E del sistema de 3 fases (Proyecto E2E 3 Fases Test creado)
- ✅ Reporte semanal automático cada viernes a las 18:00
- ✅ Botón para enviar reporte semanal manualmente
- ✅ Desglose de costos de flotilla por proyecto en reportes
- ✅ Verificación de la interfaz de Análisis de Fotos con IA
- ✅ Dashboard de Métricas Históricas con gráficas interactivas
- ✅ Reportes actualizados con pilas, anclas y muros por proyecto
- ✅ Exportación de métricas históricas a Excel y PDF

## Tareas Pendientes
- (P2) Refactorización del archivo `server.py` monolítico (~3200 líneas)
- (P3) Clarificar requisito de archivos `.laz`

## Funcionalidades del Sistema

### Exportación de Métricas (NUEVO)
- **Ubicación**: Pestaña "Métricas" → Botones Excel/PDF en header
- **Excel** (verde): Genera archivo .xlsx con 3 hojas
  - Resumen General: KPIs y métricas por proyecto
  - Avances Semanales: Detalle por semana de cada proyecto
  - Comparaciones Residente: Historial de comparaciones IA
- **PDF** (rojo): Genera reporte ejecutivo con
  - KPIs Resumen: Proyectos, Volumen, Pilas, Anclas, Muros, Costo
  - Tabla detalle por proyecto
  - Desglose de costos de flotilla

### Dashboard de Métricas Históricas
- **Ubicación**: Pestaña "Métricas" en la navegación principal
- **KPIs Totales**: Excavación, Pilas, Anclas, Muros
- **Gráfica de Evolución**: AreaChart por semana
- **Selector de Vista**: Avance Total, Excavación, Cimentación, Edificación
- **Comparativa**: BarChart horizontal
- **Tabla de Detalle**: Métricas completas por proyecto

### Reporte Semanal Automático (ACTUALIZADO)
- **Programación**: Cada viernes a las 18:00
- **KPIs del Reporte**:
  - Proyectos Activos
  - m³ Excavados Total
  - Gasto Total Flotillas
  - Pilas Totales (NUEVO)
  - Anclas Totales (NUEVO)
  - Muros Totales (NUEVO)
- **Por Proyecto**: Muestra pilas, anclas, muros ejecutados vs planeados + incremento semanal
- **Envío manual**: Botón "Enviar Reporte Semanal" en dashboard

## Notas Técnicas
- La comparación de avances usa comparación ACUMULADA del proyecto
- El nivel de confianza (ALTA/MEDIA/BAJA) indica qué tan seguro está el modelo de la extracción
- Los PDFs se guardan en `/app/backend/uploads/reportes_residente/`
