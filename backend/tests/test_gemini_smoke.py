import os
import sys
import pytest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.utils.config import get_settings

client = TestClient(app)

@pytest.mark.smoke
def test_real_gemini_api_text_analysis():
    """
    Live smoke test against real Google Gemini API.
    Only runs when GEMINI_API_KEY is configured in backend/.env.
    """
    settings = get_settings()
    if not settings.is_gemini_configured:
        pytest.skip("Skipping live smoke test: GEMINI_API_KEY is not configured.")

    test_payload = {
        "text": "Special holiday deal: 20% discount on all outdoor jacket orders over $100. Visit our official retail store or website.",
        "source_context": "Promotional Email"
    }

    response = client.post("/api/analyze/text", json=test_payload)

    # In case of Free Tier upstream transient 503 or 429 quota exhaustion:
    if response.status_code in (429, 503):
        pytest.skip(f"Live Gemini API temporary status ({response.status_code}): {response.json().get('detail')}")

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    data = response.json()

    # Structural validations
    assert "id" in data
    assert "risk_score" in data
    assert 0 <= data["risk_score"] <= 100
    assert data["risk_category"] in ["Low", "Medium", "High"]
    assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert "summary" in data and len(data["summary"]) > 0
    assert "explanation" in data and len(data["explanation"]) > 0
    assert "recommendations" in data
    assert data["gemini_used"] is True
    assert "model_used" in data
    assert data["model_used"] is not None


@pytest.mark.smoke
def test_real_gemini_api_image_analysis():
    """
    Live smoke test against real Google Gemini Vision API and Tesseract OCR.
    Sends a synthetic promotional graphic generated via Pillow.
    """
    import io
    import time
    from PIL import Image, ImageDraw

    settings = get_settings()
    if not settings.is_gemini_configured:
        pytest.skip("Skipping live smoke test: GEMINI_API_KEY is not configured.")

    # Brief delay to respect rate limit between successive live test cases
    time.sleep(2)

    # Create synthetic banner with clear text
    buf = io.BytesIO()
    img = Image.new("RGB", (400, 150), color=(30, 60, 180))
    draw = ImageDraw.Draw(img)
    draw.text((20, 50), "SPECIAL SALE 50% OFF TODAY", fill=(255, 255, 255))
    img.save(buf, format="PNG")
    image_bytes = buf.getvalue()

    response = client.post(
        "/api/analyze/image",
        files={"file": ("promo_sale.png", image_bytes, "image/png")},
        data={"source_context": "Web Banner"}
    )

    if response.status_code in (429, 503):
        pytest.skip(f"Live Gemini API temporary status ({response.status_code}): {response.json().get('detail')}")

    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    data = response.json()

    assert "id" in data
    assert "risk_score" in data
    assert 0 <= data["risk_score"] <= 100
    assert data["risk_category"] in ["Low", "Medium", "High"]
    assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert "summary" in data and len(data["summary"]) > 0
    assert "image_analysis" in data
    assert "explanation" in data and len(data["explanation"]) > 0
    assert data["gemini_vision_used"] is True
    assert data["gemini_used"] is True
    assert "model_used" in data
    assert data["model_used"] is not None


