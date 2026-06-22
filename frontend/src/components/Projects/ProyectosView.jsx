import { useState, useEffect } from 'react';
import axios from 'axios';
import { Building2, Plus, Eye, Trash2, Pencil, Layers, X, FileText, Users, UserPlus, FileSpreadsheet, CalendarClock, Wallet } from 'lucide-react';
import { ProjectFormContent } from './ProjectFormContent';
import { AvancesSemanalesModal } from './AvancesSemanalesModal';
import { ImportarCronograma } from './ImportarCronograma';
import { CronogramaProyectoModal } from './CronogramaProyectoModal';
import { PresupuestoSection } from './PresupuestoSection';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function ProyectosView({ proyectos, onDelete, onSelect, onRefresh, onShowSuccess }) {
  const [showForm, setShowForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [showAvancesModal, setShowAvancesModal] = useState(false);
  const [selectedProjectForAvances, setSelectedProjectForAvances] = useState(null);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [selectedProjectForAssign, setSelectedProjectForAssign] = useState(null);
  const [availableClients, setAvailableClients] = useState([]);
  const [selectedClients, setSelectedClients] = useState([]);
  const [loadingClients, setLoadingClients] = useState(false);
  const [savingAssignment, setSavingAssignment] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showCronogramaModal, setShowCronogramaModal] = useState(false);
  const [selectedProjectForCronograma, setSelectedProjectForCronograma] = useState(null);
  const [showPresupuestoModal, setShowPresupuestoModal] = useState(false);
  const [selectedProjectForPresupuesto, setSelectedProjectForPresupuesto] = useState(null);
  const [formData, setFormData] = useState({
    nombre: '', ubicacion: '', direccion: '', coordenadas: { lat: 0, lng: 0 },
    fecha_inicio: '', fecha_fin_planeada: '', descripcion: '', avance_actual: 0,
    volumen_total_planeado: 0, semanas_planeadas: 0,
    pilas_planeadas: 0, anclas_planeadas: 0, muros_planeados: 0, perfiles_planeados: 0,
    capacidad_camion: 25, costo_m3: 150,
    caras_excavacion: [],
    fases: { excavacion: false, cimentacion: false, edificacion: false }
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const resetForm = () => {
    setFormData({
      nombre: '', ubicacion: '', direccion: '', coordenadas: { lat: 0, lng: 0 },
      fecha_inicio: '', fecha_fin_planeada: '', descripcion: '', avance_actual: 0,
      volumen_total_planeado: 0, semanas_planeadas: 0,
      pilas_planeadas: 0, anclas_planeadas: 0, muros_planeados: 0, perfiles_planeados: 0,
      capacidad_camion: 25, costo_m3: 150,
      caras_excavacion: [],
      fases: { excavacion: false, cimentacion: false, edificacion: false }
    });
  };

  const handleEditClick = (proyecto) => {
    setEditingProject(proyecto);
    
    // Usar fases_activas guardadas si existen, sino calcular basado en datos
    let fases;
    if (proyecto.fases_activas && Array.isArray(proyecto.fases_activas)) {
      fases = {
        excavacion: proyecto.fases_activas.includes('excavacion'),
        cimentacion: proyecto.fases_activas.includes('cimentacion'),
        edificacion: proyecto.fases_activas.includes('edificacion')
      };
    } else {
      // Fallback: determinar fases basadas en los datos del proyecto (proyectos antiguos)
      const tipos = proyecto.actividades_tipo || [];
      fases = {
        excavacion: tipos.includes('excavacion') || proyecto.volumen_total_planeado > 0,
        cimentacion: tipos.includes('pilas') || tipos.includes('anclas') || proyecto.pilas_planeadas > 0 || proyecto.anclas_planeadas > 0,
        edificacion: tipos.includes('muros') || proyecto.muros_planeados > 0
      };
    }
    
    setFormData({
      id: proyecto.id,
      nombre: proyecto.nombre || '', 
      ubicacion: proyecto.ubicacion || '',
      direccion: proyecto.direccion || proyecto.ubicacion || '',
      coordenadas: proyecto.coordenadas || { lat: 0, lng: 0 },
      fecha_inicio: proyecto.fecha_inicio || '', 
      fecha_fin_planeada: proyecto.fecha_fin_planeada || '',
      descripcion: proyecto.descripcion || '', 
      avance_actual: proyecto.avance_actual || 0,
      volumen_total_planeado: proyecto.volumen_total_planeado || 0,
      semanas_planeadas: proyecto.semanas_planeadas || 0,
      pilas_planeadas: proyecto.pilas_planeadas || 0,
      anclas_planeadas: proyecto.anclas_planeadas || 0,
      muros_planeados: proyecto.muros_planeados || 0,
      capacidad_camion: proyecto.capacidad_camion || 25, 
      costo_m3: proyecto.costo_m3 || 150,
      caras_excavacion: Array.isArray(proyecto.caras_excavacion) ? proyecto.caras_excavacion : [],
      perfiles_planeados: proyecto.perfiles_planeados || 0,
      wa_grupo_chat_id: proyecto.wa_grupo_chat_id || null,
      wa_grupo_nombre: proyecto.wa_grupo_nombre || null,
      fases
    });
    setShowEditForm(true);
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      // Construir actividades_tipo basado en las fases seleccionadas
      const actividades_tipo = [];
      const fases_activas = [];
      
      if (formData.fases?.excavacion) {
        actividades_tipo.push('excavacion');
        fases_activas.push('excavacion');
      }
      if (formData.fases?.cimentacion) {
        actividades_tipo.push('pilas');
        fases_activas.push('cimentacion');
        if (formData.anclas_planeadas > 0) actividades_tipo.push('anclas');
        if (formData.perfiles_planeados > 0) actividades_tipo.push('perfiles');
      }
      if (formData.fases?.edificacion) {
        actividades_tipo.push('muros');
        fases_activas.push('edificacion');
      }
      
      const dataToSend = {
        ...formData,
        actividades_tipo,
        fases_activas, // Guardar las fases seleccionadas
        fases: undefined // No enviar el objeto fases temporal
      };
      delete dataToSend.fases;
      
      await axios.post(`${API}/proyectos`, dataToSend);
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
      // Construir actividades_tipo basado en las fases seleccionadas
      const actividades_tipo = [];
      if (formData.fases?.excavacion) actividades_tipo.push('excavacion');
      if (formData.fases?.cimentacion) {
        actividades_tipo.push('pilas');
        if (formData.anclas_planeadas > 0) actividades_tipo.push('anclas');
        if (formData.perfiles_planeados > 0) actividades_tipo.push('perfiles');
      }
      if (formData.fases?.edificacion) actividades_tipo.push('muros');
      
      const dataToSend = {
        ...formData,
        actividades_tipo,
        fases: undefined
      };
      delete dataToSend.fases;
      
      await axios.put(`${API}/proyectos/${editingProject.id}`, dataToSend);
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

  const handleOpenAssignModal = async (proyecto) => {
    setSelectedProjectForAssign(proyecto);
    setSelectedClients(proyecto.clientes_asignados || []);
    setShowAssignModal(true);
    setLoadingClients(true);
    
    try {
      const response = await axios.get(`${API}/auth/users`);
      // Filtrar solo clientes activos
      const clients = response.data.filter(u => u.rol === 'client' && u.activo);
      setAvailableClients(clients);
    } catch (err) {
      console.error('Error cargando clientes:', err);
    } finally {
      setLoadingClients(false);
    }
  };

  const handleToggleClient = (clientId) => {
    setSelectedClients(prev => 
      prev.includes(clientId) 
        ? prev.filter(id => id !== clientId)
        : [...prev, clientId]
    );
  };

  const handleSaveAssignment = async () => {
    if (!selectedProjectForAssign) return;
    setSavingAssignment(true);
    
    try {
      await axios.post(`${API}/proyectos/${selectedProjectForAssign.id}/asignar-clientes`, selectedClients);
      setShowAssignModal(false);
      setSelectedProjectForAssign(null);
      if (onShowSuccess) onShowSuccess(`Clientes asignados al proyecto "${selectedProjectForAssign.nombre}"`);
      await onRefresh();
    } catch (err) {
      console.error('Error asignando clientes:', err);
      alert(err.response?.data?.detail || 'Error al asignar clientes');
    } finally {
      setSavingAssignment(false);
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h2 className="text-xl sm:text-2xl font-bold text-white">Proyectos</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setShowImportModal(true)}
            className="flex items-center justify-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            data-testid="import-cronograma-btn"
          >
            <FileSpreadsheet className="h-5 w-5" />
            <span>Importar Excel</span>
          </button>
          <button
            onClick={() => { resetForm(); setShowForm(true); }}
            className="flex items-center justify-center space-x-2 px-4 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors"
            data-testid="add-proyecto-btn"
          >
            <Plus className="h-5 w-5" />
            <span>Nuevo Proyecto</span>
          </button>
        </div>
      </div>

      {/* Modal de Importar Cronograma */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[1000] p-2 sm:p-4">
          <div className="bg-[#15151B] rounded-xl shadow-xl w-full max-w-4xl max-h-[95vh] overflow-y-auto">
            <div className="sticky top-0 bg-[#15151B] border-b border-white/10 px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between z-10">
              <h3 className="text-lg sm:text-xl font-semibold text-white">Importar Cronograma desde Excel</h3>
              <button onClick={() => setShowImportModal(false)} className="text-white/40 hover:text-white/60">
                <X className="h-6 w-6" />
              </button>
            </div>
            <div className="p-4">
              <ImportarCronograma 
                onProyectoCreado={(data) => {
                  onShowSuccess && onShowSuccess(`Proyecto creado: ${data.mensaje}`);
                  onRefresh && onRefresh();
                  setShowImportModal(false);
                }}
                onClose={() => setShowImportModal(false)}
              />
            </div>
          </div>
        </div>
      )}

      {/* Modal de Crear Proyecto */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[1000] p-2 sm:p-4">
          <div className="bg-[#15151B] rounded-xl shadow-xl w-full sm:max-w-2xl max-h-[95vh] sm:max-h-[90vh] overflow-hidden">
            <div className="sticky top-0 bg-[#15151B] border-b border-white/10 px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
              <h3 className="text-lg sm:text-xl font-semibold text-white">Nuevo Proyecto</h3>
              <button onClick={() => setShowForm(false)} className="text-white/40 hover:text-white/60">
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
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[1000] p-2 sm:p-4">
          <div className="bg-[#15151B] rounded-xl shadow-xl w-full sm:max-w-2xl max-h-[95vh] sm:max-h-[90vh] overflow-hidden">
            <div className="sticky top-0 bg-[#15151B] border-b border-white/10 px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
              <h3 className="text-lg sm:text-xl font-semibold text-white">Editar Proyecto</h3>
              <button onClick={() => { setShowEditForm(false); setEditingProject(null); }} className="text-white/40 hover:text-white/60">
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

      {/* Modal de Asignar Clientes */}
      {showAssignModal && selectedProjectForAssign && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[1000] p-4">
          <div className="bg-[#15151B] rounded-xl shadow-xl w-full max-w-md max-h-[80vh] overflow-hidden">
            <div className="sticky top-0 bg-[#15151B] border-b border-white/10 px-6 py-4 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white">Asignar Clientes</h3>
                <p className="text-sm text-white/50">{selectedProjectForAssign.nombre}</p>
              </div>
              <button 
                onClick={() => { setShowAssignModal(false); setSelectedProjectForAssign(null); }} 
                className="text-white/40 hover:text-white/60"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[calc(80vh-140px)]">
              {loadingClients ? (
                <div className="flex items-center justify-center py-8">
                  <div className="w-8 h-8 border-4 border-[#994B49] border-t-transparent rounded-full animate-spin" />
                </div>
              ) : availableClients.length === 0 ? (
                <div className="text-center py-8 text-white/50">
                  <Users className="h-12 w-12 mx-auto mb-3 text-white/30" />
                  <p>No hay clientes disponibles</p>
                  <p className="text-sm mt-1">Crea clientes desde el panel de usuarios</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {availableClients.map(client => (
                    <label
                      key={client.id}
                      className={`flex items-center p-3 rounded-lg border cursor-pointer transition-colors ${
                        selectedClients.includes(client.id)
                          ? 'border-[#994B49] bg-[#994B49]/5'
                          : 'border-white/10 hover:border-white/15'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedClients.includes(client.id)}
                        onChange={() => handleToggleClient(client.id)}
                        className="w-4 h-4 text-[#994B49] border-white/15 rounded focus:ring-[#994B49]"
                      />
                      <div className="ml-3 flex-1">
                        <p className="font-medium text-white">{client.email}</p>
                        <p className="text-xs text-white/50">ID: {client.id.slice(0, 8)}...</p>
                      </div>
                      {selectedClients.includes(client.id) && (
                        <span className="text-xs bg-[#994B49] text-white px-2 py-0.5 rounded-full">
                          Asignado
                        </span>
                      )}
                    </label>
                  ))}
                </div>
              )}
            </div>
            
            <div className="sticky bottom-0 bg-[#15151B] border-t border-white/10 px-6 py-4 flex items-center justify-between">
              <span className="text-sm text-white/50">
                {selectedClients.length} cliente(s) seleccionado(s)
              </span>
              <div className="flex space-x-3">
                <button
                  onClick={() => { setShowAssignModal(false); setSelectedProjectForAssign(null); }}
                  className="px-4 py-2 text-white/80 hover:bg-[#15151B] rounded-lg transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleSaveAssignment}
                  disabled={savingAssignment}
                  className="px-4 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] disabled:opacity-50 transition-colors flex items-center space-x-2"
                >
                  {savingAssignment ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <UserPlus className="h-4 w-4" />
                  )}
                  <span>Guardar</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Cronograma/Programa de Obra */}
      {showCronogramaModal && selectedProjectForCronograma && (
        <CronogramaProyectoModal
          proyecto={selectedProjectForCronograma}
          onClose={() => {
            setShowCronogramaModal(false);
            setSelectedProjectForCronograma(null);
          }}
          onSuccess={(msg) => {
            onShowSuccess && onShowSuccess(msg);
            onRefresh && onRefresh();
          }}
        />
      )}

      {/* Grid de Proyectos */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6" data-testid="proyectos-grid">
        {proyectos.map((proyecto) => (
          <div key={proyecto.id} className="bg-[#15151B] rounded-xl border border-white/10 shadow-sm overflow-hidden hover:shadow-md transition-shadow" data-testid={`proyecto-card-${proyecto.id}`}>
            <div className="p-4 sm:p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-white text-base sm:text-lg truncate">{proyecto.nombre}</h3>
                  <p className="text-xs sm:text-sm text-white/50 truncate">{proyecto.ubicacion}</p>
                </div>
                <div className="flex items-center space-x-1 ml-2">
                  <button onClick={() => onSelect(proyecto)} className="p-1.5 sm:p-2 text-white/60 hover:bg-[#0F0F14] rounded-lg transition-colors" title="Ver en Dashboard">
                    <Eye className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => { setSelectedProjectForAvances(proyecto); setShowAvancesModal(true); }}
                    className="p-1.5 sm:p-2 text-purple-600 hover:bg-purple-500/10 rounded-lg transition-colors" title="Ver Avances Semanales"
                    data-testid={`avances-proyecto-${proyecto.id}`}
                  >
                    <Layers className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => window.open(`${process.env.REACT_APP_BACKEND_URL}/api/proyectos/${proyecto.id}/reporte-ejecutivo`, '_blank')}
                    className="p-1.5 sm:p-2 text-green-600 hover:bg-green-500/10 rounded-lg transition-colors" title="Descargar Reporte Ejecutivo PDF"
                    data-testid={`reporte-proyecto-${proyecto.id}`}
                  >
                    <FileText className="h-4 w-4" />
                  </button>
                  <button 
                    onClick={() => handleOpenAssignModal(proyecto)} 
                    className="p-1.5 sm:p-2 text-orange-600 hover:bg-orange-500/10 rounded-lg transition-colors" 
                    title="Asignar Clientes"
                    data-testid={`assign-proyecto-${proyecto.id}`}
                  >
                    <Users className="h-4 w-4" />
                  </button>
                  <button 
                    onClick={() => {
                      setSelectedProjectForCronograma(proyecto);
                      setShowCronogramaModal(true);
                    }} 
                    className="p-1.5 sm:p-2 text-purple-600 hover:bg-purple-500/10 rounded-lg transition-colors" 
                    title="Programa de Obra"
                    data-testid={`cronograma-proyecto-${proyecto.id}`}
                  >
                    <CalendarClock className="h-4 w-4" />
                  </button>
                  <button 
                    onClick={() => {
                      setSelectedProjectForPresupuesto(proyecto);
                      setShowPresupuestoModal(true);
                    }} 
                    className="p-1.5 sm:p-2 text-amber-400 hover:bg-amber-500/10 rounded-lg transition-colors" 
                    title="Presupuesto (IA)"
                    data-testid={`presupuesto-proyecto-${proyecto.id}`}
                  >
                    <Wallet className="h-4 w-4" />
                  </button>
                  <button onClick={() => handleEditClick(proyecto)} className="p-1.5 sm:p-2 text-blue-600 hover:bg-blue-500/10 rounded-lg transition-colors" title="Editar Proyecto" data-testid={`edit-proyecto-${proyecto.id}`}>
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button onClick={() => onDelete(proyecto.id)} className="p-1.5 sm:p-2 text-red-600 hover:bg-red-500/10 rounded-lg transition-colors" title="Eliminar Proyecto" data-testid={`delete-proyecto-${proyecto.id}`}>
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-white/60">Avance</span>
                <span className="font-medium text-[#994B49]">{proyecto.avance_actual}%</span>
              </div>
              <div className="w-full bg-[#1F1F26] rounded-full h-2">
                <div className="bg-[#994B49] h-2 rounded-full transition-all" style={{ width: `${proyecto.avance_actual}%` }} />
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2 text-xs sm:text-sm">
                <div><span className="text-white/50">Inicio:</span> <span className="text-white/80">{proyecto.fecha_inicio}</span></div>
                <div><span className="text-white/50">Fin:</span> <span className="text-white/80">{proyecto.fecha_fin_planeada}</span></div>
              </div>
              {proyecto.clientes_asignados && proyecto.clientes_asignados.length > 0 && (
                <div className="mt-3 flex items-center space-x-1 text-xs text-orange-600">
                  <Users className="h-3.5 w-3.5" />
                  <span>{proyecto.clientes_asignados.length} cliente(s) asignado(s)</span>
                </div>
              )}
              {proyecto.cronograma_archivo && (
                <div className="mt-2 flex items-center space-x-1 text-xs text-purple-600">
                  <CalendarClock className="h-3.5 w-3.5" />
                  <span>Programa de obra cargado</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {proyectos.length === 0 && (
        <div className="text-center py-12 text-white/60">
          <Building2 className="h-12 w-12 mx-auto mb-4 text-white/30" />
          <p>No hay proyectos registrados.</p>
          <button onClick={() => { resetForm(); setShowForm(true); }} className="mt-4 text-[#994B49] hover:underline">Agregar primer proyecto</button>
        </div>
      )}

      {/* Modal Presupuesto */}
      {showPresupuestoModal && selectedProjectForPresupuesto && (
        <div className="fixed inset-0 bg-black/70 z-[1000] flex items-center justify-center p-4" data-testid="presupuesto-modal">
          <div className="bg-[#0B0B0F] border border-white/10 rounded-xl shadow-2xl w-full max-w-5xl max-h-[92vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <div className="flex items-center gap-3">
                <Wallet className="h-5 w-5 text-amber-400" />
                <div>
                  <h3 className="text-white font-semibold">Presupuesto del Proyecto</h3>
                  <p className="text-xs text-white/40">{selectedProjectForPresupuesto.nombre}</p>
                </div>
              </div>
              <button
                onClick={() => {
                  setShowPresupuestoModal(false);
                  setSelectedProjectForPresupuesto(null);
                  onRefresh?.();
                }}
                className="text-white/50 hover:text-white"
                data-testid="close-presupuesto-modal"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <PresupuestoSection
                proyecto={selectedProjectForPresupuesto}
                onShowSuccess={onShowSuccess}
                onProyectoUpdated={(updated) => {
                  setSelectedProjectForPresupuesto(updated);
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
