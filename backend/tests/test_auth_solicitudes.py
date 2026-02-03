"""
Backend API Tests for DrON Topografía - Authentication and Solicitudes de Vuelo
Tests for JWT auth, role-based access, and solicitudes-vuelo endpoints
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


class TestAuthEndpoints:
    """Tests for /api/auth endpoints"""
    
    def test_login_admin_success(self):
        """Test admin login with correct credentials"""
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
        assert user["activo"] == True
        assert "nombre" in user
        print(f"Admin login successful: {user['nombre']} (rol: {user['rol']})")
    
    def test_login_client_success(self):
        """Test client login with correct credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify token structure
        assert "access_token" in data
        assert "token_type" in data
        
        # Verify user data
        user = data["user"]
        assert user["email"] == CLIENT_EMAIL
        assert user["rol"] == "client"
        assert user["activo"] == True
        print(f"Client login successful: {user['nombre']} (rol: {user['rol']})")
    
    def test_login_invalid_email(self):
        """Test login with non-existent email"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "anypassword"
        })
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        print(f"Invalid email login rejected: {data['detail']}")
    
    def test_login_invalid_password(self):
        """Test login with wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        print(f"Invalid password login rejected: {data['detail']}")
    
    def test_get_me_with_admin_token(self):
        """Test /api/auth/me endpoint with admin token"""
        # First login to get token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = login_response.json()["access_token"]
        
        # Get user info
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == ADMIN_EMAIL
        assert data["rol"] == "admin"
        print(f"Auth/me returned: {data['nombre']} ({data['rol']})")
    
    def test_get_me_with_client_token(self):
        """Test /api/auth/me endpoint with client token"""
        # First login to get token
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": CLIENT_EMAIL,
            "password": CLIENT_PASSWORD
        })
        token = login_response.json()["access_token"]
        
        # Get user info
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == CLIENT_EMAIL
        assert data["rol"] == "client"
        print(f"Auth/me returned: {data['nombre']} ({data['rol']})")
    
    def test_get_me_without_token(self):
        """Test /api/auth/me endpoint without token - should fail"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403]
        print("Unauthorized access to /auth/me correctly rejected")
    
    def test_get_me_with_invalid_token(self):
        """Test /api/auth/me endpoint with invalid token"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": "Bearer invalid_token_here"
        })
        assert response.status_code == 401
        print("Invalid token correctly rejected")


class TestSolicitudesVueloEndpoints:
    """Tests for /api/solicitudes-vuelo endpoints"""
    
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
    
    def test_admin_can_list_all_solicitudes(self, admin_token):
        """Test that admin can see all solicitudes"""
        response = requests.get(f"{BASE_URL}/api/solicitudes-vuelo", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Admin can see {len(data)} solicitudes")
    
    def test_client_can_list_own_solicitudes(self, client_token):
        """Test that client can only see their own solicitudes"""
        response = requests.get(f"{BASE_URL}/api/solicitudes-vuelo", headers={
            "Authorization": f"Bearer {client_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Client should only see their own solicitudes (may be empty)
        print(f"Client can see {len(data)} of their own solicitudes")
    
    def test_client_can_create_solicitud(self, client_token):
        """Test that client can create a new solicitud de vuelo"""
        test_id = uuid.uuid4().hex[:8]
        solicitud_data = {
            "nombre_proyecto": f"TEST_Proyecto_{test_id}",
            "fecha_inicio_proyecto": "2025-03-01",
            "fecha_fin_proyecto": "2025-09-30",
            "fecha_vuelo_deseada": "2025-03-15",
            "hora_preferencia": "09:00",
            "notas": "Test solicitud created by pytest"
        }
        
        response = requests.post(f"{BASE_URL}/api/solicitudes-vuelo", 
            json=solicitud_data,
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] in ["success", "partial"]
        assert "solicitud_id" in data
        print(f"Client created solicitud: {data['solicitud_id']}")
        
        # Store for cleanup
        return data["solicitud_id"]
    
    def test_admin_can_update_solicitud_estado(self, admin_token):
        """Test that admin can update solicitud estado (confirm/reject)"""
        # First get list of solicitudes
        response = requests.get(f"{BASE_URL}/api/solicitudes-vuelo", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        solicitudes = response.json()
        
        if len(solicitudes) == 0:
            pytest.skip("No solicitudes to test with")
        
        # Find a pendiente solicitud
        pendiente = next((s for s in solicitudes if s["estado"] == "pendiente"), None)
        if not pendiente:
            pytest.skip("No pending solicitudes to test with")
        
        solicitud_id = pendiente["id"]
        original_estado = pendiente["estado"]
        
        # Update to confirmado
        response = requests.put(
            f"{BASE_URL}/api/solicitudes-vuelo/{solicitud_id}/estado",
            json={"estado": "confirmado", "comentario_admin": "Test confirmation"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["estado"] == "confirmado"
        print(f"Admin updated solicitud {solicitud_id} to confirmado")
        
        # Revert to original estado
        response = requests.put(
            f"{BASE_URL}/api/solicitudes-vuelo/{solicitud_id}/estado",
            json={"estado": original_estado},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print(f"Reverted solicitud to {original_estado}")
    
    def test_client_cannot_update_solicitud_estado(self, client_token):
        """Test that client cannot update solicitud estado (admin only)"""
        # First get list of solicitudes (as admin to find one)
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        admin_token = admin_response.json()["access_token"]
        
        response = requests.get(f"{BASE_URL}/api/solicitudes-vuelo", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        solicitudes = response.json()
        
        if len(solicitudes) == 0:
            pytest.skip("No solicitudes to test with")
        
        solicitud_id = solicitudes[0]["id"]
        
        # Try to update as client - should fail
        response = requests.put(
            f"{BASE_URL}/api/solicitudes-vuelo/{solicitud_id}/estado",
            json={"estado": "confirmado"},
            headers={"Authorization": f"Bearer {client_token}"}
        )
        assert response.status_code == 403
        print("Client correctly denied from updating solicitud estado")
    
    def test_update_solicitud_invalid_estado(self, admin_token):
        """Test that invalid estado values are rejected"""
        # Get a solicitud
        response = requests.get(f"{BASE_URL}/api/solicitudes-vuelo", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        solicitudes = response.json()
        
        if len(solicitudes) == 0:
            pytest.skip("No solicitudes to test with")
        
        solicitud_id = solicitudes[0]["id"]
        
        # Try invalid estado
        response = requests.put(
            f"{BASE_URL}/api/solicitudes-vuelo/{solicitud_id}/estado",
            json={"estado": "invalid_estado"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 400
        print("Invalid estado correctly rejected")


class TestAdminOnlyEndpoints:
    """Tests for admin-only endpoints"""
    
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
        """Test that admin can list all users"""
        response = requests.get(f"{BASE_URL}/api/auth/users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # At least admin and client
        
        # Verify user structure (no password_hash)
        for user in data:
            assert "email" in user
            assert "rol" in user
            assert "password_hash" not in user
        print(f"Admin can see {len(data)} users")
    
    def test_client_cannot_list_users(self, client_token):
        """Test that client cannot list users"""
        response = requests.get(f"{BASE_URL}/api/auth/users", headers={
            "Authorization": f"Bearer {client_token}"
        })
        assert response.status_code == 403
        print("Client correctly denied from listing users")


class TestRegistration:
    """Tests for user registration"""
    
    def test_register_new_user(self):
        """Test registering a new user"""
        test_id = uuid.uuid4().hex[:8]
        new_user = {
            "email": f"TEST_user_{test_id}@test.com",
            "password": "testpassword123",
            "nombre": f"Test User {test_id}",
            "rol": "client"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=new_user)
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == new_user["email"]
        assert data["user"]["rol"] == "client"
        print(f"Registered new user: {data['user']['email']}")
    
    def test_register_duplicate_email(self):
        """Test that duplicate email registration fails"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": ADMIN_EMAIL,  # Already exists
            "password": "anypassword",
            "nombre": "Duplicate User"
        })
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        print(f"Duplicate email registration rejected: {data['detail']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
