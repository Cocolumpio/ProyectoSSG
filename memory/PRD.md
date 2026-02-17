# DrON Topografía - Product Requirements Document

## Declaración del Problema
Dashboard interactivo para visualizar informes de vuelos de drones en proyectos de construcción. Permite gestionar proyectos, visualizar avances, métricas de volumetría y modelos 3D de Pix4D.

## Requisitos del Usuario
- Dashboard con KPIs de proyectos y vuelos
- Visualización de datos de volumetría (excavación, relleno, materiales) en m³
- Seguimiento del avance de proyectos comparado con el cronograma
- Mapa interactivo para ubicaciones de obras
- Visor 3D para nubes de puntos usando Pix4D iframe y archivos PLY locales
- CRUD completo para proyectos con campos para URL de Pix4D y volumetría
- CRUD completo para vuelos
- Avances semanales con galería de fotos y modelos 3D
- Gráfico de volumen excavado por semana
- Descarga de fotos en formato ZIP
- Generación de reportes ejecutivos PDF con costos de flotilla
- Programación de vuelos por el cliente con notificación por email
- Sistema de autenticación con roles (Admin/Cliente)
- **Importación de cronograma desde Excel con detección automática de tipos de actividades**
- **Análisis de fotos con IA (Gemini Vision) para detectar pilas y anclas**
- **Gráfico Gantt visual de progreso del proyecto**

## Usuarios del Sistema
- **Admin:** Acceso completo a todas las funciones
  - Credenciales: admin@dron.mx / admin123
- **Clientes:** Vista de solo lectura + solicitar vuelos
  - Ejemplo: cliente@test.com / cliente123

## Stack Tecnológico
- **Frontend:** React, TailwindCSS, Leaflet, Recharts, Axios, Three.js
- **Backend:** FastAPI, Pydantic, Motor (MongoDB async driver), Resend (email), python-jose (JWT)
- **Base de datos:** MongoDB
- **Autenticación:** JWT con bcrypt para hashing de contraseñas
- **Visor 3D:** Pix4D iframe + Three.js para PLY locales
- **Email:** Resend API
- **IA:** Gemini Vision via emergentintegrations

## Arquitectura
```
/app/
├── backend/
│   ├── server.py              # API FastAPI con auth + endpoints
│   ├── models/
│   │   └── schemas.py         # Modelos Pydantic
│   ├── services/
│   │   ├── auth.py            # Autenticación JWT
│   │   ├── database.py        # Conexión MongoDB
│   │   ├── thumbnails.py      # Generación thumbnails PLY
│   │   └── cronograma_ai.py   # Parser Excel + IA Gemini
│   └── uploads/               # Archivos y modelos 3D
├── frontend/
│   └── src/
│       ├── App.js
│       ├── context/
│       │   └── AuthContext.jsx
│       └── components/
│           ├── Auth/LoginPage.jsx
│           ├── Admin/SolicitudesAdminView.jsx
│           ├── Client/MisSolicitudesView.jsx
│           ├── Dashboard/
│           │   ├── DashboardView.jsx
│           │   └── GanttChart.jsx          # NUEVO (Feb 2025)
│           ├── Projects/
│           │   ├── ProyectosView.jsx
│           │   ├── ProjectFormContent.jsx
│           │   ├── AvancesSemanalesModal.jsx
│           │   ├── PointCloudViewer.jsx
│           │   ├── ImportarCronograma.jsx  # NUEVO (Feb 2025)
│           │   └── AnalisisFotoIA.jsx      # NUEVO (Feb 2025)
│           └── Flights/
│               ├── VuelosView.jsx
│               └── SolicitarVueloForm.jsx
└── memory/
    └── PRD.md
```

## Implementado (Febrero 2025)

### Sesión Actual - 17 Feb 2025

#### P0 - Tipos de Actividades (COMPLETADO)
- [x] Parser de Excel detecta tipos de actividades: pilas, muros, anclas, excavación
- [x] Endpoint `/api/proyectos/crear-desde-cronograma` guarda `actividades_tipo` y métricas
- [x] ImportarCronograma.jsx muestra tipos detectados con badges de colores
- [x] DashboardView.jsx muestra métricas condicionales (Pilas X/Y, Muros X/Y, Anclas X/Y)
- [x] Tests: 13/13 backend tests pasados

#### P1 - Análisis de Fotos con IA (COMPLETADO)
- [x] Componente AnalisisFotoIA.jsx para upload de fotos y análisis
- [x] Botón "Analizar Fotos con IA" en AvancesSemanalesModal.jsx
- [x] Endpoint `/api/avances/{id}/analizar-foto` con Gemini Vision
- [x] Muestra: pilas detectadas, anclas, estado proyecto, observaciones
- [x] Integración con emergentintegrations y EMERGENT_LLM_KEY

#### P1 - Gráfico Gantt Visual (COMPLETADO)
- [x] Componente GanttChart.jsx con métricas de estado
- [x] Muestra Progreso Semanal (X/Y), Avance Total (%), Estado (Adelantado/En Tiempo/Retrasado)
- [x] Gráfico de barras "Planeado vs Ejecutado" por semana
- [x] Colores: verde = adelantado, rojo = retrasado
- [x] Timeline visual del proyecto con barras de progreso
- [x] Integrado en DashboardView.jsx

### Funcionalidades Anteriores

#### Backend
- [x] Modelos Pydantic para proyectos, vuelos, avances, frentes
- [x] Autenticación JWT con roles admin/client
- [x] CRUD completo para proyectos, vuelos, avances semanales
- [x] Generación de thumbnails para modelos PLY
- [x] Endpoints de estadísticas y reportes PDF
- [x] Gestión de usuarios desde panel admin
- [x] Importación de cronograma desde Excel

#### Frontend
- [x] Dashboard con KPIs y mapa interactivo
- [x] Visor 3D con Three.js para archivos PLY
- [x] Sistema de avances semanales con galería de fotos
- [x] Descarga de fotos en ZIP
- [x] Formulario de solicitud de vuelos
- [x] Sistema de notificaciones por email
- [x] Asignación de proyectos a clientes

## Backlog

### P2 - Pendiente
- [ ] Refactorizar server.py en módulos de rutas separados
- [ ] Soporte para archivos LAZ/LAS

### P3 - Futuro
- [ ] Dashboard de métricas avanzadas
- [ ] Exportación de reportes a Excel
- [ ] Integración con más proveedores de nube de puntos

## API Endpoints Principales
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | /api/auth/login | Login de usuario |
| GET | /api/proyectos | Listar proyectos |
| POST | /api/proyectos/crear-desde-cronograma | Crear proyecto desde Excel |
| POST | /api/proyectos/importar-cronograma | Parsear archivo Excel |
| GET | /api/proyectos/{id}/avances-semanales | Obtener avances |
| POST | /api/avances/{id}/analizar-foto | Analizar foto con IA |
| GET | /api/plantilla-cronograma | Descargar plantilla Excel |

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
  actividades_tipo: ["pilas", "muros", "anclas", "excavacion"],
  pilas_planeadas: int,
  muros_planeados: int,
  anclas_planeadas: int,
  volumen_total_planeado: float,
  semanas_planeadas: int
}

// Avance Semanal
{
  id: string,
  proyecto_id: string,
  semana: int,
  fecha: string,
  volumen_excavacion: float,
  pilas_completadas: int,
  anclas_instaladas: int,
  modelo_3d_url: string,
  thumbnail_url: string,
  imagenes: [string]
}
```

## Testing
- Backend: 13 tests con pytest (100% éxito)
- Frontend: 10 features verificadas (100% éxito)
- Playwright: Flujos e2e automatizados
