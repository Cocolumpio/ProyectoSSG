import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell, LineChart, Line, Area, AreaChart } from 'recharts';
import { Calendar, Flag, Clock, Columns3, Shovel, Building2, Anchor } from 'lucide-react';

export function GanttChart({ proyecto, avances = [] }) {
  // Determinar qué tipo de métrica principal usar basado en actividades_tipo
  const tipoMetrica = useMemo(() => {
    const tipos = proyecto?.actividades_tipo || [];
    
    // Prioridad: pilas > muros > anclas > excavacion
    if (tipos.includes('pilas')) return 'pilas';
    if (tipos.includes('muros')) return 'muros';
    if (tipos.includes('anclas')) return 'anclas';
    if (tipos.includes('excavacion')) return 'excavacion';
    
    // Si no hay tipos definidos, verificar si hay datos de excavación o pilas
    const tieneExcavacion = proyecto?.volumen_total_planeado > 0;
    const tienePilas = proyecto?.pilas_planeadas > 0;
    
    if (tienePilas) return 'pilas';
    if (tieneExcavacion) return 'excavacion';
    
    return 'pilas'; // Default a pilas
  }, [proyecto]);

  const chartData = useMemo(() => {
    if (!proyecto || avances.length === 0) return [];

    const semanasPlaneadas = proyecto.semanas_planeadas || avances.length;
    const sortedAvances = [...avances].sort((a, b) => a.semana - b.semana);
    
    // Obtener totales planeados según el tipo de métrica
    let totalPlaneado = 0;
    let unidad = '';
    let campoReal = '';
    
    switch (tipoMetrica) {
      case 'pilas':
        totalPlaneado = proyecto.pilas_planeadas || 0;
        unidad = 'pilas';
        campoReal = 'pilas_completadas';
        break;
      case 'muros':
        totalPlaneado = proyecto.muros_planeados || 0;
        unidad = 'muros';
        campoReal = 'muros_completados';
        break;
      case 'anclas':
        totalPlaneado = proyecto.anclas_planeadas || 0;
        unidad = 'anclas';
        campoReal = 'anclas_instaladas';
        break;
      case 'excavacion':
      default:
        totalPlaneado = proyecto.volumen_total_planeado || 0;
        unidad = 'm³';
        campoReal = 'volumen_excavacion';
        break;
    }
    
    // Calcular progreso por semana (distribuido uniformemente)
    const porSemana = semanasPlaneadas > 0 ? totalPlaneado / semanasPlaneadas : 0;
    
    // Calcular progreso real
    let acumuladoReal = 0;
    let acumuladoPlaneado = 0;

    return sortedAvances.map((avance, idx) => {
      const valorReal = avance[campoReal] || 0;
      acumuladoReal += valorReal;
      acumuladoPlaneado += porSemana;
      
      const porcentajeReal = totalPlaneado > 0 
        ? Math.min((acumuladoReal / totalPlaneado) * 100, 100) 
        : 0;
      const porcentajePlaneado = totalPlaneado > 0 
        ? Math.min((acumuladoPlaneado / totalPlaneado) * 100, 100) 
        : ((idx + 1) / semanasPlaneadas) * 100;

      return {
        semana: `Sem ${avance.semana}`,
        semanaNum: avance.semana,
        fecha: avance.fecha,
        valorReal,
        valorPlaneado: porSemana,
        acumuladoReal,
        acumuladoPlaneado,
        porcentajeReal,
        porcentajePlaneado,
        planeado: porcentajePlaneado,
        ejecutado: porcentajeReal,
        diferencia: porcentajeReal - porcentajePlaneado
      };
    });
  }, [proyecto, avances, tipoMetrica]);

  // Calcular métricas del proyecto
  const metricas = useMemo(() => {
    if (chartData.length === 0) return null;
    
    const ultimaSemana = chartData[chartData.length - 1];
    const diferencia = ultimaSemana?.diferencia || 0;
    const estado = diferencia >= 0 ? 'adelantado' : diferencia >= -10 ? 'en_tiempo' : 'retrasado';
    
    // Obtener totales para mostrar
    let totalPlaneado = 0;
    let totalEjecutado = 0;
    let unidad = '';
    let icono = Columns3;
    let color = 'blue';
    
    switch (tipoMetrica) {
      case 'pilas':
        totalPlaneado = proyecto?.pilas_planeadas || 0;
        totalEjecutado = ultimaSemana?.acumuladoReal || 0;
        unidad = 'pilas';
        icono = Columns3;
        color = 'blue';
        break;
      case 'muros':
        totalPlaneado = proyecto?.muros_planeados || 0;
        totalEjecutado = ultimaSemana?.acumuladoReal || 0;
        unidad = 'muros';
        icono = Building2;
        color = 'purple';
        break;
      case 'anclas':
        totalPlaneado = proyecto?.anclas_planeadas || 0;
        totalEjecutado = ultimaSemana?.acumuladoReal || 0;
        unidad = 'anclas';
        icono = Anchor;
        color = 'teal';
        break;
      case 'excavacion':
      default:
        totalPlaneado = proyecto?.volumen_total_planeado || 0;
        totalEjecutado = ultimaSemana?.acumuladoReal || 0;
        unidad = 'm³';
        icono = Shovel;
        color = 'amber';
        break;
    }
    
    return {
      semanasCompletadas: chartData.filter(d => d.valorReal > 0).length,
      semanasPlaneadas: proyecto?.semanas_planeadas || chartData.length,
      porcentajeActual: ultimaSemana?.porcentajeReal || 0,
      diferencia,
      estado,
      totalPlaneado,
      totalEjecutado,
      unidad,
      icono,
      color
    };
  }, [chartData, proyecto, tipoMetrica]);

  // Obtener info del tipo de métrica para mostrar
  const tipoInfo = useMemo(() => {
    switch (tipoMetrica) {
      case 'pilas':
        return { nombre: 'Pilas', icono: Columns3, color: 'blue', colorHex: '#2563EB' };
      case 'muros':
        return { nombre: 'Muros', icono: Building2, color: 'purple', colorHex: '#7C3AED' };
      case 'anclas':
        return { nombre: 'Anclas', icono: Anchor, color: 'teal', colorHex: '#0D9488' };
      case 'excavacion':
      default:
        return { nombre: 'Excavación', icono: Shovel, color: 'amber', colorHex: '#D97706' };
    }
  }, [tipoMetrica]);

  if (chartData.length === 0) {
    return (
      <div className="bg-gray-50 rounded-lg p-8 text-center text-gray-400">
        <Calendar className="h-12 w-12 mx-auto mb-2 text-gray-300" />
        <p>Sin datos de avance para mostrar</p>
      </div>
    );
  }

  const IconoTipo = tipoInfo.icono;

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 rounded-lg shadow-lg border border-gray-200">
          <p className="font-semibold text-gray-900">{label}</p>
          <p className="text-sm text-gray-500">{data.fecha}</p>
          <div className="mt-2 space-y-1">
            <p className="text-sm">
              <span className={`inline-block w-3 h-3 rounded mr-2`} style={{ backgroundColor: tipoInfo.colorHex }}></span>
              Ejecutado: <span className="font-medium">{data.porcentajeReal.toFixed(1)}%</span>
              <span className="text-gray-400 ml-1">({data.acumuladoReal.toLocaleString()} {metricas?.unidad})</span>
            </p>
            <p className="text-sm">
              <span className="inline-block w-3 h-3 rounded mr-2 bg-gray-300"></span>
              Planeado: <span className="font-medium">{data.porcentajePlaneado.toFixed(1)}%</span>
            </p>
            <p className={`text-sm font-medium ${data.diferencia >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {data.diferencia >= 0 ? '+' : ''}{data.diferencia.toFixed(1)}%
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-4">
      {/* Badge del tipo de métrica */}
      <div className="flex items-center gap-2">
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium bg-${tipoInfo.color}-100 text-${tipoInfo.color}-700`}
          style={{ backgroundColor: `${tipoInfo.colorHex}20`, color: tipoInfo.colorHex }}>
          <IconoTipo className="h-4 w-4" />
          Progresión de {tipoInfo.nombre}
        </span>
      </div>

      {/* Métricas del proyecto */}
      {metricas && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="h-4 w-4 text-blue-600" />
              <span className="text-xs font-medium text-blue-800">Semanas</span>
            </div>
            <p className="text-xl font-bold text-blue-700">
              {metricas.semanasCompletadas} / {metricas.semanasPlaneadas}
            </p>
          </div>
          
          <div className="rounded-lg p-3 border" style={{ backgroundColor: `${tipoInfo.colorHex}10`, borderColor: `${tipoInfo.colorHex}40` }}>
            <div className="flex items-center gap-2 mb-1">
              <IconoTipo className="h-4 w-4" style={{ color: tipoInfo.colorHex }} />
              <span className="text-xs font-medium" style={{ color: tipoInfo.colorHex }}>{tipoInfo.nombre}</span>
            </div>
            <p className="text-xl font-bold" style={{ color: tipoInfo.colorHex }}>
              {metricas.totalEjecutado.toLocaleString()} / {metricas.totalPlaneado.toLocaleString()}
            </p>
            <p className="text-xs text-gray-500">{metricas.unidad}</p>
          </div>
          
          <div className="bg-[#994B49]/10 rounded-lg p-3 border border-[#994B49]/20">
            <div className="flex items-center gap-2 mb-1">
              <Flag className="h-4 w-4 text-[#994B49]" />
              <span className="text-xs font-medium text-[#994B49]">Avance Total</span>
            </div>
            <p className="text-xl font-bold text-[#994B49]">
              {metricas.porcentajeActual.toFixed(1)}%
            </p>
          </div>
          
          <div className={`rounded-lg p-3 border ${
            metricas.estado === 'adelantado' ? 'bg-green-50 border-green-200' :
            metricas.estado === 'en_tiempo' ? 'bg-blue-50 border-blue-200' :
            'bg-red-50 border-red-200'
          }`}>
            <div className="flex items-center gap-2 mb-1">
              <Calendar className="h-4 w-4" />
              <span className="text-xs font-medium">Estado</span>
            </div>
            <p className={`text-xl font-bold ${
              metricas.estado === 'adelantado' ? 'text-green-700' :
              metricas.estado === 'en_tiempo' ? 'text-blue-700' :
              'text-red-700'
            }`}>
              {metricas.estado === 'adelantado' ? 'Adelantado' :
               metricas.estado === 'en_tiempo' ? 'En Tiempo' : 'Retrasado'}
            </p>
            <p className={`text-xs ${metricas.diferencia >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {metricas.diferencia >= 0 ? '+' : ''}{metricas.diferencia.toFixed(1)}% vs plan
            </p>
          </div>
        </div>
      )}

      {/* Gráfico de área - Progresión Acumulada */}
      <div className="bg-white rounded-lg p-4 border border-gray-200">
        <h4 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <IconoTipo className="h-5 w-5" style={{ color: tipoInfo.colorHex }} />
          Progresión de {tipoInfo.nombre}: Planeado vs Ejecutado
        </h4>
        
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis 
              dataKey="semana" 
              tick={{ fontSize: 11, fill: '#6B7280' }}
              axisLine={{ stroke: '#D1D5DB' }}
            />
            <YAxis 
              tick={{ fontSize: 11, fill: '#6B7280' }}
              domain={[0, 100]}
              tickFormatter={(value) => `${value}%`}
              axisLine={{ stroke: '#D1D5DB' }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend 
              wrapperStyle={{ paddingTop: '10px' }}
              formatter={(value) => <span className="text-sm text-gray-600">{value}</span>}
            />
            <Area 
              type="monotone"
              dataKey="planeado" 
              name="Planeado" 
              fill="#D1D5DB" 
              stroke="#9CA3AF"
              fillOpacity={0.3}
            />
            <Area 
              type="monotone"
              dataKey="ejecutado" 
              name="Ejecutado" 
              fill={tipoInfo.colorHex}
              stroke={tipoInfo.colorHex}
              fillOpacity={0.5}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Timeline visual estilo Gantt */}
      <div className="bg-white rounded-lg p-4 border border-gray-200">
        <h4 className="font-semibold text-gray-900 mb-4">Timeline del Proyecto</h4>
        <div className="space-y-2">
          {/* Barra de progreso planeado */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-500 w-16">Planeado</span>
            <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gray-300 rounded-full transition-all duration-500"
                style={{ width: `${(metricas?.semanasCompletadas / metricas?.semanasPlaneadas * 100) || 0}%` }}
              />
            </div>
            <span className="text-xs text-gray-600 w-12 text-right">
              {metricas?.semanasCompletadas || 0}/{metricas?.semanasPlaneadas || 0}
            </span>
          </div>
          
          {/* Barra de progreso real */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-500 w-16">Ejecutado</span>
            <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden">
              <div 
                className="h-full rounded-full transition-all duration-500"
                style={{ 
                  width: `${metricas?.porcentajeActual || 0}%`,
                  backgroundColor: metricas?.estado === 'adelantado' ? '#059669' :
                                   metricas?.estado === 'en_tiempo' ? '#3B82F6' : '#DC2626'
                }}
              />
            </div>
            <span className="text-xs text-gray-600 w-12 text-right">
              {metricas?.porcentajeActual?.toFixed(0) || 0}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
