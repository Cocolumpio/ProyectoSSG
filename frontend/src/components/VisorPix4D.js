import React, { useState } from 'react';
import { Box, ExternalLink, Edit2, Save, X } from 'lucide-react';

const VisorPix4D = ({ vuelo, onUpdateUrl }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [tempUrl, setTempUrl] = useState('');
  
  // URL por defecto del proyecto Pix4D
  const defaultUrl = vuelo?.pix4d_url || 'https://cloud.pix4d.com/embed/bim/mesh/2509725?shareToken=6c0b297df8a2429da6c43b31b28767a9';
  const [currentUrl, setCurrentUrl] = useState(defaultUrl);
  
  const handleEdit = () => {
    setTempUrl(currentUrl);
    setIsEditing(true);
  };
  
  const handleSave = () => {
    if (tempUrl.trim()) {
      setCurrentUrl(tempUrl);
      if (onUpdateUrl) {
        onUpdateUrl(tempUrl);
      }
    }
    setIsEditing(false);
  };
  
  const handleCancel = () => {
    setTempUrl('');
    setIsEditing(false);
  };
  
  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Box className="h-5 w-5 text-blue-400" />
          <h2 className="text-xl font-semibold text-white">Visor 3D - Modelo Pix4D</h2>
        </div>
        
        <div className="flex items-center space-x-2">
          {!isEditing ? (
            <>
              <a
                href={currentUrl.replace('/embed/', '/')}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center space-x-2 px-3 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 transition-colors"
                title="Abrir en Pix4D"
              >
                <ExternalLink className="h-4 w-4" />
              </a>
              <button
                onClick={handleEdit}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
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
                className="flex items-center space-x-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
              >
                <Save className="h-4 w-4" />
                <span>Guardar</span>
              </button>
              <button
                onClick={handleCancel}
                className="flex items-center space-x-2 px-3 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-500 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </>
          )}
        </div>
      </div>
      
      {isEditing && (
        <div className="mb-4">
          <label className="block text-sm text-slate-400 mb-2">
            URL del iframe de Pix4D
          </label>
          <input
            type="text"
            value={tempUrl}
            onChange={(e) => setTempUrl(e.target.value)}
            placeholder="https://cloud.pix4d.com/embed/bim/mesh/..."
            className="w-full px-4 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-slate-500 mt-1">
            Pega aquí el src del iframe que te proporciona Pix4D
          </p>
        </div>
      )}
      
      <div 
        className="relative bg-slate-900 rounded-lg overflow-hidden"
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
      
      {vuelo && (
        <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-slate-400 mb-1">Excavación</div>
            <div className="text-white font-semibold text-lg">
              {vuelo.volumetria.excavacion.toLocaleString()} m³
            </div>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-slate-400 mb-1">Relleno</div>
            <div className="text-white font-semibold text-lg">
              {vuelo.volumetria.relleno.toLocaleString()} m³
            </div>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-slate-400 mb-1">Materiales</div>
            <div className="text-white font-semibold text-lg">
              {vuelo.volumetria.materiales.toLocaleString()} m³
            </div>
          </div>
        </div>
      )}
      
      <div className="mt-4 bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
        <p className="text-blue-400 text-sm">
          <strong>✨ Visor Pix4D Integrado:</strong> Este modelo 3D es procesado por Pix4D Cloud. 
          Usa los controles del visor para rotar, hacer zoom y explorar el modelo. 
          Haz clic en el botón de abrir para ver en pantalla completa.
        </p>
      </div>
      
      <div className="mt-3 bg-green-500/10 border border-green-500/30 rounded-lg p-3">
        <p className="text-green-400 text-sm">
          <strong>📊 Datos del Vuelo:</strong> Fecha: {vuelo?.fecha_vuelo}, 
          Duración: {vuelo?.duracion_minutos} min, 
          Área: {vuelo?.area_cubierta?.toLocaleString()} m², 
          Imágenes: {vuelo?.num_imagenes}
        </p>
      </div>
    </div>
  );
};

export default VisorPix4D;
