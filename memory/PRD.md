# DrON Topografía - Product Requirements Document

## Estado Actual (Actualizado: 2026-02-19)
- **Sistema Funcional**: Dashboard multi-fase completamente operativo
- **IA 100% Funcional**: Catálogo de Maquinaria + Análisis de Fotos + Volumetría DEM
- **🆕 Volumetría DEM (TIFF)**: Cálculo retiro/relleno con heatmap + interpretación IA
- **🆕 Landing page** pública en `/`, dark mode completo en `/app/*`
- **Arquitectura Modular**: server.py 5089 → 2475 líneas, 8 routers modulares

## Volumetría DEM (Feb 2026)
Nueva funcionalidad para calcular volumen de material retirado/rellenado entre semanas:

**Backend**:
- `services/dem_volumetry.py`: cálculo con rasterio + numpy, reproyección a grilla común, percentiles para outliers, heatmap matplotlib (rojo=retiro, azul=relleno), interpretación con Gemini.
- `routes/dem_volumetry.py`: 8 endpoints (subir/eliminar DEM avance, subir DEM terreno original al proyecto, calcular volumetría, listar/eliminar comparaciones, servir heatmap PNG, interpretar IA).
- Modelos: `AvanceSemanal.dem_gridfs_id` + `dem_metadata`, `Proyecto.dem_terreno_original_gridfs_id`, colección `comparaciones_dem`.

**Frontend**:
- `components/Projects/DEMVolumetrySection.jsx`: UI completa dentro del modal de Avances Semanales — subida de DEM semanal + terreno original, dropdown para elegir contra qué comparar (cualquier avance con DEM o terreno original), tarjetas grandes con Retirado/Rellenado/Neto, heatmap PNG, texto IA opcional, vista de comparaciones previas.

**Resultado de prueba**: validado con DEMs sintéticos — calculó 4500 m³ retirado / 25 m³ rellenado / -4475 m³ neto con precisión perfecta.

## Refactor P0 Completado (2026-02-11)
Se extrajeron 7 bloques cohesivos del monolito `server.py` (5089 líneas) hacia routers modulares en `/app/backend/routes/`:

| Router | Endpoints extraídos | Descripción |
|---|---|---|
| `routes/comparaciones.py` | comparar-avance, comparaciones, reportes-residente | Comparación de avances con PDF residente (Gemini) |
| `routes/exportar.py` | exportar/metricas-excel, exportar/metricas-pdf | Exportación de métricas históricas |
| `routes/reporte_ejecutivo.py` | proyectos/{id}/reporte-ejecutivo | Reporte ejecutivo PDF |
| `routes/solicitudes_vuelo.py` | solicitudes-vuelo (CRUD + estado) | Solicitudes de vuelo de clientes + emails |
| `routes/cronograma.py` | importar/actualizar/obtener cronograma, frentes, analizar-desviacion | Gestión de cronogramas |
| `routes/maquinaria_ia.py` | analizar-catalogo-maquinaria, comparar-plan-ia, dashboard/comparaciones-resumen | IA de catálogo de maquinaria |
| `routes/analisis_ia.py` | analisis/foto-avance, generar-reporte-ia | IA de fotos de avance |

**Servicios nuevos**: `services/notifications.py` (helper `crear_notificacion_sistema` reutilizable).

**Resultados de testing (testing_agent v3, iteration 18)**: 52/53 PASS (98%). Cero regresiones. Único skip por dato obsoleto en BD (no relacionado al refactor).

**Lo que quedó en server.py (2493 líneas)**: Auth + usuarios, notificaciones, CRUD proyectos, vuelos + nube de puntos, avances semanales + imágenes ZIP, modelos 3D con chunked upload + GridFS streaming + open3d preview, estadísticas, scheduler (reporte semanal + análisis desviación).

## Funcionalidades de IA Completadas

### 1. Catálogo de Maquinaria con Plan de Trabajo IA ✅
Genera planes de trabajo óptimos basados en las máquinas disponibles:

**Entrada:**
- Excel con catálogo de máquinas (Tipo, Marca, Modelo, Estatus)
- Parámetros del proyecto:
  - Área del terreno (m²)
  - Espacio de maniobra (m²)
  - Distancia entre pilas (m)
  - Volumen de excavación (m³)
  - Número de pilas

**Salida del análisis IA:**
- **plan_excavacion**: Máquinas recomendadas, tiempo estimado, rendimiento m³/día
- **plan_pilas**: Máquinas recomendadas, tiempo estimado, pilas/día
- **plan_anclas**: Máquinas recomendadas, tiempo estimado, anclas/día
- **maquinas_con_specs**: Especificaciones técnicas de cada máquina
  - Dimensiones (largo × ancho × altura)
  - Radio de giro
  - Rendimiento
  - Si es adecuada para el proyecto
- **distribucion_espacial**: Recomendaciones de ubicación y seguridad
- **resumen_ejecutivo**: Resumen del plan completo

**Ejemplo de resultado:**
```
Plan Excavación: CAT EXC. 324, CAT EXC. 320 → 2 días, 5,000 m³/día
Plan Pilas: XCMG XR168E, XCMG XR150, SOILMEC SR30 → 6 días, 8 pilas/día
Plan Anclas: SOILMEC SM14 → 3 días, 6 anclas/día
Total estimado: 11 días
```

### 2. Análisis de Fotos de Avance con IA ✅
Analiza fotos aéreas de dron para detectar:
- Pilas terminadas y en proceso
- Anclas instaladas
- Excavaciones activas
- Maquinaria visible
- Estado del proyecto (EN_TIEMPO/RETRASADO/ADELANTADO)

**Ejemplo de resultado con foto real:**
```
Pilas en proceso: 2
Excavaciones activas: 3
Maquinaria visible: Excavadoras, grúas, camiones
Estado: RETRASADO (vs 576 pilas planeadas)
Confianza: MEDIA
```

## Endpoints de IA

### Catálogo de Maquinaria
```
POST /api/proyectos/analizar-catalogo-maquinaria
  ?area_terreno=10000
  &volumen_excavacion=50000
  &num_pilas=576
  &distancia_pilas=3
  &espacio_maniobra=5000
  Body: form-data { file: archivo.xlsx }
```

### Análisis de Fotos
```
POST /api/avances/{avance_id}/analizar-foto
  Body: { "imagen_base64": "..." }
```

## Testing
- **22/22 tests pasados** para catálogo de maquinaria
- Integración con Gemini AI funcional (usa EMERGENT_LLM_KEY)
- Archivo de prueba: `/tmp/test_catalogo.xlsx` (36 máquinas, 29 disponibles)

## Credenciales de Prueba
- **Admin:** admin@dron.mx / admin123
- **Cliente:** cliente@test.com / cliente123

## Tareas Completadas
- ✅ Sistema de autenticación JWT
- ✅ CRUD de proyectos con fases
- ✅ Avances semanales con modelos 3D
- ✅ Comparación de avances Dron vs Residente
- ✅ Alertas automáticas por discrepancias
- ✅ Reporte semanal automático
- ✅ Dashboard de métricas históricas
- ✅ Exportación a Excel y PDF
- ✅ **Catálogo de Maquinaria con IA** (100% funcional)
- ✅ **Análisis de Fotos con IA** (100% funcional)
- ✅ **Parámetros del Terreno** guardados
- ✅ **Comparación de Planes: Real vs Usuario vs IA** (100% funcional) - 2025-12-18

## Comparación de Planes (Nueva Feature)

### Descripción
Sección del dashboard que compara visualmente tres series de datos:
1. **Progreso Real**: Datos de avances semanales registrados
2. **Plan del Usuario**: Cronograma planeado por el usuario (semanas por fase)
3. **Plan de IA**: Recomendación generada por el análisis de maquinaria

### Endpoints
```
POST /api/proyectos/{proyecto_id}/comparar-plan-ia
  - Genera comparación usando Gemini AI
  - Guarda resultado en campo 'comparacion_planes' del proyecto

GET /api/proyectos/{proyecto_id}/comparacion-planes
  - Obtiene la comparación guardada

GET /api/dashboard/comparaciones-resumen
  - Resumen de comparaciones de todos los proyectos
```

### Componente Frontend
- `ComparacionPlanesView.jsx` integrado en `DashboardView.jsx`
- Gráfica de barras con 3 series usando Recharts
- Cards por fase (Excavación, Pilas, Anclas)
- Badge de veredicto: "Plan IA es Mejor" / "Tu Plan es Mejor" / "Similar"
- Botón toggle para mostrar/ocultar
- Solo visible para proyectos con `analisis_maquinaria_ia`

### Testing
- Backend: 14/14 tests passed
- Frontend: 5/5 tests passed
- Test file: `/app/backend/tests/test_comparacion_planes.py`

## Programa de Obra / Cronograma (Nueva Feature - 2025-12-18)

### Descripción
Funcionalidad para subir y actualizar el programa de obra (cronograma Excel) a proyectos existentes desde la sección de proyectos.

### Endpoints
```
GET /api/proyectos/{proyecto_id}/cronograma
  - Obtiene información del cronograma cargado
  - Devuelve: tiene_cronograma, archivo, fecha_carga, resumen, frentes

POST /api/proyectos/{proyecto_id}/actualizar-cronograma
  - Sube/actualiza el cronograma Excel del proyecto
  - Parsea el archivo, actualiza métricas del proyecto
  - Recrea los frentes de trabajo

POST /api/proyectos/{proyecto_id}/analizar-desviacion
  - Compara progreso real vs cronograma planificado
  - Envía alerta por email (Resend) si desviación >20%
  - Retorna: desviaciones por fase, progreso esperado, estado alerta

GET /api/plantilla-cronograma
  - Descarga plantilla Excel de ejemplo
```

### Componente Frontend
- `CronogramaProyectoModal.jsx` integrado en `ProyectosView.jsx`
- Botón con icono CalendarClock en cada tarjeta de proyecto
- Modal muestra estado actual del cronograma o permite subir nuevo
- **Sección "Análisis de Desviación"** con botón "Analizar y Alertar"
- Visualización de desviaciones por fase con tabla comparativa
- Badge de estado: Alerta Crítica / Moderada / Sin Desviaciones
- Indicador "Email enviado" cuando se envía alerta

### Testing
- Backend: 9/9 tests passed
- Frontend: 7/7 tests passed
- Test file: `/app/backend/tests/test_cronograma_proyecto.py`

## Tareas Pendientes

### Próximas (P1)
- Refactorizar endpoints nuevos de `server.py` a `routes/proyectos.py`

### Futuras (P2-P3)
- ~~Filtrado por Rol de Cliente~~ ✅ Completado
- Formulario de Programación de Vuelos con notificaciones

## Tareas Completadas Recientemente

### Formulario Dinámico de Avances Semanales con IA (2025-12-19)
- **Formulario adaptativo**: Muestra campos según las fases activas del proyecto
  - Excavación: Campo de volumen excavado (m³)
  - Cimentación: Campos de pilas y anclas completadas
  - Edificación: Campo de muros completados
- **Análisis con IA**: Botón para subir foto y detectar avance automáticamente
  - Sube foto → IA analiza → Rellena formulario → Usuario revisa y ajusta
  - Endpoint: `POST /api/analisis/foto-avance`
- **Meta visible**: Muestra la meta planeada junto a cada campo

### Fix: Almacenamiento de Modelos 3D para Producción (2025-12-19)
- **Problema**: Los archivos .ply se guardaban en filesystem local, que no persiste en Kubernetes
- **Solución**: Implementado almacenamiento en MongoDB GridFS
- **Nuevo servicio**: `/app/backend/services/storage.py` con clase `GridFSStorage`
- **Endpoints actualizados**:
  - `POST /api/proyectos/{id}/avances-semanales/{avance_id}/modelo3d` - Guarda en GridFS
  - `GET /api/modelos3d/gridfs/{file_id}` - Obtiene de GridFS
  - Endpoint legacy mantenido para compatibilidad

### Fix: Fases de Construcción en Edición de Proyectos (2025-12-19)
- **Bug corregido**: Ahora se pueden deseleccionar fases al editar proyectos
- **Nuevo campo `fases_activas`**: Se guarda en el proyecto para recordar selección
- **Checkboxes funcionales**: stopPropagation para evitar doble-toggle
- **Formulario de avances actualizado**: Usa `fases_activas` del proyecto

### Panel de Notificaciones (2025-12-19)
- **Botón en header** con badge de notificaciones no leídas
- **Panel deslizable** con lista de notificaciones
- Filtro "Solo no leídas"
- Acciones: Marcar como leída, Ver detalles, Eliminar
- Marcar todas como leídas
- **Integración automática** con análisis de desviación
- Refresco automático cada 30 segundos

### Subida de Archivos Grandes por Chunks (2025-12-19) ✅
- **Problema resuelto**: Archivos .ply de más de 10MB fallaban en producción por límite de ingress/proxy
- **Solución**: Sistema de subida por chunks (5MB cada uno) con almacenamiento temporal en GridFS
- **Flujo**:
  1. `init-upload`: Crea sesión de subida, devuelve `upload_id`
  2. `upload-chunk`: Guarda cada chunk directamente en GridFS (evita límite BSON 16MB)
  3. `complete-upload`: Ensambla chunks, guarda archivo final, elimina chunks temporales
- **Verificado con archivo de 192.7 MB** (39 chunks) exitosamente
- **Frontend actualizado**: Barra de progreso con porcentaje, estado de cada parte
- **Tests**: 11/11 backend + 100% frontend UI tests

### Endpoints de Upload por Chunks
```
POST /api/proyectos/{id}/avances-semanales/{avance_id}/modelo3d/init-upload
  Query: filename, total_size, total_chunks
  Response: { upload_id, message, total_chunks }

POST /api/proyectos/{id}/avances-semanales/{avance_id}/modelo3d/upload-chunk
  Form: upload_id, chunk_index, chunk (file)
  Response: { success, chunk_index, chunk_size }

POST /api/proyectos/{id}/avances-semanales/{avance_id}/modelo3d/complete-upload
  Query: upload_id
  Response: { success, url, filename, original_name, size_mb, gridfs_id }
```

### Endpoints de Notificaciones
```
GET /api/notificaciones - Lista notificaciones del usuario
POST /api/notificaciones - Crear notificación (admin)
PUT /api/notificaciones/{id}/leer - Marcar como leída
PUT /api/notificaciones/leer-todas - Marcar todas como leídas
DELETE /api/notificaciones/{id} - Eliminar notificación
```

### Análisis Automático de Desviación Semanal (2025-12-19)
- Job programado con APScheduler: **Lunes 9:00 AM**
- Analiza todos los proyectos con cronograma cargado
- Envía alertas por email solo si hay desviaciones >10%
- **Crea notificación en el sistema** automáticamente
- Guarda resultado del análisis en cada proyecto

### Filtrado de Vistas para Rol "Cliente" (2025-12-19)
- Backend filtra automáticamente según el token JWT
- Endpoint `/api/proyectos` y `/api/estadisticas/resumen` filtrados
- Clientes solo ven proyectos asignados a ellos
- Frontend muestra vista de solo lectura para clientes
- Navegación adaptada: oculta opciones de administración
