import { useState, useEffect } from 'react';
import '@/App.css';
import axios from 'axios';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';
import { Building2, Plane, TrendingUp, Database, Upload, Plus, Map as MapIcon, Eye, Trash2 } from 'lucide-react';
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

  // Fetch data
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
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
      
      // Si hay proyectos, seleccionar el primero
      if (proyectosRes.data.length > 0 && !selectedProyecto) {
        setSelectedProyecto(proyectosRes.data[0]);
        setMapCenter(proyectosRes.data[0].coordenadas);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

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
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-[#994B49] p-2 rounded-lg">
                <Plane className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">DroneBuild Pro</h1>
                <p className="text-sm text-gray-600">Gestión de Construcción con Drones</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setActiveView('dashboard')}
                className={`px-4 py-2 rounded-lg transition-all ${
                  activeView === 'dashboard'
                    ? 'bg-[#994B49] text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
                data-testid="nav-dashboard-btn"
              >
                Dashboard
              </button>
              <button
                onClick={() => setActiveView('proyectos')}
                className={`px-4 py-2 rounded-lg transition-all ${
                  activeView === 'proyectos'
                    ? 'bg-[#994B49] text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
                data-testid="nav-proyectos-btn"
              >
                Proyectos
              </button>
              <button
                onClick={() => setActiveView('vuelos')}
                className={`px-4 py-2 rounded-lg transition-all ${
                  activeView === 'vuelos'
                    ? 'bg-[#994B49] text-white'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
                data-testid="nav-vuelos-btn"
              >
                Vuelos
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          icon={Building2}
          label="Total Proyectos"
          value={estadisticas?.total_proyectos || 0}
          color="blue"
          testId="kpi-proyectos"
        />
        <KPICard
          icon={Plane}
          label="Vuelos Realizados"
          value={estadisticas?.total_vuelos || 0}
          color="green"
          testId="kpi-vuelos"
        />
        <KPICard
          icon={TrendingUp}
          label="Avance Promedio"
          value={`${estadisticas?.avance_promedio || 0}%`}
          color="purple"
          testId="kpi-avance"
        />
        <KPICard
          icon={Database}
          label="Vol. Excavación Total"
          value={`${Math.round(estadisticas?.volumetria_total?.excavacion || 0)} m³`}
          color="orange"
          testId="kpi-volumetria"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Mapa */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
          <div className="flex items-center space-x-2 mb-4">
            <MapIcon className="h-5 w-5 text-blue-400" />
            <h2 className="text-xl font-semibold text-white">Ubicación de Proyectos</h2>
          </div>
          <div className="h-[400px] rounded-lg overflow-hidden" data-testid="map-container">
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
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
          <h2 className="text-xl font-semibold text-white mb-4">Proyectos Activos</h2>
          <div className="space-y-3 max-h-[400px] overflow-y-auto" data-testid="proyectos-list">
            {proyectos.map((proyecto) => (
              <div
                key={proyecto.id}
                onClick={() => onProyectoClick(proyecto)}
                className={`p-4 rounded-lg cursor-pointer transition-all ${
                  selectedProyecto?.id === proyecto.id
                    ? 'bg-blue-500/20 border-2 border-blue-500'
                    : 'bg-slate-700/50 border border-slate-600 hover:bg-slate-700'
                }`}
                data-testid={`proyecto-item-${proyecto.id}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h3 className="font-semibold text-white">{proyecto.nombre}</h3>
                    <p className="text-sm text-slate-400">{proyecto.ubicacion}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-blue-400">
                      {proyecto.avance_actual}%
                    </div>
                    <div className="text-xs text-slate-400">Avance</div>
                  </div>
                </div>
                <div className="mt-2">
                  <div className="w-full bg-slate-600 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all"
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
      {selectedProyecto && vuelosDelProyecto.length > 0 && (
        <VisorPix4D 
          vuelo={vuelosDelProyecto[0]} 
          onUpdateUrl={(url) => console.log('Nueva URL:', url)}
        />
      )}

      {/* Volumetría del Proyecto Seleccionado */}
      {selectedProyecto && volumetriaData.length > 0 && (
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
          <h2 className="text-xl font-semibold text-white mb-4">
            Volumetrías - {selectedProyecto.nombre}
          </h2>
          <div className="h-[300px]" data-testid="volumetria-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={volumetriaData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                <XAxis dataKey="nombre" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }}
                  labelStyle={{ color: '#fff' }}
                />
                <Legend />
                <Bar dataKey="excavacion" fill="#ef4444" name="Excavación (m³)" />
                <Bar dataKey="relleno" fill="#10b981" name="Relleno (m³)" />
                <Bar dataKey="materiales" fill="#3b82f6" name="Materiales (m³)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Vuelos Recientes */}
      {selectedProyecto && vuelosDelProyecto.length > 0 && (
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
          <h2 className="text-xl font-semibold text-white mb-4">
            Vuelos Recientes - {selectedProyecto.nombre}
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left" data-testid="vuelos-table">
              <thead className="border-b border-slate-700">
                <tr className="text-slate-400">
                  <th className="pb-3 pr-4">Fecha</th>
                  <th className="pb-3 pr-4">Duración</th>
                  <th className="pb-3 pr-4">Área</th>
                  <th className="pb-3 pr-4">Imágenes</th>
                  <th className="pb-3">Estado</th>
                </tr>
              </thead>
              <tbody className="text-white">
                {vuelosDelProyecto.map((vuelo) => (
                  <tr key={vuelo.id} className="border-b border-slate-700/50">
                    <td className="py-3 pr-4">{vuelo.fecha_vuelo}</td>
                    <td className="py-3 pr-4">{vuelo.duracion_minutos} min</td>
                    <td className="py-3 pr-4">{vuelo.area_cubierta.toLocaleString()} m²</td>
                    <td className="py-3 pr-4">{vuelo.num_imagenes}</td>
                    <td className="py-3">
                      <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-sm">
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

// Proyectos View
function ProyectosView({ proyectos, onDelete, onSelect, onRefresh }) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Proyectos</h2>
        <button
          onClick={() => alert('Función de agregar proyecto próximamente')}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          data-testid="add-proyecto-btn"
        >
          <Plus className="h-5 w-5" />
          <span>Nuevo Proyecto</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {proyectos.map((proyecto) => (
          <div
            key={proyecto.id}
            className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700 hover:border-blue-500 transition-all"
            data-testid={`proyecto-card-${proyecto.id}`}
          >
            <div className="flex items-start justify-between mb-4">
              <Building2 className="h-8 w-8 text-blue-400" />
              <div className="flex space-x-2">
                <button
                  onClick={() => onSelect(proyecto)}
                  className="p-2 text-blue-400 hover:bg-blue-500/20 rounded-lg transition-colors"
                  data-testid={`view-proyecto-${proyecto.id}`}
                >
                  <Eye className="h-4 w-4" />
                </button>
                <button
                  onClick={() => onDelete(proyecto.id)}
                  className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                  data-testid={`delete-proyecto-${proyecto.id}`}
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">{proyecto.nombre}</h3>
            <p className="text-slate-400 text-sm mb-4">{proyecto.ubicacion}</p>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between text-slate-300">
                <span>Inicio:</span>
                <span>{proyecto.fecha_inicio}</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Fin Planeado:</span>
                <span>{proyecto.fecha_fin_planeada}</span>
              </div>
              <div className="mt-4">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-400">Avance</span>
                  <span className="text-blue-400 font-semibold">{proyecto.avance_actual}%</span>
                </div>
                <div className="w-full bg-slate-600 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${proyecto.avance_actual}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Vuelos View
function VuelosView({ vuelos, proyectos, onDelete, onRefresh }) {
  const [filtroProyecto, setFiltroProyecto] = useState('todos');

  const vuelosFiltrados = filtroProyecto === 'todos'
    ? vuelos
    : vuelos.filter(v => v.proyecto_id === filtroProyecto);

  const getProyectoNombre = (proyectoId) => {
    const proyecto = proyectos.find(p => p.id === proyectoId);
    return proyecto?.nombre || 'Proyecto desconocido';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Vuelos de Drones</h2>
        <div className="flex items-center space-x-4">
          <select
            value={filtroProyecto}
            onChange={(e) => setFiltroProyecto(e.target.value)}
            className="px-4 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-testid="filter-proyecto-select"
          >
            <option value="todos">Todos los proyectos</option>
            {proyectos.map((p) => (
              <option key={p.id} value={p.id}>{p.nombre}</option>
            ))}
          </select>
          <button
            onClick={() => alert('Función de agregar vuelo próximamente')}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            data-testid="add-vuelo-btn"
          >
            <Plus className="h-5 w-5" />
            <span>Nuevo Vuelo</span>
          </button>
        </div>
      </div>

      <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full" data-testid="vuelos-full-table">
            <thead className="bg-slate-700/50 border-b border-slate-700">
              <tr className="text-slate-300">
                <th className="text-left py-4 px-6">Proyecto</th>
                <th className="text-left py-4 px-6">Fecha</th>
                <th className="text-left py-4 px-6">Duración</th>
                <th className="text-left py-4 px-6">Área Cubierta</th>
                <th className="text-left py-4 px-6">Imágenes</th>
                <th className="text-left py-4 px-6">Excavación</th>
                <th className="text-left py-4 px-6">Estado</th>
                <th className="text-left py-4 px-6">Acciones</th>
              </tr>
            </thead>
            <tbody className="text-white">
              {vuelosFiltrados.map((vuelo) => (
                <tr key={vuelo.id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                  <td className="py-4 px-6">
                    <div className="font-medium">{getProyectoNombre(vuelo.proyecto_id)}</div>
                  </td>
                  <td className="py-4 px-6">{vuelo.fecha_vuelo}</td>
                  <td className="py-4 px-6">{vuelo.duracion_minutos} min</td>
                  <td className="py-4 px-6">{vuelo.area_cubierta.toLocaleString()} m²</td>
                  <td className="py-4 px-6">{vuelo.num_imagenes}</td>
                  <td className="py-4 px-6">{vuelo.volumetria.excavacion.toLocaleString()} m³</td>
                  <td className="py-4 px-6">
                    <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-sm">
                      {vuelo.estado}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    <button
                      onClick={() => onDelete(vuelo.id)}
                      className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                      data-testid={`delete-vuelo-${vuelo.id}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {vuelosFiltrados.length === 0 && (
        <div className="text-center py-12 text-slate-400">
          No hay vuelos registrados para este proyecto.
        </div>
      )}
    </div>
  );
}

// KPI Card Component
function KPICard({ icon: Icon, label, value, color, testId }) {
  const colorClasses = {
    blue: 'bg-blue-500/20 text-blue-400',
    green: 'bg-green-500/20 text-green-400',
    purple: 'bg-purple-500/20 text-purple-400',
    orange: 'bg-orange-500/20 text-orange-400'
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700" data-testid={testId}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-slate-400 text-sm mb-1">{label}</p>
          <p className="text-3xl font-bold text-white">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  );
}

export default App;