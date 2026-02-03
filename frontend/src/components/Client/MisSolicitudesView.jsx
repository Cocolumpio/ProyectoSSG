import { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  ClipboardList, Clock, CheckCircle, XCircle, Calendar, 
  Plus, MessageSquare 
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const estadoConfig = {
  pendiente: { color: 'bg-yellow-100 text-yellow-700 border-yellow-300', icon: Clock, label: 'Pendiente' },
  confirmado: { color: 'bg-green-100 text-green-700 border-green-300', icon: CheckCircle, label: 'Confirmado' },
  completado: { color: 'bg-blue-100 text-blue-700 border-blue-300', icon: CheckCircle, label: 'Completado' },
  cancelado: { color: 'bg-red-100 text-red-700 border-red-300', icon: XCircle, label: 'Rechazado' }
};

export function MisSolicitudesView({ onNuevaSolicitud }) {
  const [solicitudes, setSolicitudes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedSolicitud, setSelectedSolicitud] = useState(null);

  useEffect(() => {
    fetchSolicitudes();
  }, []);

  const fetchSolicitudes = async () => {
    try {
      const response = await axios.get(`${API}/solicitudes-vuelo`);
      setSolicitudes(response.data);
    } catch (error) {
      console.error('Error fetching solicitudes:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-8 h-8 border-4 border-[#994B49] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900">Mis Solicitudes de Vuelo</h2>
          <p className="text-gray-500 text-sm">Historial de tus solicitudes</p>
        </div>
        <button
          onClick={onNuevaSolicitud}
          className="flex items-center justify-center space-x-2 px-4 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors"
          data-testid="nueva-solicitud-btn"
        >
          <Plus className="h-5 w-5" />
          <span>Nueva Solicitud</span>
        </button>
      </div>

      {/* Lista de Solicitudes */}
      {solicitudes.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <ClipboardList className="h-12 w-12 mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No tienes solicitudes</h3>
          <p className="text-gray-500 mb-4">Solicita tu primer vuelo de dron</p>
          <button
            onClick={onNuevaSolicitud}
            className="px-4 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors"
          >
            Solicitar Vuelo
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {solicitudes.map((solicitud) => {
            const config = estadoConfig[solicitud.estado] || estadoConfig.pendiente;
            const Icon = config.icon;
            
            return (
              <div
                key={solicitud.id}
                className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => setSelectedSolicitud(selectedSolicitud?.id === solicitud.id ? null : solicitud)}
                data-testid={`mi-solicitud-${solicitud.id}`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold text-gray-900">{solicitud.nombre_proyecto}</h3>
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${config.color}`}>
                        <Icon className="h-3 w-3" />
                        {config.label}
                      </span>
                    </div>
                    
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <Calendar className="h-4 w-4" />
                      <span>Vuelo programado: {solicitud.fecha_vuelo_deseada}</span>
                      {solicitud.hora_preferencia && (
                        <span>a las {solicitud.hora_preferencia}</span>
                      )}
                    </div>
                  </div>
                  
                  <div className="text-sm text-gray-400">
                    Solicitado: {new Date(solicitud.created_at).toLocaleDateString('es-MX')}
                  </div>
                </div>

                {/* Detalles expandidos */}
                {selectedSolicitud?.id === solicitud.id && (
                  <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-gray-500">Inicio del proyecto</p>
                        <p className="font-medium">{solicitud.fecha_inicio_proyecto}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Fin del proyecto</p>
                        <p className="font-medium">{solicitud.fecha_fin_proyecto}</p>
                      </div>
                    </div>
                    
                    {solicitud.notas && (
                      <div>
                        <p className="text-sm text-gray-500">Tus notas:</p>
                        <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3 mt-1">
                          {solicitud.notas}
                        </p>
                      </div>
                    )}
                    
                    {solicitud.comentario_admin && (
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <div className="flex items-center gap-2 text-blue-700 mb-1">
                          <MessageSquare className="h-4 w-4" />
                          <span className="font-medium text-sm">Respuesta del administrador:</span>
                        </div>
                        <p className="text-blue-800">{solicitud.comentario_admin}</p>
                        {solicitud.fecha_respuesta && (
                          <p className="text-xs text-blue-500 mt-2">
                            Respondido: {new Date(solicitud.fecha_respuesta).toLocaleDateString('es-MX')}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
