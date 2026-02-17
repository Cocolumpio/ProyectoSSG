# DrON Topografía - Product Requirements Document

## Declaración del Problema
Dashboard interactivo para visualizar informes de vuelos de drones en proyectos de construcción. Permite gestionar proyectos con **múltiples fases** (Excavación, Cimentación, Edificación), visualizar avances por fase y un avance TOTAL del proyecto.

## Requisitos Implementados

### Fases de Construcción (NUEVO)
- **Excavación**: Volumen total en m³
- **Cimentación**: Pilas planeadas + Anclas planeadas  
- **Edificación**: Muros planeados
- Se pueden seleccionar una o más fases por proyecto
- El avance TOTAL se calcula como promedio de las fases activas

### Formulario de Proyecto (NUEVO)
- Checkboxes para seleccionar fases (Excavación, Cimentación, Edificación)
- Campos condicionales que se muestran al seleccionar cada fase
- Mensaje informativo sobre proyección automática sin cronograma

### Dashboard con Avance por Fase (NUEVO)
- **Avance Total del Proyecto**: Barra de progreso con porcentaje
- **Avance por Fase**: Barras de progreso para cada fase activa
  - Excavación (naranja)
  - Cimentación (azul)
  - Edificación (púrpura)
- **Proyección de semanas restantes**: Si no hay cronograma, calcula basado en ritmo
- **Detalles numéricos**: Tarjetas con ejecutado/planeado por cada métrica

### Avances Semanales - Campos Editables
- **Pilas Completadas** (azul)
- **Anclas Instaladas** (teal)
- **Muros Completados** (púrpura) - NUEVO
- **Volumen Excavado** (rojo/naranja)
- Los campos solo aparecen si el proyecto tiene esa fase configurada

### Cálculo de Avance Automático
- Se recalcula al guardar cualquier métrica
- Prioridad para tipo principal: pilas > muros > anclas > excavación
- Avance TOTAL: promedio de todas las fases activas

## Stack Tecnológico
- **Frontend:** React, TailwindCSS, Leaflet, Recharts, Three.js
- **Backend:** FastAPI, Pydantic, Motor (MongoDB), python-jose (JWT)
- **Base de datos:** MongoDB
- **IA:** Gemini Vision via emergentintegrations

## Proyectos de Prueba
| Proyecto | Fases | Métricas | Avance |
|----------|-------|----------|--------|
| Proyecto Pilas Demo | Cimentación | 576 pilas, 464 anclas | 5.21% |
| Programa Tabla | Cimentación | 576 pilas, 464 anclas | 0% |
| Acuarela | Excavación | 50,000 m³ | 0% |
| Hotel Marriott Centro | Excavación | 70,000 m³ | 0% |

## Credenciales de Prueba
- **Admin:** admin@dron.mx / admin123
- **Cliente:** cliente@test.com / cliente123

## API Endpoints Principales
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | /api/proyectos | Crear proyecto con fases |
| PUT | /api/proyectos/{id}/avances-semanales/{avance_id} | Actualizar pilas/anclas/muros/volumen |
| POST | /api/proyectos/crear-desde-cronograma | Crear desde Excel |
| POST | /api/avances/{id}/analizar-foto | Analizar con IA |

## Esquema de Datos
```javascript
// Proyecto
{
  id: string,
  nombre: string,
  actividades_tipo: ["excavacion", "pilas", "anclas", "muros"],
  volumen_total_planeado: float,  // Excavación
  pilas_planeadas: int,           // Cimentación
  anclas_planeadas: int,          // Cimentación
  muros_planeados: int,           // Edificación
  semanas_planeadas: int,
  avance_actual: float            // Calculado automáticamente
}

// Avance Semanal
{
  id: string,
  proyecto_id: string,
  semana: int,
  volumen_excavacion: float,
  pilas_completadas: int,
  anclas_instaladas: int,
  muros_completados: int
}
```

## Backlog
- [ ] P2: Refactorizar server.py en módulos de rutas
- [ ] P3: Soporte para archivos LAZ/LAS
- [ ] P3: Gráficos Gantt con múltiples fases en paralelo
