import { useState } from 'react';
import { Plane, LogIn, UserPlus, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export function LoginPage() {
  const { login, register } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nombre, setNombre] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await register(email, password, nombre, 'client');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Error en la autenticación');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#F8F9FA] to-gray-200 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-[#994B49] rounded-2xl mb-4 shadow-lg">
            <Plane className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-[#994B49]">DrON</h1>
          <p className="text-gray-500">Topografía</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h2 className="text-2xl font-semibold text-gray-900 text-center mb-6">
            {isLogin ? 'Iniciar Sesión' : 'Crear Cuenta'}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre completo
                </label>
                <input
                  type="text"
                  value={nombre}
                  onChange={(e) => setNombre(e.target.value)}
                  required={!isLogin}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49] focus:border-transparent"
                  placeholder="Tu nombre"
                  data-testid="register-nombre-input"
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Correo electrónico
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49] focus:border-transparent"
                placeholder="correo@ejemplo.com"
                data-testid="login-email-input"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Contraseña
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#994B49] focus:border-transparent pr-12"
                  placeholder="••••••••"
                  data-testid="login-password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-[#994B49] text-white rounded-lg font-medium hover:bg-[#7D3C3A] transition-colors disabled:opacity-50 flex items-center justify-center space-x-2"
              data-testid="login-submit-btn"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  {isLogin ? <LogIn className="h-5 w-5" /> : <UserPlus className="h-5 w-5" />}
                  <span>{isLogin ? 'Iniciar Sesión' : 'Crear Cuenta'}</span>
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => { setIsLogin(!isLogin); setError(null); }}
              className="text-[#994B49] hover:underline text-sm font-medium"
              data-testid="toggle-auth-mode"
            >
              {isLogin ? '¿No tienes cuenta? Regístrate' : '¿Ya tienes cuenta? Inicia sesión'}
            </button>
          </div>
        </div>

        {/* Demo credentials */}
        <div className="mt-6 bg-white/50 rounded-xl p-4 text-center">
          <p className="text-sm text-gray-500 mb-2">Credenciales de demostración:</p>
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div className="bg-white rounded-lg p-2">
              <p className="font-medium text-gray-700">Admin</p>
              <p className="text-gray-500">admin@dron.mx</p>
              <p className="text-gray-400">admin123</p>
            </div>
            <div className="bg-white rounded-lg p-2">
              <p className="font-medium text-gray-700">Cliente</p>
              <p className="text-gray-500">cliente@test.com</p>
              <p className="text-gray-400">cliente123</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
