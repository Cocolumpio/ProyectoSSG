import { Grid3x3, Columns3, Anchor } from 'lucide-react';

const DEFAULT_NAMES = ['Norte', 'Sur', 'Este', 'Oeste'];

/**
 * Configurador inline para las 4 caras de la excavación.
 * Cada cara tiene un nombre (editable), cantidad de pilas y cantidad de anclas.
 * El estado de cada celda (matriz) se gestiona en otra vista; aquí solo el layout.
 */
export function CarasExcavacionConfig({ caras, onChange }) {
  // Garantizar 4 elementos
  const carasNormalizadas = (() => {
    const arr = Array.isArray(caras) ? [...caras] : [];
    while (arr.length < 4) {
      arr.push({
        nombre: DEFAULT_NAMES[arr.length] || `Cara ${arr.length + 1}`,
        pilas: 0,
        anclas: 0,
        pilas_estados: [],
        anclas_estados: [],
      });
    }
    return arr.slice(0, 4);
  })();

  const updateCara = (idx, patch) => {
    const nuevas = carasNormalizadas.map((c, i) => (i === idx ? { ...c, ...patch } : c));
    onChange(nuevas);
  };

  const totalPilas = carasNormalizadas.reduce((s, c) => s + (parseInt(c.pilas) || 0), 0);
  const totalAnclas = carasNormalizadas.reduce((s, c) => s + (parseInt(c.anclas) || 0), 0);

  return (
    <div
      className="bg-cyan-500/5 rounded-xl p-4 border border-cyan-500/30 mt-3"
      data-testid="caras-excavacion-config"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Grid3x3 className="h-5 w-5 text-cyan-400" />
          <h4 className="font-semibold text-white text-sm">Distribución por Caras de Excavación</h4>
        </div>
        <div className="text-xs text-cyan-300 bg-cyan-900/40 px-2 py-0.5 rounded">
          Total: <span className="font-bold">{totalPilas}</span> pilas · <span className="font-bold">{totalAnclas}</span> anclas
        </div>
      </div>
      <p className="text-xs text-white/50 mb-3">
        Asigna las pilas y anclas a cada una de las 4 caras. En el dashboard podrás marcar visualmente las
        que ya están completadas (matriz por cara).
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {carasNormalizadas.map((cara, idx) => (
          <div
            key={idx}
            className="bg-[#0F0F14] rounded-lg p-3 border border-white/10"
            data-testid={`caras-excavacion-cara-${idx}`}
          >
            <input
              type="text"
              value={cara.nombre || ''}
              onChange={(e) => updateCara(idx, { nombre: e.target.value })}
              placeholder={DEFAULT_NAMES[idx]}
              className="w-full bg-transparent text-white font-semibold text-sm border-b border-white/10 focus:border-cyan-400 focus:outline-none pb-1 mb-2"
              data-testid={`caras-excavacion-nombre-${idx}`}
            />
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="flex items-center gap-1 text-xs text-blue-300 mb-1">
                  <Columns3 className="h-3 w-3" /> Pilas
                </label>
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={cara.pilas || ''}
                  onChange={(e) => updateCara(idx, { pilas: parseInt(e.target.value) || 0 })}
                  placeholder="0"
                  className="w-full px-2 py-1 text-sm bg-[#15151B] border border-blue-500/30 rounded focus:ring-1 focus:ring-blue-500 text-white"
                  data-testid={`caras-excavacion-pilas-${idx}`}
                />
              </div>
              <div>
                <label className="flex items-center gap-1 text-xs text-teal-300 mb-1">
                  <Anchor className="h-3 w-3" /> Anclas
                </label>
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={cara.anclas || ''}
                  onChange={(e) => updateCara(idx, { anclas: parseInt(e.target.value) || 0 })}
                  placeholder="0"
                  className="w-full px-2 py-1 text-sm bg-[#15151B] border border-teal-500/30 rounded focus:ring-1 focus:ring-teal-500 text-white"
                  data-testid={`caras-excavacion-anclas-${idx}`}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
