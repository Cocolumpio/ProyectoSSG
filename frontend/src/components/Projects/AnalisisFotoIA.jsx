import { useState } from 'react';
import axios from 'axios';
import { Camera, Loader2, CheckCircle, AlertTriangle, TrendingUp, TrendingDown, Minus, Eye, Anchor } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function AnalisisFotoIA({ avanceId, proyectoId, semana, onAnalisisCompleto }) {
  const [imagen, setImagen] = useState(null);
  const [imagenPreview, setImagenPreview] = useState(null);
  const [analizando, setAnalizando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);

  const handleImagenChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setImagenPreview(reader.result);
      // Guardar base64 sin el prefijo
      const base64 = reader.result.split(',')[1];
      setImagen(base64);
    };
    reader.readAsDataURL(file);
    setResultado(null);
    setError(null);
  };

  const handleAnalizar = async () => {
    if (!imagen) return;
    
    setAnalizando(true);
    setError(null);
    
    try {
      const response = await axios.post(`${API}/avances/${avanceId}/analizar-foto`, {
        imagen_base64: imagen
      });
      
      setResultado(response.data);
      onAnalisisCompleto && onAnalisisCompleto(response.data);
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al analizar la imagen');
    } finally {
      setAnalizando(false);
    }
  };

  const getEstadoIcon = (estado) => {
    switch (estado) {
      case 'ADELANTADO':
        return <TrendingUp className="h-5 w-5 text-green-500" />;
      case 'RETRASADO':
        return <TrendingDown className="h-5 w-5 text-red-500" />;
      default:
        return <Minus className="h-5 w-5 text-blue-500" />;
    }
  };

  const getEstadoColor = (estado) => {
    switch (estado) {
      case 'ADELANTADO':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'RETRASADO':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-blue-100 text-blue-800 border-blue-200';
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 bg-purple-100 rounded-lg">
          <Eye className="h-6 w-6 text-purple-600" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-gray-900">Análisis con IA</h3>
          <p className="text-sm text-gray-500">Detecta pilas y anclas automáticamente</p>
        </div>
      </div>

      {/* Upload Area */}
      <div className="mb-6">
        <label className="block cursor-pointer">
          <div className={`border-2 border-dashed rounded-xl overflow-hidden transition-colors
            ${imagenPreview ? 'border-purple-400' : 'border-gray-300 hover:border-purple-400'}`}>
            {imagenPreview ? (
              <div className="relative">
                <img 
                  src={imagenPreview} 
                  alt="Preview" 
                  className="w-full h-48 object-cover"
                />
                <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                  <p className="text-white text-sm">Clic para cambiar imagen</p>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center">
                <Camera className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-600">Sube una foto aérea del sitio</p>
                <p className="text-xs text-gray-400 mt-1">JPG, PNG (máx 10MB)</p>
              </div>
            )}
          </div>
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleImagenChange}
            className="hidden"
          />
        </label>
      </div>

      {/* Analyze Button */}
      {imagen && !resultado && (
        <button
          onClick={handleAnalizar}
          disabled={analizando}
          className="w-full py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {analizando ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Analizando con IA...
            </>
          ) : (
            <>
              <Eye className="h-5 w-5" />
              Analizar Imagen
            </>
          )}
        </button>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      )}

      {/* Results */}
      {resultado && resultado.success && (
        <div className="mt-6 space-y-4">
          {/* Estado General */}
          <div className={`p-4 rounded-lg border ${getEstadoColor(resultado.estado_proyecto)}`}>
            <div className="flex items-center gap-2">
              {getEstadoIcon(resultado.estado_proyecto)}
              <span className="font-semibold">
                {resultado.estado_proyecto === 'EN_TIEMPO' && 'Proyecto en Tiempo'}
                {resultado.estado_proyecto === 'ADELANTADO' && 'Proyecto Adelantado'}
                {resultado.estado_proyecto === 'RETRASADO' && 'Proyecto Retrasado'}
              </span>
            </div>
            <p className="text-sm mt-1 opacity-80">
              Confianza de detección: {resultado.confianza_deteccion}
            </p>
          </div>

          {/* Métricas */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 border border-blue-200">
              <div className="flex items-center gap-2 mb-2">
                <div className="p-2 bg-blue-500 rounded-lg">
                  <CheckCircle className="h-4 w-4 text-white" />
                </div>
                <span className="text-sm font-medium text-blue-800">Pilas Detectadas</span>
              </div>
              <p className="text-3xl font-bold text-blue-700">{resultado.pilas_detectadas}</p>
              {resultado.pilas_en_proceso > 0 && (
                <p className="text-xs text-blue-600 mt-1">
                  +{resultado.pilas_en_proceso} en proceso
                </p>
              )}
            </div>

            <div className="bg-gradient-to-br from-amber-50 to-amber-100 rounded-lg p-4 border border-amber-200">
              <div className="flex items-center gap-2 mb-2">
                <div className="p-2 bg-amber-500 rounded-lg">
                  <Anchor className="h-4 w-4 text-white" />
                </div>
                <span className="text-sm font-medium text-amber-800">Anclas Detectadas</span>
              </div>
              <p className="text-3xl font-bold text-amber-700">{resultado.anclas_detectadas}</p>
            </div>
          </div>

          {/* Porcentaje de Avance */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-gray-700">Avance Estimado por IA</span>
              <span className="text-lg font-bold text-[#994B49]">
                {resultado.porcentaje_avance_estimado}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div 
                className="bg-[#994B49] h-3 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(resultado.porcentaje_avance_estimado, 100)}%` }}
              />
            </div>
          </div>

          {/* Observaciones */}
          {resultado.observaciones && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">Observaciones</h4>
              <p className="text-sm text-gray-600">{resultado.observaciones}</p>
            </div>
          )}

          {/* Recomendaciones */}
          {resultado.recomendaciones && (
            <div className="bg-amber-50 rounded-lg p-4 border border-amber-200">
              <h4 className="text-sm font-semibold text-amber-800 mb-2 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                Recomendaciones
              </h4>
              <p className="text-sm text-amber-700">{resultado.recomendaciones}</p>
            </div>
          )}

          {/* Nuevo análisis */}
          <button
            onClick={() => {
              setImagen(null);
              setImagenPreview(null);
              setResultado(null);
            }}
            className="w-full py-2 text-purple-600 hover:text-purple-700 text-sm"
          >
            Analizar otra imagen
          </button>
        </div>
      )}
    </div>
  );
}
