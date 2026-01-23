import React, { useRef, useEffect, useState } from 'react';
import { Box, Upload, AlertCircle, CheckCircle } from 'lucide-react';

/**
 * Componente Visor3D - Visualización de nubes de puntos
 * 
 * En una implementación completa, este componente usaría Three.js
 * para renderizar nubes de puntos 3D reales (.las, .laz, .ply, .xyz)
 * 
 * Para el MVP, mostramos una representación visual simulada
 */
const Visor3D = ({ vuelo, onUploadComplete }) => {
  const canvasRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Limpiar canvas
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, width, height);

    // Simular nube de puntos 3D
    if (vuelo) {
      const numPuntos = 2000;
      const centerX = width / 2;
      const centerY = height / 2;

      // Crear degradado de fondo
      const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, width / 2);
      gradient.addColorStop(0, '#1e293b');
      gradient.addColorStop(1, '#0f172a');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, height);

      // Dibujar puntos simulados
      for (let i = 0; i < numPuntos; i++) {
        const angle = Math.random() * Math.PI * 2;
        const radius = Math.random() * Math.min(width, height) * 0.4;
        const z = Math.random();
        
        const x = centerX + Math.cos(angle) * radius * z;
        const y = centerY + Math.sin(angle) * radius * z * 0.6;
        
        // Color basado en altura (z)
        const hue = 200 + z * 60; // De azul a verde
        const size = 1 + z * 2;
        const alpha = 0.3 + z * 0.7;
        
        ctx.fillStyle = `hsla(${hue}, 70%, 60%, ${alpha})`;
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fill();
      }

      // Dibujar grid de referencia
      ctx.strokeStyle = 'rgba(100, 116, 139, 0.3)';
      ctx.lineWidth = 1;
      
      // Líneas horizontales
      for (let i = 0; i < 5; i++) {
        const y = (height / 5) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }
      
      // Líneas verticales
      for (let i = 0; i < 5; i++) {
        const x = (width / 5) * i;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }

      // Información del vuelo
      ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
      ctx.font = 'bold 14px system-ui';
      ctx.fillText(`Vuelo: ${vuelo.fecha_vuelo}`, 20, 30);
      ctx.fillText(`Área: ${vuelo.area_cubierta.toLocaleString()} m²`, 20, 50);
      ctx.fillText(`Imágenes: ${vuelo.num_imagenes}`, 20, 70);
    } else {
      // Estado sin datos
      ctx.fillStyle = 'rgba(148, 163, 184, 0.5)';
      ctx.font = '16px system-ui';
      ctx.textAlign = 'center';
      ctx.fillText('Seleccione un vuelo para visualizar', centerX, centerY - 20);
      ctx.fillText('la nube de puntos 3D', centerX, centerY + 10);
    }
  }, [vuelo]);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const allowedExtensions = ['.las', '.laz', '.ply', '.xyz', '.txt'];
    const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    
    if (!allowedExtensions.includes(fileExtension)) {
      setUploadStatus({
        type: 'error',
        message: `Formato no permitido. Use: ${allowedExtensions.join(', ')}`
      });
      return;
    }

    setUploading(true);
    setUploadStatus(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
      const response = await fetch(`${BACKEND_URL}/api/upload/nube-puntos/${vuelo.id}`, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const result = await response.json();
        setUploadStatus({
          type: 'success',
          message: `Archivo ${result.filename} subido exitosamente`
        });
        if (onUploadComplete) {
          onUploadComplete(result);
        }
      } else {
        throw new Error('Error al subir archivo');
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      setUploadStatus({
        type: 'error',
        message: 'Error al subir el archivo. Intente nuevamente.'
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Box className="h-5 w-5 text-blue-400" />
          <h2 className="text-xl font-semibold text-white">Visor 3D - Nube de Puntos</h2>
        </div>
        
        {vuelo && (
          <div className="flex items-center space-x-2">
            <label
              htmlFor="file-upload"
              className="flex items-center space-x-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 cursor-pointer transition-colors"
            >
              <Upload className="h-4 w-4" />
              <span>{uploading ? 'Subiendo...' : 'Cargar Nube de Puntos'}</span>
            </label>
            <input
              id="file-upload"
              type="file"
              accept=".las,.laz,.ply,.xyz,.txt"
              onChange={handleFileUpload}
              disabled={uploading}
              className="hidden"
              data-testid="upload-nube-puntos"
            />
          </div>
        )}
      </div>

      {uploadStatus && (
        <div className={`mb-4 p-3 rounded-lg flex items-center space-x-2 ${
          uploadStatus.type === 'success' 
            ? 'bg-green-500/20 text-green-400' 
            : 'bg-red-500/20 text-red-400'
        }`}>
          {uploadStatus.type === 'success' ? (
            <CheckCircle className="h-5 w-5" />
          ) : (
            <AlertCircle className="h-5 w-5" />
          )}
          <span>{uploadStatus.message}</span>
        </div>
      )}

      <div className="relative bg-slate-900 rounded-lg overflow-hidden" style={{ height: '500px' }}>
        <canvas
          ref={canvasRef}
          width={800}
          height={500}
          className="w-full h-full"
          data-testid="canvas-3d-viewer"
        />
        
        {!vuelo && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <Box className="h-16 w-16 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400 text-lg">Seleccione un vuelo para visualizar</p>
              <p className="text-slate-500 text-sm mt-2">
                La nube de puntos 3D se mostrará aquí
              </p>
            </div>
          </div>
        )}
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
          <strong>Nota:</strong> Este visor muestra una representación simulada. 
          En producción, se utilizaría Three.js con bibliotecas especializadas (Potree, LAS.js) 
          para renderizar nubes de puntos reales en formatos LAS, LAZ, PLY o XYZ.
        </p>
      </div>
    </div>
  );
};

export default Visor3D;
