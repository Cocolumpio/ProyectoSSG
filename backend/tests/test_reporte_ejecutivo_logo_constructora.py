"""Tests for constructora logo embedded in /api/proyectos/{id}/reporte-ejecutivo PDF.

Covers:
  1) PDF with constructora assigned (logo present) -> +1 imagen page 1, texto Cliente / fila tabla.
  2) Regresión: PDF sin constructora sigue funcionando (sin fila 'Constructora / Cliente').
  3) Edge case: constructora asignada SIN logo -> no falla, no imagen extra, sí fila con nombre.
"""
import io
import os
import pytest
import requests
from PIL import Image
from pypdf import PdfReader

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN_EMAIL = "admin@dron.mx"
ADMIN_PASS = "admin123"
TIMEOUT = 180

# Torre Mezquitan: sin modelo 3D, para minimizar tiempo de render
PROYECTO_ID = "2e38ce19-3ce3-4bf1-a7be-84b2f5a1049f"


def _png_bytes(size=(200, 100), color=(231, 122, 95, 255)):
    buf = io.BytesIO()
    Image.new("RGBA", size, color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def admin_headers():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def proyecto_original(admin_headers):
    """Snapshot del proyecto para restaurar constructora_id al final."""
    r = requests.get(f"{BASE_URL}/api/proyectos/{PROYECTO_ID}", headers=admin_headers, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def _fetch_pdf():
    return requests.get(f"{BASE_URL}/api/proyectos/{PROYECTO_ID}/reporte-ejecutivo", timeout=TIMEOUT)


def _analyze_pdf(pdf_bytes: bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    page1_text = ""
    page1_images = 0
    total_text = ""
    total_images = 0
    for idx, page in enumerate(reader.pages):
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        total_text += t + "\n"
        try:
            imgs = list(page.images)
        except Exception:
            imgs = []
        total_images += len(imgs)
        if idx == 0:
            page1_text = t
            page1_images = len(imgs)
    return {
        "page1_text": page1_text,
        "page1_images": page1_images,
        "total_text": total_text,
        "total_images": total_images,
    }


def _assign_constructora(headers, proyecto_original, constructora_id):
    """PUT /api/proyectos/{id} asignando constructora_id (necesita otro campo != None)."""
    payload = {
        "nombre": proyecto_original["nombre"],
        "constructora_id": constructora_id,
    }
    r = requests.put(
        f"{BASE_URL}/api/proyectos/{PROYECTO_ID}", json=payload, headers=headers, timeout=30
    )
    assert r.status_code == 200, r.text


# ---------- Test 1: regresión — sin constructora ----------
def test_pdf_sin_constructora_no_regresion(admin_headers, proyecto_original):
    """Baseline: sin constructora asignada, PDF genera OK y no muestra 'Cliente:'."""
    # Asegurar que no hay constructora asignada: si tiene, la limpiamos vía cascade delete.
    # En vez de eso, verificamos el estado actual; si tiene, saltamos limpieza directa.
    # Cascade solo aplica al borrar constructora, así que usamos update directo de Mongo.
    # Estrategia simple: si tiene constructora, la conservamos en fixture para restaurar.
    # Para forzar "sin constructora" para este test, hacemos update via endpoint asignando None
    # -- pero endpoint filtra None. Alternativa: si actualmente ya está en None -> proceder.
    current_cid = proyecto_original.get("constructora_id")
    if current_cid:
        pytest.skip(f"Proyecto ya tiene constructora ({current_cid}); test de regresión requiere estado limpio")

    r = _fetch_pdf()
    assert r.status_code == 200, r.text[:400]
    info = _analyze_pdf(r.content)
    baseline_page1_imgs = info["page1_images"]

    assert "Cliente:" not in info["page1_text"], f"No debería aparecer 'Cliente:' en PDF sin constructora. text={info['page1_text'][:400]}"
    assert "Constructora / Cliente" not in info["total_text"], "No debería aparecer la fila 'Constructora / Cliente'"

    # Guardar baseline para test siguiente
    pytest.baseline_page1_imgs = baseline_page1_imgs
    print(f"[OK] baseline sin constructora: page1_images={baseline_page1_imgs}, total_images={info['total_images']}")


# ---------- Test 2: con logo ----------
def test_pdf_con_constructora_y_logo(admin_headers, proyecto_original):
    baseline = getattr(pytest, "baseline_page1_imgs", None)

    # Crear constructora con logo
    files = {"logo": ("logo.png", _png_bytes(), "image/png")}
    data = {"nombre": "TEST_ConstructoraLogo_RE", "activo": "true", "orden": "9"}
    r = requests.post(
        f"{BASE_URL}/api/constructoras", data=data, files=files, headers=admin_headers, timeout=30
    )
    assert r.status_code == 200, r.text
    constructora = r.json()
    cid = constructora["id"]

    try:
        _assign_constructora(admin_headers, proyecto_original, cid)

        r = _fetch_pdf()
        assert r.status_code == 200, r.text[:400]
        info = _analyze_pdf(r.content)

        # (a) Texto Cliente + nombre. El header italic es "Cliente: <nombre>"
        # (distinto de la fila de tabla "Constructora / Cliente:").
        assert "Cliente: TEST_ConstructoraLogo_RE" in info["page1_text"], (
            f"Header 'Cliente: <nombre>' ausente en page 1. text={info['page1_text'][:500]}"
        )

        # (b) Fila tabla
        assert "Constructora / Cliente" in info["total_text"], "Fila 'Constructora / Cliente' ausente en tabla"
        assert "TEST_ConstructoraLogo_RE" in info["total_text"]

        # (c) +1 imagen en page 1 (el logo)
        if baseline is not None:
            assert info["page1_images"] >= baseline + 1, (
                f"Se esperaba +1 imagen en page 1 (baseline={baseline}), got={info['page1_images']}"
            )
        else:
            assert info["page1_images"] >= 1, "Se esperaba al menos 1 imagen (logo) en page 1"

        print(
            f"[OK] con logo: page1_images={info['page1_images']} (baseline={baseline}), "
            f"total_images={info['total_images']}"
        )
    finally:
        # Cleanup: borrar constructora (cascade limpia constructora_id del proyecto)
        d = requests.delete(f"{BASE_URL}/api/constructoras/{cid}", headers=admin_headers, timeout=30)
        assert d.status_code in (200, 204), d.text


# ---------- Test 3: constructora sin logo ----------
def test_pdf_con_constructora_sin_logo_no_falla(admin_headers, proyecto_original):
    """Edge case: constructora asignada pero sin logo -> PDF OK, sin imagen extra, con fila."""
    baseline = getattr(pytest, "baseline_page1_imgs", None)

    # POST sin archivo logo (permitido)
    data = {"nombre": "TEST_ConstructoraSinLogo_RE", "activo": "true", "orden": "9"}
    r = requests.post(
        f"{BASE_URL}/api/constructoras", data=data, headers=admin_headers, timeout=30
    )
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    assert not r.json().get("logo_url"), "No debería tener logo_url"

    try:
        _assign_constructora(admin_headers, proyecto_original, cid)

        r = _fetch_pdf()
        assert r.status_code == 200, f"PDF falló con constructora sin logo: {r.text[:400]}"
        info = _analyze_pdf(r.content)

        # Fila sí debe aparecer con el nombre
        assert "Constructora / Cliente" in info["total_text"], "Fila 'Constructora / Cliente' esperada aun sin logo"
        assert "TEST_ConstructoraSinLogo_RE" in info["total_text"]

        # No debe haber imagen extra
        if baseline is not None:
            assert info["page1_images"] <= baseline, (
                f"No debía haber imagen extra sin logo (baseline={baseline}, got={info['page1_images']})"
            )
        # No debe aparecer el header italic 'Cliente: <nombre>' (viene solo con logo)
        assert "Cliente: TEST_ConstructoraSinLogo_RE" not in info["page1_text"], (
            f"Header 'Cliente: <nombre>' no debería aparecer sin logo. text={info['page1_text'][:400]}"
        )

        print(
            f"[OK] sin logo: page1_images={info['page1_images']} (baseline={baseline})"
        )
    finally:
        d = requests.delete(f"{BASE_URL}/api/constructoras/{cid}", headers=admin_headers, timeout=30)
        assert d.status_code in (200, 204), d.text
