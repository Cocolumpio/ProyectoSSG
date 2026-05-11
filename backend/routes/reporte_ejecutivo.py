"""Rutas de Reporte Ejecutivo PDF - DrON Topografía"""
import os
import io
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER

from core.config import get_db

db = get_db()
router = APIRouter(prefix="/api")

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
    
    # --- ENCABEZADO ---
    story.append(Paragraph("REPORTE EJECUTIVO", title_style))
    story.append(Paragraph("Gestión de Construcción con Drones", subtitle_style))
    story.append(Spacer(1, 20))
    
    # --- INFORMACIÓN DEL PROYECTO ---
    story.append(Paragraph("📋 INFORMACIÓN DEL PROYECTO", section_style))
    
    proyecto_info = [
        ["Nombre del Proyecto:", proyecto.get('nombre', 'N/A')],
        ["Ubicación:", proyecto.get('ubicacion', 'N/A')],
        ["Coordenadas:", f"Lat: {proyecto.get('coordenadas', {}).get('lat', 'N/A')}, Lng: {proyecto.get('coordenadas', {}).get('lng', 'N/A')}"],
        ["Fecha de Inicio:", proyecto.get('fecha_inicio', 'N/A')],
        ["Fecha Fin Planeada:", proyecto.get('fecha_fin_planeada', 'N/A')],
        ["Descripción:", proyecto.get('descripcion', 'Sin descripción')[:100] + '...' if proyecto.get('descripcion') and len(proyecto.get('descripcion', '')) > 100 else proyecto.get('descripcion', 'Sin descripción')],
    ]
    
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

