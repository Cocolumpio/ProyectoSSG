"""
Test suite for E2E 3 Fases project and multi-phase system
Tests the 3-phase construction tracking (Excavación, Cimentación, Edificación)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://dron-topografia-dash.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@dron.mx"
ADMIN_PASSWORD = "admin123"

# Known project IDs
E2E_PROJECT_ID = "808bcba5-7792-492e-a2ee-fd9ff10e6e5e"  # Proyecto E2E 3 Fases Test
TORRE_CORP_ID = "d250ab6b-56d5-48e5-b114-f1c7f9c04c59"  # Torre Corporativa Demo


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestE2E3FasesProject:
    """Tests for the E2E 3 Fases Test project"""
    
    def test_project_exists(self, api_client):
        """Test that E2E 3 Fases project exists"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{E2E_PROJECT_ID}")
        assert response.status_code == 200, f"Project not found: {response.text}"
        
        data = response.json()
        assert data["nombre"] == "Proyecto E2E 3 Fases Test"
    
    def test_project_has_correct_avance(self, api_client):
        """Test that project has ~30.3% avance"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{E2E_PROJECT_ID}")
        assert response.status_code == 200
        
        data = response.json()
        avance = data.get("avance_actual", 0)
        # Should be around 30.28%
        assert 29 <= avance <= 32, f"Expected avance ~30.3%, got {avance}%"
    
    def test_project_has_3_phases_metrics(self, api_client):
        """Test that project has metrics for all 3 phases"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{E2E_PROJECT_ID}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check Excavación metrics
        assert "volumen_total_planeado" in data, "Missing excavation volume metric"
        assert data.get("volumen_total_planeado", 0) > 0, "Excavation volume should be > 0"
        
        # Check Cimentación metrics (pilas, anclas)
        assert "pilas_planeadas" in data, "Missing pilas metric"
        assert "anclas_planeadas" in data, "Missing anclas metric"
        
        # Check Edificación metrics (muros)
        assert "muros_planeados" in data, "Missing muros metric"
    
    def test_project_avances_semanales(self, api_client):
        """Test that project has weekly progress records"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{E2E_PROJECT_ID}/avances-semanales")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 2, f"Expected at least 2 weeks of progress, got {len(data)}"
        
        # Verify structure
        for avance in data:
            assert "semana" in avance
            assert "fecha" in avance
            assert "volumen_excavacion" in avance or "pilas_completadas" in avance


class TestTorreCorporativaComparaciones:
    """Tests for Torre Corporativa Demo comparisons"""
    
    def test_project_has_comparaciones(self, api_client):
        """Test that Torre Corporativa has comparisons"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{TORRE_CORP_ID}/comparaciones")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1, "Should have at least one comparison"
    
    def test_comparacion_structure(self, api_client):
        """Test comparison data structure"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{TORRE_CORP_ID}/comparaciones")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            comp = data[0]
            # Check required fields
            assert "id" in comp
            assert "pdf_nombre" in comp
            assert "fecha_comparacion" in comp
            assert "avance_general_dron" in comp or "metricas_dron" in comp
            assert "avance_general_residente" in comp or "metricas_residente" in comp
            # alerta_enviada is optional for older comparisons (added in recent update)
            # New comparisons will have this field


class TestProjectSelection:
    """Tests for project selection functionality"""
    
    def test_list_all_projects(self, api_client):
        """Test listing all projects"""
        response = api_client.get(f"{BASE_URL}/api/proyectos")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 6, f"Expected at least 6 projects, got {len(data)}"
        
        # Verify E2E project is in list
        project_names = [p["nombre"] for p in data]
        assert "Proyecto E2E 3 Fases Test" in project_names
    
    def test_project_details_endpoint(self, api_client):
        """Test getting individual project details"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{E2E_PROJECT_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == E2E_PROJECT_ID
        assert "coordenadas" in data  # For map display


class TestAvanceSemanalCreation:
    """Tests for creating new weekly progress"""
    
    def test_create_avance_semanal_validation(self, api_client):
        """Test that creating avance requires valid data"""
        # Try to create without required fields
        response = api_client.post(
            f"{BASE_URL}/api/proyectos/{E2E_PROJECT_ID}/avances-semanales",
            json={}
        )
        # Should fail validation
        assert response.status_code == 422, f"Expected 422 for invalid data, got {response.status_code}"
    
    def test_avance_semanal_duplicate_week_rejected(self, api_client):
        """Test that duplicate week numbers are rejected"""
        # Try to create week 1 which already exists
        response = api_client.post(
            f"{BASE_URL}/api/proyectos/{E2E_PROJECT_ID}/avances-semanales",
            json={
                "semana": 1,
                "fecha": "2026-03-08",
                "volumen_excavacion": 1000
            }
        )
        # Should fail because week 1 already exists
        assert response.status_code == 400, f"Expected 400 for duplicate week, got {response.status_code}"


class TestNavigationEndpoints:
    """Tests for navigation-related endpoints"""
    
    def test_estadisticas_resumen(self, api_client):
        """Test statistics summary endpoint"""
        response = api_client.get(f"{BASE_URL}/api/estadisticas/resumen")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_proyectos" in data
        assert "total_vuelos" in data
        assert "avance_promedio" in data
    
    def test_vuelos_endpoint(self, api_client):
        """Test vuelos listing endpoint"""
        response = api_client.get(f"{BASE_URL}/api/vuelos")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
