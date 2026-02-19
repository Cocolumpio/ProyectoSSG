"""
Tests for chunked upload feature for large PLY files.
Tests init-upload, upload-chunk, and complete-upload endpoints.
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@dron.mx"
ADMIN_PASSWORD = "admin123"

# Test project and avance IDs (Acuarela project, Semana 1)
TEST_PROJECT_ID = "aa547723-9d64-4d4d-8b6a-ef615941ee05"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_avance_id(api_client, auth_token):
    """Get or create a test avance semanal for upload testing"""
    # First, get existing avances
    response = api_client.get(
        f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    if response.status_code == 200:
        avances = response.json()
        if avances:
            # Use the first avance
            return avances[0]["id"]
    
    # Create a new avance if none exists
    response = api_client.post(
        f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales",
        json={
            "semana": 99,  # Test semana
            "fecha": "2025-01-15",
            "descripcion": "Test avance for chunked upload"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    if response.status_code in [200, 201]:
        return response.json()["id"]
    
    pytest.skip("Could not get or create test avance")


class TestInitUpload:
    """Tests for init-upload endpoint"""
    
    def test_init_upload_success(self, api_client, auth_token, test_avance_id):
        """Test successful upload initialization"""
        response = api_client.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/init-upload",
            params={
                "filename": "test_model.ply",
                "total_size": 10485760,  # 10MB
                "total_chunks": 2
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "upload_id" in data
        assert data["message"] == "Upload iniciado"
        assert data["total_chunks"] == 2
        
        # Store upload_id for cleanup
        return data["upload_id"]
    
    def test_init_upload_invalid_extension(self, api_client, auth_token, test_avance_id):
        """Test init-upload rejects invalid file extensions"""
        response = api_client.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/init-upload",
            params={
                "filename": "test_model.exe",  # Invalid extension
                "total_size": 1000,
                "total_chunks": 1
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 400
        assert "Formato no soportado" in response.json()["detail"]
    
    def test_init_upload_avance_not_found(self, api_client, auth_token):
        """Test init-upload with non-existent avance"""
        response = api_client.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/non-existent-id/modelo3d/init-upload",
            params={
                "filename": "test_model.ply",
                "total_size": 1000,
                "total_chunks": 1
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
        assert "Avance semanal no encontrado" in response.json()["detail"]


class TestUploadChunk:
    """Tests for upload-chunk endpoint"""
    
    def test_upload_chunk_success(self, api_client, auth_token, test_avance_id):
        """Test successful chunk upload to GridFS"""
        # First, init upload
        init_response = api_client.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/init-upload",
            params={
                "filename": "test_chunk_upload.ply",
                "total_size": 2000,
                "total_chunks": 2
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert init_response.status_code == 200
        upload_id = init_response.json()["upload_id"]
        
        # Upload first chunk
        chunk_data = b"x" * 1000  # 1KB of data
        files = {"chunk": ("chunk_0", io.BytesIO(chunk_data), "application/octet-stream")}
        data = {"upload_id": upload_id, "chunk_index": 0}
        
        response = requests.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/upload-chunk",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert result["success"] == True
        assert result["chunk_index"] == 0
        assert result["chunk_size"] == 1000
    
    def test_upload_chunk_invalid_session(self, api_client, auth_token, test_avance_id):
        """Test upload-chunk with invalid upload session"""
        chunk_data = b"x" * 100
        files = {"chunk": ("chunk_0", io.BytesIO(chunk_data), "application/octet-stream")}
        data = {"upload_id": "invalid-upload-id", "chunk_index": 0}
        
        response = requests.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/upload-chunk",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
        assert "Sesión de upload no encontrada" in response.json()["detail"]


class TestCompleteUpload:
    """Tests for complete-upload endpoint"""
    
    def test_complete_upload_success(self, api_client, auth_token, test_avance_id):
        """Test successful upload completion - chunks assembled and saved to GridFS"""
        # Init upload
        init_response = api_client.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/init-upload",
            params={
                "filename": "test_complete.ply",
                "total_size": 2000,
                "total_chunks": 2
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert init_response.status_code == 200
        upload_id = init_response.json()["upload_id"]
        
        # Upload both chunks
        for i in range(2):
            chunk_data = f"chunk_{i}_data_".encode() * 100  # ~1.4KB each
            files = {"chunk": (f"chunk_{i}", io.BytesIO(chunk_data), "application/octet-stream")}
            data = {"upload_id": upload_id, "chunk_index": i}
            
            chunk_response = requests.post(
                f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/upload-chunk",
                files=files,
                data=data,
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            assert chunk_response.status_code == 200, f"Chunk {i} upload failed: {chunk_response.text}"
        
        # Complete upload
        complete_response = api_client.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/complete-upload",
            params={"upload_id": upload_id},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert complete_response.status_code == 200, f"Complete failed: {complete_response.text}"
        
        result = complete_response.json()
        assert result["success"] == True
        assert "url" in result
        assert result["url"].startswith("/api/modelos3d/gridfs/")
        assert "filename" in result
        assert result["filename"].endswith(".ply")
        assert "size_mb" in result
    
    def test_complete_upload_missing_chunks(self, api_client, auth_token, test_avance_id):
        """Test complete-upload fails when chunks are missing"""
        # Init upload with 3 chunks
        init_response = api_client.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/init-upload",
            params={
                "filename": "test_missing.ply",
                "total_size": 3000,
                "total_chunks": 3
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert init_response.status_code == 200
        upload_id = init_response.json()["upload_id"]
        
        # Upload only chunk 0 (skip 1 and 2)
        chunk_data = b"chunk_0_data" * 100
        files = {"chunk": ("chunk_0", io.BytesIO(chunk_data), "application/octet-stream")}
        data = {"upload_id": upload_id, "chunk_index": 0}
        
        requests.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/upload-chunk",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Try to complete - should fail
        complete_response = api_client.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/complete-upload",
            params={"upload_id": upload_id},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert complete_response.status_code == 400
        assert "Faltan chunks" in complete_response.json()["detail"]
    
    def test_complete_upload_invalid_session(self, api_client, auth_token, test_avance_id):
        """Test complete-upload with invalid session"""
        response = api_client.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/complete-upload",
            params={"upload_id": "invalid-session-id"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 404
        assert "Sesión de upload no encontrada" in response.json()["detail"]


class TestChunksCleanup:
    """Tests for temporary chunks cleanup after upload completion"""
    
    def test_chunks_deleted_after_complete(self, api_client, auth_token, test_avance_id):
        """Test that temporary chunks are deleted from GridFS after completion"""
        # Init upload
        init_response = api_client.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/init-upload",
            params={
                "filename": "test_cleanup.ply",
                "total_size": 1000,
                "total_chunks": 1
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        upload_id = init_response.json()["upload_id"]
        
        # Upload chunk
        chunk_data = b"cleanup_test_data" * 50
        files = {"chunk": ("chunk_0", io.BytesIO(chunk_data), "application/octet-stream")}
        data = {"upload_id": upload_id, "chunk_index": 0}
        
        requests.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/upload-chunk",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Complete upload
        complete_response = api_client.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/complete-upload",
            params={"upload_id": upload_id},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert complete_response.status_code == 200
        
        # Verify the final file is accessible
        result = complete_response.json()
        file_url = result["url"]
        
        # Try to access the final file
        file_response = requests.get(
            f"{BASE_URL}{file_url}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert file_response.status_code == 200, "Final file should be accessible"


class TestAvanceUpdate:
    """Tests for avance semanal update after upload"""
    
    def test_avance_updated_with_model_url(self, api_client, auth_token, test_avance_id):
        """Test that avance semanal is updated with model URL after upload"""
        # Init upload
        init_response = api_client.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/init-upload",
            params={
                "filename": "test_avance_update.ply",
                "total_size": 500,
                "total_chunks": 1
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        upload_id = init_response.json()["upload_id"]
        
        # Upload chunk
        chunk_data = b"avance_update_test" * 30
        files = {"chunk": ("chunk_0", io.BytesIO(chunk_data), "application/octet-stream")}
        data = {"upload_id": upload_id, "chunk_index": 0}
        
        requests.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/upload-chunk",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Complete upload
        complete_response = api_client.post(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales/{test_avance_id}/modelo3d/complete-upload",
            params={"upload_id": upload_id},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert complete_response.status_code == 200
        
        # Get avance and verify model URL is set
        avance_response = api_client.get(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert avance_response.status_code == 200
        avances = avance_response.json()
        
        # Find our test avance
        test_avance = next((a for a in avances if a["id"] == test_avance_id), None)
        assert test_avance is not None
        
        # Verify model URL is set
        assert test_avance.get("modelo_3d_url") is not None
        assert test_avance["modelo_3d_url"].startswith("/api/modelos3d/gridfs/")
        assert test_avance.get("modelo_3d_tipo") == "gridfs"


class TestGridFSModelAccess:
    """Tests for accessing models stored in GridFS"""
    
    def test_access_model_from_gridfs(self, api_client, auth_token, test_avance_id):
        """Test that uploaded model can be accessed from GridFS"""
        # Get avance to find model URL
        avance_response = api_client.get(
            f"{BASE_URL}/api/proyectos/{TEST_PROJECT_ID}/avances-semanales",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert avance_response.status_code == 200
        avances = avance_response.json()
        
        # Find avance with model
        avance_with_model = next(
            (a for a in avances if a.get("modelo_3d_url") and "gridfs" in a.get("modelo_3d_url", "")),
            None
        )
        
        if not avance_with_model:
            pytest.skip("No avance with GridFS model found")
        
        model_url = avance_with_model["modelo_3d_url"]
        
        # Access the model
        response = requests.get(
            f"{BASE_URL}{model_url}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        assert len(response.content) > 0
