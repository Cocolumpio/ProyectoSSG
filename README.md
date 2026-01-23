# 🚁 DroneBuild Pro - Sistema de Gestión de Construcción con Drones

Dashboard profesional para gestión y monitoreo de proyectos de construcción mediante vuelos de drones con análisis de nubes de puntos 3D.

![Dashboard Preview](https://img.shields.io/badge/Stack-MERN-green)
![License](https://img.shields.io/badge/License-MIT-blue)

## 🌟 Características Principales

### 📊 Dashboard Interactivo
- **KPIs en tiempo real**: Total de proyectos, vuelos realizados, avance promedio y volumetría total
- **Vista general**: Métricas consolidadas de todos los proyectos activos
- **Navegación fluida**: Tres vistas principales (Dashboard, Proyectos, Vuelos)

### 🗺️ Mapas Interactivos
- **Visualización geográfica**: Ubicación de todos los proyectos en mapa interactivo
- **Leaflet + OpenStreetMap**: Sin necesidad de API keys externas
- **Marcadores interactivos**: Click en marcadores para ver detalles del proyecto
- **Centrado automático**: El mapa se centra al seleccionar un proyecto

### 📐 Análisis Volumétrico
- **Cálculos de excavación**: Volumen de tierra removida (m³)
- **Cálculos de relleno**: Volumen de tierra agregada (m³)
- **Cálculos de materiales**: Volumen de materiales utilizados (m³)
- **Gráficos comparativos**: Visualización por vuelo y proyecto

### 🎯 Gestión de Proyectos
- **Información completa**: Nombre, ubicación, fechas, descripción
- **Seguimiento de avance**: Porcentaje de avance vs. planeado
- **Coordenadas GPS**: Ubicación exacta de cada proyecto
- **CRUD completo**: Crear, leer, actualizar y eliminar proyectos

### ✈️ Registro de Vuelos
- **Detalles de vuelo**: Fecha, duración, área cubierta, número de imágenes
- **Estado del vuelo**: Completado, procesando o fallido
- **Volumetrías asociadas**: Datos volumétricos por vuelo
- **Filtros**: Filtrar vuelos por proyecto

### 🔲 Visor 3D de Nubes de Puntos
- **Visualización 3D**: Renderizado de nubes de puntos densas
- **Carga de archivos**: Soporte para formatos .las, .laz, .ply, .xyz
- **Grid de referencia**: Sistema de coordenadas visual
- **Información del vuelo**: Datos contextuales en el visor

## 🏗️ Arquitectura Técnica

### Backend (FastAPI + MongoDB)
```
/app/backend/
├── server.py           # API principal
├── requirements.txt    # Dependencias Python
├── .env               # Variables de entorno
└── uploads/           # Archivos de nubes de puntos
```

**Endpoints Principales:**
- `GET /api/` - Health check
- `GET/POST /api/proyectos` - Gestión de proyectos
- `PUT /api/proyectos/{id}/avance` - Actualizar avance
- `GET/POST /api/vuelos` - Gestión de vuelos
- `POST /api/upload/nube-puntos/{vuelo_id}` - Subir archivos
- `GET /api/estadisticas/resumen` - Estadísticas generales

### Frontend (React + Tailwind CSS)
```
/app/frontend/
├── src/
│   ├── App.js              # Componente principal
│   ├── App.css             # Estilos del dashboard
│   ├── components/
│   │   └── Visor3D.js      # Visor de nubes de puntos
│   └── index.js            # Punto de entrada
├── package.json            # Dependencias Node.js
└── .env                    # Variables de entorno
```

**Tecnologías Frontend:**
- **React 19**: Biblioteca de UI
- **Leaflet**: Mapas interactivos
- **Recharts**: Gráficos y visualizaciones
- **Tailwind CSS**: Estilos modernos
- **shadcn/ui**: Componentes de UI
- **Lucide Icons**: Iconografía

### Base de Datos (MongoDB)
**Colecciones:**
- `proyectos`: Información de proyectos de construcción
- `vuelos`: Registro de vuelos de drones
- `avances`: Seguimiento de hitos y avance

## 🚀 Instalación y Configuración

### Prerrequisitos
- Node.js 20+
- Python 3.11+
- MongoDB
- Yarn

### 1. Clonar el Repositorio
```bash
git clone <repository-url>
cd dronebuild-pro
```

### 2. Configurar Backend
```bash
cd backend

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cat > .env << EOF
MONGO_URL=mongodb://localhost:27017
DB_NAME=construction_db
CORS_ORIGINS=*
EOF

# Ejecutar servidor
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### 3. Configurar Frontend
```bash
cd frontend

# Instalar dependencias
yarn install

# Configurar variables de entorno
cat > .env << EOF
REACT_APP_BACKEND_URL=http://localhost:8001
EOF

# Ejecutar aplicación
yarn start
```

### 4. Acceder a la Aplicación
- Frontend: http://localhost:3000
- Backend API: http://localhost:8001
- API Docs: http://localhost:8001/docs

## 📊 Modelos de Datos

### Proyecto
```json
{
  "id": "uuid",
  "nombre": "Torre Corporativa Santa Fe",
  "ubicacion": "Santa Fe, Ciudad de México",
  "coordenadas": {
    "lat": 19.3586,
    "lng": -99.2628
  },
  "fecha_inicio": "2024-01-15",
  "fecha_fin_planeada": "2025-12-30",
  "avance_actual": 65.5,
  "descripcion": "Construcción de torre de oficinas"
}
```

### Vuelo
```json
{
  "id": "uuid",
  "proyecto_id": "uuid",
  "fecha_vuelo": "2024-02-10",
  "duracion_minutos": 45,
  "area_cubierta": 12500,
  "num_imagenes": 850,
  "volumetria": {
    "excavacion": 4200,
    "relleno": 1800,
    "materiales": 950
  },
  "archivo_nube_puntos": "filename.las",
  "estado": "completado"
}
```

## 🎨 Capturas de Pantalla

### Dashboard Principal
- KPIs en tiempo real
- Mapa interactivo con ubicaciones
- Lista de proyectos activos
- Visor 3D de nubes de puntos

### Vista de Proyectos
- Cards con información detallada
- Barras de progreso visual
- Acciones rápidas (ver, eliminar)

### Vista de Vuelos
- Tabla completa de todos los vuelos
- Filtros por proyecto
- Datos volumétricos por vuelo

### Gráficos de Volumetría
- Comparación de excavación, relleno y materiales
- Visualización por vuelo
- Datos históricos del proyecto

## 🔧 Tecnologías Utilizadas

### Backend
- **FastAPI**: Framework web moderno y rápido
- **Motor**: Driver asíncrono de MongoDB
- **Pydantic**: Validación de datos
- **Python-multipart**: Manejo de uploads

### Frontend
- **React 19**: Última versión con hooks
- **React Router**: Navegación SPA
- **Axios**: Cliente HTTP
- **Leaflet**: Mapas interactivos
- **Recharts**: Gráficos y visualizaciones
- **Tailwind CSS**: Framework de estilos
- **Lucide React**: Íconos modernos

### Base de Datos
- **MongoDB**: Base de datos NoSQL
- **Motor**: Driver asíncrono

## 📝 Características Futuras

### Visor 3D Avanzado
- [ ] Integración con **Three.js** para renderizado real
- [ ] Soporte para **Potree** (nubes de puntos masivas)
- [ ] Parser de archivos **LAS/LAZ** con **LAS.js**
- [ ] Mediciones directas en el modelo 3D
- [ ] Comparación de modelos (antes/después)

### Análisis Avanzado
- [ ] Detección automática de cambios volumétricos
- [ ] Generación de curvas de nivel
- [ ] Cálculo de áreas y perímetros
- [ ] Exportación de reportes PDF

### Colaboración
- [ ] Sistema de autenticación
- [ ] Roles y permisos (admin, supervisor, operador)
- [ ] Comentarios en proyectos
- [ ] Notificaciones en tiempo real

### Integraciones
- [ ] Integración con software CAD
- [ ] Exportación a AutoCAD/Revit
- [ ] API de drones (DJI, Parrot)
- [ ] Servicios de procesamiento en la nube

## 🐛 Solución de Problemas

### El backend no inicia
```bash
# Verificar que MongoDB esté corriendo
sudo systemctl status mongodb

# Verificar puertos disponibles
lsof -i :8001

# Ver logs del backend
tail -f /var/log/supervisor/backend.err.log
```

### El frontend no compila
```bash
# Limpiar caché
rm -rf node_modules package-lock.json
yarn cache clean
yarn install

# Verificar versión de Node
node --version  # Debe ser 20+
```

### Errores de CORS
Verificar que `CORS_ORIGINS` en `.env` del backend incluya el origen del frontend.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 👥 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📧 Contacto

Para preguntas o soporte, contacta a: [tu-email@ejemplo.com]

## 🙏 Agradecimientos

- **OpenStreetMap** por los datos de mapas
- **Leaflet** por la biblioteca de mapas
- **Recharts** por los componentes de gráficos
- **shadcn/ui** por los componentes de UI

---

**Desarrollado con ❤️ usando Emergent AI**
