# DrON Topografía - Product Requirements Document

## Estado Actual (Actualizado: 2025-12-18)
- **Sistema Funcional**: Dashboard multi-fase completamente operativo
- **Bugs Corregidos**: Catálogo de maquinaria y visor de modelos 3D

## Correcciones Realizadas Hoy (2025-12-18)

### 1. Bug: Catálogo de Maquinaria - "No se encontraron máquinas"
**Problema**: El Excel tenía filas vacías al inicio y el parser no detectaba correctamente la fila de headers.

**Solución**: 
- Se implementó detección automática de la fila de headers buscando palabras clave (TIPO, MARCA, MODELO)
- Se agregó mapeo flexible de nombres de columnas (acepta variaciones como "TIPO DE MAQUINA", "TIPO", "EQUIPO")
- El parser ahora salta filas vacías automáticamente

**Resultado**: 36 máquinas extraídas correctamente del catálogo de prueba (29 disponibles)

### 2. Bug: Modelo 3D PLY no carga
**Problema**: Archivos grandes (193MB+) causaban timeout y el visor no mostraba progreso descriptivo.

**Solución**:
- Se aumentó el timeout de 15 a 60 segundos
- Se agregó diezmado automático de puntos para archivos con más de 5 millones de puntos
- Se mejoró el indicador de progreso con mensajes descriptivos (tamaño descargado, estado de procesamiento)
- Se agregó mensaje informativo para archivos grandes

## Sistema de Fases de Construcción

### Fases Implementadas
- **Excavación**: Volumen total en m³
- **Cimentación**: Pilas + Anclas  
- **Edificación**: Muros

### Cálculo de Avance
- Avance TOTAL = promedio de todas las fases activas

## Funcionalidades Principales

### Catálogo de Maquinaria con Análisis IA
- Subir Excel con catálogo de maquinaria
- Extracción automática: Tipo, Marca, Modelo, Estatus, Operador, Obra, Ubicación
- Categorización: Excavadoras, Perforadoras, Perforadoras de Anclas, Grúas, Manipuladores
- Análisis con Gemini AI (opcional): Plan de ejecución óptimo por fase

**Formato del Excel aceptado:**
- Filas vacías al inicio son ignoradas
- Headers detectados automáticamente
- Columnas flexibles: "TIPO DE MAQUINA" o "TIPO" o "EQUIPO"

### Avances Semanales
- Registro semanal sin URL de modelo
- Modelo 3D (.ply) se sube después de crear el avance
- Visor mejorado con soporte para archivos grandes (hasta 200MB+)

### Dashboard Principal
- Mapa interactivo con marcadores
- KPIs: Proyectos, Volumen, Avance

### Comparación Dron vs Residente
- Subir PDF del residente
- Análisis automático con IA
- Alertas por discrepancias >15%

### Métricas Históricas
- Gráficas de evolución
- Exportación Excel/PDF

## Credenciales de Prueba
- **Admin:** admin@dron.mx / admin123
- **Cliente:** cliente@test.com / cliente123

## Stack Tecnológico
- **Frontend:** React, TailwindCSS, Three.js
- **Backend:** FastAPI, Motor (MongoDB)
- **IA:** Gemini Vision
- **Email:** Resend

## Tareas Pendientes

### Próximas (P1)
- **Test E2E del Análisis de Fotos con IA**

### Futuras (P2-P3)
- Formulario de Programación de Vuelos
- Filtrado por Rol de Cliente

## Notas Técnicas
- Archivos .ply grandes son diezmados automáticamente a ~2M puntos para mejor rendimiento
- El catálogo detecta automáticamente la fila de headers en el Excel
- El análisis IA puede no estar disponible temporalmente (límites de API), pero el catálogo siempre se procesa
