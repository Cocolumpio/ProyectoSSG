"""Tests for /api/constructoras CRUD + public endpoints + proyecto.constructora_id persistence."""
import io
import os
import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN_EMAIL = "admin@dron.mx"
ADMIN_PASS = "admin123"


def _png_bytes(size=(200, 100), color=(231, 122, 95, 255)):
    buf = io.BytesIO()
    Image.new("RGBA", size, color).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def created_constructora(auth_headers):
    files = {"logo": ("logo.png", _png_bytes(), "image/png")}
    data = {"nombre": "TEST_Constructora_Auto", "activo": "true", "orden": "5"}
    r = requests.post(f"{BASE_URL}/api/constructoras", data=data, files=files, headers=auth_headers, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "id" in body
    assert body["nombre"] == "TEST_Constructora_Auto"
    assert body.get("logo_url"), "logo_url should be present"
    yield body
    # Teardown
    requests.delete(f"{BASE_URL}/api/constructoras/{body['id']}", headers=auth_headers, timeout=30)


class TestConstructorasCRUD:
    def test_create_returned_id_and_logo(self, created_constructora):
        assert created_constructora["id"]
        assert created_constructora["logo_url"].endswith(f"/api/constructoras/{created_constructora['id']}/logo")

    def test_list_admin_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/constructoras", timeout=30)
        assert r.status_code in (401, 403)

    def test_list_admin_ok(self, auth_headers, created_constructora):
        r = requests.get(f"{BASE_URL}/api/constructoras", headers=auth_headers, timeout=30)
        assert r.status_code == 200
        ids = [c["id"] for c in r.json()["constructoras"]]
        assert created_constructora["id"] in ids

    def test_update_multipart(self, auth_headers, created_constructora):
        cid = created_constructora["id"]
        r = requests.put(
            f"{BASE_URL}/api/constructoras/{cid}",
            data={"nombre": "TEST_Constructora_Updated", "activo": "true"},
            headers=auth_headers, timeout=30,
        )
        assert r.status_code == 200, r.text
        assert r.json()["nombre"] == "TEST_Constructora_Updated"

    def test_public_endpoint_no_auth(self, created_constructora):
        r = requests.get(f"{BASE_URL}/api/public/constructoras", timeout=30)
        assert r.status_code == 200
        ids = [c["id"] for c in r.json()["constructoras"]]
        assert created_constructora["id"] in ids

    def test_logo_binary(self, created_constructora):
        r = requests.get(f"{BASE_URL}{created_constructora['logo_url']}", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/")
        assert len(r.content) > 100


class TestValidations:
    def test_reject_large_logo(self, auth_headers):
        # 4MB PNG
        big = _png_bytes(size=(3000, 3000))
        assert len(big) > 3 * 1024 * 1024 or True  # generated large may not exceed; enforce
        # ensure size > 3MB by padding
        while len(big) <= 3 * 1024 * 1024:
            big += b"\x00" * (1024 * 1024)
        files = {"logo": ("big.png", big, "image/png")}
        r = requests.post(f"{BASE_URL}/api/constructoras", data={"nombre": "TEST_Big"}, files=files, headers=auth_headers, timeout=60)
        assert r.status_code == 400, r.text

    def test_reject_bad_format(self, auth_headers):
        files = {"logo": ("doc.pdf", b"%PDF-1.4 fake", "application/pdf")}
        r = requests.post(f"{BASE_URL}/api/constructoras", data={"nombre": "TEST_BadFmt"}, files=files, headers=auth_headers, timeout=30)
        assert r.status_code == 400

    def test_reject_empty_name(self, auth_headers):
        files = {"logo": ("l.png", _png_bytes(), "image/png")}
        r = requests.post(f"{BASE_URL}/api/constructoras", data={"nombre": "   "}, files=files, headers=auth_headers, timeout=30)
        assert r.status_code == 400


class TestProyectoConstructoraId:
    def test_create_and_persist(self, auth_headers, created_constructora):
        cid = created_constructora["id"]
        payload = {
            "nombre": "TEST_Proj_Constructora",
            "tipo": "excavacion",
            "ubicacion": "TEST",
            "coordenadas": {"lat": 19.0, "lng": -99.0},
            "fecha_inicio": "2026-01-01",
            "fecha_fin_planeada": "2026-06-01",
            "constructora_id": cid,
        }
        r = requests.post(f"{BASE_URL}/api/proyectos", json=payload, headers=auth_headers, timeout=30)
        assert r.status_code in (200, 201), r.text
        pid = r.json()["id"]
        # GET
        r2 = requests.get(f"{BASE_URL}/api/proyectos/{pid}", headers=auth_headers, timeout=30)
        assert r2.status_code == 200
        assert r2.json().get("constructora_id") == cid
        # Update reassign via PUT
        r4 = requests.put(f"{BASE_URL}/api/proyectos/{pid}", json={"constructora_id": cid, "nombre": "TEST_Proj_Constructora"}, headers=auth_headers, timeout=30)
        assert r4.status_code == 200
        assert r4.json().get("constructora_id") == cid
        # Cleanup project
        requests.delete(f"{BASE_URL}/api/proyectos/{pid}", headers=auth_headers, timeout=30)

    def test_delete_constructora_unlinks_project(self, auth_headers):
        # create a temp constructora
        files = {"logo": ("t.png", _png_bytes(), "image/png")}
        rc = requests.post(f"{BASE_URL}/api/constructoras", data={"nombre": "TEST_ToDelete"}, files=files, headers=auth_headers, timeout=30)
        assert rc.status_code == 200
        cid = rc.json()["id"]
        # create project linked
        rp = requests.post(f"{BASE_URL}/api/proyectos", json={"nombre": "TEST_Proj_Unlink", "tipo": "excavacion", "ubicacion": "TEST", "coordenadas": {"lat": 19.0, "lng": -99.0}, "fecha_inicio": "2026-01-01", "fecha_fin_planeada": "2026-06-01", "constructora_id": cid}, headers=auth_headers, timeout=30)
        assert rp.status_code in (200, 201)
        pid = rp.json()["id"]
        # delete constructora
        rd = requests.delete(f"{BASE_URL}/api/constructoras/{cid}", headers=auth_headers, timeout=30)
        assert rd.status_code == 200
        # verify project constructora_id is None
        rg = requests.get(f"{BASE_URL}/api/proyectos/{pid}", headers=auth_headers, timeout=30)
        assert rg.status_code == 200
        assert rg.json().get("constructora_id") in (None, "")
        # cleanup
        requests.delete(f"{BASE_URL}/api/proyectos/{pid}", headers=auth_headers, timeout=30)
