import { useState } from 'react';
import axios from 'axios';
import { Building2, Plus, Eye, Trash2, Pencil, Layers, X, FileText } from 'lucide-react';
import { ProjectFormContent } from './ProjectFormContent';
import { AvancesSemanalesModal } from './AvancesSemanalesModal';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function ProyectosView({ proyectos, onDelete, onSelect, onRefresh, onShowSuccess }) {
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
