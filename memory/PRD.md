# DrON Topografía - Product Requirements Document

## Declaración del Problema
Dashboard interactivo para visualizar informes de vuelos de drones en proyectos de construcción. Permite gestionar proyectos, visualizar avances, métricas de volumetría/pilas y modelos 3D de Pix4D.

## Requisitos del Usuario
- Dashboard con KPIs de proyectos y vuelos
- **Métricas dinámicas según tipo de actividad**: pilas, muros, anclas, excavación
- **Edición inline de pilas/anclas/volumen** en Avances Semanales
- Visualización de datos de volumetría (excavación, relleno, materiales) en m³
- Seguimiento del avance de proyectos comparado con el cronograma
- Mapa interactivo para ubicaciones de obras
- Visor 3D para nubes de puntos usando Pix4D iframe y archivos PLY locales
- CRUD completo para proyectos y vuelos
- Avances semanales con galería de fotos y modelos 3D
- Gráfico de progresión dinámico según tipo de actividad
- Sistema de autenticación con roles (Admin/Cliente)
- Importación de cronograma desde Excel con detección automática de tipos
- Análisis de fotos con IA (Gemini Vision)
- Gráfico Gantt visual de progreso del proyecto

## Stack Tecnológico
- **Frontend:** React, TailwindCSS, Leaflet, Recharts, Axios, Three.js
- **Backend:** FastAPI, Pydantic, Motor (MongoDB), python-jose (JWT)
- **Base de datos:** MongoDB
- **IA:** Gemini Vision via emergentintegrations

## Implementado (Febrero 2025)

### Sesión Actual - 17 Feb 2025

#### Edición de Pilas/Anclas en Avances Semanales (COMPLETADO)
- [x] Campos editables para pilas_completadas y anclas_instaladas
- [x] Campos solo se muestran cuando el proyecto tiene esos tipos de actividades
- [x] Diseño con colores por tipo: Pilas (azul), Anclas (teal), Excavación (rojo)
- [x] Backend actualizado con campos en AvanceSemanalUpdate
- [x] Función recalcular_avance_proyecto actualizada para calcular por tipo
- [x] Verificado: 30 pilas completadas = 5.21% avance (30/576)

#### Métricas Dinámicas por Tipo de Actividad (COMPLETADO)
- [x] GanttChart muestra progresión según actividades_tipo del proyecto
- [x] Prioridad: pilas > muros > anclas > excavación
- [x] Dashboard oculta "Volumen Excavado" cuando no hay excavación planeada
- [x] AvancesSemanalesModal con gráfico dinámico

### Funcionalidades Base

#### Backend
- [x] Autenticación JWT con roles admin/client
- [x] CRUD completo para proyectos, vuelos, avances semanales
- [x] Generación de thumbnails para modelos PLY
- [x] Importación de cronograma desde Excel
- [x] Análisis de fotos con Gemini Vision

#### Frontend
- [x] Dashboard con KPIs y mapa interactivo
- [x] Visor 3D con Three.js para archivos PLY
- [x] Sistema de avances semanales con galería de fotos
- [x] Descarga de fotos en ZIP
- [x] Formulario de solicitud de vuelos
- [x] Sistema de notificaciones por email

## Proyectos de Prueba
| Proyecto | Tipo | Meta | Avance |
|----------|------|------|--------|
| Proyecto Pilas Demo | Pilas + Anclas | 576 pilas, 464 anclas | 5.21% (30 pilas) |
| Acuarela | Excavación | 50,000 m³ | 0% |
| Hotel Marriott Centro | Excavación | 70,000 m³ | 0% |
| Torre Mezquitan | Sin tipo | - | 0% |

## Credenciales de Prueba
- **Admin:** admin@dron.mx / admin123
- **Cliente:** cliente@test.com / cliente123

## API Endpoints Principales
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| PUT | /api/proyectos/{id}/avances-semanales/{avance_id} | Actualizar pilas/anclas/volumen |
| POST | /api/proyectos/crear-desde-cronograma | Crear proyecto desde Excel |
| POST | /api/avances/{id}/analizar-foto | Analizar foto con IA |

## Backlog
- [ ] P2: Refactorizar server.py en módulos de rutas
- [ ] P3: Soporte para archivos LAZ/LAS
