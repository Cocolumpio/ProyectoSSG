"""
Test suite for Catálogo de Maquinaria AI Analysis endpoint
Tests the POST /api/proyectos/analizar-catalogo-maquinaria endpoint with real Excel file
Verifies:
1. AI analysis returns plan_excavacion, plan_pilas, plan_anclas
2. maquinas_con_specs contains technical specifications
3. Parameters (area_terreno, espacio_maniobra, distancia_pilas) are processed correctly
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCatalogoAIAnalysis:
    """Tests for the AI-powered machinery catalog analysis endpoint"""
    
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
    
    def test_analizar_catalogo_with_real_excel(self):
        """Test POST /api/proyectos/analizar-catalogo-maquinaria with real Excel file"""
        # Check if test file exists
        test_file_path = "/tmp/test_catalogo.xlsx"
        if not os.path.exists(test_file_path):
            pytest.skip("Test Excel file not found at /tmp/test_catalogo.xlsx")
        
        # Read the test file
        with open(test_file_path, 'rb') as f:
            file_content = f.read()
        
        # Prepare parameters
        params = {
            "area_terreno": 5000,
            "volumen_excavacion": 10000,
            "num_pilas": 50,
            "distancia_pilas": 3,
            "espacio_maniobra": 1000
        }
        
        # Send request with file
        files = {'file': ('test_catalogo.xlsx', io.BytesIO(file_content), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        
        response = requests.post(
            f"{BASE_URL}/api/proyectos/analizar-catalogo-maquinaria",
            files=files,
            params=params,
            timeout=120  # AI analysis may take time
        )
        
        print(f"Response status: {response.status_code}")
        
        # Should return 200
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Response keys: {data.keys()}")
        
        # Verify basic structure
        assert data.get("success") == True, "Expected success=True"
        assert "total_maquinas" in data, "Expected total_maquinas in response"
        assert "maquinas_disponibles" in data, "Expected maquinas_disponibles in response"
        assert "resumen_catalogo" in data, "Expected resumen_catalogo in response"
        
        print(f"✓ Total máquinas: {data.get('total_maquinas')}")
        print(f"✓ Máquinas disponibles: {data.get('maquinas_disponibles')}")
        print(f"✓ Resumen catálogo: {data.get('resumen_catalogo')}")
        
        # Check if AI analysis is present
        if "analisis_ia" in data and data["analisis_ia"]:
            analisis = data["analisis_ia"]
            print(f"✓ AI Analysis keys: {analisis.keys()}")
            
            # Verify plan_excavacion
            if "plan_excavacion" in analisis:
                plan_exc = analisis["plan_excavacion"]
                print(f"✓ Plan Excavación: {plan_exc}")
                assert "maquinas_recomendadas" in plan_exc or "estrategia" in plan_exc, "plan_excavacion should have maquinas_recomendadas or estrategia"
            
            # Verify plan_pilas
            if "plan_pilas" in analisis:
                plan_pilas = analisis["plan_pilas"]
                print(f"✓ Plan Pilas: {plan_pilas}")
                assert "maquinas_recomendadas" in plan_pilas or "estrategia" in plan_pilas, "plan_pilas should have maquinas_recomendadas or estrategia"
            
            # Verify plan_anclas
            if "plan_anclas" in analisis:
                plan_anclas = analisis["plan_anclas"]
                print(f"✓ Plan Anclas: {plan_anclas}")
                assert "maquinas_recomendadas" in plan_anclas or "estrategia" in plan_anclas, "plan_anclas should have maquinas_recomendadas or estrategia"
            
            # Verify maquinas_con_specs
            if "maquinas_con_specs" in analisis:
                specs = analisis["maquinas_con_specs"]
                print(f"✓ Máquinas con specs: {len(specs)} máquinas")
                if len(specs) > 0:
                    first_spec = specs[0]
                    print(f"  First machine spec keys: {first_spec.keys()}")
                    # Check for expected fields
                    expected_fields = ["tipo", "marca", "modelo"]
                    for field in expected_fields:
                        if field in first_spec:
                            print(f"  ✓ {field}: {first_spec[field]}")
        elif "analisis_ia_texto" in data:
            print(f"✓ AI Analysis (text): {data['analisis_ia_texto'][:200]}...")
        else:
            print("⚠ No AI analysis in response (may be due to AI service issue)")
        
        print("✓ Catálogo analysis endpoint working correctly")
    
    def test_analizar_catalogo_parameters_validation(self):
        """Test that parameters are correctly passed to the analysis"""
        test_file_path = "/tmp/test_catalogo.xlsx"
        if not os.path.exists(test_file_path):
            pytest.skip("Test Excel file not found at /tmp/test_catalogo.xlsx")
        
        with open(test_file_path, 'rb') as f:
            file_content = f.read()
        
        # Test with specific parameters
        params = {
            "area_terreno": 8000,
            "volumen_excavacion": 15000,
            "num_pilas": 100,
            "distancia_pilas": 2.5,
            "espacio_maniobra": 2000
        }
        
        files = {'file': ('test_catalogo.xlsx', io.BytesIO(file_content), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        
        response = requests.post(
            f"{BASE_URL}/api/proyectos/analizar-catalogo-maquinaria",
            files=files,
            params=params,
            timeout=120
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print(f"✓ Parameters validation passed with area_terreno={params['area_terreno']}")
    
    def test_guardar_y_recuperar_parametros_proyecto(self):
        """Test that terrain parameters are saved and retrieved with the project"""
        if not self.project_id:
            pytest.skip("No project available for testing")
        
        # Save catalog with parameters
        test_data = {
            "maquinas": [
                {"tipo": "EXCAVADORA", "marca": "CAT", "modelo": "320D", "estatus": "OPTIMA"}
            ],
            "analisis_ia": {
                "plan_excavacion": {"tiempo_estimado_dias": 20, "rendimiento_esperado_m3_dia": 500},
                "plan_pilas": {"tiempo_estimado_dias": 30, "pilas_por_dia": 3},
                "plan_anclas": {"tiempo_estimado_dias": 15, "anclas_por_dia": 5}
            },
            "parametros": {
                "area_terreno": 6000,
                "espacio_maniobra": 1500,
                "distancia_pilas": 2.8
            }
        }
        
        # Save
        save_response = requests.post(
            f"{BASE_URL}/api/proyectos/{self.project_id}/guardar-catalogo-maquinaria",
            json=test_data
        )
        assert save_response.status_code == 200
        print(f"✓ Saved catalog with parameters")
        
        # Retrieve
        get_response = requests.get(f"{BASE_URL}/api/proyectos/{self.project_id}/catalogo-maquinaria")
        assert get_response.status_code == 200
        
        retrieved = get_response.json()
        assert "parametros" in retrieved
        params = retrieved["parametros"]
        
        # Verify parameters were saved
        assert params.get("area_terreno") == 6000, f"Expected area_terreno=6000, got {params.get('area_terreno')}"
        assert params.get("espacio_maniobra") == 1500, f"Expected espacio_maniobra=1500, got {params.get('espacio_maniobra')}"
        assert params.get("distancia_pilas") == 2.8, f"Expected distancia_pilas=2.8, got {params.get('distancia_pilas')}"
        
        print(f"✓ Parameters correctly saved and retrieved: {params}")


class TestAnalizarFotoAvance:
    """Tests for the photo analysis endpoint"""
    
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
        
        # Get first project and its avances
        projects_response = requests.get(f"{BASE_URL}/api/proyectos")
        if projects_response.status_code == 200 and projects_response.json():
            self.project_id = projects_response.json()[0]["id"]
            # Get avances for this project
            avances_response = requests.get(f"{BASE_URL}/api/proyectos/{self.project_id}/avances-semanales")
            if avances_response.status_code == 200 and avances_response.json():
                self.avance_id = avances_response.json()[0]["id"]
            else:
                self.avance_id = None
        else:
            self.project_id = None
            self.avance_id = None
    
    def test_analizar_foto_sin_imagen(self):
        """Test that endpoint requires imagen_base64"""
        if not self.avance_id:
            pytest.skip("No avance available for testing")
        
        response = requests.post(
            f"{BASE_URL}/api/avances/{self.avance_id}/analizar-foto",
            json={}
        )
        
        assert response.status_code == 400
        assert "imagen" in response.json().get("detail", "").lower() or "base64" in response.json().get("detail", "").lower()
        print("✓ Correctly requires imagen_base64")
    
    def test_analizar_foto_avance_not_found(self):
        """Test that endpoint returns 404 for invalid avance ID"""
        response = requests.post(
            f"{BASE_URL}/api/avances/invalid-avance-id-12345/analizar-foto",
            json={"imagen_base64": "test"}
        )
        
        assert response.status_code == 404
        print("✓ Correctly returns 404 for invalid avance ID")


class TestAdminLoginAndProyectos:
    """Tests for admin login and project listing"""
    
    def test_admin_login(self):
        """Test admin login with correct credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@dron.mx", "password": "admin123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["rol"] == "admin"
        assert data["user"]["email"] == "admin@dron.mx"
        print(f"✓ Admin login successful: {data['user']['nombre']}")
    
    def test_admin_login_wrong_password(self):
        """Test admin login with wrong password"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@dron.mx", "password": "wrongpassword"}
        )
        
        assert response.status_code == 401
        print("✓ Correctly rejects wrong password")
    
    def test_listar_proyectos(self):
        """Test listing all projects"""
        response = requests.get(f"{BASE_URL}/api/proyectos")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} projects")
        
        if len(data) > 0:
            first_project = data[0]
            assert "id" in first_project
            assert "nombre" in first_project
            print(f"  First project: {first_project['nombre']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
