"""
Test suite for Cronograma Import and Activity Types Detection
Tests the Excel parser, project creation from cronograma, and activity type metrics
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@dron.mx"
ADMIN_PASSWORD = "admin123"
CLIENT_EMAIL = "cliente@test.com"
CLIENT_PASSWORD = "cliente123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def client_token():
    """Get client authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": CLIENT_EMAIL,
        "password": CLIENT_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Client authentication failed")


class TestCronogramaImport:
    """Tests for /api/proyectos/importar-cronograma endpoint"""
    
    def test_importar_cronograma_success(self):
        """Test importing Excel cronograma file"""
        # Use the test file
        test_file_path = "/app/backend/uploads/cronograma_tipos_test.xlsx"
        
        with open(test_file_path, 'rb') as f:
            response = requests.post(
                f"{BASE_URL}/api/proyectos/importar-cronograma",
                files={"file": ("cronograma_test.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify success
        assert data.get("success") == True
        
        # Verify frentes were parsed
        assert "frentes" in data
        assert len(data["frentes"]) > 0
        
        # Verify resumen contains activity types
        resumen = data.get("resumen", {})
        assert "tipos_actividades" in resumen
        assert isinstance(resumen["tipos_actividades"], list)
        
        # Verify activity types were detected
        tipos = resumen["tipos_actividades"]
        assert "pilas" in tipos, "Should detect 'pilas' activity type"
        assert "excavacion" in tipos, "Should detect 'excavacion' activity type"
        assert "muros" in tipos, "Should detect 'muros' activity type"
        assert "anclas" in tipos, "Should detect 'anclas' activity type"
        
        # Verify metrics
        assert resumen.get("total_pilas", 0) > 0, "Should have pilas count"
        assert resumen.get("total_muros", 0) > 0, "Should have muros count"
        assert resumen.get("total_anclas", 0) > 0, "Should have anclas count"
        assert resumen.get("total_excavacion", 0) > 0, "Should have excavacion volume"
    
    def test_importar_cronograma_invalid_file(self):
        """Test importing invalid file type"""
        response = requests.post(
            f"{BASE_URL}/api/proyectos/importar-cronograma",
            files={"file": ("test.txt", b"invalid content", "text/plain")}
        )
        
        assert response.status_code == 400
        assert "Excel" in response.json().get("detail", "")


class TestCrearProyectoDesdeCronograma:
    """Tests for /api/proyectos/crear-desde-cronograma endpoint"""
    
    def test_crear_proyecto_con_tipos_actividades(self):
        """Test creating project with activity types from cronograma"""
        payload = {
            "nombre": "TEST_Proyecto_Cronograma_API",
            "ubicacion": "Test Location",
            "direccion": "Test Address 123",
            "coordenadas": {"lat": 20.6597, "lng": -103.3496},
            "frentes": [
                {
                    "nombre": "FRENTE TEST",
                    "actividades": [
                        {"descripcion": "Pilas test", "cantidad": 20, "tipo": "pilas"}
                    ]
                }
            ],
            "resumen": {
                "total_frentes": 1,
                "total_pilas": 20,
                "total_muros": 5,
                "total_anclas": 25,
                "total_excavacion": 300,
                "tipos_actividades": ["pilas", "muros", "anclas", "excavacion"],
                "semanas_estimadas": 6,
                "fecha_inicio": "2026-03-01",
                "fecha_fin": "2026-04-15",
                "semanas_excavacion": 2,
                "semanas_pilas": 2,
                "semanas_muros": 1
            },
            "descripcion": "Test project from API"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/proyectos/crear-desde-cronograma",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") == True
        assert "proyecto_id" in data
        
        proyecto_id = data["proyecto_id"]
        
        # Verify project was created with correct data
        get_response = requests.get(f"{BASE_URL}/api/proyectos/{proyecto_id}")
        assert get_response.status_code == 200
        
        proyecto = get_response.json()
        
        # Verify actividades_tipo was saved
        assert "actividades_tipo" in proyecto
        assert "pilas" in proyecto["actividades_tipo"]
        assert "muros" in proyecto["actividades_tipo"]
        assert "anclas" in proyecto["actividades_tipo"]
        assert "excavacion" in proyecto["actividades_tipo"]
        
        # Verify metrics were saved
        assert proyecto["pilas_planeadas"] == 20
        assert proyecto["muros_planeados"] == 5
        assert proyecto["anclas_planeadas"] == 25
        assert proyecto["volumen_total_planeado"] == 300
        
        # Verify semanas were saved
        assert proyecto["semanas_planeadas"] == 6
        assert proyecto["semanas_excavacion"] == 2
        assert proyecto["semanas_pilas"] == 2
        assert proyecto["semanas_muros"] == 1
        
        # Cleanup - delete test project
        requests.delete(f"{BASE_URL}/api/proyectos/{proyecto_id}")


class TestProyectoActividadesTipo:
    """Tests for project activity types and metrics"""
    
    def test_proyecto_update_actividades_tipo(self):
        """Test updating project with activity types"""
        # First create a project
        create_response = requests.post(f"{BASE_URL}/api/proyectos", json={
            "nombre": "TEST_Update_Tipos",
            "ubicacion": "Test",
            "coordenadas": {"lat": 20.0, "lng": -103.0},
            "fecha_inicio": "2026-01-01",
            "fecha_fin_planeada": "2026-06-01"
        })
        
        assert create_response.status_code == 200
        proyecto_id = create_response.json()["id"]
        
        # Update with activity types
        update_response = requests.put(f"{BASE_URL}/api/proyectos/{proyecto_id}", json={
            "actividades_tipo": ["pilas", "muros"],
            "pilas_planeadas": 50,
            "muros_planeados": 20
        })
        
        assert update_response.status_code == 200
        updated = update_response.json()
        
        assert "pilas" in updated["actividades_tipo"]
        assert "muros" in updated["actividades_tipo"]
        assert updated["pilas_planeadas"] == 50
        assert updated["muros_planeados"] == 20
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/proyectos/{proyecto_id}")
    
    def test_proyecto_metricas_ejecutadas(self):
        """Test updating executed metrics"""
        # Create project
        create_response = requests.post(f"{BASE_URL}/api/proyectos", json={
            "nombre": "TEST_Metricas_Ejecutadas",
            "ubicacion": "Test",
            "coordenadas": {"lat": 20.0, "lng": -103.0},
            "fecha_inicio": "2026-01-01",
            "fecha_fin_planeada": "2026-06-01",
            "actividades_tipo": ["pilas", "anclas"],
            "pilas_planeadas": 100,
            "anclas_planeadas": 100
        })
        
        assert create_response.status_code == 200
        proyecto_id = create_response.json()["id"]
        
        # Update executed metrics
        update_response = requests.put(f"{BASE_URL}/api/proyectos/{proyecto_id}", json={
            "pilas_ejecutadas": 30,
            "anclas_ejecutadas": 25
        })
        
        assert update_response.status_code == 200
        updated = update_response.json()
        
        assert updated["pilas_ejecutadas"] == 30
        assert updated["anclas_ejecutadas"] == 25
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/proyectos/{proyecto_id}")


class TestDashboardEstadisticas:
    """Tests for dashboard statistics endpoint"""
    
    def test_estadisticas_endpoint(self):
        """Test /api/estadisticas returns correct data"""
        response = requests.get(f"{BASE_URL}/api/estadisticas")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_proyectos" in data
        assert "total_vuelos" in data
        assert "avance_promedio" in data
        assert isinstance(data["total_proyectos"], int)
        assert isinstance(data["avance_promedio"], (int, float))


class TestPlantillaCronograma:
    """Tests for cronograma template download"""
    
    def test_descargar_plantilla(self):
        """Test downloading cronograma template"""
        response = requests.get(f"{BASE_URL}/api/plantilla-cronograma")
        
        assert response.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers.get("content-type", "")


class TestAuthEndpoints:
    """Tests for authentication endpoints"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["user"]["rol"] == "admin"
        assert data["user"]["email"] == ADMIN_EMAIL
    
    def test_client_login(self):
        """Test client login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["user"]["rol"] == "client"
    
    def test_invalid_login(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401


class TestProyectosAPI:
    """Tests for proyectos CRUD operations"""
    
    def test_listar_proyectos(self):
        """Test listing all projects"""
        response = requests.get(f"{BASE_URL}/api/proyectos")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_crear_y_obtener_proyecto(self):
        """Test creating and retrieving a project"""
        # Create
        create_response = requests.post(f"{BASE_URL}/api/proyectos", json={
            "nombre": "TEST_CRUD_Proyecto",
            "ubicacion": "Test Location",
            "coordenadas": {"lat": 20.0, "lng": -103.0},
            "fecha_inicio": "2026-01-01",
            "fecha_fin_planeada": "2026-12-31"
        })
        
        assert create_response.status_code == 200
        proyecto = create_response.json()
        proyecto_id = proyecto["id"]
        
        # Get
        get_response = requests.get(f"{BASE_URL}/api/proyectos/{proyecto_id}")
        assert get_response.status_code == 200
        assert get_response.json()["nombre"] == "TEST_CRUD_Proyecto"
        
        # Cleanup
        delete_response = requests.delete(f"{BASE_URL}/api/proyectos/{proyecto_id}")
        assert delete_response.status_code == 200


class TestAvancesSemanales:
    """Tests for avances semanales endpoints"""
    
    def test_listar_avances_semanales(self):
        """Test listing weekly progress for a project"""
        # First get a project
        proyectos = requests.get(f"{BASE_URL}/api/proyectos").json()
        
        if proyectos:
            proyecto_id = proyectos[0]["id"]
            response = requests.get(f"{BASE_URL}/api/proyectos/{proyecto_id}/avances-semanales")
            
            assert response.status_code == 200
            assert isinstance(response.json(), list)


# Cleanup test data after all tests
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data():
    """Cleanup TEST_ prefixed projects after tests"""
    yield
    
    # Get all projects
    response = requests.get(f"{BASE_URL}/api/proyectos")
    if response.status_code == 200:
        proyectos = response.json()
        for p in proyectos:
            if p.get("nombre", "").startswith("TEST_"):
                requests.delete(f"{BASE_URL}/api/proyectos/{p['id']}")
