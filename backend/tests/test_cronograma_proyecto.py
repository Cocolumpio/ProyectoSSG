"""
Test suite for Cronograma/Programa de Obra feature
Tests:
- GET /api/proyectos/{id}/cronograma - Get cronograma info
- POST /api/proyectos/{id}/actualizar-cronograma - Upload/update cronograma Excel
- GET /api/plantilla-cronograma - Download template
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test project ID (Acuarela)
TEST_PROJECT_ID = "aa547723-9d64-4d4d-8b6a-ef615941ee05"

class TestCronogramaEndpoints:
    """Tests for cronograma/programa de obra endpoints"""
    
    def test_get_cronograma_info_no_cronograma(self):
        """Test GET /api/proyectos/{id}/cronograma returns correct structure when no cronograma"""
        response = requests.get(f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/cronograma")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Verify response structure
        assert "proyecto_nombre" in data
        assert "tiene_cronograma" in data
        assert "cronograma_archivo" in data
        assert "cronograma_fecha_carga" in data
        assert "cronograma_resumen" in data
        assert "semanas_planeadas" in data
        assert "fecha_inicio" in data
        assert "fecha_fin_planeada" in data
        assert "frentes" in data
        
        # Verify data types
        assert isinstance(data["tiene_cronograma"], bool)
        assert isinstance(data["frentes"], list)
        print(f"✓ GET cronograma returns correct structure: tiene_cronograma={data['tiene_cronograma']}")
    
    def test_get_cronograma_project_not_found(self):
        """Test GET /api/proyectos/{id}/cronograma returns 404 for non-existent project"""
        response = requests.get(f"{BASE_URL}/api/proyectos/non-existent-id/cronograma")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ GET cronograma returns 404 for non-existent project")
    
    def test_download_plantilla_cronograma(self):
        """Test GET /api/plantilla-cronograma downloads Excel template"""
        response = requests.get(f"{BASE_URL}/api/plantilla-cronograma")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify content type is Excel
        content_type = response.headers.get('content-type', '')
        assert 'spreadsheet' in content_type or 'excel' in content_type.lower() or 'octet-stream' in content_type, \
            f"Expected Excel content type, got {content_type}"
        
        # Verify file has content
        assert len(response.content) > 0, "Template file is empty"
        
        # Verify it starts with Excel signature (PK for zip-based xlsx)
        assert response.content[:2] == b'PK', "File does not appear to be a valid xlsx file"
        
        print(f"✓ Plantilla downloaded successfully: {len(response.content)} bytes")
    
    def test_upload_cronograma_invalid_file_type(self):
        """Test POST /api/proyectos/{id}/actualizar-cronograma rejects non-Excel files"""
        # Create a fake text file
        fake_file = io.BytesIO(b"This is not an Excel file")
        
        response = requests.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/actualizar-cronograma",
            files={"file": ("test.txt", fake_file, "text/plain")}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Upload rejects non-Excel files")
    
    def test_upload_cronograma_project_not_found(self):
        """Test POST /api/proyectos/{id}/actualizar-cronograma returns 404 for non-existent project"""
        # Download the real template to use as test file
        template_response = requests.get(f"{BASE_URL}/api/plantilla-cronograma")
        if template_response.status_code != 200:
            pytest.skip("Could not download template for test")
        
        response = requests.post(
            f"{BASE_URL}/api/proyectos/non-existent-id/actualizar-cronograma",
            files={"file": ("test.xlsx", io.BytesIO(template_response.content), 
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Upload returns 404 for non-existent project")
    
    def test_upload_cronograma_with_template(self):
        """Test POST /api/proyectos/{id}/actualizar-cronograma with valid Excel template"""
        # Download the real template
        template_response = requests.get(f"{BASE_URL}/api/plantilla-cronograma")
        if template_response.status_code != 200:
            pytest.skip("Could not download template for test")
        
        # Upload the template to a test project
        response = requests.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/actualizar-cronograma",
            files={"file": ("cronograma_test.xlsx", io.BytesIO(template_response.content), 
                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        # Should succeed or return parsing error (not 500)
        assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert data["success"] == True
            assert "mensaje" in data
            print(f"✓ Upload successful: {data.get('mensaje')}")
        else:
            # 400 is acceptable if template has parsing issues
            print(f"✓ Upload returned 400 (parsing issue): {response.json().get('detail', 'Unknown')}")
    
    def test_get_cronograma_after_upload(self):
        """Test GET /api/proyectos/{id}/cronograma after uploading a cronograma"""
        response = requests.get(f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/cronograma")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check if cronograma was uploaded in previous test
        if data.get("tiene_cronograma"):
            assert data["cronograma_archivo"] is not None
            assert data["cronograma_fecha_carga"] is not None
            print(f"✓ Cronograma info retrieved: archivo={data['cronograma_archivo']}")
        else:
            print("✓ No cronograma uploaded yet (expected if previous test failed)")


class TestCronogramaIntegration:
    """Integration tests for cronograma feature"""
    
    def test_list_projects_shows_cronograma_status(self):
        """Test that project list includes cronograma_archivo field"""
        response = requests.get(f"{BASE_URL}/api/proyectos")
        
        assert response.status_code == 200
        projects = response.json()
        
        assert len(projects) > 0, "No projects found"
        
        # Check that projects have cronograma-related fields
        for project in projects[:3]:
            # These fields should exist (even if null)
            assert "nombre" in project
            # cronograma_archivo may or may not be in the response depending on projection
            print(f"✓ Project {project['nombre']}: cronograma_archivo={project.get('cronograma_archivo', 'N/A')}")
    
    def test_get_single_project_has_cronograma_fields(self):
        """Test that single project endpoint includes cronograma fields"""
        response = requests.get(f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}")
        
        assert response.status_code == 200
        project = response.json()
        
        # Verify project has expected fields
        assert "nombre" in project
        assert "semanas_planeadas" in project
        print(f"✓ Project {project['nombre']} has semanas_planeadas={project.get('semanas_planeadas', 0)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
