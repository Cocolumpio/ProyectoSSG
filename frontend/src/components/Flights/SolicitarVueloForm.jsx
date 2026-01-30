import { useState } from 'react';
import axios from 'axios';
import { Calendar, Clock, FileText, Send, CheckCircle, Plane } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function SolicitarVueloForm({ onSuccess }) {
  const [formData, setFormData] = useState({
    nombre_proyecto: '',
    fecha_inicio_proyecto: '',
    fecha_fin_proyecto: '',
    fecha_vuelo_deseada: '',
    hora_preferencia: '',
    notas: ''
  });
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSending(true);
    setError(null);

    try {
      const response = await axios.post(`${API}/solicitudes-vuelo`, formData);
      
      if (response.data.status === 'success' || response.data.status === 'partial') {
        setSent(true);
        if (onSuccess) onSuccess(response.data);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al enviar la solicitud. Por favor intenta de nuevo.');
    } finally {
      setSending(false);
    }
  };

  const resetForm = () => {
    setFormData({
      nombre_proyecto: '',
      fecha_inicio_proyecto: '',
      fecha_fin_proyecto: '',
      fecha_vuelo_deseada: '',
      hora_preferencia: '',
      notas: ''
    });
    setSent(false);
    setError(null);
  };

  if (sent) {
    return (
      <div className="bg-white rounded-2xl shadow-lg p-8 max-w-xl mx-auto text-center">
        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <CheckCircle className="h-10 w-10 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-3">¡Solicitud Enviada!</h2>
        <p className="text-gray-600 mb-6">
          Tu solicitud de vuelo ha sido enviada correctamente. 
          Nos pondremos en contacto contigo para confirmar la fecha.
        </p>
        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <p className="text-sm text-gray-500">Detalles de la solicitud:</p>
          <p className="font-semibold text-gray-900">{formData.nombre_proyecto}</p>
          <p className="text-[#994B49]">{formData.fecha_vuelo_deseada} {formData.hora_preferencia && `a las ${formData.hora_preferencia}`}</p>
        </div>
        <button
          onClick={resetForm}
          className="px-6 py-3 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors font-medium"
        >
          Enviar otra solicitud
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg overflow-hidden max-w-xl mx-auto">
      {/* Header */}
      <div className="bg-[#994B49] text-white px-6 py-5">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
            <Plane className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold">Programar Vuelo de Dron</h2>
            <p className="text-white/80 text-sm">DrON Topografía</p>
          </div>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="p-6 space-y-5">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Nombre del Proyecto */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            <FileText className="h-4 w-4 inline mr-2 text-[#994B49]" />
            Nombre del Proyecto *
          </label>
          <input
            type="text"
            name="nombre_proyecto"
            value={formData.nombre_proyecto}
            onChange={handleChange}
            required
            placeholder="Ej: Construcción Plaza Norte"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49] focus:border-transparent transition-all"
            data-testid="solicitud-nombre-input"
          />
        </div>

        {/* Fechas del Proyecto */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Calendar className="h-4 w-4 inline mr-2 text-[#994B49]" />
              Inicio del Proyecto *
            </label>
            <input
              type="date"
              name="fecha_inicio_proyecto"
              value={formData.fecha_inicio_proyecto}
              onChange={handleChange}
              required
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49] focus:border-transparent transition-all"
              data-testid="solicitud-fecha-inicio-input"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Calendar className="h-4 w-4 inline mr-2 text-[#994B49]" />
              Fin del Proyecto *
            </label>
            <input
              type="date"
              name="fecha_fin_proyecto"
              value={formData.fecha_fin_proyecto}
              onChange={handleChange}
              required
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49] focus:border-transparent transition-all"
              data-testid="solicitud-fecha-fin-input"
            />
          </div>
        </div>

        {/* Fecha y Hora del Vuelo */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <h3 className="font-medium text-amber-800 mb-3 flex items-center">
            <Plane className="h-4 w-4 mr-2" />
            Fecha deseada para el vuelo
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Fecha *</label>
              <input
                type="date"
                name="fecha_vuelo_deseada"
                value={formData.fecha_vuelo_deseada}
                onChange={handleChange}
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49] focus:border-transparent transition-all bg-white"
                data-testid="solicitud-fecha-vuelo-input"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">
                <Clock className="h-3 w-3 inline mr-1" />
                Hora preferida
              </label>
              <input
                type="time"
                name="hora_preferencia"
                value={formData.hora_preferencia}
                onChange={handleChange}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49] focus:border-transparent transition-all bg-white"
                data-testid="solicitud-hora-input"
              />
            </div>
          </div>
        </div>

        {/* Notas */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            📝 Notas y Peticiones Específicas
          </label>
          <textarea
            name="notas"
            value={formData.notas}
            onChange={handleChange}
            rows={4}
            placeholder="Describe cualquier requerimiento especial, áreas específicas a cubrir, restricciones de horario, etc."
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49] focus:border-transparent transition-all resize-none"
            data-testid="solicitud-notas-input"
          />
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={sending}
          className="w-full py-4 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors font-medium text-lg flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="solicitud-submit-btn"
        >
          {sending ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              <span>Enviando solicitud...</span>
            </>
          ) : (
            <>
              <Send className="h-5 w-5" />
              <span>Enviar Solicitud de Vuelo</span>
            </>
          )}
        </button>

        <p className="text-xs text-gray-500 text-center">
          Al enviar esta solicitud, recibirás una confirmación por parte de nuestro equipo.
        </p>
      </form>
    </div>
  );
}
