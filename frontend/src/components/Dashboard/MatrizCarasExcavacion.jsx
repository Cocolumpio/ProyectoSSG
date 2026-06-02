import { useState, useEffect } from 'react';
import axios from 'axios';
import { Grid3x3, Columns3, Anchor, Loader2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Vista interactiva de la matriz de pilas/anclas dividida en 4 caras.
 * - Admin: puede hacer click en cada celda para marcar/desmarcar.
 * - Cliente: vista de solo lectura.
 *
 * Layout en planta (Cara 0 arriba, 1 abajo, 2 derecha, 3 izquierda) si los
 * nombres son Norte/Sur/Este/Oeste; en otros casos se muestra como grilla 2x2.
 */
export function MatrizCarasExcavacion({ proyectoId, isAdmin = false }) {
  const [caras, setCaras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(null);
  const [tipoActivo, setTipoActivo] = useState('pilas'); // 'pilas' | 'anclas'

  useEffect(() => {
    if (!proyectoId) return;
    cargarCaras();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [proyectoId]);

  const cargarCaras = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API}/proyectos/${proyectoId}/caras-excavacion`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setCaras(res.data?.caras || []);
    } catch (err) {
      console.error('Error cargando caras:', err);
      setCaras([]);
    } finally {
      setLoading(false);
    }
  };

  const toggleCelda = async (caraIdx, tipo, cellIdx) => {
    if (!isAdmin) return;
    const key = `${caraIdx}-${tipo}-${cellIdx}`;
    if (updating === key) return;

    // Optimistic update
    const carasPrev = caras;
    const nuevas = caras.map((c, i) => {
      if (i !== caraIdx) return c;
      const campo = tipo === 'pilas' ? 'pilas_estados' : 'anclas_estados';
      const total = tipo === 'pilas' ? c.pilas : c.anclas;
      const estados = [...(c[campo] || [])];
      while (estados.length < total) estados.push(false);
      estados[cellIdx] = !estados[cellIdx];
      return { ...c, [campo]: estados };
    });
    setCaras(nuevas);
    setUpdating(key);

    try {
      const token = localStorage.getItem('token');
      await axios.put(
        `${API}/proyectos/${proyectoId}/caras-excavacion/${caraIdx}/${tipo}/${cellIdx}`,
        null,
        { headers: { Authorization: `Bearer ${token}` } }
      );
    } catch (err) {
      console.error('Error actualizando celda:', err);
      setCaras(carasPrev);
    } finally {
      setUpdating(null);
    }
  };

  if (loading) {
    return (
      <div className="bg-[#15151B] rounded-xl p-6 border border-white/10 flex items-center justify-center min-h-[120px]">
        <Loader2 className="h-6 w-6 text-cyan-400 animate-spin" />
      </div>
    );
  }

  const carasConfiguradas = caras.length === 4 && caras.some((c) => (c.pilas || c.anclas));

  if (!carasConfiguradas) {
    return (
      <div className="bg-[#15151B] rounded-xl p-6 border border-white/10" data-testid="matriz-no-configurada">
        <div className="flex items-center gap-2 mb-2">
          <Grid3x3 className="h-5 w-5 text-cyan-400" />
          <h3 className="font-semibold text-white">Matriz de Pilas y Anclas por Cara</h3>
        </div>
        <p className="text-sm text-white/50">
          La distribución por caras de excavación aún no se ha configurado. Edita el proyecto y define las
          pilas/anclas asignadas a cada una de las 4 caras para activar esta vista.
        </p>
      </div>
    );
  }

  const totalCompletadas = (cara, tipo) => {
    const estados = (tipo === 'pilas' ? cara.pilas_estados : cara.anclas_estados) || [];
    return estados.filter(Boolean).length;
  };

  // Calcular totales globales
  const totalP = caras.reduce((s, c) => s + (c.pilas || 0), 0);
  const totalPC = caras.reduce((s, c) => s + totalCompletadas(c, 'pilas'), 0);
  const totalA = caras.reduce((s, c) => s + (c.anclas || 0), 0);
  const totalAC = caras.reduce((s, c) => s + totalCompletadas(c, 'anclas'), 0);

  return (
    <div
      className="bg-[#15151B] rounded-xl p-4 sm:p-6 border border-white/10"
      data-testid="matriz-caras-excavacion"
    >
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Grid3x3 className="h-5 w-5 text-cyan-400" />
          <h3 className="font-semibold text-white">Matriz de Pilas y Anclas por Cara</h3>
        </div>

        {/* Toggle Pilas/Anclas */}
        <div className="inline-flex rounded-lg overflow-hidden border border-white/10 bg-[#0F0F14]">
          <button
            onClick={() => setTipoActivo('pilas')}
            className={`flex items-center gap-1 px-3 py-1.5 text-xs font-medium transition-colors ${
              tipoActivo === 'pilas'
                ? 'bg-blue-500/20 text-blue-300'
                : 'text-white/50 hover:text-white/80'
            }`}
            data-testid="matriz-tab-pilas"
          >
            <Columns3 className="h-3 w-3" /> Pilas
            <span className="ml-1 bg-blue-900/40 px-1.5 py-0.5 rounded-full">{totalPC}/{totalP}</span>
          </button>
          <button
            onClick={() => setTipoActivo('anclas')}
            className={`flex items-center gap-1 px-3 py-1.5 text-xs font-medium transition-colors ${
              tipoActivo === 'anclas'
                ? 'bg-teal-500/20 text-teal-300'
                : 'text-white/50 hover:text-white/80'
            }`}
            data-testid="matriz-tab-anclas"
          >
            <Anchor className="h-3 w-3" /> Anclas
            <span className="ml-1 bg-teal-900/40 px-1.5 py-0.5 rounded-full">{totalAC}/{totalA}</span>
          </button>
        </div>
      </div>

      {/* Layout en planta 2x2 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {caras.map((cara, caraIdx) => (
          <CaraCard
            key={caraIdx}
            cara={cara}
            caraIdx={caraIdx}
            tipo={tipoActivo}
            isAdmin={isAdmin}
            onToggle={toggleCelda}
            updatingKey={updating}
          />
        ))}
      </div>

      {isAdmin && (
        <p className="mt-3 text-xs text-white/40">
          💡 Haz click en cada celda para marcarla como completada. Los avances se reflejan en el resumen del proyecto.
        </p>
      )}
    </div>
  );
}

function CaraCard({ cara, caraIdx, tipo, isAdmin, onToggle, updatingKey }) {
  const total = tipo === 'pilas' ? (cara.pilas || 0) : (cara.anclas || 0);
  const estados = (tipo === 'pilas' ? cara.pilas_estados : cara.anclas_estados) || [];
  const completadas = estados.filter(Boolean).length;
  const pct = total ? (completadas / total) * 100 : 0;

  const colorPrincipal = tipo === 'pilas' ? 'blue' : 'teal';
  const colorClasses = {
    blue: {
      border: 'border-blue-500/30',
      text: 'text-blue-300',
      bg: 'bg-blue-500/20',
      bgFull: 'bg-blue-500',
      bgEmpty: 'bg-blue-500/5 border-blue-500/20',
      bgEmptyHover: 'hover:bg-blue-500/15',
    },
    teal: {
      border: 'border-teal-500/30',
      text: 'text-teal-300',
      bg: 'bg-teal-500/20',
      bgFull: 'bg-teal-500',
      bgEmpty: 'bg-teal-500/5 border-teal-500/20',
      bgEmptyHover: 'hover:bg-teal-500/15',
    },
  }[colorPrincipal];

  // Tamaño de celda adaptativo según cantidad
  let cellSize = 'h-6 w-6';
  let gridCols = 'grid-cols-10';
  if (total > 80) {
    cellSize = 'h-4 w-4';
    gridCols = 'grid-cols-12';
  } else if (total > 40) {
    cellSize = 'h-5 w-5';
    gridCols = 'grid-cols-10';
  } else if (total <= 12) {
    cellSize = 'h-8 w-8';
    gridCols = 'grid-cols-6';
  }

  return (
    <div
      className={`rounded-lg p-3 border ${colorClasses.border} bg-[#0F0F14]`}
      data-testid={`matriz-cara-${caraIdx}`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold ${colorClasses.text} uppercase tracking-wider`}>
            {cara.nombre || `Cara ${caraIdx + 1}`}
          </span>
        </div>
        <span className={`text-xs font-mono ${colorClasses.text}`}>
          {completadas}/{total} · {pct.toFixed(0)}%
        </span>
      </div>

      {/* Barra de progreso */}
      <div className="w-full bg-[#1F1F26] rounded-full h-1.5 mb-2 overflow-hidden">
        <div
          className={`${colorClasses.bgFull} h-1.5 rounded-full transition-all duration-300`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Cuadrícula de celdas */}
      {total > 0 ? (
        <div className={`grid ${gridCols} gap-1`} data-testid={`matriz-cells-${caraIdx}-${tipo}`}>
          {Array.from({ length: total }).map((_, idx) => {
            const completada = !!estados[idx];
            const key = `${caraIdx}-${tipo}-${idx}`;
            const isUpdating = updatingKey === key;
            return (
              <button
                key={idx}
                type="button"
                disabled={!isAdmin || isUpdating}
                onClick={() => onToggle(caraIdx, tipo, idx)}
                title={`${tipo === 'pilas' ? 'Pila' : 'Ancla'} ${idx + 1} — ${
                  completada ? 'Completada' : 'Pendiente'
                }`}
                className={`${cellSize} rounded transition-all duration-150 ${
                  completada
                    ? `${colorClasses.bgFull} shadow-sm hover:opacity-80`
                    : `${colorClasses.bgEmpty} border ${isAdmin ? colorClasses.bgEmptyHover + ' cursor-pointer' : 'cursor-default'}`
                } ${isUpdating ? 'animate-pulse' : ''} ${
                  !isAdmin ? 'cursor-default' : ''
                }`}
                data-testid={`matriz-cell-${caraIdx}-${tipo}-${idx}`}
              />
            );
          })}
        </div>
      ) : (
        <p className="text-xs text-white/30 italic py-2">Sin {tipo} en esta cara</p>
      )}
    </div>
  );
}
