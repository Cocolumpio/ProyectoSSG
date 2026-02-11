import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Plane, CalendarPlus, LogOut, User, ClipboardList, Users } from 'lucide-react';

// Auth
import { AuthProvider, useAuth } from './context/AuthContext';
import { LoginPage } from './components/Auth/LoginPage';

// Componentes refactorizados
import { DashboardView } from './components/Dashboard/DashboardView';
import { ProyectosView } from './components/Projects/ProyectosView';
import { VuelosView } from './components/Flights/VuelosView';
import { SolicitarVueloForm } from './components/Flights/SolicitarVueloForm';
import { SolicitudesAdminView } from './components/Admin/SolicitudesAdminView';
import { UsuariosAdminView } from './components/Admin/UsuariosAdminView';
import { MisSolicitudesView } from './components/Client/MisSolicitudesView';

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

function AppContent() {
  const { user, isAdmin, isAuthenticated, loading, logout } = useAuth();
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
      // Si el usuario es cliente, filtrar proyectos por su ID
      const proyectosUrl = user?.rol === 'client' 
        ? `${API}/proyectos?cliente_id=${user.id}`
        : `${API}/proyectos`;
      
      const [proyectosRes, vuelosRes, estadisticasRes] = await Promise.all([
        axios.get(proyectosUrl),
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
  }, [selectedProyecto, user]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchData();
    }
  }, [fetchData, isAuthenticated]);

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

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8F9FA] flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-[#994B49] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-500">Cargando...</p>
        </div>
      </div>
    );
  }

  // Not authenticated - show login
  if (!isAuthenticated) {
    return <LoginPage />;
  }

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
              <img 
                src="/logo-dron.png" 
                alt="DrON Topografía" 
                className="h-10 sm:h-12 w-auto"
              />
            </div>
            
            <nav className="flex items-center space-x-1 sm:space-x-2">
              <NavButton active={activeView === 'dashboard'} onClick={() => setActiveView('dashboard')} testId="nav-dashboard-btn">
                Dashboard
              </NavButton>
              <NavButton active={activeView === 'proyectos'} onClick={() => setActiveView('proyectos')} testId="nav-proyectos-btn">
                Proyectos
              </NavButton>
              <NavButton active={activeView === 'vuelos'} onClick={() => setActiveView('vuelos')} testId="nav-vuelos-btn">
                Vuelos
              </NavButton>
              
              {/* Admin: gestión de solicitudes */}
              {isAdmin && (
                <NavButton 
                  active={activeView === 'solicitudes'} 
                  onClick={() => setActiveView('solicitudes')} 
                  testId="nav-solicitudes-btn"
                >
                  <ClipboardList className="h-4 w-4 sm:mr-1" />
                  <span className="hidden sm:inline">Solicitudes</span>
                </NavButton>
              )}
              
              {/* Admin: gestión de usuarios */}
              {isAdmin && (
                <NavButton 
                  active={activeView === 'usuarios'} 
                  onClick={() => setActiveView('usuarios')} 
                  testId="nav-usuarios-btn"
                >
                  <Users className="h-4 w-4 sm:mr-1" />
                  <span className="hidden sm:inline">Usuarios</span>
                </NavButton>
              )}
              
              {/* Cliente: mis solicitudes */}
              {!isAdmin && (
                <NavButton 
                  active={activeView === 'mis-solicitudes'} 
                  onClick={() => setActiveView('mis-solicitudes')} 
                  testId="nav-mis-solicitudes-btn"
                >
                  <ClipboardList className="h-4 w-4 sm:mr-1" />
                  <span className="hidden sm:inline">Mis Solicitudes</span>
                </NavButton>
              )}
              
              <NavButton 
                active={activeView === 'programar'} 
                onClick={() => setActiveView('programar')} 
                testId="nav-programar-btn" 
                highlight
              >
                <CalendarPlus className="h-4 w-4 sm:mr-1" />
                <span className="hidden sm:inline">Programar</span>
              </NavButton>
            </nav>

            {/* User Menu */}
            <div className="flex items-center space-x-3">
              <div className="hidden sm:flex items-center space-x-2 text-sm">
                <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                  isAdmin ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
                }`}>
                  {isAdmin ? 'Admin' : 'Cliente'}
                </div>
                <span className="text-gray-600">{user?.nombre}</span>
              </div>
              <button
                onClick={logout}
                className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                title="Cerrar sesión"
                data-testid="logout-btn"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
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
            readOnly={!isAdmin}
          />
        )}
        
        {activeView === 'proyectos' && (
          isAdmin ? (
            <ProyectosView
              proyectos={proyectos}
              onDelete={handleDeleteProyecto}
              onSelect={handleProyectoClick}
              onRefresh={fetchData}
              onShowSuccess={showGlobalSuccess}
            />
          ) : (
            <ProyectosViewReadOnly
              proyectos={proyectos}
              onSelect={handleProyectoClick}
              onShowSuccess={showGlobalSuccess}
            />
          )
        )}
        
        {activeView === 'vuelos' && (
          isAdmin ? (
            <VuelosView
              vuelos={vuelos}
              proyectos={proyectos}
              onDelete={handleDeleteVuelo}
              onRefresh={fetchData}
            />
          ) : (
            <VuelosViewReadOnly
              vuelos={vuelos}
              proyectos={proyectos}
            />
          )
        )}
        
        {activeView === 'solicitudes' && isAdmin && (
          <SolicitudesAdminView onShowSuccess={showGlobalSuccess} />
        )}
        
        {activeView === 'usuarios' && isAdmin && (
          <UsuariosAdminView onShowSuccess={showGlobalSuccess} />
        )}
        
        {activeView === 'mis-solicitudes' && !isAdmin && (
          <MisSolicitudesView onNuevaSolicitud={() => setActiveView('programar')} />
        )}
        
        {activeView === 'programar' && (
          <div className="max-w-2xl mx-auto py-8">
            <SolicitarVueloForm 
              onSuccess={(data) => {
                showGlobalSuccess('¡Solicitud de vuelo enviada correctamente!');
                if (!isAdmin) {
                  setActiveView('mis-solicitudes');
                }
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
      className={`px-2 sm:px-3 py-2 rounded-lg text-xs sm:text-sm font-medium transition-colors flex items-center ${
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

// Read-only views for clients
function ProyectosViewReadOnly({ proyectos, onSelect, onShowSuccess }) {
  const { Building2, Eye, Layers, FileText } = require('lucide-react');
  const [showAvancesModal, setShowAvancesModal] = useState(false);
  const [selectedProjectForAvances, setSelectedProjectForAvances] = useState(null);
  const { AvancesSemanalesModal } = require('./components/Projects/AvancesSemanalesModal');

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h2 className="text-xl sm:text-2xl font-bold text-gray-900">Proyectos</h2>
        <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
          Vista de solo lectura
        </span>
      </div>

      {showAvancesModal && selectedProjectForAvances && (
        <AvancesSemanalesModal
          proyecto={selectedProjectForAvances}
          onClose={() => { setShowAvancesModal(false); setSelectedProjectForAvances(null); }}
          onShowSuccess={onShowSuccess}
          readOnly={true}
        />
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6" data-testid="proyectos-grid">
        {proyectos.map((proyecto) => (
          <div key={proyecto.id} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden hover:shadow-md transition-shadow">
            <div className="p-4 sm:p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 text-base sm:text-lg truncate">{proyecto.nombre}</h3>
                  <p className="text-xs sm:text-sm text-gray-500 truncate">{proyecto.ubicacion}</p>
                </div>
                <div className="flex items-center space-x-1 ml-2">
                  <button onClick={() => onSelect(proyecto)} className="p-1.5 sm:p-2 text-gray-600 hover:bg-gray-50 rounded-lg transition-colors" title="Ver en Dashboard">
                    <Eye className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => { setSelectedProjectForAvances(proyecto); setShowAvancesModal(true); }}
                    className="p-1.5 sm:p-2 text-purple-600 hover:bg-purple-50 rounded-lg transition-colors" title="Ver Avances Semanales"
                  >
                    <Layers className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL}/api/proyectos/${proyecto.id}/reporte-ejecutivo`, '_blank')}
                    className="p-1.5 sm:p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors" title="Descargar Reporte PDF"
                  >
                    <FileText className="h-4 w-4" />
                  </button>
                </div>
              </div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-600">Avance</span>
                <span className="font-medium text-[#994B49]">{proyecto.avance_actual}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-[#994B49] h-2 rounded-full transition-all" style={{ width: `${proyecto.avance_actual}%` }} />
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2 text-xs sm:text-sm">
                <div><span className="text-gray-500">Inicio:</span> <span className="text-gray-700">{proyecto.fecha_inicio}</span></div>
                <div><span className="text-gray-500">Fin:</span> <span className="text-gray-700">{proyecto.fecha_fin_planeada}</span></div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {proyectos.length === 0 && (
        <div className="text-center py-12 text-gray-600">
          <Building2 className="h-12 w-12 mx-auto mb-4 text-gray-300" />
          <p>No hay proyectos registrados.</p>
        </div>
      )}
    </div>
  );
}

function VuelosViewReadOnly({ vuelos, proyectos }) {
  const { Plane } = require('lucide-react');
  const [filtroProyecto, setFiltroProyecto] = useState('todos');

  const vuelosFiltrados = filtroProyecto === 'todos' ? vuelos : vuelos.filter(v => v.proyecto_id === filtroProyecto);
  const getProyectoNombre = (proyectoId) => proyectos.find(p => p.id === proyectoId)?.nombre || 'Proyecto desconocido';

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h2 className="text-xl sm:text-2xl font-bold text-gray-900">Vuelos de Drones</h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
            Vista de solo lectura
          </span>
          <select
            value={filtroProyecto} onChange={(e) => setFiltroProyecto(e.target.value)}
            className="px-4 py-2 bg-white text-gray-900 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#994B49]"
          >
            <option value="todos">Todos los proyectos</option>
            {proyectos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
          </select>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr className="text-gray-700 text-sm">
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6">Proyecto</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6">Fecha</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6 hidden sm:table-cell">Duración</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6 hidden md:table-cell">Área</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6 hidden md:table-cell">Imágenes</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6 hidden lg:table-cell">Excavación</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6">Estado</th>
              </tr>
            </thead>
            <tbody className="text-gray-900 text-sm">
              {vuelosFiltrados.map((vuelo) => (
                <tr key={vuelo.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4 sm:py-4 sm:px-6"><div className="font-medium truncate max-w-[120px] sm:max-w-none">{getProyectoNombre(vuelo.proyecto_id)}</div></td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6">{vuelo.fecha_vuelo}</td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6 hidden sm:table-cell">{vuelo.duracion_minutos} min</td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6 hidden md:table-cell">{vuelo.area_cubierta.toLocaleString()} m²</td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6 hidden md:table-cell">{vuelo.num_imagenes}</td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6 hidden lg:table-cell">{vuelo.volumetria.excavacion.toLocaleString()} m³</td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6">
                    <span className={`px-2 py-1 rounded text-xs ${vuelo.estado === 'completado' ? 'bg-green-100 text-green-700' : vuelo.estado === 'procesando' ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>
                      {vuelo.estado}
                    </span>
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
        </div>
      )}
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
