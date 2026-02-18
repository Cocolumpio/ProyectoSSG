"""
Backend API Tests for DrON Topografía - Post-Refactoring Verification
Tests all endpoints after refactoring to verify functionality is intact.
Modules tested: core/config.py, services/helpers.py, services/email.py
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@dron.mx"
ADMIN_PASSWORD = "admin123"
CLIENT_EMAIL = "cliente@test.com"
CLIENT_PASSWORD = "cliente123"


class TestAPIRoot:
    """Test basic API connectivity"""
    
    def test_api_root_returns_200(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"API root: {data['message']}")


class TestAuthenticationAfterRefactor:
    """Test auth endpoints after refactoring to core/config.py"""
    
    def test_admin_login(self):
        """Test admin login - verify auth functions work from core/config.py"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify token structure
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        
        # Verify user data
        assert "user" in data
        user = data["user"]
        assert user["email"] == ADMIN_EMAIL
        assert user["rol"] == "admin"
        print(f"Admin login OK: {user['nombre']}")
    
    def test_client_login(self):
        """Test client login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        user = data["user"]
        assert user["email"] == CLIENT_EMAIL
        assert user["rol"] == "client"
        print(f"Client login OK: {user['nombre']}")
    
    def test_invalid_login(self):
        """Test invalid credentials are rejected"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        print("Invalid login correctly rejected")
    
    def test_auth_me_with_token(self):
        """Test /auth/me endpoint with valid token"""
        # Login first
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_resp.json()["access_token"]
        
        # Get user info
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == ADMIN_EMAIL
        print(f"Auth/me OK: {data['nombre']}")


class TestProyectosEndpoints:
    """Test proyectos endpoints"""
    
    def test_list_proyectos(self):
        """Test GET /api/proyectos"""
        response = requests.get(f"{BASE_URL}/api/proyectos")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} proyectos")
        
        # Verify project structure
        if len(data) > 0:
            proyecto = data[0]
            assert "id" in proyecto
            assert "nombre" in proyecto
            assert "ubicacion" in proyecto
            assert "coordenadas" in proyecto
            assert "avance_actual" in proyecto
            print(f"First project: {proyecto['nombre']}")
    
    def test_get_proyecto_by_id(self):
        """Test GET /api/proyectos/{id}"""
        # First get list to find a valid ID
        list_resp = requests.get(f"{BASE_URL}/api/proyectos")
        proyectos = list_resp.json()
        
        if len(proyectos) == 0:
            pytest.skip("No projects to test")
        
        proyecto_id = proyectos[0]["id"]
        response = requests.get(f"{BASE_URL}/api/proyectos/{proyecto_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == proyecto_id
        print(f"Got project: {data['nombre']}")
    
    def test_get_proyecto_not_found(self):
        """Test GET /api/proyectos/{invalid_id} returns 404"""
        response = requests.get(f"{BASE_URL}/api/proyectos/invalid-id-12345")
        assert response.status_code == 404
        print("Invalid project ID correctly returns 404")
    
    def test_create_and_delete_proyecto(self):
        """Test POST and DELETE /api/proyectos"""
        test_id = uuid.uuid4().hex[:8]
        new_proyecto = {
            "nombre": f"TEST_Proyecto_{test_id}",
            "ubicacion": "Test Location",
            "coordenadas": {"lat": 20.6597, "lng": -103.3496},
            "fecha_inicio": "2025-01-01",
            "fecha_fin_planeada": "2025-12-31",
            "descripcion": "Test project for pytest"
        }
        
        # Create
        create_resp = requests.post(f"{BASE_URL}/api/proyectos", json=new_proyecto)
        assert create_resp.status_code == 200
        created = create_resp.json()
        assert created["nombre"] == new_proyecto["nombre"]
        proyecto_id = created["id"]
        print(f"Created project: {created['nombre']}")
        
        # Verify it exists
        get_resp = requests.get(f"{BASE_URL}/api/proyectos/{proyecto_id}")
        assert get_resp.status_code == 200
        
        # Delete
        delete_resp = requests.delete(f"{BASE_URL}/api/proyectos/{proyecto_id}")
        assert delete_resp.status_code == 200
        print(f"Deleted project: {proyecto_id}")
        
        # Verify it's gone
        verify_resp = requests.get(f"{BASE_URL}/api/proyectos/{proyecto_id}")
        assert verify_resp.status_code == 404


class TestEstadisticasEndpoint:
    """Test estadisticas endpoint"""
    
    def test_get_estadisticas_resumen(self):
        """Test GET /api/estadisticas/resumen"""
        response = requests.get(f"{BASE_URL}/api/estadisticas/resumen")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "total_proyectos" in data
        assert "total_vuelos" in data
        assert "avance_promedio" in data
        assert "volumetria_total" in data
        
        # Verify types
        assert isinstance(data["total_proyectos"], int)
        assert isinstance(data["total_vuelos"], int)
        assert isinstance(data["avance_promedio"], (int, float))
        
        print(f"Estadisticas: {data['total_proyectos']} proyectos, {data['total_vuelos']} vuelos, {data['avance_promedio']}% avance")


class TestAvancesSemanales:
    """Test avances semanales endpoints - uses recalcular_avance_proyecto from services/helpers.py"""
    
    def test_list_avances_semanales(self):
        """Test GET /api/proyectos/{id}/avances-semanales"""
        # Get a project first
        list_resp = requests.get(f"{BASE_URL}/api/proyectos")
        proyectos = list_resp.json()
        
        if len(proyectos) == 0:
            pytest.skip("No projects to test")
        
        proyecto_id = proyectos[0]["id"]
        response = requests.get(f"{BASE_URL}/api/proyectos/{proyecto_id}/avances-semanales")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Project {proyectos[0]['nombre']} has {len(data)} avances semanales")
    
    def test_create_avance_semanal(self):
        """Test POST /api/proyectos/{id}/avances-semanales"""
        # Create a test project first
        test_id = uuid.uuid4().hex[:8]
        new_proyecto = {
            "nombre": f"TEST_AvanceProject_{test_id}",
            "ubicacion": "Test Location",
            "coordenadas": {"lat": 20.6597, "lng": -103.3496},
            "fecha_inicio": "2025-01-01",
            "fecha_fin_planeada": "2025-12-31",
            "volumen_total_planeado": 1000.0
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/proyectos", json=new_proyecto)
        assert create_resp.status_code == 200
        proyecto_id = create_resp.json()["id"]
        
        try:
            # Create avance semanal
            avance_data = {
                "semana": 1,
                "fecha": "2025-01-15",
                "descripcion": "Test avance semanal",
                "volumen_excavacion": 100.0
            }
            
            avance_resp = requests.post(
                f"{BASE_URL}/api/proyectos/{proyecto_id}/avances-semanales",
                json=avance_data
            )
            assert avance_resp.status_code == 200
            avance = avance_resp.json()
            assert avance["semana"] == 1
            assert avance["volumen_excavacion"] == 100.0
            print(f"Created avance semanal: semana {avance['semana']}")
            
            # Verify project avance was recalculated (uses services/helpers.py)
            proyecto_resp = requests.get(f"{BASE_URL}/api/proyectos/{proyecto_id}")
            proyecto = proyecto_resp.json()
            # 100/1000 = 10% avance
            assert proyecto["avance_actual"] == 10.0
            print(f"Project avance recalculated: {proyecto['avance_actual']}%")
            
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/proyectos/{proyecto_id}")


class TestExportEndpoints:
    """Test export endpoints"""
    
    def test_export_excel(self):
        """Test GET /api/exportar/metricas-excel"""
        response = requests.get(f"{BASE_URL}/api/exportar/metricas-excel")
        assert response.status_code == 200
        
        # Verify content type
        content_type = response.headers.get("content-type", "")
        assert "spreadsheet" in content_type or "excel" in content_type.lower()
        
        # Verify it's a valid XLSX (starts with PK - ZIP format)
        assert response.content[:2] == b'PK'
        print(f"Excel export OK: {len(response.content)} bytes")
    
    def test_export_pdf(self):
        """Test GET /api/exportar/metricas-pdf"""
        response = requests.get(f"{BASE_URL}/api/exportar/metricas-pdf")
        assert response.status_code == 200
        
        # Verify content type
        content_type = response.headers.get("content-type", "")
        assert "pdf" in content_type.lower()
        
        # Verify it's a valid PDF (starts with %PDF)
        assert response.content[:4] == b'%PDF'
        print(f"PDF export OK: {len(response.content)} bytes")


class TestSolicitudesVuelo:
    """Test solicitudes de vuelo endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def client_token(self):
        """Get client token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_list_solicitudes_as_admin(self, admin_token):
        """Test GET /api/solicitudes-vuelo as admin"""
        response = requests.get(f"{BASE_URL}/api/solicitudes-vuelo", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Admin sees {len(data)} solicitudes")
    
    def test_list_solicitudes_as_client(self, client_token):
        """Test GET /api/solicitudes-vuelo as client"""
        response = requests.get(f"{BASE_URL}/api/solicitudes-vuelo", headers={
            "Authorization": f"Bearer {client_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Client sees {len(data)} of their solicitudes")
    
    def test_create_solicitud_as_client(self, client_token):
        """Test POST /api/solicitudes-vuelo as client"""
        test_id = uuid.uuid4().hex[:8]
        solicitud_data = {
            "nombre_proyecto": f"TEST_SolicitudProject_{test_id}",
            "fecha_inicio_proyecto": "2025-03-01",
            "fecha_fin_proyecto": "2025-09-30",
            "fecha_vuelo_deseada": "2025-03-15",
            "hora_preferencia": "10:00",
            "notas": "Test solicitud from pytest"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/solicitudes-vuelo",
            json=solicitud_data,
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["success", "partial"]
        assert "solicitud_id" in data
        print(f"Created solicitud: {data['solicitud_id']}")


class TestVuelosEndpoints:
    """Test vuelos endpoints"""
    
    def test_list_vuelos(self):
        """Test GET /api/vuelos"""
        response = requests.get(f"{BASE_URL}/api/vuelos")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} vuelos")
    
    def test_create_and_delete_vuelo(self):
        """Test POST and DELETE /api/vuelos"""
        # First get a project ID
        proyectos_resp = requests.get(f"{BASE_URL}/api/proyectos")
        proyectos = proyectos_resp.json()
        
        if len(proyectos) == 0:
            pytest.skip("No projects to test with")
        
        proyecto_id = proyectos[0]["id"]
        
        # Create vuelo
        vuelo_data = {
            "proyecto_id": proyecto_id,
            "fecha_vuelo": "2025-01-20",
            "duracion_minutos": 45,
            "area_cubierta": 5000.0,
            "num_imagenes": 150,
            "notas": "Test vuelo from pytest"
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/vuelos", json=vuelo_data)
        assert create_resp.status_code == 200
        vuelo = create_resp.json()
        vuelo_id = vuelo["id"]
        print(f"Created vuelo: {vuelo_id}")
        
        # Verify it exists
        get_resp = requests.get(f"{BASE_URL}/api/vuelos/{vuelo_id}")
        assert get_resp.status_code == 200
        
        # Delete
        delete_resp = requests.delete(f"{BASE_URL}/api/vuelos/{vuelo_id}")
        assert delete_resp.status_code == 200
        print(f"Deleted vuelo: {vuelo_id}")


class TestUsersEndpoint:
    """Test users management endpoints (admin only)"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def client_token(self):
        """Get client token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_admin_can_list_users(self, admin_token):
        """Test GET /api/auth/users as admin"""
        response = requests.get(f"{BASE_URL}/api/auth/users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # At least admin and client
        
        # Verify no password_hash in response
        for user in data:
            assert "password_hash" not in user
        print(f"Admin can see {len(data)} users")
    
    def test_client_cannot_list_users(self, client_token):
        """Test GET /api/auth/users as client - should be forbidden"""
        response = requests.get(f"{BASE_URL}/api/auth/users", headers={
            "Authorization": f"Bearer {client_token}"
        })
        assert response.status_code == 403
        print("Client correctly denied from listing users")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
