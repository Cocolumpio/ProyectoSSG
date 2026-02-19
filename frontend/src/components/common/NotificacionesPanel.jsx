import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { 
  Bell, X, Check, CheckCheck, Trash2, AlertTriangle, 
  AlertCircle, Info, CheckCircle, ChevronRight, Clock 
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function NotificacionesPanel({ isOpen, onClose, onNotificationClick }) {
  const [notificaciones, setNotificaciones] = useState([]);
  const [totalNoLeidas, setTotalNoLeidas] = useState(0);
  const [loading, setLoading] = useState(true);
  const [soloNoLeidas, setSoloNoLeidas] = useState(false);

  const fetchNotificaciones = useCallback(async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/notificaciones`, {
        params: { solo_no_leidas: soloNoLeidas, limite: 50 }
      });
      setNotificaciones(response.data.notificaciones || []);
      setTotalNoLeidas(response.data.total_no_leidas || 0);
    } catch (err) {
      console.error('Error fetching notificaciones:', err);
    } finally {
      setLoading(false);
    }
  }, [soloNoLeidas]);

  useEffect(() => {
    if (isOpen) {
      fetchNotificaciones();
    }
  }, [isOpen, fetchNotificaciones]);

  const handleMarcarLeida = async (notifId) => {
    try {
      await axios.put(`${API}/notificaciones/${notifId}/leer`);
      setNotificaciones(prev => 
        prev.map(n => n.id === notifId ? { ...n, leida: true } : n)
      );
      setTotalNoLeidas(prev => Math.max(0, prev - 1));
    } catch (err) {
      console.error('Error marcando como leída:', err);
    }
  };

  const handleMarcarTodasLeidas = async () => {
    try {
      await axios.put(`${API}/notificaciones/leer-todas`);
      setNotificaciones(prev => prev.map(n => ({ ...n, leida: true })));
      setTotalNoLeidas(0);
    } catch (err) {
      console.error('Error marcando todas como leídas:', err);
    }
  };

  const handleEliminar = async (notifId) => {
    try {
      await axios.delete(`${API}/notificaciones/${notifId}`);
      setNotificaciones(prev => prev.filter(n => n.id !== notifId));
    } catch (err) {
      console.error('Error eliminando notificación:', err);
    }
  };

  const getIconByType = (tipo) => {
    switch (tipo) {
      case 'error':
        return <AlertTriangle className="h-5 w-5 text-red-500" />;
      case 'warning':
        return <AlertCircle className="h-5 w-5 text-amber-500" />;
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'alert':
        return <AlertTriangle className="h-5 w-5 text-orange-500" />;
      default:
        return <Info className="h-5 w-5 text-blue-500" />;
    }
  };

  const getBgByType = (tipo, leida) => {
    if (leida) return 'bg-gray-50';
    switch (tipo) {
      case 'error':
        return 'bg-red-50';
      case 'warning':
        return 'bg-amber-50';
      case 'success':
        return 'bg-green-50';
      case 'alert':
        return 'bg-orange-50';
      default:
        return 'bg-blue-50';
    }
  };

  const formatFecha = (fechaStr) => {
    try {
      const fecha = new Date(fechaStr);
      const ahora = new Date();
      const diff = ahora - fecha;
      const minutos = Math.floor(diff / 60000);
      const horas = Math.floor(diff / 3600000);
      const dias = Math.floor(diff / 86400000);

      if (minutos < 1) return 'Ahora';
      if (minutos < 60) return `Hace ${minutos} min`;
      if (horas < 24) return `Hace ${horas}h`;
      if (dias < 7) return `Hace ${dias} días`;
      return fecha.toLocaleDateString('es-MX', { day: 'numeric', month: 'short' });
    } catch {
      return '';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/20" />
      
      {/* Panel */}
      <div 
        className="relative w-full max-w-md bg-white shadow-xl h-full flex flex-col animate-slide-in-right"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-4 py-3 z-10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell className="h-5 w-5 text-[#994B49]" />
              <h2 className="text-lg font-semibold text-gray-900">Notificaciones</h2>
              {totalNoLeidas > 0 && (
                <span className="bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                  {totalNoLeidas}
                </span>
              )}
            </div>
            <button 
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          
          {/* Filtros y acciones */}
          <div className="flex items-center justify-between mt-3">
            <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
              <input
                type="checkbox"
                checked={soloNoLeidas}
                onChange={(e) => setSoloNoLeidas(e.target.checked)}
                className="w-4 h-4 text-[#994B49] rounded border-gray-300 focus:ring-[#994B49]"
              />
              Solo no leídas
            </label>
            
            {totalNoLeidas > 0 && (
              <button
                onClick={handleMarcarTodasLeidas}
                className="flex items-center gap-1 text-sm text-[#994B49] hover:text-[#7D3C3A] transition-colors"
              >
                <CheckCheck className="h-4 w-4" />
                Marcar todas como leídas
              </button>
            )}
          </div>
        </div>

        {/* Lista de notificaciones */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-8 h-8 border-4 border-[#994B49] border-t-transparent rounded-full animate-spin" />
            </div>
          ) : notificaciones.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500">
              <Bell className="h-16 w-16 text-gray-300 mb-4" />
              <p className="font-medium">No hay notificaciones</p>
              <p className="text-sm">Te avisaremos cuando haya novedades</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {notificaciones.map((notif) => (
                <div
                  key={notif.id}
                  className={`p-4 transition-colors hover:bg-gray-50 ${getBgByType(notif.tipo, notif.leida)}`}
                >
                  <div className="flex gap-3">
                    {/* Icono */}
                    <div className="flex-shrink-0 mt-0.5">
                      {getIconByType(notif.tipo)}
                    </div>
                    
                    {/* Contenido */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <h3 className={`text-sm font-medium ${notif.leida ? 'text-gray-600' : 'text-gray-900'}`}>
                          {notif.titulo}
                        </h3>
                        <span className="flex-shrink-0 text-xs text-gray-400 flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatFecha(notif.fecha)}
                        </span>
                      </div>
                      
                      <p className={`text-sm mt-1 ${notif.leida ? 'text-gray-400' : 'text-gray-600'}`}>
                        {notif.mensaje}
                      </p>
                      
                      {notif.proyecto_nombre && (
                        <p className="text-xs text-[#994B49] mt-1 font-medium">
                          {notif.proyecto_nombre}
                        </p>
                      )}
                      
                      {/* Acciones */}
                      <div className="flex items-center gap-2 mt-2">
                        {!notif.leida && (
                          <button
                            onClick={() => handleMarcarLeida(notif.id)}
                            className="flex items-center gap-1 text-xs text-gray-500 hover:text-[#994B49] transition-colors"
                          >
                            <Check className="h-3.5 w-3.5" />
                            Marcar como leída
                          </button>
                        )}
                        
                        {notif.link && (
                          <button
                            onClick={() => {
                              handleMarcarLeida(notif.id);
                              onNotificationClick && onNotificationClick(notif);
                              onClose();
                            }}
                            className="flex items-center gap-1 text-xs text-[#994B49] hover:text-[#7D3C3A] transition-colors"
                          >
                            Ver detalles
                            <ChevronRight className="h-3.5 w-3.5" />
                          </button>
                        )}
                        
                        <button
                          onClick={() => handleEliminar(notif.id)}
                          className="flex items-center gap-1 text-xs text-gray-400 hover:text-red-500 transition-colors ml-auto"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                    
                    {/* Indicador no leída */}
                    {!notif.leida && (
                      <div className="flex-shrink-0">
                        <div className="w-2.5 h-2.5 bg-[#994B49] rounded-full" />
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        @keyframes slide-in-right {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }
        .animate-slide-in-right {
          animation: slide-in-right 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}

// Componente del botón de notificaciones para el header
export function NotificacionesBadge({ onClick }) {
  const [totalNoLeidas, setTotalNoLeidas] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchCount = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/notificaciones`, {
        params: { solo_no_leidas: true, limite: 1 }
      });
      setTotalNoLeidas(response.data.total_no_leidas || 0);
    } catch (err) {
      console.error('Error fetching notification count:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCount();
    // Refrescar cada 30 segundos
    const interval = setInterval(fetchCount, 30000);
    return () => clearInterval(interval);
  }, [fetchCount]);

  return (
    <button
      onClick={onClick}
      className="relative p-2 text-gray-600 hover:text-[#994B49] hover:bg-gray-100 rounded-lg transition-colors"
      data-testid="notificaciones-btn"
    >
      <Bell className="h-5 w-5" />
      {!loading && totalNoLeidas > 0 && (
        <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-xs font-bold min-w-[18px] h-[18px] flex items-center justify-center rounded-full px-1">
          {totalNoLeidas > 99 ? '99+' : totalNoLeidas}
        </span>
      )}
    </button>
  );
}
