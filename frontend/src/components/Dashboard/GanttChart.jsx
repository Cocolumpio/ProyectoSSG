import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import { Calendar, Flag, Clock } from 'lucide-react';

export function GanttChart({ proyecto, avances = [] }) {
  const chartData = useMemo(() => {
    if (!proyecto || avances.length === 0) return [];

    const semanasPlaneadas = proyecto.semanas_planeadas || avances.length;
    const sortedAvances = [...avances].sort((a, b) => a.semana - b.semana);
    
    // Calcular volumen total planeado por semana (distribuido uniformemente)
    const volumenTotal = proyecto.volumen_total_planeado || 0;
    const volumenPorSemana = semanasPlaneadas > 0 ? volumenTotal / semanasPlaneadas : 0;
    
    // Calcular progreso real
    let acumuladoReal = 0;
    let acumuladoPlaneado = 0;

    return sortedAvances.map((avance, idx) => {
      const volReal = avance.volumen_excavacion || 0;
      acumuladoReal += volReal;
      acumuladoPlaneado += volumenPorSemana;
      
      const porcentajeReal = volumenTotal > 0 
        ? Math.min((acumuladoReal / volumenTotal) * 100, 100) 
        : 0;
      const porcentajePlaneado = volumenTotal > 0 
        ? Math.min((acumuladoPlaneado / volumenTotal) * 100, 100) 
        : ((idx + 1) / semanasPlaneadas) * 100;

      return {
        semana: `Sem ${avance.semana}`,
        semanaNum: avance.semana,
        fecha: avance.fecha,
        volumenReal: volReal,
        volumenPlaneado: volumenPorSemana,
        porcentajeReal,
        porcentajePlaneado,
        acumuladoReal,
        acumuladoPlaneado,
        // Para el Gantt visual
        planeado: porcentajePlaneado,
        ejecutado: porcentajeReal,
        diferencia: porcentajeReal - porcentajePlaneado
      };
    });
  }, [proyecto, avances]);

  // Calcular métricas del proyecto
  const metricas = useMemo(() => {
    if (chartData.length === 0) return null;
    
    const ultimaSemana = chartData[chartData.length - 1];
    const diferencia = ultimaSemana?.diferencia || 0;
    const estado = diferencia >= 0 ? 'adelantado' : diferencia >= -10 ? 'en_tiempo' : 'retrasado';
    
    return {
      semanasCompletadas: chartData.filter(d => d.volumenReal > 0).length,
      semanasPlaneadas: proyecto?.semanas_planeadas || chartData.length,
      porcentajeActual: ultimaSemana?.porcentajeReal || 0,
      diferencia,
      estado
    };
  }, [chartData, proyecto]);

  if (chartData.length === 0) {
    return (
      <div className="bg-gray-50 rounded-lg p-8 text-center text-gray-400">
        <Calendar className="h-12 w-12 mx-auto mb-2 text-gray-300" />
        <p>Sin datos de avance para mostrar</p>
      </div>
    );
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 rounded-lg shadow-lg border border-gray-200">
          <p className="font-semibold text-gray-900">{label}</p>
          <p className="text-sm text-gray-500">{data.fecha}</p>
          <div className="mt-2 space-y-1">
            <p className="text-sm">
              <span className="inline-block w-3 h-3 rounded mr-2 bg-[#994B49]"></span>
              Ejecutado: <span className="font-medium">{data.porcentajeReal.toFixed(1)}%</span>
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
      {/* Métricas del proyecto */}
      {metricas && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
            <div className="flex items-center gap-2 mb-1">
              <Clock className="h-4 w-4 text-blue-600" />
              <span className="text-xs font-medium text-blue-800">Progreso Semanal</span>
            </div>
            <p className="text-xl font-bold text-blue-700">
              {metricas.semanasCompletadas} / {metricas.semanasPlaneadas}
            </p>
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

      {/* Gráfico de barras comparativo */}
      <div className="bg-white rounded-lg p-4 border border-gray-200">
        <h4 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Calendar className="h-5 w-5 text-[#994B49]" />
          Progreso Semanal: Planeado vs Ejecutado
        </h4>
        
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData} barGap={0}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis 
              dataKey="semana" 
              tick={{ fontSize: 12, fill: '#6B7280' }}
              axisLine={{ stroke: '#D1D5DB' }}
            />
            <YAxis 
              tick={{ fontSize: 12, fill: '#6B7280' }}
              domain={[0, 100]}
              tickFormatter={(value) => `${value}%`}
              axisLine={{ stroke: '#D1D5DB' }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend 
              wrapperStyle={{ paddingTop: '10px' }}
              formatter={(value) => <span className="text-sm text-gray-600">{value}</span>}
            />
            <Bar 
              dataKey="planeado" 
              name="Planeado" 
              fill="#D1D5DB" 
              radius={[4, 4, 0, 0]}
            />
            <Bar 
              dataKey="ejecutado" 
              name="Ejecutado" 
              radius={[4, 4, 0, 0]}
            >
              {chartData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.diferencia >= 0 ? '#059669' : '#994B49'} 
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        
        <div className="flex items-center justify-center gap-6 mt-3 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-gray-300"></span> Planeado
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-green-600"></span> Adelantado
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded bg-[#994B49]"></span> Retrasado
          </span>
        </div>
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
                style={{ width: `${metricas?.semanasCompletadas / metricas?.semanasPlaneadas * 100 || 0}%` }}
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
                className={`h-full rounded-full transition-all duration-500 ${
                  metricas?.estado === 'adelantado' ? 'bg-green-500' :
                  metricas?.estado === 'en_tiempo' ? 'bg-blue-500' :
                  'bg-[#994B49]'
                }`}
                style={{ width: `${metricas?.porcentajeActual || 0}%` }}
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
