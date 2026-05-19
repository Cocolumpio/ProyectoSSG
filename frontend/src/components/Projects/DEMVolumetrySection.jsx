/**
 * DEMVolumetrySection — Sección de Volumetría DEM (TIFF) en Avances Semanales
 * Permite subir un DEM por avance, comparar contra avance anterior/terreno original
 * y visualizar retiro/relleno + heatmap + interpretación IA.
 */
import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  Mountain, Upload, Trash2, BarChart3, Sparkles, Loader2,
  ArrowDown, ArrowUp, Minus, AlertCircle, X, Calculator,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function DEMVolumetrySection({ proyecto, avances, selectedAvance, readOnly, onShowSuccess, onAvanceUpdated, onProyectoUpdated }) {
  const [uploading, setUploading] = useState(false);
  const [uploadingTerreno, setUploadingTerreno] = useState(false);
  const [progress, setProgress] = useState(0);
  const [comparaciones, setComparaciones] = useState([]);
  const [loadingComparaciones, setLoadingComparaciones] = useState(false);
  const [showCompareModal, setShowCompareModal] = useState(false);
  const [compareAnteriorId, setCompareAnteriorId] = useState('');
  const [interpretarIA, setInterpretarIA] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState(null);
  const [activeComparacion, setActiveComparacion] = useState(null);
  const [interpretingId, setInterpretingId] = useState(null);
  const fileInputRef = useRef(null);
  const terrenoFileRef = useRef(null);

  const tieneTerrenoOriginal = !!proyecto?.dem_terreno_original_gridfs_id;
  const tieneDem = !!selectedAvance?.dem_gridfs_id;
  const avancesConDem = (avances || []).filter(a => a.dem_gridfs_id && a.id !== selectedAvance?.id);

  // Cargar comparaciones del proyecto
  useEffect(() => {
    if (!proyecto?.id) return;
    fetchComparaciones();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [proyecto?.id, selectedAvance?.id]);

  const fetchComparaciones = async () => {
    setLoadingComparaciones(true);
    try {
      const r = await axios.get(`${API}/proyectos/${proyecto.id}/volumetria-dem`);
      setComparaciones(r.data || []);
    } catch (err) {
      console.error('Error cargando comparaciones:', err);
    } finally {
      setLoadingComparaciones(false);
    }
  };

  // -------- Subir DEM terreno original al PROYECTO --------
  const handleUploadTerreno = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.tif') && !file.name.toLowerCase().endsWith('.tiff')) {
      setError('Solo archivos .tif o .tiff');
      return;
    }
    setUploadingTerreno(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const r = await axios.post(`${API}/proyectos/${proyecto.id}/dem-terreno-original`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      onShowSuccess?.(`Terreno original "${file.name}" cargado`);
      onProyectoUpdated?.({
        ...proyecto,
        dem_terreno_original_gridfs_id: 'set',  // marker
        dem_terreno_original_filename: r.data.filename,
        dem_terreno_original_metadata: r.data.metadata,
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Error subiendo terreno original');
    } finally {
      setUploadingTerreno(false);
      if (terrenoFileRef.current) terrenoFileRef.current.value = '';
    }
  };

  // -------- Subir DEM al avance actual --------
  const handleUploadDem = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.tif') && !file.name.toLowerCase().endsWith('.tiff')) {
      setError('Solo archivos .tif o .tiff');
      return;
    }
    setUploading(true);
    setError(null);
    setProgress(0);
    try {
      const form = new FormData();
      form.append('file', file);
      const r = await axios.post(
        `${API}/proyectos/${proyecto.id}/avances-semanales/${selectedAvance.id}/dem`,
        form,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (evt) => {
            if (evt.total) setProgress(Math.round((evt.loaded / evt.total) * 100));
          },
        }
      );
      onShowSuccess?.(`DEM "${file.name}" cargado en Semana ${selectedAvance.semana}`);
      onAvanceUpdated?.({
        ...selectedAvance,
        dem_gridfs_id: r.data.dem_gridfs_id,
        dem_filename: r.data.dem_filename,
        dem_metadata: r.data.metadata,
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Error subiendo DEM');
    } finally {
      setUploading(false);
      setProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // -------- Eliminar DEM --------
  const handleDeleteDem = async () => {
    if (!window.confirm(`¿Eliminar el DEM "${selectedAvance.dem_filename}"?`)) return;
    try {
      await axios.delete(
        `${API}/proyectos/${proyecto.id}/avances-semanales/${selectedAvance.id}/dem`
      );
      onShowSuccess?.('DEM eliminado');
      onAvanceUpdated?.({ ...selectedAvance, dem_gridfs_id: null, dem_filename: null, dem_metadata: null });
    } catch (err) {
      setError(err.response?.data?.detail || 'Error eliminando');
    }
  };

  // -------- Calcular volumetría --------
  const handleCalcular = async () => {
    if (!compareAnteriorId) {
      setError('Selecciona contra qué DEM comparar');
      return;
    }
    setCalculating(true);
    setError(null);
    try {
      const r = await axios.post(`${API}/proyectos/${proyecto.id}/volumetria-dem`, {
        avance_anterior_id: compareAnteriorId,
        avance_actual_id: selectedAvance.id,
        threshold_m: 0.05,
        interpretar_ia: interpretarIA,
      });
      onShowSuccess?.('Volumetría calculada correctamente');
      setShowCompareModal(false);
      setActiveComparacion(r.data);
      await fetchComparaciones();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error calculando volumetría');
    } finally {
      setCalculating(false);
    }
  };

  // -------- Eliminar comparación --------
  const handleDeleteComparacion = async (id) => {
    if (!window.confirm('¿Eliminar esta comparación volumétrica?')) return;
    try {
      await axios.delete(`${API}/volumetria-dem/${id}`);
      onShowSuccess?.('Comparación eliminada');
      if (activeComparacion?.id === id) setActiveComparacion(null);
      await fetchComparaciones();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error eliminando');
    }
  };

  // -------- Interpretar con IA una comparación previa --------
  const handleInterpretar = async (id) => {
    setInterpretingId(id);
    try {
      const r = await axios.post(`${API}/volumetria-dem/${id}/interpretar`);
      onShowSuccess?.('Interpretación IA generada');
      const updated = comparaciones.map(c => c.id === id ? { ...c, interpretacion_ia: r.data.interpretacion_ia } : c);
      setComparaciones(updated);
      if (activeComparacion?.id === id) {
        setActiveComparacion({ ...activeComparacion, interpretacion_ia: r.data.interpretacion_ia });
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Error generando IA');
    } finally {
      setInterpretingId(null);
    }
  };

  const comparacionesAvanceActual = comparaciones.filter(c => c.avance_actual_id === selectedAvance?.id);

  return (
    <div className="bg-[#15151B] rounded-xl p-3 sm:p-4 shadow-sm space-y-4" data-testid="dem-volumetry-section">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-lg bg-emerald-500/15 grid place-items-center">
            <Mountain className="h-5 w-5 text-emerald-400" />
          </div>
          <div>
            <h5 className="font-semibold text-white text-sm sm:text-base">Volumetría DEM</h5>
            <p className="text-[10px] sm:text-xs text-white/40 leading-tight">
              Compara modelos digitales de elevación (TIFF) entre semanas
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {tieneDem && !readOnly && (
            <button
              onClick={() => setShowCompareModal(true)}
              className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors"
              data-testid="calcular-volumetria-btn"
              disabled={avancesConDem.length === 0 && !tieneTerrenoOriginal}
              title={avancesConDem.length === 0 && !tieneTerrenoOriginal ? 'Necesitas al menos otro DEM (avance anterior o terreno original)' : ''}
            >
              <Calculator className="h-3.5 w-3.5" /> Calcular volumetría
            </button>
          )}
          {!readOnly && (
            <label className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 bg-[#994B49] hover:bg-[#7D3C3A] text-white rounded-lg cursor-pointer transition-colors">
              <Upload className="h-3.5 w-3.5" />
              {tieneDem ? 'Reemplazar DEM' : 'Subir DEM (TIFF)'}
              <input
                ref={fileInputRef}
                type="file"
                accept=".tif,.tiff,image/tiff"
                className="hidden"
                onChange={handleUploadDem}
                disabled={uploading}
                data-testid="upload-dem-input"
              />
            </label>
          )}
          {tieneDem && !readOnly && (
            <button
              onClick={handleDeleteDem}
              className="p-1.5 text-white/50 hover:text-red-400 hover:bg-red-500/10 rounded-lg"
              title="Eliminar DEM"
              data-testid="delete-dem-btn"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* Upload progress */}
      {uploading && (
        <div>
          <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-emerald-500 to-emerald-300" style={{ width: `${progress}%` }} />
          </div>
          <p className="text-xs text-white/50 mt-1.5">Subiendo DEM… {progress}%</p>
        </div>
      )}

      {/* Terreno original del proyecto */}
      {!readOnly && (
        <div className={`rounded-lg p-3 border ${tieneTerrenoOriginal ? 'bg-amber-500/5 border-amber-500/20' : 'bg-[#0F0F14] border-dashed border-white/10'}`}>
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-amber-500/15 grid place-items-center flex-shrink-0">
                <Mountain className="h-4 w-4 text-amber-400" />
              </div>
              <div className="min-w-0">
                <div className="text-sm text-white/90">Terreno original (proyecto)</div>
                <div className="text-[10px] sm:text-xs text-white/40 truncate">
                  {tieneTerrenoOriginal
                    ? proyecto.dem_terreno_original_filename
                    : 'Útil para calcular volumen total excavado desde el inicio'}
                </div>
              </div>
            </div>
            <label className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/30 rounded-lg cursor-pointer transition-colors flex-shrink-0">
              {uploadingTerreno ? (
                <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Subiendo…</>
              ) : (
                <><Upload className="h-3.5 w-3.5" /> {tieneTerrenoOriginal ? 'Reemplazar' : 'Subir TIFF'}</>
              )}
              <input
                ref={terrenoFileRef}
                type="file"
                accept=".tif,.tiff,image/tiff"
                className="hidden"
                onChange={handleUploadTerreno}
                disabled={uploadingTerreno}
                data-testid="upload-terreno-input"
              />
            </label>
          </div>
        </div>
      )}

      {/* Estado del DEM actual */}
      {tieneDem ? (
        <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-3 text-xs sm:text-sm">
          <div className="flex items-center gap-2 text-emerald-300 mb-1">
            <Mountain className="h-4 w-4" />
            <span className="font-medium">DEM cargado:</span>
            <span className="text-white/70 break-all">{selectedAvance.dem_filename}</span>
          </div>
          {selectedAvance.dem_metadata && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2 text-white/50">
              <div><span className="text-white/30">CRS:</span> <span className="text-white/80">{selectedAvance.dem_metadata.crs || 'N/D'}</span></div>
              <div><span className="text-white/30">Resolución:</span> <span className="text-white/80">{selectedAvance.dem_metadata.resolution_x?.toFixed(3)}</span></div>
              <div><span className="text-white/30">Dimensiones:</span> <span className="text-white/80">{selectedAvance.dem_metadata.width}×{selectedAvance.dem_metadata.height}</span></div>
              <div><span className="text-white/30">Bandas:</span> <span className="text-white/80">{selectedAvance.dem_metadata.bands}</span></div>
            </div>
          )}
        </div>
      ) : (
        !readOnly && (
          <div className="text-center py-6 px-4 bg-[#0F0F14] rounded-lg border border-dashed border-white/10">
            <Mountain className="h-10 w-10 text-white/20 mx-auto mb-2" />
            <p className="text-sm text-white/50">Aún no hay DEM en esta semana.</p>
            <p className="text-xs text-white/30 mt-1">Sube un GeoTIFF para habilitar el cálculo volumétrico.</p>
          </div>
        )
      )}

      {/* Error */}
      {error && (
        <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/30 rounded-lg p-2.5 text-xs text-red-300">
          <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <span className="flex-1">{error}</span>
          <button onClick={() => setError(null)}><X className="h-4 w-4" /></button>
        </div>
      )}

      {/* Lista de comparaciones de este avance */}
      {comparacionesAvanceActual.length > 0 && (
        <div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-white/40 mb-2">
            <BarChart3 className="h-3.5 w-3.5" />
            Comparaciones de esta semana ({comparacionesAvanceActual.length})
          </div>
          <div className="space-y-2">
            {comparacionesAvanceActual.map(c => (
              <ComparacionCard
                key={c.id}
                comparacion={c}
                onView={() => setActiveComparacion(c)}
                onDelete={() => handleDeleteComparacion(c.id)}
                onInterpretar={() => handleInterpretar(c.id)}
                isActive={activeComparacion?.id === c.id}
                interpreting={interpretingId === c.id}
                readOnly={readOnly}
              />
            ))}
          </div>
        </div>
      )}

      {/* Resultado activo (gran display) */}
      {activeComparacion && (
        <ComparacionDetalle comparacion={activeComparacion} onClose={() => setActiveComparacion(null)} />
      )}

      {/* Modal: elegir contra qué comparar */}
      {showCompareModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-[1100] p-4" data-testid="compare-modal">
          <div className="bg-[#15151B] border border-white/10 rounded-xl shadow-2xl w-full max-w-md">
            <div className="flex items-center justify-between p-5 border-b border-white/10">
              <h3 className="text-white font-semibold flex items-center gap-2">
                <Calculator className="h-5 w-5 text-emerald-400" />
                Calcular volumetría
              </h3>
              <button onClick={() => setShowCompareModal(false)} className="text-white/50 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="text-xs uppercase tracking-wider text-white/40 mb-2 block">
                  DEM actual (Semana {selectedAvance.semana})
                </label>
                <div className="bg-[#0F0F14] border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 truncate">
                  {selectedAvance.dem_filename}
                </div>
              </div>
              <div>
                <label className="text-xs uppercase tracking-wider text-white/40 mb-2 block">
                  Comparar contra
                </label>
                <select
                  value={compareAnteriorId}
                  onChange={(e) => setCompareAnteriorId(e.target.value)}
                  className="w-full bg-[#0F0F14] border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500"
                  data-testid="compare-select"
                >
                  <option value="">— Selecciona —</option>
                  {tieneTerrenoOriginal && (
                    <option value="terreno_original">🏔️ Terreno original</option>
                  )}
                  {avancesConDem.map(a => (
                    <option key={a.id} value={a.id}>
                      Semana {a.semana} ({a.fecha}) — {a.dem_filename}
                    </option>
                  ))}
                </select>
              </div>
              <label className="flex items-center gap-2 text-sm text-white/70 cursor-pointer">
                <input
                  type="checkbox"
                  checked={interpretarIA}
                  onChange={(e) => setInterpretarIA(e.target.checked)}
                  className="rounded"
                />
                <Sparkles className="h-4 w-4 text-amber-400" />
                Interpretar resultados con IA (Gemini)
              </label>
              {error && (
                <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/30 rounded p-2">{error}</div>
              )}
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  onClick={() => setShowCompareModal(false)}
                  className="px-4 py-2 text-sm text-white/70 hover:text-white"
                  disabled={calculating}
                >
                  Cancelar
                </button>
                <button
                  onClick={handleCalcular}
                  disabled={calculating || !compareAnteriorId}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-lg text-sm flex items-center gap-2"
                  data-testid="confirm-calcular-btn"
                >
                  {calculating ? (
                    <><Loader2 className="h-4 w-4 animate-spin" /> Calculando…</>
                  ) : (
                    <><Calculator className="h-4 w-4" /> Calcular</>
                  )}
                </button>
              </div>
              {calculating && (
                <p className="text-xs text-white/40 text-center">
                  Procesando rasters, esto puede tardar 10-60 segundos según el tamaño…
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------- */
/*  Card resumen de una comparación                   */
/* -------------------------------------------------- */
function ComparacionCard({ comparacion, onView, onDelete, onInterpretar, isActive, interpreting, readOnly }) {
  const r = comparacion.resultado || {};
  return (
    <div
      className={`bg-[#0F0F14] border rounded-lg p-3 transition-all ${
        isActive ? 'border-emerald-500/50' : 'border-white/5 hover:border-white/15'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <button onClick={onView} className="flex-1 text-left">
          <div className="text-xs text-white/40 mb-1">
            {comparacion.avance_anterior_label} → {comparacion.avance_actual_label}
          </div>
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <span className="flex items-center gap-1 text-red-300">
              <ArrowDown className="h-3.5 w-3.5" />
              <strong>{(r.volumen_retirado_m3 || 0).toLocaleString('es-MX', { maximumFractionDigits: 2 })}</strong> m³
            </span>
            <span className="flex items-center gap-1 text-blue-300">
              <ArrowUp className="h-3.5 w-3.5" />
              <strong>{(r.volumen_rellenado_m3 || 0).toLocaleString('es-MX', { maximumFractionDigits: 2 })}</strong> m³
            </span>
            <span className={`flex items-center gap-1 ${(r.volumen_neto_m3 || 0) >= 0 ? 'text-blue-200' : 'text-red-200'}`}>
              <Minus className="h-3.5 w-3.5" />
              Neto: <strong>{(r.volumen_neto_m3 || 0).toLocaleString('es-MX', { maximumFractionDigits: 2 })}</strong> m³
            </span>
          </div>
        </button>
        <div className="flex items-center gap-1">
          {!comparacion.interpretacion_ia && !readOnly && (
            <button
              onClick={onInterpretar}
              disabled={interpreting}
              className="p-1.5 text-amber-300 hover:bg-amber-500/10 rounded disabled:opacity-50"
              title="Interpretar con IA"
            >
              {interpreting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            </button>
          )}
          {!readOnly && (
            <button
              onClick={onDelete}
              className="p-1.5 text-white/40 hover:text-red-400 hover:bg-red-500/10 rounded"
              title="Eliminar"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* -------------------------------------------------- */
/*  Detalle expandido (heatmap + IA)                  */
/* -------------------------------------------------- */
function ComparacionDetalle({ comparacion, onClose }) {
  const r = comparacion.resultado || {};
  const heatmapSrc = `${process.env.REACT_APP_BACKEND_URL}${comparacion.heatmap_url}`;

  return (
    <div className="bg-gradient-to-br from-emerald-500/5 to-transparent border border-emerald-500/20 rounded-xl p-4 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs text-white/40 mb-1">Comparación volumétrica</div>
          <div className="text-sm text-white">
            <span className="text-white/60">{comparacion.avance_anterior_label}</span>
            <span className="text-white/30 mx-2">→</span>
            <span className="font-semibold">{comparacion.avance_actual_label}</span>
          </div>
        </div>
        <button onClick={onClose} className="p-1.5 text-white/50 hover:text-white">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Cards de volúmenes */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-red-300 text-xs uppercase tracking-wider mb-1">
            <ArrowDown className="h-3 w-3" /> Retirado
          </div>
          <div className="text-lg sm:text-xl font-bold text-red-200">
            {(r.volumen_retirado_m3 || 0).toLocaleString('es-MX', { maximumFractionDigits: 2 })}
            <span className="text-xs text-white/40 font-normal ml-1">m³</span>
          </div>
        </div>
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-blue-300 text-xs uppercase tracking-wider mb-1">
            <ArrowUp className="h-3 w-3" /> Rellenado
          </div>
          <div className="text-lg sm:text-xl font-bold text-blue-200">
            {(r.volumen_rellenado_m3 || 0).toLocaleString('es-MX', { maximumFractionDigits: 2 })}
            <span className="text-xs text-white/40 font-normal ml-1">m³</span>
          </div>
        </div>
        <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-3">
          <div className="flex items-center gap-1.5 text-purple-300 text-xs uppercase tracking-wider mb-1">
            <Minus className="h-3 w-3" /> Neto
          </div>
          <div className={`text-lg sm:text-xl font-bold ${(r.volumen_neto_m3 || 0) >= 0 ? 'text-blue-200' : 'text-red-200'}`}>
            {(r.volumen_neto_m3 || 0).toLocaleString('es-MX', { maximumFractionDigits: 2 })}
            <span className="text-xs text-white/40 font-normal ml-1">m³</span>
          </div>
        </div>
        <div className="bg-white/[0.03] border border-white/10 rounded-lg p-3">
          <div className="text-xs uppercase tracking-wider text-white/40 mb-1">Área analizada</div>
          <div className="text-lg sm:text-xl font-bold text-white">
            {(r.area_analizada_m2 || 0).toLocaleString('es-MX', { maximumFractionDigits: 0 })}
            <span className="text-xs text-white/40 font-normal ml-1">m²</span>
          </div>
          <div className="text-[10px] text-white/30 mt-0.5">Res. {r.resolution_m} m/px</div>
        </div>
      </div>

      {/* Heatmap */}
      <div>
        <div className="text-xs uppercase tracking-wider text-white/40 mb-2 flex items-center gap-1.5">
          <BarChart3 className="h-3.5 w-3.5" />
          Mapa de calor — rojo: retiro, azul: relleno
        </div>
        <div className="bg-[#0B0B0F] rounded-lg overflow-hidden border border-white/5">
          <img
            src={heatmapSrc}
            alt="Heatmap volumétrico"
            className="w-full h-auto"
            data-testid="dem-heatmap-img"
          />
        </div>
      </div>

      {/* Interpretación IA */}
      {comparacion.interpretacion_ia && (
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-4">
          <div className="flex items-center gap-2 text-amber-300 text-xs uppercase tracking-wider mb-2">
            <Sparkles className="h-3.5 w-3.5" />
            Análisis IA (Gemini)
          </div>
          <p className="text-sm text-white/80 whitespace-pre-wrap leading-relaxed" data-testid="dem-ia-text">
            {comparacion.interpretacion_ia}
          </p>
        </div>
      )}

      {/* Stats técnicas */}
      <details className="text-xs text-white/40">
        <summary className="cursor-pointer hover:text-white/70 select-none">
          Datos técnicos
        </summary>
        <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1 text-[11px]">
          <div><span className="text-white/30">CRS:</span> <span className="text-white/60">{r.crs}</span></div>
          <div><span className="text-white/30">Geográfico:</span> <span className="text-white/60">{r.is_geographic ? 'Sí (lat/lon)' : 'No'}</span></div>
          <div><span className="text-white/30">Δ máx:</span> <span className="text-white/60">{r.stats?.diff_max?.toFixed(2)} m</span></div>
          <div><span className="text-white/30">Δ mín:</span> <span className="text-white/60">{r.stats?.diff_min?.toFixed(2)} m</span></div>
          <div><span className="text-white/30">Δ promedio:</span> <span className="text-white/60">{r.stats?.diff_mean?.toFixed(3)} m</span></div>
          <div><span className="text-white/30">Umbral ruido:</span> <span className="text-white/60">{comparacion.threshold_m} m</span></div>
        </div>
      </details>
    </div>
  );
}

export default DEMVolumetrySection;
