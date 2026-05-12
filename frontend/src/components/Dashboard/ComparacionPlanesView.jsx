import { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis } from 'recharts';
import { Loader2, TrendingUp, TrendingDown, Minus, AlertCircle, CheckCircle2, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function ComparacionPlanesView({ proyectoId, proyectoNombre, onClose }) {
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [comparacion, setComparacion] = useState(null);
  const [error, setError] = useState(null);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    if (proyectoId) {
      fetchComparacion();
    }
  }, [proyectoId]);

  const fetchComparacion = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/proyectos/${proyectoId}/comparacion-planes`);
      setComparacion(response.data.comparacion);
    } catch (err) {
      console.error('Error fetching comparacion:', err);
    } finally {
      setLoading(false);
    }
  };

  const generarComparacion = async () => {
    try {
      setAnalyzing(true);
      setError(null);
      const response = await axios.post(`${API}/proyectos/${proyectoId}/comparar-plan-ia`);
      if (response.data.success) {
        setComparacion(response.data.comparacion);
      }
    } catch (err) {
      console.error('Error generating comparison:', err);
      setError(err.response?.data?.detail || 'Error al generar la comparación');
    } finally {
      setAnalyzing(false);
    }
  };

  // Preparar datos para gráfica de barras
  const prepareBarData = () => {
    if (!comparacion) return [];
    
    const usuario = comparacion.datos_usuario || {};
    const ia = comparacion.datos_ia || {};
    const real = comparacion.datos_reales || {};
    
    return [
      {
        fase: 'Excavación',
        'Tu Plan (semanas)': usuario.semanas_excavacion || 0,
        'Plan IA (semanas)': ia.semanas_excavacion || 0,
        'Real (semanas)': real.semanas_transcurridas || 0
      },
      {
        fase: 'Pilas',
        'Tu Plan (semanas)': usuario.semanas_pilas || 0,
        'Plan IA (semanas)': ia.semanas_pilas || 0,
        'Real (semanas)': 0
      },
      {
        fase: 'Anclas',
        'Tu Plan (semanas)': usuario.semanas_anclas || 0,
        'Plan IA (semanas)': ia.semanas_anclas || 0,
        'Real (semanas)': 0
      },
      {
        fase: 'TOTAL',
        'Tu Plan (semanas)': usuario.semanas_total || 0,
        'Plan IA (semanas)': ia.semanas_total || 0,
        'Real (semanas)': real.semanas_transcurridas || 0
      }
    ];
  };

  // Preparar datos para gráfica radar
  const prepareRadarData = () => {
    if (!comparacion) return [];
    
    const usuario = comparacion.datos_usuario || {};
    const ia = comparacion.datos_ia || {};
    
    // Normalizar a escala 0-100
    const maxSemanas = Math.max(
      usuario.semanas_total || 1,
      ia.semanas_total || 1
    );
    
    return [
      {
        metric: 'Tiempo Excavación',
        'Tu Plan': ((usuario.semanas_excavacion || 0) / maxSemanas) * 100,
        'Plan IA': ((ia.semanas_excavacion || 0) / maxSemanas) * 100,
      },
      {
        metric: 'Tiempo Pilas',
        'Tu Plan': ((usuario.semanas_pilas || 0) / maxSemanas) * 100,
        'Plan IA': ((ia.semanas_pilas || 0) / maxSemanas) * 100,
      },
      {
        metric: 'Tiempo Anclas',
        'Tu Plan': ((usuario.semanas_anclas || 0) / maxSemanas) * 100,
        'Plan IA': ((ia.semanas_anclas || 0) / maxSemanas) * 100,
      },
      {
        metric: 'Tiempo Total',
        'Tu Plan': ((usuario.semanas_total || 0) / maxSemanas) * 100,
        'Plan IA': ((ia.semanas_total || 0) / maxSemanas) * 100,
      }
    ];
  };

  const getVeredictoBadge = () => {
    const veredicto = comparacion?.analisis_ia?.veredicto;
    if (!veredicto) return null;
    
    if (veredicto === 'PLAN_IA_MEJOR') {
      return (
        <span className="flex items-center gap-1 px-3 py-1 bg-green-500/15 text-green-300 rounded-full text-sm font-medium">
          <TrendingUp className="h-4 w-4" />
          Plan IA es Mejor
        </span>
      );
    } else if (veredicto === 'PLAN_USUARIO_MEJOR') {
      return (
        <span className="flex items-center gap-1 px-3 py-1 bg-blue-500/15 text-blue-300 rounded-full text-sm font-medium">
          <CheckCircle2 className="h-4 w-4" />
          Tu Plan es Mejor
        </span>
      );
    } else {
      return (
        <span className="flex items-center gap-1 px-3 py-1 bg-[#15151B] text-white/80 rounded-full text-sm font-medium">
          <Minus className="h-4 w-4" />
          Planes Similares
        </span>
      );
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-[#994B49]" />
      </div>
    );
  }

  return (
    <div className="bg-[#15151B] rounded-xl shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-xl font-bold text-white">Comparación de Planes</h3>
          <p className="text-sm text-white/50">{proyectoNombre}</p>
        </div>
        <div className="flex items-center gap-3">
          {getVeredictoBadge()}
          <button
            onClick={generarComparacion}
            disabled={analyzing}
            className="flex items-center gap-2 px-4 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors disabled:opacity-50"
          >
            {analyzing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Analizando...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4" />
                {comparacion ? 'Actualizar Análisis' : 'Generar Comparación'}
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6 flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
          <p className="text-red-300 text-sm">{error}</p>
        </div>
      )}

      {!comparacion ? (
        <div className="text-center py-12 bg-[#0F0F14] rounded-lg">
          <TrendingUp className="h-12 w-12 text-white/40 mx-auto mb-4" />
          <p className="text-white/60 mb-2">No hay comparación disponible</p>
          <p className="text-sm text-white/50">
            Primero sube el catálogo de maquinaria y luego genera la comparación con tu cronograma.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Resumen */}
          {comparacion.analisis_ia?.resumen && (
            <div className="bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg p-4 border border-purple-500/30">
              <h4 className="font-medium text-purple-300 mb-2">📊 Resumen del Análisis IA</h4>
              <p className="text-white/80">{comparacion.analisis_ia.resumen}</p>
            </div>
          )}

          {/* Gráfica de Barras Comparativa */}
          <div className="bg-[#0F0F14] rounded-lg p-4">
            <h4 className="font-medium text-white mb-4">Comparación por Fase (Semanas)</h4>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={prepareBarData()} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="fase" />
                <YAxis label={{ value: 'Semanas', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="Tu Plan (semanas)" fill="#3B82F6" name="Tu Plan" />
                <Bar dataKey="Plan IA (semanas)" fill="#10B981" name="Plan IA" />
                <Bar dataKey="Real (semanas)" fill="#F59E0B" name="Avance Real" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Cards de Comparación por Fase */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Excavación */}
            <div className={`rounded-lg p-4 border ${
              comparacion.analisis_ia?.evaluacion_excavacion?.mejor_plan === 'ia' 
                ? 'bg-green-500/10 border-green-500/30' 
                : comparacion.analisis_ia?.evaluacion_excavacion?.mejor_plan === 'usuario'
                ? 'bg-blue-500/10 border-blue-500/30'
                : 'bg-[#0F0F14] border-white/10'
            }`}>
              <h5 className="font-medium text-white mb-2">🚜 Excavación</h5>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-white/60">Tu Plan:</span>
                  <span className="font-medium">{comparacion.datos_usuario?.semanas_excavacion || 0} sem</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-white/60">Plan IA:</span>
                  <span className="font-medium text-green-600">{comparacion.datos_ia?.semanas_excavacion || 0} sem</span>
                </div>
              </div>
              {comparacion.analisis_ia?.evaluacion_excavacion?.razon && (
                <p className="text-xs text-white/50 mt-2 italic">
                  {comparacion.analisis_ia.evaluacion_excavacion.razon}
                </p>
              )}
            </div>

            {/* Pilas */}
            <div className={`rounded-lg p-4 border ${
              comparacion.analisis_ia?.evaluacion_pilas?.mejor_plan === 'ia' 
                ? 'bg-green-500/10 border-green-500/30' 
                : comparacion.analisis_ia?.evaluacion_pilas?.mejor_plan === 'usuario'
                ? 'bg-blue-500/10 border-blue-500/30'
                : 'bg-[#0F0F14] border-white/10'
            }`}>
              <h5 className="font-medium text-white mb-2">🔩 Pilas</h5>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-white/60">Tu Plan:</span>
                  <span className="font-medium">{comparacion.datos_usuario?.semanas_pilas || 0} sem</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-white/60">Plan IA:</span>
                  <span className="font-medium text-green-600">{comparacion.datos_ia?.semanas_pilas || 0} sem</span>
                </div>
              </div>
              {comparacion.analisis_ia?.evaluacion_pilas?.razon && (
                <p className="text-xs text-white/50 mt-2 italic">
                  {comparacion.analisis_ia.evaluacion_pilas.razon}
                </p>
              )}
            </div>

            {/* Anclas */}
            <div className={`rounded-lg p-4 border ${
              comparacion.analisis_ia?.evaluacion_anclas?.mejor_plan === 'ia' 
                ? 'bg-green-500/10 border-green-500/30' 
                : comparacion.analisis_ia?.evaluacion_anclas?.mejor_plan === 'usuario'
                ? 'bg-blue-500/10 border-blue-500/30'
                : 'bg-[#0F0F14] border-white/10'
            }`}>
              <h5 className="font-medium text-white mb-2">⚓ Anclas</h5>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-white/60">Tu Plan:</span>
                  <span className="font-medium">{comparacion.datos_usuario?.semanas_anclas || 0} sem</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-white/60">Plan IA:</span>
                  <span className="font-medium text-green-600">{comparacion.datos_ia?.semanas_anclas || 0} sem</span>
                </div>
              </div>
              {comparacion.analisis_ia?.evaluacion_anclas?.razon && (
                <p className="text-xs text-white/50 mt-2 italic">
                  {comparacion.analisis_ia.evaluacion_anclas.razon}
                </p>
              )}
            </div>
          </div>

          {/* Total y Mejora */}
          <div className="bg-gradient-to-r from-[#994B49]/10 to-[#B85C5A]/10 rounded-lg p-4 border border-[#994B49]/20">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-blue-600">{comparacion.datos_usuario?.semanas_total || 0}</div>
                <div className="text-xs text-white/60">Tu Plan Total (sem)</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-green-600">{comparacion.datos_ia?.semanas_total?.toFixed(1) || 0}</div>
                <div className="text-xs text-white/60">Plan IA Total (sem)</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-amber-600">{comparacion.datos_reales?.semanas_transcurridas || 0}</div>
                <div className="text-xs text-white/60">Semanas Reales</div>
              </div>
              <div>
                <div className={`text-2xl font-bold ${
                  (comparacion.analisis_ia?.comparacion_general?.porcentaje_mejora || 0) > 0 
                    ? 'text-green-600' 
                    : 'text-red-600'
                }`}>
                  {comparacion.analisis_ia?.comparacion_general?.porcentaje_mejora 
                    ? `${comparacion.analisis_ia.comparacion_general.porcentaje_mejora > 0 ? '+' : ''}${comparacion.analisis_ia.comparacion_general.porcentaje_mejora}%`
                    : 'N/A'
                  }
                </div>
                <div className="text-xs text-white/60">Mejora IA vs Tu Plan</div>
              </div>
            </div>
          </div>

          {/* Recomendaciones */}
          {comparacion.analisis_ia?.recomendaciones?.length > 0 && (
            <div className="bg-amber-500/10 rounded-lg p-4 border border-amber-500/30">
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="w-full flex items-center justify-between"
              >
                <h4 className="font-medium text-amber-300">💡 Recomendaciones</h4>
                {showDetails ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
              </button>
              {showDetails && (
                <ul className="mt-3 space-y-2">
                  {comparacion.analisis_ia.recomendaciones.map((rec, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-white/80">
                      <span className="text-amber-500">•</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Fecha de última comparación */}
          {comparacion.fecha_comparacion && (
            <p className="text-xs text-white/40 text-right">
              Última comparación: {new Date(comparacion.fecha_comparacion).toLocaleString('es-MX')}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default ComparacionPlanesView;
