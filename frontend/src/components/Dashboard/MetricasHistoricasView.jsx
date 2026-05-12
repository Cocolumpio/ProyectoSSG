import { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  LineChart, Line, AreaChart, Area, BarChart, Bar, 
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, 
  ResponsiveContainer, PieChart, Pie, Cell 
} from 'recharts';
import { 
  TrendingUp, Calendar, Building2, Layers, 
  ArrowUp, ArrowDown, Minus, RefreshCw, 
  Shovel, Anchor, Columns3, Box, Download, FileSpreadsheet, FileText
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const COLORS = ['#994B49', '#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899'];

export function MetricasHistoricasView({ proyectos }) {
  const [selectedProyectos, setSelectedProyectos] = useState([]);
  const [historicalData, setHistoricalData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(null); // 'excel' | 'pdf' | null
  const [viewMode, setViewMode] = useState('avance'); // avance, excavacion, cimentacion, edificacion

  useEffect(() => {
    if (proyectos.length > 0 && selectedProyectos.length === 0) {
      // Seleccionar todos los proyectos por defecto
      setSelectedProyectos(proyectos.map(p => p.id));
    }
  }, [proyectos]);

  useEffect(() => {
    if (selectedProyectos.length > 0) {
      loadHistoricalData();
    }
  }, [selectedProyectos]);

  const loadHistoricalData = async () => {
    setLoading(true);
    try {
      const allData = [];
      
      for (const proyectoId of selectedProyectos) {
        const proyecto = proyectos.find(p => p.id === proyectoId);
        if (!proyecto) continue;
        
        const response = await axios.get(`${API}/proyectos/${proyectoId}/avances-semanales`);
        const avances = response.data;
        
        // Calcular avance acumulado por semana
        let volumenAcum = 0;
        let pilasAcum = 0;
        let anclasAcum = 0;
        let murosAcum = 0;
        
        const volumenTotal = proyecto.volumen_total_planeado || 1;
        const pilasTotal = proyecto.pilas_planeadas || 1;
        const anclasTotal = proyecto.anclas_planeadas || 1;
        const murosTotal = proyecto.muros_planeados || 1;
        
        avances.forEach(avance => {
          volumenAcum += avance.volumen_excavacion || 0;
          pilasAcum += avance.pilas_completadas || 0;
          anclasAcum += avance.anclas_instaladas || 0;
          murosAcum += avance.muros_completados || 0;
          
          allData.push({
            semana: avance.semana,
            fecha: avance.fecha,
            proyecto: proyecto.nombre,
            proyectoId: proyectoId,
            avance: proyecto.avance_actual || 0,
            volumen: volumenAcum,
            volumenPct: (volumenAcum / volumenTotal) * 100,
            pilas: pilasAcum,
            pilasPct: (pilasAcum / pilasTotal) * 100,
            anclas: anclasAcum,
            anclasPct: (anclasAcum / anclasTotal) * 100,
            muros: murosAcum,
            murosPct: (murosAcum / murosTotal) * 100,
            volumenSemana: avance.volumen_excavacion || 0,
            pilasSemana: avance.pilas_completadas || 0,
            anclasSemana: avance.anclas_instaladas || 0,
            murosSemana: avance.muros_completados || 0
          });
        });
      }
      
      // Ordenar por semana
      allData.sort((a, b) => a.semana - b.semana);
      setHistoricalData(allData);
    } catch (err) {
      console.error('Error loading historical data:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleProyecto = (id) => {
    if (selectedProyectos.includes(id)) {
      setSelectedProyectos(selectedProyectos.filter(p => p !== id));
    } else {
      setSelectedProyectos([...selectedProyectos, id]);
    }
  };

  // Preparar datos para gráficas comparativas
  const prepareChartData = () => {
    const weeklyData = {};
    
    historicalData.forEach(item => {
      const key = `Sem ${item.semana}`;
      if (!weeklyData[key]) {
        weeklyData[key] = { semana: key };
      }
      
      const shortName = item.proyecto.length > 15 
        ? item.proyecto.substring(0, 12) + '...' 
        : item.proyecto;
      
      switch (viewMode) {
        case 'excavacion':
          weeklyData[key][shortName] = item.volumenPct;
          break;
        case 'cimentacion':
          weeklyData[key][`${shortName} Pilas`] = item.pilasPct;
          weeklyData[key][`${shortName} Anclas`] = item.anclasPct;
          break;
        case 'edificacion':
          weeklyData[key][shortName] = item.murosPct;
          break;
        default:
          weeklyData[key][shortName] = item.avance;
      }
    });
    
    return Object.values(weeklyData);
  };

  // Calcular totales para el resumen
  const calcularTotales = () => {
    const totales = {
      volumen: 0,
      pilas: 0,
      anclas: 0,
      muros: 0
    };
    
    // Obtener el último valor de cada proyecto
    const ultimosPorProyecto = {};
    historicalData.forEach(item => {
      ultimosPorProyecto[item.proyectoId] = item;
    });
    
    Object.values(ultimosPorProyecto).forEach(item => {
      totales.volumen += item.volumen || 0;
      totales.pilas += item.pilas || 0;
      totales.anclas += item.anclas || 0;
      totales.muros += item.muros || 0;
    });
    
    return totales;
  };

  const totales = calcularTotales();
  const chartData = prepareChartData();

  // Funciones de exportación
  const handleExportExcel = async () => {
    setExporting('excel');
    try {
      const response = await axios.get(`${API}/exportar/metricas-excel`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `DrON_Metricas_${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error exportando a Excel:', err);
      alert('Error al exportar a Excel');
    } finally {
      setExporting(null);
    }
  };

  const handleExportPDF = async () => {
    setExporting('pdf');
    try {
      const response = await axios.get(`${API}/exportar/metricas-pdf`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `DrON_Metricas_${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Error exportando a PDF:', err);
      alert('Error al exportar a PDF');
    } finally {
      setExporting(null);
    }
  };

  // Obtener nombres únicos de proyectos para las líneas del gráfico
  const getProjectKeys = () => {
    const keys = new Set();
    chartData.forEach(item => {
      Object.keys(item).forEach(key => {
        if (key !== 'semana') keys.add(key);
      });
    });
    return Array.from(keys);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Métricas Históricas</h1>
          <p className="text-white/50">Evolución del avance de todos los proyectos</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Botón Exportar Excel */}
          <button
            onClick={handleExportExcel}
            disabled={exporting === 'excel'}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
            data-testid="export-excel-btn"
          >
            <FileSpreadsheet className={`h-4 w-4 ${exporting === 'excel' ? 'animate-pulse' : ''}`} />
            <span className="hidden sm:inline">{exporting === 'excel' ? 'Exportando...' : 'Excel'}</span>
          </button>
          
          {/* Botón Exportar PDF */}
          <button
            onClick={handleExportPDF}
            disabled={exporting === 'pdf'}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
            data-testid="export-pdf-btn"
          >
            <FileText className={`h-4 w-4 ${exporting === 'pdf' ? 'animate-pulse' : ''}`} />
            <span className="hidden sm:inline">{exporting === 'pdf' ? 'Exportando...' : 'PDF'}</span>
          </button>
          
          {/* Botón Actualizar */}
          <button
            onClick={loadHistoricalData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Actualizar</span>
          </button>
        </div>
      </div>

      {/* KPIs Totales */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-orange-500/10 to-orange-500/5 rounded-xl p-4 border border-orange-500/30">
          <div className="flex items-center gap-2 text-orange-600 mb-2">
            <Shovel className="h-5 w-5" />
            <span className="text-sm font-medium">Excavación Total</span>
          </div>
          <div className="text-2xl font-bold text-orange-300">{totales.volumen.toLocaleString()} m³</div>
        </div>
        
        <div className="bg-gradient-to-br from-blue-500/10 to-blue-500/5 rounded-xl p-4 border border-blue-500/30">
          <div className="flex items-center gap-2 text-blue-600 mb-2">
            <Box className="h-5 w-5" />
            <span className="text-sm font-medium">Pilas Totales</span>
          </div>
          <div className="text-2xl font-bold text-blue-300">{totales.pilas.toLocaleString()}</div>
        </div>
        
        <div className="bg-gradient-to-br from-teal-500/10 to-teal-500/5 rounded-xl p-4 border border-teal-500/30">
          <div className="flex items-center gap-2 text-teal-600 mb-2">
            <Anchor className="h-5 w-5" />
            <span className="text-sm font-medium">Anclas Totales</span>
          </div>
          <div className="text-2xl font-bold text-teal-300">{totales.anclas.toLocaleString()}</div>
        </div>
        
        <div className="bg-gradient-to-br from-purple-500/10 to-purple-500/5 rounded-xl p-4 border border-purple-500/30">
          <div className="flex items-center gap-2 text-purple-600 mb-2">
            <Columns3 className="h-5 w-5" />
            <span className="text-sm font-medium">Muros Totales</span>
          </div>
          <div className="text-2xl font-bold text-purple-300">{totales.muros.toLocaleString()}</div>
        </div>
      </div>

      {/* Filtros y Selector de Vista */}
      <div className="bg-[#15151B] rounded-xl shadow-sm border border-white/10 p-4">
        <div className="flex flex-col md:flex-row gap-4 justify-between">
          {/* Selector de proyectos */}
          <div className="flex-1">
            <label className="block text-sm font-medium text-white/80 mb-2">Proyectos a mostrar:</label>
            <div className="flex flex-wrap gap-2">
              {proyectos.map((p, idx) => (
                <button
                  key={p.id}
                  onClick={() => toggleProyecto(p.id)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                    selectedProyectos.includes(p.id)
                      ? 'text-white'
                      : 'bg-[#15151B] text-white/60 hover:bg-[#1F1F26]'
                  }`}
                  style={{
                    backgroundColor: selectedProyectos.includes(p.id) ? COLORS[idx % COLORS.length] : undefined
                  }}
                >
                  {p.nombre.length > 20 ? p.nombre.substring(0, 17) + '...' : p.nombre}
                </button>
              ))}
            </div>
          </div>
          
          {/* Selector de vista */}
          <div>
            <label className="block text-sm font-medium text-white/80 mb-2">Métrica:</label>
            <div className="flex gap-2">
              <button
                onClick={() => setViewMode('avance')}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  viewMode === 'avance' 
                    ? 'bg-[#994B49] text-white' 
                    : 'bg-[#15151B] text-white/60 hover:bg-[#1F1F26]'
                }`}
              >
                Avance Total
              </button>
              <button
                onClick={() => setViewMode('excavacion')}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  viewMode === 'excavacion' 
                    ? 'bg-orange-500 text-white' 
                    : 'bg-[#15151B] text-white/60 hover:bg-[#1F1F26]'
                }`}
              >
                Excavación
              </button>
              <button
                onClick={() => setViewMode('cimentacion')}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  viewMode === 'cimentacion' 
                    ? 'bg-blue-500 text-white' 
                    : 'bg-[#15151B] text-white/60 hover:bg-[#1F1F26]'
                }`}
              >
                Cimentación
              </button>
              <button
                onClick={() => setViewMode('edificacion')}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  viewMode === 'edificacion' 
                    ? 'bg-purple-500 text-white' 
                    : 'bg-[#15151B] text-white/60 hover:bg-[#1F1F26]'
                }`}
              >
                Edificación
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Gráfica Principal - Evolución */}
      <div className="bg-[#15151B] rounded-xl shadow-sm border border-white/10 p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-[#994B49]" />
          Evolución del Avance por Semana
          <span className="text-sm font-normal text-white/50 ml-2">
            ({viewMode === 'avance' ? 'Avance Total %' : 
              viewMode === 'excavacion' ? 'Volumen %' :
              viewMode === 'cimentacion' ? 'Pilas/Anclas %' : 'Muros %'})
          </span>
        </h3>
        
        {loading ? (
          <div className="h-80 flex items-center justify-center">
            <RefreshCw className="h-8 w-8 animate-spin text-[#994B49]" />
          </div>
        ) : chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={chartData}>
              <defs>
                {getProjectKeys().map((key, idx) => (
                  <linearGradient key={key} id={`color${idx}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS[idx % COLORS.length]} stopOpacity={0.3}/>
                    <stop offset="95%" stopColor={COLORS[idx % COLORS.length]} stopOpacity={0}/>
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis 
                dataKey="semana" 
                tick={{ fontSize: 12 }}
                stroke="rgba(255,255,255,0.5)"
              />
              <YAxis 
                tick={{ fontSize: 12 }}
                stroke="rgba(255,255,255,0.5)"
                domain={[0, 100]}
                tickFormatter={(value) => `${value}%`}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#15151B', color: 'white', 
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
                }}
                formatter={(value) => [`${value?.toFixed(1)}%`, '']}
              />
              <Legend />
              {getProjectKeys().map((key, idx) => (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={COLORS[idx % COLORS.length]}
                  fill={`url(#color${idx})`}
                  strokeWidth={2}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-80 flex items-center justify-center text-white/50">
            Selecciona al menos un proyecto para ver las métricas
          </div>
        )}
      </div>

      {/* Gráfica de Barras - Comparativa por Proyecto */}
      <div className="bg-[#15151B] rounded-xl shadow-sm border border-white/10 p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Building2 className="h-5 w-5 text-[#994B49]" />
          Comparativa de Avance Actual por Proyecto
        </h3>
        
        <ResponsiveContainer width="100%" height={300}>
          <BarChart 
            data={proyectos.filter(p => selectedProyectos.includes(p.id)).map((p, idx) => ({
              nombre: p.nombre.length > 15 ? p.nombre.substring(0, 12) + '...' : p.nombre,
              avance: p.avance_actual || 0,
              color: COLORS[idx % COLORS.length]
            }))}
            layout="vertical"
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
            <YAxis type="category" dataKey="nombre" width={120} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(value) => [`${value.toFixed(1)}%`, 'Avance']} />
            <Bar dataKey="avance" radius={[0, 4, 4, 0]}>
              {proyectos.filter(p => selectedProyectos.includes(p.id)).map((p, idx) => (
                <Cell key={p.id} fill={COLORS[idx % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Tabla de Detalle */}
      <div className="bg-[#15151B] rounded-xl shadow-sm border border-white/10 overflow-hidden">
        <div className="px-6 py-4 border-b border-white/10 bg-[#0F0F14]">
          <h3 className="text-lg font-semibold text-white">Detalle por Proyecto</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[#0F0F14] border-b border-white/10">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-white/50 uppercase">Proyecto</th>
                <th className="px-6 py-3 text-center text-xs font-medium text-white/50 uppercase">Avance</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-orange-500 uppercase">Excavación</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-blue-500 uppercase">Pilas</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-teal-500 uppercase">Anclas</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-purple-500 uppercase">Muros</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-white/50 uppercase">Semanas</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {proyectos.filter(p => selectedProyectos.includes(p.id)).map((proyecto, idx) => {
                const lastData = historicalData.filter(d => d.proyectoId === proyecto.id).slice(-1)[0] || {};
                return (
                  <tr key={proyecto.id} className="hover:bg-[#0F0F14]">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div 
                          className="w-3 h-3 rounded-full" 
                          style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                        />
                        <span className="font-medium text-white">{proyecto.nombre}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                        (proyecto.avance_actual || 0) >= 75 ? 'bg-green-500/15 text-green-300' :
                        (proyecto.avance_actual || 0) >= 50 ? 'bg-yellow-500/15 text-yellow-300' :
                        'bg-red-500/15 text-red-300'
                      }`}>
                        {(proyecto.avance_actual || 0).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right font-mono text-sm">
                      {(lastData.volumen || 0).toLocaleString()} / {(proyecto.volumen_total_planeado || 0).toLocaleString()} m³
                    </td>
                    <td className="px-6 py-4 text-right font-mono text-sm">
                      {lastData.pilas || 0} / {proyecto.pilas_planeadas || 0}
                    </td>
                    <td className="px-6 py-4 text-right font-mono text-sm">
                      {lastData.anclas || 0} / {proyecto.anclas_planeadas || 0}
                    </td>
                    <td className="px-6 py-4 text-right font-mono text-sm">
                      {lastData.muros || 0} / {proyecto.muros_planeados || 0}
                    </td>
                    <td className="px-6 py-4 text-right font-mono text-sm text-white/50">
                      {lastData.semana || 0}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
