"""Renderiza nubes de puntos PLY a imágenes (planta + isométricas) para reportes PDF"""
import io
import os
import logging
import tempfile
import numpy as np

logger = logging.getLogger(__name__)

MAX_RENDER_POINTS = 300000

# (titulo, elevación, azimut)
VISTAS = [
    ("Vista Superior (Planta)", 90, -90),
    ("Vista Isométrica Noreste", 32, 45),
    ("Vista Isométrica Suroeste", 32, 225),
]


def _cargar_nube(ply_bytes: bytes):
    """Carga puntos y colores desde bytes PLY.

    Intenta primero con open3d (rápido, maneja binary y ascii); si falla,
    hace fallback a plyfile (más tolerante con headers no estándar).
    """
    with tempfile.NamedTemporaryFile(suffix='.ply', delete=False) as tmp:
        tmp.write(ply_bytes)
        tmp_path = tmp.name
    try:
        # Intento 1: open3d
        try:
            import open3d as o3d
            pcd = o3d.io.read_point_cloud(tmp_path)
            n = len(pcd.points)
            if n > 0:
                if n > MAX_RENDER_POINTS:
                    pcd = pcd.uniform_down_sample(every_k_points=max(1, n // MAX_RENDER_POINTS))
                pts = np.asarray(pcd.points, dtype=np.float64)
                cols = np.asarray(pcd.colors, dtype=np.float64) if pcd.has_colors() else None
                logger.info(f"[ply_render] open3d cargó {n:,} puntos")
                return pts, cols
            logger.warning("[ply_render] open3d devolvió 0 puntos, intentando fallback plyfile")
        except Exception as e:
            logger.warning(f"[ply_render] open3d falló: {e}. Intentando fallback con plyfile")

        # Intento 2: plyfile (fallback)
        try:
            from plyfile import PlyData
            plydata = PlyData.read(tmp_path)
            vertex = plydata['vertex']
            pts = np.stack([vertex['x'], vertex['y'], vertex['z']], axis=1).astype(np.float64)
            n = len(pts)
            if n == 0:
                return None, None
            cols = None
            names = set(vertex.data.dtype.names or [])
            if {'red', 'green', 'blue'}.issubset(names):
                r = np.asarray(vertex['red'], dtype=np.float64) / 255.0
                g = np.asarray(vertex['green'], dtype=np.float64) / 255.0
                b = np.asarray(vertex['blue'], dtype=np.float64) / 255.0
                cols = np.stack([r, g, b], axis=1)
            if n > MAX_RENDER_POINTS:
                step = max(1, n // MAX_RENDER_POINTS)
                pts = pts[::step]
                if cols is not None:
                    cols = cols[::step]
            logger.info(f"[ply_render] plyfile cargó {len(pts):,} puntos")
            return pts, cols
        except Exception as e:
            logger.error(f"[ply_render] plyfile también falló: {e}")
            return None, None
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _recortar_blanco(buf: io.BytesIO) -> io.BytesIO:
    """Recorta los bordes blancos de la imagen para maximizar nitidez en el PDF."""
    from PIL import Image, ImageChops
    im = Image.open(buf).convert('RGB')
    bg = Image.new('RGB', im.size, (255, 255, 255))
    bbox = ImageChops.difference(im, bg).getbbox()
    if bbox:
        pad = 12
        im = im.crop((
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(im.size[0], bbox[2] + pad),
            min(im.size[1], bbox[3] + pad),
        ))
    out = io.BytesIO()
    im.save(out, format='PNG')
    out.seek(0)
    return out


def render_vistas_ply(ply_bytes: bytes, dpi: int = 180):
    """
    Renderiza 3 vistas de la nube de puntos: planta + 2 isométricas.
    Returns: lista de (titulo, BytesIO con PNG)
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    pts, cols = _cargar_nube(ply_bytes)
    if pts is None:
        return []

    centro = (pts.min(axis=0) + pts.max(axis=0)) / 2
    pts = pts - centro
    rangos = pts.max(axis=0) - pts.min(axis=0)
    rangos[rangos == 0] = 1.0

    n = len(pts)
    tam_punto = float(np.clip(600000.0 / n, 0.5, 4.0))

    if cols is not None:
        c = np.clip(cols, 0, 1)
        cmap = None
    else:
        c = pts[:, 2]  # colorear por elevación
        cmap = 'terrain'

    imagenes = []
    for titulo, elev, azim in VISTAS:
        fig = plt.figure(figsize=(9, 6.5), dpi=dpi, facecolor='white')
        ax = fig.add_subplot(111, projection='3d')
        ax.set_facecolor('white')
        ax.scatter(
            pts[:, 0], pts[:, 1], pts[:, 2],
            c=c, cmap=cmap, s=tam_punto,
            alpha=1.0, linewidths=0, depthshade=False, rasterized=True,
        )
        ax.view_init(elev=elev, azim=azim)
        ax.set_box_aspect((rangos[0], rangos[1], max(rangos[2], float(rangos[:2].max()) * 0.15)))
        ax.set_xlim(pts[:, 0].min(), pts[:, 0].max())
        ax.set_ylim(pts[:, 1].min(), pts[:, 1].max())
        ax.set_zlim(pts[:, 2].min(), pts[:, 2].max())
        ax.set_axis_off()
        ax.set_position([-0.12, -0.12, 1.24, 1.24])

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, facecolor='white', bbox_inches='tight', pad_inches=0.02)
        plt.close(fig)
        buf.seek(0)
        imagenes.append((titulo, _recortar_blanco(buf)))
        logger.info(f"Vista 3D renderizada: {titulo} ({n:,} puntos)")

    return imagenes
