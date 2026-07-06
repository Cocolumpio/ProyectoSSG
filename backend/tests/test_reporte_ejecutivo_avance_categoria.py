"""Tests para sección 'AVANCE FÍSICO POR CATEGORÍA' del reporte ejecutivo PDF.

Verifica:
- Se ELIMINÓ la gráfica horizontal 'Progreso de Obra por Categoría'.
- La gráfica vertical tiene el nuevo título 'Avance Físico a Semana N: Esperado vs Real por Categoría'.
- Texto descriptivo 'Comparativa hasta la semana N (semana del corte)'.
- Tabla ahora tiene 5 columnas (Categoría, Planeado total, Esperado a sem. N, Real ejecutado, % vs Esperado).
- Fallback semana_corte por fecha_inicio (Torre Mezquitan).
- Regresión: proyectos sin programa_semanal se generan sin error.
"""
import io
import os
import re
import pytest
import requests
from pypdf import PdfReader

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
TIMEOUT = 180

# Proyectos preview
HOTEL_MARRIOTT = ("Hotel Marriott GDL", "51a604b9-e513-4a9b-ab96-b9706cae0dda")
TORRE_MEZQUITAN = ("Torre Mezquitan", "2e38ce19-3ce3-4bf1-a7be-84b2f5a1049f")
E2E_3FASES = ("Proyecto E2E 3 Fases Test", "808bcba5-7792-492e-a2ee-fd9ff10e6e5e")


def _fetch_pdf(proyecto_id: str):
    url = f"{BASE_URL}/api/proyectos/{proyecto_id}/reporte-ejecutivo"
    return requests.get(url, timeout=TIMEOUT)


def _extract_text(pdf_bytes: bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text_all = ""
    for page in reader.pages:
        try:
            text_all += (page.extract_text() or "") + "\n"
        except Exception:
            pass
    return text_all


@pytest.mark.parametrize("nombre,proyecto_id", [HOTEL_MARRIOTT, TORRE_MEZQUITAN, E2E_3FASES])
def test_grafica_horizontal_eliminada(nombre, proyecto_id):
    """La gráfica horizontal 'Progreso de Obra por Categoría' NO debe aparecer."""
    r = _fetch_pdf(proyecto_id)
    assert r.status_code == 200, f"{nombre}: HTTP {r.status_code}: {r.text[:400]}"
    text = _extract_text(r.content)
    assert "Progreso de Obra por Categoría" not in text, \
        f"{nombre}: PDF aún contiene el título de la gráfica horizontal eliminada"
    print(f"[OK] {nombre}: gráfica horizontal ausente")


def test_hotel_marriott_semana_corte_desde_avances():
    """Hotel Marriott (con avances): 'Comparativa hasta la semana N (semana del corte)' + tabla con 'Esperado a sem. N'.
    Nota: el título 'Avance Físico a Semana N: Esperado vs Real por Categoría' se renderiza dentro
    de la imagen matplotlib y NO es extraíble como texto por pypdf. Verificamos entonces:
    - Texto descriptivo con Semana N (semana del corte)
    - Encabezado de tabla 'Esperado a sem. N' con la misma N
    - Que Hotel Marriott (que tiene avances) devuelva semana_corte>0.
    """
    nombre, pid = HOTEL_MARRIOTT
    r = _fetch_pdf(pid)
    assert r.status_code == 200
    text = _extract_text(r.content)

    m = re.search(r"Comparativa hasta la semana\s+(\d+)\s*\(semana del corte\)", text)
    assert m, f"{nombre}: no se encontró 'Comparativa hasta la semana N (semana del corte)'. Sample: {text[:800]}"
    semana_n = int(m.group(1))
    assert semana_n > 0, f"{nombre}: semana_corte debe ser > 0, fue {semana_n}"

    # Encabezado de tabla debe reflejar misma semana
    assert f"Esperado a sem. {semana_n}" in text, \
        f"{nombre}: encabezado 'Esperado a sem. {semana_n}' no encontrado"
    print(f"[OK] {nombre}: semana_corte={semana_n} (desde avances)")


def test_tabla_5_columnas_hotel_marriott():
    """La tabla debe tener 5 columnas: Categoría, Planeado total, Esperado a sem. N, Real ejecutado, % vs Esperado."""
    nombre, pid = HOTEL_MARRIOTT
    r = _fetch_pdf(pid)
    assert r.status_code == 200
    text = _extract_text(r.content)
    for header in ["Categor", "Planeado total", "Esperado a sem", "Real ejecutado", "% vs Esperado"]:
        assert header in text, f"{nombre}: falta encabezado '{header}' en tabla. Sample: {text[:1200]}"
    print(f"[OK] {nombre}: tabla con 5 columnas")


def test_torre_mezquitan_fallback_semana_corte_por_fecha():
    """Torre Mezquitan tiene programa_semanal pero SIN avances: semana_corte debe calcularse por fecha_inicio."""
    nombre, pid = TORRE_MEZQUITAN
    r = _fetch_pdf(pid)
    assert r.status_code == 200, f"{nombre}: HTTP {r.status_code}: {r.text[:400]}"
    assert r.headers.get("content-type", "").startswith("application/pdf")
    text = _extract_text(r.content)

    m = re.search(r"Comparativa hasta la semana\s+(\d+)\s*\(semana del corte\)", text)
    assert m, f"{nombre}: no se encontró 'Comparativa hasta la semana N'. Sample: {text[:1200]}"
    semana_n = int(m.group(1))
    assert semana_n > 0, f"{nombre}: fallback por fecha debe dar semana_corte>0, obtuvo {semana_n}"
    assert f"Esperado a sem. {semana_n}" in text
    print(f"[OK] {nombre}: fallback OK, semana_corte={semana_n}")


def test_regresion_sin_programa_semanal_no_falla():
    """Proyecto sin programa_semanal (E2E 3 Fases legacy) debe generar el PDF sin errores."""
    nombre, pid = E2E_3FASES
    r = _fetch_pdf(pid)
    assert r.status_code == 200, f"{nombre}: HTTP {r.status_code}: {r.text[:400]}"
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert len(r.content) > 3000
    print(f"[OK] {nombre}: PDF generado sin errores, {len(r.content):,} bytes")
