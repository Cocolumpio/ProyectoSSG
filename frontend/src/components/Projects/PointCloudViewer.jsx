import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader';

export function PointCloudViewer({ modelUrl, onError }) {
  const containerRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  const [pointCount, setPointCount] = useState(0);
  const [originalCount, setOriginalCount] = useState(0);
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
    scene.background = new THREE.Color(0x0B0B0F);
    sceneRef.current = scene;

    // Camera — far plane set generously; will be tuned after model loads
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100000);
    camera.position.set(50, 50, 50);

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
    controls.minDistance = 0.5;
    controls.maxDistance = 100000;

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
          // ============================================================
          // OUTLIER REJECTION: Pix4D/drone PLYs often contain stray points
          // (sky, reflections, isolated noise) that inflate the bounding box
          // and place the camera far from the real model.
          //
          // Strategy: compute robust bounding box from percentiles (1%-99%)
          // of point coordinates and center the geometry on the robust center.
          //
          // GEO-PROJECTION: Some PLYs (e.g., from Pix4D with WGS84 output)
          // store coordinates as decimal degrees (lon/lat) + meters (alt).
          // In that case X/Y are effectively flat (~0.01 deg) while Z spans
          // many meters → the model collapses to a vertical line. We detect
          // this and project lon/lat to local meters using equirectangular.
          // ============================================================
          const positions = geometry.getAttribute('position').array;
          const numPts = positions.length / 3;
          
          // Sample up to 50K points for percentile calculation (fast & accurate)
          const SAMPLE = Math.min(numPts, 50000);
          const step = Math.max(1, Math.floor(numPts / SAMPLE));
          const xs = new Float32Array(Math.ceil(numPts / step));
          const ys = new Float32Array(Math.ceil(numPts / step));
          const zs = new Float32Array(Math.ceil(numPts / step));
          let sIdx = 0;
          for (let i = 0; i < numPts; i += step) {
            xs[sIdx] = positions[i * 3];
            ys[sIdx] = positions[i * 3 + 1];
            zs[sIdx] = positions[i * 3 + 2];
            sIdx++;
          }
          // In-place sort and pick percentiles
          const sortFn = (a, b) => a - b;
          const sortedX = Array.from(xs.slice(0, sIdx)).sort(sortFn);
          const sortedY = Array.from(ys.slice(0, sIdx)).sort(sortFn);
          const sortedZ = Array.from(zs.slice(0, sIdx)).sort(sortFn);
          const pct = (arr, p) => arr[Math.floor(arr.length * p)];
          let minX = pct(sortedX, 0.01), maxX = pct(sortedX, 0.99);
          let minY = pct(sortedY, 0.01), maxY = pct(sortedY, 0.99);
          let minZ = pct(sortedZ, 0.01), maxZ = pct(sortedZ, 0.99);
          
          // ---- Detect geographic coordinates (lon/lat in decimal degrees) ----
          // Heuristic: X in [-180,180], Y in [-90,90], and rangeXY << rangeZ
          const rangeX = maxX - minX;
          const rangeY = maxY - minY;
          const rangeZ = maxZ - minZ;
          const looksGeographic =
            Math.abs(maxX) <= 180 && Math.abs(minX) <= 180 &&
            Math.abs(maxY) <= 90  && Math.abs(minY) <= 90  &&
            rangeX < 1 && rangeY < 1 &&
            rangeZ > Math.max(rangeX, rangeY) * 50;
          
          let isGeo = false;
          if (looksGeographic) {
            isGeo = true;
            console.warn('Detected GEOGRAPHIC coordinates (lon/lat degrees). Projecting to local meters.');
            const lat0 = (minY + maxY) / 2;
            const cosLat = Math.cos((lat0 * Math.PI) / 180);
            const M_PER_DEG_LAT = 110540;       // meters per degree of latitude
            const M_PER_DEG_LON = 111320 * cosLat; // meters per degree of longitude at lat0
            // Project ALL points in-place: X = (lon - lon0) * M_per_deg_lon
            const lon0 = (minX + maxX) / 2;
            for (let i = 0; i < numPts; i++) {
              positions[i * 3]     = (positions[i * 3]     - lon0) * M_PER_DEG_LON;
              positions[i * 3 + 1] = (positions[i * 3 + 1] - lat0) * M_PER_DEG_LAT;
              // Z (altitude in meters) stays as-is, but we will re-center below
            }
            // Re-compute percentiles AFTER projection (X,Y are now in meters)
            sIdx = 0;
            for (let i = 0; i < numPts; i += step) {
              xs[sIdx] = positions[i * 3];
              ys[sIdx] = positions[i * 3 + 1];
              sIdx++;
            }
            const sX = Array.from(xs.slice(0, sIdx)).sort(sortFn);
            const sY = Array.from(ys.slice(0, sIdx)).sort(sortFn);
            minX = pct(sX, 0.01); maxX = pct(sX, 0.99);
            minY = pct(sY, 0.01); maxY = pct(sY, 0.99);
          }
          
          const robustCenter = new THREE.Vector3(
            (minX + maxX) / 2,
            (minY + maxY) / 2,
            (minZ + maxZ) / 2
          );
          const robustSize = new THREE.Vector3(
            maxX - minX,
            maxY - minY,
            maxZ - minZ
          );
          const maxDim = Math.max(robustSize.x, robustSize.y, robustSize.z) || 1;
          
          console.log('Robust bounding box (1-99 percentile):', {
            isGeographic: isGeo,
            min: { x: minX, y: minY, z: minZ },
            max: { x: maxX, y: maxY, z: maxZ },
            center: robustCenter,
            size: robustSize,
            maxDim,
            totalPoints: numPts
          });
          
          // Shift ALL points so robust center is at world origin
          for (let i = 0; i < numPts; i++) {
            positions[i * 3]     -= robustCenter.x;
            positions[i * 3 + 1] -= robustCenter.y;
            positions[i * 3 + 2] -= robustCenter.z;
          }
          geometry.attributes.position.needsUpdate = true;
          geometry.computeBoundingBox();
          geometry.computeBoundingSphere();

          // OPTIMIZACIÓN AGRESIVA: Reducir puntos para evitar crashes de memoria
          const MAX_POINTS = 500000;
          const origCount = numPts;
          setOriginalCount(origCount);
          console.log('Original point count:', origCount);
          let pointsGeometry = geometry;
          
          if (origCount > MAX_POINTS) {
            setLoadingMessage(`Optimizando ${(origCount/1000000).toFixed(1)}M puntos para visualización...`);
            
            const skipRate = Math.ceil(origCount / MAX_POINTS);
            const hasColors = geometry.hasAttribute('color');
            const colors = hasColors ? geometry.getAttribute('color').array : null;
            
            const finalCount = Math.ceil(origCount / skipRate);
            const newPositions = new Float32Array(finalCount * 3);
            const newColors = hasColors ? new Float32Array(finalCount * 3) : null;
            
            let idx = 0;
            for (let i = 0; i < origCount && idx < finalCount; i += skipRate) {
              newPositions[idx * 3] = positions[i * 3];
              newPositions[idx * 3 + 1] = positions[i * 3 + 1];
              newPositions[idx * 3 + 2] = positions[i * 3 + 2];
              if (hasColors) {
                newColors[idx * 3] = colors[i * 3];
                newColors[idx * 3 + 1] = colors[i * 3 + 1];
                newColors[idx * 3 + 2] = colors[i * 3 + 2];
              }
              idx++;
            }
            
            geometry.dispose();
            
            pointsGeometry = new THREE.BufferGeometry();
            pointsGeometry.setAttribute('position', new THREE.BufferAttribute(newPositions, 3));
            if (hasColors) {
              pointsGeometry.setAttribute('color', new THREE.BufferAttribute(newColors, 3));
            }
            pointsGeometry.computeBoundingBox();
            pointsGeometry.computeBoundingSphere();
            
            console.log(`Puntos optimizados: ${origCount.toLocaleString()} → ${idx.toLocaleString()} (reducción ${skipRate}x)`);
          }

          // Check if geometry has colors
          const hasColors = pointsGeometry.hasAttribute('color');
          console.log('Has colors:', hasColors);
          
          // Point material — adaptive size based on robust dimension
          // Drone point clouds typically range 20-500m. We size points so
          // they cover ~0.15-0.4% of the model's max dimension.
          const pointSize = Math.max(maxDim * 0.0025, 0.05);
          const materialOptions = {
            size: pointSize,
            vertexColors: hasColors,
            sizeAttenuation: true,
            transparent: false,
          };
          
          if (!hasColors) {
            materialOptions.color = new THREE.Color(0xCCCCCC);
          }
          
          const material = new THREE.PointsMaterial(materialOptions);

          const points = new THREE.Points(pointsGeometry, material);
          scene.add(points);

          scene.remove(gridHelper);

          // ============================================================
          // CAMERA POSITIONING: Frame the robust bounding box
          // Use 35° FOV math: distance = (maxDim/2) / tan(fov/2) * margin
          // ============================================================
          const fovRad = (camera.fov * Math.PI) / 180;
          const distance = (maxDim / 2) / Math.tan(fovRad / 2) * 1.4;
          // Place camera at isometric-ish angle for nice 3D view
          camera.position.set(distance * 0.6, distance * 0.6, distance * 0.7);
          camera.near = Math.max(0.1, maxDim * 0.001);
          camera.far = distance * 10;
          camera.updateProjectionMatrix();
          camera.lookAt(0, 0, 0);
          controls.target.set(0, 0, 0);
          controls.minDistance = maxDim * 0.05;
          controls.maxDistance = distance * 8;
          controls.update();
          
          console.log('Camera positioned at distance:', distance, 'maxDim:', maxDim, 'point size:', pointSize);

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
    <div className="relative w-full h-full bg-[#0B0B0F] rounded-lg overflow-hidden">
      <div ref={containerRef} className="w-full h-full" />
      
      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#0B0B0F]/95">
          <div className="w-64 h-3 bg-[#2A2A33] rounded-full overflow-hidden">
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
      
      {/* Info badge - muestra si está optimizado */}
      {!loading && pointCount > 0 && (
        <div className="absolute bottom-2 left-2 bg-black/70 text-white text-xs px-2 py-1 rounded flex items-center gap-2">
          <span>{pointCount.toLocaleString()} puntos</span>
          {originalCount > pointCount && (
            <span className="bg-amber-500/80 text-black px-1.5 py-0.5 rounded text-[10px] font-medium">
              Vista optimizada ({(originalCount/1000000).toFixed(1)}M original)
            </span>
          )}
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
