# DrON Topografía - Product Requirements Document

## Declaración del Problema
Dashboard interactivo para visualizar informes de vuelos de drones en proyectos de construcción. Permite gestionar proyectos, visualizar avances, métricas de volumetría/pilas y modelos 3D de Pix4D.

## Requisitos del Usuario
- Dashboard con KPIs de proyectos y vuelos
- **Métricas dinámicas según tipo de actividad**: pilas, muros, anclas, excavación
- Visualización de datos de volumetría (excavación, relleno, materiales) en m³
- Seguimiento del avance de proyectos comparado con el cronograma
- Mapa interactivo para ubicaciones de obras
- Visor 3D para nubes de puntos usando Pix4D iframe y archivos PLY locales
- CRUD completo para proyectos con campos para URL de Pix4D y volumetría
- CRUD completo para vuelos
- Avances semanales con galería de fotos y modelos 3D
- Gráfico de progresión dinámico según tipo de actividad
- Descarga de fotos en formato ZIP
- Generación de reportes ejecutivos PDF con costos de flotilla
- Programación de vuelos por el cliente con notificación por email
- Sistema de autenticación con roles (Admin/Cliente)
- Importación de cronograma desde Excel con detección automática de tipos de actividades
- Análisis de fotos con IA (Gemini Vision) para detectar pilas y anclas
- Gráfico Gantt visual de progreso del proyecto

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
│   ├── server.py
│   ├── models/
│   │   └── schemas.py
│   ├── services/
│   │   ├── auth.py
│   │   ├── database.py
│   │   ├── thumbnails.py
│   │   └── cronograma_ai.py
│   └── uploads/
├── frontend/
│   └── src/
│       └── components/
│           ├── Dashboard/
│           │   ├── DashboardView.jsx
│           │   └── GanttChart.jsx
│           ├── Projects/
│           │   ├── ProyectosView.jsx
│           │   ├── AvancesSemanalesModal.jsx
│           │   ├── ImportarCronograma.jsx
│           │   └── AnalisisFotoIA.jsx
│           └── ...
└── memory/
    └── PRD.md
```

## Implementado (Febrero 2025)

### Sesión Actual - 17 Feb 2025

#### Métricas Dinámicas por Tipo de Actividad (COMPLETADO)
- [x] GanttChart.jsx muestra progresión según `actividades_tipo` del proyecto
- [x] Prioridad de visualización: pilas > muros > anclas > excavación
- [x] Dashboard oculta "Volumen Excavado vs Planeado" cuando no hay excavación planeada
- [x] AvancesSemanalesModal.jsx muestra gráfico dinámico con título y unidades correctas
- [x] Badges de color según tipo: Pilas (azul), Muros (púrpura), Anclas (teal), Excavación (naranja)
- [x] "Última actualización" muestra dato relevante (Pilas: X o Volumen: X m³)

#### Bug Fixes
- [x] Eliminación de proyectos funcionando correctamente (verificado)

### Funcionalidades Anteriores

#### Tipos de Actividades (COMPLETADO)
- [x] Parser de Excel detecta tipos: pilas, muros, anclas, excavación
- [x] ImportarCronograma.jsx muestra tipos detectados con badges
- [x] Dashboard muestra métricas condicionales

#### Análisis de Fotos con IA (COMPLETADO)
- [x] AnalisisFotoIA.jsx para upload y análisis
- [x] Botón "Analizar Fotos con IA" en Avances Semanales
- [x] Integración con Gemini Vision

#### Gráfico Gantt Visual (COMPLETADO)
- [x] Métricas: Semanas, Pilas/Muros/Anclas/Volumen, Avance Total, Estado
- [x] Gráfico de área "Planeado vs Ejecutado"
- [x] Timeline visual del proyecto

## Proyectos de Prueba
| Proyecto | Tipo | Métricas |
|----------|------|----------|
| Acuarela | Excavación | 50,000 m³ |
| Proyecto Pilas Demo | Pilas + Anclas | 576 pilas, 464 anclas |
| Torre Mezquitan | Sin tipo | - |
| Hotel Marriott Centro | Excavación | 70,000 m³ |

## API Endpoints Principales
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | /api/auth/login | Login de usuario |
| GET | /api/proyectos | Listar proyectos |
| DELETE | /api/proyectos/{id} | Eliminar proyecto |
| POST | /api/proyectos/crear-desde-cronograma | Crear proyecto desde Excel |
| GET | /api/proyectos/{id}/avances-semanales | Obtener avances |
| POST | /api/avances/{id}/analizar-foto | Analizar foto con IA |

## Esquema de Datos
```javascript
// Proyecto
{
  id: string,
  nombre: string,
  ubicacion: string,
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
  muros_completados: int,
  anclas_instaladas: int
}
```

## Backlog
- [ ] P2: Refactorizar server.py en módulos de rutas
- [ ] P3: Soporte para archivos LAZ/LAS
