import { useEffect, useState } from 'react';
import axios from 'axios';
import {
  Calendar, CheckCircle2, AlertTriangle, Clock, TrendingUp,
  Shovel, Columns3, Anchor, Building2, DollarSign, Loader2, ChevronDown, ChevronUp,
  ShieldCheck,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ESTADO_CONFIG = {
  ok: {
    color: 'border-emerald-500/40 bg-emerald-500/5',
    badge: 'bg-emerald-500/20 text-emerald-300',
    icon: CheckCircle2,
    label: 'Al día',
  },
  atraso: {
    color: 'border-amber-500/40 bg-amber-500/5',
    badge: 'bg-amber-500/20 text-amber-300',
    icon: TrendingUp,
    label: 'En riesgo',
  },
  critico: {
    color: 'border-rose-500/40 bg-rose-500/5',
    badge: 'bg-rose-500/20 text-rose-300',
    icon: AlertTriangle,
    label: 'Crítico',
  },
  pendiente: {
    color: 'border-white/10 bg-[#0F0F14]',
    badge: 'bg-white/10 text-white/50',
    icon: Clock,
    label: 'Sin avance',
  },
};

/**
 * Muestra una tarjeta por cada semana del programa de obra (V2).
 * Cada tarjeta presenta:
 *  - Cantidades planeadas vs reales por fase (solo las fases activas esa semana)
 *  - Presupuesto planeado vs ejecutado
 *  - % de cumplimiento global
 */
export function ComparativaSemanalCards({ proyectoId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState({});

  useEffect(() => {
    if (!proyectoId) return;
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [proyectoId]);

  const cargar = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/proyectos/${proyectoId}/comparativa-semanal`);
      setData(res.data);
    } catch (e) {
      console.error('Error cargando comparativa semanal', e);
      setData({ tiene_programa: false, semanas: [] });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-[#15151B] rounded-xl p-8 border border-white/10 flex items-center justify-center">
        <Loader2 className="h-6 w-6 text-cyan-400 animate-spin" />
      </div>
    );
  }

  if (!data?.tiene_programa) {
    return (
      <div className="bg-[#15151B] rounded-xl p-6 border border-white/10" data-testid="comparativa-no-programa">
        <h3 className="text-white font-semibold flex items-center gap-2 mb-2">
          <Calendar className="h-5 w-5 text-cyan-400" />
          Comparativa Semanal (Programa vs Real)
        </h3>
        <p className="text-sm text-white/50">
          Este proyecto no tiene un programa de obra cargado. Vuelve a importar el cronograma desde
          "Importar Programa de Obra" para activar la comparativa semana a semana.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-[#15151B] rounded-xl p-4 sm:p-6 border border-white/10" data-testid="comparativa-semanal">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Calendar className="h-5 w-5 text-cyan-400" />
          <h3 className="text-white font-semibold">Comparativa Semanal: Programa vs Real</h3>
        </div>
        <div className="text-xs text-white/50">
          <span className="font-semibold text-white/80">{data.total_semanas}</span> semanas planeadas ·
          contrato <span className="font-semibold text-emerald-300 ml-1">
            ${(data.presupuesto_total_contrato || 0).toLocaleString('es-MX', { maximumFractionDigits: 0 })} MXN
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {data.semanas.map((sem) => (
          <SemanaCard
            key={sem.semana}
            sem={sem}
            expanded={!!expanded[sem.semana]}
            onToggle={() => setExpanded((e) => ({ ...e, [sem.semana]: !e[sem.semana] }))}
          />
        ))}
      </div>
    </div>
  );
}

function SemanaCard({ sem, expanded, onToggle }) {
  const cfg = ESTADO_CONFIG[sem.estado] || ESTADO_CONFIG.pendiente;
  const Icon = cfg.icon;
  const p = sem.planeado;
  const r = sem.real;
  const pct = sem.pct;

  // Detectar qué fases tienen plan en esta semana (no mostrar fases con planeado=0)
  const fasesActivas = [
    { key: 'excavacion_m3', label: 'Excavación', unidad: 'm³', icon: Shovel, color: 'amber',
      plan: p.excavacion_m3, real: r.excavacion_m3, pct: pct.excavacion },
    { key: 'pilas', label: 'Pilas', unidad: 'pzs', icon: Columns3, color: 'blue',
      plan: p.pilas, real: r.pilas, pct: pct.pilas },
    { key: 'anclas', label: 'Anclas', unidad: 'pzs', icon: Anchor, color: 'teal',
      plan: p.anclas, real: r.anclas, pct: pct.anclas },
    { key: 'perfiles', label: 'Reforz. Perfiles', unidad: 'pzs', icon: ShieldCheck, color: 'emerald',
      plan: p.perfiles, real: r.perfiles, pct: pct.perfiles },
    { key: 'muros_m2', label: 'Muros', unidad: 'm²', icon: Building2, color: 'violet',
      plan: p.muros_m2, real: r.muros_m2, pct: pct.muros },
  ].filter((f) => f.plan > 0);

  return (
    <div
      className={`rounded-lg p-3 border-2 transition-shadow hover:shadow-lg ${cfg.color}`}
      data-testid={`semana-card-${sem.semana}`}
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="flex items-center gap-1 text-xs text-white/40 mb-0.5">
            {sem.fecha_inicio} · {sem.fecha_fin?.slice(5) || ''}
          </div>
          <div className="font-bold text-white text-base flex items-center gap-2">
            {sem.semana === 0 ? 'PRELIMINARES (S0)' : `Semana ${sem.semana}`}
          </div>
        </div>
        <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${cfg.badge}`}>
          <Icon className="h-3 w-3" />
          {cfg.label}
        </div>
      </div>

      {/* % global */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-xs mb-1">
          <span className="text-white/60">Cumplimiento esta semana</span>
          <span className={`font-bold ${
            pct.global >= 90 ? 'text-emerald-300' : pct.global >= 70 ? 'text-amber-300' : pct.global > 0 ? 'text-rose-300' : 'text-white/50'
          }`}>
            {sem.tiene_avance ? `${pct.global}%` : '— %'}
          </span>
        </div>
        <div className="w-full bg-[#1F1F26] rounded-full h-2 overflow-hidden">
          <div
            className={`h-2 rounded-full transition-all duration-500 ${
              pct.global >= 90 ? 'bg-emerald-500' : pct.global >= 70 ? 'bg-amber-500' : 'bg-rose-500'
            }`}
            style={{ width: `${Math.min(pct.global, 100)}%` }}
          />
        </div>
      </div>

      {/* Fases activas */}
      <div className="space-y-1.5">
        {fasesActivas.map((f) => (
          <FaseRow key={f.key} fase={f} />
        ))}
      </div>

      {/* Presupuesto */}
      <div className="mt-3 pt-3 border-t border-white/10">
        <div className="flex items-center justify-between text-xs mb-0.5">
          <span className="flex items-center gap-1 text-white/60">
            <DollarSign className="h-3 w-3" /> Presupuesto semana
          </span>
          <span className="text-white/80 font-mono text-xs">
            ${p.presupuesto.toLocaleString('es-MX', { maximumFractionDigits: 0 })}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-white/40">Acum. ejecutado</span>
          <span className="font-mono text-emerald-300 text-xs">
            ${sem.acumulado.real.presupuesto.toLocaleString('es-MX', { maximumFractionDigits: 0 })}
            <span className="text-white/40 ml-1">({sem.acumulado.pct_presupuesto}%)</span>
          </span>
        </div>
      </div>

      {/* Detalle de actividades planeadas */}
      {sem.actividades_planeadas?.length > 0 && (
        <button
          onClick={onToggle}
          className="mt-2 w-full text-xs text-cyan-400 hover:text-cyan-300 flex items-center justify-center gap-1 py-1"
          data-testid={`semana-card-toggle-${sem.semana}`}
        >
          {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          {expanded ? 'Ocultar' : `Ver ${sem.actividades_planeadas.length} actividades`}
        </button>
      )}
      {expanded && (
        <div className="mt-2 space-y-1">
          {sem.actividades_planeadas.map((a, i) => (
            <div key={i} className="text-xs bg-[#0F0F14]/60 rounded p-2 border border-white/5">
              <div className="text-white/80 line-clamp-2 leading-tight">{a.descripcion}</div>
              <div className="flex items-center justify-between mt-1 text-white/50">
                <span>{a.cantidad} {a.unidad}</span>
                <span className="font-mono">${a.importe.toLocaleString('es-MX', { maximumFractionDigits: 0 })}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function FaseRow({ fase }) {
  const Icon = fase.icon;
  const colorClasses = {
    amber: { text: 'text-amber-300', bg: 'bg-amber-500' },
    blue: { text: 'text-blue-300', bg: 'bg-blue-500' },
    teal: { text: 'text-teal-300', bg: 'bg-teal-500' },
    violet: { text: 'text-violet-300', bg: 'bg-violet-500' },
    emerald: { text: 'text-emerald-300', bg: 'bg-emerald-500' },
  }[fase.color];

  const pctClamped = Math.min(fase.pct, 100);

  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-0.5">
        <span className={`flex items-center gap-1 ${colorClasses.text} font-medium`}>
          <Icon className="h-3 w-3" /> {fase.label}
        </span>
        <span className="text-white/70 font-mono">
          <span className="text-white">{fase.real}</span>
          <span className="text-white/30 mx-1">/</span>
          <span className="text-white/50">{fase.plan} {fase.unidad}</span>
          <span className={`ml-1 font-bold ${colorClasses.text}`}>{fase.pct}%</span>
        </span>
      </div>
      <div className="w-full bg-[#1F1F26] rounded-full h-1 overflow-hidden">
        <div className={`${colorClasses.bg} h-1 rounded-full transition-all duration-500`}
             style={{ width: `${pctClamped}%` }} />
      </div>
    </div>
  );
}
