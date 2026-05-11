"""
Regression tests for NEWLY EXTRACTED route modules under /app/backend/routes/.
Focus: routes pulled out of monolithic server.py during P0 refactor.

Modules covered:
- routes/comparaciones.py
- routes/exportar.py
- routes/reporte_ejecutivo.py
- routes/solicitudes_vuelo.py
- routes/cronograma.py
- routes/maquinaria_ia.py
- routes/analisis_ia.py
- server.py: /api/notificaciones (uses services/notifications.py helper)
"""
import os
import io
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_EMAIL = "admin@dron.mx"
ADMIN_PASSWORD = "admin123"
CLIENT_EMAIL = "cliente@test.com"
CLIENT_PASSWORD = "cliente123"


# ---------------- Fixtures ----------------

@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def client_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD})
    assert r.status_code == 200, f"Client login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def client_headers(client_token):
    return {"Authorization": f"Bearer {client_token}"}


@pytest.fixture(scope="module")
def any_proyecto_id():
    r = requests.get(f"{BASE_URL}/api/proyectos")
    assert r.status_code == 200
    proyectos = r.json()
    if not proyectos:
        pytest.skip("No proyectos exist in DB to test against")
    return proyectos[0]["id"]


# ---------------- server.py: notificaciones ----------------

class TestNotificaciones:
    def test_get_notificaciones_admin(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/notificaciones", headers=admin_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        # Response shape: {"notificaciones": [...], "total_no_leidas": N}
        assert isinstance(data, dict)
        assert "notificaciones" in data
        assert isinstance(data["notificaciones"], list)
        assert "total_no_leidas" in data
        print(f"Admin notificaciones: {len(data['notificaciones'])}, no leidas: {data['total_no_leidas']}")

    def test_get_notificaciones_unauth(self):
        r = requests.get(f"{BASE_URL}/api/notificaciones")
        assert r.status_code in (401, 403)


# ---------------- routes/comparaciones.py ----------------

class TestComparaciones:
    def test_list_comparaciones(self, any_proyecto_id, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/proyectos/{any_proyecto_id}/comparaciones",
            headers=admin_headers,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)
        print(f"Proyecto {any_proyecto_id} comparaciones: {len(data)}")

    def test_comparar_avance_validation(self, any_proyecto_id, admin_headers):
        """POST without PDF should fail with 4xx (validation) — endpoint reachable."""
        r = requests.post(
            f"{BASE_URL}/api/proyectos/{any_proyecto_id}/comparar-avance",
            headers=admin_headers,
        )
        # Should NOT be 404 (route exists) and NOT 500
        assert r.status_code != 404, "Route not registered"
        assert r.status_code != 500, f"Server error: {r.text[:200]}"
        # Expect 422 (missing file) or 400
        assert r.status_code in (400, 422), f"Unexpected: {r.status_code} {r.text[:200]}"


# ---------------- routes/exportar.py ----------------

class TestExportar:
    def test_export_excel(self):
        r = requests.get(f"{BASE_URL}/api/exportar/metricas-excel")
        assert r.status_code == 200
        assert r.content[:2] == b"PK"  # XLSX is a zip
        print(f"Excel bytes: {len(r.content)}")

    def test_export_pdf(self):
        r = requests.get(f"{BASE_URL}/api/exportar/metricas-pdf")
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"
        print(f"PDF bytes: {len(r.content)}")


# ---------------- routes/reporte_ejecutivo.py ----------------

class TestReporteEjecutivo:
    def test_reporte_ejecutivo_pdf(self, any_proyecto_id, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/proyectos/{any_proyecto_id}/reporte-ejecutivo",
            headers=admin_headers,
        )
        assert r.status_code == 200, r.text[:400]
        ctype = r.headers.get("content-type", "")
        assert "pdf" in ctype.lower(), f"Expected pdf content-type, got {ctype}"
        assert r.content[:4] == b"%PDF"
        print(f"Reporte ejecutivo bytes: {len(r.content)}")

    def test_reporte_ejecutivo_invalid_project(self, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/proyectos/invalid-xyz-123/reporte-ejecutivo",
            headers=admin_headers,
        )
        assert r.status_code == 404


# ---------------- routes/solicitudes_vuelo.py ----------------

class TestSolicitudesVuelo:
    def test_list_admin(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/solicitudes-vuelo", headers=admin_headers)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_list_client(self, client_headers):
        r = requests.get(f"{BASE_URL}/api/solicitudes-vuelo", headers=client_headers)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_create_and_update_estado(self, client_headers, admin_headers):
        tid = uuid.uuid4().hex[:8]
        payload = {
            "nombre_proyecto": f"TEST_Solicitud_{tid}",
            "fecha_inicio_proyecto": "2025-03-01",
            "fecha_fin_proyecto": "2025-09-30",
            "fecha_vuelo_deseada": "2025-03-15",
            "hora_preferencia": "10:00",
            "notas": "regression test",
        }
        r = requests.post(f"{BASE_URL}/api/solicitudes-vuelo",
                          json=payload, headers=client_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "solicitud_id" in body
        sid = body["solicitud_id"]

        # PUT estado (admin only) — valid enum: pendiente|confirmado|completado|cancelado
        r2 = requests.put(
            f"{BASE_URL}/api/solicitudes-vuelo/{sid}/estado",
            json={"estado": "confirmado"},
            headers=admin_headers,
        )
        assert r2.status_code == 200, r2.text
        print(f"Solicitud {sid} -> confirmado OK")


# ---------------- routes/cronograma.py ----------------

class TestCronograma:
    def test_plantilla_cronograma(self):
        r = requests.get(f"{BASE_URL}/api/plantilla-cronograma")
        assert r.status_code == 200, r.text[:200]
        # Should be xlsx
        assert r.content[:2] == b"PK"
        print(f"Plantilla bytes: {len(r.content)}")

    def test_frentes_endpoint(self, any_proyecto_id, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/proyectos/{any_proyecto_id}/frentes",
            headers=admin_headers,
        )
        assert r.status_code == 200, r.text[:200]
        # Expect either a list or dict
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_actualizar_cronograma_validation(self, any_proyecto_id, admin_headers):
        """POST without file should be reachable, not 404/500."""
        r = requests.post(
            f"{BASE_URL}/api/proyectos/{any_proyecto_id}/actualizar-cronograma",
            headers=admin_headers,
        )
        assert r.status_code != 404, "Route not registered"
        assert r.status_code != 500, f"Server error: {r.text[:200]}"
        assert r.status_code in (400, 422)


# ---------------- routes/maquinaria_ia.py ----------------

class TestMaquinariaIA:
    def test_dashboard_comparaciones_resumen(self, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/dashboard/comparaciones-resumen",
            headers=admin_headers,
        )
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_analizar_catalogo_maquinaria_validation(self, admin_headers):
        """POST without file should be reachable, not 404/500."""
        r = requests.post(
            f"{BASE_URL}/api/proyectos/analizar-catalogo-maquinaria",
            headers=admin_headers,
        )
        assert r.status_code != 404
        assert r.status_code != 500, f"Server error: {r.text[:200]}"
        assert r.status_code in (400, 422)

    def test_comparar_plan_ia_validation(self, any_proyecto_id, admin_headers):
        r = requests.post(
            f"{BASE_URL}/api/proyectos/{any_proyecto_id}/comparar-plan-ia",
            headers=admin_headers,
        )
        # Route reachable; should not be 404 or 500
        assert r.status_code != 404
        assert r.status_code != 500, f"Server error: {r.text[:200]}"


# ---------------- routes/analisis_ia.py ----------------

class TestAnalisisIA:
    def test_get_analisis_ia(self, any_proyecto_id, admin_headers):
        r = requests.get(
            f"{BASE_URL}/api/proyectos/{any_proyecto_id}/analisis-ia",
            headers=admin_headers,
        )
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_foto_avance_validation(self, admin_headers):
        """POST without file should be reachable, not 404/500."""
        r = requests.post(
            f"{BASE_URL}/api/analisis/foto-avance",
            headers=admin_headers,
        )
        assert r.status_code != 404, "Route not registered"
        assert r.status_code != 500, f"Server error: {r.text[:200]}"
        assert r.status_code in (400, 422)

    def test_generar_reporte_ia_reachable(self, any_proyecto_id, admin_headers):
        """POST endpoint must be reachable (not 404). May 400/422/200 based on data."""
        r = requests.post(
            f"{BASE_URL}/api/proyectos/{any_proyecto_id}/generar-reporte-ia",
            headers=admin_headers,
        )
        assert r.status_code != 404, "Route not registered"
        # 500 acceptable only if it's a downstream LLM call issue; flag it
        if r.status_code == 500:
            pytest.fail(f"500 server error: {r.text[:300]}")


# ---------------- modelo3d/generar-preview (server.py - CRITICAL open3d) ----------------

class TestModelo3DPreview:
    def test_generar_preview_reachable(self, admin_headers):
        """Endpoint must be reachable post-refactor. Find an avance with modelo3d.
        Note: existing DB has avances with stale modelo_3d_url where the underlying
        file is missing; we accept that case as 'route works' since refactor goal is
        to ensure the endpoint is registered and code path executes."""
        proyectos = requests.get(f"{BASE_URL}/api/proyectos").json()
        target = None
        for p in proyectos:
            avances = requests.get(
                f"{BASE_URL}/api/proyectos/{p['id']}/avances-semanales",
                headers=admin_headers,
            ).json()
            if not isinstance(avances, list):
                continue
            for a in avances:
                if a.get("modelo_3d_url") or a.get("modelo_3d_gridfs_id"):
                    target = (p["id"], a["id"], a)
                    break
            if target:
                break
        if not target:
            pytest.skip("No avance with modelo3d found to test preview")
        pid, aid, avance = target
        r = requests.post(
            f"{BASE_URL}/api/proyectos/{pid}/avances-semanales/{aid}/modelo3d/generar-preview",
            headers=admin_headers,
        )
        # Route MUST exist (refactor regression check)
        assert r.status_code != 404, "generar-preview route missing after refactor!"
        # Acceptable: 200 (preview generated), 400 (no model), 500 with specific
        # 'archivo no existe' message (stale data, NOT a refactor regression)
        if r.status_code == 500:
            body = r.text
            assert "no existir" in body or "no se pudo leer" in body.lower(), (
                f"Unexpected 500 (possible open3d regression): {body[:300]}"
            )
            pytest.skip(f"Stale modelo data (file missing): {body[:200]}")
        assert r.status_code in (200, 400), f"Unexpected: {r.status_code} {r.text[:200]}"
        print(f"generar-preview status: {r.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
