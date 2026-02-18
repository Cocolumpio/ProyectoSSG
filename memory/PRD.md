# DrON Topografía - Product Requirements Document

## Estado Actual (Actualizado: 2025-12-18)
- **Sistema Funcional**: Dashboard multi-fase completamente operativo
- **Nuevas Funcionalidades**: Catálogo de Maquinaria con IA + Formulario de avance simplificado
- **Testing**: 100% de pruebas pasadas (14 tests nuevos)

## Funcionalidades Implementadas Hoy (2025-12-18)

### 1. Catálogo de Maquinaria con Análisis IA
Nueva funcionalidad en el formulario de "Nuevo Proyecto" que permite:
- **Subir Excel** con el catálogo de maquinaria disponible
- **Parámetros del proyecto**: Área del terreno, espacio de maniobra, distancia entre pilas
- **Análisis con Gemini AI** que:
  - Extrae máquinas del Excel (Excavadoras, Perforadoras, Grúas, etc.)
  - Busca especificaciones técnicas (dimensiones, rendimiento)
  - **Propone plan de ejecución óptimo por fase:**
    - Fase 1: Excavación - qué excavadoras usar
    - Fase 2: Perforación de Pilas - qué perforadoras usar
    - Fase 3: Anclas - qué perforadoras de anclas usar
  - Estima tiempos y rendimientos
  - Considera distribución espacial y seguridad

**Endpoints:**
- `POST /api/proyectos/analizar-catalogo-maquinaria` - Analiza Excel con IA
- `POST /api/proyectos/{id}/guardar-catalogo-maquinaria` - Guarda catálogo
- `GET /api/proyectos/{id}/catalogo-maquinaria` - Obtiene catálogo guardado

**Formato del Excel esperado:**
| TIPO DE MAQUINA | MARCA | MODELO | ESTATUS |
|-----------------|-------|--------|---------|
| EXCAVADORA | CAT | 320 | OPTIMA |
| PERFORADORA | XCMG | XR168E | SATISFACTORIO |
| GRUA | GROVE | RT75 | DISPONIBLE |

### 2. Formulario de Avance Semanal Simplificado
- **Removido**: Campo "URL del Modelo 3D (Pix4D)"
- **Agregado**: Mensaje informativo sobre subir archivo .ply después de crear el avance
- El modelo 3D ahora se sube localmente desde la vista de detalle del avance

## Sistema de Fases de Construcción

### Fases Implementadas
- **Excavación**: Volumen total en m³
- **Cimentación**: Pilas + Anclas  
- **Edificación**: Muros

### Cálculo de Avance
- Avance TOTAL = promedio de todas las fases activas
- Ejemplo: Torre Corporativa Demo = 52.26%

## Funcionalidades Existentes

### Dashboard Principal
- Mapa interactivo con marcadores de proyectos
- KPIs: 6 Proyectos, 31.3% Avance, 72,149 m³ Excavación

### Gestión de Proyectos
- CRUD completo de proyectos
- Configuración de fases activas
- Metas por fase (m³, pilas, anclas, muros)
- **NUEVO**: Catálogo de maquinaria con IA

### Avances Semanales
- Registro semanal por proyecto
- **Modelos 3D (.ply)** - Se suben después de crear el avance
- Fotos del vuelo
- Métricas de excavación, pilas, anclas, muros

### Comparación de Avances con IA
- Subir PDF del residente
- Análisis automático con Gemini
- Alertas automáticas por discrepancias >15%

### Métricas Históricas
- Gráficas de evolución por semana
- Exportación a Excel y PDF

### Reporte Semanal Automático
- Envío cada viernes 18:00
- KPIs de todos los proyectos

## Credenciales de Prueba
- **Admin:** admin@dron.mx / admin123
- **Cliente:** cliente@test.com / cliente123

## Stack Tecnológico
- **Frontend:** React, TailwindCSS, Recharts, Three.js
- **Backend:** FastAPI, Pydantic, Motor (MongoDB)
- **IA:** Gemini Vision via emergentintegrations
- **Email:** Resend

## Arquitectura del Código
```
/app/backend/
├── core/
│   └── config.py              # Configuración central y auth
├── models/
│   └── schemas.py             # Modelos Pydantic
├── services/
│   ├── email.py               # Servicios de email
│   ├── helpers.py             # Funciones auxiliares
│   └── cronograma_ai.py       # Análisis de cronogramas
├── uploads/
└── server.py                  # API principal (~3300 líneas)

/app/frontend/src/components/Projects/
├── CatalogoMaquinariaSection.jsx  # NUEVO - Sección de catálogo con IA
├── ProjectFormContent.jsx         # Formulario de proyecto (actualizado)
├── AvancesSemanalesModal.jsx      # Modal de avances (actualizado)
├── PointCloudViewer.jsx           # Visor de modelos .ply
└── ComparacionAvanceModal.jsx     # Comparación dron vs residente
```

## Tareas Completadas
- ✅ Sistema de autenticación JWT
- ✅ CRUD de proyectos con fases
- ✅ Avances semanales con modelos 3D
- ✅ Comparación de avances Dron vs Residente con IA
- ✅ Alertas automáticas por discrepancias
- ✅ Reporte semanal automático
- ✅ Dashboard de métricas históricas
- ✅ Exportación a Excel y PDF
- ✅ Refactorización del backend
- ✅ **Catálogo de Maquinaria con análisis IA** (2025-12-18)
- ✅ **Simplificación formulario de avance** (2025-12-18)

## Tareas Pendientes

### Próximas (P1)
- **Test E2E del Análisis de Fotos con IA**: La UI está integrada pero falta verificar con imagen real

### Futuras (P2-P3)
- **Formulario de Programación de Vuelos**: Crear formulario completo para agendar vuelos
- **Filtrado por Rol de Cliente**: Usuarios "Cliente" solo ven sus proyectos asignados
- **Verificar Pronóstico de Finalización**: Validar lógica de estimación de tiempo

## Notas Técnicas
- El catálogo de maquinaria usa Gemini AI para analizar y proponer distribución
- El análisis considera: dimensiones de máquinas, rendimiento, espacio de maniobra
- Los modelos .ply se suben localmente después de crear el avance semanal
- PDFs se guardan en `/app/backend/uploads/reportes_residente/`
