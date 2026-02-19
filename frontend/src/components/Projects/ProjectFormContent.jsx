import { useState, useEffect, useRef } from 'react';
import { MapPin, Search, Loader2, Shovel, Columns3, Building2, Anchor, Info } from 'lucide-react';
import { CatalogoMaquinariaSection } from './CatalogoMaquinariaSection';

export function ProjectFormContent({ formData, setFormData, error, saving, isEdit, onSubmit, onClose, onShowSuccess }) {
  const [searchingAddress, setSearchingAddress] = useState(false);
  const [addressSuggestions, setAddressSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [addressInput, setAddressInput] = useState(formData.direccion || formData.ubicacion || '');
  const searchTimeout = useRef(null);
  const suggestionsRef = useRef(null);

  useEffect(() => {
    if (formData.direccion) {
      setAddressInput(formData.direccion);
    } else if (formData.ubicacion && !addressInput) {
      setAddressInput(formData.ubicacion);
    }
  }, [formData.direccion, formData.ubicacion]);

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

  const searchAddress = async (query) => {
    if (query.length < 3) {
      setAddressSuggestions([]);
      return;
    }

    setSearchingAddress(true);
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&countrycodes=mx&limit=5`,
        { headers: { 'Accept-Language': 'es' } }
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
      ubicacion: displayName.split(',').slice(0, 2).join(',').trim(),
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
            Semanas Planeadas de Trabajo *
          </label>
          <div className="relative">
            <input
              type="number"
              name="semanas_planeadas"
              value={formData.semanas_planeadas || ''}
              onChange={handleInputChange}
              min="1"
              step="1"
              placeholder="Ej: 12"
              className="w-full px-4 py-2 pr-16 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
              data-testid="project-semanas-planeadas-input"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">semanas</span>
          </div>
          <p className="text-xs text-gray-500 mt-1">Número de semanas de trabajo según el cronograma</p>
        </div>
      </div>

      {/* Fases de Construcción */}
      <div className="bg-gradient-to-r from-slate-50 to-slate-100 rounded-xl p-4 border border-slate-200">
        <div className="flex items-center gap-2 mb-3">
          <Building2 className="h-5 w-5 text-slate-700" />
          <h4 className="font-semibold text-slate-800">Fases de Construcción</h4>
          <span className="text-xs text-slate-500 bg-white px-2 py-0.5 rounded">(Selecciona una o más)</span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Excavación */}
          <div className={`rounded-lg p-4 border-2 transition-all ${
            formData.fases?.excavacion 
              ? 'bg-amber-50 border-amber-400 shadow-md' 
              : 'bg-white border-gray-200 hover:border-amber-300'
          }`}
            data-testid="fase-excavacion-toggle"
          >
            <div 
              className="flex items-center gap-2 mb-2 cursor-pointer"
              onClick={() => setFormData(prev => ({
                ...prev,
                fases: { ...prev.fases, excavacion: !prev.fases?.excavacion }
              }))}
            >
              <input
                type="checkbox"
                checked={formData.fases?.excavacion || false}
                onChange={() => setFormData(prev => ({
                  ...prev,
                  fases: { ...prev.fases, excavacion: !prev.fases?.excavacion }
                }))}
                className="h-4 w-4 text-amber-600 rounded focus:ring-amber-500 cursor-pointer"
              />
              <Shovel className="h-5 w-5 text-amber-600" />
              <span className="font-medium text-gray-800">Excavación</span>
            </div>
            {formData.fases?.excavacion && (
              <div className="mt-3 space-y-2" onClick={e => e.stopPropagation()}>
                <div>
                  <label className="text-xs text-amber-700 font-medium">Volumen Total (m³)</label>
                  <input
                    type="number"
                    min="0"
                    step="100"
                    value={formData.volumen_total_planeado || ''}
                    onChange={(e) => setFormData(prev => ({ 
                      ...prev, 
                      volumen_total_planeado: parseFloat(e.target.value) || 0 
                    }))}
                    className="w-full mt-1 px-3 py-1.5 text-sm border border-amber-300 rounded-lg focus:ring-2 focus:ring-amber-500"
                    placeholder="50000"
                    data-testid="project-volumen-planeado-input"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Cimentación */}
          <div className={`rounded-lg p-4 border-2 transition-all ${
            formData.fases?.cimentacion 
              ? 'bg-blue-50 border-blue-400 shadow-md' 
              : 'bg-white border-gray-200 hover:border-blue-300'
          }`}
            data-testid="fase-cimentacion-toggle"
          >
            <div 
              className="flex items-center gap-2 mb-2 cursor-pointer"
              onClick={() => setFormData(prev => ({
                ...prev,
                fases: { ...prev.fases, cimentacion: !prev.fases?.cimentacion }
              }))}
            >
              <input
                type="checkbox"
                checked={formData.fases?.cimentacion || false}
                onChange={() => setFormData(prev => ({
                  ...prev,
                  fases: { ...prev.fases, cimentacion: !prev.fases?.cimentacion }
                }))}
                className="h-4 w-4 text-blue-600 rounded focus:ring-blue-500 cursor-pointer"
              />
              <Columns3 className="h-5 w-5 text-blue-600" />
              <span className="font-medium text-gray-800">Cimentación</span>
            </div>
            {formData.fases?.cimentacion && (
              <div className="mt-3 space-y-2">
                <div>
                  <label className="text-xs text-blue-700 font-medium">Pilas Planeadas</label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={formData.pilas_planeadas || ''}
                    onChange={(e) => setFormData(prev => ({ 
                      ...prev, 
                      pilas_planeadas: parseInt(e.target.value) || 0 
                    }))}
                    className="w-full mt-1 px-3 py-1.5 text-sm border border-blue-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    placeholder="576"
                    data-testid="project-pilas-planeadas-input"
                  />
                </div>
                <div>
                  <label className="text-xs text-teal-700 font-medium">Anclas Planeadas</label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={formData.anclas_planeadas || ''}
                    onChange={(e) => setFormData(prev => ({ 
                      ...prev, 
                      anclas_planeadas: parseInt(e.target.value) || 0 
                    }))}
                    className="w-full mt-1 px-3 py-1.5 text-sm border border-teal-300 rounded-lg focus:ring-2 focus:ring-teal-500"
                    placeholder="464"
                    data-testid="project-anclas-planeadas-input"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Edificación */}
          <div className={`rounded-lg p-4 border-2 transition-all cursor-pointer ${
            formData.fases?.edificacion 
              ? 'bg-purple-50 border-purple-400 shadow-md' 
              : 'bg-white border-gray-200 hover:border-purple-300'
          }`}
            onClick={() => setFormData(prev => ({
              ...prev,
              fases: { ...prev.fases, edificacion: !prev.fases?.edificacion }
            }))}
            data-testid="fase-edificacion-toggle"
          >
            <div className="flex items-center gap-2 mb-2">
              <input
                type="checkbox"
                checked={formData.fases?.edificacion || false}
                onChange={() => {}}
                className="h-4 w-4 text-purple-600 rounded focus:ring-purple-500"
              />
              <Building2 className="h-5 w-5 text-purple-600" />
              <span className="font-medium text-gray-800">Edificación</span>
            </div>
            {formData.fases?.edificacion && (
              <div className="mt-3 space-y-2" onClick={e => e.stopPropagation()}>
                <div>
                  <label className="text-xs text-purple-700 font-medium">Muros Planeados</label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={formData.muros_planeados || ''}
                    onChange={(e) => setFormData(prev => ({ 
                      ...prev, 
                      muros_planeados: parseInt(e.target.value) || 0 
                    }))}
                    className="w-full mt-1 px-3 py-1.5 text-sm border border-purple-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                    placeholder="50"
                    data-testid="project-muros-planeados-input"
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Info si no hay cronograma */}
        <div className="mt-4 flex items-start gap-2 text-xs text-slate-600 bg-white/50 rounded-lg p-2">
          <Info className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <span>Si no cuentas con las cantidades exactas del cronograma, el sistema proyectará automáticamente las semanas restantes basándose en el ritmo de avance semanal.</span>
        </div>
      </div>

      {/* Avance calculado automáticamente - Por fase */}
      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h4 className="font-medium text-blue-900">📊 Avance del Proyecto</h4>
            <p className="text-xs text-blue-700">
              El porcentaje se calcula automáticamente basado en cada fase activa
            </p>
          </div>
          <div className="text-right">
            <span className="text-3xl font-bold text-blue-600">{formData.avance_actual || 0}%</span>
            <p className="text-xs text-blue-500">Total</p>
          </div>
        </div>
        
        {/* Barras de progreso por fase */}
        <div className="space-y-2">
          {formData.fases?.excavacion && formData.volumen_total_planeado > 0 && (
            <div className="flex items-center gap-3">
              <Shovel className="h-4 w-4 text-amber-600" />
              <span className="text-xs text-gray-600 w-20">Excavación</span>
              <div className="flex-1 bg-amber-200 rounded-full h-2">
                <div className="bg-amber-600 h-2 rounded-full transition-all" style={{ width: '0%' }} />
              </div>
              <span className="text-xs text-amber-700 font-medium w-10">0%</span>
            </div>
          )}
          {formData.fases?.cimentacion && formData.pilas_planeadas > 0 && (
            <div className="flex items-center gap-3">
              <Columns3 className="h-4 w-4 text-blue-600" />
              <span className="text-xs text-gray-600 w-20">Cimentación</span>
              <div className="flex-1 bg-blue-200 rounded-full h-2">
                <div className="bg-blue-600 h-2 rounded-full transition-all" style={{ width: '0%' }} />
              </div>
              <span className="text-xs text-blue-700 font-medium w-10">0%</span>
            </div>
          )}
          {formData.fases?.edificacion && formData.muros_planeados > 0 && (
            <div className="flex items-center gap-3">
              <Building2 className="h-4 w-4 text-purple-600" />
              <span className="text-xs text-gray-600 w-20">Edificación</span>
              <div className="flex-1 bg-purple-200 rounded-full h-2">
                <div className="bg-purple-600 h-2 rounded-full transition-all" style={{ width: '0%' }} />
              </div>
              <span className="text-xs text-purple-700 font-medium w-10">0%</span>
            </div>
          )}
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

      {/* Catálogo de Maquinaria con IA */}
      <CatalogoMaquinariaSection 
        formData={formData} 
        setFormData={setFormData}
        onShowSuccess={onShowSuccess}
      />

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
