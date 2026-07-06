"""Rutas de Reporte Ejecutivo PDF - DrON Topografía"""
import os
import io
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.enums import TA_CENTER

from core.config import get_db
from services import avance_financiero as af_service
from services.helpers import obtener_metricas_proyecto

db = get_db()
router = APIRouter(prefix="/api")


async def _obtener_bytes_modelo(avance: dict):
    """Obtiene los bytes del PLY del avance: prefiere la versión preview de GridFS, luego el original, luego disco local.

    Intentamos siempre: si el preview no existe, se descarga el original (aunque pese >300MB) porque
    el renderizado sub-muestrea la nube antes de dibujar.
    """
    from services.storage import get_storage
    storage = get_storage(db)
    size_mb = avance.get("modelo_3d_size_mb") or 0
    logging.info(
        f"[reporte-pdf] Intentando obtener modelo 3D: semana={avance.get('semana')} "
        f"size_mb={size_mb} preview_id={avance.get('modelo_3d_preview_id')} "
        f"gridfs_id={avance.get('modelo_3d_gridfs_id')}"
    )
    for key in ("modelo_3d_preview_id", "modelo_3d_gridfs_id"):
        fid = avance.get(key)
        if not fid:
            continue
        try:
            content, _ = await storage.get_file(fid)
            if content:
                logging.info(f"[reporte-pdf] Modelo obtenido de {key}={fid} ({len(content):,} bytes)")
                return content
            logging.warning(f"[reporte-pdf] Storage devolvió vacío para {key}={fid}")
        except Exception as e:
            logging.warning(f"[reporte-pdf] Error leyendo modelo de GridFS {key}={fid}: {e}")
    # Modelos antiguos guardados en disco local
    url = avance.get("modelo_3d_url") or ""
    if url.startswith("/api/modelos3d/") and "/gridfs/" not in url:
        from core.config import UPLOAD_DIR
        path = UPLOAD_DIR / "modelos3d" / url.replace("/api/modelos3d/", "")
        if path.exists():
            logging.info(f"[reporte-pdf] Modelo obtenido de disco local: {path}")
            return path.read_bytes()
    logging.warning(f"[reporte-pdf] No se pudo obtener modelo 3D para semana {avance.get('semana')}")
    return None


def _imagen_pdf(buf: io.BytesIO, width: float) -> RLImage:
    """Crea una RLImage con altura proporcional al PNG (sin distorsión)."""
    from PIL import Image as PILImage
    im = PILImage.open(buf)
    w, h = im.size
    buf.seek(0)
    return RLImage(buf, width=width, height=width * h / w)


def _texto_wa_pdf(texto: str) -> str:
    """Convierte el texto del resumen de WhatsApp a formato seguro para reportlab."""
    import re
    t = (texto or "").split("📋 Diagnóstico Green API")[0].strip()
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*([^*\n]+)\*", r"<b>\1</b>", t)
    t = re.sub(r"_([^_\n]+)_", r"<i>\1</i>", t)
    return t.replace("\n", "<br/>")

# --- Reporte Ejecutivo PDF ---
@router.get("/proyectos/{proyecto_id}/reporte-ejecutivo")
async def generar_reporte_ejecutivo(proyecto_id: str):
    """
    Genera un reporte ejecutivo en PDF para un proyecto.
    Usa la configuración de flotilla guardada en el proyecto.
    
    Returns:
        PDF con el reporte ejecutivo
    """
    # Obtener datos del proyecto
    proyecto = await db.proyectos.find_one({"id": proyecto_id}, {"_id": 0})
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Obtener configuración de flotilla del proyecto
    capacidad_camion = proyecto.get('capacidad_camion', 25.0) or 25.0
    costo_por_m3 = proyecto.get('costo_m3', 150.0) or 150.0
    
    # Obtener avances semanales
    avances = await db.avances_semanales.find(
        {"proyecto_id": proyecto_id}, 
        {"_id": 0}
    ).sort("semana", 1).to_list(100)
    
    # Calcular totales
    volumen_total = sum(a.get('volumen_excavacion', 0) or 0 for a in avances)
    total_viajes = int(volumen_total / capacidad_camion) if capacidad_camion > 0 else 0
    costo_total_estimado = volumen_total * costo_por_m3  # Cálculo basado en m³
    
    # Crear PDF en memoria
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo personalizado para título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#994B49'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#666666'),
        spaceAfter=15,
        alignment=TA_CENTER
    )
    
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#994B49'),
        spaceBefore=20,
        spaceAfter=10
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=8
    )
    
    # Contenido del PDF
    story = []

    # --- LOGO DE CONSTRUCTORA (si el proyecto tiene una asignada) ---
    constructora = None
    constructora_id = proyecto.get("constructora_id")
    if constructora_id:
        try:
            constructora = await db.constructoras.find_one({"id": constructora_id}, {"_id": 0})
        except Exception as e:
            logging.warning(f"[reporte-pdf] Error leyendo constructora {constructora_id}: {e}")

    if constructora and constructora.get("logo_gridfs_id"):
        try:
            from services.storage import get_storage
            storage = get_storage(db)
            logo_bytes, _meta = await storage.get_file(constructora["logo_gridfs_id"])
            if logo_bytes:
                from PIL import Image as PILImage
                logo_buf = io.BytesIO(logo_bytes)
                # Convertir SVG u otros formatos no soportados por ReportLab a PNG
                try:
                    pil_img = PILImage.open(logo_buf)
                    if pil_img.mode not in ("RGB", "RGBA"):
                        pil_img = pil_img.convert("RGBA")
                    logo_out = io.BytesIO()
                    pil_img.save(logo_out, format="PNG")
                    logo_out.seek(0)
                    w, h = pil_img.size
                    max_w = 140
                    max_h = 60
                    ratio = min(max_w / w, max_h / h)
                    story.append(RLImage(logo_out, width=w * ratio, height=h * ratio))
                    nombre_c = constructora.get("nombre", "")
                    if nombre_c:
                        story.append(Paragraph(
                            f"<i>Cliente: {nombre_c}</i>",
                            ParagraphStyle(
                                'ClienteHeader',
                                parent=styles['Normal'],
                                fontSize=9,
                                textColor=colors.HexColor('#64748B'),
                                alignment=TA_CENTER,
                                spaceAfter=4,
                            ),
                        ))
                    story.append(Spacer(1, 10))
                except Exception as e:
                    logging.warning(f"[reporte-pdf] No se pudo procesar logo constructora: {e}")
        except Exception as e:
            logging.warning(f"[reporte-pdf] Error insertando logo constructora: {e}")

    # --- ENCABEZADO ---
    story.append(Paragraph("REPORTE EJECUTIVO", title_style))
    story.append(Paragraph("Gestión de Construcción con Drones", subtitle_style))
    story.append(Spacer(1, 20))
    
    # --- INFORMACIÓN DEL PROYECTO ---
    story.append(Paragraph("📋 INFORMACIÓN DEL PROYECTO", section_style))
    
    proyecto_info = [
        ["Nombre del Proyecto:", proyecto.get('nombre', 'N/A')],
    ]
    if constructora and constructora.get("nombre"):
        proyecto_info.append(["Constructora / Cliente:", constructora["nombre"]])
    proyecto_info.extend([
        ["Ubicación:", proyecto.get('ubicacion', 'N/A')],
        ["Coordenadas:", f"Lat: {proyecto.get('coordenadas', {}).get('lat', 'N/A')}, Lng: {proyecto.get('coordenadas', {}).get('lng', 'N/A')}"],
        ["Fecha de Inicio:", proyecto.get('fecha_inicio', 'N/A')],
        ["Fecha Fin Planeada:", proyecto.get('fecha_fin_planeada', 'N/A')],
        ["Descripción:", proyecto.get('descripcion', 'Sin descripción')[:100] + '...' if proyecto.get('descripcion') and len(proyecto.get('descripcion', '')) > 100 else proyecto.get('descripcion', 'Sin descripción')],
    ])
    
    info_table = Table(proyecto_info, colWidths=[150, 350])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#994B49')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # --- AVANCE DE OBRA ---
    story.append(Paragraph("📊 AVANCE DE OBRA", section_style))
    
    avance_actual = proyecto.get('avance_actual', 0)
    avance_color = colors.HexColor('#10B981') if avance_actual >= 75 else colors.HexColor('#F59E0B') if avance_actual >= 50 else colors.HexColor('#EF4444')
    
    avance_data = [
        ["Avance Actual:", f"{avance_actual}%"],
        ["Estado:", "En Progreso" if avance_actual < 100 else "Completado"],
        ["Semanas Registradas:", str(len(avances))],
    ]
    
    avance_table = Table(avance_data, colWidths=[150, 350])
    avance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#994B49')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (1, 0), 14),
        ('TEXTCOLOR', (1, 0), (1, 0), avance_color),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(avance_table)
    story.append(Spacer(1, 20))
    
    # --- MODELO 3D DEL SITIO (planta + 2 isométricas) ---
    # Tomamos todos los avances con modelo, de más reciente a más antiguo,
    # y usamos el primero que se pueda renderizar correctamente.
    candidatos_modelo = [
        a for a in reversed(avances)
        if a.get("modelo_3d_gridfs_id") or a.get("modelo_3d_preview_id") or a.get("modelo_3d_url")
    ]
    vistas = []
    avance_modelo = None
    intentos_fallidos = []
    if candidatos_modelo:
        from services.ply_render import render_vistas_ply
        loop = asyncio.get_event_loop()
        for cand in candidatos_modelo:
            try:
                ply_bytes = await _obtener_bytes_modelo(cand)
                if not ply_bytes:
                    intentos_fallidos.append(f"Semana {cand.get('semana', '?')}: sin bytes disponibles")
                    continue
                vistas_cand = await loop.run_in_executor(None, render_vistas_ply, ply_bytes)
                if vistas_cand:
                    vistas = vistas_cand
                    avance_modelo = cand
                    break
                intentos_fallidos.append(f"Semana {cand.get('semana', '?')}: render vacío")
            except Exception as e:
                logging.error(
                    f"[reporte-pdf] Error renderizando modelo de semana {cand.get('semana', '?')}: {e}"
                )
                intentos_fallidos.append(f"Semana {cand.get('semana', '?')}: {e}")

    if vistas and avance_modelo:
        story.append(Paragraph("🛰️ MODELO 3D DEL SITIO (LEVANTAMIENTO CON DRON)", section_style))
        puntos = avance_modelo.get("modelo_3d_points") or 0
        detalle = f"Levantamiento más reciente: Semana {avance_modelo.get('semana', '?')} ({avance_modelo.get('fecha', 'N/D')})"
        if puntos:
            detalle += f" · {puntos:,} puntos"
        story.append(Paragraph(detalle, normal_style))
        story.append(Spacer(1, 6))

        caption_style = ParagraphStyle(
            'Caption3D',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#64748B'),
            alignment=TA_CENTER,
            spaceAfter=4,
        )
        titulo_top, buf_top = vistas[0]
        story.append(_imagen_pdf(buf_top, width=460))
        story.append(Paragraph(titulo_top, caption_style))
        story.append(Spacer(1, 10))
        if len(vistas) >= 3:
            (t1, b1), (t2, b2) = vistas[1], vistas[2]
            iso_table = Table(
                [
                    [_imagen_pdf(b1, width=235), _imagen_pdf(b2, width=235)],
                    [Paragraph(t1, caption_style), Paragraph(t2, caption_style)],
                ],
                colWidths=[245, 245],
            )
            iso_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(iso_table)
        story.append(Spacer(1, 20))
    elif candidatos_modelo:
        # Hay modelos registrados pero ninguno pudo renderizarse: dejamos evidencia en el reporte
        story.append(Paragraph("🛰️ MODELO 3D DEL SITIO (LEVANTAMIENTO CON DRON)", section_style))
        detalle_fallo = (
            "No se pudo generar la imagen del modelo 3D en este reporte. "
            f"Se intentaron {len(candidatos_modelo)} levantamiento(s) sin éxito."
        )
        story.append(Paragraph(detalle_fallo, normal_style))
        if intentos_fallidos:
            story.append(Paragraph(
                "<i>Detalle técnico: " + "; ".join(intentos_fallidos[:3]) + "</i>",
                normal_style,
            ))
        story.append(Spacer(1, 12))
    
    # --- VOLUMETRÍA POR SEMANA ---
    story.append(Paragraph("🚛 VOLUMETRÍA DE EXCAVACIÓN POR SEMANA", section_style))
    
    if avances:
        # Tabla de volúmenes por semana
        vol_headers = ["Semana", "Fecha", "Volumen (m³)", "Viajes Estimados", "Avance (%)"]
        vol_data = [vol_headers]
        
        for avance in avances:
            volumen = avance.get('volumen_excavacion', 0) or 0
            viajes = int(volumen / capacidad_camion) if capacidad_camion > 0 else 0
            porcentaje = avance.get('porcentaje_avance', 0) or 0
            vol_data.append([
                f"Semana {avance.get('semana', '?')}",
                avance.get('fecha', 'N/A'),
                f"{volumen:,.1f}",
                str(viajes),
                f"{porcentaje}%"
            ])
        
        # Fila de totales
        vol_data.append([
            "TOTAL",
            "-",
            f"{volumen_total:,.1f}",
            str(total_viajes),
            f"{avance_actual}%"
        ])
        
        vol_table = Table(vol_data, colWidths=[80, 90, 100, 110, 80])
        vol_table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#994B49')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            # Body
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F8F9FA')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#994B49')),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(vol_table)
    else:
        story.append(Paragraph("No hay datos de volumetría registrados.", normal_style))
    
    story.append(Spacer(1, 20))
    
    # --- AVANCE SEMANAL POR CONCEPTO: PROGRAMA vs EJECUTADO ---
    programa = proyecto.get("programa_semanal") or []
    plan_por_semana = {int(s.get("semana") or 0): s for s in programa}
    avances_por_semana = {int(a.get("semana") or 0): a for a in avances}
    conceptos_def = [
        ("Excavación", "excavacion_m3", "volumen_excavacion", "m³", "#D97706"),
        ("Pilas de Cimentación", "pilas", "pilas_completadas", "pzs", "#2563EB"),
        ("Anclas", "anclas", "anclas_instaladas", "pzs", "#0D9488"),
        ("Muros", "muros_m2", "muros_completados", "m²", "#9333EA"),
        ("Reforzamiento por Perfiles", "perfiles", "perfiles_completados", "pzs", "#059669"),
    ]

    tablas_conceptos = []
    for nombre, key_plan, key_real, unidad, color_hex in conceptos_def:
        semanas_con_dato = sorted(
            {w for w, s in plan_por_semana.items() if float(s.get(key_plan) or 0) > 0}
            | {w for w, a in avances_por_semana.items() if float(a.get(key_real) or 0) > 0}
        )
        if not semanas_con_dato:
            continue

        filas = [["Semana", "Periodo", f"Esperado ({unidad})", f"Ejecutado ({unidad})", "% Semana", "Acum. Esp.", "Acum. Ejec."]]
        acum_plan = 0.0
        acum_real = 0.0
        for w in semanas_con_dato:
            sem_plan = plan_por_semana.get(w) or {}
            sem_real = avances_por_semana.get(w) or {}
            plan_v = float(sem_plan.get(key_plan) or 0)
            real_v = float(sem_real.get(key_real) or 0)
            acum_plan += plan_v
            acum_real += real_v
            periodo = sem_plan.get("fecha_inicio") or sem_real.get("fecha") or "—"
            if plan_v > 0:
                pct_txt = f"{(real_v / plan_v * 100):.0f}%"
            elif real_v > 0:
                pct_txt = "Fuera de programa"
            else:
                pct_txt = "—"
            filas.append([
                f"Sem {w}",
                str(periodo),
                f"{plan_v:,.1f}" if plan_v else "—",
                f"{real_v:,.1f}" if real_v else "0",
                pct_txt,
                f"{acum_plan:,.1f}",
                f"{acum_real:,.1f}",
            ])
        pct_total = (acum_real / acum_plan * 100) if acum_plan > 0 else 0
        filas.append([
            "TOTAL", "—",
            f"{acum_plan:,.1f}",
            f"{acum_real:,.1f}",
            f"{pct_total:.1f}%" if acum_plan > 0 else "—",
            f"{acum_plan:,.1f}",
            f"{acum_real:,.1f}",
        ])
        tablas_conceptos.append((nombre, color_hex, filas))

    if tablas_conceptos:
        story.append(Paragraph("📈 AVANCE SEMANAL POR CONCEPTO: ESPERADO vs EJECUTADO", section_style))
        story.append(Paragraph(
            "Para cada concepto se compara lo esperado según el programa de obra de cada semana contra lo "
            "realmente ejecutado (medido por dron), y al final el acumulado esperado vs el acumulado ejecutado.",
            normal_style
        ))
        story.append(Spacer(1, 6))
        concepto_style = ParagraphStyle(
            'ConceptoTitle',
            parent=styles['Heading3'],
            fontSize=11,
            textColor=colors.HexColor('#334155'),
            spaceBefore=10,
            spaceAfter=6,
        )
        for nombre, color_hex, filas in tablas_conceptos:
            story.append(Paragraph(nombre, concepto_style))
            tabla = Table(filas, colWidths=[48, 88, 82, 82, 74, 68, 68])
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(color_hex)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F1F5F9')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor(color_hex)),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#FAFAFA')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(tabla)
            story.append(Spacer(1, 8))
        story.append(Spacer(1, 12))
    
    # --- RESUMEN PARA LOGÍSTICA DE TRANSPORTE ---
    story.append(Paragraph("🚚 RESUMEN PARA LOGÍSTICA DE TRANSPORTE", section_style))
    
    # Los valores vienen del proyecto (ya calculados arriba)
    logistica_data = [
        ["Capacidad por Camión:", f"{capacidad_camion:,.1f} m³"],
        ["Volumen Total Excavado:", f"{volumen_total:,.1f} m³"],
        ["Total de Viajes Requeridos:", f"{total_viajes:,} viajes"],
        ["Costo por m³:", f"${costo_por_m3:,.2f} MXN"],
        ["Costo Total Estimado:", f"${costo_total_estimado:,.2f} MXN"],
    ]
    
    logistica_table = Table(logistica_data, colWidths=[180, 320])
    logistica_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#994B49')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        # Destacar costo total
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (1, -1), (1, -1), 12),
        ('TEXTCOLOR', (1, -1), (1, -1), colors.HexColor('#994B49')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FEF3C7')),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(logistica_table)
    story.append(Spacer(1, 20))
    
    # --- DESGLOSE POR SEMANA PARA PRESUPUESTO ---
    if avances:
        story.append(Paragraph("💰 DESGLOSE DE COSTOS POR SEMANA", section_style))
        
        costo_headers = ["Semana", "Volumen (m³)", "Viajes", "Costo Estimado"]
        costo_data = [costo_headers]
        
        for avance in avances:
            volumen = avance.get('volumen_excavacion', 0) or 0
            viajes = int(volumen / capacidad_camion) if capacidad_camion > 0 else 0
            costo = volumen * costo_por_m3  # Costo basado en volumen
            costo_data.append([
                f"Semana {avance.get('semana', '?')}",
                f"{volumen:,.1f}",
                str(viajes),
                f"${costo:,.2f}"
            ])
        
        costo_data.append([
            "TOTAL",
            f"{volumen_total:,.1f}",
            str(total_viajes),
            f"${costo_total_estimado:,.2f}"
        ])
        
        costo_table = Table(costo_data, colWidths=[100, 120, 100, 140])
        costo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#D1FAE5')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#059669')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(costo_table)
    
    story.append(Spacer(1, 30))

    # --- AVANCE FÍSICO DE OBRA POR CATEGORÍA ---
    metricas = await obtener_metricas_proyecto(proyecto_id)
    categorias_fisicas = []
    if metricas.get("volumen_planeado", 0) > 0:
        categorias_fisicas.append({
            "nombre": "Excavación",
            "real": metricas["volumen_excavado"],
            "planeado": metricas["volumen_planeado"],
            "pct": metricas["avance_excavacion_pct"],
            "unidad": "m³",
            "color": "#F59E0B",
        })
    if metricas.get("pilas_planeadas", 0) > 0:
        categorias_fisicas.append({
            "nombre": "Pilas",
            "real": metricas["pilas_completadas"],
            "planeado": metricas["pilas_planeadas"],
            "pct": metricas["avance_pilas_pct"],
            "unidad": "pzs",
            "color": "#3B82F6",
        })
    if metricas.get("anclas_planeadas", 0) > 0:
        categorias_fisicas.append({
            "nombre": "Anclas",
            "real": metricas["anclas_instaladas"],
            "planeado": metricas["anclas_planeadas"],
            "pct": metricas["avance_anclas_pct"],
            "unidad": "pzs",
            "color": "#14B8A6",
        })
    if metricas.get("muros_planeados", 0) > 0:
        categorias_fisicas.append({
            "nombre": "Muros",
            "real": metricas["muros_completados"],
            "planeado": metricas["muros_planeados"],
            "pct": metricas["avance_muros_pct"],
            "unidad": "m²",
            "color": "#A855F7",
        })

    if categorias_fisicas:
        story.append(Paragraph("🏗️ AVANCE FÍSICO POR CATEGORÍA", section_style))

        # Determinar semana del corte: última semana con avance registrado.
        # Fallback: semanas transcurridas desde fecha_inicio del proyecto.
        semana_corte = max((int(a.get("semana") or 0) for a in avances), default=0)
        if semana_corte == 0:
            try:
                from datetime import date
                fi_str = proyecto.get("fecha_inicio")
                if fi_str:
                    fi = date.fromisoformat(fi_str[:10])
                    dias = (date.today() - fi).days
                    semana_corte = max(1, (dias // 7) + 1) if dias >= 0 else 1
            except Exception:
                semana_corte = 1
        # Mapa de programa por semana para calcular acumulados esperados
        programa_por_semana = {int(s.get("semana") or 0): s for s in (proyecto.get("programa_semanal") or [])}

        # Claves del programa_semanal que corresponden a cada categoría
        clave_programa_por_categoria = {
            "Excavación": "excavacion_m3",
            "Pilas": "pilas",
            "Anclas": "anclas",
            "Muros": "muros_m2",
        }

        # Calcular esperado acumulado hasta la semana del corte para cada categoría
        for c in categorias_fisicas:
            key_p = clave_programa_por_categoria.get(c["nombre"])
            acum_esperado = 0.0
            if key_p and semana_corte > 0:
                for w in range(1, semana_corte + 1):
                    sem = programa_por_semana.get(w) or {}
                    try:
                        acum_esperado += float(sem.get(key_p) or 0)
                    except (TypeError, ValueError):
                        pass
            total_planeado = float(c.get("planeado") or 0)
            c["esperado_hasta_corte"] = acum_esperado
            c["esperado_hasta_corte_pct"] = (acum_esperado / total_planeado * 100) if total_planeado > 0 else 0.0

        story.append(Paragraph(
            f"Comparativa hasta la <b>semana {semana_corte}</b> (semana del corte): "
            "porcentaje del total que se debería llevar acumulado según el programa vs porcentaje real medido por dron.",
            normal_style
        ))
        story.append(Spacer(1, 8))

        # Gráfica única: Barras agrupadas Esperado (a la semana de corte) vs Real, en % del total
        try:
            nombres = [c["nombre"] for c in categorias_fisicas]
            esperados_pct = [min(c.get("esperado_hasta_corte_pct", 0), 100) for c in categorias_fisicas]
            reales_pct = [min(c["pct"], 100) for c in categorias_fisicas]
            colors_real = [c["color"] for c in categorias_fisicas]

            x = np.arange(len(nombres))
            width = 0.38

            fig, ax = plt.subplots(figsize=(8, 4.2), facecolor='white')
            bars_p = ax.bar(x - width/2, esperados_pct, width,
                            label=f'Esperado a semana {semana_corte}',
                            color='#CBD5E1', edgecolor='#94A3B8', linewidth=0.8)
            bars_r = ax.bar(x + width/2, reales_pct, width, label='Real ejecutado',
                            color=colors_real, edgecolor='black', linewidth=0.5)

            ax.set_ylabel('% del total planeado', fontsize=9)
            ax.set_title(f'Avance Físico a Semana {semana_corte}: Esperado vs Real por Categoría',
                         fontsize=11, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(nombres, fontsize=9)
            y_max = max(esperados_pct + reales_pct + [10])
            ax.set_ylim(0, min(max(y_max * 1.2, 20), 110))
            ax.legend(loc='upper right', fontsize=8)
            ax.grid(axis='y', alpha=0.2, linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            # Etiquetas encima de cada barra
            for bar, val in zip(bars_p, esperados_pct):
                ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                        f'{val:.1f}%', ha='center', va='bottom', fontsize=8,
                        color='#475569', fontweight='bold')
            for bar, cat in zip(bars_r, categorias_fisicas):
                h = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., h + 1,
                        f'{cat["pct"]:.1f}%', ha='center', va='bottom', fontsize=8,
                        color='#0F172A', fontweight='bold')

            plt.tight_layout()
            chart_buf = io.BytesIO()
            plt.savefig(chart_buf, format='png', dpi=130, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            chart_buf.seek(0)
            story.append(RLImage(chart_buf, width=480, height=250))
            story.append(Spacer(1, 10))
        except Exception as e:
            story.append(Paragraph(f"<i>No se pudo generar la gráfica de avance físico: {e}</i>", normal_style))

        # Tabla detallada por categoría
        fis_headers = ["Categoría", "Planeado total", f"Esperado a sem. {semana_corte}", "Real ejecutado", "% vs Esperado"]
        fis_data = [fis_headers]
        for c in categorias_fisicas:
            esperado = c.get("esperado_hasta_corte", 0)
            real = c.get("real", 0)
            pct_vs_esperado = (real / esperado * 100) if esperado > 0 else 0
            fis_data.append([
                c["nombre"],
                f"{c['planeado']:,.2f} {c['unidad']}",
                f"{esperado:,.2f} {c['unidad']}",
                f"{real:,.2f} {c['unidad']}",
                f"{pct_vs_esperado:.1f}%" if esperado > 0 else "—",
            ])
        fis_table = Table(fis_data, colWidths=[90, 105, 105, 105, 75])
        fis_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#475569')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFA')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(fis_table)
        story.append(Spacer(1, 20))

    # --- MATRIZ DE PILAS/ANCLAS POR CARA (si está configurada) ---
    caras = proyecto.get("caras_excavacion") or []
    if len(caras) == 4 and any((c.get('pilas') or c.get('anclas')) for c in caras):
        story.append(Paragraph("🧱 PROGRESO POR CARA DE EXCAVACIÓN", section_style))
        cara_headers = ["Cara", "Pilas (compl./total)", "% Pilas", "Anclas (compl./total)", "% Anclas"]
        cara_data = [cara_headers]
        for c in caras:
            p_tot = int(c.get('pilas') or 0)
            a_tot = int(c.get('anclas') or 0)
            p_comp = sum(1 for s in (c.get('pilas_estados') or []) if s)
            a_comp = sum(1 for s in (c.get('anclas_estados') or []) if s)
            p_pct = (p_comp / p_tot * 100) if p_tot else 0
            a_pct = (a_comp / a_tot * 100) if a_tot else 0
            cara_data.append([
                c.get('nombre', '—'),
                f"{p_comp} / {p_tot}",
                f"{p_pct:.1f}%",
                f"{a_comp} / {a_tot}",
                f"{a_pct:.1f}%",
            ])
        cara_table = Table(cara_data, colWidths=[80, 110, 80, 110, 80])
        cara_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0E7490')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0FDFA')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(cara_table)
        story.append(Spacer(1, 20))

    # --- PRESUPUESTO vs EJECUTADO (con avances reales del dron) ---
    af = af_service.calcular_avance_financiero(proyecto, avances)
    if af.get("tiene_presupuesto") and af["categorias"]:
        story.append(Paragraph("💼 PRESUPUESTO vs EJECUTADO", section_style))
        story.append(Paragraph(
            f"Comparativa con avances reales medidos por dron. Versión: <b>{af.get('version', 'N/D')}</b>",
            normal_style
        ))
        story.append(Spacer(1, 8))

        # Cards de totales
        tot = af["totales"]
        totales_data = [
            ["Presupuestado", "Ejecutado", "Pendiente", "% Avance Financiero"],
            [
                f"${tot['presupuestado']:,.0f}",
                f"${tot['ejecutado']:,.0f}",
                f"${tot['pendiente']:,.0f}",
                f"{tot['pct']:.1f}%",
            ],
        ]
        totales_table = Table(totales_data, colWidths=[115, 115, 115, 115])
        totales_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#D97706')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 1), (-1, 1), 11),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#FEF3C7')),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#92400E')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(totales_table)
        story.append(Spacer(1, 12))

        # Gráfica de barras: Presupuestado vs Ejecutado por categoría
        try:
            cats = af["categorias"]
            nombres = [c["nombre"] for c in cats]
            presupuestados = [c["presupuestado"] for c in cats]
            ejecutados = [c["ejecutado"] for c in cats]
            cat_colors = [c["color"] for c in cats]

            x = np.arange(len(nombres))
            width = 0.38

            fig, ax = plt.subplots(figsize=(8, 4.5), facecolor='white')
            bars_p = ax.bar(x - width/2, presupuestados, width, label='Presupuestado',  # noqa: F841
                            color='#CBD5E1', edgecolor='#94A3B8', linewidth=0.8)
            bars_e = ax.bar(x + width/2, ejecutados, width, label='Ejecutado (real)',
                            color=cat_colors, edgecolor='black', linewidth=0.5)

            ax.set_ylabel('MXN', fontsize=9)
            ax.set_title('Presupuesto vs Ejecutado por Categoría', fontsize=11, fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(nombres, rotation=20, ha='right', fontsize=8)
            ax.legend(loc='upper right', fontsize=8)
            ax.grid(axis='y', alpha=0.2, linestyle='--')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            # Format Y-axis as currency
            ax.yaxis.set_major_formatter(plt.FuncFormatter(
                lambda x, _: f'${x/1_000_000:.1f}M' if x >= 1_000_000 else f'${x/1_000:.0f}k'
            ))
            # Etiquetar barras de ejecutado con % avance
            for bar, cat in zip(bars_e, cats):
                h = bar.get_height()
                if h > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., h,
                            f'{cat["pct_avance"]:.0f}%',
                            ha='center', va='bottom', fontsize=7, color='#0F172A', fontweight='bold')

            plt.tight_layout()
            chart_buf = io.BytesIO()
            plt.savefig(chart_buf, format='png', dpi=130, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            chart_buf.seek(0)
            story.append(RLImage(chart_buf, width=480, height=270))
            story.append(Spacer(1, 12))
        except Exception as e:
            story.append(Paragraph(f"<i>No se pudo generar la gráfica: {e}</i>", normal_style))

        # Tabla detallada por categoría
        cat_headers = ["Categoría", "Presupuestado", "Ejecutado", "% Avance", "Real medido"]
        cat_data = [cat_headers]
        for c in af["categorias"]:
            real_str = (
                f"{c['real']:,.2f} / {c['planeado']:,.2f} {c['unidad']}"
                if c.get("fuente_real") and c.get("planeado") else
                "—"
            )
            cat_data.append([
                c["nombre"],
                f"${c['presupuestado']:,.0f}",
                f"${c['ejecutado']:,.0f}",
                f"{c['pct_avance']:.1f}%",
                real_str,
            ])
        cat_table = Table(cat_data, colWidths=[100, 110, 110, 65, 105])
        cat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#D97706')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFA')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(cat_table)
        story.append(Spacer(1, 20))

    # --- RESUMEN DEL CHAT DE OBRA (WHATSAPP · IA) ---
    try:
        todos_wa = await db.comentarios_semana.find(
            {"proyecto_id": proyecto_id, "fuente": "whatsapp_ia"},
            {"_id": 0},
        ).sort("semana", -1).to_list(20)
        con_mensajes = [c for c in todos_wa if (c.get("mensajes_analizados") or 0) > 0]
        comentarios_wa = con_mensajes[:4] if con_mensajes else todos_wa[:2]
    except Exception as e:
        logging.error(f"Error leyendo comentarios de WhatsApp: {e}")
        comentarios_wa = []

    if comentarios_wa:
        comentarios_wa = sorted(comentarios_wa, key=lambda c: c.get("semana", 0))
        story.append(Paragraph("💬 RESUMEN DEL CHAT DE OBRA (WHATSAPP · IA)", section_style))
        story.append(Paragraph(
            "Resumen generado por IA a partir de los mensajes del grupo de WhatsApp de la obra, "
            "con las posibles justificaciones de retrasos reportadas por el equipo en campo.",
            normal_style
        ))
        story.append(Spacer(1, 6))
        wa_semana_style = ParagraphStyle(
            'WaSemana',
            parent=styles['Heading3'],
            fontSize=11,
            textColor=colors.HexColor('#128C7E'),
            spaceBefore=8,
            spaceAfter=4,
        )
        wa_texto_style = ParagraphStyle(
            'WaTexto',
            parent=styles['Normal'],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#334155'),
            spaceAfter=6,
        )
        for c in comentarios_wa:
            texto = _texto_wa_pdf(c.get("texto") or "")
            if not texto:
                continue
            n_msgs = c.get("mensajes_analizados") or 0
            encabezado = f"Semana {c.get('semana', '?')}"
            if n_msgs:
                encabezado += f" · {n_msgs} mensajes analizados"
            story.append(Paragraph(encabezado, wa_semana_style))
            wa_box = Table([[Paragraph(texto, wa_texto_style)]], colWidths=[500])
            wa_box.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0FDF4')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#BBF7D0')),
                ('PADDING', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(wa_box)
        story.append(Spacer(1, 10))

    story.append(Spacer(1, 30))
    
    # --- PIE DE PÁGINA ---
    fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M")
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#9CA3AF'),
        alignment=TA_CENTER
    )
    story.append(Paragraph(f"Reporte generado el {fecha_generacion} | DrON Topografía - Gestión de Construcción con Drones", footer_style))
    story.append(Paragraph("* Los costos son estimados y pueden variar según las condiciones del mercado y la distancia de transporte.", footer_style))
    
    # Generar PDF
    doc.build(story)
    buffer.seek(0)
    
    # Nombre del archivo
    proyecto_nombre = proyecto.get('nombre', 'Proyecto').replace(' ', '_')
    fecha_archivo = datetime.now().strftime("%Y%m%d")
    pdf_filename = f"Reporte_Ejecutivo_{proyecto_nombre}_{fecha_archivo}.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={pdf_filename}"}
    )

