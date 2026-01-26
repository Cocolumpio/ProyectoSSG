# 📘 Instrucciones: Cómo Cargar y Visualizar tu Archivo LAZ

## 🎉 ¡Visor 3D Real Implementado!

Tu sistema **DroneBuild Pro** ahora tiene un **visor 3D completamente funcional** con Three.js que puede renderizar archivos LAZ/LAS reales.

---

## 🚀 Cómo Usar el Visor 3D

### **Paso 1: Acceder al Dashboard**
1. Abre tu navegador y ve a: https://dron-dashboard.preview.emergentagent.com
2. Verás el dashboard principal con 3 proyectos activos

### **Paso 2: Seleccionar un Proyecto**
1. En la sección "Proyectos Activos" (lado derecho), haz clic en cualquier proyecto
2. El mapa se centrará en el proyecto seleccionado
3. Aparecerá el **Visor 3D - Nube de Puntos** más abajo

### **Paso 3: Cargar tu Archivo LAZ**
1. Haz scroll hacia abajo hasta ver el **"Visor 3D - Nube de Puntos"**
2. Haz clic en el botón azul **"Cargar Nube de Puntos"**
3. Selecciona tu archivo LAZ (o LAS, PLY, XYZ)
4. Espera mientras el archivo se sube y procesa (puede tomar 5-30 segundos dependiendo del tamaño)

### **Paso 4: Visualizar e Interactuar**
Una vez cargado, verás tu nube de puntos en 3D con:

**Controles del Mouse:**
- 🖱️ **Clic izquierdo + arrastrar**: Rotar la vista
- 🖱️ **Scroll**: Zoom in/out
- 🖱️ **Clic derecho + arrastrar**: Pan (mover la vista)
- 🔄 **Botón reset**: Volver a la vista inicial

**Información Mostrada:**
- Total de puntos en el archivo
- Puntos siendo renderizados (optimizado a 100,000 máximo)
- Rango X, Y, Z (dimensiones)
- Volumetrías del vuelo (excavación, relleno, materiales)

---

## 🎨 Características del Visor

### **Coloreado por Altura**
Los puntos se colorean automáticamente basándose en su altura (Z):
- 🔵 **Azul**: Puntos más bajos
- 🟢 **Verde**: Altura media-baja
- 🟡 **Amarillo**: Altura media-alta
- 🔴 **Rojo**: Puntos más altos

### **Optimización Automática**
- Si tu archivo tiene más de 100,000 puntos, el sistema hace un **muestreo aleatorio uniforme**
- Esto mantiene el rendimiento fluido sin perder la forma general de la nube
- Puedes ajustar este límite en el código si necesitas más puntos

### **Grid de Referencia**
- Un grid 3D te ayuda a entender la escala y posición
- El grid es infinito y sigue la cámara

### **Stats de Rendimiento**
- En la esquina superior izquierda verás FPS (cuadros por segundo)
- Útil para monitorear el rendimiento con nubes grandes

---

## 📁 Formatos Soportados

### **Archivos Soportados**
✅ **.laz** - LAS comprimido (recomendado)
✅ **.las** - Estándar de nubes de puntos LIDAR
✅ **.ply** - Polygon File Format
✅ **.xyz** - Texto plano con coordenadas
✅ **.txt** - Formato personalizado

### **Requisitos del Archivo**
- El archivo debe ser un archivo válido de nube de puntos
- Tamaño recomendado: < 500 MB
- Puntos recomendados: 100K - 50M puntos

---

## 🔧 Procesamiento Backend

El sistema hace lo siguiente con tu archivo:

1. **Upload**: Sube el archivo al servidor
2. **Parsing**: Lee el archivo LAZ/LAS usando la librería `laspy`
3. **Extracción**: Obtiene coordenadas X, Y, Z de cada punto
4. **Normalización**: Centra los puntos en el origen (0,0,0)
5. **Downsampling**: Si hay muchos puntos, hace muestreo aleatorio
6. **Coloreado**: Calcula colores basados en altura
7. **Serialización**: Convierte a JSON para el frontend
8. **Renderizado**: Three.js renderiza los puntos en 3D

---

## 🛠️ Tecnologías Utilizadas

### Backend
- **FastAPI**: Framework web
- **laspy[laszip]**: Procesamiento de archivos LAZ/LAS
- **NumPy**: Cálculos matemáticos y muestreo
- **Python 3.11**: Lenguaje principal

### Frontend
- **Three.js 0.182**: Motor de renderizado 3D WebGL
- **@react-three/fiber**: React renderer para Three.js
- **@react-three/drei**: Helpers y componentes útiles
- **React 19**: Framework UI

---

## 📊 API Endpoints

### **Upload**
```bash
POST /api/upload/nube-puntos/{vuelo_id}
Content-Type: multipart/form-data

# Respuesta:
{
  "message": "Archivo subido exitosamente",
  "filename": "abc123.laz",
  "vuelo_id": "..."
}
```

### **Procesar**
```bash
GET /api/process/nube-puntos/{vuelo_id}?max_points=100000

# Respuesta:
{
  "success": true,
  "vuelo_id": "...",
  "metadata": {
    "total_points": 1500000,
    "displayed_points": 100000,
    "bounds": { "x": {...}, "y": {...}, "z": {...} },
    "center": { "x": ..., "y": ..., "z": ... }
  },
  "points": [
    { "x": 1.23, "y": 4.56, "z": 7.89, "color": [0.5, 0.8, 0.2] },
    ...
  ]
}
```

---

## 🐛 Solución de Problemas

### **El visor muestra "Procesando..." por mucho tiempo**
- **Causa**: El archivo es muy grande
- **Solución**: Espera hasta 60 segundos. Si continúa, verifica la consola del navegador (F12)

### **Error: "Formato no permitido"**
- **Causa**: El archivo no tiene extensión .laz, .las, .ply, .xyz o .txt
- **Solución**: Verifica la extensión del archivo

### **Error: "Error procesando archivo"**
- **Causa**: El archivo está corrupto o no es un formato válido
- **Solución**: Verifica que el archivo se pueda abrir con software LAZ (CloudCompare, QGIS)

### **El visor está en blanco/negro**
- **Causa**: El navegador no soporta WebGL
- **Solución**: Usa Chrome, Firefox o Edge moderno. Safari también funciona.

### **El visor va lento (< 30 FPS)**
- **Causa**: Demasiados puntos o GPU débil
- **Solución**: Reduce `max_points` en la URL: `?max_points=50000`

---

## 📈 Próximas Mejoras Posibles

### **Funcionalidades Avanzadas**
- [ ] Mediciones en el modelo 3D
- [ ] Cortes transversales
- [ ] Comparación de nubes (antes/después)
- [ ] Coloreado por intensidad RGB
- [ ] Exportación de vistas
- [ ] Anotaciones y marcadores
- [ ] Integración con Potree para nubes masivas (> 100M puntos)

### **Mejoras de UI**
- [ ] Panel de configuración de visualización
- [ ] Ajuste de tamaño de punto
- [ ] Selector de esquema de colores
- [ ] Histograma de altura
- [ ] Perfil de elevación

---

## 💡 Tips y Mejores Prácticas

1. **Archivos Grandes**: Para archivos > 10M puntos, considera usar Potree
2. **Calidad vs Performance**: Ajusta `max_points` según tu GPU
3. **Nombres de Archivo**: Usa nombres descriptivos para tus archivos LAZ
4. **Backup**: El sistema guarda los archivos en `/app/backend/uploads/`
5. **Múltiples Vuelos**: Carga diferentes vuelos y compáralos

---

## 🎓 Recursos Adicionales

### **Documentación**
- [Three.js Documentation](https://threejs.org/docs/)
- [laspy Documentation](https://laspy.readthedocs.io/)
- [LAS Format Specification](https://www.asprs.org/divisions-committees/lidar-division/laser-las-file-format-exchange-activities)

### **Herramientas Útiles**
- **CloudCompare**: Visor de nubes de puntos de escritorio
- **QGIS**: GIS con soporte para LAZ
- **Potree**: Visor web para nubes masivas

---

## 📞 Soporte

Si encuentras algún problema o tienes preguntas:
1. Verifica esta guía primero
2. Revisa los logs del navegador (F12 → Console)
3. Verifica los logs del backend: `/var/log/supervisor/backend.err.log`

---

**¡Disfruta visualizando tus nubes de puntos en 3D!** 🚁✨
