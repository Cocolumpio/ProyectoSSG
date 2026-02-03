import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Plane, CalendarPlus } from 'lucide-react';

// Componentes refactorizados
import { DashboardView } from './components/Dashboard/DashboardView';
import { ProyectosView } from './components/Projects/ProyectosView';
import { VuelosView } from './components/Flights/VuelosView';
import { SolicitarVueloForm } from './components/Flights/SolicitarVueloForm';

// Configuración de Leaflet
import './utils/leafletConfig';

// Fix Leaflet default icon issue
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function App() {
  const [activeView, setActiveView] = useState('dashboard');
  const [proyectos, setProyectos] = useState([]);
  const [vuelos, setVuelos] = useState([]);
  const [estadisticas, setEstadisticas] = useState(null);
  const [selectedProyecto, setSelectedProyecto] = useState(null);
  const [mapCenter, setMapCenter] = useState({ lat: 20.6597, lng: -103.3496 });
  const [globalSuccessMessage, setGlobalSuccessMessage] = useState(null);

  const showGlobalSuccess = (message) => {
    setGlobalSuccessMessage(message);
    setTimeout(() => setGlobalSuccessMessage(null), 5000);
  };

  const fetchData = useCallback(async () => {
    try {
      const [proyectosRes, vuelosRes, estadisticasRes] = await Promise.all([
        axios.get(`${API}/proyectos`),
        axios.get(`${API}/vuelos`),
        axios.get(`${API}/estadisticas/resumen`)
      ]);
      setProyectos(proyectosRes.data);
      setVuelos(vuelosRes.data);
      setEstadisticas(estadisticasRes.data);

      if (proyectosRes.data.length > 0 && !selectedProyecto) {
        const firstProject = proyectosRes.data[0];
        setSelectedProyecto(firstProject);
        if (firstProject.coordenadas) {
          setMapCenter(firstProject.coordenadas);
        }
      } else if (selectedProyecto) {
        const updatedProject = proyectosRes.data.find(p => p.id === selectedProyecto.id);
        if (updatedProject) {
          setSelectedProyecto(updatedProject);
        }
      }
    } catch (err) {
      console.error('Error fetching data:', err);
    }
  }, [selectedProyecto]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleProyectoClick = (proyecto) => {
    setSelectedProyecto(proyecto);
    if (proyecto.coordenadas) {
      setMapCenter(proyecto.coordenadas);
    }
  };

  const handleDeleteProyecto = async (id) => {
    if (!window.confirm('¿Eliminar este proyecto?')) return;
    try {
      await axios.delete(`${API}/proyectos/${id}`);
      fetchData();
      if (selectedProyecto?.id === id) {
        setSelectedProyecto(null);
      }
    } catch (err) {
      console.error('Error deleting proyecto:', err);
    }
  };

  const handleDeleteVuelo = async (id) => {
    if (!window.confirm('¿Eliminar este vuelo?')) return;
    try {
      await axios.delete(`${API}/vuelos/${id}`);
      fetchData();
    } catch (err) {
      console.error('Error deleting vuelo:', err);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA]">
      {/* Notificación global de éxito */}
      {globalSuccessMessage && (
        <div className="fixed top-4 right-4 z-50 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg flex items-center space-x-2 animate-fade-in">
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span>{globalSuccessMessage}</span>
        </div>
      )}

      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14 sm:h-16">
            <div className="flex items-center space-x-2 sm:space-x-3">
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-[#994B49] rounded-lg flex items-center justify-center">
                <Plane className="h-5 w-5 sm:h-6 sm:w-6 text-white" />
              </div>
              <div>
                <h1 className="text-lg sm:text-xl font-bold text-[#994B49]">DrON</h1>
                <p className="text-xs text-gray-500 hidden sm:block">Topografía</p>
              </div>
            </div>
            <nav className="flex items-center space-x-1 sm:space-x-4">
              <NavButton active={activeView === 'dashboard'} onClick={() => setActiveView('dashboard')} testId="nav-dashboard-btn">
                Dashboard
              </NavButton>
              <NavButton active={activeView === 'proyectos'} onClick={() => setActiveView('proyectos')} testId="nav-proyectos-btn">
                Proyectos
              </NavButton>
              <NavButton active={activeView === 'vuelos'} onClick={() => setActiveView('vuelos')} testId="nav-vuelos-btn">
                Vuelos
              </NavButton>
              <NavButton active={activeView === 'programar'} onClick={() => setActiveView('programar')} testId="nav-programar-btn" highlight>
                <CalendarPlus className="h-4 w-4 sm:mr-1" />
                <span className="hidden sm:inline">Programar</span>
              </NavButton>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
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
            onShowSuccess={showGlobalSuccess}
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
        {activeView === 'programar' && (
          <div className="max-w-2xl mx-auto py-8">
            <SolicitarVueloForm 
              onSuccess={(data) => {
                showGlobalSuccess('¡Solicitud de vuelo enviada correctamente!');
              }}
            />
          </div>
        )}
      </main>
    </div>
  );
}

// NavButton Component
function NavButton({ children, active, onClick, testId, highlight }) {
  return (
    <button
      onClick={onClick}
      className={`px-2 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-medium transition-colors flex items-center ${
        active
          ? 'bg-[#994B49] text-white'
          : highlight
            ? 'bg-amber-100 text-amber-700 hover:bg-amber-200 border border-amber-300'
            : 'text-gray-600 hover:bg-gray-100'
      }`}
      data-testid={testId}
    >
      {children}
    </button>
  );
}

export default App;
