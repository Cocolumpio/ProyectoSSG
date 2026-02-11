# DrON Topografía - Product Requirements Document

## Declaración del Problema
Dashboard interactivo para visualizar informes de vuelos de drones en proyectos de construcción. Permite gestionar proyectos, visualizar avances, métricas de volumetría y modelos 3D de Pix4D.

## Requisitos del Usuario
- Dashboard con KPIs de proyectos y vuelos
- Visualización de datos de volumetría (excavación, relleno, materiales) en m³
- Seguimiento del avance de proyectos comparado con el cronograma
- Mapa interactivo para ubicaciones de obras
- Visor 3D para nubes de puntos usando Pix4D iframe
- CRUD completo para proyectos con campos para URL de Pix4D y volumetría
- CRUD completo para vuelos
- Avances semanales con galería de fotos y modelos 3D
- Gráfico de volumen excavado por semana
- Descarga de fotos en formato ZIP
- Generación de reportes ejecutivos PDF con costos de flotilla
- **Programación de vuelos por el cliente con notificación por email + Google Calendar**
- **Sistema de autenticación con roles (Admin/Cliente)**
- **Vista Admin: acceso completo + gestión de solicitudes**
- **Vista Cliente: solo lectura + crear/ver solicitudes propias**
- Tema de UI con logo de "DrON Topografía" y colores gris claro (#F8F9FA) / rojo ladrillo (#994B49)

## Usuarios del Sistema
- **Admin (ianalejandrogn@gmail.com):** Acceso completo a todas las funciones
  - Credenciales: admin@dron.mx / admin123
- **Clientes:** Vista de solo lectura + solicitar vuelos
  - Ejemplo: cliente@test.com / cliente123

## Stack Tecnológico
- **Frontend:** React, TailwindCSS, Leaflet, Recharts, Axios
- **Backend:** FastAPI, Pydantic, Motor (MongoDB async driver), Resend (email), python-jose (JWT)
- **Base de datos:** MongoDB
- **Autenticación:** JWT con bcrypt para hashing de contraseñas
- **Visor 3D:** Pix4D iframe embebido
- **Email:** Resend API

## Arquitectura
```
/app/
├── backend/
│   ├── server.py        # API FastAPI con auth + endpoints
│   └── uploads/         # Archivos e imágenes
├── frontend/
│   └── src/
│       ├── App.js       # Estado global, routing, header, vistas read-only
│       ├── context/
│       │   └── AuthContext.jsx    # ✅ NUEVO (Feb 2025)
│       └── components/
│           ├── Auth/
│           │   └── LoginPage.jsx         # ✅ NUEVO (Feb 2025)
│           ├── Admin/
│           │   └── SolicitudesAdminView.jsx  # ✅ NUEVO (Feb 2025)
│           ├── Client/
│           │   └── MisSolicitudesView.jsx    # ✅ NUEVO (Feb 2025)
│           ├── Dashboard/
│           │   └── DashboardView.jsx
│           ├── Projects/
│           │   ├── ProyectosView.jsx
│           │   ├── ProjectFormContent.jsx
│           │   └── AvancesSemanalesModal.jsx
│           ├── Flights/
│           │   ├── VuelosView.jsx
│           │   └── SolicitarVueloForm.jsx
│           └── common/
│               ├── KPICard.jsx
│               └── MapRecenter.jsx
└── memory/
    └── PRD.md
```
│           │   ├── VuelosView.jsx         # ✅ NUEVO (Feb 2025)
│           │   └── SolicitarVueloForm.jsx
│           └── common/
│               ├── KPICard.jsx
│               └── MapRecenter.jsx
└── memory/
    └── PRD.md           # Este archivo
```

## Implementado (Enero 2025)

### Nuevas Funcionalidades (29 Enero 2025)
- [x] **CRUD completo para Vuelos** - Formulario con crear, editar, eliminar
  - Campos: proyecto, fecha, duración, área, imágenes, volumetría, URL Pix4D, estado, notas
  - Endpoint PUT /api/vuelos/{id} agregado
- [x] **Gráfico de Volumen Excavado por Semana** - BarChart que muestra toneladas extraídas por semana
- [x] **Descarga de Fotos en ZIP** - Botón "Descargar ZIP" en galería de fotos
  - Endpoint GET /api/proyectos/{id}/avances-semanales/{avance_id}/imagenes/zip
- [x] **Reporte Ejecutivo PDF** - Generación de reportes para gestión de presupuesto de flotillas
  - Endpoint GET /api/proyectos/{id}/reporte-ejecutivo
  - Contenido:
    - Información del proyecto (nombre, ubicación, coordenadas, fechas)
    - Avance de obra en porcentaje
    - Volumetría por semana (toneladas excavadas)
    - Viajes de camión estimados por semana
    - Desglose de costos por semana y total
    - Resumen para logística de transporte
- [x] **Programación de Vuelos con Notificación Email** (Resend)
  - Formulario para que el cliente solicite vuelos
  - Envío automático de email al administrador
  - Link de Google Calendar incluido en el email
  - Campos: nombre proyecto, fechas, hora preferida, notas
- [x] **Configuración de Flotilla por Proyecto** - Campos configurables para cálculo de costos
  - `capacidad_camion`: Toneladas que carga cada camión (default 25 ton)
  - `costo_viaje_camion`: Precio por viaje en MXN (default $2,500)
  - Cálculo automático de viajes necesarios y costo total en el reporte PDF

### Correcciones de Despliegue (29 Enero 2025)
- [x] **CRÍTICO:** Eliminados paquetes obsoletos `@react-three/drei`, `@react-three/fiber`, `three` que causaban error de build
  - El paquete `camera-controls@3.1.2` requería Node.js >=22.0.0, incompatible con el servidor de producción (20.18.1)
- [x] Eliminado proyecto de prueba "Acuarela" de la base de datos
- [x] Build de producción verificado exitosamente

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
- [x] **CRUD completo para Vuelos** - Modal con formulario de crear/editar
- [x] **Gráfico de Evolución del Progreso** - LineChart en modal de avances semanales
- [x] **Botón Descargar ZIP** - Descarga todas las fotos de una semana en ZIP
- [x] Branding personalizado (logo, colores)

### Testing
- [x] Tests de API con pytest (14/14 pasados)
- [x] Tests e2e de UI con Playwright (100% éxito)

## Backlog (P1)
- [x] **COMPLETADO:** Refactorizar App.js en componentes más pequeños
  - Reducido de ~640 líneas a ~209 líneas (67% reducción)
  - Componentes extraídos: DashboardView, ProjectFormContent, AvancesSemanalesModal, KPICard, MapRecenter
  - **Feb 2025:** Extraídos `ProyectosView` y `VuelosView` - Refactorización 100% completa
- [x] **COMPLETADO (Feb 2025):** Sistema de autenticación con roles Admin/Cliente
  - JWT con bcrypt para hashing de contraseñas
  - Vista Admin: acceso completo + panel de gestión de solicitudes
  - Vista Cliente: solo lectura + historial de solicitudes propias
  - Notificación por email al cliente cuando admin confirma/rechaza
- [x] **COMPLETADO (Feb 2025):** Gestión de usuarios desde panel admin
  - Crear nuevos usuarios (admin/cliente)
  - Activar/desactivar usuarios
  - Búsqueda de usuarios
  - Estadísticas de usuarios
- [x] **COMPLETADO (Feb 2025):** Edición inline del volumen excavado en avances semanales
  - Botón de editar junto al valor del volumen (solo visible para admins)
  - Campo de entrada con botones de guardar y cancelar
  - Recálculo automático del porcentaje de avance del proyecto
  - Actualización instantánea del gráfico de progresión
- [x] **COMPLETADO (Feb 2025):** Proyección automática de excavación
  - Cálculo del ritmo semanal promedio basado en datos históricos
  - Línea de proyección naranja que muestra la tendencia hacia la meta
  - Indicador de "Meta en: ~X semanas" con estimación de tiempo
  - Se muestra "✅ Meta alcanzada" cuando se completa el volumen planeado
- [x] **COMPLETADO (Feb 2025):** Visor de nubes de puntos 3D local
  - Subida de archivos PLY, XYZ, PTS, PCD desde el navegador
  - Visor 3D con Three.js (rotación, zoom, pan)
  - Tabs para cambiar entre visor local y Pix4D
  - Pix4D como respaldo si el visor local falla
  - Indicador de número de puntos y controles de navegación

## Backlog (P2)
- [x] **COMPLETADO:** Vista Admin para Solicitudes de Vuelo
- [x] **COMPLETADO:** Notificación al cliente cuando se confirma un vuelo
- [x] **COMPLETADO:** Funcionalidad DELETE para Vuelos (ya existía en backend y frontend)
- [x] **COMPLETADO:** Gestión de usuarios desde panel admin
- [x] **COMPLETADO:** Estructura de carpetas preparada para refactorización gradual del backend
  - `/backend/models/` - Modelos Pydantic
  - `/backend/services/` - Database, Auth services
  - `/backend/routes/` - Rutas de API (estructura lista)
- [ ] Completar migración gradual de server.py a módulos
- [ ] Funcionalidad de carga de archivos LAZ/LAS para archivo

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
| **PUT** | **/api/vuelos/{id}** | **Actualizar vuelo** |
| DELETE | /api/vuelos/{id} | Eliminar vuelo |
| GET | /api/proyectos/{id}/avances-semanales | Listar avances semanales |
| POST | /api/proyectos/{id}/avances-semanales | Crear avance semanal |
| **GET** | **/api/proyectos/{id}/avances-semanales/{avance_id}/imagenes/zip** | **Descargar fotos en ZIP** |
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
