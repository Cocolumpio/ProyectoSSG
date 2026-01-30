import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Building2, Plane, Plus, Eye, Trash2, Pencil, Layers, X, FileText, CalendarPlus } from 'lucide-react';

// Componentes refactorizados
import { DashboardView } from './components/Dashboard/DashboardView';
import { ProjectFormContent } from './components/Projects/ProjectFormContent';
import { AvancesSemanalesModal } from './components/Projects/AvancesSemanalesModal';
import { SolicitarVueloForm } from './components/Flights/SolicitarVueloForm';
import { KPICard } from './components/common/KPICard';

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
      </main>
    </div>
  );
}

// NavButton Component
function NavButton({ children, active, onClick, testId }) {
  return (
    <button
      onClick={onClick}
      className={`px-2 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-medium transition-colors ${
        active
          ? 'bg-[#994B49] text-white'
          : 'text-gray-600 hover:bg-gray-100'
      }`}
      data-testid={testId}
    >
      {children}
    </button>
  );
}

// ProyectosView Component
function ProyectosView({ proyectos, onDelete, onSelect, onRefresh, onShowSuccess }) {
  const [showForm, setShowForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [showAvancesModal, setShowAvancesModal] = useState(false);
  const [selectedProjectForAvances, setSelectedProjectForAvances] = useState(null);
  const [formData, setFormData] = useState({
    nombre: '', ubicacion: '', coordenadas: { lat: 20.6597, lng: -103.3496 },
    fecha_inicio: '', fecha_fin_planeada: '', descripcion: '', avance_actual: 0,
    pix4d_url: '', volumetria: { excavacion: 0, relleno: 0, materiales: 0 },
    capacidad_camion: 25, costo_viaje_camion: 2500
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const resetForm = () => {
    setFormData({
      nombre: '', ubicacion: '', coordenadas: { lat: 20.6597, lng: -103.3496 },
      fecha_inicio: '', fecha_fin_planeada: '', descripcion: '', avance_actual: 0,
      pix4d_url: '', volumetria: { excavacion: 0, relleno: 0, materiales: 0 },
      capacidad_camion: 25, costo_viaje_camion: 2500
    });
  };

  const handleEditClick = (proyecto) => {
    setEditingProject(proyecto);
    setFormData({
      nombre: proyecto.nombre || '', ubicacion: proyecto.ubicacion || '',
      coordenadas: proyecto.coordenadas || { lat: 20.6597, lng: -103.3496 },
      fecha_inicio: proyecto.fecha_inicio || '', fecha_fin_planeada: proyecto.fecha_fin_planeada || '',
      descripcion: proyecto.descripcion || '', avance_actual: proyecto.avance_actual || 0,
      pix4d_url: proyecto.pix4d_url || '',
      volumetria: proyecto.volumetria || { excavacion: 0, relleno: 0, materiales: 0 },
      capacidad_camion: proyecto.capacidad_camion || 25, costo_viaje_camion: proyecto.costo_viaje_camion || 2500
    });
    setShowEditForm(true);
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
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
    try {
      await axios.put(`${API}/proyectos/${editingProject.id}`, formData);
      setShowEditForm(false);
      setEditingProject(null);
      resetForm();
      if (onShowSuccess) onShowSuccess(`¡Proyecto "${projectName}" actualizado correctamente!`);
      await onRefresh();
    } catch (err) {
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

      {/* Modal de Crear Proyecto */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-2 sm:p-4">
          <div className="bg-white rounded-xl shadow-xl w-full sm:max-w-2xl max-h-[95vh] sm:max-h-[90vh] overflow-hidden">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
              <h3 className="text-lg sm:text-xl font-semibold text-gray-900">Nuevo Proyecto</h3>
              <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-6 w-6" />
              </button>
            </div>
            <div className="overflow-y-auto max-h-[calc(95vh-60px)] sm:max-h-[calc(90vh-70px)]">
              <ProjectFormContent
                formData={formData} setFormData={setFormData} error={error} saving={saving}
                isEdit={false} onSubmit={handleSubmit} onClose={() => setShowForm(false)}
              />
            </div>
          </div>
        </div>
      )}

      {/* Modal de Editar Proyecto */}
      {showEditForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-2 sm:p-4">
          <div className="bg-white rounded-xl shadow-xl w-full sm:max-w-2xl max-h-[95vh] sm:max-h-[90vh] overflow-hidden">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
              <h3 className="text-lg sm:text-xl font-semibold text-gray-900">Editar Proyecto</h3>
              <button onClick={() => { setShowEditForm(false); setEditingProject(null); }} className="text-gray-400 hover:text-gray-600">
                <X className="h-6 w-6" />
              </button>
            </div>
            <div className="overflow-y-auto max-h-[calc(95vh-60px)] sm:max-h-[calc(90vh-70px)]">
              <ProjectFormContent
                formData={formData} setFormData={setFormData} error={error} saving={saving}
                isEdit={true} onSubmit={handleEditSubmit} onClose={() => { setShowEditForm(false); setEditingProject(null); }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Modal de Avances Semanales */}
      {showAvancesModal && selectedProjectForAvances && (
        <AvancesSemanalesModal
          proyecto={selectedProjectForAvances}
          onClose={() => { setShowAvancesModal(false); setSelectedProjectForAvances(null); }}
          onShowSuccess={onShowSuccess}
        />
      )}

      {/* Grid de Proyectos */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6" data-testid="proyectos-grid">
        {proyectos.map((proyecto) => (
          <div key={proyecto.id} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden hover:shadow-md transition-shadow" data-testid={`proyecto-card-${proyecto.id}`}>
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
                    data-testid={`avances-proyecto-${proyecto.id}`}
                  >
                    <Layers className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL}/api/proyectos/${proyecto.id}/reporte-ejecutivo`, '_blank')}
                    className="p-1.5 sm:p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors" title="Descargar Reporte Ejecutivo PDF"
                    data-testid={`reporte-proyecto-${proyecto.id}`}
                  >
                    <FileText className="h-4 w-4" />
                  </button>
                  <button onClick={() => handleEditClick(proyecto)} className="p-1.5 sm:p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Editar Proyecto" data-testid={`edit-proyecto-${proyecto.id}`}>
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button onClick={() => onDelete(proyecto.id)} className="p-1.5 sm:p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors" title="Eliminar Proyecto" data-testid={`delete-proyecto-${proyecto.id}`}>
                    <Trash2 className="h-4 w-4" />
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
          <button onClick={() => { resetForm(); setShowForm(true); }} className="mt-4 text-[#994B49] hover:underline">Agregar primer proyecto</button>
        </div>
      )}
    </div>
  );
}

// VuelosView Component
function VuelosView({ vuelos, proyectos, onDelete, onRefresh }) {
  const [filtroProyecto, setFiltroProyecto] = useState('todos');
  const [showForm, setShowForm] = useState(false);
  const [editingVuelo, setEditingVuelo] = useState(null);
  const [formData, setFormData] = useState({
    proyecto_id: '', fecha_vuelo: '', duracion_minutos: 30, area_cubierta: 1000, num_imagenes: 100,
    volumetria: { excavacion: 0, relleno: 0, materiales: 0 }, pix4d_url: '', notas: '', estado: 'completado'
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const vuelosFiltrados = filtroProyecto === 'todos' ? vuelos : vuelos.filter(v => v.proyecto_id === filtroProyecto);
  const getProyectoNombre = (proyectoId) => proyectos.find(p => p.id === proyectoId)?.nombre || 'Proyecto desconocido';

  const resetForm = () => {
    setFormData({
      proyecto_id: proyectos.length > 0 ? proyectos[0].id : '', fecha_vuelo: new Date().toISOString().split('T')[0],
      duracion_minutos: 30, area_cubierta: 1000, num_imagenes: 100,
      volumetria: { excavacion: 0, relleno: 0, materiales: 0 }, pix4d_url: '', notas: '', estado: 'completado'
    });
  };

  const handleEditClick = (vuelo) => {
    setEditingVuelo(vuelo);
    setFormData({
      proyecto_id: vuelo.proyecto_id || '', fecha_vuelo: vuelo.fecha_vuelo || '',
      duracion_minutos: vuelo.duracion_minutos || 30, area_cubierta: vuelo.area_cubierta || 1000,
      num_imagenes: vuelo.num_imagenes || 100,
      volumetria: vuelo.volumetria || { excavacion: 0, relleno: 0, materiales: 0 },
      pix4d_url: vuelo.pix4d_url || '', notas: vuelo.notas || '', estado: vuelo.estado || 'completado'
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
    setFormData(prev => ({ ...prev, volumetria: { ...prev.volumetria, [field]: parseFloat(value) || 0 } }));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h2 className="text-xl sm:text-2xl font-bold text-gray-900">Vuelos de Drones</h2>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-4">
          <select
            value={filtroProyecto} onChange={(e) => setFiltroProyecto(e.target.value)}
            className="px-4 py-2 bg-white text-gray-900 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            data-testid="filter-proyecto-select"
          >
            <option value="todos">Todos los proyectos</option>
            {proyectos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
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
              <h3 className="text-lg sm:text-xl font-semibold text-gray-900">{editingVuelo ? 'Editar Vuelo' : 'Nuevo Vuelo'}</h3>
              <button onClick={() => { setShowForm(false); setEditingVuelo(null); }} className="text-gray-400 hover:text-gray-600" data-testid="close-vuelo-modal">
                <X className="h-6 w-6" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-4 sm:p-6 space-y-4">
              {error && <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">{error}</div>}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Proyecto *</label>
                  <select name="proyecto_id" value={formData.proyecto_id} onChange={handleInputChange} required className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-proyecto-select">
                    <option value="">Seleccionar proyecto</option>
                    {proyectos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Fecha del Vuelo *</label>
                  <input type="date" name="fecha_vuelo" value={formData.fecha_vuelo} onChange={handleInputChange} required className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-fecha-input" />
                </div>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Duración (min) *</label>
                  <input type="number" name="duracion_minutos" value={formData.duracion_minutos} onChange={handleInputChange} min="1" required className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-duracion-input" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Área (m²) *</label>
                  <input type="number" name="area_cubierta" value={formData.area_cubierta} onChange={handleInputChange} min="0" step="0.1" required className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-area-input" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Nº Imágenes *</label>
                  <input type="number" name="num_imagenes" value={formData.num_imagenes} onChange={handleInputChange} min="0" required className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-imagenes-input" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
                <select name="estado" value={formData.estado} onChange={handleInputChange} className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-estado-select">
                  <option value="completado">Completado</option>
                  <option value="procesando">Procesando</option>
                  <option value="fallido">Fallido</option>
                </select>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <h4 className="font-medium text-gray-900 mb-3">Volumetría del Vuelo (m³)</h4>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Excavación</label>
                    <input type="number" step="0.1" min="0" value={formData.volumetria.excavacion} onChange={(e) => handleVolumetriaChange('excavacion', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-vol-excavacion-input" />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Relleno</label>
                    <input type="number" step="0.1" min="0" value={formData.volumetria.relleno} onChange={(e) => handleVolumetriaChange('relleno', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-vol-relleno-input" />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1">Materiales</label>
                    <input type="number" step="0.1" min="0" value={formData.volumetria.materiales} onChange={(e) => handleVolumetriaChange('materiales', e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-vol-materiales-input" />
                  </div>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">URL Modelo 3D (Pix4D)</label>
                <input type="url" name="pix4d_url" value={formData.pix4d_url} onChange={handleInputChange} placeholder="https://cloud.pix4d.com/embed/..." className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-pix4d-input" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notas</label>
                <textarea name="notas" value={formData.notas} onChange={handleInputChange} rows={2} placeholder="Observaciones del vuelo..." className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-notas-input" />
              </div>
              <div className="flex items-center justify-end space-x-3 pt-4">
                <button type="button" onClick={() => { setShowForm(false); setEditingVuelo(null); }} className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors">Cancelar</button>
                <button type="submit" disabled={saving} className="px-6 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors disabled:opacity-50" data-testid="vuelo-submit-btn">
                  {saving ? 'Guardando...' : (editingVuelo ? 'Guardar Cambios' : 'Crear Vuelo')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Tabla de Vuelos */}
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
                  <td className="py-3 px-4 sm:py-4 sm:px-6">
                    <div className="flex items-center space-x-1">
                      <button onClick={() => handleEditClick(vuelo)} className="p-1.5 sm:p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Editar" data-testid={`edit-vuelo-${vuelo.id}`}>
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button onClick={() => onDelete(vuelo.id)} className="p-1.5 sm:p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors" title="Eliminar" data-testid={`delete-vuelo-${vuelo.id}`}>
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
          <button onClick={() => { resetForm(); setShowForm(true); }} className="mt-4 text-[#994B49] hover:underline">Agregar primer vuelo</button>
        </div>
      )}
    </div>
  );
}

export default App;
