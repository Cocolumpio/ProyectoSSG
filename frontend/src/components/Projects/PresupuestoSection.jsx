/**
 * PresupuestoSection — Análisis IA del presupuesto del proyecto (Excel/xlsm).
 *
 * Flujo:
 *  1. Usuario sube un archivo Excel.
 *  2. Backend lista todas las hojas; si hay múltiples versiones (R3/R4/PPTO), el
 *     usuario elige cuál usar (con sugerencia automática a la más reciente).
 *  3. IA Gemini clasifica cada concepto en categorías estándar (Excavación,
 *     Cimentación, Anclas, Muros, Edificación, Generales, Otros).
 *  4. Se muestra la tabla agrupada con totales por categoría.
 */
import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import {
  Upload, FileSpreadsheet, Trash2, Sparkles, AlertCircle, X, Check,
  Loader2, ChevronRight, DollarSign, Wallet,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CATEGORIA_COLORS = {
  Generales: '#94A3B8',
  Excavación: '#F59E0B',
  Cimentación: '#3B82F6',
  Anclas: '#14B8A6',
  Muros: '#A855F7',
  Edificación: '#EC4899',
  Otros: '#71717A',
};

export function PresupuestoSection({ proyecto, readOnly, onShowSuccess, onProyectoUpdated }) {
  const [presupuesto, setPresupuesto] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  const [hojasInfo, setHojasInfo] = useState(null);
  const [selectedSheet, setSelectedSheet] = useState('');
  const [pendingFile, setPendingFile] = useState(null);
  const [expanded, setExpanded] = useState({});
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!proyecto?.id) return;
    fetchPresupuesto();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [proyecto?.id]);

  const fetchPresupuesto = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/proyectos/${proyecto.id}/presupuesto`);
      if (r.data && !r.data.empty) {
        setPresupuesto(r.data);
        // Expand all by default
        const exp = {};
        Object.keys(r.data.categorias || {}).forEach(k => { exp[k] = true; });
        setExpanded(exp);
      } else {
        setPresupuesto(null);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().match(/\.(xlsx|xlsm|xls)$/)) {
      setError('Solo archivos .xlsx, .xlsm o .xls');
      return;
    }
    setUploading(true);
    setError(null);
    setHojasInfo(null);
    setPendingFile(file);
    try {
      const form = new FormData();
      form.append('file', file);
      const r = await axios.post(`${API}/presupuesto/listar-hojas`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setHojasInfo(r.data);
      // Auto-select recommended
      setSelectedSheet(r.data.version_recomendada || r.data.hojas_con_presupuesto?.[0] || '');
    } catch (err) {
      setError(err.response?.data?.detail || 'Error leyendo el Excel');
      setPendingFile(null);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleAnalizar = async () => {
    if (!selectedSheet || !pendingFile) return;
    setAnalyzing(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', pendingFile);
      form.append('sheet_name', selectedSheet);
      // Si la hoja seleccionada tiene posible_version conocido (R3/R4), lo pasamos
      const hoja = hojasInfo.hojas.find(h => h.nombre === selectedSheet);
      if (hoja?.posible_version) form.append('version', hoja.posible_version);

      const r = await axios.post(
        `${API}/proyectos/${proyecto.id}/presupuesto/analizar`,
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      setPresupuesto(r.data);
      setHojasInfo(null);
      setPendingFile(null);
      setSelectedSheet('');
      const exp = {};
      Object.keys(r.data.categorias || {}).forEach(k => { exp[k] = true; });
      setExpanded(exp);
      onShowSuccess?.(`Presupuesto analizado: ${r.data.num_conceptos} conceptos, $${r.data.total_general.toLocaleString('es-MX')} MXN`);
      onProyectoUpdated?.({ ...proyecto, presupuesto: r.data });
    } catch (err) {
      setError(err.response?.data?.detail || 'Error analizando con IA');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('¿Eliminar el presupuesto cargado?')) return;
    try {
      await axios.delete(`${API}/proyectos/${proyecto.id}/presupuesto`);
      setPresupuesto(null);
      onShowSuccess?.('Presupuesto eliminado');
      onProyectoUpdated?.({ ...proyecto, presupuesto: null });
    } catch (err) {
      setError(err.response?.data?.detail || 'Error eliminando');
    }
  };

  const cancelarSeleccion = () => {
    setHojasInfo(null);
    setPendingFile(null);
    setSelectedSheet('');
  };

  const fmtMoney = (v) => `$${(v || 0).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  if (loading) {
    return (
      <div className="bg-[#15151B] rounded-xl p-4 text-center text-white/40">
        <Loader2 className="h-5 w-5 animate-spin mx-auto" />
      </div>
    );
  }

  return (
    <div className="bg-[#15151B] rounded-xl p-3 sm:p-4 shadow-sm space-y-4" data-testid="presupuesto-section">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-lg bg-amber-500/15 grid place-items-center">
            <Wallet className="h-5 w-5 text-amber-400" />
          </div>
          <div>
            <h5 className="font-semibold text-white text-sm sm:text-base">Presupuesto del Proyecto</h5>
            <p className="text-[10px] sm:text-xs text-white/40 leading-tight">
              {presupuesto
                ? `${presupuesto.num_conceptos} conceptos • ${presupuesto.version} • ${presupuesto.filename}`
                : 'Sube un Excel para extraer el presupuesto con IA'}
            </p>
          </div>
        </div>
        {!readOnly && (
          <div className="flex items-center gap-2">
            {presupuesto && (
              <button
                onClick={handleDelete}
                className="p-1.5 text-white/50 hover:text-red-400 hover:bg-red-500/10 rounded-lg"
                title="Eliminar presupuesto"
                data-testid="delete-presupuesto-btn"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
            <label className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg cursor-pointer transition-colors">
              {uploading ? (
                <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Leyendo Excel…</>
              ) : (
                <><Upload className="h-3.5 w-3.5" /> {presupuesto ? 'Reemplazar' : 'Subir Excel'}</>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xlsm,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel.sheet.macroEnabled.12"
                className="hidden"
                onChange={handleFileChange}
                disabled={uploading || analyzing}
                data-testid="upload-presupuesto-input"
              />
            </label>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/30 rounded-lg p-2.5 text-xs text-red-300">
          <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <span className="flex-1">{error}</span>
          <button onClick={() => setError(null)}><X className="h-4 w-4" /></button>
        </div>
      )}

      {/* Selector de hoja (cuando hay múltiples versiones) */}
      {hojasInfo && (
        <div className="bg-[#0F0F14] border border-amber-500/30 rounded-lg p-4 space-y-3">
          <div className="flex items-center gap-2 text-amber-300">
            <FileSpreadsheet className="h-4 w-4" />
            <span className="text-sm font-medium">
              {hojasInfo.tiene_multiples_versiones
                ? 'Encontré varias versiones — ¿cuál uso?'
                : 'Confirma la hoja a procesar'}
            </span>
          </div>
          <div className="space-y-2">
            {hojasInfo.hojas
              .filter(h => h.es_presupuesto)
              .map(h => (
                <label
                  key={h.nombre}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                    selectedSheet === h.nombre
                      ? 'bg-amber-500/10 border-amber-500/50'
                      : 'bg-[#15151B] border-white/10 hover:border-white/20'
                  }`}
                >
                  <input
                    type="radio"
                    name="sheet"
                    value={h.nombre}
                    checked={selectedSheet === h.nombre}
                    onChange={() => setSelectedSheet(h.nombre)}
                    className="mt-1"
                    data-testid={`sheet-radio-${h.nombre}`}
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white">{h.nombre}</span>
                      {h.posible_version && (
                        <span className="text-[10px] px-2 py-0.5 bg-amber-500/20 text-amber-300 rounded-full uppercase">
                          {h.posible_version}
                        </span>
                      )}
                      {h.nombre === hojasInfo.version_recomendada && (
                        <span className="text-[10px] px-2 py-0.5 bg-green-500/20 text-green-300 rounded-full flex items-center gap-1">
                          <Sparkles className="h-3 w-3" /> Recomendada
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-white/40 mt-0.5">
                      {h.rows} filas × {h.cols} columnas
                    </div>
                  </div>
                </label>
              ))}
          </div>
          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              onClick={cancelarSeleccion}
              className="px-3 py-1.5 text-sm text-white/70 hover:text-white"
              disabled={analyzing}
            >
              Cancelar
            </button>
            <button
              onClick={handleAnalizar}
              disabled={!selectedSheet || analyzing}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white rounded-lg text-sm flex items-center gap-2"
              data-testid="analizar-presupuesto-btn"
            >
              {analyzing ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Analizando con IA…</>
              ) : (
                <><Sparkles className="h-4 w-4" /> Analizar con IA</>
              )}
            </button>
          </div>
          {analyzing && (
            <p className="text-xs text-white/40 text-center pt-1">
              Procesando con Gemini Vision. Puede tardar 15-45 segundos…
            </p>
          )}
        </div>
      )}

      {/* Presupuesto cargado */}
      {presupuesto && (
        <div className="space-y-3">
          {/* Total general destacado */}
          <div className="bg-gradient-to-r from-amber-500/15 to-amber-500/5 border border-amber-500/30 rounded-xl p-4 flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-500/20 grid place-items-center">
                <DollarSign className="h-5 w-5 text-amber-300" />
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider text-amber-300/70">Total general</div>
                <div className="text-xl sm:text-2xl font-bold text-white">
                  {fmtMoney(presupuesto.total_general)}
                </div>
              </div>
            </div>
            <div className="text-xs text-white/40">
              Versión <span className="text-white/80 font-medium">{presupuesto.version}</span> · clasificado con IA
            </div>
          </div>

          {/* Categorías */}
          <div className="space-y-2">
            {Object.entries(presupuesto.categorias || {})
              .sort((a, b) => (b[1].total || 0) - (a[1].total || 0))
              .map(([cat, info]) => {
                const color = CATEGORIA_COLORS[cat] || '#94A3B8';
                const pct = presupuesto.total_general > 0
                  ? (info.total / presupuesto.total_general) * 100
                  : 0;
                return (
                  <div key={cat} className="bg-[#0F0F14] border border-white/5 rounded-lg overflow-hidden">
                    <button
                      onClick={() => setExpanded(e => ({ ...e, [cat]: !e[cat] }))}
                      className="w-full p-3 flex items-center gap-3 hover:bg-white/[0.02] transition-colors"
                      data-testid={`cat-toggle-${cat}`}
                    >
                      <ChevronRight
                        className={`h-4 w-4 text-white/40 transition-transform ${expanded[cat] ? 'rotate-90' : ''}`}
                      />
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                      <div className="flex-1 text-left">
                        <div className="text-white font-medium text-sm">{cat}</div>
                        <div className="text-xs text-white/40">{info.conceptos.length} conceptos · {pct.toFixed(1)}% del total</div>
                      </div>
                      <div className="text-right">
                        <div className="text-white font-bold text-sm sm:text-base">{fmtMoney(info.total)}</div>
                      </div>
                    </button>
                    {/* Barra proporcional */}
                    <div className="h-1 bg-white/5">
                      <div className="h-full" style={{ width: `${pct}%`, backgroundColor: color }} />
                    </div>
                    {expanded[cat] && (
                      <div className="border-t border-white/5">
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs">
                            <thead className="bg-white/[0.02] text-white/50">
                              <tr>
                                <th className="text-left px-3 py-2 font-medium">Concepto</th>
                                <th className="text-center px-2 py-2 font-medium w-16">Unidad</th>
                                <th className="text-right px-2 py-2 font-medium w-24">Cantidad</th>
                                <th className="text-right px-2 py-2 font-medium w-28">P. Unitario</th>
                                <th className="text-right px-3 py-2 font-medium w-32">Importe</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                              {info.conceptos.map((c, i) => (
                                <tr key={i} className="text-white/80 hover:bg-white/[0.02]">
                                  <td className="px-3 py-2 max-w-md">
                                    <span title={c.concepto}>{c.concepto}</span>
                                  </td>
                                  <td className="text-center px-2 py-2 text-white/50">{c.unidad}</td>
                                  <td className="text-right px-2 py-2">
                                    {c.cantidad !== null ? c.cantidad.toLocaleString('es-MX', { maximumFractionDigits: 2 }) : '—'}
                                  </td>
                                  <td className="text-right px-2 py-2 text-white/60">
                                    {c.p_unitario !== null ? `$${c.p_unitario.toLocaleString('es-MX', { maximumFractionDigits: 2 })}` : '—'}
                                  </td>
                                  <td className="text-right px-3 py-2 font-medium" style={{ color }}>
                                    {fmtMoney(c.importe)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Estado vacío */}
      {!presupuesto && !hojasInfo && !uploading && !readOnly && (
        <div className="text-center py-6 px-4 bg-[#0F0F14] rounded-lg border border-dashed border-white/10">
          <Wallet className="h-10 w-10 text-white/20 mx-auto mb-2" />
          <p className="text-sm text-white/50">Sube un Excel para extraer el presupuesto con IA</p>
          <p className="text-xs text-white/30 mt-1">
            Acepta .xlsx, .xlsm — detecta versiones (R3, R4, PPTO) y clasifica conceptos automáticamente
          </p>
        </div>
      )}
    </div>
  );
}

export default PresupuestoSection;
