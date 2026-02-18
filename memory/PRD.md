# DrON Topografía - Product Requirements Document

## Estado Actual (Actualizado: 2025-12-18)
- **Sistema Funcional**: Dashboard multi-fase completamente operativo
- **IA 100% Funcional**: Catálogo de Maquinaria + Análisis de Fotos

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

## Tareas Pendientes

### Próximas (P1)
- Refactorizar endpoints nuevos de `server.py` a `routes/proyectos.py`

### Futuras (P2-P3)
- Formulario de Programación de Vuelos
- Filtrado por Rol de Cliente
