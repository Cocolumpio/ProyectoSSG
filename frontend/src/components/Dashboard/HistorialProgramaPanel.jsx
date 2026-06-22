import { useEffect, useState } from 'react';
import axios from 'axios';
import {
  History, Loader2, TrendingDown, TrendingUp, FileSpreadsheet, Pencil, Bot,
  AlertTriangle, RefreshCw, MessageSquare,
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const METRICAS = [
  { key: 'volumen_total_planeado', label: 'Excavación', unidad: 'm³', color: '#f59e0b' },
  { key: 'pilas_planeadas', label: 'Pilas', unidad: 'pzs', color: '#3b82f6' },
  { key: 'anclas_planeadas', label: 'Anclas', unidad: 'pzs', color: '#14b8a6' },
  { key: 'perfiles_planeados', label: 'Perfiles', unidad: 'pzs', color: '#10b981' },
  { key: 'muros_planeados', label: 'Muros', unidad: 'm²', color: '#8b5cf6' },
  { key: 'semanas_planeadas', label: 'Semanas', unidad: '', color: '#a3a3a3' },
];

export function HistorialProgramaPanel({ proyectoId, isAdmin }) {
  const [versiones, setVersiones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [vistaPct, setVistaPct] = useState(false); // false = absolutos, true = % vs v1
  const [inferiendoId, setInferiendoId] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/proyectos/${proyectoId}/programa-historial`);
      setVersiones(r.data?.versiones || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (proyectoId) fetchData();
  }, [proyectoId]);

  const inferirMotivo = async (version) => {
    setInferiendoId(version);
    try {
      const r = await axios.post(
        `${API}/proyectos/${proyectoId}/programa-historial/${version}/inferir-motivo`,
      );
      await fetchData();
      alert(`Motivo inferido (${r.data?.mensajes_analizados} mensajes analizados).`);
    } catch (e) {
      alert(`Error: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setInferiendoId(null);
    }
  };

  // Construir datos para la gráfica
  const baseV1 = versiones[0]?.totales || {};
  const chartData = versiones.map((v) => {
    const row = { version: `v${v.version}`, fecha: v.created_at?.slice(0, 10) };
    METRICAS.forEach((m) => {
      const val = Number(v.totales?.[m.key] || 0);
      if (vistaPct) {
        const base = Number(baseV1?.[m.key] || 0);
        row[m.label] = base > 0 ? ((val - base) / base) * 100 : 0;
      } else {
        row[m.label] = val;
      }
    });
    return row;
  });

  if (loading) {
    return (
      <div className="bg-[#15151B] rounded-xl p-6 border border-white/10 flex justify-center">
        <Loader2 className="h-6 w-6 text-amber-400 animate-spin" />
      </div>
    );
  }

  return (
    <div
      className="bg-[#15151B] rounded-xl p-4 sm:p-6 border border-white/10"
      data-testid="historial-programa-panel"
    >
      <div className="flex items-start justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-start gap-2">
          <History className="h-5 w-5 text-amber-400 mt-0.5" />
          <div>
            <h3 className="text-white font-semibold">Historial de cambios al programa de obra</h3>
            <p className="text-xs text-white/50">
              Detecta ajustes inusuales en metas que pudieran intentar "maquillar" el avance real.
              {' '}Las mediciones siguen tomando la versión más reciente como referencia.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Toggle vista */}
          <div className="flex bg-[#0F0F14] border border-white/10 rounded-lg overflow-hidden text-xs">
            <button
              onClick={() => setVistaPct(false)}
              className={`px-2 py-1 ${!vistaPct ? 'bg-amber-500/20 text-amber-300' : 'text-white/50'}`}
              data-testid="vista-absolutos-btn"
            >
              Absolutos
            </button>
            <button
              onClick={() => setVistaPct(true)}
              className={`px-2 py-1 ${vistaPct ? 'bg-amber-500/20 text-amber-300' : 'text-white/50'}`}
              data-testid="vista-pct-btn"
            >
              % vs v1
            </button>
          </div>
          <button
            onClick={fetchData}
            className="text-white/40 hover:text-white p-1"
            title="Refrescar"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {versiones.length === 0 ? (
        <div className="text-center py-6 text-white/40 text-sm">
          Aún no se han registrado cambios al programa. Cuando se suba un Excel o se modifiquen
          las cantidades planeadas, aparecerán aquí.
        </div>
      ) : (
        <>
          {/* Gráfica */}
          <div className="bg-[#0F0F14] rounded-lg p-3 mb-4" style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
                <CartesianGrid stroke="#27272a" strokeDasharray="3 3" />
                <XAxis dataKey="version" tick={{ fill: '#a3a3a3', fontSize: 11 }} />
                <YAxis
                  tick={{ fill: '#a3a3a3', fontSize: 11 }}
                  tickFormatter={(v) => vistaPct ? `${v.toFixed(0)}%` : v}
                />
                <Tooltip
                  contentStyle={{ background: '#15151B', border: '1px solid rgba(255,255,255,0.1)', fontSize: 12 }}
                  formatter={(v, name) => {
                    const m = METRICAS.find((mt) => mt.label === name);
                    return vistaPct
                      ? [`${Number(v).toFixed(1)}%`, name]
                      : [`${Number(v).toLocaleString()} ${m?.unidad || ''}`, name];
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {METRICAS.map((m) => (
                  <Line
                    key={m.key}
                    type="monotone"
                    dataKey={m.label}
                    stroke={m.color}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Lista de versiones */}
          <div className="space-y-2">
            {versiones.slice().reverse().map((v) => {
              const cambios = Object.entries(v.delta_vs_anterior || {}).filter(([, d]) => d?.abs);
              return (
                <div
                  key={v.id}
                  className="bg-[#0F0F14] rounded-lg p-3 border border-white/10"
                  data-testid={`version-${v.version}`}
                >
                  <div className="flex items-start justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30">
                        v{v.version}
                      </span>
                      <span className="inline-flex items-center gap-1 text-xs text-white/60">
                        {v.fuente === 'excel' ? (
                          <>
                            <FileSpreadsheet className="h-3 w-3" /> Excel
                          </>
                        ) : (
                          <>
                            <Pencil className="h-3 w-3" /> Manual
                          </>
                        )}
                      </span>
                      <span className="text-xs text-white/40">·</span>
                      <span className="text-xs text-white/70">{v.autor_nombre}</span>
                      <span className="text-xs text-white/40">·</span>
                      <span className="text-xs text-white/50">
                        {new Date(v.created_at).toLocaleString('es-MX')}
                      </span>
                    </div>
                    {isAdmin && v.version > 1 && (
                      <button
                        onClick={() => inferirMotivo(v.version)}
                        disabled={inferiendoId === v.version}
                        className="inline-flex items-center gap-1 text-xs text-emerald-300 hover:text-emerald-200 disabled:opacity-50"
                        title="Buscar en el grupo WhatsApp del proyecto el motivo probable del cambio"
                      >
                        {inferiendoId === v.version
                          ? <Loader2 className="h-3 w-3 animate-spin" />
                          : <Bot className="h-3 w-3" />}
                        Inferir motivo desde WhatsApp
                      </button>
                    )}
                  </div>

                  {/* Cambios */}
                  {cambios.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {cambios.map(([key, d]) => {
                        const meta = METRICAS.find((m) => m.key === key);
                        if (!meta) return null;
                        const aumento = d.abs > 0;
                        return (
                          <span
                            key={key}
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] border ${
                              aumento
                                ? 'bg-amber-500/10 text-amber-200 border-amber-500/30'
                                : 'bg-rose-500/10 text-rose-200 border-rose-500/30'
                            }`}
                          >
                            {aumento ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                            {meta.label}: {d.anterior} → {d.actual} {meta.unidad}
                            <span className="font-bold ml-1">({d.pct > 0 ? '+' : ''}{d.pct.toFixed(1)}%)</span>
                          </span>
                        );
                      })}
                    </div>
                  )}

                  {/* Alerta si cambio fuerte */}
                  {cambios.some(([, d]) => Math.abs(d.pct) >= 25) && (
                    <div className="mt-2 inline-flex items-center gap-1 text-xs text-rose-300 bg-rose-500/10 border border-rose-500/30 px-2 py-1 rounded">
                      <AlertTriangle className="h-3 w-3" />
                      Cambio significativo detectado (≥25%). Revisar justificación.
                    </div>
                  )}

                  {/* Motivo */}
                  {v.motivo && (
                    <div className="mt-2 bg-[#15151B] border border-white/5 rounded p-2 text-xs text-white/80">
                      <div className="inline-flex items-center gap-1 text-white/40 mb-1">
                        <MessageSquare className="h-3 w-3" />
                        {v.motivo_fuente === 'whatsapp_ia' ? 'Motivo (inferido por IA desde WhatsApp)' : 'Motivo'}
                      </div>
                      <p className="whitespace-pre-wrap leading-relaxed">{v.motivo}</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
