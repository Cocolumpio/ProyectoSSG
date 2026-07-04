"""Tests para el endpoint /api/proyectos/{id}/reporte-ejecutivo (PDF con modelo 3D embebido)."""
import io
import os
import pytest
import requests
from pypdf import PdfReader

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
TIMEOUT = 180  # PLY rendering can take 10-60s for large models

# Proyectos con modelo 3D
PROYECTOS_CON_MODELO = [
    ("Hotel Marriott GDL", "51a604b9-e513-4a9b-ab96-b9706cae0dda"),
    ("Proyecto E2E 3 Fases Test", "808bcba5-7792-492e-a2ee-fd9ff10e6e5e"),
    ("Torre Corporativa Demo", "d250ab6b-56d5-48e5-b114-f1c7f9c04c59"),
]

PROYECTO_SIN_MODELO_ID = "2e38ce19-3ce3-4bf1-a7be-84b2f5a1049f"  # Torre Mezquitan


def _fetch_pdf(proyecto_id: str):
    url = f"{BASE_URL}/api/proyectos/{proyecto_id}/reporte-ejecutivo"
    r = requests.get(url, timeout=TIMEOUT)
    return r


def _extract_text_and_image_count(pdf_bytes: bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text_all = ""
    total_images = 0
    for page in reader.pages:
        try:
            text_all += (page.extract_text() or "") + "\n"
        except Exception:
            pass
        try:
            total_images += len(page.images)
        except Exception:
            pass
    return text_all, total_images


@pytest.mark.parametrize("nombre,proyecto_id", PROYECTOS_CON_MODELO)
def test_reporte_con_modelo_3d(nombre, proyecto_id):
    """El PDF debe contener sección MODELO 3D y las 3 vistas embebidas."""
    r = _fetch_pdf(proyecto_id)
    assert r.status_code == 200, f"{nombre}: HTTP {r.status_code}: {r.text[:400]}"
    assert r.headers.get("content-type", "").startswith("application/pdf"), \
        f"{nombre}: content-type={r.headers.get('content-type')}"
    assert len(r.content) > 5000, f"{nombre}: PDF too small ({len(r.content)} bytes)"

    text, img_count = _extract_text_and_image_count(r.content)

    # 1) Texto de sección
    assert "MODELO 3D DEL SITIO" in text, \
        f"{nombre}: falta 'MODELO 3D DEL SITIO' en PDF. Contenido inicial: {text[:600]}"
    # 2) Titulos de las 3 vistas (captions)
    for expected in ["Vista Superior", "Isométrica Noreste", "Isométrica Suroeste"]:
        assert expected in text, f"{nombre}: falta caption '{expected}' en PDF"

    # 3) Al menos 3 imágenes del modelo 3D embebidas
    #    (el PDF también contiene gráficas de avance/presupuesto, así que esperamos >=3)
    assert img_count >= 3, f"{nombre}: se esperaban >=3 imágenes en PDF, se encontraron {img_count}"

    print(f"[OK] {nombre}: {len(r.content):,} bytes, {img_count} imágenes")


def test_reporte_sin_modelo_3d_no_regresa_error():
    """Proyecto sin modelo 3D: el PDF debe generarse OK, sin sección de modelo 3D."""
    r = _fetch_pdf(PROYECTO_SIN_MODELO_ID)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:400]}"
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert len(r.content) > 3000

    text, _ = _extract_text_and_image_count(r.content)
    # Debe tener información del proyecto pero NO la sección de modelo 3D
    assert "INFORMACIÓN DEL PROYECTO" in text or "INFORMACI" in text
    assert "MODELO 3D DEL SITIO" not in text, \
        "Torre Mezquitan no tiene modelo 3D pero el PDF contiene la sección"
    print(f"[OK] Torre Mezquitan (sin modelo): {len(r.content):,} bytes, sin sección modelo 3D")
