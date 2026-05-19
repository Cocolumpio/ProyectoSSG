"""
DEM Volumetry Service — DrON Topografía

Calcula el volumen retirado/rellenado entre dos modelos digitales de elevación
(DEM) en formato GeoTIFF, generando un mapa de calor del cambio y opcionalmente
una interpretación con IA Gemini.

Técnica: rasterización + diferencial de superficie estándar (Pix4D, CloudCompare).
- Reproyecta ambos rasters a una grilla común
- Calcula delta_Z = Z_actual - Z_anterior por pixel
- Volumen_retirado = sum(|delta_Z[delta_Z<0]|) * area_pixel
- Volumen_rellenado = sum(delta_Z[delta_Z>0]) * area_pixel
"""
import io
import logging
import os
import tempfile
from typing import Optional

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.io import MemoryFile
import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
from matplotlib import cm

logger = logging.getLogger(__name__)


def _read_dem_to_array(tif_bytes: bytes, max_pixels: int = 30_000_000):
    """Lee un GeoTIFF en bytes y devuelve (array, transform, crs, nodata, bounds, res).
    
    Si el raster tiene más de max_pixels (~30M, ≈ 240MB en float32), aplica
    decimación en lectura (overview) para evitar OOM en rasters enormes.
    """
    with MemoryFile(tif_bytes) as memfile:
        with memfile.open() as src:
            total_px = src.width * src.height
            decimate = 1
            if total_px > max_pixels:
                decimate = int(np.ceil(np.sqrt(total_px / max_pixels)))
                logger.warning(
                    f"DEM grande ({src.width}x{src.height}={total_px:,} px). "
                    f"Decimando 1/{decimate} para evitar OOM."
                )
            new_w = src.width // decimate
            new_h = src.height // decimate
            arr = src.read(
                1,
                out_shape=(new_h, new_w),
                resampling=Resampling.average,
            ).astype(np.float32)
            # Ajustar transform por la decimación
            new_transform = src.transform * src.transform.scale(decimate, decimate)
            return arr, new_transform, src.crs, src.nodata, src.bounds, src.res


def _reproject_to_match(src_bytes: bytes, ref_transform, ref_crs, ref_width, ref_height, max_pixels: int = 30_000_000):
    """Reproyecta el DEM src a la grilla del DEM de referencia."""
    with MemoryFile(src_bytes) as memfile:
        with memfile.open() as src:
            # Si el source es enorme, leerlo decimado primero
            total_px = src.width * src.height
            decimate = 1
            if total_px > max_pixels:
                decimate = int(np.ceil(np.sqrt(total_px / max_pixels)))
            new_w = src.width // decimate
            new_h = src.height // decimate
            src_arr = src.read(
                1,
                out_shape=(new_h, new_w),
                resampling=Resampling.average,
            ).astype(np.float32)
            src_transform = src.transform * src.transform.scale(decimate, decimate)
            
            destination = np.full((ref_height, ref_width), np.nan, dtype=np.float32)
            reproject(
                source=src_arr,
                destination=destination,
                src_transform=src_transform,
                src_crs=src.crs,
                dst_transform=ref_transform,
                dst_crs=ref_crs,
                resampling=Resampling.bilinear,
                src_nodata=src.nodata,
                dst_nodata=np.nan,
            )
            return destination


def calcular_volumetria_dem(
    dem_anterior_bytes: bytes,
    dem_actual_bytes: bytes,
    threshold_m: float = 0.05,
):
    """
    Calcula volumetría diferencial entre dos DEMs.

    Args:
        dem_anterior_bytes: GeoTIFF de la semana anterior (o terreno original).
        dem_actual_bytes: GeoTIFF de la semana actual.
        threshold_m: ignorar cambios menores a este valor (ruido sensor).

    Returns:
        dict con: volumen_retirado, volumen_rellenado, volumen_neto, area_analizada,
                  resolution, heatmap_png (bytes), bounds, crs, stats
    """
    # ---- Leer DEM actual como referencia (define la grilla común) ----
    logger.info(f"Leyendo DEM actual ({len(dem_actual_bytes):,} bytes)…")
    z_ref, transform, crs, nodata, bounds, res = _read_dem_to_array(dem_actual_bytes)
    height, width = z_ref.shape
    logger.info(f"DEM actual: {width}x{height} px, CRS={crs}")
    if nodata is not None:
        z_ref = np.where(z_ref == nodata, np.nan, z_ref)

    # ---- Reproyectar DEM anterior a la misma grilla ----
    logger.info(f"Reproyectando DEM anterior ({len(dem_anterior_bytes):,} bytes)…")
    z_prev = _reproject_to_match(dem_anterior_bytes, transform, crs, width, height)

    # ---- Calcular diferencial ----
    diff = z_ref - z_prev  # positivo = relleno, negativo = retiro
    mask_valid = ~np.isnan(diff)
    
    # Liberar memoria temprano
    del z_ref, z_prev
    
    # Filtrar ruido
    diff_clean = np.where(np.abs(diff) < threshold_m, 0, diff).astype(np.float32)
    del diff

    # Tamaño de pixel en metros (asume CRS proyectado; si es geográfico, aproximamos)
    px_size_x = abs(transform.a)
    px_size_y = abs(transform.e)
    
    # Si el CRS es geográfico (lat/lon en grados), convertir a metros aprox
    is_geographic = crs is not None and crs.is_geographic
    if is_geographic:
        lat_center = (bounds.top + bounds.bottom) / 2
        m_per_deg_lat = 110540
        m_per_deg_lon = 111320 * np.cos(np.radians(lat_center))
        px_size_x = px_size_x * m_per_deg_lon
        px_size_y = px_size_y * m_per_deg_lat
    
    area_pixel = px_size_x * px_size_y  # m²
    logger.info(f"Pixel area: {area_pixel:.4f} m², total grid: {width}x{height}")

    # ---- Cálculo de volúmenes ----
    retiro_mask = (diff_clean < 0) & mask_valid
    relleno_mask = (diff_clean > 0) & mask_valid
    
    volumen_retirado = float(np.abs(diff_clean[retiro_mask]).sum() * area_pixel)
    volumen_rellenado = float(diff_clean[relleno_mask].sum() * area_pixel)
    volumen_neto = volumen_rellenado - volumen_retirado  # neto: positivo = ganancia
    area_analizada = float(mask_valid.sum() * area_pixel)
    area_con_cambio = float((retiro_mask | relleno_mask).sum() * area_pixel)

    stats = {
        "diff_max": float(np.nanmax(diff_clean)) if mask_valid.any() else 0.0,
        "diff_min": float(np.nanmin(diff_clean)) if mask_valid.any() else 0.0,
        "diff_mean": float(np.nanmean(diff_clean[mask_valid])) if mask_valid.any() else 0.0,
        "diff_std": float(np.nanstd(diff_clean[mask_valid])) if mask_valid.any() else 0.0,
        "pixel_size_m": float(np.sqrt(area_pixel)),
        "total_pixels": int(mask_valid.sum()),
    }

    # ---- Generar mapa de calor PNG ----
    heatmap_png = _generar_heatmap(diff_clean, mask_valid, bounds)

    return {
        "volumen_retirado_m3": round(volumen_retirado, 2),
        "volumen_rellenado_m3": round(volumen_rellenado, 2),
        "volumen_neto_m3": round(volumen_neto, 2),
        "area_analizada_m2": round(area_analizada, 2),
        "area_con_cambio_m2": round(area_con_cambio, 2),
        "resolution_m": round(stats["pixel_size_m"], 3),
        "crs": str(crs) if crs else "desconocido",
        "is_geographic": is_geographic,
        "bounds": {
            "left": float(bounds.left),
            "bottom": float(bounds.bottom),
            "right": float(bounds.right),
            "top": float(bounds.top),
        },
        "stats": stats,
        "heatmap_png": heatmap_png,
    }


def _generar_heatmap(diff: np.ndarray, mask: np.ndarray, bounds) -> bytes:
    """Genera un mapa de calor PNG: rojo=retiro, blanco=sin cambio, azul=relleno."""
    fig, ax = plt.subplots(figsize=(10, 8), facecolor="#0B0B0F")
    ax.set_facecolor("#0B0B0F")
    
    # Color limits simétricos para que rojo y azul tengan la misma escala
    diff_display = np.where(mask, diff, np.nan)
    valid = diff[mask]
    if len(valid) > 0:
        vmax = float(np.percentile(np.abs(valid), 98))
        vmax = max(vmax, 0.1)
    else:
        vmax = 1.0
    
    # Custom colormap: rojo (retiro) → blanco (sin cambio) → azul (relleno)
    cmap = plt.get_cmap("RdBu")  # Red-White-Blue
    
    extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
    im = ax.imshow(diff_display, cmap=cmap, vmin=-vmax, vmax=vmax,
                   extent=extent, origin="upper", interpolation="bilinear")
    
    # Colorbar
    cbar = plt.colorbar(im, ax=ax, label="Δ altura (m)", shrink=0.8)
    cbar.ax.yaxis.label.set_color("white")
    cbar.ax.tick_params(colors="white")
    
    ax.set_title("Diferencial Volumétrico\n(rojo = retiro, azul = relleno)",
                 color="white", fontsize=14, pad=15)
    ax.tick_params(colors="white", labelsize=8)
    for spine in ax.spines.values():
        spine.set_color("white")
        spine.set_alpha(0.3)
    
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor="#0B0B0F", edgecolor="none")
    plt.close(fig)
    return buf.getvalue()


def extraer_metadata_dem(tif_bytes: bytes) -> dict:
    """Extrae metadata básica de un TIFF sin procesarlo completamente."""
    try:
        with MemoryFile(tif_bytes) as memfile:
            with memfile.open() as src:
                return {
                    "width": src.width,
                    "height": src.height,
                    "crs": str(src.crs) if src.crs else None,
                    "is_geographic": src.crs.is_geographic if src.crs else None,
                    "resolution_x": abs(src.transform.a),
                    "resolution_y": abs(src.transform.e),
                    "bounds": {
                        "left": float(src.bounds.left),
                        "bottom": float(src.bounds.bottom),
                        "right": float(src.bounds.right),
                        "top": float(src.bounds.top),
                    },
                    "bands": src.count,
                    "dtype": str(src.dtypes[0]) if src.dtypes else None,
                    "nodata": float(src.nodata) if src.nodata is not None else None,
                }
    except Exception as e:
        logger.error(f"Error extrayendo metadata DEM: {e}")
        return {"error": str(e)}


async def interpretar_volumetria_con_ia(resultado: dict, contexto: Optional[dict] = None) -> str:
    """
    Genera una interpretación en español del resultado volumétrico usando Gemini.
    contexto: opcional, puede incluir nombre del proyecto, semana actual/anterior, plan, etc.
    """
    from core.config import EMERGENT_LLM_KEY
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import uuid

    ctx_str = ""
    if contexto:
        partes = []
        if contexto.get("proyecto_nombre"):
            partes.append(f"Proyecto: {contexto['proyecto_nombre']}")
        if contexto.get("semana_actual"):
            partes.append(f"Semana actual: {contexto['semana_actual']}")
        if contexto.get("semana_anterior"):
            partes.append(f"Semana anterior comparada: {contexto['semana_anterior']}")
        if contexto.get("volumen_planeado_total"):
            partes.append(f"Volumen total planeado del proyecto: {contexto['volumen_planeado_total']:,} m³")
        if contexto.get("volumen_acumulado_real"):
            partes.append(f"Volumen acumulado real hasta ahora: {contexto['volumen_acumulado_real']:,} m³")
        ctx_str = "\n".join(partes) + "\n\n"

    prompt = f"""{ctx_str}Resultados del cálculo volumétrico DEM-vs-DEM:
- Volumen retirado (excavado): {resultado['volumen_retirado_m3']:,} m³
- Volumen rellenado (depositado): {resultado['volumen_rellenado_m3']:,} m³
- Volumen neto: {resultado['volumen_neto_m3']:,} m³
- Área analizada: {resultado['area_analizada_m2']:,} m²
- Área con cambio detectado: {resultado['area_con_cambio_m2']:,} m²
- Resolución del DEM: {resultado['resolution_m']} m/pixel
- Cambio máximo en altura: {resultado['stats']['diff_max']:.2f} m (relleno) / {resultado['stats']['diff_min']:.2f} m (retiro)
- Cambio promedio: {resultado['stats']['diff_mean']:.3f} m

Escribe un análisis ejecutivo en español mexicano (máximo 4 párrafos cortos) interpretando estos resultados para un director de obra. Incluye:
1. Resumen del trabajo realizado en este periodo.
2. Si el ritmo es adecuado, lento, o acelerado (basándote en el contexto si lo hay).
3. Cualquier observación técnica relevante (calidad del DEM, posibles outliers, áreas de atención).
4. Una recomendación clara para la siguiente semana.

NO uses bullets ni listas. Escribe en prosa fluida, profesional, sin tecnicismos innecesarios."""

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"dem-vol-{uuid.uuid4().hex[:8]}",
            system_message="Eres un experto en topografía y gestión de obras de construcción en México. Hablas con autoridad técnica pero de forma accesible para directores y residentes de obra."
        ).with_model("gemini", "gemini-2.5-flash")
        
        response = await chat.send_message(UserMessage(text=prompt))
        return response.strip()
    except Exception as e:
        logger.error(f"Error generando interpretación IA: {e}")
        return f"No se pudo generar la interpretación automática: {str(e)}. Los datos numéricos están disponibles arriba."
