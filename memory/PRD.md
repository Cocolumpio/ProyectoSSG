# DrON Topografía - Product Requirements Document

## Estado Actual (Actualizado: 2026-02-21)
- **Sistema Funcional**: Dashboard multi-fase completamente operativo
- **IA 100% Funcional**: Catálogo de Maquinaria + Análisis de Fotos + Volumetría DEM
- **Volumetría DEM (TIFF)**: Cálculo retiro/relleno con heatmap + interpretación IA
- **Landing page** pública en `/`, dark mode completo en `/app/*`
- **Arquitectura Modular**: server.py refactorizado, 10 routers modulares
- **Matriz de Pilas/Anclas por 4 Caras**: configuración por proyecto + heatmap interactivo en dashboard + tabla en PDF
- **Reporte Ejecutivo Mejorado**: gráficas de avance físico Planeado vs Real por categoría (vertical agrupadas + horizontales con %)
- **🆕 Programa de Obra V2**: parser detecta automáticamente cronogramas con columnas diarias por semana (LUN-DOM × N semanas)
- **🆕 Tarjetas Comparativa Semanal**: una tarjeta por cada semana del programa con planeado vs real (drone) + presupuesto, mostrando solo las fases activas en esa semana
- **🆕 Alertas WhatsApp + Comentarios Semanales (Feb 2026)**: Twilio + IA recomendaciones de recuperación + comentarios por semana en avances.

## 🆕 Alertas WhatsApp + Comentarios Semanales (Feb 2026)
Sistema de detección de desviación ≥10% que notifica a directores vía WhatsApp con un plan de recuperación generado por IA (Claude Sonnet 4.5 via Emergent LLM Key).

**Backend**:
- `routes/directores.py`: CRUD admin para `db.directores` ({id, nombre, whatsapp, cargo, activo, created_at}).
- `services/whatsapp.py`: cliente Twilio, normalización a E.164 (default +52), captura excepciones (success=false).
- `services/ia_recomendacion.py`: prompt estructurado a Claude Sonnet 4.5 → DIAGNÓSTICO / PREGUNTAS CLAVE / ACCIONES INMEDIATAS / REVISAR PROGRAMA / PLAN DE RECUPERACIÓN. Fallback heurístico por fase (excavación/anclas/pilas/muros).
- `routes/alertas.py`: 
  - POST `/api/proyectos/{id}/alerta-desviacion?forzar=bool` — evalúa última semana con avance real > 0, compara acumulado por fase contra programa, dispara WhatsApp si desviación ≤ -10% o forzar=true. Idempotente (clave `proyecto:semana` en `db.alertas_enviadas`).
  - GET `/api/proyectos/{id}/alertas-historial` — lista de alertas enviadas (admin + cliente con acceso).
  - PUT/GET/DELETE `/api/proyectos/{id}/comentario-semana/{semana}` — admin guarda justificación textual ≤2000 chars; cliente sólo lee.
  - `evaluar_y_disparar_si_aplica(proyecto_id)` hook llamado desde el flujo de upload de avance semanal en `server.py`.

**Frontend**:
- `components/Admin/DirectoresAdmin.jsx`: CRUD de destinatarios, integrado dentro de `UsuariosAdminView` (después del search).
- `components/Dashboard/AlertasDesviacionPanel.jsx`: panel del dashboard (sólo admin) con botones Evaluar desviación / Probar envío real (con confirm) / Ver historial. Muestra recomendación IA en `<details>`.
- `components/Projects/ComentarioSemanaSection.jsx`: textarea por semana dentro de `AvancesSemanalesModal` (admin edita, cliente sólo lee). Persiste autor + timestamp.

**Stack añadido**: `httpx` (ya existente) — backend. **Green API (https://green-api.com)** reemplazó a Twilio (Feb 2026): el remitente es el WhatsApp personal del admin vinculado por QR (+52 1 33 1990 6249, instancia 7107658502 host https://7107.api.greenapi.com). Variables backend: `GREEN_API_HOST`, `GREEN_API_INSTANCE_ID`, `GREEN_API_TOKEN`.

**Endpoints adicionales (Green API)**:
- `GET /api/whatsapp/estado` — devuelve `{state: authorized|notAuthorized|...}` de la instancia.
- `POST /api/whatsapp/test` — `{to, message}` envía mensaje individual de prueba.

**UI**: `DirectoresAdmin` muestra badge de estado del bot (verde "authorized") + botón ✈️ "Enviar prueba" por director.

## 🆕 Resumen Semanal Automático desde Grupos de WhatsApp (Feb 2026)
Sistema que lee los mensajes del grupo de WhatsApp del proyecto y, cada domingo 22:00 CDMX, genera un resumen IA enfocado en JUSTIFICACIONES DE ATRASO que se guarda en `comentarios_semana`.

**Backend**:
- `services/whatsapp_groups.py`: `listar_grupos()` (Green API `getContacts` filtrado por `@g.us`), `buscar_grupo_para_proyecto()` (auto-match flexible normalizando acentos/case), `obtener_mensajes_grupo()` (`getChatHistory` con rango temporal), `formatear_mensajes_para_ia()`.
- `services/resumen_chat_ia.py`: Claude Sonnet 4.5 genera resumen estructurado (RESUMEN EJECUTIVO / JUSTIFICACIONES DE ATRASO / ACTIVIDADES / DECISIONES TÉCNICAS / RIESGOS / PARTICIPANTES). Truncado a 25k chars; correlaciona con avance real/esperado si está disponible.
- `routes/resumen_whatsapp.py`:
  - `GET /api/whatsapp/grupos` — lista grupos.
  - `GET /api/whatsapp/grupos/auto-match/{proyecto_id}` — sugerencia automática.
  - `PUT /api/proyectos/{id}/whatsapp-grupo` — vincular/desvincular.
  - `POST /api/proyectos/{id}/resumen-whatsapp-semana/{semana}` — genera manualmente.
  - `cron_resumen_semanal_dominical()` — hook del scheduler.
- `server.py`: nuevo cron job `CronTrigger(day_of_week='mon', hour=4, minute=0)` UTC = domingo 22:00 CDMX. Calcula semana actual desde `fecha_inicio` y dispara para todos los proyectos activos.
- Modelo `Proyecto`: nuevos campos `wa_grupo_chat_id`, `wa_grupo_nombre`.

**Frontend**:
- `components/Projects/WhatsAppGrupoSelector.jsx`: en el formulario del proyecto (modo edit), botón "Buscar grupos" + sugerencia automática + lista completa para selección manual.
- `ComentarioSemanaSection`: si `comentario.fuente === 'whatsapp_ia'` muestra badge "🤖 WhatsApp · IA". Botón "Resumir WhatsApp" disponible cuando el proyecto tiene grupo vinculado (admin).

**Validado en vivo (22 Jun 2026)**: Torre Mezquitan auto-matcheó con grupo "| Torre Mezquitan |". Resumen semana 19 procesó 11 mensajes, detectó correctamente "lluvia el sábado 20/06 sin protección de costales" como justificación de atraso.

## 🆕 Reforzamiento por Perfiles (Feb 2026)
Nueva fase de medición añadida al sistema, integrada con el flujo existente.

**Backend**:
- Modelos `Proyecto` / Create / Update: nuevos campos `perfiles_planeados`, `perfiles_ejecutados` (float).
- Modelos `AvanceSemanal` / Create / Update: campo `perfiles_completados` (float).
- `services/helpers.py`: `recalcular_avance_proyecto` incluye perfiles en el promedio de fase "Cimentación" (junto con pilas y anclas).
- `services/cronograma_ai.py`: nuevo mapeo `"REFORZAMIENTO"`, `"REFORZAMIENTO POR PERFILES"`, `"PERFILES"`, `"REFORZAMIENTO ESTRUCTURAL"` → fase `perfiles`. Contador `total_perfiles` agregado al resumen y a `programa_semanal[].perfiles`.
- `routes/cronograma.py`: persiste `perfiles_planeados` cuando `total_perfiles > 0` al subir el Excel.
- `routes/comparativa_semanal.py`: nueva fase con acumuladores, % por semana, % global y mapping de categorías de presupuesto ("reforzamiento" sin "colindancia" → perfiles).

**Frontend**:
- `ProjectFormContent.jsx`: input manual "Reforzamiento por Perfiles (pzas)" en la sección Cimentación.
- `ProyectosView.jsx`: campo en estado inicial, edición, payload de submit, y `actividades_tipo` incluye `'perfiles'` cuando `perfiles_planeados > 0`.
- `AvancesSemanalesModal.jsx`: input "Reforz. por Perfiles (pzas)" en el formulario de avance semanal (visible si proyecto tiene `perfiles_planeados > 0` o `actividades_tipo` incluye 'perfiles').
- `ComparativaSemanalCards.jsx`: nueva fila color emerald con icono ShieldCheck en cada tarjeta semanal (solo si la semana tiene perfiles planeados).

**Validado (22 Jun 2026 - Torre Mezquitan)**:
- Excel detectó **18 perfiles** correctamente desde sección "REFORZAMIENTO" → "COLOCACION Y COLADO DE PILA DE REFORZAMIENTO".
- Comparativa semanal: acumulado planeado=18 perfiles, real=0.
- Avance semanal con `perfiles_completados: 3` → `perfiles_ejecutados=3` en proyecto, `avance_actual` recalculado correctamente.

**Testing (iter_21)**: 14/14 pytest backend pasados (1 skipped por falta de proyecto con programa+avances), frontend admin y cliente verificados (cliente no ve panel de alertas ni edita comentarios).

## Comparativa Semanal — Programa de Obra V2 (Feb 2026)
- `services/cronograma_ai.py` extiende parser V2 con detección de bloques de 7 días por semana (PRELIMINARES + N semanas).
- `routes/comparativa_semanal.py` (NEW): GET `/api/proyectos/{id}/comparativa-semanal` devuelve `total_semanas`, `presupuesto_total_contrato` y array de semanas con planeado/real/pct/acumulado por fase, fechas, estado.
- Estado por semana: `pendiente` (sin avance real > 0), `ok` (>=90%), `atraso` (>=70%), `critico` (<70%).
- Frontend `Dashboard/ComparativaSemanalCards.jsx`: tarjetas responsive (grid 1-2-3 col), expandibles para ver actividades planeadas individuales (descripción + cantidad + importe).
- Solo muestra fases activas por semana — ej. Sem 1 solo Excavación, Sem 2 empieza Pilas/Anclas, Sem 14 solo Pilas.
- Persistencia: `programa_semanal` se guarda en el doc del proyecto al importar/actualizar cronograma.

**Testing (iter_20)**: 12/12 backend pytest passed; UI verificada con 16 tarjetas renderizando correctamente y filtrado por fase activa. Bug fix: estado="pendiente" cuando no hay métricas reales > 0 (anteriormente fallaba mostrando "critico" por avance.id en el truthy check).

## Matriz de Pilas/Anclas por Caras (Feb 2026)
Nueva funcionalidad para distribuir y visualizar el progreso de pilas y anclas en las 4 caras de la excavación:

**Backend**:
- Modelo `CaraExcavacion`: `{nombre, pilas, anclas, pilas_estados, anclas_estados}` (estados = lista binaria por celda).
- `routes/caras_excavacion.py`: GET configuración + resumen, PUT configurar (4 caras, admin), PUT toggle celda (admin), GET resumen agregado.
- `services/helpers.py`: cuando hay matriz configurada, pilas/anclas planeadas y ejecutadas se derivan de las celdas; fallback a avances semanales si no hay matriz.
- `services/avance_financiero.py`: usa totales de la matriz para Cimentación/Anclas cuando está activa.
- `routes/reporte_ejecutivo.py`: añade sección "Avance Físico por Categoría" con dos gráficas (vertical agrupada Planeado vs Real, horizontal con %) + tabla detallada; sección extra "Progreso por Cara de Excavación".

**Frontend**:
- `Projects/CarasExcavacionConfig.jsx`: inline en formulario de proyecto (aparece cuando se activa "Cimentación"), 4 tarjetas con nombre editable + cantidades de pilas/anclas.
- `Dashboard/MatrizCarasExcavacion.jsx`: heatmap por cara, toggle Pilas/Anclas, click binario, layout responsive con tamaño de celda adaptativo según cantidad.
- Integrado en `Dashboard/DashboardView.jsx` debajo del Gantt; `ProyectosView.jsx` persiste y rehidrata el campo.

**Testing**: 15/15 tests backend pasados (iter_19); estados read-only para cliente; RBAC validado (admin-only writes).

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

### Clasificación de Pilas: Cimentación vs Reforzamiento (2026-06)
- Al subir un programa de obra Excel (importar o actualizar), selector `tipo_pilas`: "auto" | "cimentacion" | "reforzamiento".
  - "reforzamiento": todas las pilas parseadas se reclasifican como Reforz. Perfiles (totales, tarjetas semanales, % esperado).
  - Backend: `aplicar_tipo_pilas()` en services/cronograma_ai.py; Form param en importar-cronograma y actualizar-cronograma; persistido en proyecto.tipo_pilas.
- Mapeo por defecto: "REFORZAMIENTO DE COLINDANCIAS" ahora → perfiles (antes pilas).
- Nuevo endpoint admin: POST /api/proyectos/{id}/reclasificar-pilas — migra pilas planeadas/ejecutadas → perfiles (programa_semanal, cronograma_resumen, avances, frentes, caras) y recalcula avance. Botón "Convertir a Reforzamiento" en CronogramaProyectoModal (panel data-testid=reclasificar-pilas-panel).
- USO PARA CLEMENTE 70 (producción): tras Redeploy, abrir Programa de Obra del proyecto → botón "Convertir a Reforzamiento" (1 clic).
- Fix: crear-desde-cronograma ahora persiste tipo_pilas, perfiles_planeados, cronograma_archivo/resumen/fecha_carga.
- Testeado: iteration_22 (frontend 100%) + curl e2e backend.
