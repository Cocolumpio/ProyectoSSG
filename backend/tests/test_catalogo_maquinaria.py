"""
Test suite for Catálogo de Maquinaria endpoints and Avance Semanal modifications
Tests the new features:
1. POST /api/proyectos/analizar-catalogo-maquinaria - Analyze machinery catalog with AI
2. POST /api/proyectos/{id}/guardar-catalogo-maquinaria - Save machinery catalog
3. GET /api/proyectos/{id}/catalogo-maquinaria - Get machinery catalog
4. Avance semanal creation without URL field
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCatalogoMaquinaria:
    """Tests for the new Catálogo de Maquinaria feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.admin_credentials = {"email": "admin@dron.mx", "password": "admin123"}
        # Get auth token
        response = requests.post(f"{BASE_URL}/api/auth/login", json=self.admin_credentials)
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}
        
        # Get first project ID
        projects_response = requests.get(f"{BASE_URL}/api/proyectos")
        if projects_response.status_code == 200 and projects_response.json():
            self.project_id = projects_response.json()[0]["id"]
        else:
            self.project_id = None
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        assert "message" in response.json()
        print("✓ API root endpoint working")
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=self.admin_credentials)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["rol"] == "admin"
        print("✓ Admin login successful")
    
    def test_list_proyectos(self):
        """Test listing projects"""
        response = requests.get(f"{BASE_URL}/api/proyectos")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        print(f"✓ Listed {len(data)} projects")
    
    def test_guardar_catalogo_maquinaria(self):
        """Test POST /api/proyectos/{id}/guardar-catalogo-maquinaria"""
        if not self.project_id:
            pytest.skip("No project available for testing")
        
        test_data = {
            "maquinas": [
                {"tipo": "EXCAVADORA", "marca": "CAT", "modelo": "320D", "estatus": "OPTIMA"},
                {"tipo": "PERFORADORA", "marca": "BAUER", "modelo": "BG28", "estatus": "SATISFACTORIO"}
            ],
            "analisis_ia": {
                "resumen_ejecutivo": "Test analysis",
                "plan_excavacion": {"tiempo_estimado_dias": 15}
            },
            "parametros": {
                "area_terreno": 5000,
                "volumen_excavacion": 10000,
                "num_pilas": 50
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/proyectos/{self.project_id}/guardar-catalogo-maquinaria",
            json=test_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "message" in data
        print(f"✓ Saved machinery catalog for project {self.project_id}")
    
    def test_obtener_catalogo_maquinaria(self):
        """Test GET /api/proyectos/{id}/catalogo-maquinaria"""
        if not self.project_id:
            pytest.skip("No project available for testing")
        
        response = requests.get(f"{BASE_URL}/api/proyectos/{self.project_id}/catalogo-maquinaria")
        
        assert response.status_code == 200
        data = response.json()
        assert "catalogo" in data
        assert "analisis_ia" in data
        assert "parametros" in data
        print(f"✓ Retrieved machinery catalog for project {self.project_id}")
    
    def test_catalogo_maquinaria_not_found(self):
        """Test GET catalogo-maquinaria with invalid project ID"""
        response = requests.get(f"{BASE_URL}/api/proyectos/invalid-id-12345/catalogo-maquinaria")
        assert response.status_code == 404
        print("✓ Correctly returns 404 for invalid project ID")


class TestAvancesSemanalSinURL:
    """Tests for Avance Semanal creation without URL field"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.admin_credentials = {"email": "admin@dron.mx", "password": "admin123"}
        # Get auth token
        response = requests.post(f"{BASE_URL}/api/auth/login", json=self.admin_credentials)
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}
        
        # Get first project ID
        projects_response = requests.get(f"{BASE_URL}/api/proyectos")
        if projects_response.status_code == 200 and projects_response.json():
            self.project_id = projects_response.json()[0]["id"]
        else:
            self.project_id = None
    
    def test_crear_avance_semanal_sin_url(self):
        """Test creating avance semanal without URL field (new behavior)"""
        if not self.project_id:
            pytest.skip("No project available for testing")
        
        # Get existing avances to determine next week number
        avances_response = requests.get(f"{BASE_URL}/api/proyectos/{self.project_id}/avances-semanales")
        existing_avances = avances_response.json() if avances_response.status_code == 200 else []
        next_week = max([a.get("semana", 0) for a in existing_avances], default=0) + 100  # Use high number to avoid conflicts
        
        # Create avance WITHOUT pix4d_url (new behavior)
        avance_data = {
            "semana": next_week,
            "fecha": "2025-01-20",
            "descripcion": "Test avance sin URL - verificando nueva funcionalidad",
            "volumen_excavacion": 500.0,
            "pilas_completadas": 5,
            "anclas_instaladas": 3
        }
        
        response = requests.post(
            f"{BASE_URL}/api/proyectos/{self.project_id}/avances-semanales",
            json=avance_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["semana"] == next_week
        assert data["fecha"] == "2025-01-20"
        assert data.get("pix4d_url") is None or data.get("pix4d_url") == ""
        assert data.get("modelo_3d_url") is None
        print(f"✓ Created avance semanal week {next_week} without URL field")
        
        # Cleanup - delete the test avance
        avance_id = data["id"]
        delete_response = requests.delete(
            f"{BASE_URL}/api/proyectos/{self.project_id}/avances-semanales/{avance_id}"
        )
        assert delete_response.status_code == 200
        print(f"✓ Cleaned up test avance {avance_id}")
    
    def test_listar_avances_semanales(self):
        """Test listing avances semanales"""
        if not self.project_id:
            pytest.skip("No project available for testing")
        
        response = requests.get(f"{BASE_URL}/api/proyectos/{self.project_id}/avances-semanales")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} avances semanales for project")


class TestAnalizarCatalogoMaquinaria:
    """Tests for the AI-powered machinery catalog analysis endpoint"""
    
    def test_analizar_catalogo_sin_archivo(self):
        """Test that endpoint requires a file"""
        response = requests.post(f"{BASE_URL}/api/proyectos/analizar-catalogo-maquinaria")
        # Should return 422 (validation error) because file is required
        assert response.status_code == 422
        print("✓ Correctly requires file upload")
    
    def test_analizar_catalogo_archivo_invalido(self):
        """Test that endpoint rejects non-Excel files"""
        # Create a fake text file
        files = {'file': ('test.txt', io.BytesIO(b'test content'), 'text/plain')}
        response = requests.post(
            f"{BASE_URL}/api/proyectos/analizar-catalogo-maquinaria",
            files=files
        )
        assert response.status_code == 400
        assert "Excel" in response.json().get("detail", "")
        print("✓ Correctly rejects non-Excel files")


class TestExistingFunctionality:
    """Tests to ensure existing functionality still works"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.admin_credentials = {"email": "admin@dron.mx", "password": "admin123"}
    
    def test_admin_login(self):
        """Test admin login still works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=self.admin_credentials)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "admin@dron.mx"
        print("✓ Admin login working")
    
    def test_estadisticas_resumen(self):
        """Test estadisticas resumen endpoint"""
        response = requests.get(f"{BASE_URL}/api/estadisticas/resumen")
        assert response.status_code == 200
        data = response.json()
        assert "total_proyectos" in data
        print(f"✓ Estadisticas: {data['total_proyectos']} proyectos")
    
    def test_export_excel(self):
        """Test Excel export still works"""
        response = requests.get(f"{BASE_URL}/api/exportar/metricas-excel")
        assert response.status_code == 200
        assert "spreadsheet" in response.headers.get("content-type", "")
        print("✓ Excel export working")
    
    def test_export_pdf(self):
        """Test PDF export still works"""
        response = requests.get(f"{BASE_URL}/api/exportar/metricas-pdf")
        assert response.status_code == 200
        assert "pdf" in response.headers.get("content-type", "")
        print("✓ PDF export working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
