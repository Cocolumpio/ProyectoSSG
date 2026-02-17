# DrON Topografía - Product Requirements Document

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
  - Cimentación: 61.7% ((69.2%+54.2%)/2 de pilas+anclas)
  - Edificación: 11.1% (5/45 muros)
  - **TOTAL: 52.26%** ((84+61.7+11.1)/3)

## Proyectos de Demo

| Proyecto | Fases | Métricas | Avance |
|----------|-------|----------|--------|
| Torre Corporativa Demo | Excavación + Cimentación + Edificación | 25K m³, 120 pilas, 240 anclas, 45 muros | 52.26% |
| Proyecto Pilas Demo | Cimentación | 576 pilas, 464 anclas | 5.21% |
| Acuarela | Excavación | 50,000 m³ | 42% |

## Credenciales
- **Admin:** admin@dron.mx / admin123
- **Cliente:** cliente@test.com / cliente123

## Stack Tecnológico
- Frontend: React, TailwindCSS, Recharts, Three.js
- Backend: FastAPI, Pydantic, Motor (MongoDB)
- IA: Gemini Vision via emergentintegrations
