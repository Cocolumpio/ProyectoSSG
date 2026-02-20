import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader';

export function PointCloudViewer({ modelUrl, onError }) {
  const containerRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  const [pointCount, setPointCount] = useState(0);
  const [loadingMessage, setLoadingMessage] = useState('Iniciando carga...');
  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const animationRef = useRef(null);
  const progressRef = useRef(0);
  const timeoutRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !modelUrl) {
      console.log('PointCloudViewer: Missing container or modelUrl', { containerRef: !!containerRef.current, modelUrl });
      return;
    }

    console.log('PointCloudViewer: Initializing with modelUrl:', modelUrl);
    
    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    console.log('PointCloudViewer: Container dimensions:', { width, height });

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 10000);
    camera.position.set(0, 0, 100);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.screenSpacePanning = true;
    controls.minDistance = 1;
    controls.maxDistance = 5000;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 10, 10);
    scene.add(directionalLight);

    // Grid helper
    const gridHelper = new THREE.GridHelper(100, 20, 0x444466, 0x333355);
    gridHelper.rotation.x = Math.PI / 2;
    scene.add(gridHelper);

    // Load PLY with timeout detection
    const loader = new PLYLoader();
    const fullUrl = modelUrl.startsWith('http') ? modelUrl : `${process.env.REACT_APP_BACKEND_URL}${modelUrl}`;
    
    let lastProgress = 0;
    let stuckCounter = 0;
    const STUCK_THRESHOLD = 180; // 3 minutes for very large files
    
    setLoadingMessage('Conectando al servidor...');
    console.log('Starting PLY load from:', fullUrl);
    
    timeoutRef.current = setInterval(() => {
      if (progressRef.current === lastProgress && progressRef.current < 100) {
        stuckCounter++;
        // Show progress message every 30 seconds
        if (stuckCounter % 30 === 0 && stuckCounter < STUCK_THRESHOLD) {
          console.log(`Still loading... ${stuckCounter}s elapsed, progress: ${progressRef.current}%`);
        }
        if (stuckCounter >= STUCK_THRESHOLD) {
          if (timeoutRef.current) clearInterval(timeoutRef.current);
          console.warn('Model loading stalled after', stuckCounter, 'seconds');
          setLoading(false);
          if (onError) onError('Timeout: El modelo es demasiado grande o hay problemas de conexión. Intenta recargar la página.');
        }
      } else {
        stuckCounter = 0;
        lastProgress = progressRef.current;
      }
    }, 1000);
    
    loader.load(
      fullUrl,
      (geometry) => {
        if (timeoutRef.current) clearInterval(timeoutRef.current);
        console.log('PLY loaded successfully, processing geometry...');
        setLoadingMessage('Procesando geometría...');
        
        try {
          // Center the geometry
          geometry.computeBoundingBox();
          const center = new THREE.Vector3();
          geometry.boundingBox.getCenter(center);
          geometry.center();

          // Get bounding box for camera positioning
          const box = geometry.boundingBox;
          const size = new THREE.Vector3();
          box.getSize(size);
          const maxDim = Math.max(size.x, size.y, size.z);
          
          console.log('Geometry size:', size, 'Max dimension:', maxDim);

          // Reducir puntos si hay demasiados (más de 5 millones)
          const originalCount = geometry.getAttribute('position').count;
          console.log('Original point count:', originalCount);
          let pointsGeometry = geometry;
          
          if (originalCount > 5000000) {
            setLoadingMessage(`Optimizando ${(originalCount/1000000).toFixed(1)}M puntos...`);
            
            // Diezmar la geometría para mejor rendimiento
            const skipRate = Math.ceil(originalCount / 2000000); // Reducir a ~2M puntos
            const positions = geometry.getAttribute('position').array;
            const hasColors = geometry.hasAttribute('color');
            const colors = hasColors ? geometry.getAttribute('color').array : null;
            
            const newPositions = [];
            const newColors = [];
            
            for (let i = 0; i < originalCount; i += skipRate) {
              newPositions.push(positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2]);
              if (hasColors) {
                newColors.push(colors[i * 3], colors[i * 3 + 1], colors[i * 3 + 2]);
              }
            }
            
            pointsGeometry = new THREE.BufferGeometry();
            pointsGeometry.setAttribute('position', new THREE.Float32BufferAttribute(newPositions, 3));
            if (hasColors) {
              pointsGeometry.setAttribute('color', new THREE.Float32BufferAttribute(newColors, 3));
            }
            
            console.log(`Puntos reducidos de ${originalCount.toLocaleString()} a ${(newPositions.length/3).toLocaleString()}`);
          }

          // Check if geometry has colors
          const hasColors = pointsGeometry.hasAttribute('color');
          console.log('Has colors:', hasColors);
          
          // Point material - NO pasar 'color' cuando usamos vertexColors
          const materialOptions = {
            size: maxDim * 0.002,
            vertexColors: hasColors,
            sizeAttenuation: true,
            transparent: true,
            opacity: 0.9
          };
          
          // Solo agregar color si NO tiene vertex colors
          if (!hasColors) {
            materialOptions.color = new THREE.Color(0x994B49);
          }
          
          const material = new THREE.PointsMaterial(materialOptions);

          // Create points mesh
          const points = new THREE.Points(pointsGeometry, material);
          scene.add(points);

          // Remove grid helper once model is loaded
          scene.remove(gridHelper);

          // Position camera to see the whole model
          const distance = maxDim * 1.5;
          camera.position.set(distance * 0.5, distance * 0.5, distance);
          camera.lookAt(0, 0, 0);
          controls.target.set(0, 0, 0);
          controls.update();

          // Update state
          const count = pointsGeometry.getAttribute('position').count;
          console.log('Final point count:', count);
          setPointCount(count);
          setLoading(false);
        } catch (processingError) {
          console.error('Error processing geometry:', processingError);
          setLoading(false);
          if (onError) onError('Error procesando la geometría del modelo');
        }
      },
      (xhr) => {
        if (xhr.lengthComputable) {
          const percentComplete = (xhr.loaded / xhr.total) * 100;
          progressRef.current = Math.round(percentComplete);
          setProgress(Math.round(percentComplete));
          
          // Mensaje descriptivo según el progreso
          const loadedMB = (xhr.loaded / (1024 * 1024)).toFixed(1);
          const totalMB = (xhr.total / (1024 * 1024)).toFixed(1);
          if (percentComplete < 100) {
            setLoadingMessage(`Descargando: ${loadedMB}MB / ${totalMB}MB`);
          }
          
          // Log progress every 10%
          if (Math.round(percentComplete) % 10 === 0) {
            console.log(`PLY Download progress: ${Math.round(percentComplete)}% (${loadedMB}MB / ${totalMB}MB)`);
          }
        } else {
          console.log('PLY Download: length not computable, loaded:', xhr.loaded);
        }
      },
      (error) => {
        if (timeoutRef.current) clearInterval(timeoutRef.current);
        console.error('Error loading PLY:', error);
        console.error('Error details:', error.message, error.stack);
        setLoading(false);
        if (onError) onError(`Error cargando el modelo 3D: ${error.message || 'desconocido'}`);
      }
    );

    // Animation loop
    const animate = () => {
      animationRef.current = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Resize handler
    const handleResize = () => {
      const newWidth = container.clientWidth;
      const newHeight = container.clientHeight;
      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    };
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      if (timeoutRef.current) clearInterval(timeoutRef.current);
      window.removeEventListener('resize', handleResize);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      if (rendererRef.current) {
        container.removeChild(rendererRef.current.domElement);
        rendererRef.current.dispose();
      }
      if (sceneRef.current) {
        sceneRef.current.traverse((object) => {
          if (object.geometry) object.geometry.dispose();
          if (object.material) {
            if (Array.isArray(object.material)) {
              object.material.forEach(m => m.dispose());
            } else {
              object.material.dispose();
            }
          }
        });
      }
    };
  }, [modelUrl, onError]);

  return (
    <div className="relative w-full h-full bg-[#1a1a2e] rounded-lg overflow-hidden">
      <div ref={containerRef} className="w-full h-full" />
      
      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#1a1a2e]/90">
          <div className="w-64 h-3 bg-gray-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-[#994B49] to-[#B85C5A] transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-white/90 text-sm mt-3 font-medium">{loadingMessage}</p>
          <p className="text-white/60 text-xs mt-1">{progress}% completado</p>
          {progress > 0 && progress < 100 && (
            <p className="text-white/40 text-xs mt-2">
              Por favor espera, los archivos grandes pueden tardar varios minutos
            </p>
          )}
        </div>
      )}
      
      {/* Info badge */}
      {!loading && pointCount > 0 && (
        <div className="absolute bottom-2 left-2 bg-black/50 text-white text-xs px-2 py-1 rounded">
          {pointCount.toLocaleString()} puntos
        </div>
      )}
      
      {/* Controls hint */}
      {!loading && (
        <div className="absolute bottom-2 right-2 bg-black/50 text-white/70 text-xs px-2 py-1 rounded">
          🖱️ Rotar • Scroll: Zoom • Shift+Arrastrar: Pan
        </div>
      )}
    </div>
  );
}
