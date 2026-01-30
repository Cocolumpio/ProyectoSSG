import { useState, useEffect, useCallback } from 'react';
import '@/App.css';
import axios from 'axios';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';
import { Building2, Plane, TrendingUp, Database, Upload, Plus, Map as MapIcon, Eye, Trash2, Pencil, Calendar, Layers, X, ChevronLeft, ChevronRight, Download, Image, FileArchive, FileText } from 'lucide-react';
import VisorPix4D from './components/VisorPix4D';

// Fix Leaflet default icon issue
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Component to recenter map
function MapRecenter({ center }) {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.setView([center.lat, center.lng], 13);
    }
  }, [center, map]);
  return null;
}

function App() {
  const [proyectos, setProyectos] = useState([]);
  const [vuelos, setVuelos] = useState([]);
  const [estadisticas, setEstadisticas] = useState(null);
  const [selectedProyecto, setSelectedProyecto] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState('dashboard'); // dashboard, proyectos, vuelos
  const [showNewProjectForm, setShowNewProjectForm] = useState(false);
  const [showNewFlightForm, setShowNewFlightForm] = useState(false);
  const [mapCenter, setMapCenter] = useState({ lat: 19.4326, lng: -99.1332 }); // Ciudad de México default
  const [globalSuccessMessage, setGlobalSuccessMessage] = useState(null);

  // Función para mostrar mensaje de éxito global
  const showSuccessMessage = (message) => {
    setGlobalSuccessMessage(message);
    setTimeout(() => setGlobalSuccessMessage(null), 5000);
  };

  // Fetch data
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [proyectosRes, vuelosRes, statsRes] = await Promise.all([
        axios.get(`${API}/proyectos`),
        axios.get(`${API}/vuelos`),
        axios.get(`${API}/estadisticas/resumen`)
      ]);
      setProyectos(proyectosRes.data);
      setVuelos(vuelosRes.data);
      setEstadisticas(statsRes.data);
      
      // Si hay proyectos
      if (proyectosRes.data.length > 0) {
        // Si ya hay un proyecto seleccionado, actualizarlo con los datos más recientes
        setSelectedProyecto(prev => {
          if (prev) {
            // Buscar el proyecto actualizado en los nuevos datos
            const updated = proyectosRes.data.find(p => p.id === prev.id);
            return updated || proyectosRes.data[0];
          }
          return proyectosRes.data[0];
        });
        if (!selectedProyecto) {
          setMapCenter(proyectosRes.data[0].coordenadas);
        }
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedProyecto]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleDeleteProyecto = async (id) => {
    if (window.confirm('¿Estás seguro de eliminar este proyecto?')) {
      try {
        await axios.delete(`${API}/proyectos/${id}`);
        await fetchData();
        if (selectedProyecto?.id === id) {
          setSelectedProyecto(null);
        }
      } catch (error) {
        console.error('Error eliminando proyecto:', error);
      }
    }
  };

  const handleDeleteVuelo = async (id) => {
    if (window.confirm('¿Estás seguro de eliminar este vuelo?')) {
      try {
        await axios.delete(`${API}/vuelos/${id}`);
        await fetchData();
      } catch (error) {
        console.error('Error eliminando vuelo:', error);
      }
    }
  };

  const handleProyectoClick = (proyecto) => {
    setSelectedProyecto(proyecto);
    setMapCenter(proyecto.coordenadas);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8F9FA] flex items-center justify-center">
        <div className="text-gray-900 text-2xl">Cargando...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F8F9FA]">
      {/* Mensaje de éxito global */}
      {globalSuccessMessage && (
        <div className="fixed top-4 right-4 z-[100] bg-green-500 text-white px-6 py-4 rounded-lg shadow-lg flex items-center space-x-3" data-testid="global-success-message">
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span className="font-medium">{globalSuccessMessage}</span>
          <button 
            onClick={() => setGlobalSuccessMessage(null)}
            className="ml-2 hover:bg-green-600 rounded p-1"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-3 sm:py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 sm:space-x-3">
              <div className="flex items-center">
                <img 
                  src="https://customer-assets.emergentagent.com/job_flight-reports-1/artifacts/arowdsbk_WhatsApp%20Image%202026-01-26%20at%201.14.37%20PM.jpeg" 
                  alt="DrON Topografía"
                  className="h-8 sm:h-12 w-auto"
                />
              </div>
              <div className="border-l border-gray-300 pl-2 sm:pl-3 hidden sm:block">
                <h1 className="text-lg sm:text-2xl font-bold text-gray-900">DrON Topografía</h1>
                <p className="text-xs sm:text-sm text-gray-600">Gestión de Construcción con Drones</p>
              </div>
            </div>
            <div className="flex items-center space-x-1 sm:space-x-4">
              <button
                onClick={() => setActiveView('dashboard')}
                className={`px-2 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-base rounded-lg transition-all ${
                  activeView === 'dashboard'
                    ? 'bg-[#994B49] text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
                data-testid="nav-dashboard-btn"
              >
                <span className="hidden sm:inline">Dashboard</span>
                <TrendingUp className="h-4 w-4 sm:hidden" />
              </button>
              <button
                onClick={() => setActiveView('proyectos')}
                className={`px-2 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-base rounded-lg transition-all ${
                  activeView === 'proyectos'
                    ? 'bg-[#994B49] text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
                data-testid="nav-proyectos-btn"
              >
                <span className="hidden sm:inline">Proyectos</span>
                <Building2 className="h-4 w-4 sm:hidden" />
              </button>
              <button
                onClick={() => setActiveView('vuelos')}
                className={`px-2 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-base rounded-lg transition-all ${
                  activeView === 'vuelos'
                    ? 'bg-[#994B49] text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
                data-testid="nav-vuelos-btn"
              >
                <span className="hidden sm:inline">Vuelos</span>
                <Plane className="h-4 w-4 sm:hidden" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-8">
        {activeView === 'dashboard' && (
          <DashboardView
            estadisticas={estadisticas}
            proyectos={proyectos}
            vuelos={vuelos}
            selectedProyecto={selectedProyecto}
            onProyectoClick={handleProyectoClick}
            mapCenter={mapCenter}
          />
        )}

        {activeView === 'proyectos' && (
          <ProyectosView
            proyectos={proyectos}
            onDelete={handleDeleteProyecto}
            onSelect={handleProyectoClick}
            onRefresh={fetchData}
            onShowSuccess={showSuccessMessage}
          />
        )}

        {activeView === 'vuelos' && (
          <VuelosView
            vuelos={vuelos}
            proyectos={proyectos}
            onDelete={handleDeleteVuelo}
            onRefresh={fetchData}
          />
        )}
      </main>
    </div>
  );
}

// Dashboard View Component
function DashboardView({ estadisticas, proyectos, vuelos, selectedProyecto, onProyectoClick, mapCenter }) {
  const vuelosDelProyecto = selectedProyecto
    ? vuelos.filter(v => v.proyecto_id === selectedProyecto.id)
    : [];

  const volumetriaData = vuelosDelProyecto.map((v, idx) => ({
    nombre: `Vuelo ${idx + 1}`,
    excavacion: v.volumetria.excavacion,
    relleno: v.volumetria.relleno,
    materiales: v.volumetria.materiales
  }));

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6">
        <KPICard
          icon={Building2}
          label="Total Proyectos"
          value={estadisticas?.total_proyectos || 0}
          color="brick"
          testId="kpi-proyectos"
        />
        <KPICard
          icon={Plane}
          label="Vuelos Realizados"
          value={estadisticas?.total_vuelos || 0}
          color="brick"
          testId="kpi-vuelos"
        />
        <KPICard
          icon={TrendingUp}
          label="Avance Promedio"
          value={`${estadisticas?.avance_promedio || 0}%`}
          color="brick"
          testId="kpi-avance"
        />
        <KPICard
          icon={Database}
          label="Vol. Excavación Total"
          value={`${Math.round(estadisticas?.volumetria_total?.excavacion || 0)} m³`}
          color="brick"
          testId="kpi-volumetria"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Mapa */}
        <div className="bg-white rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
          <div className="flex items-center space-x-2 mb-3 sm:mb-4">
            <MapIcon className="h-4 sm:h-5 w-4 sm:w-5 text-[#994B49]" />
            <h2 className="text-base sm:text-xl font-semibold text-gray-900">Ubicación de Proyectos</h2>
          </div>
          <div className="h-[250px] sm:h-[400px] rounded-lg overflow-hidden border border-gray-200" data-testid="map-container">
            <MapContainer
              center={[mapCenter.lat, mapCenter.lng]}
              zoom={11}
              style={{ height: '100%', width: '100%' }}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              />
              <MapRecenter center={mapCenter} />
              {proyectos.map((proyecto) => (
                <Marker
                  key={proyecto.id}
                  position={[proyecto.coordenadas.lat, proyecto.coordenadas.lng]}
                  eventHandlers={{
                    click: () => onProyectoClick(proyecto)
                  }}
                >
                  <Popup>
                    <div className="text-sm">
                      <strong>{proyecto.nombre}</strong>
                      <br />
                      Avance: {proyecto.avance_actual}%
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          </div>
        </div>

        {/* Lista de Proyectos */}
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Proyectos Activos</h2>
          <div className="space-y-3 max-h-[400px] overflow-y-auto" data-testid="proyectos-list">
            {proyectos.map((proyecto) => (
              <div
                key={proyecto.id}
                onClick={() => onProyectoClick(proyecto)}
                className={`p-3 sm:p-4 rounded-lg cursor-pointer transition-all ${
                  selectedProyecto?.id === proyecto.id
                    ? 'bg-[#994B49]/10 border-2 border-[#994B49]'
                    : 'bg-gray-50 border border-gray-200 hover:bg-gray-100'
                }`}
                data-testid={`proyecto-item-${proyecto.id}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 text-sm sm:text-base truncate">{proyecto.nombre}</h3>
                    <p className="text-xs sm:text-sm text-gray-600 truncate">{proyecto.ubicacion}</p>
                  </div>
                  <div className="text-right ml-2">
                    <div className="text-lg sm:text-2xl font-bold text-[#994B49]">
                      {proyecto.avance_actual}%
                    </div>
                    <div className="text-xs text-gray-600">Avance</div>
                  </div>
                </div>
                <div className="mt-2">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-[#994B49] h-2 rounded-full transition-all"
                      style={{ width: `${proyecto.avance_actual}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Visor 3D - Pix4D */}
      {selectedProyecto && (selectedProyecto.pix4d_url || vuelosDelProyecto.length > 0) && (
        <VisorPix4D 
          vuelo={vuelosDelProyecto[0]} 
          proyectoPix4dUrl={selectedProyecto.pix4d_url}
          onUpdateUrl={(url) => console.log('Nueva URL:', url)}
        />
      )}

      {/* Volumetría del Proyecto Seleccionado */}
      {selectedProyecto && volumetriaData.length > 0 && (
        <div className="bg-white rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
          <h2 className="text-base sm:text-xl font-semibold text-gray-900 mb-3 sm:mb-4">
            Volumetrías - {selectedProyecto.nombre}
          </h2>
          <div className="h-[200px] sm:h-[300px]" data-testid="volumetria-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={volumetriaData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="nombre" stroke="#6B7280" fontSize={12} />
                <YAxis stroke="#6B7280" fontSize={12} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#FFFFFF', border: '1px solid #E5E7EB' }}
                  labelStyle={{ color: '#111827' }}
                />
                <Legend />
                <Bar dataKey="excavacion" fill="#994B49" name="Excavación (m³)" />
                <Bar dataKey="relleno" fill="#10b981" name="Relleno (m³)" />
                <Bar dataKey="materiales" fill="#6B7280" name="Materiales (m³)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Vuelos Recientes */}
      {selectedProyecto && vuelosDelProyecto.length > 0 && (
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Vuelos Recientes - {selectedProyecto.nombre}
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left" data-testid="vuelos-table">
              <thead className="border-b border-gray-200">
                <tr className="text-gray-600">
                  <th className="pb-3 pr-4">Fecha</th>
                  <th className="pb-3 pr-4">Duración</th>
                  <th className="pb-3 pr-4">Área</th>
                  <th className="pb-3 pr-4">Imágenes</th>
                  <th className="pb-3">Estado</th>
                </tr>
              </thead>
              <tbody className="text-gray-900">
                {vuelosDelProyecto.map((vuelo) => (
                  <tr key={vuelo.id} className="border-b border-gray-100">
                    <td className="py-3 pr-4">{vuelo.fecha_vuelo}</td>
                    <td className="py-3 pr-4">{vuelo.duracion_minutos} min</td>
                    <td className="py-3 pr-4">{vuelo.area_cubierta.toLocaleString()} m²</td>
                    <td className="py-3 pr-4">{vuelo.num_imagenes}</td>
                    <td className="py-3">
                      <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-sm">
                        {vuelo.estado}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// Componente de formulario de proyecto reutilizable
function ProjectFormContent({ formData, setFormData, error, saving, isEdit, onSubmit, onClose }) {
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleCoordChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      coordenadas: { ...prev.coordenadas, [field]: parseFloat(value) || 0 }
    }));
  };

  const handleVolumetriaChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      volumetria: { ...prev.volumetria, [field]: parseFloat(value) || 0 }
    }));
  };

  return (
    <form onSubmit={onSubmit} className="p-6 space-y-4">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Nombre del Proyecto *
          </label>
          <input
            type="text"
            name="nombre"
            value={formData.nombre}
            onChange={handleInputChange}
            required
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            placeholder="Ej: Hotel Marriott"
            data-testid="project-name-input"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Ubicación *
          </label>
          <input
            type="text"
            name="ubicacion"
            value={formData.ubicacion}
            onChange={handleInputChange}
            required
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            placeholder="Ej: Guadalajara, Jalisco"
            data-testid="project-location-input"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Latitud *
          </label>
          <input
            type="number"
            step="any"
            value={formData.coordenadas.lat}
            onChange={(e) => handleCoordChange('lat', e.target.value)}
            required
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            placeholder="20.6597"
            data-testid="project-lat-input"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Longitud *
          </label>
          <input
            type="number"
            step="any"
            value={formData.coordenadas.lng}
            onChange={(e) => handleCoordChange('lng', e.target.value)}
            required
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            placeholder="-103.3496"
            data-testid="project-lng-input"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Fecha de Inicio *
          </label>
          <input
            type="date"
            name="fecha_inicio"
            value={formData.fecha_inicio}
            onChange={handleInputChange}
            required
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            data-testid="project-start-date-input"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Fecha de Fin Planeada *
          </label>
          <input
            type="date"
            name="fecha_fin_planeada"
            value={formData.fecha_fin_planeada}
            onChange={handleInputChange}
            required
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            data-testid="project-end-date-input"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Avance Actual (%)
        </label>
        <div className="relative">
          <input
            type="number"
            name="avance_actual"
            value={formData.avance_actual}
            onChange={handleInputChange}
            min="0"
            max="100"
            step="0.1"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            placeholder="0"
            data-testid="project-progress-input"
          />
          <div className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-500">
            %
          </div>
        </div>
        <div className="mt-2">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-[#994B49] h-2 rounded-full transition-all"
              style={{ width: `${formData.avance_actual}%` }}
            />
          </div>
        </div>
      </div>

      {/* URL de Pix4D */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          URL del Modelo 3D (Pix4D)
        </label>
        <input
          type="url"
          name="pix4d_url"
          value={formData.pix4d_url}
          onChange={handleInputChange}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
          placeholder="https://cloud.pix4d.com/embed/?projectId=..."
          data-testid="project-pix4d-input"
        />
        <p className="text-xs text-gray-500 mt-1">
          Pega la URL del iframe de Pix4D para visualizar el modelo 3D
        </p>
      </div>

      {/* Volumetrías */}
      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
        <h4 className="font-medium text-gray-900 mb-3">Volumetría del Proyecto (m³)</h4>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Excavación</label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={formData.volumetria.excavacion}
              onChange={(e) => handleVolumetriaChange('excavacion', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
              data-testid="project-vol-excavacion-input"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Relleno</label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={formData.volumetria.relleno}
              onChange={(e) => handleVolumetriaChange('relleno', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
              data-testid="project-vol-relleno-input"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Materiales</label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={formData.volumetria.materiales}
              onChange={(e) => handleVolumetriaChange('materiales', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
              data-testid="project-vol-materiales-input"
            />
          </div>
        </div>
      </div>

      {/* Configuración de Flotilla de Camiones */}
      <div className="bg-amber-50 rounded-lg p-4 border border-amber-200">
        <h4 className="font-medium text-gray-900 mb-3 flex items-center">
          <span className="mr-2">🚛</span>
          Configuración de Flotilla de Camiones
        </h4>
        <p className="text-xs text-gray-500 mb-3">
          Estos valores se usarán para calcular los costos de retiro de material en el reporte ejecutivo
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Capacidad por Camión</label>
            <div className="relative">
              <input
                type="number"
                step="0.1"
                min="1"
                value={formData.capacidad_camion}
                onChange={(e) => setFormData(prev => ({ ...prev, capacidad_camion: parseFloat(e.target.value) || 25 }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                data-testid="project-capacidad-camion-input"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">ton</span>
            </div>
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Costo por Viaje</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">$</span>
              <input
                type="number"
                step="100"
                min="0"
                value={formData.costo_viaje_camion}
                onChange={(e) => setFormData(prev => ({ ...prev, costo_viaje_camion: parseFloat(e.target.value) || 2500 }))}
                className="w-full pl-7 pr-14 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                data-testid="project-costo-viaje-input"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">MXN</span>
            </div>
          </div>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Descripción
        </label>
        <textarea
          name="descripcion"
          value={formData.descripcion}
          onChange={handleInputChange}
          rows={3}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
          placeholder="Descripción del proyecto..."
          data-testid="project-description-input"
        />
      </div>

      <div className="flex items-center justify-end space-x-3 pt-4">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          data-testid="project-cancel-btn"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={saving}
          className="px-6 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="project-submit-btn"
        >
          {saving ? 'Guardando...' : (isEdit ? 'Guardar Cambios' : 'Crear Proyecto')}
        </button>
      </div>
    </form>
  );
}

// Componente para visualizar avances semanales de un proyecto
function AvancesSemanalesModal({ proyecto, onClose, onShowSuccess }) {
  const [avances, setAvances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAvance, setSelectedAvance] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null); // Para vista previa ampliada
  const [formData, setFormData] = useState({
    semana: 1,
    fecha: '',
    pix4d_url: '',
    descripcion: '',
    porcentaje_avance: 0,
    volumen_excavacion: 0
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

  // Cargar avances semanales al montar el componente
  useEffect(() => {
    const loadAvances = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${API}/proyectos/${proyecto.id}/avances-semanales`);
        setAvances(response.data);
        if (response.data.length > 0) {
          setSelectedAvance(response.data[response.data.length - 1]); // Seleccionar el más reciente
        }
      } catch (err) {
        console.error('Error cargando avances:', err);
      } finally {
        setLoading(false);
      }
    };
    loadAvances();
  }, [proyecto.id, API]);

  // Función para recargar avances
  const fetchAvances = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/proyectos/${proyecto.id}/avances-semanales`);
      setAvances(response.data);
      if (response.data.length > 0 && !selectedAvance) {
        setSelectedAvance(response.data[response.data.length - 1]);
      }
    } catch (err) {
      console.error('Error cargando avances:', err);
    } finally {
      setLoading(false);
    }
  };

  // Agregar nuevo avance
  const handleAddAvance = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      await axios.post(`${API}/proyectos/${proyecto.id}/avances-semanales`, formData);
      setShowAddForm(false);
      setFormData({ semana: avances.length + 2, fecha: '', pix4d_url: '', descripcion: '', porcentaje_avance: 0, volumen_excavacion: 0 });
      fetchAvances();
      if (onShowSuccess) {
        onShowSuccess(`Avance de Semana ${formData.semana} agregado correctamente`);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al agregar el avance');
    } finally {
      setSaving(false);
    }
  };

  // Eliminar avance
  const handleDeleteAvance = async (avanceId) => {
    if (!window.confirm('¿Eliminar este avance semanal?')) return;
    
    try {
      await axios.delete(`${API}/proyectos/${proyecto.id}/avances-semanales/${avanceId}`);
      fetchAvances();
      if (selectedAvance?.id === avanceId) {
        setSelectedAvance(null);
      }
    } catch (err) {
      console.error('Error eliminando avance:', err);
    }
  };

  // Subir imagen
  const handleImageUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !selectedAvance) return;

    setUploadingImage(true);
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        
        await axios.post(
          `${API}/proyectos/${proyecto.id}/avances-semanales/${selectedAvance.id}/imagenes`,
          formData,
          { headers: { 'Content-Type': 'multipart/form-data' } }
        );
      }
      
      // Recargar avances para obtener las nuevas imágenes
      fetchAvances();
      if (onShowSuccess) {
        onShowSuccess(`${files.length} imagen(es) subida(s) correctamente`);
      }
    } catch (err) {
      console.error('Error subiendo imagen:', err);
    } finally {
      setUploadingImage(false);
      e.target.value = ''; // Limpiar input
    }
  };

  // Descargar imagen
  const handleDownloadImage = async (imageUrl, index) => {
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}${imageUrl}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${proyecto.nombre}_Semana${selectedAvance.semana}_Foto${index + 1}.jpg`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error descargando imagen:', err);
    }
  };

  // Eliminar imagen
  const handleDeleteImage = async (imageUrl) => {
    if (!window.confirm('¿Eliminar esta imagen?')) return;
    
    try {
      await axios.delete(
        `${API}/proyectos/${proyecto.id}/avances-semanales/${selectedAvance.id}/imagenes`,
        { params: { image_url: imageUrl } }
      );
      fetchAvances();
    } catch (err) {
      console.error('Error eliminando imagen:', err);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-2 sm:p-4">
      <div className="bg-white rounded-xl shadow-xl w-full sm:w-[95vw] md:w-[90vw] lg:w-[80vw] h-[95vh] sm:h-[90vh] md:h-[85vh] lg:h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-[#994B49] text-white px-3 sm:px-6 py-3 sm:py-4 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center space-x-2 sm:space-x-3">
            <Layers className="h-5 sm:h-6 w-5 sm:w-6" />
            <div>
              <h3 className="text-base sm:text-xl font-semibold">Avances Semanales</h3>
              <p className="text-white/80 text-xs sm:text-sm truncate max-w-[150px] sm:max-w-none">{proyecto.nombre}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white/80 hover:text-white p-1.5 sm:p-2 rounded-lg hover:bg-white/10"
            data-testid="close-avances-modal"
          >
            <X className="h-5 sm:h-6 w-5 sm:w-6" />
          </button>
        </div>

        <div className="flex flex-col sm:flex-row flex-1 overflow-hidden">
          {/* Panel izquierdo - Lista de semanas */}
          <div className="w-full sm:w-48 md:w-56 lg:w-64 bg-gray-50 border-b sm:border-b-0 sm:border-r border-gray-200 flex flex-col flex-shrink-0 max-h-[30vh] sm:max-h-none">
            <div className="p-2 sm:p-4 border-b border-gray-200">
              <button
                onClick={() => {
                  setFormData({ 
                    semana: avances.length + 1, 
                    fecha: new Date().toISOString().split('T')[0], 
                    pix4d_url: '', 
                    descripcion: '', 
                    porcentaje_avance: 0,
                    volumen_excavacion: 0
                  });
                  setShowAddForm(true);
                }}
                className="w-full flex items-center justify-center space-x-2 px-3 sm:px-4 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors text-sm sm:text-base"
                data-testid="add-avance-btn"
              >
                <Plus className="h-4 w-4" />
                <span>Nueva Semana</span>
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-2 space-y-2 flex sm:flex-col flex-row overflow-x-auto sm:overflow-x-hidden">
              {loading ? (
                <div className="text-center py-8 text-gray-500">Cargando...</div>
              ) : avances.length === 0 ? (
                <div className="text-center py-8 text-gray-500 text-sm">
                  No hay avances semanales registrados
                </div>
              ) : (
                avances.map((avance) => (
                  <div
                    key={avance.id}
                    onClick={() => setSelectedAvance(avance)}
                    className={`p-2 sm:p-3 rounded-lg cursor-pointer transition-all flex-shrink-0 min-w-[120px] sm:min-w-0 ${
                      selectedAvance?.id === avance.id
                        ? 'bg-[#994B49] text-white'
                        : 'bg-white hover:bg-gray-100 text-gray-700'
                    }`}
                    data-testid={`avance-semana-${avance.semana}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-1 sm:space-x-2">
                        <Calendar className="h-3 sm:h-4 w-3 sm:w-4" />
                        <span className="font-medium text-xs sm:text-base">Sem. {avance.semana}</span>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteAvance(avance.id);
                        }}
                        className={`p-1 rounded hover:bg-red-100 hidden sm:block ${
                          selectedAvance?.id === avance.id ? 'hover:bg-white/20' : ''
                        }`}
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                    <div className={`text-xs mt-1 ${selectedAvance?.id === avance.id ? 'text-white/70' : 'text-gray-500'}`}>
                      {avance.fecha}
                    </div>
                    {avance.porcentaje_avance > 0 && (
                      <div className="mt-1 sm:mt-2">
                        <div className={`text-xs mb-1 ${selectedAvance?.id === avance.id ? 'text-white/70' : 'text-gray-500'}`}>
                          {avance.porcentaje_avance}%
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-1 sm:h-1.5">
                          <div
                            className={`h-1 sm:h-1.5 rounded-full ${selectedAvance?.id === avance.id ? 'bg-white' : 'bg-[#994B49]'}`}
                            style={{ width: `${avance.porcentaje_avance}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Panel derecho - Visor 3D e Imágenes */}
          <div className="flex-1 flex flex-col bg-gray-100 overflow-hidden">
            {selectedAvance ? (
              <div className="flex-1 flex flex-col overflow-y-auto">
                {/* Header del avance */}
                <div className="p-3 sm:p-4 bg-white border-b border-gray-200 flex-shrink-0">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-semibold text-gray-900 text-sm sm:text-base">Semana {selectedAvance.semana}</h4>
                      <p className="text-xs sm:text-sm text-gray-500">{selectedAvance.fecha}</p>
                    </div>
                    {selectedAvance.porcentaje_avance > 0 && (
                      <div className="text-right">
                        <span className="text-xl sm:text-2xl font-bold text-[#994B49]">{selectedAvance.porcentaje_avance}%</span>
                        <p className="text-xs text-gray-500">Avance</p>
                      </div>
                    )}
                  </div>
                  {selectedAvance.descripcion && (
                    <p className="mt-2 text-xs sm:text-sm text-gray-600">{selectedAvance.descripcion}</p>
                  )}
                </div>

                {/* Gráfico de Volumen de Excavación por Semana */}
                {avances.length > 0 && avances.some(a => a.volumen_excavacion > 0) && (
                  <div className="p-2 sm:p-4 flex-shrink-0">
                    <div className="bg-white rounded-xl p-3 sm:p-4 shadow-sm">
                      <div className="flex items-center space-x-2 mb-3">
                        <Database className="h-4 sm:h-5 w-4 sm:w-5 text-[#994B49]" />
                        <h5 className="font-semibold text-gray-900 text-sm sm:text-base">Volumen Excavado por Semana</h5>
                      </div>
                      <div className="h-[150px] sm:h-[180px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={avances.filter(a => a.volumen_excavacion > 0).map(a => ({
                            semana: `Sem ${a.semana}`,
                            volumen: a.volumen_excavacion
                          }))}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                            <XAxis dataKey="semana" stroke="#6B7280" fontSize={11} />
                            <YAxis stroke="#6B7280" fontSize={11} tickFormatter={(v) => `${v} t`} />
                            <Tooltip 
                              formatter={(value) => [`${value.toLocaleString()} m³`, 'Volumen Excavado']}
                              contentStyle={{ backgroundColor: '#FFF', border: '1px solid #E5E7EB', borderRadius: '8px' }}
                            />
                            <Bar 
                              dataKey="volumen" 
                              fill="#994B49" 
                              radius={[4, 4, 0, 0]}
                              name="Volumen (m³)"
                            />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>
                )}

                {/* Visor 3D */}
                <div className="p-2 sm:p-4 flex-shrink-0">
                  <div className="bg-white rounded-xl overflow-hidden shadow-sm h-[200px] sm:h-[280px] md:h-[350px]">
                    <iframe
                      src={selectedAvance.pix4d_url}
                      className="w-full h-full border-0"
                      title={`Modelo 3D - Semana ${selectedAvance.semana}`}
                      allowFullScreen
                    />
                  </div>
                </div>

                {/* Galería de Imágenes */}
                <div className="p-2 sm:p-4 flex-1">
                  <div className="bg-white rounded-xl p-3 sm:p-4 shadow-sm h-full">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3 sm:mb-4">
                      <div className="flex items-center space-x-2">
                        <Image className="h-4 sm:h-5 w-4 sm:w-5 text-[#994B49]" />
                        <h5 className="font-semibold text-gray-900 text-sm sm:text-base">Fotos del Vuelo</h5>
                        {selectedAvance.imagenes && selectedAvance.imagenes.length > 0 && (
                          <span className="text-xs sm:text-sm text-gray-500">({selectedAvance.imagenes.length})</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {/* Botón Descargar ZIP */}
                        {selectedAvance.imagenes && selectedAvance.imagenes.length > 0 && (
                          <button
                            onClick={() => {
                              window.open(`${process.env.REACT_APP_BACKEND_URL}/api/proyectos/${proyecto.id}/avances-semanales/${selectedAvance.id}/imagenes/zip`, '_blank');
                            }}
                            className="flex items-center justify-center space-x-2 px-3 py-1.5 sm:py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                            title="Descargar todas las fotos en ZIP"
                            data-testid="download-zip-btn"
                          >
                            <FileArchive className="h-4 w-4" />
                            <span className="text-xs sm:text-sm hidden sm:inline">Descargar ZIP</span>
                          </button>
                        )}
                        <label className="flex items-center justify-center space-x-2 px-3 py-1.5 sm:py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] cursor-pointer transition-colors">
                          <Upload className="h-4 w-4" />
                          <span className="text-xs sm:text-sm">{uploadingImage ? 'Subiendo...' : 'Subir Fotos'}</span>
                          <input
                            type="file"
                            multiple
                            accept="image/*"
                            onChange={handleImageUpload}
                            disabled={uploadingImage}
                            className="hidden"
                            data-testid="upload-images-input"
                          />
                        </label>
                      </div>
                    </div>

                    {selectedAvance.imagenes && selectedAvance.imagenes.length > 0 ? (
                      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-2 sm:gap-3 max-h-[150px] sm:max-h-[200px] overflow-y-auto">
                        {selectedAvance.imagenes.map((imageUrl, index) => (
                          <div
                            key={index}
                            className="relative group aspect-square bg-gray-100 rounded-lg overflow-hidden cursor-pointer"
                            onClick={() => setSelectedImage({ url: imageUrl, index })}
                          >
                            <img
                              src={`${process.env.REACT_APP_BACKEND_URL}${imageUrl}`}
                              alt={`Foto ${index + 1}`}
                              className="w-full h-full object-cover"
                            />
                            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDownloadImage(imageUrl, index);
                                }}
                                className="p-2 bg-white rounded-full text-[#994B49] hover:bg-gray-100 mx-1"
                                title="Descargar"
                              >
                                <Download className="h-4 w-4" />
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDeleteImage(imageUrl);
                                }}
                                className="p-2 bg-white rounded-full text-red-600 hover:bg-gray-100 mx-1"
                                title="Eliminar"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                            <div className="absolute bottom-1 left-1 bg-black/50 text-white text-xs px-2 py-0.5 rounded">
                              {index + 1}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center py-8 text-gray-400">
                        <Image className="h-12 w-12 mb-2" />
                        <p className="text-sm">No hay fotos para esta semana</p>
                        <p className="text-xs mt-1">Sube fotos del vuelo para que el cliente pueda descargarlas</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <Layers className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                  <p className="text-lg">Selecciona una semana para ver el modelo 3D</p>
                  <p className="text-sm mt-2">o agrega un nuevo avance semanal</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Modal de vista previa de imagen */}
        {selectedImage && (
          <div 
            className="absolute inset-0 bg-black/90 flex items-center justify-center z-20"
            onClick={() => setSelectedImage(null)}
          >
            <button
              onClick={() => setSelectedImage(null)}
              className="absolute top-4 right-4 text-white/80 hover:text-white p-2"
            >
              <X className="h-8 w-8" />
            </button>
            <div className="max-w-4xl max-h-[80vh] p-4">
              <img
                src={`${process.env.REACT_APP_BACKEND_URL}${selectedImage.url}`}
                alt={`Foto ${selectedImage.index + 1}`}
                className="max-w-full max-h-[70vh] object-contain rounded-lg"
              />
              <div className="flex items-center justify-center mt-4 space-x-4">
                <span className="text-white">Foto {selectedImage.index + 1}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDownloadImage(selectedImage.url, selectedImage.index);
                  }}
                  className="flex items-center space-x-2 px-4 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A]"
                >
                  <Download className="h-4 w-4" />
                  <span>Descargar</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Modal para agregar avance */}
        {showAddForm && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-10">
            <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4">
              <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <h4 className="text-lg font-semibold text-gray-900">Nuevo Avance Semanal</h4>
                <button onClick={() => setShowAddForm(false)} className="text-gray-400 hover:text-gray-600">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <form onSubmit={handleAddAvance} className="p-6 space-y-4">
                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                    {error}
                  </div>
                )}
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Semana *</label>
                    <input
                      type="number"
                      min="1"
                      value={formData.semana}
                      onChange={(e) => setFormData(prev => ({ ...prev, semana: parseInt(e.target.value) || 1 }))}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                      data-testid="avance-semana-input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Fecha *</label>
                    <input
                      type="date"
                      value={formData.fecha}
                      onChange={(e) => setFormData(prev => ({ ...prev, fecha: e.target.value }))}
                      required
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                      data-testid="avance-fecha-input"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">URL del Modelo 3D (Pix4D) *</label>
                  <input
                    type="url"
                    value={formData.pix4d_url}
                    onChange={(e) => setFormData(prev => ({ ...prev, pix4d_url: e.target.value }))}
                    required
                    placeholder="https://cloud.pix4d.com/embed/..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                    data-testid="avance-pix4d-input"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Porcentaje de Avance</label>
                    <div className="relative">
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="0.1"
                        value={formData.porcentaje_avance}
                        onChange={(e) => setFormData(prev => ({ ...prev, porcentaje_avance: parseFloat(e.target.value) || 0 }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                        data-testid="avance-porcentaje-input"
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">%</span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Volumen Excavado</label>
                    <div className="relative">
                      <input
                        type="number"
                        min="0"
                        step="0.1"
                        value={formData.volumen_excavacion}
                        onChange={(e) => setFormData(prev => ({ ...prev, volumen_excavacion: parseFloat(e.target.value) || 0 }))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                        data-testid="avance-volumen-input"
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">ton</span>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Descripción</label>
                  <textarea
                    value={formData.descripcion}
                    onChange={(e) => setFormData(prev => ({ ...prev, descripcion: e.target.value }))}
                    rows={2}
                    placeholder="Notas sobre el avance de esta semana..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                    data-testid="avance-descripcion-input"
                  />
                </div>

                <div className="flex justify-end space-x-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAddForm(false)}
                    className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="px-4 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors disabled:opacity-50"
                    data-testid="avance-submit-btn"
                  >
                    {saving ? 'Guardando...' : 'Agregar Avance'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Proyectos View
function ProyectosView({ proyectos, onDelete, onSelect, onRefresh, onShowSuccess }) {
  const [showForm, setShowForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [showAvancesModal, setShowAvancesModal] = useState(false);
  const [selectedProjectForAvances, setSelectedProjectForAvances] = useState(null);
  const [formData, setFormData] = useState({
    nombre: '',
    ubicacion: '',
    coordenadas: { lat: 20.6597, lng: -103.3496 },
    fecha_inicio: '',
    fecha_fin_planeada: '',
    descripcion: '',
    avance_actual: 0,
    pix4d_url: '',
    volumetria: { excavacion: 0, relleno: 0, materiales: 0 },
    capacidad_camion: 25,
    costo_viaje_camion: 2500
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const resetForm = () => {
    setFormData({
      nombre: '',
      ubicacion: '',
      coordenadas: { lat: 20.6597, lng: -103.3496 },
      fecha_inicio: '',
      fecha_fin_planeada: '',
      descripcion: '',
      avance_actual: 0,
      pix4d_url: '',
      volumetria: { excavacion: 0, relleno: 0, materiales: 0 },
      capacidad_camion: 25,
      costo_viaje_camion: 2500
    });
  };

  const handleEditClick = (proyecto) => {
    console.log('handleEditClick - proyecto recibido:', proyecto);
    console.log('handleEditClick - pix4d_url:', proyecto.pix4d_url);
    setEditingProject(proyecto);
    setFormData({
      nombre: proyecto.nombre || '',
      ubicacion: proyecto.ubicacion || '',
      coordenadas: proyecto.coordenadas || { lat: 20.6597, lng: -103.3496 },
      fecha_inicio: proyecto.fecha_inicio || '',
      fecha_fin_planeada: proyecto.fecha_fin_planeada || '',
      descripcion: proyecto.descripcion || '',
      avance_actual: proyecto.avance_actual || 0,
      pix4d_url: proyecto.pix4d_url || '',
      volumetria: proyecto.volumetria || { excavacion: 0, relleno: 0, materiales: 0 },
      capacidad_camion: proyecto.capacidad_camion || 25,
      costo_viaje_camion: proyecto.costo_viaje_camion || 2500
    });
    setShowEditForm(true);
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
      await axios.post(`${API}/proyectos`, formData);
      resetForm();
      setShowForm(false);
      onRefresh();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al crear el proyecto');
    } finally {
      setSaving(false);
    }
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    const projectName = formData.nombre;
    
    // Log detallado para debug
    console.log('=== GUARDANDO PROYECTO ===');
    console.log('editingProject.id:', editingProject?.id);
    console.log('formData.pix4d_url:', formData.pix4d_url);
    console.log('formData completo:', JSON.stringify(formData));

    try {
      const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
      const response = await axios.put(`${API}/proyectos/${editingProject.id}`, formData);
      
      console.log('=== RESPUESTA DEL SERVIDOR ===');
      console.log('response.data:', JSON.stringify(response.data));
      console.log('response.data.pix4d_url:', response.data.pix4d_url);
      
      setShowEditForm(false);
      setEditingProject(null);
      resetForm();
      
      // Mostrar mensaje de éxito global
      if (onShowSuccess) {
        onShowSuccess(`¡Proyecto "${projectName}" actualizado correctamente!`);
      }
      
      await onRefresh();
    } catch (err) {
      console.error('=== ERROR AL GUARDAR ===');
      console.error('Error:', err);
      console.error('Error response:', err.response?.data);
      setError(err.response?.data?.detail || 'Error al actualizar el proyecto');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h2 className="text-xl sm:text-2xl font-bold text-gray-900">Proyectos</h2>
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          className="flex items-center justify-center space-x-2 px-4 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors"
          data-testid="add-proyecto-btn"
        >
          <Plus className="h-5 w-5" />
          <span>Nuevo Proyecto</span>
        </button>
      </div>

      {/* Modal: Nuevo Proyecto */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-2 sm:p-4">
          <div className="bg-white rounded-xl shadow-xl w-full sm:max-w-2xl max-h-[95vh] sm:max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
              <h3 className="text-lg sm:text-xl font-semibold text-gray-900">Nuevo Proyecto</h3>
              <button
                onClick={() => setShowForm(false)}
                className="text-gray-400 hover:text-gray-600"
                data-testid="close-new-project-modal"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <ProjectFormContent 
              formData={formData}
              setFormData={setFormData}
              error={error}
              saving={saving}
              onSubmit={handleSubmit} 
              onClose={() => setShowForm(false)} 
            />
          </div>
        </div>
      )}

      {/* Modal: Editar Proyecto */}
      {showEditForm && editingProject && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <h3 className="text-xl font-semibold text-gray-900">Editar Proyecto: {editingProject.nombre}</h3>
              <button
                onClick={() => { setShowEditForm(false); setEditingProject(null); }}
                className="text-gray-400 hover:text-gray-600"
                data-testid="close-edit-project-modal"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <ProjectFormContent 
              formData={formData}
              setFormData={setFormData}
              error={error}
              saving={saving}
              isEdit 
              onSubmit={handleEditSubmit} 
              onClose={() => { setShowEditForm(false); setEditingProject(null); }} 
            />
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
        {proyectos.map((proyecto) => (
          <div
            key={proyecto.id}
            className="bg-white rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm hover:border-[#994B49] transition-all"
            data-testid={`proyecto-card-${proyecto.id}`}
          >
            <div className="flex items-start justify-between mb-3 sm:mb-4">
              <Building2 className="h-6 sm:h-8 w-6 sm:w-8 text-[#994B49]" />
              <div className="flex space-x-0.5 sm:space-x-1">
                <button
                  onClick={() => onSelect(proyecto)}
                  className="p-1.5 sm:p-2 text-[#994B49] hover:bg-[#994B49]/10 rounded-lg transition-colors"
                  title="Ver en Dashboard"
                  data-testid={`view-proyecto-${proyecto.id}`}
                >
                  <Eye className="h-4 w-4" />
                </button>
                <button
                  onClick={() => {
                    setSelectedProjectForAvances(proyecto);
                    setShowAvancesModal(true);
                  }}
                  className="p-1.5 sm:p-2 text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                  title="Ver Avances Semanales"
                  data-testid={`avances-proyecto-${proyecto.id}`}
                >
                  <Layers className="h-4 w-4" />
                </button>
                <button
                  onClick={() => {
                    window.open(`${process.env.REACT_APP_BACKEND_URL}/api/proyectos/${proyecto.id}/reporte-ejecutivo`, '_blank');
                  }}
                  className="p-1.5 sm:p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                  title="Descargar Reporte Ejecutivo PDF"
                  data-testid={`reporte-proyecto-${proyecto.id}`}
                >
                  <FileText className="h-4 w-4" />
                </button>
                <button
                  onClick={() => handleEditClick(proyecto)}
                  className="p-1.5 sm:p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  title="Editar Proyecto"
                  data-testid={`edit-proyecto-${proyecto.id}`}
                >
                  <Pencil className="h-4 w-4" />
                </button>
                <button
                  onClick={() => onDelete(proyecto.id)}
                  className="p-1.5 sm:p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  title="Eliminar Proyecto"
                  data-testid={`delete-proyecto-${proyecto.id}`}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">{proyecto.nombre}</h3>
            <p className="text-gray-600 text-sm mb-4">{proyecto.ubicacion}</p>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between text-gray-700">
                <span>Inicio:</span>
                <span>{proyecto.fecha_inicio}</span>
              </div>
              <div className="flex justify-between text-gray-700">
                <span>Fin Planeado:</span>
                <span>{proyecto.fecha_fin_planeada}</span>
              </div>
              {proyecto.pix4d_url && (
                <div className="flex items-center text-green-600 text-xs mt-2">
                  <Eye className="h-3 w-3 mr-1" />
                  Modelo 3D disponible
                </div>
              )}
              <div className="mt-4">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">Avance</span>
                  <span className="text-[#994B49] font-semibold">{proyecto.avance_actual}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-[#994B49] h-2 rounded-full transition-all"
                    style={{ width: `${proyecto.avance_actual}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Modal de Avances Semanales */}
      {showAvancesModal && selectedProjectForAvances && (
        <AvancesSemanalesModal
          proyecto={selectedProjectForAvances}
          onClose={() => {
            setShowAvancesModal(false);
            setSelectedProjectForAvances(null);
          }}
          onShowSuccess={onShowSuccess}
        />
      )}
    </div>
  );
}

// Vuelos View
function VuelosView({ vuelos, proyectos, onDelete, onRefresh }) {
  const [filtroProyecto, setFiltroProyecto] = useState('todos');
  const [showForm, setShowForm] = useState(false);
  const [editingVuelo, setEditingVuelo] = useState(null);
  const [formData, setFormData] = useState({
    proyecto_id: '',
    fecha_vuelo: '',
    duracion_minutos: 30,
    area_cubierta: 1000,
    num_imagenes: 100,
    volumetria: { excavacion: 0, relleno: 0, materiales: 0 },
    pix4d_url: '',
    notas: '',
    estado: 'completado'
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

  const vuelosFiltrados = filtroProyecto === 'todos'
    ? vuelos
    : vuelos.filter(v => v.proyecto_id === filtroProyecto);

  const getProyectoNombre = (proyectoId) => {
    const proyecto = proyectos.find(p => p.id === proyectoId);
    return proyecto?.nombre || 'Proyecto desconocido';
  };

  const resetForm = () => {
    setFormData({
      proyecto_id: proyectos.length > 0 ? proyectos[0].id : '',
      fecha_vuelo: new Date().toISOString().split('T')[0],
      duracion_minutos: 30,
      area_cubierta: 1000,
      num_imagenes: 100,
      volumetria: { excavacion: 0, relleno: 0, materiales: 0 },
      pix4d_url: '',
      notas: '',
      estado: 'completado'
    });
  };

  const handleEditClick = (vuelo) => {
    setEditingVuelo(vuelo);
    setFormData({
      proyecto_id: vuelo.proyecto_id || '',
      fecha_vuelo: vuelo.fecha_vuelo || '',
      duracion_minutos: vuelo.duracion_minutos || 30,
      area_cubierta: vuelo.area_cubierta || 1000,
      num_imagenes: vuelo.num_imagenes || 100,
      volumetria: vuelo.volumetria || { excavacion: 0, relleno: 0, materiales: 0 },
      pix4d_url: vuelo.pix4d_url || '',
      notas: vuelo.notas || '',
      estado: vuelo.estado || 'completado'
    });
    setShowForm(true);
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      if (editingVuelo) {
        await axios.put(`${API}/vuelos/${editingVuelo.id}`, formData);
      } else {
        await axios.post(`${API}/vuelos`, formData);
      }
      resetForm();
      setShowForm(false);
      setEditingVuelo(null);
      onRefresh();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al guardar el vuelo');
    } finally {
      setSaving(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleVolumetriaChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      volumetria: { ...prev.volumetria, [field]: parseFloat(value) || 0 }
    }));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h2 className="text-xl sm:text-2xl font-bold text-gray-900">Vuelos de Drones</h2>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-4">
          <select
            value={filtroProyecto}
            onChange={(e) => setFiltroProyecto(e.target.value)}
            className="px-4 py-2 bg-white text-gray-900 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            data-testid="filter-proyecto-select"
          >
            <option value="todos">Todos los proyectos</option>
            {proyectos.map((p) => (
              <option key={p.id} value={p.id}>{p.nombre}</option>
            ))}
          </select>
          <button
            onClick={() => { resetForm(); setEditingVuelo(null); setShowForm(true); }}
            className="flex items-center justify-center space-x-2 px-4 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors"
            data-testid="add-vuelo-btn"
          >
            <Plus className="h-5 w-5" />
            <span>Nuevo Vuelo</span>
          </button>
        </div>
      </div>

      {/* Modal: Formulario de Vuelo */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-2 sm:p-4">
          <div className="bg-white rounded-xl shadow-xl w-full sm:max-w-2xl max-h-[95vh] sm:max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
              <h3 className="text-lg sm:text-xl font-semibold text-gray-900">
                {editingVuelo ? 'Editar Vuelo' : 'Nuevo Vuelo'}
              </h3>
              <button
                onClick={() => { setShowForm(false); setEditingVuelo(null); }}
                className="text-gray-400 hover:text-gray-600"
                data-testid="close-vuelo-modal"
              >
                <X className="h-6 w-6" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-4 sm:p-6 space-y-4">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                  {error}
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Proyecto *</label>
                  <select
                    name="proyecto_id"
                    value={formData.proyecto_id}
                    onChange={handleInputChange}
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                    data-testid="vuelo-proyecto-select"
                  >
                    <option value="">Seleccionar proyecto</option>
                    {proyectos.map((p) => (
                      <option key={p.id} value={p.id}>{p.nombre}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Fecha del Vuelo *</label>
                  <input
                    type="date"
                    name="fecha_vuelo"
                    value={formData.fecha_vuelo}
                    onChange={handleInputChange}
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                    data-testid="vuelo-fecha-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Duración (min) *</label>
                  <input
                    type="number"
                    name="duracion_minutos"
                    value={formData.duracion_minutos}
                    onChange={handleInputChange}
                    min="1"
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                    data-testid="vuelo-duracion-input"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Área (m²) *</label>
                  <input
                    type="number"
                    name="area_cubierta"
                    value={formData.area_cubierta}
                    onChange={handleInputChange}
                    min="0"
                    step="0.1"
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                    data-testid="vuelo-area-input"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nº Imágenes *</label>
                  <input
                    type="number"
                    name="num_imagenes"
                    value={formData.num_imagenes}
                    onChange={handleInputChange}
                    min="0"
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                    data-testid="vuelo-imagenes-input"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
                <select
                  name="estado"
                  value={formData.estado}
                  onChange={handleInputChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                  data-testid="vuelo-estado-select"
                >
                  <option value="completado">Completado</option>
                  <option value="procesando">Procesando</option>
                  <option value="fallido">Fallido</option>
                </select>
              </div>

              {/* Volumetrías */}
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <h4 className="font-medium text-gray-900 mb-3">Volumetría del Vuelo (m³)</h4>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Excavación</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={formData.volumetria.excavacion}
                      onChange={(e) => handleVolumetriaChange('excavacion', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                      data-testid="vuelo-vol-excavacion-input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Relleno</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={formData.volumetria.relleno}
                      onChange={(e) => handleVolumetriaChange('relleno', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                      data-testid="vuelo-vol-relleno-input"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Materiales</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={formData.volumetria.materiales}
                      onChange={(e) => handleVolumetriaChange('materiales', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                      data-testid="vuelo-vol-materiales-input"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">URL Modelo 3D (Pix4D)</label>
                <input
                  type="url"
                  name="pix4d_url"
                  value={formData.pix4d_url}
                  onChange={handleInputChange}
                  placeholder="https://cloud.pix4d.com/embed/..."
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                  data-testid="vuelo-pix4d-input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notas</label>
                <textarea
                  name="notas"
                  value={formData.notas}
                  onChange={handleInputChange}
                  rows={2}
                  placeholder="Observaciones del vuelo..."
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                  data-testid="vuelo-notas-input"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => { setShowForm(false); setEditingVuelo(null); }}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-6 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors disabled:opacity-50"
                  data-testid="vuelo-submit-btn"
                >
                  {saving ? 'Guardando...' : (editingVuelo ? 'Guardar Cambios' : 'Crear Vuelo')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full" data-testid="vuelos-full-table">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr className="text-gray-700 text-sm">
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6">Proyecto</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6">Fecha</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6 hidden sm:table-cell">Duración</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6 hidden md:table-cell">Área</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6 hidden md:table-cell">Imágenes</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6 hidden lg:table-cell">Excavación</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6">Estado</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6">Acciones</th>
              </tr>
            </thead>
            <tbody className="text-gray-900 text-sm">
              {vuelosFiltrados.map((vuelo) => (
                <tr key={vuelo.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4 sm:py-4 sm:px-6">
                    <div className="font-medium truncate max-w-[120px] sm:max-w-none">{getProyectoNombre(vuelo.proyecto_id)}</div>
                  </td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6">{vuelo.fecha_vuelo}</td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6 hidden sm:table-cell">{vuelo.duracion_minutos} min</td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6 hidden md:table-cell">{vuelo.area_cubierta.toLocaleString()} m²</td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6 hidden md:table-cell">{vuelo.num_imagenes}</td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6 hidden lg:table-cell">{vuelo.volumetria.excavacion.toLocaleString()} m³</td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6">
                    <span className={`px-2 py-1 rounded text-xs ${
                      vuelo.estado === 'completado' ? 'bg-green-100 text-green-700' :
                      vuelo.estado === 'procesando' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {vuelo.estado}
                    </span>
                  </td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6">
                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => handleEditClick(vuelo)}
                        className="p-1.5 sm:p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Editar"
                        data-testid={`edit-vuelo-${vuelo.id}`}
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => onDelete(vuelo.id)}
                        className="p-1.5 sm:p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Eliminar"
                        data-testid={`delete-vuelo-${vuelo.id}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {vuelosFiltrados.length === 0 && (
        <div className="text-center py-12 text-gray-600">
          <Plane className="h-12 w-12 mx-auto mb-4 text-gray-300" />
          <p>No hay vuelos registrados para este proyecto.</p>
          <button
            onClick={() => { resetForm(); setShowForm(true); }}
            className="mt-4 text-[#994B49] hover:underline"
          >
            Agregar primer vuelo
          </button>
        </div>
      )}
    </div>
  );
}

// KPI Card Component
function KPICard({ icon: Icon, label, value, color, testId }) {
  const colorClasses = {
    brick: 'bg-[#994B49]/10 text-[#994B49]'
  };

  return (
    <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm" data-testid={testId}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-gray-600 text-sm mb-1">{label}</p>
          <p className="text-3xl font-bold text-gray-900">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  );
}

export default App;