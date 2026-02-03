import { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  ClipboardList, Clock, CheckCircle, XCircle, AlertCircle, 
  Send, X, User, Calendar, MessageSquare 
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const estadoConfig = {
  pendiente: { color: 'bg-yellow-100 text-yellow-700 border-yellow-300', icon: Clock, label: 'Pendiente' },
  confirmado: { color: 'bg-green-100 text-green-700 border-green-300', icon: CheckCircle, label: 'Confirmado' },
  completado: { color: 'bg-blue-100 text-blue-700 border-blue-300', icon: CheckCircle, label: 'Completado' },
  cancelado: { color: 'bg-red-100 text-red-700 border-red-300', icon: XCircle, label: 'Cancelado' }
};

export function SolicitudesAdminView({ onShowSuccess }) {
  const [solicitudes, setSolicitudes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtroEstado, setFiltroEstado] = useState('todos');
  const [selectedSolicitud, setSelectedSolicitud] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [comentario, setComentario] = useState('');
  const [updating, setUpdating] = useState(false);

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

  useEffect(() => {
    fetchSolicitudes();
  }, []);

  const solicitudesFiltradas = filtroEstado === 'todos' 
    ? solicitudes 
    : solicitudes.filter(s => s.estado === filtroEstado);

  const handleOpenModal = (solicitud) => {
    setSelectedSolicitud(solicitud);
    setComentario(solicitud.comentario_admin || '');
    setShowModal(true);
  };

  const handleUpdateEstado = async (nuevoEstado) => {
    if (!selectedSolicitud) return;
    
    setUpdating(true);
    try {
      await axios.put(`${API}/solicitudes-vuelo/${selectedSolicitud.id}/estado`, {
        estado: nuevoEstado,
        comentario_admin: comentario || null
      });
      
      onShowSuccess?.(`Solicitud ${nuevoEstado === 'confirmado' ? 'confirmada' : nuevoEstado === 'cancelado' ? 'cancelada' : 'actualizada'} correctamente`);
      setShowModal(false);
      fetchSolicitudes();
    } catch (error) {
      console.error('Error updating solicitud:', error);
      alert('Error al actualizar la solicitud');
    } finally {
      setUpdating(false);
    }
  };

  const contadores = {
    pendiente: solicitudes.filter(s => s.estado === 'pendiente').length,
    confirmado: solicitudes.filter(s => s.estado === 'confirmado').length,
    completado: solicitudes.filter(s => s.estado === 'completado').length,
    cancelado: solicitudes.filter(s => s.estado === 'cancelado').length
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
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900">Solicitudes de Vuelo</h2>
          <p className="text-gray-500 text-sm">Gestiona las solicitudes de los clientes</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {Object.entries(estadoConfig).map(([estado, config]) => {
          const Icon = config.icon;
          return (
            <button
              key={estado}
              onClick={() => setFiltroEstado(filtroEstado === estado ? 'todos' : estado)}
              className={`p-4 rounded-xl border-2 transition-all ${
                filtroEstado === estado 
                  ? 'border-[#994B49] bg-[#994B49]/5' 
                  : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <Icon className={`h-5 w-5 ${filtroEstado === estado ? 'text-[#994B49]' : 'text-gray-400'}`} />
                <span className={`text-2xl font-bold ${filtroEstado === estado ? 'text-[#994B49]' : 'text-gray-900'}`}>
                  {contadores[estado]}
                </span>
              </div>
              <p className={`text-sm mt-1 ${filtroEstado === estado ? 'text-[#994B49]' : 'text-gray-500'}`}>
                {config.label}
              </p>
            </button>
          );
        })}
      </div>

      {/* Lista de Solicitudes */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {solicitudesFiltradas.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <ClipboardList className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>No hay solicitudes {filtroEstado !== 'todos' && `con estado "${filtroEstado}"`}</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {solicitudesFiltradas.map((solicitud) => {
              const config = estadoConfig[solicitud.estado] || estadoConfig.pendiente;
              const Icon = config.icon;
              
              return (
                <div
                  key={solicitud.id}
                  className="p-4 sm:p-6 hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => handleOpenModal(solicitud)}
                  data-testid={`solicitud-${solicitud.id}`}
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
                      
                      <div className="flex flex-wrap gap-4 text-sm text-gray-500">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          Vuelo: {solicitud.fecha_vuelo_deseada}
                          {solicitud.hora_preferencia && ` a las ${solicitud.hora_preferencia}`}
                        </span>
                        {solicitud.cliente_nombre && (
                          <span className="flex items-center gap-1">
                            <User className="h-4 w-4" />
                            {solicitud.cliente_nombre}
                          </span>
                        )}
                      </div>
                      
                      {solicitud.notas && (
                        <p className="mt-2 text-sm text-gray-600 line-clamp-1">
                          "{solicitud.notas}"
                        </p>
                      )}
                    </div>
                    
                    <div className="text-right text-sm text-gray-400">
                      {new Date(solicitud.created_at).toLocaleDateString('es-MX')}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Modal de Gestión */}
      {showModal && selectedSolicitud && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Gestionar Solicitud</h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-6 w-6" />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              {/* Detalles */}
              <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Proyecto</p>
                  <p className="font-semibold text-gray-900">{selectedSolicitud.nombre_proyecto}</p>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Fecha de Vuelo</p>
                    <p className="font-medium text-gray-900">{selectedSolicitud.fecha_vuelo_deseada}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Hora Preferida</p>
                    <p className="font-medium text-gray-900">{selectedSolicitud.hora_preferencia || 'Sin preferencia'}</p>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Inicio Proyecto</p>
                    <p className="font-medium text-gray-900">{selectedSolicitud.fecha_inicio_proyecto}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Fin Proyecto</p>
                    <p className="font-medium text-gray-900">{selectedSolicitud.fecha_fin_proyecto}</p>
                  </div>
                </div>
                
                {selectedSolicitud.cliente_nombre && (
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Cliente</p>
                    <p className="font-medium text-gray-900">
                      {selectedSolicitud.cliente_nombre}
                      {selectedSolicitud.cliente_email && (
                        <span className="text-gray-500 font-normal"> ({selectedSolicitud.cliente_email})</span>
                      )}
                    </p>
                  </div>
                )}
                
                {selectedSolicitud.notas && (
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wide">Notas del Cliente</p>
                    <p className="text-gray-700">{selectedSolicitud.notas}</p>
                  </div>
                )}
              </div>

              {/* Estado Actual */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">Estado actual:</span>
                <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium border ${estadoConfig[selectedSolicitud.estado]?.color}`}>
                  {estadoConfig[selectedSolicitud.estado]?.label}
                </span>
              </div>

              {/* Comentario */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  <MessageSquare className="h-4 w-4 inline mr-1" />
                  Comentario para el cliente
                </label>
                <textarea
                  value={comentario}
                  onChange={(e) => setComentario(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                  placeholder="Escribe un mensaje para el cliente (opcional)..."
                  data-testid="solicitud-comentario"
                />
                {selectedSolicitud.cliente_email && (
                  <p className="text-xs text-gray-500 mt-1">
                    Se enviará notificación a: {selectedSolicitud.cliente_email}
                  </p>
                )}
              </div>

              {/* Acciones */}
              <div className="flex flex-col sm:flex-row gap-3 pt-4">
                {selectedSolicitud.estado === 'pendiente' && (
                  <>
                    <button
                      onClick={() => handleUpdateEstado('confirmado')}
                      disabled={updating}
                      className="flex-1 py-3 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                      data-testid="confirm-solicitud-btn"
                    >
                      <CheckCircle className="h-5 w-5" />
                      Confirmar Vuelo
                    </button>
                    <button
                      onClick={() => handleUpdateEstado('cancelado')}
                      disabled={updating}
                      className="flex-1 py-3 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                      data-testid="cancel-solicitud-btn"
                    >
                      <XCircle className="h-5 w-5" />
                      Rechazar
                    </button>
                  </>
                )}
                
                {selectedSolicitud.estado === 'confirmado' && (
                  <button
                    onClick={() => handleUpdateEstado('completado')}
                    disabled={updating}
                    className="flex-1 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                    data-testid="complete-solicitud-btn"
                  >
                    <CheckCircle className="h-5 w-5" />
                    Marcar como Completado
                  </button>
                )}
                
                {(selectedSolicitud.estado === 'completado' || selectedSolicitud.estado === 'cancelado') && (
                  <button
                    onClick={() => handleUpdateEstado('pendiente')}
                    disabled={updating}
                    className="flex-1 py-3 bg-yellow-600 text-white rounded-lg font-medium hover:bg-yellow-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    <AlertCircle className="h-5 w-5" />
                    Reabrir Solicitud
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
