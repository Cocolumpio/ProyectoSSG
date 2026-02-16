import { useState, useEffect } from 'react';
import axios from 'axios';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { Building2, Plane, TrendingUp, Database, Map as MapIcon, Box, Calendar, Truck, DollarSign, BarChart3, Layers, ExternalLink } from 'lucide-react';
import { KPICard } from '../common/KPICard';
import { MapRecenter } from '../common/MapRecenter';
import { PointCloudViewer } from '../Projects/PointCloudViewer';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function DashboardView({ estadisticas, proyectos, vuelos, selectedProyecto, onProyectoClick, mapCenter }) {
  const [avancesSemanales, setAvancesSemanales] = useState([]);
  const [loadingAvances, setLoadingAvances] = useState(false);
  const [model3dError, setModel3dError] = useState(false);
  
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
      if (!selectedProyecto) {
        setAvancesSemanales([]);
        return;
      }
      
      setLoadingAvances(true);
      setModel3dError(false); // Reset error when project changes
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
  }, [selectedProyecto]);

  // Calcular estadísticas del proyecto seleccionado
  const calcularEstadisticasProyecto = () => {
    if (!selectedProyecto || avancesSemanales.length === 0) return null;
    
    const volumenPlaneado = selectedProyecto.volumen_total_planeado || 0;
    const volumenExcavado = avancesSemanales.reduce((sum, a) => sum + (a.volumen_excavacion || 0), 0);
    const semanasTrabajas = avancesSemanales.filter(a => a.volumen_excavacion > 0).length;
    const costoM3 = selectedProyecto.costo_m3 || 150;
    const capacidadCamion = selectedProyecto.capacidad_camion || 25;
    const costoFlotilla = volumenExcavado * costoM3;
    const viajesCamion = Math.ceil(volumenExcavado / capacidadCamion);
    const porcentajeAvance = volumenPlaneado > 0 ? Math.min((volumenExcavado / volumenPlaneado) * 100, 100) : 0;
    const volumenRestante = Math.max(volumenPlaneado - volumenExcavado, 0);
    
    return {
      volumenPlaneado,
      volumenExcavado,
      volumenRestante,
      semanasTrabajas,
      totalSemanas: avancesSemanales.length,
      costoFlotilla,
      viajesCamion,
      porcentajeAvance,
      costoM3,
      capacidadCamion
    };
  };

  const stats = calcularEstadisticasProyecto();
  const ultimoAvance = avancesSemanales.length > 0 ? avancesSemanales[0] : null;

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
                <div className="text-3xl sm:text-4xl font-bold">{stats?.porcentajeAvance?.toFixed(1) || 0}%</div>
                <div className="text-white/80 text-sm">Avance Total</div>
              </div>
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
                    <div className="w-full h-full flex items-center justify-center">
                      <div className="w-8 h-8 border-4 border-[#994B49] border-t-transparent rounded-full animate-spin" />
                    </div>
                  ) : ultimoAvance?.modelo_3d_url ? (
                    <PointCloudViewer modelUrl={ultimoAvance.modelo_3d_url} />
                  ) : ultimoAvance?.pix4d_url ? (
                    <iframe
                      src={ultimoAvance.pix4d_url}
                      className="w-full h-full border-0"
                      title="Modelo 3D"
                      allowFullScreen
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-400">
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
                    Última actualización: {ultimoAvance.fecha} • Volumen: {(ultimoAvance.volumen_excavacion || 0).toLocaleString()} m³
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
                    {/* Volumen */}
                    <div className="bg-white rounded-lg p-4 border border-gray-200">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-gray-600">Volumen Excavado vs Planeado</span>
                        <span className="text-sm font-medium text-[#994B49]">{stats.porcentajeAvance.toFixed(1)}%</span>
                      </div>
                      <div className="flex items-end justify-between mb-2">
                        <div>
                          <span className="text-2xl font-bold text-gray-900">{stats.volumenExcavado.toLocaleString()}</span>
                          <span className="text-sm text-gray-500 ml-1">m³</span>
                        </div>
                        <div className="text-right">
                          <span className="text-sm text-gray-500">de </span>
                          <span className="text-lg font-semibold text-gray-700">{stats.volumenPlaneado.toLocaleString()}</span>
                          <span className="text-sm text-gray-500 ml-1">m³</span>
                        </div>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div
                          className="bg-gradient-to-r from-[#994B49] to-[#B85C5A] h-3 rounded-full transition-all"
                          style={{ width: `${stats.porcentajeAvance}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-500 mt-2">
                        Restante: <span className="font-medium">{stats.volumenRestante.toLocaleString()} m³</span>
                      </p>
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
                          <span className="text-sm font-normal text-blue-500"> / {stats.totalSemanas}</span>
                        </div>
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
    </div>
  );
}
