export function ProjectFormContent({ formData, setFormData, error, saving, isEdit, onSubmit, onClose }) {
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleCoordChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      coordenadas: { ...prev.coordenadas, [field]: parseFloat(value) || 0 }
    }));
  };

  const handleVolumetriaChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      volumetria: { ...prev.volumetria, [field]: parseFloat(value) || 0 }
    }));
  };

  return (
    <form onSubmit={onSubmit} className="p-6 space-y-4">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Nombre del Proyecto *
          </label>
          <input
            type="text"
            name="nombre"
            value={formData.nombre}
            onChange={handleInputChange}
            required
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            placeholder="Ej: Hotel Marriott"
            data-testid="project-name-input"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Ubicación *
          </label>
          <input
            type="text"
            name="ubicacion"
            value={formData.ubicacion}
            onChange={handleInputChange}
            required
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            placeholder="Ej: Guadalajara, Jalisco"
            data-testid="project-location-input"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Latitud *
          </label>
          <input
            type="number"
            step="any"
            value={formData.coordenadas.lat}
            onChange={(e) => handleCoordChange('lat', e.target.value)}
            required
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            placeholder="20.6597"
            data-testid="project-lat-input"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Longitud *
          </label>
          <input
            type="number"
            step="any"
            value={formData.coordenadas.lng}
            onChange={(e) => handleCoordChange('lng', e.target.value)}
            required
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            placeholder="-103.3496"
            data-testid="project-lng-input"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Fecha de Inicio *
          </label>
          <input
            type="date"
            name="fecha_inicio"
            value={formData.fecha_inicio}
            onChange={handleInputChange}
            required
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            data-testid="project-start-date-input"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Fecha de Fin Planeada *
          </label>
          <input
            type="date"
            name="fecha_fin_planeada"
            value={formData.fecha_fin_planeada}
            onChange={handleInputChange}
            required
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            data-testid="project-end-date-input"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Avance Actual (%)
        </label>
        <div className="relative">
          <input
            type="number"
            name="avance_actual"
            value={formData.avance_actual}
            onChange={handleInputChange}
            min="0"
            max="100"
            step="0.1"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            placeholder="0"
            data-testid="project-progress-input"
          />
          <div className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-500">
            %
          </div>
        </div>
        <div className="mt-2">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-[#994B49] h-2 rounded-full transition-all"
              style={{ width: `${formData.avance_actual}%` }}
            />
          </div>
        </div>
      </div>

      {/* URL de Pix4D */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          URL del Modelo 3D (Pix4D)
        </label>
        <input
          type="url"
          name="pix4d_url"
          value={formData.pix4d_url}
          onChange={handleInputChange}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
          placeholder="https://cloud.pix4d.com/embed/?projectId=..."
          data-testid="project-pix4d-input"
        />
        <p className="text-xs text-gray-500 mt-1">
          Pega la URL del iframe de Pix4D para visualizar el modelo 3D
        </p>
      </div>

      {/* Volumetrías */}
      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
        <h4 className="font-medium text-gray-900 mb-3">Volumetría del Proyecto (m³)</h4>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Excavación</label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={formData.volumetria.excavacion}
              onChange={(e) => handleVolumetriaChange('excavacion', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
              data-testid="project-vol-excavacion-input"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Relleno</label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={formData.volumetria.relleno}
              onChange={(e) => handleVolumetriaChange('relleno', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
              data-testid="project-vol-relleno-input"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Materiales</label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={formData.volumetria.materiales}
              onChange={(e) => handleVolumetriaChange('materiales', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
              data-testid="project-vol-materiales-input"
            />
          </div>
        </div>
      </div>

      {/* Configuración de Flotilla de Camiones */}
      <div className="bg-amber-50 rounded-lg p-4 border border-amber-200">
        <h4 className="font-medium text-gray-900 mb-3 flex items-center">
          <span className="mr-2">🚛</span>
          Configuración de Flotilla de Camiones
        </h4>
        <p className="text-xs text-gray-500 mb-3">
          Estos valores se usarán para calcular los costos de retiro de material en el reporte ejecutivo
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Capacidad por Camión</label>
            <div className="relative">
              <input
                type="number"
                step="0.1"
                min="1"
                value={formData.capacidad_camion}
                onChange={(e) => setFormData(prev => ({ ...prev, capacidad_camion: parseFloat(e.target.value) || 25 }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                data-testid="project-capacidad-camion-input"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">m³</span>
            </div>
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Costo por Viaje</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">$</span>
              <input
                type="number"
                step="100"
                min="0"
                value={formData.costo_viaje_camion}
                onChange={(e) => setFormData(prev => ({ ...prev, costo_viaje_camion: parseFloat(e.target.value) || 2500 }))}
                className="w-full pl-7 pr-14 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                data-testid="project-costo-viaje-input"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">MXN</span>
            </div>
          </div>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Descripción
        </label>
        <textarea
          name="descripcion"
          value={formData.descripcion}
          onChange={handleInputChange}
          rows={3}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
          placeholder="Descripción del proyecto..."
          data-testid="project-description-input"
        />
      </div>

      <div className="flex items-center justify-end space-x-3 pt-4">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          data-testid="project-cancel-btn"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={saving}
          className="px-6 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="project-submit-btn"
        >
          {saving ? 'Guardando...' : (isEdit ? 'Guardar Cambios' : 'Crear Proyecto')}
        </button>
      </div>
    </form>
  );
}
