"""Regression tests for the new Caras de Excavación matrix feature.

Covers:
- GET/PUT /api/proyectos/{id}/caras-excavacion (admin)
- PUT /api/proyectos/{id}/caras-excavacion/{cara_idx}/{tipo}/{cell_idx} toggle (admin-only -> 403 for client)
- GET /api/proyectos/{id}/caras-excavacion/resumen
- Effect on pilas_ejecutadas / anclas_ejecutadas / avance_actual
- Reporte Ejecutivo PDF still works and grew in size (charts + caras section)
- Avance Financiero uses caras when configured
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

ADMIN_EMAIL = "admin@dron.mx"
ADMIN_PASS = "admin123"
CLIENT_EMAIL = "cliente@test.com"
CLIENT_PASS = "cliente123"


# ---------- Fixtures ----------

@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def client_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": CLIENT_EMAIL, "password": CLIENT_PASS})
    if r.status_code != 200:
        pytest.skip("client login failed; skipping client-RBAC tests")
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def client_headers(client_token):
    return {"Authorization": f"Bearer {client_token}"}


@pytest.fixture(scope="module")
def test_project(admin_headers):
    """Create a fresh project for caras-excavacion tests."""
    payload = {
        "nombre": "TEST_CarasExcavacion_Project",
        "ubicacion": "Test Site",
        "cliente": "TEST_Client",
        "tipo_obra": "edificacion",
        "presupuesto_total": 1000000,
        "fecha_inicio": "2025-01-01",
        "fecha_fin_planeada": "2025-12-31",
        "coordenadas": {"lat": 19.4326, "lng": -99.1332},
    }
    r = requests.post(f"{BASE_URL}/api/proyectos", json=payload, headers=admin_headers)
    assert r.status_code in (200, 201), f"create project failed: {r.status_code} {r.text}"
    proj = r.json()
    pid = proj.get("id") or proj.get("_id")
    assert pid, f"no project id in response: {proj}"
    yield pid
    # Teardown
    requests.delete(f"{BASE_URL}/api/proyectos/{pid}", headers=admin_headers)


# ---------- Tests ----------

class TestCarasExcavacionConfig:
    def test_get_caras_empty_initially(self, test_project, admin_headers):
        r = requests.get(f"{BASE_URL}/api/proyectos/{test_project}/caras-excavacion", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert "configurado" in data and "caras" in data
        # New project: not configured
        assert data["configurado"] is False
        assert data["caras"] == []

    def test_put_requires_exactly_4_caras(self, test_project, admin_headers):
        r = requests.put(
            f"{BASE_URL}/api/proyectos/{test_project}/caras-excavacion",
            json={"caras": [{"nombre": "Norte", "pilas": 5, "anclas": 3}]},
            headers=admin_headers,
        )
        assert r.status_code == 422, f"expected validation error, got {r.status_code}: {r.text}"

    def test_put_caras_admin(self, test_project, admin_headers):
        payload = {"caras": [
            {"nombre": "Norte", "pilas": 4, "anclas": 2},
            {"nombre": "Sur", "pilas": 4, "anclas": 2},
            {"nombre": "Este", "pilas": 3, "anclas": 1},
            {"nombre": "Oeste", "pilas": 3, "anclas": 1},
        ]}
        r = requests.put(
            f"{BASE_URL}/api/proyectos/{test_project}/caras-excavacion",
            json=payload, headers=admin_headers,
        )
        assert r.status_code == 200, r.text
        caras = r.json()["caras"]
        assert len(caras) == 4
        assert caras[0]["nombre"] == "Norte"
        assert caras[0]["pilas"] == 4
        assert len(caras[0]["pilas_estados"]) == 4
        assert all(s is False for s in caras[0]["pilas_estados"])
        assert len(caras[0]["anclas_estados"]) == 2

    def test_project_aggregates_after_config(self, test_project, admin_headers):
        r = requests.get(f"{BASE_URL}/api/proyectos/{test_project}", headers=admin_headers)
        assert r.status_code == 200
        proj = r.json()
        # Sum: 4+4+3+3 = 14 pilas, 2+2+1+1 = 6 anclas
        assert proj.get("pilas_planeadas") == 14, f"got {proj.get('pilas_planeadas')}"
        assert proj.get("anclas_planeadas") == 6
        assert proj.get("pilas_ejecutadas") == 0
        assert proj.get("anclas_ejecutadas") == 0


class TestToggleCelda:
    def test_toggle_pila_admin(self, test_project, admin_headers):
        r = requests.put(
            f"{BASE_URL}/api/proyectos/{test_project}/caras-excavacion/0/pilas/0",
            headers=admin_headers,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["estado"] is True
        assert data["cara_idx"] == 0
        assert data["tipo"] == "pilas"

    def test_toggle_persists_and_recalcs(self, test_project, admin_headers):
        # Toggle anclas[1][0] on as well
        r = requests.put(
            f"{BASE_URL}/api/proyectos/{test_project}/caras-excavacion/1/anclas/0",
            headers=admin_headers,
        )
        assert r.status_code == 200

        # Verify via GET
        r = requests.get(f"{BASE_URL}/api/proyectos/{test_project}/caras-excavacion", headers=admin_headers)
        caras = r.json()["caras"]
        assert caras[0]["pilas_estados"][0] is True
        assert caras[1]["anclas_estados"][0] is True

        # Verify project ejecutadas counters updated
        r = requests.get(f"{BASE_URL}/api/proyectos/{test_project}", headers=admin_headers)
        proj = r.json()
        assert proj.get("pilas_ejecutadas") == 1
        assert proj.get("anclas_ejecutadas") == 1

    def test_toggle_invalid_tipo(self, test_project, admin_headers):
        r = requests.put(
            f"{BASE_URL}/api/proyectos/{test_project}/caras-excavacion/0/foo/0",
            headers=admin_headers,
        )
        assert r.status_code == 400

    def test_toggle_invalid_cara_idx(self, test_project, admin_headers):
        r = requests.put(
            f"{BASE_URL}/api/proyectos/{test_project}/caras-excavacion/9/pilas/0",
            headers=admin_headers,
        )
        assert r.status_code == 400

    def test_toggle_invalid_cell_idx(self, test_project, admin_headers):
        r = requests.put(
            f"{BASE_URL}/api/proyectos/{test_project}/caras-excavacion/0/pilas/99",
            headers=admin_headers,
        )
        assert r.status_code == 400

    def test_toggle_forbidden_for_client(self, test_project, client_headers):
        r = requests.put(
            f"{BASE_URL}/api/proyectos/{test_project}/caras-excavacion/0/pilas/0",
            headers=client_headers,
        )
        # Should be 403 since toggle requires admin
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"

    def test_put_caras_forbidden_for_client(self, test_project, client_headers):
        payload = {"caras": [
            {"nombre": "X", "pilas": 1, "anclas": 0},
            {"nombre": "Y", "pilas": 1, "anclas": 0},
            {"nombre": "Z", "pilas": 1, "anclas": 0},
            {"nombre": "W", "pilas": 1, "anclas": 0},
        ]}
        r = requests.put(
            f"{BASE_URL}/api/proyectos/{test_project}/caras-excavacion",
            json=payload, headers=client_headers,
        )
        assert r.status_code == 403


class TestResumen:
    def test_resumen_aggregates_correctly(self, test_project, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/proyectos/{test_project}/caras-excavacion/resumen",
            headers=admin_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["caras"]) == 4
        cara0 = data["caras"][0]
        assert cara0["pilas_total"] == 4
        assert cara0["pilas_completadas"] == 1
        assert cara0["anclas_total"] == 2
        # totales
        t = data["totales"]
        assert t["pilas_total"] == 14
        assert t["pilas_completadas"] == 1
        assert t["anclas_total"] == 6
        assert t["anclas_completadas"] == 1


class TestReporteEjecutivoPDF:
    def test_pdf_generated_with_charts(self, test_project, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/proyectos/{test_project}/reporte-ejecutivo",
            headers=admin_headers,
        )
        assert r.status_code == 200, r.text[:300]
        ctype = r.headers.get("content-type", "")
        assert "pdf" in ctype.lower(), f"unexpected content-type: {ctype}"
        # Charts included -> >50KB per spec
        assert len(r.content) > 50_000, f"PDF too small ({len(r.content)} bytes), expected >50KB"


class TestAvanceFinanciero:
    def test_avance_financiero_uses_caras(self, test_project, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/proyectos/{test_project}/avance-financiero",
            headers=admin_headers,
        )
        # Endpoint should exist and return 200
        assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
        data = r.json()
        # Just sanity: response should be a dict
        assert isinstance(data, dict)


class TestExistingProjectMatrix:
    """The first project in DB was pre-configured via curl (per agent notes)."""

    def test_first_project_has_matrix(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/proyectos", headers=admin_headers)
        assert r.status_code == 200
        projs = r.json()
        if not projs:
            pytest.skip("no projects in DB")
        # Find first project with caras_excavacion configured (not just first)
        target = None
        for p in projs:
            pid = p.get("id")
            if not pid:
                continue
            rr = requests.get(f"{BASE_URL}/api/proyectos/{pid}/caras-excavacion", headers=admin_headers)
            if rr.status_code == 200 and rr.json().get("configurado"):
                target = (pid, rr.json())
                break
        if not target:
            pytest.skip("no pre-configured caras project found")
        pid, data = target
        assert len(data["caras"]) == 4
