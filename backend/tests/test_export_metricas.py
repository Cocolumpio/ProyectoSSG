"""
Test suite for DrON Topografía export endpoints:
- GET /api/exportar/metricas-excel - Export metrics to Excel
- GET /api/exportar/metricas-pdf - Export metrics to PDF
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestExportMetricas:
    """Tests for export endpoints - Excel and PDF generation"""
    
    def test_export_excel_returns_200(self):
        """Test that Excel export endpoint returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/exportar/metricas-excel")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ Excel export returned status 200")
    
    def test_export_excel_content_type(self):
        """Test that Excel export returns correct content type"""
        response = requests.get(f"{BASE_URL}/api/exportar/metricas-excel")
        content_type = response.headers.get('Content-Type', '')
        expected_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert expected_type in content_type, f"Expected {expected_type}, got {content_type}"
        print(f"✓ Excel export has correct content type: {content_type}")
    
    def test_export_excel_file_size(self):
        """Test that Excel export returns a file with content"""
        response = requests.get(f"{BASE_URL}/api/exportar/metricas-excel")
        file_size = len(response.content)
        assert file_size > 1000, f"Excel file too small: {file_size} bytes"
        print(f"✓ Excel file size: {file_size} bytes")
    
    def test_export_excel_valid_xlsx_header(self):
        """Test that Excel export returns valid XLSX file (ZIP format)"""
        response = requests.get(f"{BASE_URL}/api/exportar/metricas-excel")
        # XLSX files are ZIP archives, they start with "PK"
        assert response.content[:2] == b'PK', "Excel file does not have valid ZIP/XLSX header"
        print(f"✓ Excel file has valid XLSX header (PK)")
    
    def test_export_excel_content_disposition(self):
        """Test that Excel export has Content-Disposition header for download"""
        response = requests.get(f"{BASE_URL}/api/exportar/metricas-excel")
        content_disp = response.headers.get('Content-Disposition', '')
        assert 'attachment' in content_disp, f"Missing attachment in Content-Disposition: {content_disp}"
        assert '.xlsx' in content_disp, f"Missing .xlsx extension in Content-Disposition: {content_disp}"
        print(f"✓ Excel Content-Disposition: {content_disp}")
    
    def test_export_pdf_returns_200(self):
        """Test that PDF export endpoint returns 200 status"""
        response = requests.get(f"{BASE_URL}/api/exportar/metricas-pdf")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ PDF export returned status 200")
    
    def test_export_pdf_content_type(self):
        """Test that PDF export returns correct content type"""
        response = requests.get(f"{BASE_URL}/api/exportar/metricas-pdf")
        content_type = response.headers.get('Content-Type', '')
        assert "application/pdf" in content_type, f"Expected application/pdf, got {content_type}"
        print(f"✓ PDF export has correct content type: {content_type}")
    
    def test_export_pdf_file_size(self):
        """Test that PDF export returns a file with content"""
        response = requests.get(f"{BASE_URL}/api/exportar/metricas-pdf")
        file_size = len(response.content)
        assert file_size > 1000, f"PDF file too small: {file_size} bytes"
        print(f"✓ PDF file size: {file_size} bytes")
    
    def test_export_pdf_valid_header(self):
        """Test that PDF export returns valid PDF file"""
        response = requests.get(f"{BASE_URL}/api/exportar/metricas-pdf")
        # PDF files start with "%PDF"
        assert response.content[:4] == b'%PDF', "PDF file does not have valid PDF header"
        print(f"✓ PDF file has valid PDF header (%PDF)")
    
    def test_export_pdf_content_disposition(self):
        """Test that PDF export has Content-Disposition header for download"""
        response = requests.get(f"{BASE_URL}/api/exportar/metricas-pdf")
        content_disp = response.headers.get('Content-Disposition', '')
        assert 'attachment' in content_disp, f"Missing attachment in Content-Disposition: {content_disp}"
        assert '.pdf' in content_disp, f"Missing .pdf extension in Content-Disposition: {content_disp}"
        print(f"✓ PDF Content-Disposition: {content_disp}")


class TestExportMetricasDataContent:
    """Tests to verify exported files contain project data"""
    
    def test_excel_contains_project_data(self):
        """Test that Excel file contains data (not empty sheets)"""
        response = requests.get(f"{BASE_URL}/api/exportar/metricas-excel")
        # A valid Excel with data should be larger than a minimal empty workbook
        file_size = len(response.content)
        assert file_size > 5000, f"Excel file seems too small to contain project data: {file_size} bytes"
        print(f"✓ Excel file contains data ({file_size} bytes)")
    
    def test_pdf_contains_project_data(self):
        """Test that PDF file contains data (not empty document)"""
        response = requests.get(f"{BASE_URL}/api/exportar/metricas-pdf")
        # A valid PDF with data should be larger than a minimal empty document
        file_size = len(response.content)
        assert file_size > 3000, f"PDF file seems too small to contain project data: {file_size} bytes"
        print(f"✓ PDF file contains data ({file_size} bytes)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
