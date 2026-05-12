import { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import {
  ArrowRight, Plane, Brain, BarChart3, Bell, FileText, Layers,
  Wrench, ShieldCheck, Camera, MapPin, Mail, Phone, Check,
  ChevronRight, Zap, Eye, Cpu, Sparkles, ArrowUpRight,
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/* ------------------------------------------------------------------ */
/*  Reveal-on-scroll helper                                           */
/* ------------------------------------------------------------------ */
function useReveal() {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (!ref.current) return;
    const obs = new IntersectionObserver(
      ([e]) => e.isIntersecting && setVisible(true),
      { threshold: 0.15 }
    );
    obs.observe(ref.current);
    return () => obs.disconnect();
  }, []);
  return [ref, visible];
}

function Reveal({ children, delay = 0, className = '' }) {
  const [ref, visible] = useReveal();
  return (
    <div
      ref={ref}
      style={{ transitionDelay: `${delay}ms` }}
      className={`transition-all duration-[900ms] ease-out ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
      } ${className}`}
    >
      {children}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Animated KPI counter                                              */
/* ------------------------------------------------------------------ */
function Counter({ end, suffix = '', duration = 1800, decimals = 0 }) {
  const [v, setV] = useState(0);
  const [ref, visible] = useReveal();
  useEffect(() => {
    if (!visible) return;
    let start = 0;
    const t0 = performance.now();
    let raf;
    const step = (now) => {
      const p = Math.min((now - t0) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setV(start + (end - start) * eased);
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [visible, end, duration]);
  return (
    <span ref={ref}>
      {decimals > 0 ? v.toFixed(decimals) : Math.round(v).toLocaleString('es-MX')}
      {suffix}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Landing Page                                                       */
/* ------------------------------------------------------------------ */
export function LandingPage() {
  const [scrolled, setScrolled] = useState(false);
  const [formData, setFormData] = useState({
    nombre_proyecto: '',
    fecha_inicio_proyecto: '',
    fecha_fin_proyecto: '',
    fecha_vuelo_deseada: '',
    notas: '',
  });
  const [contact, setContact] = useState({ nombre: '', empresa: '', email: '', telefono: '' });
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 30);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSending(true);
    setError(null);
    try {
      const today = new Date().toISOString().split('T')[0];
      const future = new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0];
      await axios.post(`${API}/solicitudes-vuelo`, {
        nombre_proyecto: formData.nombre_proyecto || `${contact.empresa || contact.nombre} - Demo`,
        fecha_inicio_proyecto: formData.fecha_inicio_proyecto || today,
        fecha_fin_proyecto: formData.fecha_fin_proyecto || future,
        fecha_vuelo_deseada: formData.fecha_vuelo_deseada || future,
        notas: `[LANDING DEMO]\nNombre: ${contact.nombre}\nEmpresa: ${contact.empresa}\nEmail: ${contact.email}\nTel: ${contact.telefono}\n---\n${formData.notas || 'Solicitud de demo desde landing.'}`,
      });
      setSent(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'No pudimos enviar tu solicitud. Escríbenos directo a hola@dron-topografia.com');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="bg-[#0B0B0F] text-white antialiased min-h-screen overflow-x-hidden selection:bg-[#994B49] selection:text-white">
      {/* Grain overlay */}
      <div
        className="pointer-events-none fixed inset-0 z-[1] opacity-[0.035] mix-blend-overlay"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
        }}
      />

      {/* ============================== NAV ============================== */}
      <nav
        className={`fixed top-0 inset-x-0 z-50 transition-all duration-500 ${
          scrolled
            ? 'bg-[#0B0B0F]/80 backdrop-blur-xl border-b border-white/5 py-3'
            : 'bg-transparent py-5'
        }`}
      >
        <div className="max-w-7xl mx-auto px-6 lg:px-10 flex items-center justify-between">
          <a href="#top" className="flex items-center gap-2" data-testid="landing-logo">
            <img
              src="/logo-dron-dark.png"
              alt="DrON Topografía"
              className="h-14 sm:h-16 w-auto"
              style={{ filter: 'brightness(0) invert(1)' }}
            />
          </a>

          <div className="hidden md:flex items-center gap-7 text-sm text-white/70">
            <a href="#servicios" className="hover:text-white transition-colors">Servicios</a>
            <a href="#tecnologia" className="hover:text-white transition-colors">Tecnología</a>
            <a href="#proceso" className="hover:text-white transition-colors">Proceso</a>
            <a href="#precios" className="hover:text-white transition-colors">Precios</a>
            <a href="#faq" className="hover:text-white transition-colors">FAQ</a>
          </div>

          <div className="flex items-center gap-3">
            <Link
              to="/app"
              className="hidden sm:inline-flex text-sm text-white/80 hover:text-white transition-colors px-4 py-2"
              data-testid="landing-login-link"
            >
              Iniciar sesión
            </Link>
            <a
              href="#contacto"
              className="inline-flex items-center gap-1.5 text-sm bg-[#994B49] hover:bg-[#B35A57] px-4 py-2 rounded-full transition-all shadow-lg shadow-[#994B49]/20 hover:shadow-[#994B49]/40"
              data-testid="landing-cta-nav"
            >
              Solicitar demo <ArrowRight className="h-4 w-4" />
            </a>
          </div>
        </div>
      </nav>

      {/* ============================== HERO ============================== */}
      <section id="top" className="relative pt-40 pb-32 px-6 lg:px-10 overflow-hidden">
        {/* Glow background */}
        <div className="absolute inset-0 -z-0">
          <div className="absolute top-20 -left-40 w-[600px] h-[600px] rounded-full bg-[#994B49]/15 blur-[120px]" />
          <div className="absolute top-40 right-0 w-[500px] h-[500px] rounded-full bg-[#E07A5F]/10 blur-[120px]" />
        </div>

        <div className="max-w-7xl mx-auto grid lg:grid-cols-12 gap-12 items-center relative">
          <div className="lg:col-span-7">
            <Reveal>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-white/10 bg-white/5 backdrop-blur text-xs text-white/70 mb-8">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#E07A5F] opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-[#E07A5F]"></span>
                </span>
                Plataforma operativa en México · 2026
              </div>
            </Reveal>

            <Reveal delay={80}>
              <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold leading-[1.02] tracking-tight">
                Tu obra,<br />
                <span className="text-white/40">monitoreada</span><br />
                <span className="relative inline-block">
                  desde el cielo.
                  <svg className="absolute -bottom-2 left-0 w-full h-3 text-[#994B49]" viewBox="0 0 200 12" fill="none">
                    <path d="M2 9 Q 50 1, 100 6 T 198 4" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                  </svg>
                </span>
              </h1>
            </Reveal>

            <Reveal delay={180}>
              <p className="mt-8 text-lg sm:text-xl text-white/60 max-w-2xl leading-relaxed">
                Vuelos de dron semanales, modelos 3D, conteo automático de pilas y anclas con IA, y un dashboard que tu director financiero podrá entender en 10 segundos.
              </p>
            </Reveal>

            <Reveal delay={280}>
              <div className="mt-10 flex flex-col sm:flex-row gap-4">
                <a
                  href="#contacto"
                  className="inline-flex items-center justify-center gap-2 bg-[#994B49] hover:bg-[#B35A57] px-7 py-4 rounded-full font-medium transition-all shadow-xl shadow-[#994B49]/30 hover:shadow-[#994B49]/50 hover:-translate-y-0.5"
                  data-testid="hero-cta-primary"
                >
                  Programa tu primer vuelo
                  <ArrowRight className="h-4 w-4" />
                </a>
                <a
                  href="#tecnologia"
                  className="inline-flex items-center justify-center gap-2 border border-white/15 hover:bg-white/5 px-7 py-4 rounded-full font-medium transition-all"
                  data-testid="hero-cta-secondary"
                >
                  Ver cómo funciona
                  <ChevronRight className="h-4 w-4" />
                </a>
              </div>
            </Reveal>

            <Reveal delay={420}>
              <div className="mt-14 grid grid-cols-3 gap-6 max-w-xl">
                {[
                  { v: 250000, s: ' m³', l: 'monitoreados' },
                  { v: 12, s: 'x', l: 'más rápido que medición manual' },
                  { v: 98, s: '%', l: 'precisión vs. residente' },
                ].map((k, i) => (
                  <div key={i}>
                    <div className="text-3xl sm:text-4xl font-bold text-white">
                      <Counter end={k.v} suffix={k.s} />
                    </div>
                    <div className="text-xs text-white/50 mt-1.5 leading-tight">{k.l}</div>
                  </div>
                ))}
              </div>
            </Reveal>
          </div>

          {/* Right: dashboard mockup */}
          <div className="lg:col-span-5 relative">
            <Reveal delay={300}>
              <div className="relative">
                <div className="absolute -inset-6 bg-gradient-to-br from-[#994B49]/30 to-[#E07A5F]/10 blur-3xl rounded-full" />
                <div className="relative bg-gradient-to-br from-white/[0.07] to-white/[0.02] backdrop-blur-xl border border-white/10 rounded-2xl p-5 shadow-2xl">
                  <div className="flex items-center gap-1.5 mb-4">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-400/60" />
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-400/60" />
                    <div className="w-2.5 h-2.5 rounded-full bg-green-400/60" />
                    <div className="ml-2 text-xs text-white/40 font-mono">dron-topografia.com / dashboard</div>
                  </div>

                  {/* Mock dashboard content */}
                  <div className="space-y-3">
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-white/40">Torre Corporativa Reforma</span>
                      <span className="px-2 py-0.5 rounded-full bg-green-400/10 text-green-400 text-[10px] border border-green-400/20">EN TIEMPO</span>
                    </div>

                    <div className="bg-white/[0.03] rounded-lg p-3 border border-white/5">
                      <div className="flex justify-between text-xs text-white/50 mb-2">
                        <span>Avance general</span>
                        <span className="text-white font-medium">63.4%</span>
                      </div>
                      <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-[#994B49] to-[#E07A5F] rounded-full animate-pulse" style={{ width: '63.4%' }} />
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2">
                      {[
                        { l: 'Excavación', v: '14,200', u: 'm³', c: '#E07A5F' },
                        { l: 'Pilas', v: '82', u: '/120', c: '#FFB74D' },
                        { l: 'Anclas', v: '156', u: '/240', c: '#81C784' },
                      ].map((m, i) => (
                        <div key={i} className="bg-white/[0.03] rounded-lg p-2.5 border border-white/5">
                          <div className="text-[10px] text-white/40 uppercase tracking-wide">{m.l}</div>
                          <div className="text-base font-bold mt-1" style={{ color: m.c }}>{m.v}<span className="text-xs text-white/40 font-normal ml-0.5">{m.u}</span></div>
                        </div>
                      ))}
                    </div>

                    {/* fake 3d chart */}
                    <div className="bg-white/[0.03] rounded-lg p-3 border border-white/5 h-32 relative overflow-hidden">
                      <div className="text-[10px] text-white/40 uppercase tracking-wide mb-2">Modelo 3D · Semana 8</div>
                      <svg className="w-full h-20" viewBox="0 0 200 80">
                        {Array.from({ length: 60 }).map((_, i) => (
                          <circle
                            key={i}
                            cx={20 + (i % 12) * 14}
                            cy={20 + Math.sin(i) * 8 + (Math.floor(i / 12) * 12)}
                            r={1}
                            fill={`hsl(${15 + i * 2}, 70%, 60%)`}
                            opacity={0.7}
                          />
                        ))}
                      </svg>
                    </div>

                    <div className="flex items-center gap-2 text-[10px] text-white/40 pt-1">
                      <Bell className="h-3 w-3" />
                      <span>Última alerta: Cimentación con desviación de +3 días</span>
                    </div>
                  </div>
                </div>

                {/* Floating card */}
                <div className="absolute -bottom-6 -left-6 bg-[#0B0B0F] border border-white/10 rounded-xl p-3 shadow-2xl hidden sm:flex items-center gap-3 max-w-[240px]">
                  <div className="w-9 h-9 rounded-full bg-[#994B49]/20 grid place-items-center flex-shrink-0">
                    <Brain className="h-5 w-5 text-[#E07A5F]" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold">IA detectó 82 pilas</div>
                    <div className="text-[10px] text-white/50">Confianza: ALTA · Gemini Vision</div>
                  </div>
                </div>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* ============================== LOGOS ============================== */}
      <section className="border-y border-white/5 py-10">
        <div className="max-w-7xl mx-auto px-6 lg:px-10">
          <p className="text-center text-xs uppercase tracking-[0.3em] text-white/30 mb-6">
            Tecnología de confianza para constructoras mexicanas
          </p>
          <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-4 opacity-50">
            {['ICA', 'GIA+A', 'CARSO', 'CICSA', 'MARHNOS', 'COCONAL'].map((n) => (
              <span key={n} className="text-white/40 font-bold tracking-widest text-sm">{n}</span>
            ))}
          </div>
        </div>
      </section>

      {/* ============================== SERVICIOS ============================== */}
      <section id="servicios" className="py-32 px-6 lg:px-10">
        <div className="max-w-7xl mx-auto">
          <Reveal>
            <div className="max-w-3xl">
              <span className="text-xs uppercase tracking-[0.3em] text-[#E07A5F] mb-4 block">— Servicios</span>
              <h2 className="text-4xl sm:text-5xl font-bold tracking-tight">
                Todo lo que tu obra necesita,<br />
                <span className="text-white/40">en una sola plataforma.</span>
              </h2>
            </div>
          </Reveal>

          <div className="mt-20 grid md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              { icon: Camera, title: 'Vuelos de dron semanales', desc: 'Levantamientos fotogramétricos con drones DJI profesionales. Cobertura de hasta 50 ha por vuelo.' },
              { icon: Layers, title: 'Modelos 3D navegables', desc: 'Nubes de puntos PLY procesadas en el navegador. Tu cliente las explora sin instalar nada.' },
              { icon: Brain, title: 'IA Gemini Vision', desc: 'Cuenta pilas, anclas y muros desde fotos aéreas. Compara reportes del residente vs datos reales.' },
              { icon: Wrench, title: 'Plan óptimo de maquinaria', desc: 'Sube tu catálogo en Excel y la IA propone qué máquinas usar, cuándo y cuántos días tomará.' },
              { icon: Bell, title: 'Alertas de desviación', desc: 'Notificaciones automáticas por correo y en la app cuando el avance real se aleja del cronograma.' },
              { icon: FileText, title: 'Reportes ejecutivos', desc: 'Genera PDFs y Excel listos para presentar a inversionistas con un solo clic.' },
            ].map((s, i) => (
              <Reveal key={i} delay={i * 70}>
                <div className="group h-full bg-white/[0.02] hover:bg-white/[0.04] border border-white/5 hover:border-[#994B49]/40 rounded-2xl p-7 transition-all duration-500 hover:-translate-y-1">
                  <div className="w-12 h-12 rounded-xl bg-[#994B49]/10 grid place-items-center mb-5 group-hover:bg-[#994B49]/20 transition-colors">
                    <s.icon className="h-5 w-5 text-[#E07A5F]" />
                  </div>
                  <h3 className="text-lg font-semibold mb-2 tracking-tight">{s.title}</h3>
                  <p className="text-sm text-white/50 leading-relaxed">{s.desc}</p>
                  <div className="mt-5 flex items-center gap-1 text-xs text-[#E07A5F] opacity-0 group-hover:opacity-100 transition-opacity">
                    Saber más <ArrowUpRight className="h-3 w-3" />
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ============================== PROCESO ============================== */}
      <section id="proceso" className="py-32 px-6 lg:px-10 relative">
        <div className="max-w-7xl mx-auto">
          <Reveal>
            <div className="text-center max-w-3xl mx-auto">
              <span className="text-xs uppercase tracking-[0.3em] text-[#E07A5F] mb-4 block">— Cómo funciona</span>
              <h2 className="text-4xl sm:text-5xl font-bold tracking-tight">
                De vuelo a decisión <span className="text-white/40">en horas, no semanas.</span>
              </h2>
            </div>
          </Reveal>

          <div className="mt-20 grid md:grid-cols-3 gap-8 relative">
            {/* Connector line */}
            <div className="hidden md:block absolute top-12 left-[16%] right-[16%] h-px bg-gradient-to-r from-transparent via-[#994B49]/40 to-transparent" />

            {[
              { n: '01', icon: Plane, title: 'Volamos tu obra', desc: 'Cada semana, un piloto certificado SCT levanta tu obra con dron profesional.' },
              { n: '02', icon: Cpu, title: 'IA procesa todo', desc: 'Open3D, Gemini Vision y nuestra plataforma generan modelos 3D, conteos y métricas.' },
              { n: '03', icon: Eye, title: 'Tu equipo decide', desc: 'Dashboard accesible desde cualquier dispositivo. Reportes en PDF a un clic.' },
            ].map((p, i) => (
              <Reveal key={i} delay={i * 150}>
                <div className="relative text-center">
                  <div className="relative inline-block mb-6">
                    <div className="w-24 h-24 mx-auto rounded-2xl bg-gradient-to-br from-[#994B49] to-[#7D3C3A] grid place-items-center shadow-xl shadow-[#994B49]/30">
                      <p.icon className="h-9 w-9 text-white" />
                    </div>
                    <div className="absolute -top-2 -right-2 bg-[#0B0B0F] border border-[#994B49] rounded-full px-2.5 py-1 text-xs font-mono text-[#E07A5F]">
                      {p.n}
                    </div>
                  </div>
                  <h3 className="text-xl font-semibold mb-3">{p.title}</h3>
                  <p className="text-sm text-white/50 max-w-xs mx-auto leading-relaxed">{p.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ============================== TECNOLOGÍA ============================== */}
      <section id="tecnologia" className="py-32 px-6 lg:px-10 bg-gradient-to-b from-transparent via-white/[0.02] to-transparent">
        <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-16 items-center">
          <Reveal>
            <div>
              <span className="text-xs uppercase tracking-[0.3em] text-[#E07A5F] mb-4 block">— IA en producción</span>
              <h2 className="text-4xl sm:text-5xl font-bold tracking-tight mb-6">
                No es una hoja de Excel<br />con un nombre fancy.
              </h2>
              <p className="text-white/60 leading-relaxed text-lg mb-8">
                Cada foto aérea pasa por <strong className="text-white">Gemini Vision</strong> para detectar pilas, anclas y muros. Cada modelo 3D se simplifica con <strong className="text-white">Open3D</strong> para que se vea en tu navegador en segundos. Cada PDF del residente se compara automáticamente contra los datos del dron.
              </p>
              <ul className="space-y-3">
                {[
                  'Conteo automático de elementos constructivos con confianza ALTA/MEDIA/BAJA',
                  'Comparación PDF residente vs. datos del dron — discrepancias detectadas al instante',
                  'Plan de obra generado por IA según tu catálogo de maquinaria real',
                  'Modelos 3D PLY de cientos de MB optimizados a versión web sin perder fidelidad',
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-3 text-white/70">
                    <div className="w-5 h-5 rounded-full bg-[#994B49]/20 grid place-items-center flex-shrink-0 mt-0.5">
                      <Check className="h-3 w-3 text-[#E07A5F]" />
                    </div>
                    <span className="text-sm">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>

          <Reveal delay={200}>
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-[#994B49]/20 to-transparent blur-3xl" />
              {/* Before / After IA */}
              <div className="relative bg-[#0B0B0F] border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
                <div className="grid grid-cols-2">
                  <div className="p-6 border-r border-white/5">
                    <div className="text-[10px] uppercase tracking-widest text-white/30 mb-3">Foto aérea cruda</div>
                    <div className="aspect-square rounded-lg bg-gradient-to-br from-stone-700 to-stone-900 relative overflow-hidden">
                      {Array.from({ length: 30 }).map((_, i) => (
                        <div
                          key={i}
                          className="absolute w-1.5 h-1.5 rounded-full bg-stone-400/60"
                          style={{
                            left: `${10 + (i % 6) * 15}%`,
                            top: `${10 + Math.floor(i / 6) * 18}%`,
                          }}
                        />
                      ))}
                    </div>
                  </div>
                  <div className="p-6 bg-[#994B49]/[0.04]">
                    <div className="text-[10px] uppercase tracking-widest text-[#E07A5F] mb-3 flex items-center gap-1.5">
                      <Sparkles className="h-3 w-3" /> Procesado por IA
                    </div>
                    <div className="aspect-square rounded-lg bg-gradient-to-br from-stone-700 to-stone-900 relative overflow-hidden">
                      {Array.from({ length: 30 }).map((_, i) => (
                        <div
                          key={i}
                          className="absolute w-3 h-3 rounded border border-[#E07A5F] bg-[#E07A5F]/20"
                          style={{
                            left: `${9 + (i % 6) * 15}%`,
                            top: `${9 + Math.floor(i / 6) * 18}%`,
                          }}
                        />
                      ))}
                      <div className="absolute bottom-2 left-2 text-[9px] text-[#E07A5F] font-mono bg-black/40 px-1.5 py-0.5 rounded">
                        30 pilas · 98% conf.
                      </div>
                    </div>
                  </div>
                </div>
                <div className="border-t border-white/5 p-5 grid grid-cols-3 gap-4 text-center">
                  <div>
                    <div className="text-2xl font-bold text-[#E07A5F]"><Counter end={30} /></div>
                    <div className="text-[10px] text-white/40 uppercase">Pilas</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-[#E07A5F]"><Counter end={47} /></div>
                    <div className="text-[10px] text-white/40 uppercase">Anclas</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-[#E07A5F]"><Counter end={8} /></div>
                    <div className="text-[10px] text-white/40 uppercase">Maquinaria</div>
                  </div>
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ============================== COMPARATIVA ============================== */}
      <section className="py-32 px-6 lg:px-10">
        <div className="max-w-5xl mx-auto">
          <Reveal>
            <div className="text-center mb-16">
              <span className="text-xs uppercase tracking-[0.3em] text-[#E07A5F] mb-4 block">— Comparativa</span>
              <h2 className="text-4xl sm:text-5xl font-bold tracking-tight">
                Medición manual <span className="text-white/40">vs.</span> DrON
              </h2>
            </div>
          </Reveal>

          <Reveal delay={100}>
            <div className="overflow-hidden rounded-2xl border border-white/10">
              <table className="w-full text-sm">
                <thead className="bg-white/[0.03]">
                  <tr className="text-white/50">
                    <th className="text-left p-5 font-medium">Métrica</th>
                    <th className="text-center p-5 font-medium">Método tradicional</th>
                    <th className="text-center p-5 font-medium bg-[#994B49]/10 text-[#E07A5F]">Con DrON</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {[
                    ['Tiempo de levantamiento', '2-5 días con cuadrilla', '45 min de vuelo'],
                    ['Frecuencia viable', 'Mensual o menos', 'Semanal sin esfuerzo'],
                    ['Precisión volumétrica', '±10-15%', '±1-2%'],
                    ['Entregable', 'Hoja de cálculo', 'Dashboard 3D + reportes PDF'],
                    ['Costo por levantamiento', 'Alto (cuadrilla + topógrafo)', '40-60% menos'],
                    ['Detección de desviaciones', 'Manual, tardía', 'Alertas automáticas en tiempo real'],
                  ].map((row, i) => (
                    <tr key={i} className="text-white/80">
                      <td className="p-5 font-medium">{row[0]}</td>
                      <td className="p-5 text-center text-white/50">{row[1]}</td>
                      <td className="p-5 text-center bg-[#994B49]/[0.04] text-[#E07A5F] font-medium">{row[2]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ============================== PRECIOS ============================== */}
      <section id="precios" className="py-32 px-6 lg:px-10">
        <div className="max-w-7xl mx-auto">
          <Reveal>
            <div className="text-center max-w-3xl mx-auto mb-16">
              <span className="text-xs uppercase tracking-[0.3em] text-[#E07A5F] mb-4 block">— Planes</span>
              <h2 className="text-4xl sm:text-5xl font-bold tracking-tight">
                Tarifas claras. <span className="text-white/40">Sin sorpresas.</span>
              </h2>
              <p className="text-white/50 mt-5">Cotizamos según tamaño de obra y frecuencia. Estos son los rangos de partida.</p>
            </div>
          </Reveal>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                name: 'Esencial',
                price: 'Desde $18,000',
                period: 'MXN / mes',
                desc: 'Para obras pequeñas que necesitan visibilidad básica.',
                features: ['1 vuelo mensual', 'Hasta 10 ha', 'Dashboard básico', 'Reporte PDF mensual', 'Hasta 3 usuarios'],
                cta: 'Cotizar',
                highlight: false,
              },
              {
                name: 'Profesional',
                price: 'Desde $35,000',
                period: 'MXN / mes',
                desc: 'El plan elegido por el 78% de nuestros clientes.',
                features: ['1 vuelo semanal', 'Hasta 30 ha', 'IA conteo + análisis fotos', 'Alertas automáticas', 'Comparación PDF residente', 'Modelos 3D navegables', 'Usuarios ilimitados'],
                cta: 'Empezar',
                highlight: true,
              },
              {
                name: 'Enterprise',
                price: 'A medida',
                period: 'multi-proyecto',
                desc: 'Para desarrolladoras con varios proyectos en paralelo.',
                features: ['Vuelos a demanda', 'Cobertura sin límite', 'Plan IA de maquinaria', 'API + integraciones', 'Soporte dedicado 24/7', 'SLA contractual', 'Onboarding presencial'],
                cta: 'Hablar con ventas',
                highlight: false,
              },
            ].map((p, i) => (
              <Reveal key={i} delay={i * 100}>
                <div
                  className={`relative h-full rounded-2xl p-8 border transition-all duration-500 hover:-translate-y-1 ${
                    p.highlight
                      ? 'bg-gradient-to-b from-[#994B49]/20 to-[#994B49]/5 border-[#994B49]/50 shadow-2xl shadow-[#994B49]/20'
                      : 'bg-white/[0.02] border-white/10 hover:border-white/20'
                  }`}
                >
                  {p.highlight && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[#994B49] text-white text-xs px-3 py-1 rounded-full font-medium">
                      Más popular
                    </div>
                  )}
                  <h3 className="text-xl font-bold">{p.name}</h3>
                  <div className="mt-4 mb-2">
                    <span className="text-3xl font-bold">{p.price}</span>
                  </div>
                  <div className="text-xs text-white/40 uppercase tracking-wider">{p.period}</div>
                  <p className="text-sm text-white/60 mt-5 mb-6 leading-relaxed">{p.desc}</p>
                  <ul className="space-y-3 mb-8">
                    {p.features.map((f, j) => (
                      <li key={j} className="flex items-start gap-2 text-sm text-white/70">
                        <Check className="h-4 w-4 text-[#E07A5F] flex-shrink-0 mt-0.5" />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                  <a
                    href="#contacto"
                    className={`block text-center py-3 rounded-full font-medium transition-all ${
                      p.highlight
                        ? 'bg-[#994B49] hover:bg-[#B35A57] text-white shadow-lg shadow-[#994B49]/30'
                        : 'border border-white/15 hover:bg-white/5'
                    }`}
                    data-testid={`pricing-cta-${i}`}
                  >
                    {p.cta}
                  </a>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ============================== FAQ ============================== */}
      <section id="faq" className="py-32 px-6 lg:px-10">
        <div className="max-w-4xl mx-auto">
          <Reveal>
            <div className="text-center mb-14">
              <span className="text-xs uppercase tracking-[0.3em] text-[#E07A5F] mb-4 block">— Preguntas frecuentes</span>
              <h2 className="text-4xl sm:text-5xl font-bold tracking-tight">¿Aún con dudas?</h2>
            </div>
          </Reveal>

          <div className="space-y-3">
            {[
              { q: '¿Qué tan precisa es la medición con dron?', a: 'Para volumetrías obtenemos precisiones de ±1-2 cm en condiciones normales, gracias a fotogrametría con puntos de control terrestre (GCPs) y procesamiento Pix4D. Para conteo de elementos con IA, la confianza típica es ALTA (>90%) en obras visibles desde el aire.' },
              { q: '¿En qué ciudades operan?', a: 'Base en Guadalajara con cobertura en CDMX, Monterrey, Querétaro, León y Puerto Vallarta. Para obras fuera de estas zonas evaluamos viajes con costo logístico aparte.' },
              { q: '¿Necesito instalar algún software?', a: 'No. Todo corre en tu navegador. Los modelos 3D se ven con Three.js directamente. Sólo necesitas internet y un correo.' },
              { q: '¿Es legal volar drones en mi obra?', a: 'Sí. Operamos bajo la regulación AFAC (antes DGAC) con pilotos certificados y dron registrado. Gestionamos permisos de vuelo en zonas restringidas cuando aplica.' },
              { q: '¿Cómo manejan datos sensibles?', a: 'Tus modelos y reportes están aislados por proyecto y por permiso. Cada cliente sólo ve los proyectos asignados a su cuenta. Hosting cifrado en infraestructura mexicana.' },
              { q: '¿Cuánto tarda en empezar?', a: 'Primera reunión y propuesta en 48 hrs. Primer vuelo de demostración en menos de una semana desde la firma del acuerdo.' },
            ].map((item, i) => (
              <Reveal key={i} delay={i * 60}>
                <details className="group bg-white/[0.02] border border-white/5 rounded-xl overflow-hidden hover:border-white/10 transition-colors">
                  <summary className="flex items-center justify-between p-6 cursor-pointer list-none">
                    <span className="font-medium pr-4">{item.q}</span>
                    <ChevronRight className="h-5 w-5 text-white/40 group-open:rotate-90 transition-transform flex-shrink-0" />
                  </summary>
                  <div className="px-6 pb-6 text-sm text-white/60 leading-relaxed">
                    {item.a}
                  </div>
                </details>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ============================== CONTACTO ============================== */}
      <section id="contacto" className="py-32 px-6 lg:px-10 relative overflow-hidden">
        <div className="absolute inset-0 -z-0">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full bg-[#994B49]/15 blur-[140px]" />
        </div>

        <div className="max-w-5xl mx-auto relative">
          <Reveal>
            <div className="text-center mb-12">
              <h2 className="text-4xl sm:text-6xl font-bold tracking-tight leading-[1.05]">
                Programa tu primer<br />
                <span className="text-[#E07A5F]">vuelo demostrativo.</span>
              </h2>
              <p className="text-white/60 text-lg mt-6">Sin costo. Sin compromiso. Sólo resultados.</p>
            </div>
          </Reveal>

          <Reveal delay={150}>
            <div className="bg-white/[0.03] backdrop-blur-xl border border-white/10 rounded-3xl p-8 sm:p-10 shadow-2xl">
              {sent ? (
                <div className="text-center py-10" data-testid="landing-form-success">
                  <div className="w-16 h-16 rounded-full bg-green-500/20 grid place-items-center mx-auto mb-5">
                    <Check className="h-8 w-8 text-green-400" />
                  </div>
                  <h3 className="text-2xl font-bold mb-2">¡Solicitud recibida!</h3>
                  <p className="text-white/60">Te contactaremos en menos de 24 hrs por correo.</p>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-5" data-testid="landing-contact-form">
                  <div className="grid md:grid-cols-2 gap-5">
                    <div>
                      <label className="text-xs uppercase tracking-widest text-white/40 mb-2 block">Nombre *</label>
                      <input
                        type="text"
                        required
                        value={contact.nombre}
                        onChange={(e) => setContact({ ...contact, nombre: e.target.value })}
                        className="w-full bg-white/5 border border-white/10 focus:border-[#994B49] rounded-lg px-4 py-3 text-white placeholder-white/30 focus:outline-none transition-colors"
                        placeholder="Tu nombre completo"
                        data-testid="contact-nombre"
                      />
                    </div>
                    <div>
                      <label className="text-xs uppercase tracking-widest text-white/40 mb-2 block">Empresa</label>
                      <input
                        type="text"
                        value={contact.empresa}
                        onChange={(e) => setContact({ ...contact, empresa: e.target.value })}
                        className="w-full bg-white/5 border border-white/10 focus:border-[#994B49] rounded-lg px-4 py-3 text-white placeholder-white/30 focus:outline-none transition-colors"
                        placeholder="Constructora ABC"
                        data-testid="contact-empresa"
                      />
                    </div>
                    <div>
                      <label className="text-xs uppercase tracking-widest text-white/40 mb-2 block">Email *</label>
                      <input
                        type="email"
                        required
                        value={contact.email}
                        onChange={(e) => setContact({ ...contact, email: e.target.value })}
                        className="w-full bg-white/5 border border-white/10 focus:border-[#994B49] rounded-lg px-4 py-3 text-white placeholder-white/30 focus:outline-none transition-colors"
                        placeholder="tu@correo.com"
                        data-testid="contact-email"
                      />
                    </div>
                    <div>
                      <label className="text-xs uppercase tracking-widest text-white/40 mb-2 block">Teléfono</label>
                      <input
                        type="tel"
                        value={contact.telefono}
                        onChange={(e) => setContact({ ...contact, telefono: e.target.value })}
                        className="w-full bg-white/5 border border-white/10 focus:border-[#994B49] rounded-lg px-4 py-3 text-white placeholder-white/30 focus:outline-none transition-colors"
                        placeholder="+52 33 1234 5678"
                        data-testid="contact-telefono"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-xs uppercase tracking-widest text-white/40 mb-2 block">Cuéntanos sobre tu obra</label>
                    <textarea
                      rows={3}
                      value={formData.notas}
                      onChange={(e) => setFormData({ ...formData, notas: e.target.value })}
                      className="w-full bg-white/5 border border-white/10 focus:border-[#994B49] rounded-lg px-4 py-3 text-white placeholder-white/30 focus:outline-none transition-colors resize-none"
                      placeholder="Ubicación, tamaño aproximado, tipo de proyecto, frecuencia deseada de vuelos…"
                      data-testid="contact-notas"
                    />
                  </div>

                  {error && (
                    <div className="bg-red-500/10 border border-red-500/30 text-red-300 px-4 py-3 rounded-lg text-sm">
                      {error}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={sending}
                    className="w-full bg-[#994B49] hover:bg-[#B35A57] disabled:opacity-50 px-7 py-4 rounded-full font-medium transition-all shadow-xl shadow-[#994B49]/30 hover:shadow-[#994B49]/50 flex items-center justify-center gap-2"
                    data-testid="contact-submit"
                  >
                    {sending ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Enviando…
                      </>
                    ) : (
                      <>
                        Solicitar vuelo demostrativo gratuito
                        <ArrowRight className="h-4 w-4" />
                      </>
                    )}
                  </button>

                  <p className="text-xs text-white/40 text-center">
                    Al enviar aceptas que te contactemos por correo o teléfono. No spam — solo tu propuesta.
                  </p>
                </form>
              )}
            </div>
          </Reveal>

          <div className="mt-14 grid sm:grid-cols-3 gap-6 text-center">
            <div className="flex flex-col items-center gap-2">
              <Mail className="h-5 w-5 text-[#E07A5F]" />
              <a href="mailto:hola@dron-topografia.com" className="text-sm text-white/70 hover:text-white">hola@dron-topografia.com</a>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Phone className="h-5 w-5 text-[#E07A5F]" />
              <a href="tel:+523312345678" className="text-sm text-white/70 hover:text-white">+52 33 1234 5678</a>
            </div>
            <div className="flex flex-col items-center gap-2">
              <MapPin className="h-5 w-5 text-[#E07A5F]" />
              <span className="text-sm text-white/70">Guadalajara, México</span>
            </div>
          </div>
        </div>
      </section>

      {/* ============================== FOOTER ============================== */}
      <footer className="border-t border-white/5 py-12 px-6 lg:px-10">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <img
              src="/logo-dron-dark.png"
              alt="DrON Topografía"
              className="h-12 w-auto opacity-80"
              style={{ filter: 'brightness(0) invert(1)' }}
            />
            <span className="text-white/30 text-xs ml-2">© 2026</span>
          </div>
          <div className="flex items-center gap-6 text-xs text-white/40">
            <a href="#servicios" className="hover:text-white">Servicios</a>
            <a href="#precios" className="hover:text-white">Precios</a>
            <a href="#faq" className="hover:text-white">FAQ</a>
            <Link to="/app" className="hover:text-white">Iniciar sesión</Link>
            <span className="flex items-center gap-1.5"><ShieldCheck className="h-3 w-3" /> Datos protegidos</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
