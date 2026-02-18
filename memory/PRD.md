# DrON Topografía - Product Requirements Document

## Estado Actual (Actualizado: 2025-12-18)
- **Sistema Funcional**: Dashboard multi-fase completamente operativo
- **Refactorización**: Backend modularizado exitosamente
- **Testing**: 100% de pruebas pasadas (39 tests totales)

## Refactorización Completada (2025-12-18)

### Cambios Realizados
El archivo monolítico `server.py` (3534 líneas) fue refactorizado:

1. **`/app/backend/core/config.py`** (151 líneas)
   - Configuración central de la aplicación
   - Conexión a MongoDB (singleton)
   - Configuración JWT
   - Funciones de autenticación: `verify_password`, `get_password_hash`, `create_access_token`
   - Dependencias: `get_current_user`, `get_current_admin`, `get_optional_user`
   - Variables de entorno: `RESEND_API_KEY`, `ADMIN_EMAIL`, `EMERGENT_LLM_KEY`

2. **`/app/backend/services/helpers.py`** (186 líneas)
   - `recalcular_avance_proyecto()`: Recalcula avance basado en fases activas
   - `generar_google_calendar_link()`: Genera links para Google Calendar
   - `obtener_metricas_proyecto()`: Obtiene métricas acumuladas

3. **`/app/backend/services/email.py`** (293 líneas)
   - `enviar_alerta_discrepancia()`: Alertas de discrepancias >15%
   - `enviar_notificacion_solicitud_vuelo()`: Notificación de nuevas solicitudes
   - `enviar_actualizacion_solicitud()`: Notificación al cliente de cambios de estado

4. **`/app/backend/server.py`** (3254 líneas - reducido 280 líneas)
   - Ahora importa funciones compartidas de los módulos
   - Mantiene toda la lógica de endpoints
   - Código más limpio y mantenible

### Verificación de Refactorización
- ✅ Todas las funciones de auth funcionando desde `core/config.py`
- ✅ `recalcular_avance_proyecto` funciona desde `services/helpers.py`
- ✅ Servicios de email importados correctamente
- ✅ 39 tests de backend pasando (21 + 18)
- ✅ Frontend funciona correctamente

## Sistema de Fases de Construcción

### Fases Implementadas
- **Excavación**: Volumen total en m³
- **Cimentación**: Pilas + Anclas  
- **Edificación**: Muros

### Cálculo de Avance
- Avance TOTAL = promedio de todas las fases activas
- Ejemplo: Torre Corporativa Demo
  - Excavación: 84% (21,000/25,000 m³)
  - Cimentación: 69% (promedio pilas+anclas)
  - Edificación: 11% (5/45 muros)
  - **TOTAL: 52.3%**

## Funcionalidades Implementadas

### Dashboard Principal
- Mapa interactivo con marcadores de proyectos
- KPIs: Proyectos activos, Volumen excavado, Avance promedio
- Lista de proyectos con barras de progreso por fase

### Gestión de Proyectos
- CRUD completo de proyectos
- Configuración de fases activas
- Metas por fase (m³, pilas, anclas, muros)
- Asignación de clientes

### Avances Semanales
- Registro semanal por proyecto
- Modelos 3D (archivos .ply)
- Fotos del vuelo
- Métricas de excavación, pilas, anclas, muros

### Comparación de Avances con IA
- Subir PDF del residente
- Análisis automático con Gemini
- Comparación lado a lado
- Alertas automáticas por discrepancias >15%

### Métricas Históricas
- Gráficas de evolución por semana
- Comparativa entre proyectos
- Exportación a Excel y PDF

### Reporte Semanal Automático
- Envío cada viernes 18:00
- KPIs: Proyectos, Volumen, Pilas, Anclas, Muros
- Desglose de costos de flotilla
- Envío manual disponible para admin

### Solicitudes de Vuelo
- Formulario para clientes
- Notificación por email al admin
- Link de Google Calendar
- Estados: pendiente, confirmado, completado, cancelado

## Credenciales de Prueba
- **Admin:** admin@dron.mx / admin123
- **Cliente:** cliente@test.com / cliente123

## Stack Tecnológico
- **Frontend:** React, TailwindCSS, Recharts, Three.js
- **Backend:** FastAPI, Pydantic, Motor (MongoDB)
- **IA:** Gemini Vision via emergentintegrations
- **Email:** Resend

## Integraciones
- **Gemini Vision**: Análisis de PDFs y fotos
- **Resend**: Notificaciones por email
- **OpenStreetMap**: Geocodificación de ubicaciones

## Tareas Completadas
- ✅ Sistema de autenticación JWT
- ✅ CRUD de proyectos con fases
- ✅ Avances semanales con modelos 3D
- ✅ Comparación de avances Dron vs Residente con IA
- ✅ Alertas automáticas por discrepancias
- ✅ Reporte semanal automático (viernes 18:00)
- ✅ Dashboard de métricas históricas
- ✅ Exportación a Excel y PDF
- ✅ **Refactorización del backend** (2025-12-18)

## Tareas Pendientes

### Próximas (P1)
- **Test E2E del Análisis de Fotos con IA**: La UI está integrada en el modal de Avances Semanales pero falta verificar end-to-end con una imagen real

### Futuras (P2-P3)
- **Formulario de Programación de Vuelos**: Crear formulario completo para agendar vuelos
- **Filtrado por Rol de Cliente**: Usuarios "Cliente" solo deben ver sus proyectos asignados
- **Verificar Pronóstico de Finalización**: Validar lógica de estimación de tiempo

## Arquitectura del Código
```
/app/backend/
├── core/
│   └── config.py          # Configuración central y auth
├── models/
│   └── schemas.py         # Modelos Pydantic
├── services/
│   ├── email.py           # Servicios de email
│   ├── helpers.py         # Funciones auxiliares
│   ├── cronograma_ai.py   # Análisis de cronogramas con IA
│   └── database.py        # Conexión a DB
├── routes/
│   ├── auth.py            # (preparado para futura modularización)
│   ├── proyectos.py       # (preparado para futura modularización)
│   ├── estadisticas.py    # (preparado para futura modularización)
│   └── vuelos.py          # (preparado para futura modularización)
├── tests/
│   └── test_*.py          # Tests automatizados
└── server.py              # API principal (3254 líneas)
```

## Notas Técnicas
- La comparación de avances usa datos ACUMULADOS del proyecto
- El nivel de confianza (ALTA/MEDIA/BAJA) indica seguridad de extracción
- PDFs se guardan en `/app/backend/uploads/reportes_residente/`
- Archivos .laz descartados, se usa .ply como estándar
