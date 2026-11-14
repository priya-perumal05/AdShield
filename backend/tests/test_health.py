import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add backend directory to sys.path so app can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "AdShield" in data["service"]
    assert data["health_check"] == "/api/health"

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "gemini_configured" in data
    assert "safe_browsing_configured" in data
    assert "tesseract_available" in data

def test_url_analysis_validation_invalid_url():
    response = client.post("/api/analyze/url", json={"url": "not-a-valid-url"})
    assert response.status_code == 400
    assert "Invalid URL" in response.json()["detail"]

