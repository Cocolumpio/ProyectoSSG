import { useState, useRef } from 'react';
import axios from 'axios';
import { Upload, Loader2, Truck, Wrench, AlertCircle, CheckCircle, ChevronDown, ChevronUp, FileSpreadsheet, Zap, Clock, MapPin, Info } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function CatalogoMaquinariaSection({ formData, setFormData, onShowSuccess }) {
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [catalogoData, setCatalogoData] = useState(null);
  const [analisisIA, setAnalisisIA] = useState(null);
  const [error, setError] = useState(null);
  const [showAnalisis, setShowAnalisis] = useState(false);
  const [showMaquinas, setShowMaquinas] = useState(false);
  const fileInputRef = useRef(null);

  // Parámetros del proyecto para el análisis - sincronizados con formData
  const [parametros, setParametros] = useState({
    area_terreno: formData.area_terreno || 0,
    espacio_maniobra: formData.espacio_maniobra || 0,
    volumen_excavacion: formData.volumen_total_planeado || 0,
    num_pilas: formData.pilas_planeadas || 0,
    distancia_pilas: formData.distancia_pilas || 3
  });

  // Guardar parámetros en formData cuando cambian
  const handleParametroChange = (field, value) => {
    const newParametros = { ...parametros, [field]: value };
    setParametros(newParametros);
    
    // También actualizar el formData del proyecto
    setFormData(prev => ({
      ...prev,
      area_terreno: newParametros.area_terreno,
      espacio_maniobra: newParametros.espacio_maniobra,
      distancia_pilas: newParametros.distancia_pilas,
      parametros_proyecto: newParametros
    }));
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      setError('Por favor selecciona un archivo Excel (.xlsx o .xls)');
      return;
    }

    setUploading(true);
    setAnalyzing(true);
    setError(null);

    try {
      const formDataFile = new FormData();
      formDataFile.append('file', file);
      
      // Agregar parámetros del proyecto
      const queryParams = new URLSearchParams({
        area_terreno: parametros.area_terreno || 0,
        volumen_excavacion: parametros.volumen_excavacion || formData.volumen_total_planeado || 0,
        num_pilas: parametros.num_pilas || formData.pilas_planeadas || 0,
        distancia_pilas: parametros.distancia_pilas || 3,
        espacio_maniobra: parametros.espacio_maniobra || 0
      });

      const response = await axios.post(
        `${API}/proyectos/analizar-catalogo-maquinaria?${queryParams.toString()}`,
        formDataFile,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );

      if (response.data.success) {
        setCatalogoData({
          total: response.data.total_maquinas,
          disponibles: response.data.maquinas_disponibles,
          resumen: response.data.resumen_catalogo,
          maquinas: response.data.maquinas_raw
        });
        
        if (response.data.analisis_ia) {
          setAnalisisIA(response.data.analisis_ia);
          setShowAnalisis(true); // Expandir automáticamente el análisis
        } else if (response.data.analisis_ia_texto) {
          setAnalisisIA({ resumen_ejecutivo: response.data.analisis_ia_texto });
          setShowAnalisis(true);
        }

        // Guardar en formData
        setFormData(prev => ({
          ...prev,
          catalogo_maquinaria: response.data.maquinas_raw,
          analisis_maquinaria_ia: response.data.analisis_ia || null,
          parametros_proyecto: parametros
        }));

        if (onShowSuccess) {
          onShowSuccess(`Catálogo analizado: ${response.data.maquinas_disponibles} máquinas disponibles`);
        }
      } else {
        setError(response.data.error || 'Error al analizar el catálogo');
      }
    } catch (err) {
      console.error('Error:', err);
      setError(err.response?.data?.detail || 'Error al procesar el archivo');
    } finally {
      setUploading(false);
      setAnalyzing(false);
    }
  };

  const getMaquinaIcon = (tipo) => {
    const tipoUpper = tipo?.toUpperCase() || '';
    if (tipoUpper.includes('EXCAVADORA')) return '🚜';
    if (tipoUpper.includes('PERFORADORA')) return '🔩';
    if (tipoUpper.includes('GRUA')) return '🏗️';
    if (tipoUpper.includes('MANIPULADOR')) return '🦾';
    return '⚙️';
  };

  const getEstatusColor = (estatus) => {
    const estatusUpper = estatus?.toUpperCase() || '';
    if (estatusUpper.includes('OPTIMA')) return 'bg-green-500/15 text-green-300';
    if (estatusUpper.includes('SATISFACTORIO')) return 'bg-blue-500/15 text-blue-300';
    if (estatusUpper.includes('DESHABILITADA') || estatusUpper.includes('REPARACION')) return 'bg-red-500/15 text-red-300';
    return 'bg-[#15151B] text-white/80';
  };

  return (
    <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl p-4 border border-indigo-500/30">
      <div className="flex items-center gap-2 mb-4">
        <Truck className="h-5 w-5 text-indigo-300" />
        <h4 className="font-semibold text-indigo-200">Catálogo de Maquinaria</h4>
        <span className="text-xs text-indigo-500 bg-[#15151B] px-2 py-0.5 rounded">Análisis con IA</span>
      </div>

      {/* Parámetros del proyecto para análisis */}
      <div className="bg-[#15151B] rounded-lg p-4 mb-4 border border-indigo-100">
        <div className="flex items-center gap-2 mb-3">
          <MapPin className="h-4 w-4 text-indigo-600" />
          <span className="text-sm font-medium text-white/80">Parámetros del Terreno</span>
          <span className="text-xs text-white/40">(se guardan con el proyecto)</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs text-white/60 mb-1">Área del Terreno (m²)</label>
            <input
              type="number"
              min="0"
              value={parametros.area_terreno}
              onChange={(e) => handleParametroChange('area_terreno', parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-1.5 text-sm border border-white/10 rounded-lg focus:ring-2 focus:ring-indigo-500"
              placeholder="5000"
              data-testid="area-terreno-input"
            />
          </div>
          <div>
            <label className="block text-xs text-white/60 mb-1">Espacio de Maniobra (m²)</label>
            <input
              type="number"
              min="0"
              value={parametros.espacio_maniobra}
              onChange={(e) => handleParametroChange('espacio_maniobra', parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-1.5 text-sm border border-white/10 rounded-lg focus:ring-2 focus:ring-indigo-500"
              placeholder="1000"
              data-testid="espacio-maniobra-input"
            />
          </div>
          <div>
            <label className="block text-xs text-white/60 mb-1">Distancia entre Pilas (m)</label>
            <input
              type="number"
              min="0"
              step="0.5"
              value={parametros.distancia_pilas}
              onChange={(e) => handleParametroChange('distancia_pilas', parseFloat(e.target.value) || 3)}
              className="w-full px-3 py-1.5 text-sm border border-white/10 rounded-lg focus:ring-2 focus:ring-indigo-500"
              placeholder="3"
              data-testid="distancia-pilas-input"
            />
          </div>
        </div>
      </div>

      {/* Upload Button */}
      <div className="mb-4">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          accept=".xlsx,.xls"
          className="hidden"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading || analyzing}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {uploading || analyzing ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>{analyzing ? 'Analizando con IA...' : 'Subiendo...'}</span>
            </>
          ) : (
            <>
              <FileSpreadsheet className="h-5 w-5" />
              <span>Subir Catálogo de Maquinaria (Excel)</span>
            </>
          )}
        </button>
        <p className="text-xs text-indigo-600 mt-2 text-center">
          Formato esperado: Columnas con Tipo de Máquina, Marca, Modelo, Estatus
        </p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-300 px-4 py-3 rounded-lg text-sm mb-4 flex items-start gap-2">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Resumen del Catálogo */}
      {catalogoData && (
        <div className="space-y-4">
          {/* Stats */}
          <div className="bg-[#15151B] rounded-lg p-4 border border-indigo-100">
            <div className="flex items-center justify-between mb-3">
              <span className="font-medium text-white">Resumen del Catálogo</span>
              <span className="text-xs bg-green-500/15 text-green-300 px-2 py-1 rounded-full flex items-center gap-1">
                <CheckCircle className="h-3 w-3" />
                {catalogoData.disponibles} disponibles
              </span>
            </div>
            <div className="grid grid-cols-5 gap-2 text-center">
              <div className="p-2 bg-amber-500/10 rounded-lg">
                <div className="text-lg font-bold text-amber-300">{catalogoData.resumen?.excavadoras || 0}</div>
                <div className="text-xs text-amber-600">Excavadoras</div>
              </div>
              <div className="p-2 bg-blue-500/10 rounded-lg">
                <div className="text-lg font-bold text-blue-300">{catalogoData.resumen?.perforadoras || 0}</div>
                <div className="text-xs text-blue-600">Perforadoras</div>
              </div>
              <div className="p-2 bg-teal-500/10 rounded-lg">
                <div className="text-lg font-bold text-teal-300">{catalogoData.resumen?.perforadoras_anclas || 0}</div>
                <div className="text-xs text-teal-600">Perf. Anclas</div>
              </div>
              <div className="p-2 bg-purple-500/10 rounded-lg">
                <div className="text-lg font-bold text-purple-300">{catalogoData.resumen?.gruas || 0}</div>
                <div className="text-xs text-purple-600">Grúas</div>
              </div>
              <div className="p-2 bg-[#0F0F14] rounded-lg">
                <div className="text-lg font-bold text-white/80">{catalogoData.resumen?.manipuladores || 0}</div>
                <div className="text-xs text-white/60">Manipuladores</div>
              </div>
            </div>
          </div>

          {/* Lista de Máquinas Colapsable */}
          <div className="bg-[#15151B] rounded-lg border border-indigo-100 overflow-hidden">
            <button
              type="button"
              onClick={() => setShowMaquinas(!showMaquinas)}
              className="w-full px-4 py-3 flex items-center justify-between bg-[#0F0F14] hover:bg-[#15151B] transition-colors"
            >
              <span className="font-medium text-white/80 flex items-center gap-2">
                <Wrench className="h-4 w-4" />
                Ver Máquinas ({catalogoData.maquinas?.length || 0})
              </span>
              {showMaquinas ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
            </button>
            {showMaquinas && (
              <div className="max-h-64 overflow-y-auto p-2">
                <div className="space-y-1">
                  {catalogoData.maquinas?.map((m, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 bg-[#0F0F14] rounded-lg text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{getMaquinaIcon(m.tipo)}</span>
                        <div>
                          <div className="font-medium text-white">{m.marca} {m.modelo}</div>
                          <div className="text-xs text-white/50">{m.tipo}</div>
                        </div>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-xs ${getEstatusColor(m.estatus)}`}>
                        {m.estatus || 'Disponible'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Análisis de IA */}
          {analisisIA && (
            <div className="bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg border border-purple-500/30 overflow-hidden">
              <button
                type="button"
                onClick={() => setShowAnalisis(!showAnalisis)}
                className="w-full px-4 py-3 flex items-center justify-between bg-purple-500/15/50 hover:bg-purple-500/15 transition-colors"
              >
                <span className="font-medium text-purple-300 flex items-center gap-2">
                  <Zap className="h-4 w-4" />
                  Plan de Ejecución Optimizado (IA)
                </span>
                {showAnalisis ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
              </button>
              {showAnalisis && (
                <div className="p-4 space-y-4">
                  {/* Resumen Ejecutivo */}
                  {analisisIA.resumen_ejecutivo && (
                    <div className="bg-[#15151B] rounded-lg p-3 border border-purple-100">
                      <h5 className="font-medium text-purple-300 mb-2 flex items-center gap-2">
                        <Info className="h-4 w-4" />
                        Resumen Ejecutivo
                      </h5>
                      <p className="text-sm text-white/80 whitespace-pre-wrap">{analisisIA.resumen_ejecutivo}</p>
                    </div>
                  )}

                  {/* Plan de Excavación */}
                  {analisisIA.plan_excavacion && (
                    <div className="bg-amber-500/10 rounded-lg p-3 border border-amber-500/30">
                      <h5 className="font-medium text-amber-300 mb-2">🚜 Fase 1: Excavación</h5>
                      <div className="text-sm text-white/80">
                        <p><strong>Máquinas:</strong> {analisisIA.plan_excavacion.maquinas_recomendadas?.join(', ')}</p>
                        <p><strong>Estrategia:</strong> {analisisIA.plan_excavacion.estrategia}</p>
                        <div className="flex gap-4 mt-2">
                          <span className="flex items-center gap-1 text-amber-300">
                            <Clock className="h-4 w-4" />
                            {analisisIA.plan_excavacion.tiempo_estimado_dias} días
                          </span>
                          <span className="text-amber-600">
                            {analisisIA.plan_excavacion.rendimiento_esperado_m3_dia} m³/día
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Plan de Pilas */}
                  {analisisIA.plan_pilas && (
                    <div className="bg-blue-500/10 rounded-lg p-3 border border-blue-500/30">
                      <h5 className="font-medium text-blue-300 mb-2">🔩 Fase 2: Perforación de Pilas</h5>
                      <div className="text-sm text-white/80">
                        <p><strong>Máquinas:</strong> {analisisIA.plan_pilas.maquinas_recomendadas?.join(', ')}</p>
                        <p><strong>Estrategia:</strong> {analisisIA.plan_pilas.estrategia}</p>
                        <div className="flex gap-4 mt-2">
                          <span className="flex items-center gap-1 text-blue-300">
                            <Clock className="h-4 w-4" />
                            {analisisIA.plan_pilas.tiempo_estimado_dias} días
                          </span>
                          <span className="text-blue-600">
                            {analisisIA.plan_pilas.pilas_por_dia} pilas/día
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Plan de Anclas */}
                  {analisisIA.plan_anclas && (
                    <div className="bg-teal-500/10 rounded-lg p-3 border border-teal-500/30">
                      <h5 className="font-medium text-teal-300 mb-2">⚓ Fase 3: Anclas</h5>
                      <div className="text-sm text-white/80">
                        <p><strong>Máquinas:</strong> {analisisIA.plan_anclas.maquinas_recomendadas?.join(', ')}</p>
                        <p><strong>Estrategia:</strong> {analisisIA.plan_anclas.estrategia}</p>
                        <div className="flex gap-4 mt-2">
                          <span className="flex items-center gap-1 text-teal-300">
                            <Clock className="h-4 w-4" />
                            {analisisIA.plan_anclas.tiempo_estimado_dias} días
                          </span>
                          <span className="text-teal-600">
                            {analisisIA.plan_anclas.anclas_por_dia} anclas/día
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Distribución Espacial */}
                  {analisisIA.distribucion_espacial && (
                    <div className="bg-[#15151B] rounded-lg p-3 border border-purple-100">
                      <h5 className="font-medium text-purple-300 mb-2">📍 Distribución Espacial</h5>
                      <div className="text-sm text-white/80">
                        <p>{analisisIA.distribucion_espacial.recomendacion}</p>
                        {analisisIA.distribucion_espacial.consideraciones_seguridad?.length > 0 && (
                          <div className="mt-2">
                            <p className="font-medium text-red-600">⚠️ Consideraciones de Seguridad:</p>
                            <ul className="list-disc list-inside text-white/60">
                              {analisisIA.distribucion_espacial.consideraciones_seguridad.map((c, i) => (
                                <li key={i}>{c}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Especificaciones Técnicas de Máquinas */}
                  {analisisIA.maquinas_con_specs && analisisIA.maquinas_con_specs.length > 0 && (
                    <div className="bg-[#15151B] rounded-lg p-3 border border-purple-100">
                      <h5 className="font-medium text-purple-300 mb-2">📋 Especificaciones Técnicas ({analisisIA.maquinas_con_specs.length} máquinas)</h5>
                      <div className="max-h-48 overflow-y-auto space-y-2">
                        {analisisIA.maquinas_con_specs.filter(m => m.adecuada_para_proyecto !== false).slice(0, 10).map((m, i) => (
                          <div key={i} className={`p-2 rounded-lg text-xs ${m.adecuada_para_proyecto === false ? 'bg-red-500/10 border border-red-500/30' : 'bg-green-500/10 border border-green-500/30'}`}>
                            <div className="flex justify-between items-start">
                              <div>
                                <span className="font-medium text-white">{m.marca} {m.modelo}</span>
                                <span className="text-white/50 ml-2">({m.tipo})</span>
                              </div>
                              {m.adecuada_para_proyecto !== undefined && (
                                <span className={`px-1.5 py-0.5 rounded ${m.adecuada_para_proyecto ? 'bg-green-200 text-green-300' : 'bg-red-200 text-red-300'}`}>
                                  {m.adecuada_para_proyecto ? '✓ Recomendada' : '✗ No ideal'}
                                </span>
                              )}
                            </div>
                            {m.dimensiones && (
                              <div className="mt-1 text-white/60">
                                Dimensiones: {m.dimensiones.largo}m × {m.dimensiones.ancho}m × {m.dimensiones.altura}m
                                {m.radio_giro && ` | Radio giro: ${m.radio_giro}m`}
                              </div>
                            )}
                            {m.rendimiento && (
                              <div className="text-white/60">Rendimiento: {m.rendimiento}</div>
                            )}
                            {m.razon && (
                              <div className="text-white/50 italic mt-1">{m.razon}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Tiempo Total Estimado */}
                  {(analisisIA.plan_excavacion?.tiempo_estimado_dias || analisisIA.plan_pilas?.tiempo_estimado_dias || analisisIA.plan_anclas?.tiempo_estimado_dias) && (
                    <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-3 border border-green-500/30">
                      <h5 className="font-medium text-green-300 mb-2">⏱️ Tiempo Total Estimado</h5>
                      <div className="grid grid-cols-4 gap-2 text-center">
                        <div className="p-2 bg-[#15151B] rounded">
                          <div className="text-lg font-bold text-amber-600">{analisisIA.plan_excavacion?.tiempo_estimado_dias || 0}</div>
                          <div className="text-xs text-white/50">Excavación</div>
                        </div>
                        <div className="p-2 bg-[#15151B] rounded">
                          <div className="text-lg font-bold text-blue-600">{analisisIA.plan_pilas?.tiempo_estimado_dias || 0}</div>
                          <div className="text-xs text-white/50">Pilas</div>
                        </div>
                        <div className="p-2 bg-[#15151B] rounded">
                          <div className="text-lg font-bold text-teal-600">{analisisIA.plan_anclas?.tiempo_estimado_dias || 0}</div>
                          <div className="text-xs text-white/50">Anclas</div>
                        </div>
                        <div className="p-2 bg-green-500/15 rounded">
                          <div className="text-lg font-bold text-green-300">
                            {(analisisIA.plan_excavacion?.tiempo_estimado_dias || 0) + 
                             (analisisIA.plan_pilas?.tiempo_estimado_dias || 0) + 
                             (analisisIA.plan_anclas?.tiempo_estimado_dias || 0)}
                          </div>
                          <div className="text-xs text-green-600 font-medium">TOTAL días</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
