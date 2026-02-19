"""
Test suite for Comparación de Planes (Real vs Plan Usuario vs Plan IA) feature
Tests the comparison between user's plan, AI-generated plan, and real progress
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://dron-topografia-1.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@dron.mx"
ADMIN_PASSWORD = "admin123"

# Known project ID (Acuarela - has analisis_maquinaria_ia)
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


class TestComparacionPlanesEndpoints:
    """Tests for the Plan Comparison feature endpoints"""
    
    def test_proyecto_has_analisis_maquinaria_ia(self, api_client):
        """Test that Acuarela project has analisis_maquinaria_ia"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("analisis_maquinaria_ia") is not None, "Project should have analisis_maquinaria_ia"
        
        # Verify structure of analisis_maquinaria_ia
        analisis = data.get("analisis_maquinaria_ia", {})
        assert "plan_excavacion" in analisis or "plan_pilas" in analisis, "Should have plan data"
    
    def test_get_comparacion_planes_endpoint_exists(self, api_client):
        """Test that GET /proyectos/{id}/comparacion-planes endpoint exists"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparacion-planes")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "proyecto_nombre" in data, "Response should have proyecto_nombre"
        assert "comparacion" in data, "Response should have comparacion field"
    
    def test_get_comparacion_planes_for_nonexistent_project(self, api_client):
        """Test that nonexistent project returns 404"""
        response = api_client.get(f"{BASE_URL}/api/proyectos/nonexistent-id/comparacion-planes")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_post_comparar_plan_ia_endpoint_exists(self, api_client):
        """Test that POST /proyectos/{id}/comparar-plan-ia endpoint exists"""
        response = api_client.post(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparar-plan-ia")
        # Should return 200 (success) or 400 (no AI analysis) - not 404 or 405
        assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}: {response.text}"
    
    def test_post_comparar_plan_ia_generates_comparison(self, api_client):
        """Test that POST /proyectos/{id}/comparar-plan-ia generates comparison"""
        response = api_client.post(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparar-plan-ia")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Response should indicate success"
        assert "comparacion" in data, "Response should have comparacion"
        
        comparacion = data.get("comparacion", {})
        # Verify structure
        assert "fecha_comparacion" in comparacion, "Should have fecha_comparacion"
        assert "datos_usuario" in comparacion, "Should have datos_usuario"
        assert "datos_ia" in comparacion, "Should have datos_ia"
        assert "datos_reales" in comparacion, "Should have datos_reales"
    
    def test_comparacion_datos_usuario_structure(self, api_client):
        """Test that datos_usuario has correct structure"""
        response = api_client.post(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparar-plan-ia")
        assert response.status_code == 200
        
        comparacion = response.json().get("comparacion", {})
        datos_usuario = comparacion.get("datos_usuario", {})
        
        # Check required fields
        assert "semanas_excavacion" in datos_usuario, "Should have semanas_excavacion"
        assert "semanas_pilas" in datos_usuario, "Should have semanas_pilas"
        assert "semanas_anclas" in datos_usuario, "Should have semanas_anclas"
        assert "semanas_total" in datos_usuario, "Should have semanas_total"
    
    def test_comparacion_datos_ia_structure(self, api_client):
        """Test that datos_ia has correct structure"""
        response = api_client.post(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparar-plan-ia")
        assert response.status_code == 200
        
        comparacion = response.json().get("comparacion", {})
        datos_ia = comparacion.get("datos_ia", {})
        
        # Check required fields
        assert "semanas_excavacion" in datos_ia, "Should have semanas_excavacion"
        assert "semanas_pilas" in datos_ia, "Should have semanas_pilas"
        assert "semanas_anclas" in datos_ia, "Should have semanas_anclas"
        assert "semanas_total" in datos_ia, "Should have semanas_total"
    
    def test_comparacion_datos_reales_structure(self, api_client):
        """Test that datos_reales has correct structure"""
        response = api_client.post(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparar-plan-ia")
        assert response.status_code == 200
        
        comparacion = response.json().get("comparacion", {})
        datos_reales = comparacion.get("datos_reales", {})
        
        # Check required fields
        assert "semanas_transcurridas" in datos_reales, "Should have semanas_transcurridas"
        assert "volumen_excavado" in datos_reales, "Should have volumen_excavado"
        assert "pilas_completadas" in datos_reales, "Should have pilas_completadas"
        assert "anclas_instaladas" in datos_reales, "Should have anclas_instaladas"
    
    def test_get_comparacion_after_post(self, api_client):
        """Test that GET returns the comparison after POST"""
        # First generate comparison
        post_response = api_client.post(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparar-plan-ia")
        assert post_response.status_code == 200
        
        # Then get it
        get_response = api_client.get(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparacion-planes")
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert data.get("comparacion") is not None, "Should have comparacion data after POST"
        
        comparacion = data.get("comparacion", {})
        assert "fecha_comparacion" in comparacion, "Should have fecha_comparacion"
        assert "datos_usuario" in comparacion, "Should have datos_usuario"
        assert "datos_ia" in comparacion, "Should have datos_ia"
    
    def test_comparacion_has_analisis_ia(self, api_client):
        """Test that comparison includes AI analysis when available"""
        response = api_client.post(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparar-plan-ia")
        assert response.status_code == 200
        
        comparacion = response.json().get("comparacion", {})
        
        # Check if analisis_ia exists (may not if AI call failed)
        if "analisis_ia" in comparacion:
            analisis = comparacion.get("analisis_ia", {})
            # Verify expected fields from AI analysis
            expected_fields = ["veredicto", "comparacion_general", "evaluacion_excavacion"]
            for field in expected_fields:
                if field in analisis:
                    print(f"Found AI analysis field: {field}")
    
    def test_post_comparar_plan_ia_for_project_without_ia(self, api_client):
        """Test that POST returns 400 for project without analisis_maquinaria_ia"""
        # Get a project without AI analysis
        response = api_client.get(f"{BASE_URL}/api/proyectos")
        assert response.status_code == 200
        
        proyectos = response.json()
        project_without_ia = None
        for p in proyectos:
            if not p.get("analisis_maquinaria_ia"):
                project_without_ia = p
                break
        
        if project_without_ia:
            response = api_client.post(f"{BASE_URL}/api/proyectos/{project_without_ia['id']}/comparar-plan-ia")
            assert response.status_code == 400, f"Expected 400 for project without AI, got {response.status_code}"
            assert "No hay análisis de IA" in response.json().get("detail", "")


class TestComparacionVeredicto:
    """Tests for the verdict/badge functionality"""
    
    def test_veredicto_values(self, api_client):
        """Test that veredicto has valid values"""
        response = api_client.post(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparar-plan-ia")
        assert response.status_code == 200
        
        comparacion = response.json().get("comparacion", {})
        analisis = comparacion.get("analisis_ia", {})
        
        if "veredicto" in analisis:
            valid_veredictos = ["PLAN_IA_MEJOR", "PLAN_USUARIO_MEJOR", "SIMILAR"]
            assert analisis["veredicto"] in valid_veredictos, f"Invalid veredicto: {analisis['veredicto']}"
    
    def test_evaluacion_mejor_plan_values(self, api_client):
        """Test that mejor_plan has valid values in evaluations"""
        response = api_client.post(f"{BASE_URL}/api/proyectos/{ACUARELA_PROJECT_ID}/comparar-plan-ia")
        assert response.status_code == 200
        
        comparacion = response.json().get("comparacion", {})
        analisis = comparacion.get("analisis_ia", {})
        
        valid_mejor_plan = ["usuario", "ia", "similar"]
        
        for eval_key in ["evaluacion_excavacion", "evaluacion_pilas", "evaluacion_anclas"]:
            if eval_key in analisis:
                mejor_plan = analisis[eval_key].get("mejor_plan", "")
                if mejor_plan:
                    assert mejor_plan in valid_mejor_plan, f"Invalid mejor_plan in {eval_key}: {mejor_plan}"


class TestDashboardComparacionesResumen:
    """Tests for the dashboard comparisons summary endpoint"""
    
    def test_dashboard_comparaciones_resumen_endpoint(self, api_client):
        """Test that GET /dashboard/comparaciones-resumen endpoint exists"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/comparaciones-resumen")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "proyectos" in data, "Response should have proyectos key"
        assert isinstance(data["proyectos"], list), "proyectos should be a list"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
