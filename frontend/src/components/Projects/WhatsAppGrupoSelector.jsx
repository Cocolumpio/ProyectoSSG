import { useEffect, useState } from 'react';
import axios from 'axios';
import { MessageCircle, Loader2, Check, X, Sparkles, Link2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Selector de grupo de WhatsApp para vincular a un proyecto.
 * - Lista grupos disponibles
 * - Sugiere auto-match basado en el nombre del proyecto
 * - Permite guardar / desvincular
 */
export function WhatsAppGrupoSelector({ proyectoId, proyectoNombre, valor, onChange }) {
  const [grupos, setGrupos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sugerencia, setSugerencia] = useState(null);
  const [saving, setSaving] = useState(false);
  const [estado, setEstado] = useState(valor || null); // {chat_id, nombre}

  useEffect(() => {
    setEstado(valor || null);
  }, [valor?.chat_id]);

  const cargarGrupos = async () => {
    setLoading(true);
    try {
      const [gRes, mRes] = await Promise.all([
        axios.get(`${API}/whatsapp/grupos`),
        proyectoId
          ? axios.get(`${API}/whatsapp/grupos/auto-match/${proyectoId}`)
          : Promise.resolve({ data: { grupo_sugerido: null } }),
      ]);
      setGrupos(gRes.data?.grupos || []);
      setSugerencia(mRes.data?.grupo_sugerido || null);
    } catch (e) {
      console.error(e);
      alert(`No se pudo cargar grupos: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const vincular = async (grupo) => {
    if (!proyectoId) {
      // Sin proyecto aún (formulario de creación): solo notificar al padre
      setEstado(grupo);
      onChange?.(grupo);
      return;
    }
    setSaving(true);
    try {
      await axios.put(`${API}/proyectos/${proyectoId}/whatsapp-grupo`, {
        chat_id: grupo?.chat_id || null,
        nombre: grupo?.nombre || null,
      });
      setEstado(grupo);
      onChange?.(grupo);
    } catch (e) {
      alert(`Error: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const desvincular = () => vincular(null);

  return (
    <div className="bg-[#0F0F14] border border-white/10 rounded-lg p-3" data-testid="wa-grupo-selector">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2 text-sm text-white/80">
          <MessageCircle className="h-4 w-4 text-emerald-400" />
          <span className="font-medium">Grupo de WhatsApp</span>
          <span className="text-xs text-white/40">(para resumen automático semanal)</span>
        </div>
        {estado ? (
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-emerald-500/15 text-emerald-300 text-xs">
              <Link2 className="h-3 w-3" /> {estado.nombre}
            </span>
            <button
              type="button"
              onClick={desvincular}
              disabled={saving}
              className="text-xs text-rose-300 hover:text-rose-200"
              data-testid="wa-grupo-desvincular-btn"
            >
              Desvincular
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={cargarGrupos}
            disabled={loading}
            className="inline-flex items-center gap-1 text-xs text-cyan-300 hover:text-cyan-200"
            data-testid="wa-grupo-cargar-btn"
          >
            {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <MessageCircle className="h-3 w-3" />}
            {loading ? 'Cargando...' : grupos.length ? 'Recargar' : 'Buscar grupos'}
          </button>
        )}
      </div>

      {/* Sugerencia auto-match */}
      {!estado && sugerencia && (
        <div className="mt-2 flex items-center justify-between gap-2 p-2 bg-cyan-500/10 border border-cyan-500/30 rounded">
          <div className="text-xs">
            <div className="text-cyan-200 inline-flex items-center gap-1">
              <Sparkles className="h-3 w-3" /> Sugerencia automática:
            </div>
            <div className="text-white/90 font-medium">{sugerencia.nombre}</div>
          </div>
          <button
            type="button"
            onClick={() => vincular(sugerencia)}
            disabled={saving}
            className="inline-flex items-center gap-1 bg-emerald-500 hover:bg-emerald-400 text-[#0B0B0F] text-xs font-semibold px-2 py-1 rounded"
            data-testid="wa-grupo-aceptar-sugerencia-btn"
          >
            <Check className="h-3 w-3" /> Vincular
          </button>
        </div>
      )}

      {/* Lista completa de grupos */}
      {!estado && grupos.length > 0 && (
        <div className="mt-2 max-h-40 overflow-y-auto bg-[#15151B] rounded border border-white/5">
          {grupos.map((g) => (
            <button
              key={g.chat_id}
              type="button"
              onClick={() => vincular(g)}
              className="w-full text-left text-xs px-3 py-1.5 text-white/80 hover:bg-white/5 hover:text-white border-b border-white/5 last:border-b-0"
            >
              {g.nombre}
            </button>
          ))}
        </div>
      )}

      {!estado && !loading && !grupos.length && (
        <p className="text-xs text-white/40 italic mt-2">
          Toca "Buscar grupos" para listar los grupos donde está el bot.
        </p>
      )}
    </div>
  );
}
