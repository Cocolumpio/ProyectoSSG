import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader';

export function PointCloudViewer({ modelUrl, onError }) {
  const containerRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  const [pointCount, setPointCount] = useState(0);
  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const animationRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !modelUrl) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight;

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

    // Load PLY
    const loader = new PLYLoader();
    const fullUrl = modelUrl.startsWith('http') ? modelUrl : `${process.env.REACT_APP_BACKEND_URL}${modelUrl}`;
    
    loader.load(
      fullUrl,
      (geometry) => {
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

        // Check if geometry has colors
        const hasColors = geometry.hasAttribute('color');
        
        // Point material
        const material = new THREE.PointsMaterial({
          size: maxDim * 0.002,
          vertexColors: hasColors,
          color: hasColors ? undefined : new THREE.Color(0x994B49),
          sizeAttenuation: true,
          transparent: true,
          opacity: 0.9
        });

        // Create points mesh
        const points = new THREE.Points(geometry, material);
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
        const count = geometry.getAttribute('position').count;
        setPointCount(count);
        setLoading(false);
      },
      (xhr) => {
        if (xhr.lengthComputable) {
          const percentComplete = (xhr.loaded / xhr.total) * 100;
          setProgress(Math.round(percentComplete));
        }
      },
      (error) => {
        console.error('Error loading PLY:', error);
        setLoading(false);
        if (onError) onError('Error cargando el modelo 3D');
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
          <div className="w-48 h-2 bg-gray-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-[#994B49] transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-white/80 text-sm mt-3">Cargando modelo... {progress}%</p>
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
