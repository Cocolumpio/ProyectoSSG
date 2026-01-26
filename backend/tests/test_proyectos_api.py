"""
Backend API Tests for DrON Topografía Dashboard
Tests for Proyectos, Vuelos, and Estadísticas endpoints
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthAndBasicEndpoints:
    """Basic API health and root endpoint tests"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"API Root response: {data}")


class TestProyectosEndpoints:
    """Tests for /api/proyectos endpoints"""
    
    def test_get_all_proyectos(self):
        """Test GET /api/proyectos - should return list with Hotel Marriott"""
        response = requests.get(f"{BASE_URL}/api/proyectos")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Verify Hotel Marriott exists
        marriott = next((p for p in data if p.get('id') == 'hotel-marriott-001'), None)
        assert marriott is not None, "Hotel Marriott project not found"
        assert marriott['nombre'] == 'Hotel Marriott'
        assert marriott['ubicacion'] == 'Guadalajara, Jalisco'
        assert marriott['avance_actual'] == 40.0
        print(f"Found {len(data)} proyectos, Hotel Marriott verified")
    
    def test_get_proyecto_by_id(self):
        """Test GET /api/proyectos/{id} - get Hotel Marriott by ID"""
        response = requests.get(f"{BASE_URL}/api/proyectos/hotel-marriott-001")
        assert response.status_code == 200
        data = response.json()
        
        assert data['id'] == 'hotel-marriott-001'
        assert data['nombre'] == 'Hotel Marriott'
        assert data['ubicacion'] == 'Guadalajara, Jalisco'
        assert data['avance_actual'] == 40.0
        assert 'coordenadas' in data
        assert data['coordenadas']['lat'] == 20.6597
        assert data['coordenadas']['lng'] == -103.3496
        assert 'pix4d_url' in data
        assert 'volumetria' in data
        print(f"Proyecto retrieved: {data['nombre']}")
    
    def test_get_proyecto_not_found(self):
        """Test GET /api/proyectos/{id} - non-existent project returns 404"""
        response = requests.get(f"{BASE_URL}/api/proyectos/non-existent-id")
        assert response.status_code == 404
        data = response.json()
        assert 'detail' in data
        print(f"404 response: {data}")
    
    def test_create_and_delete_proyecto(self):
        """Test POST /api/proyectos and DELETE /api/proyectos/{id}"""
        # Create a test project
        test_id = f"TEST_proyecto_{uuid.uuid4().hex[:8]}"
        new_proyecto = {
            "nombre": f"TEST Proyecto {test_id}",
            "ubicacion": "Ciudad de México, CDMX",
            "coordenadas": {"lat": 19.4326, "lng": -99.1332},
            "fecha_inicio": "2025-01-01",
            "fecha_fin_planeada": "2025-12-31",
            "descripcion": "Test project for API testing",
            "avance_actual": 25.0,
            "pix4d_url": "https://cloud.pix4d.com/embed/test",
            "volumetria": {"excavacion": 100.0, "relleno": 50.0, "materiales": 75.0}
        }
        
        # POST - Create
        response = requests.post(f"{BASE_URL}/api/proyectos", json=new_proyecto)
        assert response.status_code == 200
        created = response.json()
        assert created['nombre'] == new_proyecto['nombre']
        assert created['ubicacion'] == new_proyecto['ubicacion']
        assert created['avance_actual'] == 25.0
        assert 'id' in created
        project_id = created['id']
        print(f"Created project: {project_id}")
        
        # GET - Verify creation
        response = requests.get(f"{BASE_URL}/api/proyectos/{project_id}")
        assert response.status_code == 200
        fetched = response.json()
        assert fetched['nombre'] == new_proyecto['nombre']
        
        # DELETE - Clean up
        response = requests.delete(f"{BASE_URL}/api/proyectos/{project_id}")
        assert response.status_code == 200
        print(f"Deleted project: {project_id}")
        
        # Verify deletion
        response = requests.get(f"{BASE_URL}/api/proyectos/{project_id}")
        assert response.status_code == 404
        print("Project deletion verified")
    
    def test_update_proyecto_put(self):
        """Test PUT /api/proyectos/{id} - update project fields"""
        # First get current state
        response = requests.get(f"{BASE_URL}/api/proyectos/hotel-marriott-001")
        assert response.status_code == 200
        original = response.json()
        original_avance = original['avance_actual']
        
        # Update avance to 42%
        update_data = {"avance_actual": 42.0}
        response = requests.put(
            f"{BASE_URL}/api/proyectos/hotel-marriott-001",
            json=update_data
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated['avance_actual'] == 42.0
        print(f"Updated avance from {original_avance} to 42.0")
        
        # Verify update persisted
        response = requests.get(f"{BASE_URL}/api/proyectos/hotel-marriott-001")
        assert response.status_code == 200
        fetched = response.json()
        assert fetched['avance_actual'] == 42.0
        
        # Revert to original
        response = requests.put(
            f"{BASE_URL}/api/proyectos/hotel-marriott-001",
            json={"avance_actual": original_avance}
        )
        assert response.status_code == 200
        print(f"Reverted avance to {original_avance}")
    
    def test_update_proyecto_volumetria(self):
        """Test PUT /api/proyectos/{id} - update volumetria fields"""
        # Get current state
        response = requests.get(f"{BASE_URL}/api/proyectos/hotel-marriott-001")
        assert response.status_code == 200
        original = response.json()
        original_volumetria = original.get('volumetria', {})
        
        # Update volumetria
        new_volumetria = {"excavacion": 3000.0, "relleno": 2000.0, "materiales": 3500.0}
        response = requests.put(
            f"{BASE_URL}/api/proyectos/hotel-marriott-001",
            json={"volumetria": new_volumetria}
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated['volumetria']['excavacion'] == 3000.0
        print(f"Updated volumetria: {updated['volumetria']}")
        
        # Revert to original
        response = requests.put(
            f"{BASE_URL}/api/proyectos/hotel-marriott-001",
            json={"volumetria": original_volumetria}
        )
        assert response.status_code == 200
        print("Reverted volumetria to original")
    
    def test_update_proyecto_pix4d_url(self):
        """Test PUT /api/proyectos/{id} - update pix4d_url"""
        # Get current state
        response = requests.get(f"{BASE_URL}/api/proyectos/hotel-marriott-001")
        assert response.status_code == 200
        original = response.json()
        original_url = original.get('pix4d_url', '')
        
        # Update pix4d_url
        new_url = "https://cloud.pix4d.com/embed/test-new-url"
        response = requests.put(
            f"{BASE_URL}/api/proyectos/hotel-marriott-001",
            json={"pix4d_url": new_url}
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated['pix4d_url'] == new_url
        print(f"Updated pix4d_url to: {new_url}")
        
        # Revert to original
        response = requests.put(
            f"{BASE_URL}/api/proyectos/hotel-marriott-001",
            json={"pix4d_url": original_url}
        )
        assert response.status_code == 200
        print("Reverted pix4d_url to original")
    
    def test_update_proyecto_not_found(self):
        """Test PUT /api/proyectos/{id} - non-existent project returns 404"""
        response = requests.put(
            f"{BASE_URL}/api/proyectos/non-existent-id",
            json={"avance_actual": 50.0}
        )
        assert response.status_code == 404
        print("404 for non-existent project update verified")


class TestVuelosEndpoints:
    """Tests for /api/vuelos endpoints"""
    
    def test_get_all_vuelos(self):
        """Test GET /api/vuelos - should return list with at least one vuelo"""
        response = requests.get(f"{BASE_URL}/api/vuelos")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Verify vuelo structure
        vuelo = data[0]
        assert 'id' in vuelo
        assert 'proyecto_id' in vuelo
        assert 'fecha_vuelo' in vuelo
        assert 'volumetria' in vuelo
        print(f"Found {len(data)} vuelos")
    
    def test_get_vuelos_by_proyecto(self):
        """Test GET /api/vuelos?proyecto_id={id} - filter by project"""
        response = requests.get(f"{BASE_URL}/api/vuelos?proyecto_id=hotel-marriott-001")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All vuelos should belong to Hotel Marriott
        for vuelo in data:
            assert vuelo['proyecto_id'] == 'hotel-marriott-001'
        print(f"Found {len(data)} vuelos for Hotel Marriott")
    
    def test_get_vuelo_by_id(self):
        """Test GET /api/vuelos/{id} - get specific vuelo"""
        # First get list to find a valid ID
        response = requests.get(f"{BASE_URL}/api/vuelos")
        assert response.status_code == 200
        vuelos = response.json()
        
        if len(vuelos) > 0:
            vuelo_id = vuelos[0]['id']
            response = requests.get(f"{BASE_URL}/api/vuelos/{vuelo_id}")
            assert response.status_code == 200
            data = response.json()
            assert data['id'] == vuelo_id
            print(f"Retrieved vuelo: {vuelo_id}")
    
    def test_get_vuelo_not_found(self):
        """Test GET /api/vuelos/{id} - non-existent vuelo returns 404"""
        response = requests.get(f"{BASE_URL}/api/vuelos/non-existent-id")
        assert response.status_code == 404
        print("404 for non-existent vuelo verified")


class TestEstadisticasEndpoints:
    """Tests for /api/estadisticas endpoints"""
    
    def test_get_estadisticas_resumen(self):
        """Test GET /api/estadisticas/resumen - verify KPI data"""
        response = requests.get(f"{BASE_URL}/api/estadisticas/resumen")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert 'total_proyectos' in data
        assert 'total_vuelos' in data
        assert 'avance_promedio' in data
        assert 'volumetria_total' in data
        
        # Verify values for single Hotel Marriott project
        assert data['total_proyectos'] >= 1
        assert data['total_vuelos'] >= 1
        assert data['avance_promedio'] == 40.0  # Hotel Marriott has 40% progress
        
        # Verify volumetria_total structure
        vol = data['volumetria_total']
        assert 'excavacion' in vol
        assert 'relleno' in vol
        assert 'materiales' in vol
        
        print(f"Estadísticas: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
