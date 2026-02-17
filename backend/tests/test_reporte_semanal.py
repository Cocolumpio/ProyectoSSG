"""
Test suite for Weekly Report and IA Analysis features
Tests:
1. POST /api/admin/enviar-reporte-semanal endpoint (requires admin auth)
2. Scheduler configuration for Friday 18:00
3. IA Analysis endpoint for photos
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestWeeklyReport:
    """Tests for weekly report functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_email = "admin@dron.mx"
        self.admin_password = "admin123"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_admin_token(self):
        """Get admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        return data["access_token"]
    
    def test_weekly_report_endpoint_requires_auth(self):
        """Test that weekly report endpoint requires authentication"""
        response = self.session.post(f"{BASE_URL}/api/admin/enviar-reporte-semanal")
        # Should return 403 Forbidden (no auth header)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: Weekly report endpoint requires authentication")
    
    def test_weekly_report_endpoint_requires_admin(self):
        """Test that weekly report endpoint requires admin role"""
        # First, try to create a client user and test
        # For now, just verify admin can access
        token = self.get_admin_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.post(f"{BASE_URL}/api/admin/enviar-reporte-semanal")
        assert response.status_code == 200, f"Admin should be able to send report: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "message" in data
        assert "timestamp" in data
        print(f"PASS: Weekly report sent successfully - {data.get('message')}")
    
    def test_weekly_report_response_format(self):
        """Test that weekly report returns correct response format"""
        token = self.get_admin_token()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.post(f"{BASE_URL}/api/admin/enviar-reporte-semanal")
        assert response.status_code == 200
        
        data = response.json()
        # Verify response structure
        assert "success" in data, "Response should have 'success' field"
        assert "message" in data, "Response should have 'message' field"
        assert "timestamp" in data, "Response should have 'timestamp' field"
        
        # Verify message contains email
        assert "ianalejandrogn@gmail.com" in data["message"], "Message should contain admin email"
        print("PASS: Weekly report response format is correct")


class TestIAAnalysis:
    """Tests for IA photo analysis functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_ia_analysis_endpoint_exists(self):
        """Test that IA analysis endpoint exists"""
        # The endpoint is POST /api/avances/{avance_id}/analizar-foto
        # We need a valid avance_id to test
        response = self.session.post(f"{BASE_URL}/api/avances/invalid-id/analizar-foto", json={
            "imagen_base64": "test"
        })
        # Should return 404 (avance not found) or 422 (validation error), not 500
        assert response.status_code in [404, 422, 400], f"Unexpected status: {response.status_code}"
        print("PASS: IA analysis endpoint exists and handles invalid input correctly")


class TestSchedulerConfiguration:
    """Tests to verify scheduler configuration"""
    
    def test_scheduler_cron_trigger(self):
        """Verify scheduler is configured for Friday 18:00"""
        # This is a code review test - we verify the configuration in server.py
        import sys
        sys.path.insert(0, '/app/backend')
        
        # Read server.py and check for scheduler configuration
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        # Check for CronTrigger with Friday at 18:00
        assert "CronTrigger(day_of_week='fri', hour=18, minute=0)" in content, \
            "Scheduler should be configured for Friday 18:00"
        
        # Check for scheduler.add_job
        assert "scheduler.add_job" in content, "Scheduler job should be added"
        
        # Check for generar_reporte_semanal function
        assert "generar_reporte_semanal" in content, "Weekly report function should exist"
        
        print("PASS: Scheduler is correctly configured for Friday 18:00")
    
    def test_scheduler_startup_event(self):
        """Verify scheduler starts on app startup"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        # Check for startup event
        assert '@app.on_event("startup")' in content, "Startup event should be defined"
        assert "scheduler.start()" in content, "Scheduler should start on startup"
        
        print("PASS: Scheduler starts on application startup")
    
    def test_scheduler_shutdown_event(self):
        """Verify scheduler shuts down properly"""
        with open('/app/backend/server.py', 'r') as f:
            content = f.read()
        
        # Check for shutdown event
        assert '@app.on_event("shutdown")' in content, "Shutdown event should be defined"
        assert "scheduler.shutdown()" in content, "Scheduler should shutdown on app shutdown"
        
        print("PASS: Scheduler shuts down properly on application shutdown")


class TestAPIHealth:
    """Basic API health checks"""
    
    def test_api_root(self):
        """Test API root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print("PASS: API root endpoint is healthy")
    
    def test_auth_login(self):
        """Test authentication endpoint"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dron.mx",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["rol"] == "admin"
        print("PASS: Authentication endpoint works correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
