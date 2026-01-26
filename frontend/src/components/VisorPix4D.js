import React, { useState } from 'react';
import { Box, ExternalLink, Edit2, Save, X } from 'lucide-react';

const VisorPix4D = ({ vuelo, proyectoPix4dUrl, onUpdateUrl }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [tempUrl, setTempUrl] = useState('');
  
  // URL por defecto
  const defaultUrl = 'https://cloud.pix4d.com/embed/bim/mesh/2509725?shareToken=6c0b297df8a2429da6c43b31b28767a9';
  
  // Prioridad: URL del proyecto > URL del vuelo > URL por defecto
  const currentUrl = proyectoPix4dUrl || vuelo?.pix4d_url || defaultUrl;
  
  const handleEdit = () => {
    setTempUrl(currentUrl);
    setIsEditing(true);
  };
  
  const handleSave = () => {
    if (tempUrl.trim() && onUpdateUrl) {
      onUpdateUrl(tempUrl);
    }
    setIsEditing(false);
  };
  
  const handleCancel = () => {
    setTempUrl('');
    setIsEditing(false);
  };
  
  return (
    <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Box className="h-5 w-5 text-[#994B49]" />
          <h2 className="text-xl font-semibold text-gray-900">Visor 3D - Modelo Pix4D</h2>
        </div>
        
        <div className="flex items-center space-x-2">
          {!isEditing ? (
            <>
              <a
                href={currentUrl.replace('/embed/', '/')}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center space-x-2 px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                title="Abrir en Pix4D"
              >
                <ExternalLink className="h-4 w-4" />
              </a>
              <button
                onClick={handleEdit}
                className="flex items-center space-x-2 px-4 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors"
                data-testid="edit-pix4d-url"
              >
                <Edit2 className="h-4 w-4" />
                <span>Editar URL</span>
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleSave}
                className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                <Save className="h-4 w-4" />
                <span>Guardar</span>
              </button>
              <button
                onClick={handleCancel}
                className="flex items-center space-x-2 px-3 py-2 bg-gray-400 text-white rounded-lg hover:bg-gray-500 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </>
          )}
        </div>
      </div>
      
      {isEditing && (
        <div className="mb-4">
          <label className="block text-sm text-gray-600 mb-2">
            URL del iframe de Pix4D
          </label>
          <input
            type="text"
            value={tempUrl}
            onChange={(e) => setTempUrl(e.target.value)}
            placeholder="https://cloud.pix4d.com/embed/bim/mesh/..."
            className="w-full px-4 py-2 bg-gray-50 text-gray-900 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#994B49]"
          />
          <p className="text-xs text-gray-500 mt-1">
            Pega aquí el src del iframe que te proporciona Pix4D
          </p>
        </div>
      )}
      
      <div 
        className="relative bg-gray-50 rounded-lg overflow-hidden border border-gray-200"
        style={{ height: '600px' }}
        data-testid="pix4d-viewer-container"
      >
        <iframe
          src={currentUrl}
          width="100%"
          height="100%"
          frameBorder="0"
          allowFullScreen
          title="Visor 3D Pix4D"
          className="w-full h-full"
        />
      </div>
      
      {vuelo && vuelo.volumetria && (
        <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
          <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
            <div className="text-gray-600 mb-1">Excavación</div>
            <div className="text-gray-900 font-semibold text-lg">
              {vuelo.volumetria.excavacion.toLocaleString()} m³
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
            <div className="text-gray-600 mb-1">Relleno</div>
            <div className="text-gray-900 font-semibold text-lg">
              {vuelo.volumetria.relleno.toLocaleString()} m³
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
            <div className="text-gray-600 mb-1">Materiales</div>
            <div className="text-gray-900 font-semibold text-lg">
              {vuelo.volumetria.materiales.toLocaleString()} m³
            </div>
          </div>
        </div>
      )}
      
      <div className="mt-4 bg-[#994B49]/10 border border-[#994B49]/30 rounded-lg p-3">
        <p className="text-[#994B49] text-sm">
          <strong>✨ Visor Pix4D Integrado:</strong> Este modelo 3D es procesado por Pix4D Cloud. 
          Usa los controles del visor para rotar, hacer zoom y explorar el modelo. 
          Haz clic en el botón de abrir para ver en pantalla completa.
        </p>
      </div>
      
      {vuelo && (
        <div className="mt-3 bg-green-50 border border-green-200 rounded-lg p-3">
          <p className="text-green-700 text-sm">
            <strong>📊 Datos del Vuelo:</strong> Fecha: {vuelo.fecha_vuelo}, 
            Duración: {vuelo.duracion_minutos} min, 
            Área: {vuelo.area_cubierta?.toLocaleString()} m², 
            Imágenes: {vuelo.num_imagenes}
          </p>
        </div>
      )}
    </div>
  );
};

export default VisorPix4D;
