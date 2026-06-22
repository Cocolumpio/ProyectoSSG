import { useEffect, useState } from 'react';
import axios from 'axios';
import { MessageSquare, Save, Loader2, Trash2, Pencil, Sparkles, Bot } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Sección de comentario/justificación para una semana específica del avance.
 * - Admin (readOnly=false): puede crear/editar/borrar y generar resumen IA del grupo WhatsApp.
 * - Cliente (readOnly=true): solo lectura.
 */
export function ComentarioSemanaSection({ proyectoId, semana, readOnly = false, onShowSuccess, waGrupoVinculado = false }) {
  const [loading, setLoading] = useState(true);
  const [comentario, setComentario] = useState(null);
  const [editing, setEditing] = useState(false);
  const [texto, setTexto] = useState('');
  const [saving, setSaving] = useState(false);
  const [generandoResumen, setGenerandoResumen] = useState(false);

  const fetchComentario = async () => {
    if (!proyectoId || semana == null) return;
    setLoading(true);
    try {
      const r = await axios.get(`${API}/proyectos/${proyectoId}/comentarios-semana`);
      const lista = r.data?.comentarios || [];
      const enc = lista.find((c) => Number(c.semana) === Number(semana)) || null;
      setComentario(enc);
      setTexto(enc?.texto || '');
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComentario();
    setEditing(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [proyectoId, semana]);

  const guardar = async () => {
    setSaving(true);
    try {
      const r = await axios.put(
        `${API}/proyectos/${proyectoId}/comentario-semana/${semana}`,
        { texto },
      );
      setComentario(r.data);
      setEditing(false);
      onShowSuccess?.(`Comentario guardado para semana ${semana}`);
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    } finally {
      setSaving(false);
    }
  };

  const borrar = async () => {
    if (!window.confirm('¿Eliminar el comentario de esta semana?')) return;
    try {
      await axios.delete(`${API}/proyectos/${proyectoId}/comentario-semana/${semana}`);
      setComentario(null);
      setTexto('');
      setEditing(false);
      onShowSuccess?.(`Comentario eliminado para semana ${semana}`);
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    }
  };

  const generarResumenWA = async () => {
    if (comentario && !window.confirm(
      'Ya existe un comentario para esta semana. ¿Reemplazarlo con el resumen automático del grupo de WhatsApp?',
    )) return;
    setGenerandoResumen(true);
    try {
      const r = await axios.post(`${API}/proyectos/${proyectoId}/resumen-whatsapp-semana/${semana}`);
      // Refrescar para mostrar el comentario generado
      await fetchComentario();
      setEditing(false);
      onShowSuccess?.(`Resumen WhatsApp generado: ${r.data?.mensajes_analizados || 0} mensajes analizados`);
    } catch (e) {
      alert(`Error: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setGenerandoResumen(false);
    }
  };

  // Cliente y no hay comentario: no mostrar nada (limpio)
  if (readOnly && !comentario && !loading) return null;

  return (
    <div
      className="mt-3 p-3 bg-[#0F0F14] rounded-lg border border-amber-500/20"
      data-testid={`comentario-semana-${semana}`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-amber-300 text-xs font-semibold uppercase tracking-wide">
          <MessageSquare className="h-3.5 w-3.5" />
          Comentarios / Justificación · Semana {semana}
          {comentario?.fuente === 'whatsapp_ia' && (
            <span
              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 normal-case tracking-normal"
              title={`Resumen automático del grupo WhatsApp · ${comentario.mensajes_analizados || 0} mensajes analizados`}
            >
              <Bot className="h-3 w-3" /> WhatsApp · IA
            </span>
          )}
        </div>
        {!readOnly && !editing && (
          <div className="flex items-center gap-2">
            {waGrupoVinculado && (
              <button
                onClick={generarResumenWA}
                disabled={generandoResumen}
                className="text-xs text-emerald-300 hover:text-emerald-200 inline-flex items-center gap-1 disabled:opacity-50"
                title="Generar resumen automático del grupo de WhatsApp para esta semana"
                data-testid={`comentario-resumen-wa-btn-${semana}`}
              >
                {generandoResumen ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
                Resumir WhatsApp
              </button>
            )}
            <button
              onClick={() => { setEditing(true); setTexto(comentario?.texto || ''); }}
              className="text-xs text-cyan-300 hover:text-cyan-200 inline-flex items-center gap-1"
              data-testid={`comentario-edit-btn-${semana}`}
            >
              <Pencil className="h-3 w-3" />
              {comentario ? 'Editar' : 'Agregar'}
            </button>
          </div>
        )}
      </div>

      {loading ? (
        <div className="flex justify-center py-3">
          <Loader2 className="h-4 w-4 text-amber-400 animate-spin" />
        </div>
      ) : editing ? (
        <div className="space-y-2">
          <textarea
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            rows={4}
            maxLength={2000}
            placeholder="¿Qué pasó esta semana? Lluvia, paro de maquinaria, suministros, cambios técnicos…"
            className="w-full bg-[#15151B] text-white text-sm px-3 py-2 rounded border border-white/10 focus:border-amber-400 focus:outline-none resize-none"
            data-testid={`comentario-textarea-${semana}`}
          />
          <div className="flex items-center justify-between">
            <div className="text-[10px] text-white/40">{texto.length}/2000</div>
            <div className="flex items-center gap-2">
              {comentario && (
                <button
                  onClick={borrar}
                  className="text-xs text-rose-300 hover:text-rose-200 inline-flex items-center gap-1"
                >
                  <Trash2 className="h-3 w-3" /> Eliminar
                </button>
              )}
              <button
                onClick={() => { setEditing(false); setTexto(comentario?.texto || ''); }}
                className="text-xs text-white/60 hover:text-white px-2 py-1"
              >
                Cancelar
              </button>
              <button
                onClick={guardar}
                disabled={saving || !texto.trim()}
                className="inline-flex items-center gap-1 bg-amber-500 hover:bg-amber-400 text-[#0B0B0F] text-xs font-semibold px-3 py-1.5 rounded disabled:opacity-50"
                data-testid={`comentario-save-btn-${semana}`}
              >
                {saving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
                Guardar
              </button>
            </div>
          </div>
        </div>
      ) : comentario ? (
        <div>
          <p className="text-sm text-white/85 whitespace-pre-wrap leading-relaxed">{comentario.texto}</p>
          <div className="mt-2 text-[10px] text-white/40">
            {comentario.autor_nombre || 'Admin'} · {new Date(comentario.actualizado_en).toLocaleString('es-MX')}
          </div>
        </div>
      ) : (
        <div className="text-xs text-white/40 italic">Sin comentarios para esta semana.</div>
      )}
    </div>
  );
}
