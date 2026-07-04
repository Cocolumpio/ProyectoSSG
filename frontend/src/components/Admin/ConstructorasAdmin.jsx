import { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { Building2, Plus, Trash2, Pencil, Check, X, Loader2, Power, Upload, ImageOff } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/** Admin: gestionar constructoras/clientes que se muestran como logos en la landing. */
export function ConstructorasAdmin() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ nombre: '', orden: 0, activo: true, logo: null });
  const [logoPreview, setLogoPreview] = useState(null);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const r = await axios.get(`${API}/constructoras`);
      setItems(r.data?.constructoras || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setForm({ nombre: '', orden: 0, activo: true, logo: null });
    setLogoPreview(null);
    setEditingId(null);
    setShowForm(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleLogoChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 3 * 1024 * 1024) {
      alert('El logo no debe superar 3MB');
      return;
    }
    setForm((f) => ({ ...f, logo: file }));
    setLogoPreview(URL.createObjectURL(file));
  };

  const guardar = async () => {
    if (!form.nombre.trim()) {
      alert('El nombre es requerido');
      return;
    }
    if (!editingId && !form.logo) {
      alert('Sube el logo PNG/JPG/WEBP/SVG de la constructora');
      return;
    }
    setSaving(true);
    try {
      const fd = new FormData();
      fd.append('nombre', form.nombre.trim());
      fd.append('activo', form.activo ? 'true' : 'false');
      fd.append('orden', String(form.orden || 0));
      if (form.logo) fd.append('logo', form.logo);
      if (editingId) {
        await axios.put(`${API}/constructoras/${editingId}`, fd);
      } else {
        await axios.post(`${API}/constructoras`, fd);
      }
      resetForm();
      fetchAll();
    } catch (e) {
      alert(e?.response?.data?.detail || e.message);
    } finally {
      setSaving(false);
    }
  };

  const editar = (c) => {
    setForm({ nombre: c.nombre || '', orden: c.orden || 0, activo: !!c.activo, logo: null });
    setLogoPreview(null);
    setEditingId(c.id);
    setShowForm(true);
  };

  const toggleActivo = async (c) => {
    const fd = new FormData();
    fd.append('activo', c.activo ? 'false' : 'true');
    await axios.put(`${API}/constructoras/${c.id}`, fd);
    fetchAll();
  };

  const borrar = async (c) => {
    if (!window.confirm(`¿Eliminar la constructora "${c.nombre}"? Las obras vinculadas quedarán sin cliente.`)) return;
    await axios.delete(`${API}/constructoras/${c.id}`);
    fetchAll();
  };

  const logoSrc = (c) => (c.logo_url ? `${process.env.REACT_APP_BACKEND_URL}${c.logo_url}` : null);

  return (
    <div className="bg-[#15151B] rounded-xl p-4 sm:p-6 border border-white/10" data-testid="constructoras-admin">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Building2 className="h-5 w-5 text-amber-400" />
          <div>
            <h3 className="text-white font-semibold">Constructoras (clientes)</h3>
            <p className="text-xs text-white/50">Se muestran como logos en la landing pública. Puedes asignar cada obra a una constructora.</p>
          </div>
        </div>
        {!showForm && (
          <button
            onClick={() => { setShowForm(true); setEditingId(null); }}
            className="inline-flex items-center gap-1 bg-amber-500 hover:bg-amber-400 text-[#0B0B0F] text-sm font-semibold px-3 py-1.5 rounded-lg"
            data-testid="add-constructora-btn"
          >
            <Plus className="h-4 w-4" /> Agregar
          </button>
        )}
      </div>

      {showForm && (
        <div className="bg-[#0F0F14] rounded-lg p-3 border border-amber-500/30 mb-3 space-y-2" data-testid="constructora-form">
          <input
            type="text" placeholder="Nombre (ej. Constructora XYZ, S.A. de C.V.)"
            value={form.nombre}
            onChange={(e) => setForm({ ...form, nombre: e.target.value })}
            className="w-full bg-[#15151B] text-white text-sm px-3 py-2 rounded border border-white/10 focus:border-amber-400 focus:outline-none"
            data-testid="constructora-input-nombre"
          />
          <div className="grid grid-cols-2 gap-2">
            <input
              type="number" placeholder="Orden (0 = primero)"
              value={form.orden}
              onChange={(e) => setForm({ ...form, orden: parseInt(e.target.value) || 0 })}
              className="bg-[#15151B] text-white text-sm px-3 py-2 rounded border border-white/10 focus:border-amber-400 focus:outline-none"
              data-testid="constructora-input-orden"
            />
            <label className="flex items-center gap-2 text-white/80 text-sm px-3 py-2 bg-[#15151B] rounded border border-white/10 cursor-pointer">
              <input
                type="checkbox"
                checked={form.activo}
                onChange={(e) => setForm({ ...form, activo: e.target.checked })}
                data-testid="constructora-input-activo"
              />
              Activa (visible en landing)
            </label>
          </div>
          <div className="flex items-center gap-3 bg-[#15151B] rounded border border-dashed border-white/10 p-3">
            {logoPreview ? (
              <img src={logoPreview} alt="preview" className="h-16 w-24 object-contain bg-white/5 rounded" />
            ) : (
              <div className="h-16 w-24 rounded bg-white/5 flex items-center justify-center text-white/30">
                <ImageOff className="h-6 w-6" />
              </div>
            )}
            <div className="flex-1">
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp,image/svg+xml"
                onChange={handleLogoChange}
                ref={fileInputRef}
                className="hidden"
                data-testid="constructora-input-logo"
                id="constructora-logo-input"
              />
              <label
                htmlFor="constructora-logo-input"
                className="inline-flex items-center gap-1 bg-white/10 hover:bg-white/20 text-white text-sm px-3 py-1.5 rounded cursor-pointer"
              >
                <Upload className="h-4 w-4" /> {editingId ? 'Cambiar logo' : 'Subir logo'}
              </label>
              <p className="text-xs text-white/40 mt-1">
                PNG/JPG/WEBP/SVG. Máx 3MB. Se recomienda fondo transparente.
                {editingId && !form.logo && ' (Deja vacío para conservar el actual)'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={guardar} disabled={saving}
              className="inline-flex items-center gap-1 bg-emerald-500 hover:bg-emerald-400 text-[#0B0B0F] text-sm font-semibold px-3 py-1.5 rounded"
              data-testid="constructora-save-btn"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              {editingId ? 'Actualizar' : 'Guardar'}
            </button>
            <button
              onClick={resetForm}
              className="inline-flex items-center gap-1 text-white/70 hover:text-white text-sm px-3 py-1.5 rounded"
            >
              <X className="h-4 w-4" /> Cancelar
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 text-amber-400 animate-spin" /></div>
      ) : items.length === 0 ? (
        <div className="text-center py-8 text-white/40 text-sm">
          Aún no hay constructoras. Agrega la primera para mostrar su logo en la landing.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2" data-testid="constructoras-list">
          {items.map((c) => (
            <div key={c.id} className={`flex items-center gap-3 bg-[#0F0F14] rounded-lg p-3 border ${c.activo ? 'border-white/10' : 'border-white/5 opacity-50'}`}>
              {logoSrc(c) ? (
                <img src={logoSrc(c)} alt={c.nombre} className="h-14 w-20 object-contain bg-white/5 rounded" />
              ) : (
                <div className="h-14 w-20 rounded bg-white/5 flex items-center justify-center text-white/30">
                  <ImageOff className="h-5 w-5" />
                </div>
              )}
              <div className="flex-1 min-w-0">
                <div className="text-white font-medium text-sm truncate">{c.nombre}</div>
                <div className="text-xs text-white/40">Orden: {c.orden || 0}</div>
              </div>
              <div className="flex items-center gap-1">
                <button onClick={() => toggleActivo(c)} title={c.activo ? 'Ocultar en landing' : 'Mostrar en landing'}
                  className={`p-1.5 rounded hover:bg-white/10 ${c.activo ? 'text-emerald-400' : 'text-white/30'}`}
                  data-testid={`constructora-toggle-${c.id}`}>
                  <Power className="h-4 w-4" />
                </button>
                <button onClick={() => editar(c)} className="p-1.5 rounded text-white/60 hover:text-amber-400 hover:bg-white/10"
                  data-testid={`constructora-edit-${c.id}`}>
                  <Pencil className="h-4 w-4" />
                </button>
                <button onClick={() => borrar(c)} className="p-1.5 rounded text-white/60 hover:text-rose-400 hover:bg-white/10"
                  data-testid={`constructora-delete-${c.id}`}>
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
