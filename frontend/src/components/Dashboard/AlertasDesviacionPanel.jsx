import { useEffect, useState } from 'react';
import axios from 'axios';
import { AlertTriangle, MessageCircle, Loader2, History, Send, RefreshCw } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Panel admin para disparar alertas de desviación y ver historial enviado.
 * Solo se muestra en Dashboard Admin (readOnly=false).
 */
export function AlertasDesviacionPanel({ proyectoId, proyectoNombre }) {
  const [historial, setHistorial] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [ultimoResultado, setUltimoResultado] = useState(null);
  const [showHistorial, setShowHistorial] = useState(false);

  const fetchHistorial = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/proyectos/${proyectoId}/alertas-historial`);
      setHistorial(r.data?.alertas || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (proyectoId) fetchHistorial();
    setUltimoResultado(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [proyectoId]);

  const disparar = async (forzar) => {
    if (forzar && !window.confirm(
      '¿Forzar envío de alerta a directores ahora?\n\n' +
      'Esto enviará un WhatsApp REAL a todos los directores activos con la recomendación IA.',
    )) return;
    setSending(true);
    setUltimoResultado(null);
    try {
      const r = await axios.post(
        `${API}/proyectos/${proyectoId}/alerta-desviacion?forzar=${forzar ? 'true' : 'false'}`,
      );
      setUltimoResultado(r.data);
      if (r.data?.alerta_enviada) fetchHistorial();
    } catch (e) {
      setUltimoResultado({
        error: true,
        razon: e?.response?.data?.detail || e.message,
      });
    } finally {
      setSending(false);
    }
  };

  return (
    <div
      className="bg-[#15151B] rounded-xl p-4 sm:p-6 border border-white/10"
      data-testid="alertas-desviacion-panel"
    >
      <div className="flex items-start justify-between mb-3 flex-wrap gap-2">
        <div className="flex items-start gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-400 mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="text-white font-semibold">Alertas de Desviación · WhatsApp</h3>
            <p className="text-xs text-white/50">
              Notifica a directores cuando el avance real se desvía ≥10% del programa, con plan de recuperación IA.
            </p>
          </div>
        </div>
        <button
          onClick={fetchHistorial}
          className="text-white/40 hover:text-white p-1 rounded"
          title="Refrescar"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="flex flex-wrap gap-2 mb-3">
        <button
          onClick={() => disparar(false)}
          disabled={sending}
          className="inline-flex items-center gap-1 bg-cyan-500 hover:bg-cyan-400 text-[#0B0B0F] text-sm font-semibold px-3 py-2 rounded-lg disabled:opacity-50"
          data-testid="evaluar-alerta-btn"
        >
          {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          Evaluar desviación
        </button>
        <button
          onClick={() => disparar(true)}
          disabled={sending}
          className="inline-flex items-center gap-1 bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 text-sm font-semibold px-3 py-2 rounded-lg border border-rose-500/30 disabled:opacity-50"
          data-testid="forzar-alerta-btn"
          title="Envía WhatsApp real ahora, sin importar el umbral"
        >
          <MessageCircle className="h-4 w-4" />
          Probar envío real
        </button>
        <button
          onClick={() => setShowHistorial((v) => !v)}
          className="inline-flex items-center gap-1 bg-[#0F0F14] hover:bg-white/5 text-white/70 text-sm font-medium px-3 py-2 rounded-lg border border-white/10"
          data-testid="toggle-historial-alertas-btn"
        >
          <History className="h-4 w-4" />
          {showHistorial ? 'Ocultar' : 'Ver'} historial ({historial.length})
        </button>
      </div>

      {/* Resultado del último intento */}
      {ultimoResultado && (
        <div
          className={`mb-3 p-3 rounded-lg border text-xs ${
            ultimoResultado.error
              ? 'bg-rose-500/10 border-rose-500/30 text-rose-200'
              : ultimoResultado.alerta_enviada
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200'
              : 'bg-amber-500/10 border-amber-500/30 text-amber-200'
          }`}
          data-testid="alerta-resultado"
        >
          {ultimoResultado.error ? (
            <div>❌ {ultimoResultado.razon}</div>
          ) : ultimoResultado.alerta_enviada ? (
            <div>
              <div className="font-semibold mb-1">
                ✅ Alerta enviada a {ultimoResultado.destinatarios_exitosos}/{ultimoResultado.destinatarios_total} directores
              </div>
              <div>
                Semana {ultimoResultado.semana_evaluada} · Desviación {ultimoResultado.desviacion_pct?.toFixed(1)}%
                · Real {ultimoResultado.avance_real_pct?.toFixed(1)}% vs Esperado {ultimoResultado.avance_esperado_pct?.toFixed(1)}%
              </div>
              {ultimoResultado.recomendacion && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-emerald-300">Ver recomendación IA</summary>
                  <pre className="mt-2 whitespace-pre-wrap text-white/80 font-sans text-xs">
                    {ultimoResultado.recomendacion}
                  </pre>
                </details>
              )}
            </div>
          ) : (
            <div>
              ℹ️ {ultimoResultado.razon}
              {ultimoResultado.desviacion_pct != null && (
                <div className="mt-1 text-white/60">
                  Desviación actual: {ultimoResultado.desviacion_pct.toFixed(1)}%
                  (Real {ultimoResultado.avance_real_pct?.toFixed(1)}% vs Esperado {ultimoResultado.avance_esperado_pct?.toFixed(1)}%)
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Historial */}
      {showHistorial && (
        <div className="space-y-2" data-testid="historial-alertas-lista">
          {loading ? (
            <div className="flex justify-center py-4">
              <Loader2 className="h-4 w-4 text-cyan-400 animate-spin" />
            </div>
          ) : historial.length === 0 ? (
            <div className="text-center py-4 text-white/40 text-sm">
              Aún no se ha enviado ninguna alerta para este proyecto.
            </div>
          ) : (
            historial.map((a, idx) => (
              <div
                key={a.key || idx}
                className="bg-[#0F0F14] rounded-lg p-3 border border-white/10 text-sm"
              >
                <div className="flex items-center justify-between flex-wrap gap-1">
                  <div className="text-white/90 font-medium">
                    Semana {a.semana_evaluada}
                    <span className="ml-2 text-xs text-rose-300">
                      ({a.desviacion_pct?.toFixed(1)}%)
                    </span>
                  </div>
                  <div className="text-xs text-white/40">
                    {new Date(a.enviado_at).toLocaleString('es-MX')}
                  </div>
                </div>
                <div className="text-xs text-white/60 mt-1">
                  {a.exitosos}/{a.destinatarios} directores · {a.trigger === 'auto' ? 'Auto' : 'Manual'}
                </div>
                {a.recomendacion && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-cyan-300 text-xs">Ver recomendación IA</summary>
                    <pre className="mt-2 whitespace-pre-wrap text-white/70 font-sans text-xs">
                      {a.recomendacion}
                    </pre>
                  </details>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
