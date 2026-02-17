import { useState, useEffect } from 'react';
import axios from 'axios';
import { FileText, Upload, CheckCircle, AlertTriangle, XCircle, X, Download, Trash2, RefreshCw, ArrowUpDown, TrendingUp, TrendingDown, Minus, FileWarning, Loader2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function ComparacionAvanceModal({ proyecto, onClose, onShowSuccess }) {
  const [comparaciones, setComparaciones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedComparacion, setSelectedComparacion] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadComparaciones();
  }, [proyecto.id]);

  const loadComparaciones = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/proyectos/${proyecto.id}/comparaciones`);
      setComparaciones(response.data);
      if (response.data.length > 0) {
        setSelectedComparacion(response.data[0]);
      }
    } catch (err) {
      console.error('Error cargando comparaciones:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Solo se aceptan archivos PDF');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(
        `${API}/proyectos/${proyecto.id}/comparar-avance`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );

      setComparaciones([response.data, ...comparaciones]);
      setSelectedComparacion(response.data);
      
      if (onShowSuccess) {
        if (response.data.alerta_enviada) {
          onShowSuccess('Análisis completado. ⚠️ Alerta enviada al administrador por discrepancias críticas');
        } else {
          onShowSuccess('Análisis de comparación completado');
        }
      }
    } catch (err) {
      console.error('Error subiendo PDF:', err);
      setError(err.response?.data?.detail || 'Error al analizar el PDF');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleDeleteComparacion = async (comparacionId) => {
    if (!window.confirm('¿Eliminar esta comparación?')) return;

    try {
      await axios.delete(`${API}/proyectos/${proyecto.id}/comparaciones/${comparacionId}`);
      setComparaciones(comparaciones.filter(c => c.id !== comparacionId));
      if (selectedComparacion?.id === comparacionId) {
        setSelectedComparacion(comparaciones.length > 1 ? comparaciones[1] : null);
      }
    } catch (err) {
      console.error('Error eliminando comparación:', err);
    }
  };

  const getEstadoIcon = (estado) => {
    switch (estado) {
      case 'coincide':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'discrepancia_menor':
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case 'discrepancia_mayor':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Minus className="h-5 w-5 text-gray-400" />;
    }
  };

  const getEstadoColor = (estado) => {
    switch (estado) {
      case 'coincide':
        return 'bg-green-50 border-green-200';
      case 'discrepancia_menor':
        return 'bg-yellow-50 border-yellow-200';
      case 'discrepancia_mayor':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const getDiferenciaIcon = (diferencia) => {
    if (diferencia > 0) return <TrendingUp className="h-4 w-4 text-green-600" />;
    if (diferencia < 0) return <TrendingDown className="h-4 w-4 text-red-600" />;
    return <Minus className="h-4 w-4 text-gray-400" />;
  };

  const formatNumber = (num) => {
    if (num === null || num === undefined) return '-';
    return num.toLocaleString('es-MX', { maximumFractionDigits: 2 });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div 
        className="bg-white rounded-xl w-[95vw] max-w-6xl max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-[#994B49] to-[#B85C5A] text-white px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2">
              <ArrowUpDown className="h-6 w-6" />
              Comparación de Avances: Dron vs Residente
            </h2>
            <p className="text-white/80 text-sm">{proyecto.nombre}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/20 rounded-lg transition-colors">
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="flex-1 overflow-hidden flex">
          {/* Sidebar - Lista de comparaciones */}
          <div className="w-72 border-r border-gray-200 flex flex-col">
            {/* Upload Button */}
            <div className="p-4 border-b border-gray-200">
              <label className={`flex items-center justify-center gap-2 px-4 py-3 rounded-lg cursor-pointer transition-all ${
                uploading 
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
                  : 'bg-[#994B49] hover:bg-[#B85C5A] text-white'
              }`}>
                {uploading ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    Analizando PDF...
                  </>
                ) : (
                  <>
                    <Upload className="h-5 w-5" />
                    Subir Reporte del Residente
                  </>
                )}
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileUpload}
                  disabled={uploading}
                  className="hidden"
                />
              </label>
              {error && (
                <p className="text-red-500 text-xs mt-2 flex items-center gap-1">
                  <FileWarning className="h-4 w-4" />
                  {error}
                </p>
              )}
            </div>

            {/* Lista de comparaciones */}
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-[#994B49]" />
                </div>
              ) : comparaciones.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <FileText className="h-12 w-12 mx-auto mb-2 text-gray-300" />
                  <p className="text-sm">Sin comparaciones</p>
                  <p className="text-xs">Sube un PDF para comenzar</p>
                </div>
              ) : (
                comparaciones.map((comp) => (
                  <div
                    key={comp.id}
                    onClick={() => setSelectedComparacion(comp)}
                    className={`p-3 rounded-lg cursor-pointer transition-all ${
                      selectedComparacion?.id === comp.id
                        ? 'bg-[#994B49]/10 border-2 border-[#994B49]'
                        : 'bg-gray-50 border border-gray-200 hover:bg-gray-100'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm text-gray-900 truncate">
                          {comp.pdf_nombre}
                        </p>
                        <p className="text-xs text-gray-500">
                          {new Date(comp.fecha_comparacion).toLocaleDateString('es-MX')}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteComparacion(comp.id);
                        }}
                        className="p-1 hover:bg-red-100 rounded text-gray-400 hover:text-red-500"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                    <div className="mt-2 flex items-center gap-2 flex-wrap">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        comp.confianza === 'ALTA' ? 'bg-green-100 text-green-700' :
                        comp.confianza === 'MEDIA' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-red-100 text-red-700'
                      }`}>
                        {comp.confianza || 'MEDIA'}
                      </span>
                      <span className="text-xs text-gray-500">
                        {comp.comparaciones?.length || 0} métricas
                      </span>
                      {comp.alerta_enviada && (
                        <span className="px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-700">
                          📧 Alerta
                        </span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Main Content - Detalle de comparación */}
          <div className="flex-1 overflow-y-auto p-6">
            {selectedComparacion ? (
              <div className="space-y-6">
                {/* Resumen de avance general */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-blue-50 rounded-xl p-4 border border-blue-200">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                      <span className="text-sm font-medium text-blue-800">Avance Dron (Sistema)</span>
                    </div>
                    <div className="text-3xl font-bold text-blue-700">
                      {formatNumber(selectedComparacion.avance_general_dron)}%
                    </div>
                    <p className="text-xs text-blue-600 mt-1">
                      Basado en {selectedComparacion.metricas_dron?.semanas_registradas || 0} semanas registradas
                    </p>
                  </div>
                  <div className="bg-amber-50 rounded-xl p-4 border border-amber-200">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-3 h-3 bg-amber-500 rounded-full"></div>
                      <span className="text-sm font-medium text-amber-800">Avance Residente (PDF)</span>
                    </div>
                    <div className="text-3xl font-bold text-amber-700">
                      {formatNumber(selectedComparacion.avance_general_residente)}%
                    </div>
                    <p className="text-xs text-amber-600 mt-1">
                      Según reporte: {selectedComparacion.pdf_nombre}
                    </p>
                  </div>
                </div>

                {/* Tabla de comparación */}
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                  <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                    <h3 className="font-semibold text-gray-900">Comparación por Métrica</h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50 border-b border-gray-200">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Métrica</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-blue-500 uppercase">Dron</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-amber-500 uppercase">Residente</th>
                          <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Diferencia</th>
                          <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Estado</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {selectedComparacion.comparaciones?.map((comp, idx) => (
                          <tr key={idx} className={getEstadoColor(comp.estado)}>
                            <td className="px-4 py-3">
                              <span className="font-medium text-gray-900">{comp.nombre}</span>
                              <span className="text-xs text-gray-500 ml-1">({comp.unidad})</span>
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-blue-700">
                              {formatNumber(comp.valor_dron)}
                            </td>
                            <td className="px-4 py-3 text-right font-mono text-amber-700">
                              {formatNumber(comp.valor_residente)}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <div className="flex items-center justify-end gap-1">
                                {getDiferenciaIcon(comp.diferencia)}
                                <span className={`font-mono ${
                                  comp.diferencia > 0 ? 'text-green-600' : 
                                  comp.diferencia < 0 ? 'text-red-600' : 'text-gray-500'
                                }`}>
                                  {comp.diferencia > 0 ? '+' : ''}{formatNumber(comp.diferencia)}
                                  <span className="text-xs ml-1">
                                    ({comp.diferencia_porcentaje > 0 ? '+' : ''}{formatNumber(comp.diferencia_porcentaje)}%)
                                  </span>
                                </span>
                              </div>
                            </td>
                            <td className="px-4 py-3 text-center">
                              {getEstadoIcon(comp.estado)}
                            </td>
                          </tr>
                        ))}
                        {(!selectedComparacion.comparaciones || selectedComparacion.comparaciones.length === 0) && (
                          <tr>
                            <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                              No se pudieron extraer métricas comparables del PDF
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Discrepancias detectadas */}
                {selectedComparacion.discrepancias_detectadas?.length > 0 && (
                  <div className="bg-red-50 rounded-xl p-4 border border-red-200">
                    <h3 className="font-semibold text-red-800 flex items-center gap-2 mb-3">
                      <AlertTriangle className="h-5 w-5" />
                      Discrepancias Detectadas
                    </h3>
                    <ul className="space-y-2">
                      {selectedComparacion.discrepancias_detectadas.map((disc, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm text-red-700">
                          <span className="text-red-400 mt-0.5">•</span>
                          {disc}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Análisis de IA */}
                {selectedComparacion.resumen_ia && (
                  <div className="bg-purple-50 rounded-xl p-4 border border-purple-200">
                    <h3 className="font-semibold text-purple-800 mb-3">Análisis de IA</h3>
                    <p className="text-sm text-purple-700 whitespace-pre-wrap">
                      {selectedComparacion.resumen_ia}
                    </p>
                  </div>
                )}

                {/* Recomendaciones */}
                {selectedComparacion.recomendaciones?.length > 0 && (
                  <div className="bg-green-50 rounded-xl p-4 border border-green-200">
                    <h3 className="font-semibold text-green-800 flex items-center gap-2 mb-3">
                      <CheckCircle className="h-5 w-5" />
                      Recomendaciones
                    </h3>
                    <ul className="space-y-2">
                      {selectedComparacion.recomendaciones.map((rec, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm text-green-700">
                          <span className="text-green-400 mt-0.5">✓</span>
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Ver PDF original */}
                <div className="flex justify-end">
                  <a
                    href={`${process.env.REACT_APP_BACKEND_URL}${selectedComparacion.pdf_url}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
                  >
                    <Download className="h-4 w-4" />
                    Ver PDF Original
                  </a>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <FileText className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                  <p className="text-lg font-medium">Sin comparación seleccionada</p>
                  <p className="text-sm">Sube un PDF del reporte del residente para analizar</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
