import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Grid, Stats } from '@react-three/drei';
import * as THREE from 'three';
import axios from 'axios';
import { Box, Upload, AlertCircle, CheckCircle, Loader2, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Componente para renderizar la nube de puntos
function PointCloud({ points }) {
  const pointsRef = useRef();
  
  const { positions, colors } = useMemo(() => {
    const positions = new Float32Array(points.length * 3);
    const colors = new Float32Array(points.length * 3);
    
    points.forEach((point, i) => {
      positions[i * 3] = point.x;
      positions[i * 3 + 1] = point.z; // Z hacia arriba (Three.js usa Y como arriba)
      positions[i * 3 + 2] = point.y;
      
      colors[i * 3] = point.color[0];
      colors[i * 3 + 1] = point.color[1];
      colors[i * 3 + 2] = point.color[2];
    });
    
    return { positions, colors };
  }, [points]);
  
  // Animación suave de rotación opcional
  useFrame((state) => {
    if (pointsRef.current) {
      // Rotación muy lenta para efecto visual
      pointsRef.current.rotation.y += 0.0005;
    }
  });
  
  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={positions.length / 3}
          array={positions}
          itemSize={3}
          needsUpdate={true}
        />
        <bufferAttribute
          attach="attributes-color"
          count={colors.length / 3}
          array={colors}
          itemSize={3}
          needsUpdate={true}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.1}
        vertexColors={true}
        sizeAttenuation={true}
        transparent={true}
        opacity={0.8}
      />
    </points>
  );
}

// Componente principal del visor 3D
const Visor3DReal = ({ vuelo, onUploadComplete }) => {
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [pointsData, setPointsData] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const controlsRef = useRef();
  
  // Cargar puntos si el vuelo ya tiene archivo
  useEffect(() => {
    if (vuelo?.archivo_nube_puntos) {
      loadPointCloud();
    }
  }, [vuelo]);
  
  const loadPointCloud = async () => {
    if (!vuelo) return;
    
    setLoading(true);
    setUploadStatus(null);
    
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/process/nube-puntos/${vuelo.id}?max_points=100000`
      );
      
      if (response.data.success) {
        setPointsData(response.data.points);
        setMetadata(response.data.metadata);
        setUploadStatus({
          type: 'success',
          message: `✓ ${response.data.metadata.total_points.toLocaleString()} puntos cargados (mostrando ${response.data.metadata.displayed_points.toLocaleString()})`
        });
      }
    } catch (error) {
      console.error('Error loading point cloud:', error);
      setUploadStatus({
        type: 'error',
        message: error.response?.data?.detail || 'Error cargando nube de puntos'
      });
    } finally {
      setLoading(false);
    }
  };
  
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
      
      const uploadResponse = await axios.post(
        `${BACKEND_URL}/api/upload/nube-puntos/${vuelo.id}`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );
      
      if (uploadResponse.data) {
        setUploadStatus({
          type: 'success',
          message: `✓ Archivo ${uploadResponse.data.filename} subido. Procesando...`
        });
        
        // Esperar un momento y cargar los puntos
        setTimeout(() => {
          loadPointCloud();
        }, 1000);
        
        if (onUploadComplete) {
          onUploadComplete(uploadResponse.data);
        }
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      setUploadStatus({
        type: 'error',
        message: error.response?.data?.detail || 'Error al subir el archivo'
      });
    } finally {
      setUploading(false);
    }
  };
  
  const resetCamera = () => {
    if (controlsRef.current) {
      controlsRef.current.reset();
    }
  };
  
  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Box className="h-5 w-5 text-blue-400" />
          <h2 className="text-xl font-semibold text-white">Visor 3D - Nube de Puntos</h2>
          {pointsData && (
            <span className="text-sm text-green-400 ml-4">
              ● {pointsData.length.toLocaleString()} puntos renderizados
            </span>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          {pointsData && (
            <button
              onClick={resetCamera}
              className="flex items-center space-x-2 px-3 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 transition-colors"
              title="Resetear cámara"
            >
              <RotateCcw className="h-4 w-4" />
            </button>
          )}
          
          {vuelo && (
            <label
              htmlFor="file-upload-real"
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg cursor-pointer transition-colors ${
                uploading || loading
                  ? 'bg-slate-600 cursor-not-allowed'
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
              }`}
            >
              {uploading || loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>{uploading ? 'Subiendo...' : 'Procesando...'}</span>
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  <span>Cargar Nube de Puntos</span>
                </>
              )}
            </label>
          )}
          <input
            id="file-upload-real"
            type="file"
            accept=".las,.laz,.ply,.xyz,.txt"
            onChange={handleFileUpload}
            disabled={uploading || loading}
            className="hidden"
            data-testid="upload-nube-puntos-real"
          />
        </div>
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
      
      <div
        className="relative bg-slate-900 rounded-lg overflow-hidden"
        style={{ height: '600px' }}
        data-testid="canvas-3d-viewer-real"
      >
        {pointsData ? (
          <Canvas>
            <PerspectiveCamera makeDefault position={[5, 5, 5]} fov={60} />
            
            {/* Iluminación */}
            <ambientLight intensity={0.5} />
            <directionalLight position={[10, 10, 5]} intensity={1} />
            <directionalLight position={[-10, -10, -5]} intensity={0.5} />
            
            {/* Nube de puntos */}
            <PointCloud points={pointsData} />
            
            {/* Grid de referencia */}
            <Grid
              args={[10, 10]}
              cellSize={1}
              cellThickness={0.5}
              cellColor="#444444"
              sectionSize={5}
              sectionThickness={1}
              sectionColor="#666666"
              fadeDistance={30}
              fadeStrength={1}
              followCamera={false}
              infiniteGrid
            />
            
            {/* Controles de cámara */}
            <OrbitControls
              ref={controlsRef}
              enableDamping
              dampingFactor={0.05}
              rotateSpeed={0.5}
              zoomSpeed={0.8}
              panSpeed={0.5}
              minDistance={2}
              maxDistance={50}
            />
            
            {/* Stats de rendimiento (FPS) */}
            <Stats />
          </Canvas>
        ) : loading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <Loader2 className="h-16 w-16 text-blue-500 animate-spin mx-auto mb-4" />
              <p className="text-white text-lg">Procesando nube de puntos...</p>
              <p className="text-slate-400 text-sm mt-2">
                Esto puede tomar unos segundos
              </p>
            </div>
          </div>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <Box className="h-16 w-16 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400 text-lg">
                {vuelo?.archivo_nube_puntos
                  ? 'Haz clic en "Cargar Nube de Puntos" para visualizar'
                  : 'Sube un archivo LAZ/LAS para visualizar'}
              </p>
              <p className="text-slate-500 text-sm mt-2">
                Formatos soportados: .las, .laz, .ply, .xyz
              </p>
            </div>
          </div>
        )}
      </div>
      
      {/* Información de la nube de puntos */}
      {metadata && (
        <div className="mt-4 grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-slate-400 text-xs mb-1">Total Puntos</div>
            <div className="text-white font-semibold text-lg">
              {metadata.total_points.toLocaleString()}
            </div>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-slate-400 text-xs mb-1">Mostrando</div>
            <div className="text-white font-semibold text-lg">
              {metadata.displayed_points.toLocaleString()}
            </div>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-slate-400 text-xs mb-1">Rango X</div>
            <div className="text-white font-semibold text-sm">
              {(metadata.bounds.x.max - metadata.bounds.x.min).toFixed(2)} m
            </div>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <div className="text-slate-400 text-xs mb-1">Rango Z (altura)</div>
            <div className="text-white font-semibold text-sm">
              {(metadata.bounds.z.max - metadata.bounds.z.min).toFixed(2)} m
            </div>
          </div>
        </div>
      )}
      
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
          <strong>✨ Visor 3D Real:</strong> Este visor usa Three.js para renderizar archivos LAZ/LAS reales. 
          Usa el mouse para rotar (clic izquierdo), hacer zoom (scroll) y pan (clic derecho).
          Los colores representan la altura: azul (bajo) → verde → amarillo → rojo (alto).
        </p>
      </div>
    </div>
  );
};

export default Visor3DReal;
