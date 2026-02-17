import { useState, useEffect } from 'react';
import axios from 'axios';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { Building2, Plane, TrendingUp, Database, Map as MapIcon, Box, Calendar, Truck, DollarSign, BarChart3, Layers, ExternalLink, Maximize2, Columns3, Anchor, Shovel, Mail, Loader2 } from 'lucide-react';
import { KPICard } from '../common/KPICard';
import { MapRecenter } from '../common/MapRecenter';
import { PointCloudViewer } from '../Projects/PointCloudViewer';
import { GanttChart } from './GanttChart';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function DashboardView({ estadisticas, proyectos, vuelos, selectedProyecto, onProyectoClick, mapCenter, onShowSuccess }) {
  const [avancesSemanales, setAvancesSemanales] = useState([]);
  const [loadingAvances, setLoadingAvances] = useState(false);
  const [showFullViewer, setShowFullViewer] = useState(false);
  const [sendingReport, setSendingReport] = useState(false);
  
  // Vuelos del proyecto seleccionado
  const vuelosDelProyecto = selectedProyecto
    ? vuelos.filter(v => v.proyecto_id === selectedProyecto.id)
    : [];

  // Calcular el volumen total excavado de todos los proyectos
  const volumenTotalExcavado = proyectos.reduce((total, p) => {
    const volPlaneado = p.volumen_total_planeado || 0;
    const avance = p.avance_actual || 0;
    return total + (volPlaneado * avance / 100);
  }, 0);

  // Cargar avances semanales del proyecto seleccionado
  useEffect(() => {
    const fetchAvances = async () => {
      if (!selectedProyecto?.id) {
        setAvancesSemanales([]);
        return;
      }
      
      setLoadingAvances(true);
      setShowFullViewer(false); // Cerrar visor al cambiar de proyecto
      try {
        const res = await axios.get(`${API}/proyectos/${selectedProyecto.id}/avances-semanales`);
        // Ordenar por semana descendente para obtener el último primero
        const sorted = res.data.sort((a, b) => b.semana - a.semana);
        setAvancesSemanales(sorted);
      } catch (err) {
        console.error('Error cargando avances:', err);
        setAvancesSemanales([]);
      } finally {
        setLoadingAvances(false);
      }
    };
    
    fetchAvances();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProyecto?.id]);

  // Calcular estadísticas del proyecto seleccionado
  const calcularEstadisticasProyecto = () => {
    if (!selectedProyecto || avancesSemanales.length === 0) return null;
    
    const volumenPlaneado = selectedProyecto.volumen_total_planeado || 0;
    const volumenExcavado = avancesSemanales.reduce((sum, a) => sum + (a.volumen_excavacion || 0), 0);
    // Semanas con avance registrado (avances semanales reales)
    const semanasTrabajas = avancesSemanales.filter(a => 
      (a.volumen_excavacion > 0) || (a.pilas_completadas > 0) || (a.muros_completados > 0) || (a.anclas_instaladas > 0)
    ).length;
    // Semanas planeadas del cronograma del proyecto
    const semanasPlaneadas = selectedProyecto.semanas_planeadas || 0;
    const costoM3 = selectedProyecto.costo_m3 || 150;
    const capacidadCamion = selectedProyecto.capacidad_camion || 25;
    const costoFlotilla = volumenExcavado * costoM3;
    const viajesCamion = Math.ceil(volumenExcavado / capacidadCamion);
    const porcentajeExcavacion = volumenPlaneado > 0 ? Math.min((volumenExcavado / volumenPlaneado) * 100, 100) : 0;
    const volumenRestante = Math.max(volumenPlaneado - volumenExcavado, 0);
    
    // Métricas de tipos de actividades
    const tiposActividades = selectedProyecto.actividades_tipo || [];
    const pilasPlaneadas = selectedProyecto.pilas_planeadas || 0;
    const murosPlaneados = selectedProyecto.muros_planeados || 0;
    const anclasPlaneadas = selectedProyecto.anclas_planeadas || 0;
    
    // Calcular ejecutados de los avances semanales
    const pilasEjecutadas = avancesSemanales.reduce((sum, a) => sum + (a.pilas_completadas || 0), 0);
    const murosEjecutados = avancesSemanales.reduce((sum, a) => sum + (a.muros_completados || 0), 0);
    const anclasEjecutadas = avancesSemanales.reduce((sum, a) => sum + (a.anclas_instaladas || 0), 0);
    
    // Calcular porcentajes por fase
    const porcentajePilas = pilasPlaneadas > 0 ? Math.min((pilasEjecutadas / pilasPlaneadas) * 100, 100) : 0;
    const porcentajeMuros = murosPlaneados > 0 ? Math.min((murosEjecutados / murosPlaneados) * 100, 100) : 0;
    const porcentajeAnclas = anclasPlaneadas > 0 ? Math.min((anclasEjecutadas / anclasPlaneadas) * 100, 100) : 0;
    
    // Calcular avance TOTAL como promedio de las fases activas
    const fasesActivas = [];
    const porcentajesFases = [];
    
    // Excavación
    if (tiposActividades.includes('excavacion') || volumenPlaneado > 0) {
      fasesActivas.push('excavacion');
      porcentajesFases.push(porcentajeExcavacion);
    }
    // Cimentación (pilas + anclas)
    if (tiposActividades.includes('pilas') || pilasPlaneadas > 0) {
      fasesActivas.push('cimentacion');
      // Promedio de pilas y anclas si ambas tienen metas
      if (pilasPlaneadas > 0 && anclasPlaneadas > 0) {
        porcentajesFases.push((porcentajePilas + porcentajeAnclas) / 2);
      } else if (pilasPlaneadas > 0) {
        porcentajesFases.push(porcentajePilas);
      } else if (anclasPlaneadas > 0) {
        porcentajesFases.push(porcentajeAnclas);
      }
    }
    // Edificación (muros)
    if (tiposActividades.includes('muros') || murosPlaneados > 0) {
      fasesActivas.push('edificacion');
      porcentajesFases.push(porcentajeMuros);
    }
    
    // Avance total: promedio de todas las fases activas
    const avanceTotal = porcentajesFases.length > 0 
      ? porcentajesFases.reduce((a, b) => a + b, 0) / porcentajesFases.length 
      : 0;
    
    // Proyección de semanas restantes (sin cronograma)
    let semanasProyectadas = null;
    if (semanasTrabajas > 0 && avanceTotal > 0 && avanceTotal < 100) {
      const ritmoSemanal = avanceTotal / semanasTrabajas; // % por semana
      const restante = 100 - avanceTotal;
      semanasProyectadas = Math.ceil(restante / ritmoSemanal);
    }
    
    return {
      volumenPlaneado,
      volumenExcavado,
      volumenRestante,
      semanasTrabajas,
      semanasPlaneadas,
      totalSemanas: avancesSemanales.length,
      costoFlotilla,
      viajesCamion,
      porcentajeAvance: porcentajeExcavacion, // Mantener para compatibilidad
      porcentajeExcavacion,
      costoM3,
      capacidadCamion,
      // Tipos de actividades
      tiposActividades,
      fasesActivas,
      pilasPlaneadas,
      murosPlaneados,
      anclasPlaneadas,
      pilasEjecutadas,
      murosEjecutados,
      anclasEjecutadas,
      porcentajePilas,
      porcentajeMuros,
      porcentajeAnclas,
      // Avance total del proyecto
      avanceTotal,
      semanasProyectadas,
    };
  };

  const stats = calcularEstadisticasProyecto();
  const ultimoAvance = avancesSemanales.length > 0 ? avancesSemanales[0] : null;

  // Función para enviar reporte semanal
  const handleEnviarReporte = async () => {
    setSendingReport(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/admin/enviar-reporte-semanal`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (onShowSuccess) {
        onShowSuccess('📊 Reporte semanal enviado exitosamente');
      }
    } catch (err) {
      console.error('Error enviando reporte:', err);
      alert('Error al enviar el reporte semanal');
    } finally {
      setSendingReport(false);
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6">
        <KPICard
          icon={Building2}
          label="Total Proyectos"
          value={estadisticas?.total_proyectos || 0}
          color="brick"
          testId="kpi-proyectos"
        />
        <KPICard
          icon={Plane}
          label="Vuelos Realizados"
          value={estadisticas?.total_vuelos || 0}
          color="brick"
          testId="kpi-vuelos"
        />
        <KPICard
          icon={TrendingUp}
          label="Avance Promedio"
          value={`${estadisticas?.avance_promedio || 0}%`}
          color="brick"
          testId="kpi-avance"
        />
        <KPICard
          icon={Database}
          label="Vol. Excavación Total"
          value={`${Math.round(volumenTotalExcavado).toLocaleString()} m³`}
          color="brick"
          testId="kpi-volumetria"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* Mapa */}
        <div className="bg-white rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
          <div className="flex items-center space-x-2 mb-3 sm:mb-4">
            <MapIcon className="h-4 sm:h-5 w-4 sm:w-5 text-[#994B49]" />
            <h2 className="text-base sm:text-xl font-semibold text-gray-900">Ubicación de Proyectos</h2>
          </div>
          <div className="h-[250px] sm:h-[400px] rounded-lg overflow-hidden border border-gray-200" data-testid="map-container">
            <MapContainer
              center={[mapCenter.lat, mapCenter.lng]}
              zoom={11}
              style={{ height: '100%', width: '100%' }}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              />
              <MapRecenter center={mapCenter} />
              {proyectos.map((proyecto) => (
                <Marker
                  key={proyecto.id}
                  position={[proyecto.coordenadas.lat, proyecto.coordenadas.lng]}
                  eventHandlers={{
                    click: () => onProyectoClick(proyecto)
                  }}
                >
                  <Popup>
                    <div className="text-sm">
                      <strong>{proyecto.nombre}</strong>
                      <br />
                      Avance: {proyecto.avance_actual}%
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          </div>
        </div>

        {/* Lista de Proyectos */}
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Proyectos Activos</h2>
          <div className="space-y-3 max-h-[400px] overflow-y-auto" data-testid="proyectos-list">
            {proyectos.map((proyecto) => (
              <div
                key={proyecto.id}
                onClick={() => onProyectoClick(proyecto)}
                className={`p-3 sm:p-4 rounded-lg cursor-pointer transition-all ${
                  selectedProyecto?.id === proyecto.id
                    ? 'bg-[#994B49]/10 border-2 border-[#994B49]'
                    : 'bg-gray-50 border border-gray-200 hover:bg-gray-100'
                }`}
                data-testid={`proyecto-item-${proyecto.id}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 text-sm sm:text-base truncate">{proyecto.nombre}</h3>
                    <p className="text-xs sm:text-sm text-gray-600 truncate">{proyecto.ubicacion}</p>
                  </div>
                  <div className="text-right ml-2">
                    <div className="text-lg sm:text-2xl font-bold text-[#994B49]">
                      {proyecto.avance_actual}%
                    </div>
                    <div className="text-xs text-gray-600">Avance</div>
                  </div>
                </div>
                <div className="mt-2">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-[#994B49] h-2 rounded-full transition-all"
                      style={{ width: `${proyecto.avance_actual}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Detalles del Proyecto Seleccionado */}
      {selectedProyecto && (
        <div className="bg-gradient-to-r from-[#994B49]/5 to-white rounded-xl border-2 border-[#994B49]/20 overflow-hidden">
          {/* Header del proyecto */}
          <div className="bg-[#994B49] text-white px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl sm:text-2xl font-bold">{selectedProyecto.nombre}</h2>
                <p className="text-white/80 text-sm">{selectedProyecto.direccion || selectedProyecto.ubicacion}</p>
              </div>
              <div className="text-right">
                <div className="text-3xl sm:text-4xl font-bold">{stats?.avanceTotal?.toFixed(1) || 0}%</div>
                <div className="text-white/80 text-sm">Avance Total</div>
                {stats?.semanasProyectadas && stats.semanasPlaneadas === 0 && (
                  <div className="text-white/60 text-xs mt-1">
                    📈 Proyección: ~{stats.semanasProyectadas} sem restantes
                  </div>
                )}
              </div>
            </div>
            {/* Barra de progreso total */}
            <div className="mt-3 w-full bg-white/20 rounded-full h-2">
              <div 
                className="bg-white h-2 rounded-full transition-all duration-500" 
                style={{ width: `${stats?.avanceTotal || 0}%` }}
              />
            </div>
          </div>

          <div className="p-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Modelo 3D - Último Avance */}
              <div>
                <div className="flex items-center space-x-2 mb-3">
                  <Box className="h-5 w-5 text-[#994B49]" />
                  <h3 className="font-semibold text-gray-900">
                    Modelo 3D - {ultimoAvance ? `Semana ${ultimoAvance.semana}` : 'Sin datos'}
                  </h3>
                </div>
                <div className="h-[300px] rounded-lg overflow-hidden border border-gray-200 bg-gray-100">
                  {loadingAvances ? (
                    <div className="w-full h-full flex items-center justify-center bg-[#1a1a2e]">
                      <div className="w-8 h-8 border-4 border-[#994B49] border-t-transparent rounded-full animate-spin" />
                    </div>
                  ) : ultimoAvance?.modelo_3d_url ? (
                    // Prioridad al modelo PLY local
                    <div className="w-full h-full relative group">
                      {ultimoAvance.thumbnail_url ? (
                        // Si hay thumbnail, mostrarlo con opción de ver el visor completo
                        <>
                          <img
                            src={`${process.env.REACT_APP_BACKEND_URL}${ultimoAvance.thumbnail_url}`}
                            alt={`Modelo 3D Semana ${ultimoAvance.semana}`}
                            className="w-full h-full object-cover"
                          />
                          <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                            <button
                              onClick={() => setShowFullViewer(true)}
                              className="flex items-center gap-2 bg-[#994B49] hover:bg-[#B85C5A] text-white px-4 py-2 rounded-lg transition-colors"
                            >
                              <Maximize2 className="h-4 w-4" />
                              Ver Modelo 3D
                            </button>
                          </div>
                          <div className="absolute bottom-2 left-2 bg-black/60 text-white text-xs px-2 py-1 rounded">
                            Semana {ultimoAvance.semana}
                          </div>
                        </>
                      ) : (
                        // Si no hay thumbnail, mostrar placeholder con botón
                        <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-[#1a1a2e] to-[#2d2d44]">
                          <div className="text-center p-6">
                            <Box className="h-16 w-16 mx-auto mb-4 text-[#994B49]" />
                            <h4 className="text-white font-semibold mb-2">Modelo 3D Local</h4>
                            <p className="text-gray-400 text-sm mb-4">
                              Semana {ultimoAvance.semana} - {ultimoAvance.fecha}
                            </p>
                            <button
                              onClick={() => setShowFullViewer(true)}
                              className="inline-flex items-center gap-2 bg-[#994B49] hover:bg-[#B85C5A] text-white px-4 py-2 rounded-lg transition-colors"
                            >
                              <Maximize2 className="h-4 w-4" />
                              Ver Modelo 3D
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : ultimoAvance?.pix4d_url ? (
                    // Fallback a Pix4D si no hay modelo local
                    <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-[#1a1a2e] to-[#2d2d44]">
                      <div className="text-center p-6">
                        <Box className="h-16 w-16 mx-auto mb-4 text-[#994B49]" />
                        <h4 className="text-white font-semibold mb-2">Modelo 3D en Pix4D</h4>
                        <p className="text-gray-400 text-sm mb-4">
                          Semana {ultimoAvance.semana} - {ultimoAvance.fecha}
                        </p>
                        <a
                          href={ultimoAvance.pix4d_url.replace('/embed/', '/dataset/')}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 bg-[#994B49] hover:bg-[#B85C5A] text-white px-4 py-2 rounded-lg transition-colors"
                        >
                          <ExternalLink className="h-4 w-4" />
                          Ver en Pix4D
                        </a>
                      </div>
                    </div>
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-400 bg-gray-100">
                      <div className="text-center">
                        <Layers className="h-12 w-12 mx-auto mb-2 text-gray-300" />
                        <p className="text-sm">Sin modelo 3D disponible</p>
                        <p className="text-xs text-gray-400">Sube un modelo en Avances Semanales</p>
                      </div>
                    </div>
                  )}
                </div>
                {ultimoAvance && (
                  <p className="text-xs text-gray-500 mt-2">
                    Última actualización: {ultimoAvance.fecha}
                    {selectedProyecto?.actividades_tipo?.includes('pilas') || selectedProyecto?.pilas_planeadas > 0 
                      ? ` • Pilas: ${(ultimoAvance.pilas_completadas || 0).toLocaleString()}`
                      : selectedProyecto?.volumen_total_planeado > 0 
                        ? ` • Volumen: ${(ultimoAvance.volumen_excavacion || 0).toLocaleString()} m³`
                        : ''}
                  </p>
                )}
              </div>

              {/* Estadísticas del Proyecto */}
              <div>
                <div className="flex items-center space-x-2 mb-3">
                  <BarChart3 className="h-5 w-5 text-[#994B49]" />
                  <h3 className="font-semibold text-gray-900">Resumen del Proyecto</h3>
                </div>
                
                {stats ? (
                  <div className="space-y-4">
                    {/* Avance Total del Proyecto - Siempre visible */}
                    <div className="bg-gradient-to-r from-[#994B49]/10 to-[#994B49]/5 rounded-xl p-4 border border-[#994B49]/30">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-sm font-semibold text-gray-800">Avance Total del Proyecto</span>
                        <span className="text-2xl font-bold text-[#994B49]">{stats.avanceTotal.toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-4 mb-3">
                        <div
                          className="bg-gradient-to-r from-[#994B49] to-[#B85C5A] h-4 rounded-full transition-all duration-500"
                          style={{ width: `${stats.avanceTotal}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-xs text-gray-600">
                        <span>Semanas trabajadas: <span className="font-medium text-gray-800">{stats.semanasTrabajas}</span></span>
                        {stats.semanasPlaneadas > 0 ? (
                          <span>Planeadas: <span className="font-medium text-gray-800">{stats.semanasPlaneadas}</span></span>
                        ) : stats.semanasProyectadas ? (
                          <span className="bg-orange-100 text-orange-700 px-2 py-0.5 rounded">
                            📈 ~{stats.semanasProyectadas} sem restantes
                          </span>
                        ) : null}
                      </div>
                    </div>

                    {/* Avance por Fase */}
                    {(stats.fasesActivas.length > 0 || stats.volumenPlaneado > 0 || stats.pilasPlaneadas > 0 || stats.murosPlaneados > 0) && (
                      <div className="bg-white rounded-lg p-4 border border-gray-200">
                        <h4 className="text-sm font-semibold text-gray-700 mb-3">Avance por Fase</h4>
                        <div className="space-y-3">
                          {/* Excavación */}
                          {stats.volumenPlaneado > 0 && (
                            <div className="flex items-center gap-3">
                              <div className="flex items-center gap-2 w-24">
                                <Shovel className="h-4 w-4 text-amber-600" />
                                <span className="text-xs font-medium text-amber-800">Excavación</span>
                              </div>
                              <div className="flex-1 bg-amber-100 rounded-full h-3">
                                <div
                                  className="bg-amber-500 h-3 rounded-full transition-all"
                                  style={{ width: `${stats.porcentajeExcavacion}%` }}
                                />
                              </div>
                              <span className="text-xs font-bold text-amber-700 w-12 text-right">{stats.porcentajeExcavacion.toFixed(0)}%</span>
                            </div>
                          )}
                          
                          {/* Cimentación (Pilas) */}
                          {stats.pilasPlaneadas > 0 && (
                            <div className="flex items-center gap-3">
                              <div className="flex items-center gap-2 w-24">
                                <Columns3 className="h-4 w-4 text-blue-600" />
                                <span className="text-xs font-medium text-blue-800">Cimentación</span>
                              </div>
                              <div className="flex-1 bg-blue-100 rounded-full h-3">
                                <div
                                  className="bg-blue-500 h-3 rounded-full transition-all"
                                  style={{ width: `${stats.porcentajePilas}%` }}
                                />
                              </div>
                              <span className="text-xs font-bold text-blue-700 w-12 text-right">{stats.porcentajePilas.toFixed(0)}%</span>
                            </div>
                          )}
                          
                          {/* Edificación (Muros) */}
                          {stats.murosPlaneados > 0 && (
                            <div className="flex items-center gap-3">
                              <div className="flex items-center gap-2 w-24">
                                <Building2 className="h-4 w-4 text-purple-600" />
                                <span className="text-xs font-medium text-purple-800">Edificación</span>
                              </div>
                              <div className="flex-1 bg-purple-100 rounded-full h-3">
                                <div
                                  className="bg-purple-500 h-3 rounded-full transition-all"
                                  style={{ width: `${stats.porcentajeMuros}%` }}
                                />
                              </div>
                              <span className="text-xs font-bold text-purple-700 w-12 text-right">{stats.porcentajeMuros.toFixed(0)}%</span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Detalles numéricos por fase */}
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      {/* Excavación */}
                      {stats.volumenPlaneado > 0 && (
                        <div className="bg-amber-50 rounded-lg p-3 border border-amber-200">
                          <div className="flex items-center gap-2 mb-1">
                            <Shovel className="h-4 w-4 text-amber-600" />
                            <span className="text-xs font-medium text-amber-800">Excavación</span>
                          </div>
                          <div className="text-lg font-bold text-amber-700">{stats.volumenExcavado.toLocaleString()}</div>
                          <div className="text-xs text-amber-600">/ {stats.volumenPlaneado.toLocaleString()} m³</div>
                        </div>
                      )}
                      
                      {/* Pilas */}
                      {stats.pilasPlaneadas > 0 && (
                        <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
                          <div className="flex items-center gap-2 mb-1">
                            <Columns3 className="h-4 w-4 text-blue-600" />
                            <span className="text-xs font-medium text-blue-800">Pilas</span>
                          </div>
                          <div className="text-lg font-bold text-blue-700">{stats.pilasEjecutadas.toLocaleString()}</div>
                          <div className="text-xs text-blue-600">/ {stats.pilasPlaneadas.toLocaleString()}</div>
                        </div>
                      )}
                      
                      {/* Anclas */}
                      {stats.anclasPlaneadas > 0 && (
                        <div className="bg-teal-50 rounded-lg p-3 border border-teal-200">
                          <div className="flex items-center gap-2 mb-1">
                            <Anchor className="h-4 w-4 text-teal-600" />
                            <span className="text-xs font-medium text-teal-800">Anclas</span>
                          </div>
                          <div className="text-lg font-bold text-teal-700">{stats.anclasEjecutadas.toLocaleString()}</div>
                          <div className="text-xs text-teal-600">/ {stats.anclasPlaneadas.toLocaleString()}</div>
                        </div>
                      )}
                      
                      {/* Muros */}
                      {stats.murosPlaneados > 0 && (
                        <div className="bg-purple-50 rounded-lg p-3 border border-purple-200">
                          <div className="flex items-center gap-2 mb-1">
                            <Building2 className="h-4 w-4 text-purple-600" />
                            <span className="text-xs font-medium text-purple-800">Muros</span>
                          </div>
                          <div className="text-lg font-bold text-purple-700">{stats.murosEjecutados.toLocaleString()}</div>
                          <div className="text-xs text-purple-600">/ {stats.murosPlaneados.toLocaleString()}</div>
                        </div>
                      )}
                    </div>

                    {/* Semanas y Viajes */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                        <div className="flex items-center space-x-2 mb-2">
                          <Calendar className="h-4 w-4 text-blue-600" />
                          <span className="text-xs font-medium text-blue-800">Semanas Trabajadas</span>
                        </div>
                        <div className="text-2xl font-bold text-blue-700">
                          {stats.semanasTrabajas}
                          <span className="text-sm font-normal text-blue-500"> / {stats.semanasPlaneadas}</span>
                        </div>
                        <p className="text-xs text-blue-600 mt-1">
                          {stats.totalSemanas} avances registrados
                        </p>
                      </div>
                      <div className="bg-amber-50 rounded-lg p-4 border border-amber-200">
                        <div className="flex items-center space-x-2 mb-2">
                          <Truck className="h-4 w-4 text-amber-600" />
                          <span className="text-xs font-medium text-amber-800">Viajes de Camión</span>
                        </div>
                        <div className="text-2xl font-bold text-amber-700">
                          {stats.viajesCamion.toLocaleString()}
                          <span className="text-xs font-normal text-amber-500 block">({stats.capacidadCamion} m³/viaje)</span>
                        </div>
                      </div>
                    </div>

                    {/* Costo de Flotilla */}
                    <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          <DollarSign className="h-4 w-4 text-green-600" />
                          <span className="text-sm font-medium text-green-800">Costo Total de Flotilla</span>
                        </div>
                        <span className="text-xs text-green-600">${stats.costoM3}/m³</span>
                      </div>
                      <div className="text-3xl font-bold text-green-700">
                        ${stats.costoFlotilla.toLocaleString()}
                        <span className="text-sm font-normal text-green-500 ml-1">MXN</span>
                      </div>
                      <p className="text-xs text-green-600 mt-1">
                        Basado en {stats.volumenExcavado.toLocaleString()} m³ excavados
                      </p>
                    </div>

                    {/* Fechas */}
                    <div className="flex items-center justify-between text-sm text-gray-600 px-1">
                      <div>
                        <span className="text-gray-400">Inicio:</span> {selectedProyecto.fecha_inicio}
                      </div>
                      <div>
                        <span className="text-gray-400">Fin planeado:</span> {selectedProyecto.fecha_fin_planeada}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="bg-gray-50 rounded-lg p-8 text-center text-gray-400">
                    <BarChart3 className="h-12 w-12 mx-auto mb-2 text-gray-300" />
                    <p>Sin datos de avance registrados</p>
                  </div>
                )}
              </div>
            </div>

            {/* Gráfico Gantt / Timeline del Proyecto */}
            {avancesSemanales.length > 0 && (
              <div className="mt-6">
                <GanttChart 
                  proyecto={selectedProyecto} 
                  avances={avancesSemanales} 
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Vuelos Recientes */}
      {selectedProyecto && vuelosDelProyecto.length > 0 && (
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Bitácora de Vuelos - {selectedProyecto.nombre}
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left" data-testid="vuelos-table">
              <thead className="border-b border-gray-200">
                <tr className="text-gray-600">
                  <th className="pb-3 pr-4">Fecha</th>
                  <th className="pb-3 pr-4">Duración</th>
                  <th className="pb-3 pr-4">Área</th>
                  <th className="pb-3 pr-4">Fotos</th>
                  <th className="pb-3">Estado</th>
                </tr>
              </thead>
              <tbody className="text-gray-900">
                {vuelosDelProyecto.map((vuelo) => (
                  <tr key={vuelo.id} className="border-b border-gray-100">
                    <td className="py-3 pr-4">{vuelo.fecha_vuelo}</td>
                    <td className="py-3 pr-4">{vuelo.duracion_minutos} min</td>
                    <td className="py-3 pr-4">{vuelo.area_cubierta?.toLocaleString() || 0} m²</td>
                    <td className="py-3 pr-4">{vuelo.num_imagenes || 0}</td>
                    <td className="py-3">
                      <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-sm">
                        {vuelo.estado}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal del Visor 3D Completo */}
      {showFullViewer && ultimoAvance?.modelo_3d_url && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80" onClick={() => setShowFullViewer(false)}>
          <div 
            className="relative w-[90vw] h-[80vh] bg-[#1a1a2e] rounded-xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="absolute top-4 left-4 z-10 bg-black/60 text-white px-3 py-2 rounded-lg">
              <h3 className="font-semibold">{selectedProyecto?.nombre}</h3>
              <p className="text-sm text-gray-300">Semana {ultimoAvance.semana} - {ultimoAvance.fecha}</p>
            </div>
            <button
              onClick={() => setShowFullViewer(false)}
              className="absolute top-4 right-4 z-10 bg-[#994B49] hover:bg-[#B85C5A] text-white p-2 rounded-lg transition-colors"
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <PointCloudViewer modelUrl={ultimoAvance.modelo_3d_url} />
          </div>
        </div>
      )}
    </div>
  );
}
