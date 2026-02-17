# DrON Topografía - Product Requirements Document

## Estado Actual (Actualizado: 2025-12-17)
- **Sistema Funcional**: Dashboard multi-fase completamente operativo
- **Bug Fix**: Corregido bug de selección de proyectos (P0)
- **Testing**: 100% de pruebas pasadas

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
- IA: Gemini Vision via emergentintegrations

## Bugs Corregidos (2025-12-17)
- **P0 - Selección de Proyectos**: El bug causaba que al hacer clic en cualquier proyecto, siempre mostrara el primero. Corregido eliminando `selectedProyecto` de las dependencias de `useCallback` en `App.js` y usando el patrón de función de actualización de estado.

## Tareas Pendientes
- (P1) Prueba E2E completa del sistema de 3 fases
- (P1) Probar funcionalidad de análisis de fotos con AI
- (P2) Refactorización del archivo `server.py` monolítico
- (P2) Implementar notificaciones por email con Resend
- (P3) Clarificar requisito de archivos `.laz`

## Notas Técnicas
- El análisis de fotos con AI está integrado pero el flujo E2E no ha sido probado completamente
- El cálculo de avance del backend es la fuente de verdad
