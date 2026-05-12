import { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Users, Plus, Trash2, UserCheck, UserX, Shield, User,
  X, Eye, EyeOff, Search
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function UsuariosAdminView({ onShowSuccess, currentUserId }) {
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    nombre: '',
    rol: 'client'
  });
  const [showPassword, setShowPassword] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [userToDelete, setUserToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  const fetchUsuarios = async () => {
    try {
      const response = await axios.get(`${API}/auth/users`);
      setUsuarios(response.data);
    } catch (error) {
      console.error('Error fetching usuarios:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsuarios();
  }, []);

  const handleToggleActive = async (userId, currentStatus) => {
    try {
      await axios.put(`${API}/auth/users/${userId}/toggle-active`);
      onShowSuccess?.(`Usuario ${currentStatus ? 'desactivado' : 'activado'} correctamente`);
      fetchUsuarios();
    } catch (error) {
      console.error('Error toggling user status:', error);
      alert('Error al cambiar el estado del usuario');
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    
    try {
      await axios.post(`${API}/auth/register`, formData);
      onShowSuccess?.(`Usuario "${formData.nombre}" creado correctamente`);
      setShowForm(false);
      setFormData({ email: '', password: '', nombre: '', rol: 'client' });
      fetchUsuarios();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al crear el usuario');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!userToDelete) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await axios.delete(`${API}/auth/users/${userToDelete.id}`);
      onShowSuccess?.(`Usuario "${userToDelete.nombre}" eliminado correctamente`);
      setUserToDelete(null);
      fetchUsuarios();
    } catch (err) {
      setDeleteError(err.response?.data?.detail || 'Error al eliminar el usuario');
    } finally {
      setDeleting(false);
    }
  };

  const filteredUsuarios = usuarios.filter(u => 
    u.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
    u.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const adminCount = usuarios.filter(u => u.rol === 'admin').length;
  const clientCount = usuarios.filter(u => u.rol === 'client').length;
  const activeCount = usuarios.filter(u => u.activo).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-8 h-8 border-4 border-[#994B49] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white">Gestión de Usuarios</h2>
          <p className="text-white/50 text-sm">Administra los usuarios del sistema</p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center justify-center space-x-2 px-4 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors"
          data-testid="add-usuario-btn"
        >
          <Plus className="h-5 w-5" />
          <span>Nuevo Usuario</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-[#15151B] rounded-xl border border-white/10 p-4">
          <div className="flex items-center justify-between">
            <Users className="h-5 w-5 text-white/40" />
            <span className="text-2xl font-bold text-white">{usuarios.length}</span>
          </div>
          <p className="text-sm text-white/50 mt-1">Total Usuarios</p>
        </div>
        <div className="bg-[#15151B] rounded-xl border border-white/10 p-4">
          <div className="flex items-center justify-between">
            <Shield className="h-5 w-5 text-purple-500" />
            <span className="text-2xl font-bold text-purple-600">{adminCount}</span>
          </div>
          <p className="text-sm text-white/50 mt-1">Administradores</p>
        </div>
        <div className="bg-[#15151B] rounded-xl border border-white/10 p-4">
          <div className="flex items-center justify-between">
            <UserCheck className="h-5 w-5 text-green-500" />
            <span className="text-2xl font-bold text-green-600">{activeCount}</span>
          </div>
          <p className="text-sm text-white/50 mt-1">Usuarios Activos</p>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-white/40" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Buscar por nombre o email..."
          className="w-full pl-10 pr-4 py-2 border border-white/15 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
          data-testid="search-usuarios-input"
        />
      </div>

      {/* Modal de crear usuario */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[1000] p-4">
          <div className="bg-[#15151B] rounded-xl shadow-xl w-full max-w-md">
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
              <h3 className="text-lg font-semibold text-white">Nuevo Usuario</h3>
              <button onClick={() => setShowForm(false)} className="text-white/40 hover:text-white/60">
                <X className="h-6 w-6" />
              </button>
            </div>
            
            <form onSubmit={handleCreateUser} className="p-6 space-y-4">
              {error && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-300 px-4 py-3 rounded-lg text-sm">
                  {error}
                </div>
              )}
              
              <div>
                <label className="block text-sm font-medium text-white/80 mb-1">Nombre completo *</label>
                <input
                  type="text"
                  value={formData.nombre}
                  onChange={(e) => setFormData(prev => ({ ...prev, nombre: e.target.value }))}
                  required
                  className="w-full px-4 py-2 border border-white/15 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                  placeholder="Juan Pérez"
                  data-testid="usuario-nombre-input"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-white/80 mb-1">Email *</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                  required
                  className="w-full px-4 py-2 border border-white/15 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                  placeholder="correo@ejemplo.com"
                  data-testid="usuario-email-input"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-white/80 mb-1">Contraseña *</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={formData.password}
                    onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                    required
                    minLength={6}
                    className="w-full px-4 py-2 pr-10 border border-white/15 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                    placeholder="••••••••"
                    data-testid="usuario-password-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/60"
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-white/80 mb-1">Rol *</label>
                <select
                  value={formData.rol}
                  onChange={(e) => setFormData(prev => ({ ...prev, rol: e.target.value }))}
                  className="w-full px-4 py-2 border border-white/15 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49]"
                  data-testid="usuario-rol-select"
                >
                  <option value="client">Cliente (Solo lectura)</option>
                  <option value="admin">Administrador (Control total)</option>
                </select>
              </div>
              
              <div className="flex items-center justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-white/80 bg-[#15151B] rounded-lg hover:bg-[#1F1F26] transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-6 py-2 bg-[#994B49] text-white rounded-lg hover:bg-[#7D3C3A] transition-colors disabled:opacity-50"
                  data-testid="usuario-submit-btn"
                >
                  {saving ? 'Creando...' : 'Crear Usuario'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Lista de usuarios */}
      <div className="bg-[#15151B] rounded-xl border border-white/10 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full" data-testid="usuarios-table">
            <thead className="bg-[#0F0F14] border-b border-white/10">
              <tr className="text-white/80 text-sm">
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6">Usuario</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6">Email</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6">Rol</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6">Estado</th>
                <th className="text-left py-3 px-4 sm:py-4 sm:px-6">Acciones</th>
              </tr>
            </thead>
            <tbody className="text-white text-sm">
              {filteredUsuarios.map((usuario) => (
                <tr key={usuario.id} className="border-b border-white/5 hover:bg-[#0F0F14]">
                  <td className="py-3 px-4 sm:py-4 sm:px-6">
                    <div className="flex items-center space-x-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                        usuario.rol === 'admin' ? 'bg-purple-500/15' : 'bg-blue-500/15'
                      }`}>
                        {usuario.rol === 'admin' ? (
                          <Shield className="h-4 w-4 text-purple-600" />
                        ) : (
                          <User className="h-4 w-4 text-blue-600" />
                        )}
                      </div>
                      <span className="font-medium">{usuario.nombre}</span>
                    </div>
                  </td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6 text-white/50">{usuario.email}</td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      usuario.rol === 'admin' 
                        ? 'bg-purple-500/15 text-purple-300' 
                        : 'bg-blue-500/15 text-blue-300'
                    }`}>
                      {usuario.rol === 'admin' ? 'Admin' : 'Cliente'}
                    </span>
                  </td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      usuario.activo 
                        ? 'bg-green-500/15 text-green-300' 
                        : 'bg-red-500/15 text-red-300'
                    }`}>
                      {usuario.activo ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                  <td className="py-3 px-4 sm:py-4 sm:px-6">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleToggleActive(usuario.id, usuario.activo)}
                        className={`p-2 rounded-lg transition-colors ${
                          usuario.activo 
                            ? 'text-red-600 hover:bg-red-500/10' 
                            : 'text-green-600 hover:bg-green-500/10'
                        }`}
                        title={usuario.activo ? 'Desactivar usuario' : 'Activar usuario'}
                        data-testid={`toggle-usuario-${usuario.id}`}
                      >
                        {usuario.activo ? (
                          <UserX className="h-5 w-5" />
                        ) : (
                          <UserCheck className="h-5 w-5" />
                        )}
                      </button>
                      {usuario.id !== currentUserId && (
                        <button
                          onClick={() => { setUserToDelete(usuario); setDeleteError(null); }}
                          className="p-2 rounded-lg text-white/50 hover:text-red-300 hover:bg-red-500/10 transition-colors"
                          title="Eliminar usuario permanentemente"
                          data-testid={`delete-usuario-${usuario.id}`}
                        >
                          <Trash2 className="h-5 w-5" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {filteredUsuarios.length === 0 && (
        <div className="text-center py-12 text-white/50">
          <Users className="h-12 w-12 mx-auto mb-4 text-white/30" />
          <p>No se encontraron usuarios</p>
        </div>
      )}

      {/* Modal de confirmación de eliminación */}
      {userToDelete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[1000] p-4" data-testid="delete-usuario-modal">
          <div className="bg-[#15151B] rounded-xl shadow-xl w-full max-w-md">
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
              <h3 className="text-lg font-semibold text-white">Eliminar usuario</h3>
              <button
                onClick={() => { setUserToDelete(null); setDeleteError(null); }}
                className="text-white/40 hover:text-white/60"
                disabled={deleting}
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                <Trash2 className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-red-300">
                  <p className="font-medium">Esta acción es permanente e irreversible.</p>
                  <p className="mt-1">
                    Vas a eliminar a <span className="font-semibold">{userToDelete.nombre}</span> (<span className="break-all">{userToDelete.email}</span>).
                    {userToDelete.rol === 'client' && ' El usuario será desasignado de todos sus proyectos.'}
                  </p>
                </div>
              </div>
              {deleteError && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-300 px-4 py-3 rounded-lg text-sm" data-testid="delete-usuario-error">
                  {deleteError}
                </div>
              )}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={() => { setUserToDelete(null); setDeleteError(null); }}
                  disabled={deleting}
                  className="px-4 py-2 text-white/80 bg-[#15151B] rounded-lg hover:bg-[#1F1F26] transition-colors disabled:opacity-50"
                  data-testid="cancel-delete-usuario-btn"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleDeleteUser}
                  disabled={deleting}
                  className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                  data-testid="confirm-delete-usuario-btn"
                >
                  <Trash2 className="h-4 w-4" />
                  {deleting ? 'Eliminando...' : 'Eliminar definitivamente'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
