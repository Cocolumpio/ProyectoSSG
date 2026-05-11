"""
Test suite for Comparación de Avances feature
Tests the comparison between drone data and resident PDF reports
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://dron-topografia-dash.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@dron.mx"
ADMIN_PASSWORD = "admin123"

# Known project ID (Acuarela)
ACUARELA_PROJECT_ID = "aa547723-9d64-4d4d-8b6a-ef615941ee05"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_token(api_client):
    """Get authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestComparacionAvanceEndpoints:
    """Tests for the comparison feature endpoints"""
    
    def test_get_comparaciones_endpoint_exists(self, api_client):
        """Test that GET /proyectos/{id}/comparaciones endpoint exists"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparaciones")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
    
    def test_get_comparaciones_returns_existing_data(self, api_client):
        """Test that existing comparisons are returned"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparaciones")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1, "Should have at least one comparison (from previous test)"
        
        # Verify structure of comparison object
        if len(data) > 0:
            comp = data[0]
            assert "id" in comp, "Comparison should have id"
            assert "proyecto_id" in comp, "Comparison should have proyecto_id"
            assert "pdf_nombre" in comp, "Comparison should have pdf_nombre"
            assert "fecha_comparacion" in comp, "Comparison should have fecha_comparacion"
            assert "metricas_dron" in comp, "Comparison should have metricas_dron"
            assert "comparaciones" in comp, "Comparison should have comparaciones list"
    
    def test_get_comparaciones_for_nonexistent_project(self, api_client):
        """Test that nonexistent project returns empty list or 404"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/nonexistent-id/comparaciones")
        # Should return empty list or 404
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert response.json() == []
    
    def test_comparar_avance_endpoint_requires_pdf(self, api_client):
        """Test that POST /proyectos/{id}/comparar-avance requires a PDF file"""
        # Try to post without file
        response = api_client.post(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparar-avance")
        # Should fail with 422 (validation error) since file is required
        assert response.status_code == 422, f"Expected 422 for missing file, got {response.status_code}"
    
    def test_comparar_avance_rejects_non_pdf(self, api_client):
        """Test that non-PDF files are rejected"""
        # Create a fake text file
        files = {'file': ('test.txt', b'This is not a PDF', 'text/plain')}
        
        # Remove Content-Type header for multipart
        headers = {k: v for k, v in api_client.headers.items() if k.lower() != 'content-type'}
        
        response = requests.post(
            f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparar-avance",
            files=files,
            headers=headers
        )
        assert response.status_code == 400, f"Expected 400 for non-PDF, got {response.status_code}"
        assert "PDF" in response.json().get("detail", "")


class TestAvancesSemanalesEndpoints:
    """Tests for weekly progress endpoints used by comparison feature"""
    
    def test_get_avances_semanales(self, api_client):
        """Test that avances semanales endpoint works"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/avances-semanales")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_avances_semanales_structure(self, api_client):
        """Test structure of avances semanales"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/avances-semanales")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            avance = data[0]
            assert "id" in avance
            assert "proyecto_id" in avance
            assert "semana" in avance
            assert "fecha" in avance


class TestProyectoEndpoints:
    """Tests for project endpoints used by comparison feature"""
    
    def test_get_proyecto_details(self, api_client):
        """Test getting project details"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == ACUARELA_PROJECT_ID
        assert "nombre" in data
        assert "avance_actual" in data
    
    def test_proyecto_has_metrics_for_comparison(self, api_client):
        """Test that project has metrics needed for comparison"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}")
        assert response.status_code == 200
        
        data = response.json()
        # Check for metrics used in comparison
        assert "volumen_total_planeado" in data or "pilas_planeadas" in data or "muros_planeados" in data


class TestAuthEndpoints:
    """Tests for authentication endpoints"""
    
    def test_login_success(self, api_client):
        """Test successful login"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
    
    def test_login_invalid_credentials(self, api_client):
        """Test login with invalid credentials"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@email.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401


class TestComparacionDataIntegrity:
    """Tests for data integrity in comparisons"""
    
    def test_comparison_has_valid_metrics(self, api_client):
        """Test that comparison metrics are valid"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparaciones")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            comp = data[0]
            
            # Check metricas_dron structure
            metricas_dron = comp.get("metricas_dron", {})
            assert "semanas_registradas" in metricas_dron
            
            # Check comparaciones list
            comparaciones = comp.get("comparaciones", [])
            for c in comparaciones:
                assert "nombre" in c
                assert "valor_dron" in c
                assert "valor_residente" in c
                assert "diferencia" in c
                assert "estado" in c
    
    def test_comparison_states_are_valid(self, api_client):
        """Test that comparison states are valid values"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparaciones")
        assert response.status_code == 200
        
        data = response.json()
        valid_states = ["coincide", "discrepancia_menor", "discrepancia_mayor"]
        
        for comp in data:
            for c in comp.get("comparaciones", []):
                assert c.get("estado") in valid_states, f"Invalid state: {c.get('estado')}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
