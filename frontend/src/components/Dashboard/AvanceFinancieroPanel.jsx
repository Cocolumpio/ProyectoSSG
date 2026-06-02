/**
 * AvanceFinancieroPanel — Comparativa Presupuesto vs Ejecutado por categoría.
 * Los datos reales (volumetría, conteo pilas/anclas, m² muros) vienen directo
 * de los avances semanales del dron.
 */
import { useEffect, useState } from 'react';
import axios from 'axios';
import { Wallet, TrendingUp, AlertCircle, Loader2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const fmt = (v) => `$${(v || 0).toLocaleString('es-MX', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
const fmtCompact = (v) => {
  const n = v || 0;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}k`;
  return `$${n.toFixed(0)}`;
};

export function AvanceFinancieroPanel({ proyectoId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!proyectoId) return;
    let cancel = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const r = await axios.get(`${API}/proyectos/${proyectoId}/avance-financiero`);
        if (!cancel) setData(r.data);
      } catch (err) {
        if (!cancel) setError(err.response?.data?.detail || 'Error al cargar');
      } finally {
        if (!cancel) setLoading(false);
      }
    })();
    return () => { cancel = true; };
  }, [proyectoId]);

  if (loading) {
    return (
      <div className="bg-[#0F0F14] border border-white/5 rounded-xl p-6 text-center text-white/40">
        <Loader2 className="h-5 w-5 animate-spin mx-auto" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-sm text-red-300 flex items-center gap-2">
        <AlertCircle className="h-4 w-4" /> {error}
      </div>
    );
  }

  if (!data?.tiene_presupuesto) {
    return (
      <div className="bg-[#0F0F14] border border-dashed border-white/10 rounded-xl p-6 text-center" data-testid="presupuesto-empty">
        <Wallet className="h-10 w-10 text-white/20 mx-auto mb-2" />
        <p className="text-sm text-white/50">
          Este proyecto aún no tiene presupuesto cargado.
        </p>
        <p className="text-xs text-white/30 mt-1">
          Súbelo desde la sección Proyectos → ícono <span className="text-amber-400">Wallet</span> para ver el comparativo con la obra real medida por el dron.
        </p>
      </div>
    );
  }

  const t = data.totales;
  const pctTotal = t.pct;

  return (
    <div className="bg-gradient-to-br from-amber-500/5 to-transparent border border-amber-500/20 rounded-xl p-4 sm:p-5 space-y-5" data-testid="avance-financiero-panel">
      {/* Header con totales */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-amber-500/20 grid place-items-center">
            <Wallet className="h-5 w-5 text-amber-300" />
          </div>
          <div>
            <h3 className="text-white font-semibold">Presupuesto vs Ejecutado</h3>
            <p className="text-xs text-white/40">
              Comparativa real con datos del dron · versión {data.version}
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs uppercase text-white/40">Avance financiero</div>
          <div className="text-2xl font-bold text-amber-300">{pctTotal.toFixed(1)}%</div>
        </div>
      </div>

      {/* Cards de totales */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <div className="bg-[#0F0F14] border border-white/5 rounded-lg p-3">
          <div className="text-[10px] uppercase tracking-wider text-white/40">Presupuestado</div>
          <div className="text-lg sm:text-xl font-bold text-white mt-0.5">{fmt(t.presupuestado)}</div>
          <div className="text-[10px] text-white/30 mt-0.5">MXN total</div>
        </div>
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">
          <div className="text-[10px] uppercase tracking-wider text-amber-300/70">Ejecutado</div>
          <div className="text-lg sm:text-xl font-bold text-amber-300 mt-0.5">{fmt(t.ejecutado)}</div>
          <div className="text-[10px] text-amber-400/60 mt-0.5">según avance real</div>
        </div>
        <div className="bg-[#0F0F14] border border-white/5 rounded-lg p-3 col-span-2 sm:col-span-1">
          <div className="text-[10px] uppercase tracking-wider text-white/40">Pendiente</div>
          <div className="text-lg sm:text-xl font-bold text-white mt-0.5">{fmt(t.pendiente)}</div>
          <div className="text-[10px] text-white/30 mt-0.5">por ejecutar</div>
        </div>
      </div>

      {/* Barra total */}
      <div>
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span className="text-white/50 flex items-center gap-1"><TrendingUp className="h-3 w-3" /> Progreso total ponderado</span>
          <span className="text-white/80 font-medium">{fmt(t.ejecutado)} / {fmt(t.presupuestado)}</span>
        </div>
        <div className="h-2.5 bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-amber-500 to-amber-300 rounded-full transition-all"
            style={{ width: `${Math.min(pctTotal, 100)}%` }}
          />
        </div>
      </div>

      {/* Categorías */}
      <div className="space-y-2.5">
        <div className="text-xs uppercase tracking-wider text-white/40 mb-1">Desglose por categoría</div>
        {data.categorias.map(cat => (
          <div key={cat.nombre} className="bg-[#0F0F14] border border-white/5 rounded-lg p-3">
            <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: cat.color }} />
                <div className="min-w-0">
                  <div className="text-sm font-medium text-white truncate">{cat.nombre}</div>
                  {cat.fuente_real ? (
                    <div className="text-[10px] text-white/40 mt-0.5">
                      Real: <span className="text-white/80 font-medium">{(cat.real || 0).toLocaleString('es-MX', { maximumFractionDigits: 2 })}</span>
                      <span className="text-white/30"> / {(cat.planeado || 0).toLocaleString('es-MX', { maximumFractionDigits: 2 })} {cat.unidad}</span>
                    </div>
                  ) : (
                    <div className="text-[10px] text-white/30 italic mt-0.5">
                      Pondera con avance general del proyecto
                    </div>
                  )}
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-sm font-bold" style={{ color: cat.color }}>
                  {fmtCompact(cat.ejecutado)} <span className="text-white/40 font-normal">/ {fmtCompact(cat.presupuestado)}</span>
                </div>
                <div className="text-[10px] text-white/40">{cat.pct_avance.toFixed(1)}% ejecutado</div>
              </div>
            </div>
            {/* Barra dual */}
            <div className="relative h-2 bg-white/5 rounded-full overflow-hidden">
              <div
                className="absolute inset-y-0 left-0 rounded-full transition-all"
                style={{ width: `${Math.min(cat.pct_avance, 100)}%`, backgroundColor: cat.color }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default AvanceFinancieroPanel;
