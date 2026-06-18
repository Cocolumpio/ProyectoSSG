import { useEffect, useState } from 'react';
import axios from 'axios';
import { Users, Plus, Trash2, Pencil, Check, X, Loader2, MessageCircle, Power } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/** Sección Admin: gestionar directores que reciben alertas de WhatsApp. */
export function DirectoresAdmin() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ nombre: '', whatsapp: '', cargo: 'Director' });
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState(null);

  useEffect(() => { fetchAll(); }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/directores`);
      setItems(r.data?.directores || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const guardar = async () => {
    if (!form.nombre.trim() || !form.whatsapp.trim()) {
      alert('Nombre y WhatsApp son requeridos');
      return;
    }
    setSaving(true);
    try {
      if (editingId) {
        await axios.put(`${API}/directores/${editingId}`, form);
      } else {
        await axios.post(`${API}/directores`, form);
      }
      setForm({ nombre: '', whatsapp: '', cargo: 'Director' });
      setShowForm(false);
      setEditingId(null);
      fetchAll();
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    } finally {
      setSaving(false);
    }
  };

  const editar = (d) => {
    setForm({ nombre: d.nombre, whatsapp: d.whatsapp, cargo: d.cargo, activo: d.activo });
    setEditingId(d.id);
    setShowForm(true);
  };

  const toggleActivo = async (d) => {
    await axios.put(`${API}/directores/${d.id}`, { activo: !d.activo });
    fetchAll();
  };

  const borrar = async (d) => {
    if (!window.confirm(`¿Eliminar a ${d.nombre}?`)) return;
    await axios.delete(`${API}/directores/${d.id}`);
    fetchAll();
  };

  return (
    <div className="bg-[#15151B] rounded-xl p-4 sm:p-6 border border-white/10" data-testid="directores-admin">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-cyan-400" />
          <div>
            <h3 className="text-white font-semibold">Directores con alertas de WhatsApp</h3>
            <p className="text-xs text-white/50">Reciben alertas automáticas cuando un proyecto se desvía ≥10% del programa.</p>
          </div>
        </div>
        {!showForm && (
          <button
            onClick={() => { setShowForm(true); setEditingId(null); setForm({ nombre: '', whatsapp: '', cargo: 'Director' }); }}
            className="inline-flex items-center gap-1 bg-cyan-500 hover:bg-cyan-400 text-[#0B0B0F] text-sm font-semibold px-3 py-1.5 rounded-lg"
            data-testid="add-director-btn"
          >
            <Plus className="h-4 w-4" /> Agregar
          </button>
        )}
      </div>

      {showForm && (
        <div className="bg-[#0F0F14] rounded-lg p-3 border border-cyan-500/30 mb-3 space-y-2" data-testid="director-form">
          <input
            type="text" placeholder="Nombre completo"
            value={form.nombre}
            onChange={(e) => setForm({ ...form, nombre: e.target.value })}
            className="w-full bg-[#15151B] text-white text-sm px-3 py-2 rounded border border-white/10 focus:border-cyan-400 focus:outline-none"
            data-testid="director-input-nombre"
          />
          <div className="grid grid-cols-2 gap-2">
            <input
              type="text" placeholder="WhatsApp (+52...)"
              value={form.whatsapp}
              onChange={(e) => setForm({ ...form, whatsapp: e.target.value })}
              className="bg-[#15151B] text-white text-sm px-3 py-2 rounded border border-white/10 focus:border-cyan-400 focus:outline-none"
              data-testid="director-input-whatsapp"
            />
            <input
              type="text" placeholder="Cargo"
              value={form.cargo}
              onChange={(e) => setForm({ ...form, cargo: e.target.value })}
              className="bg-[#15151B] text-white text-sm px-3 py-2 rounded border border-white/10 focus:border-cyan-400 focus:outline-none"
              data-testid="director-input-cargo"
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={guardar} disabled={saving}
              className="inline-flex items-center gap-1 bg-emerald-500 hover:bg-emerald-400 text-[#0B0B0F] text-sm font-semibold px-3 py-1.5 rounded"
              data-testid="director-save-btn"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              {editingId ? 'Actualizar' : 'Guardar'}
            </button>
            <button
              onClick={() => { setShowForm(false); setEditingId(null); }}
              className="inline-flex items-center gap-1 text-white/70 hover:text-white text-sm px-3 py-1.5 rounded"
            >
              <X className="h-4 w-4" /> Cancelar
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 text-cyan-400 animate-spin" /></div>
      ) : items.length === 0 ? (
        <div className="text-center py-8 text-white/40 text-sm">
          Aún no hay directores. Agrega al menos uno para recibir alertas.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {items.map((d) => (
            <div key={d.id} className={`flex items-center justify-between bg-[#0F0F14] rounded-lg p-3 border ${d.activo ? 'border-white/10' : 'border-white/5 opacity-50'}`}>
              <div className="flex-1 min-w-0">
                <div className="text-white font-medium text-sm truncate">{d.nombre}</div>
                <div className="text-xs text-white/40 truncate">{d.cargo}</div>
                <div className="text-xs text-cyan-300 font-mono mt-1">{d.whatsapp}</div>
              </div>
              <div className="flex items-center gap-1">
                <button onClick={() => toggleActivo(d)} title={d.activo ? 'Desactivar' : 'Activar'}
                  className={`p-1.5 rounded hover:bg-white/10 ${d.activo ? 'text-emerald-400' : 'text-white/30'}`}
                  data-testid={`director-toggle-${d.id}`}>
                  <Power className="h-4 w-4" />
                </button>
                <button onClick={() => editar(d)} className="p-1.5 rounded text-white/60 hover:text-cyan-400 hover:bg-white/10">
                  <Pencil className="h-4 w-4" />
                </button>
                <button onClick={() => borrar(d)} className="p-1.5 rounded text-white/60 hover:text-rose-400 hover:bg-white/10">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-3 text-xs text-white/40 flex items-center gap-1">
        <MessageCircle className="h-3 w-3" />
        Alerta automática al detectar desviación ≥10%. Idempotente (1 vez por semana evaluada).
      </div>
    </div>
  );
}
