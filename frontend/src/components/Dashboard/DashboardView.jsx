import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { Building2, Plane, TrendingUp, Database, Map as MapIcon } from 'lucide-react';
import { KPICard } from '../common/KPICard';
import { MapRecenter } from '../common/MapRecenter';

export function DashboardView({ estadisticas, proyectos, vuelos, selectedProyecto, onProyectoClick, mapCenter }) {
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

      {/* Vuelos Recientes */}
      {selectedProyecto && vuelosDelProyecto.length > 0 && (
        <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Vuelos Recientes - {selectedProyecto.nombre}
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
