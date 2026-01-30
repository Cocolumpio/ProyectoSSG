import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Building2, Plane, TrendingUp, Database, Map as MapIcon } from 'lucide-react';
import { KPICard } from '../common/KPICard';
import { MapRecenter } from '../common/MapRecenter';
import VisorPix4D from '../VisorPix4D';

export function DashboardView({ estadisticas, proyectos, vuelos, selectedProyecto, onProyectoClick, mapCenter }) {
  const vuelosDelProyecto = selectedProyecto
    ? vuelos.filter(v => v.proyecto_id === selectedProyecto.id)
    : [];

  const volumetriaData = vuelosDelProyecto.map((v, idx) => ({
    nombre: `Vuelo ${idx + 1}`,
    excavacion: v.volumetria.excavacion,
    relleno: v.volumetria.relleno,
    materiales: v.volumetria.materiales
  }));

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
          value={`${Math.round(estadisticas?.volumetria_total?.excavacion || 0)} m³`}
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

      {/* Visor 3D - Pix4D */}
      {selectedProyecto && (selectedProyecto.pix4d_url || vuelosDelProyecto.length > 0) && (
        <VisorPix4D 
          vuelo={vuelosDelProyecto[0]} 
          proyectoPix4dUrl={selectedProyecto.pix4d_url}
          onUpdateUrl={(url) => console.log('Nueva URL:', url)}
        />
      )}

      {/* Volumetría del Proyecto Seleccionado */}
      {selectedProyecto && volumetriaData.length > 0 && (
        <div className="bg-white rounded-xl p-4 sm:p-6 border border-gray-200 shadow-sm">
          <h2 className="text-base sm:text-xl font-semibold text-gray-900 mb-3 sm:mb-4">
            Volumetrías - {selectedProyecto.nombre}
          </h2>
          <div className="h-[200px] sm:h-[300px]" data-testid="volumetria-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={volumetriaData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="nombre" stroke="#6B7280" fontSize={12} />
                <YAxis stroke="#6B7280" fontSize={12} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#FFFFFF', border: '1px solid #E5E7EB' }}
                  labelStyle={{ color: '#111827' }}
                />
                <Legend />
                <Bar dataKey="excavacion" fill="#994B49" name="Excavación (m³)" />
                <Bar dataKey="relleno" fill="#10b981" name="Relleno (m³)" />
                <Bar dataKey="materiales" fill="#6B7280" name="Materiales (m³)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

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
                  <th className="pb-3 pr-4">Imágenes</th>
                  <th className="pb-3">Estado</th>
                </tr>
              </thead>
              <tbody className="text-gray-900">
                {vuelosDelProyecto.map((vuelo) => (
                  <tr key={vuelo.id} className="border-b border-gray-100">
                    <td className="py-3 pr-4">{vuelo.fecha_vuelo}</td>
                    <td className="py-3 pr-4">{vuelo.duracion_minutos} min</td>
                    <td className="py-3 pr-4">{vuelo.area_cubierta.toLocaleString()} m²</td>
                    <td className="py-3 pr-4">{vuelo.num_imagenes}</td>
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
