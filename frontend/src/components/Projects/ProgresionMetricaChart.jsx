/**
 * ProgresionMetricaChart — Gráfica de progresión por métrica (excavación/pilas/anclas/muros).
 * Se renderiza una por cada métrica activa en el proyecto.
 */
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';

export function ProgresionMetricaChart({ avances, metaTotal, campoReal, unidad, nombreMetrica, colorPrimario, IconoMetrica }) {
  if (!avances || avances.length === 0) return null;

  const sortedAvances = [...avances].sort((a, b) => a.semana - b.semana);
  let acumulado = 0;
  const chartData = sortedAvances.map(a => {
    acumulado += (a[campoReal] || 0);
    return {
      semana: `Sem ${a.semana}`,
      semanaNum: a.semana,
      valor: a[campoReal] || 0,
      acumulado,
      proyeccion: null,
    };
  });

  const totalEjecutado = acumulado;
  const semanasConDatos = sortedAvances.filter(a => (a[campoReal] || 0) > 0).length;
  const ritmoSemanal = semanasConDatos > 0 ? totalEjecutado / semanasConDatos : 0;
  let semanasRestantes = 0;
  if (ritmoSemanal > 0 && metaTotal > 0 && totalEjecutado < metaTotal) {
    semanasRestantes = Math.ceil((metaTotal - totalEjecutado) / ritmoSemanal);
    const ultimaSemana = sortedAvances.length > 0 ? sortedAvances[sortedAvances.length - 1].semana : 0;
    let proyeccionAcumulado = totalEjecutado;
    for (let i = 1; i <= Math.min(semanasRestantes, 8); i++) {
      proyeccionAcumulado += ritmoSemanal;
      if (proyeccionAcumulado > metaTotal) proyeccionAcumulado = metaTotal;
      chartData.push({
        semana: `Sem ${ultimaSemana + i}`,
        semanaNum: ultimaSemana + i,
        valor: null,
        acumulado: null,
        proyeccion: proyeccionAcumulado,
      });
      if (proyeccionAcumulado >= metaTotal) break;
    }
    if (chartData.length > sortedAvances.length && sortedAvances.length > 0) {
      chartData[sortedAvances.length - 1].proyeccion = totalEjecutado;
    }
  }

  const fmtVal = (v) =>
    typeof v === 'number' ? v.toLocaleString('es-MX', { maximumFractionDigits: 2 }) : v;

  return (
    <div className="bg-[#15151B] rounded-xl p-3 sm:p-4 shadow-sm" data-testid={`progresion-chart-${campoReal}`}>
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="flex items-center space-x-2">
          <IconoMetrica className="h-4 sm:h-5 w-4 sm:w-5" style={{ color: colorPrimario }} />
          <h5 className="font-semibold text-white text-sm sm:text-base">
            Progresión de {nombreMetrica}
          </h5>
        </div>
        <div className="flex items-center gap-3 text-xs">
          {metaTotal > 0 && (
            <div className="text-white/50">
              Meta: <span className="font-semibold text-green-400">{fmtVal(metaTotal)} {unidad}</span>
            </div>
          )}
          {ritmoSemanal > 0 && semanasRestantes > 0 && (
            <div className="text-white/50 bg-orange-500/10 px-2 py-1 rounded">
              📈 Ritmo: <span className="font-semibold text-orange-400">{fmtVal(ritmoSemanal)} {unidad}/sem</span>
              <span className="mx-1">•</span>
              Meta en: <span className="font-semibold text-orange-400">~{semanasRestantes} sem</span>
            </div>
          )}
          {totalEjecutado >= metaTotal && metaTotal > 0 && (
            <div className="text-green-400 bg-green-500/10 px-2 py-1 rounded font-semibold">
              ✅ Meta alcanzada
            </div>
          )}
        </div>
      </div>
      <div className="h-[180px] sm:h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="semana" stroke="rgba(255,255,255,0.5)" fontSize={11} />
            <YAxis
              stroke="rgba(255,255,255,0.5)"
              fontSize={11}
              domain={[0, metaTotal > 0 ? metaTotal * 1.05 : 'auto']}
              tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toLocaleString('es-MX', { maximumFractionDigits: 0 })}
              label={{
                value: unidad, angle: -90, position: 'insideLeft',
                style: { textAnchor: 'middle', fontSize: 10, fill: 'rgba(255,255,255,0.5)' },
              }}
            />
            <Tooltip
              formatter={(value, name) => {
                if (value === null) return [null, null];
                const label = name === 'acumulado' ? 'Total Acumulado'
                  : name === 'proyeccion' ? 'Proyección'
                  : 'Esta Semana';
                return [`${fmtVal(value)} ${unidad}`, label];
              }}
              contentStyle={{ backgroundColor: '#15151B', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: 'white' }}
            />
            {metaTotal > 0 && (
              <ReferenceLine
                y={metaTotal}
                stroke="#22C55E"
                strokeWidth={2}
                strokeDasharray="8 4"
                label={{ value: 'Meta', position: 'right', fill: '#22C55E', fontSize: 10 }}
              />
            )}
            <Line type="monotone" dataKey="acumulado" stroke={colorPrimario} strokeWidth={3}
              dot={{ fill: colorPrimario, strokeWidth: 2, r: 5 }}
              activeDot={{ r: 7, fill: colorPrimario }} name="acumulado" connectNulls={false} />
            <Line type="monotone" dataKey="proyeccion" stroke="#F97316" strokeWidth={2}
              strokeDasharray="6 3" dot={{ fill: '#F97316', strokeWidth: 2, r: 4 }}
              name="proyeccion" connectNulls={false} />
            <Line type="monotone" dataKey="valor" stroke="#60A5FA" strokeWidth={2}
              strokeDasharray="5 5" dot={{ fill: '#60A5FA', strokeWidth: 2, r: 4 }}
              name="valor" connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="flex items-center justify-center gap-3 sm:gap-5 mt-2 text-xs flex-wrap">
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-0.5" style={{ backgroundColor: colorPrimario }} />
          <span className="text-white/60">Acumulado</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-0.5 bg-blue-400" />
          <span className="text-white/60">Semanal</span>
        </div>
        {ritmoSemanal > 0 && semanasRestantes > 0 && (
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-0.5 bg-orange-500" />
            <span className="text-white/60">Proyección</span>
          </div>
        )}
        {metaTotal > 0 && (
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-0.5 bg-green-500" />
            <span className="text-white/60">Meta</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default ProgresionMetricaChart;
