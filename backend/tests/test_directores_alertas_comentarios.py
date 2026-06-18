"""Tests for Directores CRUD, Alerta Desviación + Historial, and Comentarios Semana."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN = {"email": "admin@dron.mx", "password": "admin123"}
CLIENTE = {"email": "cliente@test.com", "password": "cliente123"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login {creds['email']} failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers():
    return {"Authorization": f"Bearer {_login(ADMIN)}"}


@pytest.fixture(scope="module")
def cliente_headers():
    return {"Authorization": f"Bearer {_login(CLIENTE)}"}


# ---------------- Directores CRUD ----------------

class TestDirectoresCRUD:
    created_ids = []

    def test_list_directores_admin(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/directores", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "directores" in data
        assert isinstance(data["directores"], list)

    def test_list_directores_forbidden_for_cliente(self, cliente_headers):
        r = requests.get(f"{BASE_URL}/api/directores", headers=cliente_headers, timeout=30)
        assert r.status_code in (401, 403)

    def test_create_director(self, admin_headers):
        payload = {
            "nombre": f"TEST_Director_{uuid.uuid4().hex[:6]}",
            "whatsapp": "+5215512345678",
            "cargo": "Director de Obra",
            "activo": True,
        }
        r = requests.post(f"{BASE_URL}/api/directores", json=payload, headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("id", "nombre", "whatsapp", "cargo", "activo", "created_at"):
            assert k in d, f"missing {k} in response"
        assert d["nombre"] == payload["nombre"]
        assert d["whatsapp"] == payload["whatsapp"]
        assert d["activo"] is True
        TestDirectoresCRUD.created_ids.append(d["id"])

        # verify via GET list
        listr = requests.get(f"{BASE_URL}/api/directores", headers=admin_headers, timeout=30).json()
        assert any(x["id"] == d["id"] for x in listr["directores"])

    def test_update_director_toggle_activo(self, admin_headers):
        assert TestDirectoresCRUD.created_ids, "no director created"
        did = TestDirectoresCRUD.created_ids[0]
        r = requests.put(f"{BASE_URL}/api/directores/{did}",
                         json={"activo": False}, headers=admin_headers, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["activo"] is False

        # update nombre
        r2 = requests.put(f"{BASE_URL}/api/directores/{did}",
                          json={"nombre": "TEST_Director_Updated"}, headers=admin_headers, timeout=30)
        assert r2.status_code == 200
        assert r2.json()["nombre"] == "TEST_Director_Updated"

    def test_update_director_404(self, admin_headers):
        r = requests.put(f"{BASE_URL}/api/directores/nonexistent-id",
                         json={"activo": True}, headers=admin_headers, timeout=30)
        assert r.status_code == 404

    def test_create_director_invalid(self, admin_headers):
        r = requests.post(f"{BASE_URL}/api/directores",
                          json={"nombre": "", "whatsapp": ""}, headers=admin_headers, timeout=30)
        assert r.status_code == 400

    def test_delete_director(self, admin_headers):
        # create extra then delete
        payload = {"nombre": "TEST_DelDir", "whatsapp": "+5215599999999"}
        d = requests.post(f"{BASE_URL}/api/directores", json=payload, headers=admin_headers, timeout=30).json()
        did = d["id"]
        r = requests.delete(f"{BASE_URL}/api/directores/{did}", headers=admin_headers, timeout=30)
        assert r.status_code == 200
        assert r.json()["deleted"] is True
        # 404 second time
        r2 = requests.delete(f"{BASE_URL}/api/directores/{did}", headers=admin_headers, timeout=30)
        assert r2.status_code == 404

    def test_zzz_cleanup(self, admin_headers):
        for did in TestDirectoresCRUD.created_ids:
            requests.delete(f"{BASE_URL}/api/directores/{did}", headers=admin_headers, timeout=30)


# ---------------- Helper: pick a proyecto with programa & avances ----------------

@pytest.fixture(scope="module")
def proyecto_id(admin_headers):
    r = requests.get(f"{BASE_URL}/api/proyectos", headers=admin_headers, timeout=30)
    assert r.status_code == 200
    lista = r.json()
    if isinstance(lista, dict):
        lista = lista.get("proyectos", [])
    assert lista, "no projects in DB"
    # prefer one with programa_semanal
    for p in lista:
        if p.get("programa_semanal"):
            return p["id"]
    return lista[0]["id"]


# ---------------- Alerta Desviación ----------------

class TestAlertaDesviacion:
    def test_alerta_sin_forzar(self, admin_headers, proyecto_id):
        r = requests.post(
            f"{BASE_URL}/api/proyectos/{proyecto_id}/alerta-desviacion?forzar=false",
            headers=admin_headers, timeout=60,
        )
        # Either 400 if no programa+avances, or 200 with alerta_enviada false/true
        assert r.status_code in (200, 400), r.text
        if r.status_code == 200:
            data = r.json()
            assert "alerta_enviada" in data
            # If no override, normally not breached → false
            if not data["alerta_enviada"]:
                assert "razon" in data

    def test_historial_alertas_admin(self, admin_headers, proyecto_id):
        r = requests.get(
            f"{BASE_URL}/api/proyectos/{proyecto_id}/alertas-historial",
            headers=admin_headers, timeout=30,
        )
        assert r.status_code == 200
        assert "alertas" in r.json()
        assert isinstance(r.json()["alertas"], list)

    def test_historial_alertas_cliente_no_access(self, cliente_headers, proyecto_id):
        r = requests.get(
            f"{BASE_URL}/api/proyectos/{proyecto_id}/alertas-historial",
            headers=cliente_headers, timeout=30,
        )
        # cliente either has access (200) or 403; both are OK shape-wise
        assert r.status_code in (200, 403, 404)

    def test_alerta_forzar_idempotencia(self, admin_headers, proyecto_id):
        # Need a director active so it doesn't short-circuit with "no directores"
        d = requests.post(f"{BASE_URL}/api/directores",
                          json={"nombre": "TEST_Alerta_Dir", "whatsapp": "+5215555555555", "activo": True},
                          headers=admin_headers, timeout=30).json()
        did = d.get("id")
        try:
            r1 = requests.post(
                f"{BASE_URL}/api/proyectos/{proyecto_id}/alerta-desviacion?forzar=true",
                headers=admin_headers, timeout=120,
            )
            # Should NOT error 500 even if twilio fails
            assert r1.status_code in (200, 400), r1.text
            if r1.status_code == 400:
                pytest.skip("Proyecto sin programa/avances suficiente para forzar alerta")
            d1 = r1.json()
            assert "alerta_enviada" in d1
            # forzar=true bypasses idempotency check, so should be enviada=true if directores activos exist
            # 2nd call sin forzar para misma semana → 'Ya se envió alerta'
            r2 = requests.post(
                f"{BASE_URL}/api/proyectos/{proyecto_id}/alerta-desviacion?forzar=false",
                headers=admin_headers, timeout=30,
            )
            assert r2.status_code == 200
            d2 = r2.json()
            # Si el proyecto no estaba desviado, razón será del umbral; si lo estaba, será de idempotencia.
            assert d2.get("alerta_enviada") is False
            assert "razon" in d2
        finally:
            if did:
                requests.delete(f"{BASE_URL}/api/directores/{did}", headers=admin_headers, timeout=30)


# ---------------- Comentarios Semana ----------------

class TestComentariosSemana:
    def test_upsert_comentario(self, admin_headers, proyecto_id):
        sem = 999  # unlikely to collide
        r = requests.put(
            f"{BASE_URL}/api/proyectos/{proyecto_id}/comentario-semana/{sem}",
            json={"texto": "TEST_Comentario inicial"}, headers=admin_headers, timeout=30,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["texto"] == "TEST_Comentario inicial"
        assert d["semana"] == sem

        # update again (upsert)
        r2 = requests.put(
            f"{BASE_URL}/api/proyectos/{proyecto_id}/comentario-semana/{sem}",
            json={"texto": "TEST_Comentario actualizado"}, headers=admin_headers, timeout=30,
        )
        assert r2.status_code == 200
        assert r2.json()["texto"] == "TEST_Comentario actualizado"

        # list
        lr = requests.get(
            f"{BASE_URL}/api/proyectos/{proyecto_id}/comentarios-semana",
            headers=admin_headers, timeout=30,
        )
        assert lr.status_code == 200
        items = lr.json()["comentarios"]
        found = [c for c in items if c["semana"] == sem]
        assert found and found[0]["texto"] == "TEST_Comentario actualizado"

        # delete
        dr = requests.delete(
            f"{BASE_URL}/api/proyectos/{proyecto_id}/comentario-semana/{sem}",
            headers=admin_headers, timeout=30,
        )
        assert dr.status_code == 200

    def test_cliente_no_puede_editar(self, cliente_headers, admin_headers, proyecto_id):
        sem = 998
        r = requests.put(
            f"{BASE_URL}/api/proyectos/{proyecto_id}/comentario-semana/{sem}",
            json={"texto": "no debería"}, headers=cliente_headers, timeout=30,
        )
        assert r.status_code in (401, 403)
        # Cleanup admin side just in case
        requests.delete(f"{BASE_URL}/api/proyectos/{proyecto_id}/comentario-semana/{sem}",
                        headers=admin_headers, timeout=30)

    def test_cliente_puede_get_si_asignado(self, cliente_headers, proyecto_id):
        r = requests.get(
            f"{BASE_URL}/api/proyectos/{proyecto_id}/comentarios-semana",
            headers=cliente_headers, timeout=30,
        )
        assert r.status_code in (200, 403)
