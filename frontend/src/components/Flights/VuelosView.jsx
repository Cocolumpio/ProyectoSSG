import { useState } from 'react';
import axios from 'axios';
import { Plane, Plus, Trash2, Pencil, X, Camera, Clock, Map } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function VuelosView({ vuelos, proyectos, onDelete, onRefresh }) {
  const [filtroProyecto, setFiltroProyecto] = useState('todos');
  const [showForm, setShowForm] = useState(false);
  const [editingVuelo, setEditingVuelo] = useState(null);
  const [formData, setFormData] = useState({
    proyecto_id: '', 
    fecha_vuelo: '', 
    duracion_minutos: 30, 
    area_cubierta: 1000, 
    num_imagenes: 100,
    pix4d_url: '', 
    notas: '', 
    estado: 'completado'
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const vuelosFiltrados = filtroProyecto === 'todos' ? vuelos : vuelos.filter(v => v.proyecto_id === filtroProyecto);
  const getProyectoNombre = (proyectoId) => proyectos.find(p => p.id === proyectoId)?.nombre || 'Proyecto desconocido';

  const resetForm = () => {
    setFormData({
      proyecto_id: proyectos.length > 0 ? proyectos[0].id : '', 
      fecha_vuelo: new Date().toISOString().split('T')[0],
      duracion_minutos: 30, 
      area_cubierta: 1000, 
      num_imagenes: 100,
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

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900">Bitácora de Vuelos</h2>
          <p className="text-sm text-gray-500">Registro de todos los vuelos de dron realizados</p>
        </div>
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
          <div className="bg-white rounded-xl shadow-xl w-full sm:max-w-lg max-h-[95vh] sm:max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
              <h3 className="text-lg sm:text-xl font-semibold text-gray-900">{editingVuelo ? 'Editar Vuelo' : 'Registrar Vuelo'}</h3>
              <button onClick={() => { setShowForm(false); setEditingVuelo(null); }} className="text-gray-400 hover:text-gray-600" data-testid="close-vuelo-modal">
                <X className="h-6 w-6" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-4 sm:p-6 space-y-4">
              {error && <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">{error}</div>}
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Proyecto *</label>
                <select name="proyecto_id" value={formData.proyecto_id} onChange={handleInputChange} required className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-proyecto-select">
                  <option value="">Seleccionar proyecto</option>
                  {proyectos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
                </select>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Fecha del Vuelo *</label>
                  <input type="date" name="fecha_vuelo" value={formData.fecha_vuelo} onChange={handleInputChange} required className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-fecha-input" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
                  <select name="estado" value={formData.estado} onChange={handleInputChange} className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-estado-select">
                    <option value="completado">Completado</option>
                    <option value="procesando">Procesando</option>
                    <option value="fallido">Fallido</option>
                  </select>
                </div>
              </div>
              
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <h4 className="font-medium text-gray-900 mb-3 flex items-center">
                  <Plane className="h-4 w-4 mr-2 text-[#994B49]" />
                  Datos del Vuelo
                </h4>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm text-gray-600 mb-1 flex items-center">
                      <Clock className="h-3 w-3 mr-1" />
                      Duración (min)
                    </label>
                    <input type="number" name="duracion_minutos" value={formData.duracion_minutos} onChange={handleInputChange} min="1" required className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-duracion-input" />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1 flex items-center">
                      <Map className="h-3 w-3 mr-1" />
                      Área (m²)
                    </label>
                    <input type="number" name="area_cubierta" value={formData.area_cubierta} onChange={handleInputChange} min="0" step="0.1" required className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-area-input" />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-600 mb-1 flex items-center">
                      <Camera className="h-3 w-3 mr-1" />
                      Fotos
                    </label>
                    <input type="number" name="num_imagenes" value={formData.num_imagenes} onChange={handleInputChange} min="0" required className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]" data-testid="vuelo-imagenes-input" />
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
                  {saving ? 'Guardando...' : (editingVuelo ? 'Guardar Cambios' : 'Registrar Vuelo')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Tabla de Vuelos - Bitácora */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full" data-testid="vuelos-full-table">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr className="text-gray-700 text-sm">
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6">Proyecto</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6">Fecha</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6">Duración</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6 hidden sm:table-cell">Área</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6 hidden md:table-cell">Fotos</th>
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
                  <td className="py-3 px-4 sm:py-4 sm:px-6">
                    <span className="flex items-center">
                      <Clock className="h-3 w-3 mr-1 text-gray-400" />
                      {vuelo.duracion_minutos} min
                    </span>
                  </td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6 hidden sm:table-cell">
                    <span className="flex items-center">
                      <Map className="h-3 w-3 mr-1 text-gray-400" />
                      {vuelo.area_cubierta?.toLocaleString() || 0} m²
                    </span>
                  </td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6 hidden md:table-cell">
                    <span className="flex items-center">
                      <Camera className="h-3 w-3 mr-1 text-gray-400" />
                      {vuelo.num_imagenes || 0}
                    </span>
                  </td>
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
          <p>No hay vuelos registrados.</p>
          <button onClick={() => { resetForm(); setShowForm(true); }} className="mt-4 text-[#994B49] hover:underline">Registrar primer vuelo</button>
        </div>
      )}
    </div>
  );
}
