import { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { Database, Upload, Plus, Trash2, Calendar, Layers, X, Download, Image, FileArchive, Pencil, Link, Check } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function AvancesSemanalesModal({ proyecto, onClose, onShowSuccess, readOnly = false }) {
  const [avances, setAvances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAvance, setSelectedAvance] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [editingLink, setEditingLink] = useState(false);
  const [editLinkValue, setEditLinkValue] = useState('');
  const [savingLink, setSavingLink] = useState(false);
  const [editingVolumen, setEditingVolumen] = useState(false);
  const [editVolumenValue, setEditVolumenValue] = useState(0);
  const [savingVolumen, setSavingVolumen] = useState(false);
  const [formData, setFormData] = useState({
    semana: 1,
    fecha: '',
    pix4d_url: '',
    descripcion: '',
    volumen_excavacion: 0
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadAvances = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${API}/proyectos/${proyecto.id}/avances-semanales`);
        setAvances(response.data);
        if (response.data.length > 0) {
          setSelectedAvance(response.data[response.data.length - 1]);
        }
      } catch (err) {
        console.error('Error cargando avances:', err);
      } finally {
        setLoading(false);
      }
    };
    loadAvances();
  }, [proyecto.id]);

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

  const handleAddAvance = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      await axios.post(`${API}/proyectos/${proyecto.id}/avances-semanales`, formData);
      setShowAddForm(false);
      setFormData({ semana: avances.length + 2, fecha: '', pix4d_url: '', descripcion: '', volumen_excavacion: 0 });
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

  const handleEditLinkClick = () => {
    setEditLinkValue(selectedAvance?.pix4d_url || '');
    setEditingLink(true);
  };

  const handleSaveLink = async () => {
    if (!selectedAvance) return;
    
    setSavingLink(true);
    try {
      await axios.put(`${API}/proyectos/${proyecto.id}/avances-semanales/${selectedAvance.id}`, {
        pix4d_url: editLinkValue
      });
      
      // Actualizar el avance seleccionado localmente
      const updatedAvance = { ...selectedAvance, pix4d_url: editLinkValue };
      setSelectedAvance(updatedAvance);
      setAvances(avances.map(a => a.id === selectedAvance.id ? updatedAvance : a));
      
      setEditingLink(false);
      if (onShowSuccess) {
        onShowSuccess(`Link de Pix4D actualizado para Semana ${selectedAvance.semana}`);
      }
    } catch (err) {
      console.error('Error actualizando link:', err);
      alert('Error al actualizar el link de Pix4D');
    } finally {
      setSavingLink(false);
    }
  };

  const handleCancelEditLink = () => {
    setEditingLink(false);
    setEditLinkValue('');
  };

  const handleEditVolumenClick = () => {
    setEditVolumenValue(selectedAvance?.volumen_excavacion || 0);
    setEditingVolumen(true);
  };

  const handleSaveVolumen = async () => {
    if (!selectedAvance) return;
    
    setSavingVolumen(true);
    try {
      await axios.put(`${API}/proyectos/${proyecto.id}/avances-semanales/${selectedAvance.id}`, {
        volumen_excavacion: editVolumenValue
      });
      
      // Actualizar el avance seleccionado localmente
      const updatedAvance = { ...selectedAvance, volumen_excavacion: editVolumenValue };
      setSelectedAvance(updatedAvance);
      setAvances(avances.map(a => a.id === selectedAvance.id ? updatedAvance : a));
      
      setEditingVolumen(false);
      if (onShowSuccess) {
        onShowSuccess(`Volumen actualizado para Semana ${selectedAvance.semana}`);
      }
    } catch (err) {
      console.error('Error actualizando volumen:', err);
      alert('Error al actualizar el volumen');
    } finally {
      setSavingVolumen(false);
    }
  };

  const handleCancelEditVolumen = () => {
    setEditingVolumen(false);
    setEditVolumenValue(0);
  };

  const handleImageUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !selectedAvance) return;

    setUploadingImage(true);
    try {
      for (const file of files) {
        const formDataUpload = new FormData();
        formDataUpload.append('file', file);
        
        await axios.post(
          `${API}/proyectos/${proyecto.id}/avances-semanales/${selectedAvance.id}/imagenes`,
          formDataUpload,
          { headers: { 'Content-Type': 'multipart/form-data' } }
        );
      }
      
      fetchAvances();
      if (onShowSuccess) {
        onShowSuccess(`${files.length} imagen(es) subida(s) correctamente`);
      }
    } catch (err) {
      console.error('Error subiendo imagen:', err);
    } finally {
      setUploadingImage(false);
      e.target.value = '';
    }
  };

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
            {!readOnly && (
              <div className="p-2 sm:p-4 border-b border-gray-200">
                <button
                  onClick={() => {
                    setFormData({ 
                      semana: avances.length + 1, 
                      fecha: new Date().toISOString().split('T')[0], 
                      pix4d_url: '', 
                      descripcion: '', 
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
            )}
            
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
                      {!readOnly && (
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
                      )}
                    </div>
                    <div className={`text-xs mt-1 ${selectedAvance?.id === avance.id ? 'text-white/70' : 'text-gray-500'}`}>
                      {avance.fecha}
                    </div>
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
                  </div>
                  {selectedAvance.descripcion && (
                    <p className="mt-2 text-xs sm:text-sm text-gray-600">{selectedAvance.descripcion}</p>
                  )}
                  
                  {/* Volumen excavado con edición inline */}
                  <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Database className="h-4 w-4 text-[#994B49]" />
                        <span className="text-sm font-medium text-gray-700">Volumen Excavado:</span>
                      </div>
                      {editingVolumen ? (
                        <div className="flex items-center space-x-2">
                          <input
                            type="number"
                            min="0"
                            step="0.1"
                            value={editVolumenValue}
                            onChange={(e) => setEditVolumenValue(parseFloat(e.target.value) || 0)}
                            className="w-32 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                            data-testid="edit-volumen-input"
                          />
                          <span className="text-sm text-gray-500">m³</span>
                          <button
                            onClick={handleSaveVolumen}
                            disabled={savingVolumen}
                            className="p-1.5 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 transition-colors"
                            title="Guardar"
                            data-testid="save-volumen-btn"
                          >
                            {savingVolumen ? (
                              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            ) : (
                              <Check className="h-4 w-4" />
                            )}
                          </button>
                          <button
                            onClick={handleCancelEditVolumen}
                            className="p-1.5 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors"
                            title="Cancelar"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center space-x-2">
                          <span className="text-lg font-bold text-[#994B49]" data-testid="volumen-value">
                            {(selectedAvance.volumen_excavacion || 0).toLocaleString()} m³
                          </span>
                          {!readOnly && (
                            <button
                              onClick={handleEditVolumenClick}
                              className="p-1.5 text-gray-500 hover:text-[#994B49] hover:bg-gray-200 rounded transition-colors"
                              title="Editar volumen"
                              data-testid="edit-volumen-btn"
                            >
                              <Pencil className="h-4 w-4" />
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Gráfico de Volumen - Progresión Lineal con Proyección */}
                {avances.length > 0 && (
                  <div className="p-2 sm:p-4 flex-shrink-0">
                    <div className="bg-white rounded-xl p-3 sm:p-4 shadow-sm">
                      {(() => {
                        // Calcular datos del gráfico con proyección
                        const sortedAvances = [...avances].sort((a, b) => a.semana - b.semana);
                        let acumulado = 0;
                        const chartData = sortedAvances.map(a => {
                          acumulado += (a.volumen_excavacion || 0);
                          return {
                            semana: `Sem ${a.semana}`,
                            semanaNum: a.semana,
                            volumen: a.volumen_excavacion || 0,
                            acumulado: acumulado,
                            proyeccion: null
                          };
                        });

                        // Calcular proyección si hay datos y meta
                        const totalExcavado = acumulado;
                        const semanasConDatos = sortedAvances.filter(a => a.volumen_excavacion > 0).length;
                        const ritmoSemanal = semanasConDatos > 0 ? totalExcavado / semanasConDatos : 0;
                        const metaVolumen = proyecto.volumen_total_planeado || 0;
                        
                        let semanasRestantes = 0;
                        let semanaMeta = null;
                        
                        if (ritmoSemanal > 0 && metaVolumen > 0 && totalExcavado < metaVolumen) {
                          semanasRestantes = Math.ceil((metaVolumen - totalExcavado) / ritmoSemanal);
                          const ultimaSemana = sortedAvances.length > 0 ? sortedAvances[sortedAvances.length - 1].semana : 0;
                          semanaMeta = ultimaSemana + semanasRestantes;
                          
                          // Agregar puntos de proyección
                          let proyeccionAcumulado = totalExcavado;
                          for (let i = 1; i <= Math.min(semanasRestantes, 8); i++) {
                            proyeccionAcumulado += ritmoSemanal;
                            if (proyeccionAcumulado > metaVolumen) proyeccionAcumulado = metaVolumen;
                            chartData.push({
                              semana: `Sem ${ultimaSemana + i}`,
                              semanaNum: ultimaSemana + i,
                              volumen: null,
                              acumulado: null,
                              proyeccion: proyeccionAcumulado
                            });
                            if (proyeccionAcumulado >= metaVolumen) break;
                          }
                          
                          // Agregar punto de conexión para la proyección
                          if (chartData.length > sortedAvances.length && sortedAvances.length > 0) {
                            chartData[sortedAvances.length - 1].proyeccion = totalExcavado;
                          }
                        }

                        return (
                          <>
                            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
                              <div className="flex items-center space-x-2">
                                <Database className="h-4 sm:h-5 w-4 sm:w-5 text-[#994B49]" />
                                <h5 className="font-semibold text-gray-900 text-sm sm:text-base">Progresión de Excavación</h5>
                              </div>
                              <div className="flex items-center gap-3 text-xs">
                                {metaVolumen > 0 && (
                                  <div className="text-gray-500">
                                    Meta: <span className="font-semibold text-green-600">{metaVolumen.toLocaleString()} m³</span>
                                  </div>
                                )}
                                {ritmoSemanal > 0 && semanasRestantes > 0 && (
                                  <div className="text-gray-500 bg-orange-50 px-2 py-1 rounded">
                                    📈 Ritmo: <span className="font-semibold text-orange-600">{ritmoSemanal.toLocaleString(undefined, {maximumFractionDigits: 0})} m³/sem</span>
                                    <span className="mx-1">•</span>
                                    Meta en: <span className="font-semibold text-orange-600">~{semanasRestantes} sem</span>
                                  </div>
                                )}
                                {totalExcavado >= metaVolumen && metaVolumen > 0 && (
                                  <div className="text-green-600 bg-green-50 px-2 py-1 rounded font-semibold">
                                    ✅ Meta alcanzada
                                  </div>
                                )}
                              </div>
                            </div>
                            <div className="h-[180px] sm:h-[220px]">
                              <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={chartData}>
                                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                                  <XAxis dataKey="semana" stroke="#6B7280" fontSize={11} />
                                  <YAxis 
                                    stroke="#6B7280" 
                                    fontSize={11} 
                                    domain={[0, metaVolumen > 0 ? metaVolumen * 1.05 : 'auto']}
                                    tickFormatter={(v) => v >= 1000 ? `${(v/1000).toFixed(1)}k` : v.toLocaleString()}
                                    label={{ value: 'm³', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle', fontSize: 10, fill: '#6B7280' } }}
                                  />
                                  <Tooltip 
                                    formatter={(value, name) => {
                                      if (value === null) return [null, null];
                                      const label = name === 'acumulado' ? 'Total Acumulado' : 
                                                   name === 'proyeccion' ? 'Proyección' : 'Esta Semana';
                                      return [`${value.toLocaleString(undefined, {maximumFractionDigits: 0})} m³`, label];
                                    }}
                                    contentStyle={{ backgroundColor: '#FFF', border: '1px solid #E5E7EB', borderRadius: '8px' }}
                                  />
                                  {metaVolumen > 0 && (
                                    <ReferenceLine 
                                      y={metaVolumen} 
                                      stroke="#22C55E" 
                                      strokeWidth={2}
                                      strokeDasharray="8 4"
                                      label={{ value: 'Meta', position: 'right', fill: '#22C55E', fontSize: 10 }}
                                    />
                                  )}
                                  <Line 
                                    type="monotone" 
                                    dataKey="acumulado" 
                                    stroke="#994B49" 
                                    strokeWidth={3}
                                    dot={{ fill: '#994B49', strokeWidth: 2, r: 5 }}
                                    activeDot={{ r: 7, fill: '#7D3C3A' }}
                                    name="acumulado"
                                    connectNulls={false}
                                  />
                                  <Line 
                                    type="monotone" 
                                    dataKey="proyeccion" 
                                    stroke="#F97316" 
                                    strokeWidth={2}
                                    strokeDasharray="6 3"
                                    dot={{ fill: '#F97316', strokeWidth: 2, r: 4 }}
                                    name="proyeccion"
                                    connectNulls={false}
                                  />
                                  <Line 
                                    type="monotone" 
                                    dataKey="volumen" 
                                    stroke="#60A5FA" 
                                    strokeWidth={2}
                                    strokeDasharray="5 5"
                                    dot={{ fill: '#60A5FA', strokeWidth: 2, r: 4 }}
                                    name="volumen"
                                    connectNulls={false}
                                  />
                                </LineChart>
                              </ResponsiveContainer>
                            </div>
                            <div className="flex items-center justify-center gap-3 sm:gap-5 mt-2 text-xs flex-wrap">
                              <div className="flex items-center gap-1.5">
                                <div className="w-4 h-0.5 bg-[#994B49]"></div>
                                <span className="text-gray-600">Acumulado</span>
                              </div>
                              <div className="flex items-center gap-1.5">
                                <div className="w-4 h-0.5 bg-blue-400"></div>
                                <span className="text-gray-600">Semanal</span>
                              </div>
                              {ritmoSemanal > 0 && semanasRestantes > 0 && (
                                <div className="flex items-center gap-1.5">
                                  <div className="w-4 h-0.5 bg-orange-500"></div>
                                  <span className="text-gray-600">Proyección</span>
                                </div>
                              )}
                              {metaVolumen > 0 && (
                                <div className="flex items-center gap-1.5">
                                  <div className="w-4 h-0.5 bg-green-500"></div>
                                  <span className="text-gray-600">Meta</span>
                                </div>
                              )}
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  </div>
                )}

                {/* Visor 3D */}
                <div className="p-2 sm:p-4 flex-shrink-0">
                  <div className="bg-white rounded-xl overflow-hidden shadow-sm">
                    {/* Header del visor con botón de editar link */}
                    <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100 bg-gray-50">
                      <div className="flex items-center space-x-2">
                        <Link className="h-4 w-4 text-gray-500" />
                        <span className="text-xs text-gray-500 truncate max-w-[200px] sm:max-w-[400px]">
                          {selectedAvance.pix4d_url || 'Sin URL de Pix4D'}
                        </span>
                      </div>
                      {!readOnly && (
                        <button
                          onClick={handleEditLinkClick}
                          className="flex items-center space-x-1 px-2 py-1 text-xs text-[#994B49] hover:bg-[#994B49]/10 rounded transition-colors"
                          title="Editar link de Pix4D"
                          data-testid="edit-pix4d-link-btn"
                        >
                          <Pencil className="h-3 w-3" />
                          <span className="hidden sm:inline">Editar Link</span>
                        </button>
                      )}
                    </div>
                    
                    {/* Modal de edición de link */}
                    {editingLink && (
                      <div className="px-3 py-3 bg-blue-50 border-b border-blue-100">
                        <label className="block text-xs font-medium text-blue-700 mb-1">
                          URL del Modelo Pix4D
                        </label>
                        <div className="flex items-center space-x-2">
                          <input
                            type="url"
                            value={editLinkValue}
                            onChange={(e) => setEditLinkValue(e.target.value)}
                            placeholder="https://cloud.pix4d.com/embed/..."
                            className="flex-1 px-3 py-2 text-sm border border-blue-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                            data-testid="pix4d-link-input"
                          />
                          <button
                            onClick={handleSaveLink}
                            disabled={savingLink}
                            className="px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                            title="Guardar"
                            data-testid="save-pix4d-link-btn"
                          >
                            {savingLink ? (
                              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            ) : (
                              <Check className="h-4 w-4" />
                            )}
                          </button>
                          <button
                            onClick={handleCancelEditLink}
                            className="px-3 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                            title="Cancelar"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    )}
                    
                    {/* Iframe del modelo */}
                    <div className="h-[200px] sm:h-[280px] md:h-[350px]">
                      {selectedAvance.pix4d_url ? (
                        <iframe
                          src={selectedAvance.pix4d_url}
                          className="w-full h-full border-0"
                          title={`Modelo 3D - Semana ${selectedAvance.semana}`}
                          allowFullScreen
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center bg-gray-100 text-gray-400">
                          <div className="text-center">
                            <Layers className="h-12 w-12 mx-auto mb-2" />
                            <p className="text-sm">No hay modelo 3D configurado</p>
                            {!readOnly && (
                              <button
                                onClick={handleEditLinkClick}
                                className="mt-2 text-[#994B49] hover:underline text-sm"
                              >
                                Agregar URL de Pix4D
                              </button>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
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
                        {!readOnly && (
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
                        )}
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
                                onClick={(e) => { e.stopPropagation(); handleDownloadImage(imageUrl, index); }}
                                className="p-2 bg-white rounded-full text-[#994B49] hover:bg-gray-100 mx-1"
                                title="Descargar"
                              >
                                <Download className="h-4 w-4" />
                              </button>
                              {!readOnly && (
                                <button
                                  onClick={(e) => { e.stopPropagation(); handleDeleteImage(imageUrl); }}
                                  className="p-2 bg-white rounded-full text-red-600 hover:bg-gray-100 mx-1"
                                  title="Eliminar"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </button>
                              )}
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
          <div className="absolute inset-0 bg-black/90 flex items-center justify-center z-20" onClick={() => setSelectedImage(null)}>
            <button onClick={() => setSelectedImage(null)} className="absolute top-4 right-4 text-white/80 hover:text-white p-2">
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
                  onClick={(e) => { e.stopPropagation(); handleDownloadImage(selectedImage.url, selectedImage.index); }}
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
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">Volumen Excavado (m³) *</label>
                  <div className="relative">
                    <input
                      type="number"
                      min="0"
                      step="0.1"
                      value={formData.volumen_excavacion}
                      onChange={(e) => setFormData(prev => ({ ...prev, volumen_excavacion: parseFloat(e.target.value) || 0 }))}
                      required
                      className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                      placeholder="Ej: 3500"
                      data-testid="avance-volumen-input"
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">m³</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Volumen de material excavado esta semana</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">URL del Modelo 3D (Pix4D)</label>
                  <input
                    type="url"
                    value={formData.pix4d_url}
                    onChange={(e) => setFormData(prev => ({ ...prev, pix4d_url: e.target.value }))}
                    placeholder="https://cloud.pix4d.com/embed/..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                    data-testid="avance-pix4d-input"
                  />
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
                  <button type="button" onClick={() => setShowAddForm(false)} className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors">
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
