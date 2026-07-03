import { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, FileSpreadsheet, Check, AlertCircle, Loader2, Calendar, Layers, RefreshCw, X, Shovel, Anchor, Columns3, Building2, Clock, Download, TrendingDown, TrendingUp, Mail, AlertTriangle, Shield, ArrowRightLeft } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function CronogramaProyectoModal({ proyecto, onClose, onSuccess }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [cronogramaInfo, setCronogramaInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);
  const [analizandoDesviacion, setAnalizandoDesviacion] = useState(false);
  const [analisisDesviacion, setAnalisisDesviacion] = useState(null);
  const [tipoPilas, setTipoPilas] = useState('auto');
  const [reclasificando, setReclasificando] = useState(false);

  // Ocultar el mapa de Leaflet cuando el modal está abierto
  useEffect(() => {
    document.body.classList.add('modal-open');
    return () => {
      document.body.classList.remove('modal-open');
    };
  }, []);

  useEffect(() => {
    if (proyecto?.id) {
      fetchCronogramaInfo();
    }
  }, [proyecto?.id]);

  const handleDownloadTemplate = async () => {
    setDownloadingTemplate(true);
    try {
      const response = await axios.get(`${API}/plantilla-cronograma`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'plantilla_cronograma_dron.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error descargando plantilla:', err);
      setError('Error al descargar la plantilla');
    } finally {
      setDownloadingTemplate(false);
    }
  };

  const handleAnalizarDesviacion = async () => {
    setAnalizandoDesviacion(true);
    setError(null);
    try {
      const response = await axios.post(`${API}/proyectos/${proyecto.id}/analizar-desviacion`);
      setAnalisisDesviacion(response.data);
      if (response.data.alerta_enviada) {
        onSuccess && onSuccess('Análisis completado y alerta enviada por email');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al analizar desviación');
    } finally {
      setAnalizandoDesviacion(false);
    }
  };

  const handleReclasificarPilas = async () => {
    if (!window.confirm('¿Convertir todas las pilas de este proyecto a Reforzamiento (estabilización de colindancias)?\n\nEl plan de las tarjetas semanales, las metas y el % esperado se recalcularán a partir de las pilas de reforzamiento.')) return;
    setReclasificando(true);
    setError(null);
    try {
      const response = await axios.post(`${API}/proyectos/${proyecto.id}/reclasificar-pilas`);
      onSuccess && onSuccess(response.data.mensaje);
      await fetchCronogramaInfo();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al reclasificar las pilas');
    } finally {
      setReclasificando(false);
    }
  };

  const fetchCronogramaInfo = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/proyectos/${proyecto.id}/cronograma`);
      setCronogramaInfo(response.data);
      setShowUpload(!response.data.tiene_cronograma);
    } catch (err) {
      console.error('Error fetching cronograma:', err);
      setShowUpload(true);
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setUploading(true);
    setError(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('tipo_pilas', tipoPilas);
      
      const response = await axios.post(
        `${API}/proyectos/${proyecto.id}/actualizar-cronograma`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      
      if (response.data.success) {
        onSuccess && onSuccess(`Cronograma actualizado: ${response.data.mensaje}`);
        await fetchCronogramaInfo();
        setFile(null);
        setShowUpload(false);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al subir el cronograma');
    } finally {
      setUploading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'No definida';
    try {
      return new Date(dateStr).toLocaleDateString('es-MX', {
        year: 'numeric', month: 'short', day: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[1000] p-4">
      <div className="bg-[#15151B] rounded-xl shadow-xl w-full max-w-3xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="sticky top-0 bg-[#15151B] border-b border-white/10 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/15 rounded-lg">
              <FileSpreadsheet className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">Programa de Obra</h3>
              <p className="text-sm text-white/50">{proyecto?.nombre}</p>
            </div>
          </div>
          <button onClick={onClose} className="text-white/40 hover:text-white/60">
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
            </div>
          ) : (
            <div className="space-y-6">
              {/* Info del cronograma actual */}
              {cronogramaInfo?.tiene_cronograma && !showUpload && (
                <div className="space-y-4">
                  {/* Estado actual */}
                  <div className="bg-gradient-to-r from-purple-50 to-indigo-50 rounded-xl p-5 border border-purple-500/30">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <Check className="h-5 w-5 text-green-500" />
                        <span className="font-medium text-white">Cronograma Cargado</span>
                      </div>
                      <button
                        onClick={() => setShowUpload(true)}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                      >
                        <RefreshCw className="h-4 w-4" />
                        Actualizar
                      </button>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-white/50">Archivo:</span>
                        <p className="font-medium text-white">{cronogramaInfo.cronograma_archivo}</p>
                      </div>
                      <div>
                        <span className="text-white/50">Fecha de carga:</span>
                        <p className="font-medium text-white">{formatDate(cronogramaInfo.cronograma_fecha_carga)}</p>
                      </div>
                    </div>
                  </div>

                  {/* Resumen del cronograma */}
                  {cronogramaInfo.cronograma_resumen && (
                    <div className="bg-[#15151B] rounded-xl p-5 border border-white/10">
                      <h4 className="font-medium text-white mb-4 flex items-center gap-2">
                        <Clock className="h-5 w-5 text-purple-600" />
                        Resumen del Programa
                      </h4>
                      
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="bg-purple-500/10 rounded-lg p-3 text-center">
                          <p className="text-2xl font-bold text-purple-300">
                            {cronogramaInfo.semanas_planeadas || 0}
                          </p>
                          <p className="text-xs text-purple-600">Semanas</p>
                        </div>
                        
                        {cronogramaInfo.cronograma_resumen.total_pilas > 0 && (
                          <div className="bg-blue-500/10 rounded-lg p-3 text-center">
                            <p className="text-2xl font-bold text-blue-300">
                              {cronogramaInfo.cronograma_resumen.total_pilas}
                            </p>
                            <p className="text-xs text-blue-600">Pilas Cimentación</p>
                          </div>
                        )}

                        {cronogramaInfo.cronograma_resumen.total_perfiles > 0 && (
                          <div className="bg-emerald-500/10 rounded-lg p-3 text-center">
                            <p className="text-2xl font-bold text-emerald-300">
                              {cronogramaInfo.cronograma_resumen.total_perfiles}
                            </p>
                            <p className="text-xs text-emerald-600">Reforz. Perfiles</p>
                          </div>
                        )}
                        
                        {cronogramaInfo.cronograma_resumen.total_anclas > 0 && (
                          <div className="bg-teal-500/10 rounded-lg p-3 text-center">
                            <p className="text-2xl font-bold text-teal-300">
                              {cronogramaInfo.cronograma_resumen.total_anclas}
                            </p>
                            <p className="text-xs text-teal-600">Anclas</p>
                          </div>
                        )}
                        
                        {cronogramaInfo.cronograma_resumen.total_excavacion > 0 && (
                          <div className="bg-amber-500/10 rounded-lg p-3 text-center">
                            <p className="text-2xl font-bold text-amber-300">
                              {cronogramaInfo.cronograma_resumen.total_excavacion.toLocaleString()}
                            </p>
                            <p className="text-xs text-amber-600">m³ Excavación</p>
                          </div>
                        )}

                        {cronogramaInfo.cronograma_resumen.total_muros > 0 && (
                          <div className="bg-purple-500/10 rounded-lg p-3 text-center">
                            <p className="text-2xl font-bold text-purple-300">
                              {cronogramaInfo.cronograma_resumen.total_muros}
                            </p>
                            <p className="text-xs text-purple-600">Muros</p>
                          </div>
                        )}
                      </div>

                      <div className="mt-4 flex gap-4 text-sm text-white/60">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          Inicio: {formatDate(cronogramaInfo.fecha_inicio)}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          Fin: {formatDate(cronogramaInfo.fecha_fin_planeada)}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Reclasificar pilas existentes → Reforzamiento */}
                  {((cronogramaInfo?.cronograma_resumen?.total_pilas > 0) || (cronogramaInfo?.pilas_planeadas > 0)) && (
                    <div className="bg-[#15151B] rounded-xl p-5 border border-amber-500/30" data-testid="reclasificar-pilas-panel">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium text-white flex items-center gap-2">
                          <ArrowRightLeft className="h-5 w-5 text-amber-500" />
                          Reclasificar Pilas del Programa
                        </h4>
                        <button
                          onClick={handleReclasificarPilas}
                          disabled={reclasificando}
                          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50 transition-colors"
                          data-testid="btn-reclasificar-pilas"
                        >
                          {reclasificando ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Shield className="h-4 w-4" />
                          )}
                          Convertir a Reforzamiento
                        </button>
                      </div>
                      <p className="text-sm text-white/50">
                        Si las pilas detectadas en el programa son de <span className="text-amber-300 font-medium">reforzamiento de colindancias (estabilización)</span> y no de cimentación, usa este botón. El plan semanal, las metas y el % esperado se recalcularán como Reforz. Perfiles.
                      </p>
                    </div>
                  )}

                  {/* Análisis de Desviación del Cronograma */}
                  <div className="bg-[#15151B] rounded-xl p-5 border border-white/10">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="font-medium text-white flex items-center gap-2">
                        <TrendingDown className="h-5 w-5 text-orange-600" />
                        Análisis de Desviación
                      </h4>
                      <button
                        onClick={handleAnalizarDesviacion}
                        disabled={analizandoDesviacion}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 transition-colors"
                        data-testid="btn-analizar-desviacion"
                      >
                        {analizandoDesviacion ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Mail className="h-4 w-4" />
                        )}
                        Analizar y Alertar
                      </button>
                    </div>
                    
                    <p className="text-sm text-white/50 mb-4">
                      Compara el progreso real vs. el cronograma y envía alerta por email si hay desviaciones significativas (&gt;20%).
                    </p>

                    {/* Resultado del análisis */}
                    {analisisDesviacion && (
                      <div className="space-y-4 mt-4">
                        {/* Badge de estado */}
                        <div className={`p-4 rounded-lg border ${
                          analisisDesviacion.hay_desviacion_critica 
                            ? 'bg-red-500/10 border-red-500/30' 
                            : analisisDesviacion.hay_desviacion_moderada 
                              ? 'bg-amber-500/10 border-amber-500/30' 
                              : 'bg-green-500/10 border-green-500/30'
                        }`}>
                          <div className="flex items-center gap-2 mb-2">
                            {analisisDesviacion.hay_desviacion_critica ? (
                              <AlertTriangle className="h-5 w-5 text-red-600" />
                            ) : analisisDesviacion.hay_desviacion_moderada ? (
                              <AlertCircle className="h-5 w-5 text-amber-600" />
                            ) : (
                              <Check className="h-5 w-5 text-green-600" />
                            )}
                            <span className={`font-medium ${
                              analisisDesviacion.hay_desviacion_critica 
                                ? 'text-red-300' 
                                : analisisDesviacion.hay_desviacion_moderada 
                                  ? 'text-amber-300' 
                                  : 'text-green-300'
                            }`}>
                              {analisisDesviacion.hay_desviacion_critica 
                                ? 'Alerta Crítica' 
                                : analisisDesviacion.hay_desviacion_moderada 
                                  ? 'Alerta Moderada' 
                                  : 'Sin Desviaciones Críticas'}
                            </span>
                            {analisisDesviacion.alerta_enviada && (
                              <span className="ml-auto text-xs bg-blue-500/15 text-blue-300 px-2 py-0.5 rounded-full flex items-center gap-1">
                                <Mail className="h-3 w-3" />
                                Email enviado
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-white/60">
                            Semana {analisisDesviacion.semana_actual} de {analisisDesviacion.semanas_planeadas} | 
                            Progreso esperado: {analisisDesviacion.progreso_esperado}%
                          </p>
                        </div>

                        {/* Tabla de desviaciones */}
                        {analisisDesviacion.desviaciones && analisisDesviacion.desviaciones.length > 0 && (
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b border-white/10">
                                  <th className="text-left py-2 px-2 text-white/60 font-medium">Fase</th>
                                  <th className="text-right py-2 px-2 text-white/60 font-medium">Planeado</th>
                                  <th className="text-right py-2 px-2 text-white/60 font-medium">Real</th>
                                  <th className="text-right py-2 px-2 text-white/60 font-medium">Desviación</th>
                                </tr>
                              </thead>
                              <tbody>
                                {analisisDesviacion.desviaciones.map((d, idx) => (
                                  <tr key={idx} className="border-b border-white/5">
                                    <td className="py-2 px-2">{d.fase}</td>
                                    <td className="py-2 px-2 text-right text-white/50">{d.planeado?.toFixed(1)}%</td>
                                    <td className="py-2 px-2 text-right">{d.real?.toFixed(1)}%</td>
                                    <td className={`py-2 px-2 text-right font-medium ${
                                      d.desviacion_porcentaje < -20 ? 'text-red-600' :
                                      d.desviacion_porcentaje < -10 ? 'text-amber-600' :
                                      d.desviacion_porcentaje > 10 ? 'text-green-600' :
                                      'text-white/60'
                                    }`}>
                                      {d.desviacion_porcentaje > 0 ? '+' : ''}{d.desviacion_porcentaje?.toFixed(1)}%
                                      {d.desviacion_porcentaje < -10 && <TrendingDown className="inline h-4 w-4 ml-1" />}
                                      {d.desviacion_porcentaje > 10 && <TrendingUp className="inline h-4 w-4 ml-1" />}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Frentes */}
                  {cronogramaInfo.frentes && cronogramaInfo.frentes.length > 0 && (
                    <div className="bg-[#15151B] rounded-xl p-5 border border-white/10">
                      <h4 className="font-medium text-white mb-4 flex items-center gap-2">
                        <Layers className="h-5 w-5 text-purple-600" />
                        Frentes de Trabajo ({cronogramaInfo.frentes.length})
                      </h4>
                      
                      <div className="space-y-3 max-h-60 overflow-y-auto">
                        {cronogramaInfo.frentes.map((frente, idx) => (
                          <div key={frente.id || idx} className="border border-white/10 rounded-lg p-3">
                            <div className="flex justify-between items-start mb-2">
                              <h5 className="font-medium text-white">{frente.nombre}</h5>
                              <span className="text-xs bg-purple-500/15 text-purple-300 px-2 py-0.5 rounded">
                                {frente.actividades?.length || 0} actividades
                              </span>
                            </div>
                            {frente.actividades && frente.actividades.length > 0 && (
                              <div className="text-sm text-white/50 space-y-1">
                                {frente.actividades.slice(0, 2).map((act, i) => (
                                  <div key={i} className="flex justify-between items-center py-1 border-b border-white/5 last:border-0">
                                    <span className="truncate flex-1">{act.descripcion}</span>
                                    <span className={`ml-2 text-xs px-1.5 py-0.5 rounded ${
                                      act.tipo === 'pilas' ? 'bg-blue-500/15 text-blue-300' :
                                      act.tipo === 'excavacion' ? 'bg-amber-500/15 text-amber-300' :
                                      act.tipo === 'anclas' ? 'bg-teal-500/15 text-teal-300' :
                                      act.tipo === 'muros' ? 'bg-purple-500/15 text-purple-300' :
                                      act.tipo === 'perfiles' ? 'bg-emerald-500/15 text-emerald-300' :
                                      'bg-[#15151B] text-white/60'
                                    }`}>
                                      {act.tipo === 'perfiles' ? 'reforz.' : (act.tipo || 'otro')}
                                    </span>
                                  </div>
                                ))}
                                {frente.actividades.length > 2 && (
                                  <p className="text-xs text-white/40">
                                    +{frente.actividades.length - 2} más...
                                  </p>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Formulario de subida */}
              {(showUpload || !cronogramaInfo?.tiene_cronograma) && (
                <div className="space-y-4">
                  {cronogramaInfo?.tiene_cronograma && (
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium text-white">Actualizar Cronograma</h4>
                      <button
                        onClick={() => setShowUpload(false)}
                        className="text-sm text-white/50 hover:text-white/80"
                      >
                        Cancelar
                      </button>
                    </div>
                  )}

                  {/* Sección de Formato Esperado - Prominente */}
                  <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-500/30 rounded-xl">
                    <div className="flex items-start gap-4">
                      <div className="p-2 bg-blue-500/15 rounded-lg">
                        <FileSpreadsheet className="h-6 w-6 text-blue-600" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-white mb-1">Formato Esperado</h4>
                        <p className="text-sm text-white/60 mb-3">
                          El archivo Excel debe contener columnas para: 
                          <span className="font-medium"> Frente, Actividad, Cantidad, Tipo, Fecha Inicio, Fecha Fin</span>.
                        </p>
                        <div className="flex flex-wrap gap-2 mb-3">
                          <span className="text-xs bg-blue-500/15 text-blue-300 px-2 py-1 rounded">Pilas</span>
                          <span className="text-xs bg-amber-500/15 text-amber-300 px-2 py-1 rounded">Excavación</span>
                          <span className="text-xs bg-purple-500/15 text-purple-300 px-2 py-1 rounded">Muros</span>
                          <span className="text-xs bg-teal-500/15 text-teal-300 px-2 py-1 rounded">Anclas</span>
                        </div>
                        <button 
                          onClick={handleDownloadTemplate}
                          disabled={downloadingTemplate}
                          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                          data-testid="download-plantilla-btn"
                        >
                          {downloadingTemplate ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Download className="h-4 w-4" />
                          )}
                          Descargar Plantilla Excel
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors
                    ${file ? 'border-purple-400 bg-purple-500/10' : 'border-white/15 hover:border-purple-400'}`}>
                    <input
                      type="file"
                      accept=".xlsx,.xls"
                      onChange={handleFileChange}
                      className="hidden"
                      id="cronograma-upload"
                      disabled={uploading}
                    />
                    <label htmlFor="cronograma-upload" className="cursor-pointer">
                      {file ? (
                        <div className="flex flex-col items-center">
                          <FileSpreadsheet className="h-12 w-12 text-purple-600 mb-3" />
                          <p className="text-white font-medium">{file.name}</p>
                          <p className="text-sm text-white/50 mt-1">
                            {(file.size / 1024).toFixed(1)} KB
                          </p>
                        </div>
                      ) : (
                        <>
                          <Upload className="h-12 w-12 text-white/40 mx-auto mb-3" />
                          <p className="text-white/60 mb-1">
                            {cronogramaInfo?.tiene_cronograma 
                              ? 'Selecciona el nuevo archivo Excel' 
                              : 'Arrastra tu programa de obra aquí'}
                          </p>
                          <p className="text-sm text-white/40">o haz clic para seleccionar</p>
                          <p className="text-xs text-white/40 mt-2">Formatos: .xlsx, .xls</p>
                        </>
                      )}
                    </label>
                  </div>

                  {/* Error */}
                  {error && (
                    <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-start gap-3">
                      <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
                      <p className="text-red-300 text-sm">{error}</p>
                    </div>
                  )}

                  {/* Selector tipo de pilas */}
                  {file && (
                    <div className="p-4 bg-[#1A1A22] border border-white/10 rounded-xl space-y-3" data-testid="tipo-pilas-selector">
                      <p className="text-sm font-medium text-white">¿Las pilas del programa son de cimentación o de reforzamiento?</p>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                        {[
                          { v: 'auto', t: 'Ambas / Automático', d: 'La IA clasifica cada partida por su nombre' },
                          { v: 'cimentacion', t: 'Pilas de Cimentación', d: 'Todas son pilas estructurales' },
                          { v: 'reforzamiento', t: 'Pilas de Reforzamiento', d: 'Estabilización de colindancias' },
                        ].map(o => (
                          <button
                            key={o.v}
                            type="button"
                            onClick={() => setTipoPilas(o.v)}
                            data-testid={`tipo-pilas-${o.v}`}
                            className={`text-left p-3 rounded-lg border transition-colors ${tipoPilas === o.v ? 'border-purple-500 bg-purple-500/15' : 'border-white/10 hover:border-white/25'}`}
                          >
                            <p className="text-sm font-medium text-white">{o.t}</p>
                            <p className="text-xs text-white/50 mt-0.5">{o.d}</p>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Botón de subir */}
                  {file && (
                    <button
                      onClick={handleUpload}
                      disabled={uploading}
                      className="w-full py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                    >
                      {uploading ? (
                        <>
                          <Loader2 className="h-5 w-5 animate-spin" />
                          Subiendo cronograma...
                        </>
                      ) : (
                        <>
                          <Upload className="h-5 w-5" />
                          {cronogramaInfo?.tiene_cronograma ? 'Actualizar Programa de Obra' : 'Subir Programa de Obra'}
                        </>
                      )}
                    </button>
                  )}
                </div>
              )}

              {/* Estado vacío */}
              {!cronogramaInfo?.tiene_cronograma && !showUpload && (
                <div className="text-center py-8">
                  <FileSpreadsheet className="h-16 w-16 text-white/30 mx-auto mb-4" />
                  <p className="text-white/60 mb-2">No hay programa de obra cargado</p>
                  <p className="text-sm text-white/40 mb-4">
                    Sube un archivo Excel con el cronograma de actividades
                  </p>
                  <button
                    onClick={() => setShowUpload(true)}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                  >
                    Subir Programa de Obra
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
