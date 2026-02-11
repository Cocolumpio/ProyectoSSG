import { useState, useEffect, useRef } from 'react';
import { MapPin, Search, Loader2 } from 'lucide-react';

export function ProjectFormContent({ formData, setFormData, error, saving, isEdit, onSubmit, onClose }) {
  const [searchingAddress, setSearchingAddress] = useState(false);
  const [addressSuggestions, setAddressSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [addressInput, setAddressInput] = useState(formData.direccion || formData.ubicacion || '');
  const searchTimeout = useRef(null);
  const suggestionsRef = useRef(null);

  useEffect(() => {
    // Set initial address from formData
    if (formData.direccion) {
      setAddressInput(formData.direccion);
    } else if (formData.ubicacion && !addressInput) {
      setAddressInput(formData.ubicacion);
    }
  }, [formData.direccion, formData.ubicacion]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleVolumetriaChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      volumetria: { ...prev.volumetria, [field]: parseFloat(value) || 0 }
    }));
  };

  const searchAddress = async (query) => {
    if (query.length < 3) {
      setAddressSuggestions([]);
      return;
    }

    setSearchingAddress(true);
    try {
      // Using Nominatim (OpenStreetMap) for geocoding - free service
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&countrycodes=mx&limit=5`,
        {
          headers: {
            'Accept-Language': 'es'
          }
        }
      );
      const data = await response.json();
      setAddressSuggestions(data);
      setShowSuggestions(data.length > 0);
    } catch (err) {
      console.error('Error searching address:', err);
      setAddressSuggestions([]);
    } finally {
      setSearchingAddress(false);
    }
  };

  const handleAddressInputChange = (e) => {
    const value = e.target.value;
    setAddressInput(value);
    
    // Debounce search
    if (searchTimeout.current) {
      clearTimeout(searchTimeout.current);
    }
    
    searchTimeout.current = setTimeout(() => {
      searchAddress(value);
    }, 500);
  };

  const selectAddress = (suggestion) => {
    const displayName = suggestion.display_name;
    const lat = parseFloat(suggestion.lat);
    const lng = parseFloat(suggestion.lon);
    
    setAddressInput(displayName);
    setFormData(prev => ({
      ...prev,
      direccion: displayName,
      ubicacion: displayName.split(',').slice(0, 2).join(',').trim(), // Short version for display
      coordenadas: { lat, lng }
    }));
    setShowSuggestions(false);
    setAddressSuggestions([]);
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
      </div>

      {/* Address Search Field */}
      <div className="relative" ref={suggestionsRef}>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          <MapPin className="inline h-4 w-4 mr-1" />
          Dirección de la Obra *
        </label>
        <div className="relative">
          <input
            type="text"
            value={addressInput}
            onChange={handleAddressInputChange}
            onFocus={() => addressSuggestions.length > 0 && setShowSuggestions(true)}
            required
            className="w-full px-4 py-2 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
            placeholder="Escribe la dirección y selecciona de la lista..."
            data-testid="project-address-input"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            {searchingAddress ? (
              <Loader2 className="h-5 w-5 text-gray-400 animate-spin" />
            ) : (
              <Search className="h-5 w-5 text-gray-400" />
            )}
          </div>
        </div>
        
        {/* Address Suggestions Dropdown */}
        {showSuggestions && addressSuggestions.length > 0 && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
            {addressSuggestions.map((suggestion, index) => (
              <button
                key={index}
                type="button"
                onClick={() => selectAddress(suggestion)}
                className="w-full px-4 py-3 text-left hover:bg-gray-50 border-b border-gray-100 last:border-b-0 flex items-start space-x-2"
              >
                <MapPin className="h-4 w-4 text-[#994B49] mt-0.5 flex-shrink-0" />
                <span className="text-sm text-gray-700">{suggestion.display_name}</span>
              </button>
            ))}
          </div>
        )}
        
        {/* Show selected coordinates */}
        {formData.coordenadas && formData.coordenadas.lat !== 0 && (
          <p className="mt-1 text-xs text-gray-500">
            📍 Coordenadas: {formData.coordenadas.lat.toFixed(6)}, {formData.coordenadas.lng.toFixed(6)}
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
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
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Volumen Total Planeado (m³) *
          </label>
          <div className="relative">
            <input
              type="number"
              name="volumen_total_planeado"
              value={formData.volumen_total_planeado || ''}
              onChange={handleInputChange}
              min="0"
              step="100"
              placeholder="Ej: 50000"
              className="w-full px-4 py-2 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
              data-testid="project-volumen-planeado-input"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">m³</span>
          </div>
          <p className="text-xs text-gray-500 mt-1">Total de volumen estimado a excavar según el programa del cliente</p>
        </div>
      </div>

      {/* Avance calculado automáticamente */}
      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-medium text-blue-900 mb-1">📊 Avance del Proyecto</h4>
            <p className="text-xs text-blue-700">
              El porcentaje se calcula automáticamente: (Volumen excavado / Volumen planeado) × 100
            </p>
          </div>
          <div className="text-right">
            <span className="text-3xl font-bold text-blue-600">{formData.avance_actual || 0}%</span>
          </div>
        </div>
        {formData.volumen_total_planeado > 0 && (
          <div className="mt-3">
            <div className="w-full bg-blue-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all" 
                style={{ width: `${Math.min(formData.avance_actual || 0, 100)}%` }} 
              />
            </div>
          </div>
        )}
      </div>

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
          placeholder="https://cloud.pix4d.com/embed/..."
          data-testid="project-pix4d-input"
        />
      </div>

      {/* Volumetría Section */}
      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
        <h4 className="font-medium text-gray-900 mb-3">📊 Volumetría del Proyecto (m³)</h4>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Excavación</label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={formData.volumetria.excavacion}
              onChange={(e) => handleVolumetriaChange('excavacion', e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
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
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
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
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
              data-testid="project-vol-materiales-input"
            />
          </div>
        </div>
      </div>

      {/* Fleet Configuration Section */}
      <div className="bg-amber-50 rounded-lg p-4 border border-amber-200">
        <h4 className="font-medium text-gray-900 mb-1">🚛 Configuración de Flotilla de Camiones</h4>
        <p className="text-xs text-gray-500 mb-3">Estos valores se usarán para calcular los costos de retiro de material en el reporte ejecutivo</p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Capacidad por Camión</label>
            <div className="relative">
              <input
                type="number"
                step="1"
                min="1"
                value={formData.capacidad_camion}
                onChange={(e) => setFormData(prev => ({ ...prev, capacidad_camion: parseFloat(e.target.value) || 25 }))}
                className="w-full px-4 py-2 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                data-testid="project-capacidad-camion-input"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">m³</span>
            </div>
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Costo por m³</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">$</span>
              <input
                type="number"
                step="10"
                min="0"
                value={formData.costo_m3}
                onChange={(e) => setFormData(prev => ({ ...prev, costo_m3: parseFloat(e.target.value) || 150 }))}
                className="w-full pl-7 pr-14 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                data-testid="project-costo-m3-input"
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
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={saving}
          className="px-6 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors disabled:opacity-50"
          data-testid="project-submit-btn"
        >
          {saving ? 'Guardando...' : (isEdit ? 'Guardar Cambios' : 'Crear Proyecto')}
        </button>
      </div>
    </form>
  );
}
