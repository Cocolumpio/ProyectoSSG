import { useEffect, useState } from 'react';
import axios from 'axios';
import { Calendar, Loader2, Check, Link2, Unlink, Plane } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Panel para conectar Google Calendar y generar vuelos automáticos
 * a partir del programa de obra del proyecto.
 */
export function GoogleCalendarPanel({ proyectoId, tieneProgramaSemanal }) {
  const [status, setStatus] = useState({ connected: false });
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [disconnecting, setDisconnecting] = useState(false);

  useEffect(() => {
    fetchStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Detectar callback exitoso: ?google_calendar=connected
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('google_calendar') === 'connected') {
      // Limpiar query y refrescar status
      window.history.replaceState({}, document.title, window.location.pathname);
      fetchStatus();
    }
  }, []);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/oauth/calendar/status`);
      setStatus(r.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const conectar = async () => {
    try {
      const baseUrl = process.env.REACT_APP_BACKEND_URL;
      const r = await axios.get(`${API}/oauth/calendar/login`, {
        params: { base_url: baseUrl },
      });
      window.location.href = r.data.authorization_url;
    } catch (e) {
      alert('Error iniciando OAuth: ' + (e?.response?.data?.detail || e.message));
    }
  };

  const desconectar = async () => {
    if (!window.confirm('¿Desconectar Google Calendar? Los eventos ya creados no se borrarán.')) return;
    setDisconnecting(true);
    try {
      await axios.delete(`${API}/oauth/calendar/disconnect`);
      await fetchStatus();
    } catch (e) {
      alert('Error: ' + (e?.response?.data?.detail || e.message));
    } finally {
      setDisconnecting(false);
    }
  };

  const generarVuelos = async () => {
    if (!proyectoId) return;
    setGenerating(true);
    setLastResult(null);
    try {
      const r = await axios.post(`${API}/proyectos/${proyectoId}/vuelos/generar`);
      setLastResult(r.data);
    } catch (e) {
      setLastResult({ error: e?.response?.data?.detail || e.message });
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-[#15151B] rounded-xl p-4 border border-white/10 flex items-center justify-center">
        <Loader2 className="h-5 w-5 text-cyan-400 animate-spin" />
      </div>
    );
  }

  return (
    <div
      className="bg-gradient-to-br from-cyan-500/5 to-blue-500/5 rounded-xl p-4 sm:p-5 border border-cyan-500/30"
      data-testid="google-calendar-panel"
    >
      <div className="flex items-start justify-between mb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Calendar className="h-5 w-5 text-cyan-400" />
          <div>
            <h3 className="font-semibold text-white text-sm">Programación Automática de Vuelos</h3>
            <p className="text-xs text-white/50 mt-0.5">
              Genera eventos en tu Google Calendar para cada semana del programa de obra.
            </p>
          </div>
        </div>
        {status.connected ? (
          <div
            className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-emerald-500/20 text-emerald-300"
            data-testid="gcal-connected"
          >
            <Check className="h-3 w-3" /> Conectado
          </div>
        ) : (
          <div className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-white/10 text-white/60">
            <Link2 className="h-3 w-3" /> Sin conectar
          </div>
        )}
      </div>

      {!status.connected ? (
        <button
          onClick={conectar}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-cyan-500 hover:bg-cyan-400 text-[#0B0B0F] font-semibold text-sm px-4 py-2 rounded-lg transition-colors"
          data-testid="gcal-connect-btn"
        >
          <Link2 className="h-4 w-4" /> Conectar Google Calendar
        </button>
      ) : (
        <>
          <div className="flex items-center gap-2 text-xs text-white/60 mb-3 flex-wrap">
            <span>Conectado como</span>
            <span className="font-mono text-emerald-300 bg-emerald-500/10 px-2 py-0.5 rounded">
              {status.google_email}
            </span>
            <button
              onClick={desconectar}
              disabled={disconnecting}
              className="text-rose-400 hover:text-rose-300 underline text-xs ml-1 inline-flex items-center gap-1"
              data-testid="gcal-disconnect-btn"
            >
              {disconnecting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Unlink className="h-3 w-3" />}
              desconectar
            </button>
          </div>

          {!tieneProgramaSemanal ? (
            <div className="text-xs text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded p-2">
              ⚠️ Este proyecto no tiene un programa de obra cargado. Sube un cronograma para activar la generación automática.
            </div>
          ) : (
            <button
              onClick={generarVuelos}
              disabled={generating}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-60 text-[#0B0B0F] font-semibold text-sm px-4 py-2 rounded-lg transition-colors"
              data-testid="gcal-generate-btn"
            >
              {generating ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Generando...</>
              ) : (
                <><Plane className="h-4 w-4" /> Generar vuelos automáticos en Calendar</>
              )}
            </button>
          )}

          {lastResult && (
            <div className="mt-3 text-xs">
              {lastResult.error ? (
                <div className="bg-rose-500/10 text-rose-300 border border-rose-500/30 rounded p-2">
                  ❌ {lastResult.error}
                </div>
              ) : (
                <div className="bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 rounded p-2">
                  ✅ {lastResult.creados} creados · {lastResult.actualizados} actualizados · {lastResult.saltados} saltados (de {lastResult.total_semanas} semanas).
                  {lastResult.eventos?.length > 0 && (
                    <div className="mt-1 text-white/60">
                      Primer evento: <a href={lastResult.eventos[0].html_link} target="_blank" rel="noreferrer" className="underline text-cyan-300">Ver en Google Calendar</a>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
