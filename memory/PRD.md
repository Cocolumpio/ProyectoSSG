# DrON Topografía - Product Requirements Document

## Declaración del Problema
Dashboard interactivo para visualizar informes de vuelos de drones en proyectos de construcción. Permite gestionar proyectos, visualizar avances, métricas de volumetría y modelos 3D de Pix4D.

## Requisitos del Usuario
- Dashboard con KPIs de proyectos y vuelos
- Visualización de datos de volumetría (excavación, relleno, materiales)
- Seguimiento del avance de proyectos comparado con el cronograma
- Mapa interactivo para ubicaciones de obras
- Visor 3D para nubes de puntos usando Pix4D iframe
- CRUD completo para proyectos con campos para URL de Pix4D y volumetría
- Tema de UI con logo de "DrON Topografía" y colores gris claro (#F8F9FA) / rojo ladrillo (#994B49)

## Datos Iniciales
- Proyecto único: "Hotel Marriott" en Guadalajara, Jalisco con 40% de avance

## Stack Tecnológico
- **Frontend:** React, TailwindCSS, Leaflet, Recharts, Axios
- **Backend:** FastAPI, Pydantic, Motor (MongoDB async driver)
- **Base de datos:** MongoDB
- **Visor 3D:** Pix4D iframe embebido

## Arquitectura
```
/app/
├── backend/
│   ├── server.py        # API FastAPI, modelos Pydantic, endpoints
│   └── uploads/         # Archivos de nubes de puntos (si se usan)
├── frontend/
│   └── src/
│       ├── App.js       # Componente principal con todas las vistas
│       └── components/
│           └── VisorPix4D.js  # Visor 3D de Pix4D
└── memory/
    └── PRD.md           # Este archivo
```

## Implementado (Enero 2025)

### Backend
- [x] Modelos Pydantic: Proyecto, Vuelo, Volumetria, Avance, AvanceSemanal
- [x] Endpoints CRUD para proyectos: GET, POST, PUT, DELETE
- [x] Endpoints para vuelos
- [x] Endpoint de estadísticas/resumen
- [x] Endpoint PUT /api/proyectos/{id} para editar proyectos completos
- [x] Endpoints CRUD para avances semanales: GET, POST, PUT, DELETE /api/proyectos/{id}/avances-semanales
- [x] **Endpoints para galería de imágenes**: POST, GET, DELETE para fotos de vuelo por avance semanal

### Frontend  
- [x] Dashboard con KPIs (Total Proyectos, Vuelos, Avance Promedio, Volumetría)
- [x] Mapa interactivo con Leaflet
- [x] Lista de proyectos con selección
- [x] Gráficos de volumetría con Recharts
- [x] Visor Pix4D embebido en iframe (sincronizado con datos del proyecto)
- [x] Vista de Proyectos con tarjetas
- [x] Modal de Nuevo Proyecto con campos para Pix4D y volumetría
- [x] Modal de Editar Proyecto con datos pre-llenados
- [x] Mensaje de confirmación global al guardar cambios
- [x] **Modal de Avances Semanales (80% de pantalla)** con:
  - Visor 3D por semana
  - **Galería de fotos del vuelo** con subida múltiple
  - Vista previa ampliada de fotos
  - **Descarga individual de fotos** (nombradas automáticamente)
- [x] Vista de Vuelos con tabla y filtros
- [x] Branding personalizado (logo, colores)

### Testing
- [x] Tests de API con pytest (14/14 pasados)
- [x] Tests e2e de UI con Playwright (100% éxito)

## Backlog (P1)
- [ ] CRUD completo para Vuelos (formulario para agregar/editar/eliminar vuelos)
- [ ] Refactorizar App.js en componentes más pequeños

## Backlog (P2)
- [ ] Funcionalidad de carga de archivos LAZ/LAS para archivo
- [ ] Agregar autenticación de usuarios
- [ ] Exportar reportes en PDF

## API Endpoints
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | /api/proyectos | Listar proyectos |
| POST | /api/proyectos | Crear proyecto |
| GET | /api/proyectos/{id} | Obtener proyecto |
| PUT | /api/proyectos/{id} | Actualizar proyecto completo |
| PUT | /api/proyectos/{id}/avance | Actualizar solo avance |
| DELETE | /api/proyectos/{id} | Eliminar proyecto |
| GET | /api/vuelos | Listar vuelos |
| POST | /api/vuelos | Crear vuelo |
| GET | /api/estadisticas/resumen | Obtener estadísticas |

## Esquema de Datos
```javascript
// Proyecto
{
  id: string,
  nombre: string,
  ubicacion: string,
  coordenadas: { lat: float, lng: float },
  fecha_inicio: string,
  fecha_fin_planeada: string,
  avance_actual: float,
  descripcion: string,
  pix4d_url: string,
  volumetria: { excavacion: float, relleno: float, materiales: float }
}

// Vuelo
{
  id: string,
  proyecto_id: string,
  fecha_vuelo: string,
  duracion_minutos: int,
  area_cubierta: float,
  num_imagenes: int,
  volumetria: { excavacion: float, relleno: float, materiales: float },
  pix4d_url: string,
  estado: string
}
```
