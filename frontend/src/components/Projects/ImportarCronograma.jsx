import { useState } from 'react';
import axios from 'axios';
import { Upload, FileSpreadsheet, Check, AlertCircle, Loader2, Building2, Calendar, Layers, Shovel, Anchor, Drill, Columns3, Download } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function ImportarCronograma({ onProyectoCreado, onClose }) {
  const [file, setFile] = useState(null);
  const [parsing, setParsing] = useState(false);
  const [parsedData, setParsedData] = useState(null);
  const [error, setError] = useState(null);
  const [creating, setCreating] = useState(false);
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);
  
  // Datos adicionales del proyecto
  const [nombreProyecto, setNombreProyecto] = useState('');
  const [ubicacion, setUbicacion] = useState('');
  const [direccion, setDireccion] = useState('');

  const handleDownloadTemplate = async () => {
    setDownloadingTemplate(true);
    try {
      const response = await axios.get(`${API}/plantilla-cronograma`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'plantilla_cronograma_dron.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error descargando plantilla:', err);
      setError('Error al descargar la plantilla');
    } finally {
      setDownloadingTemplate(false);
    }
  };

  const handleFileChange = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;
    
    setFile(selectedFile);
    setError(null);
    setParsing(true);
    
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      
      const response = await axios.post(`${API}/proyectos/importar-cronograma`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setParsedData(response.data);
      
      // Extraer nombre del archivo
      const fileName = selectedFile.name.replace(/\.(xlsx|xls)$/i, '');
      setNombreProyecto(fileName);
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al procesar el archivo');
      setParsedData(null);
    } finally {
      setParsing(false);
    }
  };

  const handleCrearProyecto = async () => {
    if (!parsedData || !nombreProyecto) return;
    
    setCreating(true);
    setError(null);
    
    try {
      // Crear descripción dinámica basada en los tipos detectados
      const tipos = parsedData.resumen.tipos_actividades || [];
      let descripcionParts = [`Proyecto con ${parsedData.resumen.total_frentes} frentes`];
      if (tipos.includes('pilas')) descripcionParts.push(`${parsedData.resumen.total_pilas} pilas`);
      if (tipos.includes('muros')) descripcionParts.push(`${parsedData.resumen.total_muros} muros`);
      if (tipos.includes('anclas')) descripcionParts.push(`${parsedData.resumen.total_anclas} anclas`);
      if (tipos.includes('excavacion')) descripcionParts.push(`${parsedData.resumen.total_excavacion}m³ excavación`);
      
      const response = await axios.post(`${API}/proyectos/crear-desde-cronograma`, {
        nombre: nombreProyecto,
        ubicacion: ubicacion,
        direccion: direccion,
        coordenadas: { lat: 20.6597, lng: -103.3496 }, // Guadalajara default
        frentes: parsedData.frentes,
        resumen: parsedData.resumen,
        descripcion: descripcionParts.join(', ')
      });
      
      if (response.data.success) {
        onProyectoCreado && onProyectoCreado(response.data);
        onClose && onClose();
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al crear el proyecto');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 bg-[#994B49]/10 rounded-lg">
          <FileSpreadsheet className="h-6 w-6 text-[#994B49]" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-gray-900">Importar Cronograma</h2>
          <p className="text-sm text-gray-500">Crea un proyecto completo desde un archivo Excel</p>
        </div>
      </div>

      {/* Upload Area */}
      {!parsedData && (
        <div className="mb-6">
          <label className="block">
            <div className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors
              ${file ? 'border-[#994B49] bg-[#994B49]/5' : 'border-gray-300 hover:border-[#994B49]'}`}>
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileChange}
                className="hidden"
                disabled={parsing}
              />
              {parsing ? (
                <div className="flex flex-col items-center">
                  <Loader2 className="h-12 w-12 text-[#994B49] animate-spin mb-3" />
                  <p className="text-gray-600">Analizando cronograma...</p>
                </div>
              ) : (
                <>
                  <Upload className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                  <p className="text-gray-600 mb-1">
                    {file ? file.name : 'Arrastra tu archivo Excel aquí'}
                  </p>
                  <p className="text-sm text-gray-400">o haz clic para seleccionar</p>
                  <p className="text-xs text-gray-400 mt-2">Formatos: .xlsx, .xls</p>
                </>
              )}
            </div>
          </label>
          
          {/* Link para descargar plantilla */}
          <div className="mt-4 text-center">
            <button 
              onClick={handleDownloadTemplate}
              disabled={downloadingTemplate}
              className="inline-flex items-center gap-2 text-sm text-purple-600 hover:text-purple-700 underline disabled:opacity-50"
              data-testid="download-plantilla-btn"
            >
              {downloadingTemplate ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              Descargar plantilla de ejemplo
            </button>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-red-700 font-medium">Error</p>
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Parsed Data Preview */}
      {parsedData && (
        <div className="space-y-6">
          {/* Resumen */}
          <div className="bg-gradient-to-r from-[#994B49]/10 to-[#994B49]/5 rounded-xl p-6">
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Check className="h-5 w-5 text-green-500" />
              Cronograma Analizado Correctamente
            </h3>
            
            {/* Tipos de Actividades Detectadas */}
            {parsedData.resumen.tipos_actividades && parsedData.resumen.tipos_actividades.length > 0 && (
              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-2">Tipos de actividades detectadas:</p>
                <div className="flex flex-wrap gap-2">
                  {parsedData.resumen.tipos_actividades.map((tipo, idx) => (
                    <span 
                      key={idx}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium ${
                        tipo === 'pilas' ? 'bg-blue-100 text-blue-700' :
                        tipo === 'excavacion' ? 'bg-amber-100 text-amber-700' :
                        tipo === 'muros' ? 'bg-purple-100 text-purple-700' :
                        tipo === 'anclas' ? 'bg-teal-100 text-teal-700' :
                        'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {tipo === 'pilas' && <Columns3 className="h-4 w-4" />}
                      {tipo === 'excavacion' && <Shovel className="h-4 w-4" />}
                      {tipo === 'muros' && <Building2 className="h-4 w-4" />}
                      {tipo === 'anclas' && <Anchor className="h-4 w-4" />}
                      {tipo === 'cimentacion' && <Drill className="h-4 w-4" />}
                      {tipo.charAt(0).toUpperCase() + tipo.slice(1)}
                    </span>
                  ))}
                </div>
              </div>
            )}
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg p-4 shadow-sm">
                <p className="text-2xl font-bold text-[#994B49]">{parsedData.resumen.total_frentes}</p>
                <p className="text-sm text-gray-500">Frentes</p>
              </div>
              {/* Métricas dinámicas según tipos detectados */}
              {parsedData.resumen.tipos_actividades?.includes('pilas') && (
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <p className="text-2xl font-bold text-blue-600">{parsedData.resumen.total_pilas}</p>
                  <p className="text-sm text-gray-500">Pilas Totales</p>
                </div>
              )}
              {parsedData.resumen.tipos_actividades?.includes('muros') && (
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <p className="text-2xl font-bold text-purple-600">{parsedData.resumen.total_muros}</p>
                  <p className="text-sm text-gray-500">Muros Totales</p>
                </div>
              )}
              {parsedData.resumen.tipos_actividades?.includes('anclas') && (
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <p className="text-2xl font-bold text-teal-600">{parsedData.resumen.total_anclas}</p>
                  <p className="text-sm text-gray-500">Anclas Totales</p>
                </div>
              )}
              {parsedData.resumen.tipos_actividades?.includes('excavacion') && (
                <div className="bg-white rounded-lg p-4 shadow-sm">
                  <p className="text-2xl font-bold text-amber-600">{parsedData.resumen.total_excavacion}</p>
                  <p className="text-sm text-gray-500">Excavación (m³)</p>
                </div>
              )}
              <div className="bg-white rounded-lg p-4 shadow-sm">
                <p className="text-2xl font-bold text-amber-600">{parsedData.resumen.total_dias}</p>
                <p className="text-sm text-gray-500">Días de Trabajo</p>
              </div>
              <div className="bg-white rounded-lg p-4 shadow-sm">
                <p className="text-2xl font-bold text-green-600">{parsedData.resumen.semanas_estimadas}</p>
                <p className="text-sm text-gray-500">Semanas Estimadas</p>
              </div>
            </div>
            <div className="mt-4 flex gap-4 text-sm text-gray-600">
              <span className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                Inicio: {parsedData.resumen.fecha_inicio}
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                Fin: {parsedData.resumen.fecha_fin}
              </span>
            </div>
          </div>

          {/* Frentes Preview */}
          <div>
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Layers className="h-5 w-5 text-[#994B49]" />
              Frentes Detectados
            </h3>
            <div className="space-y-3 max-h-60 overflow-y-auto">
              {parsedData.frentes.map((frente, idx) => (
                <div key={idx} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex justify-between items-start mb-2">
                    <h4 className="font-medium text-gray-900">{frente.nombre}</h4>
                    <span className="text-sm bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                      {frente.actividades.length} actividades
                    </span>
                  </div>
                  <div className="text-sm text-gray-500">
                    {frente.actividades.slice(0, 3).map((act, i) => (
                      <div key={i} className="flex justify-between py-1 border-b border-gray-100 last:border-0">
                        <span className="truncate flex-1">{act.descripcion}</span>
                        <div className="ml-4 flex items-center gap-2">
                          <span className={`text-xs px-1.5 py-0.5 rounded ${
                            act.tipo === 'pilas' ? 'bg-blue-100 text-blue-700' :
                            act.tipo === 'excavacion' ? 'bg-amber-100 text-amber-700' :
                            act.tipo === 'muros' ? 'bg-purple-100 text-purple-700' :
                            act.tipo === 'anclas' ? 'bg-teal-100 text-teal-700' :
                            'bg-gray-100 text-gray-600'
                          }`}>
                            {act.tipo || 'otro'}
                          </span>
                          <span className="text-[#994B49] font-medium">{act.cantidad}</span>
                        </div>
                      </div>
                    ))}
                    {frente.actividades.length > 3 && (
                      <p className="text-gray-400 text-xs mt-1">
                        +{frente.actividades.length - 3} actividades más...
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Datos del Proyecto */}
          <div className="border-t pt-6">
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Building2 className="h-5 w-5 text-[#994B49]" />
              Datos del Proyecto
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre del Proyecto *
                </label>
                <input
                  type="text"
                  value={nombreProyecto}
                  onChange={(e) => setNombreProyecto(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                  placeholder="Ej: Terminal 2 Aeropuerto GDL"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Ubicación
                </label>
                <input
                  type="text"
                  value={ubicacion}
                  onChange={(e) => setUbicacion(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                  placeholder="Ej: Guadalajara, Jalisco"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Dirección
                </label>
                <input
                  type="text"
                  value={direccion}
                  onChange={(e) => setDireccion(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                  placeholder="Ej: Carretera Guadalajara-Chapala Km 17.5"
                />
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              onClick={() => {
                setFile(null);
                setParsedData(null);
                setNombreProyecto('');
              }}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Cancelar
            </button>
            <button
              onClick={handleCrearProyecto}
              disabled={creating || !nombreProyecto}
              className="px-6 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#B85C5A] disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {creating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Creando...
                </>
              ) : (
                <>
                  <Check className="h-4 w-4" />
                  Crear Proyecto
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
