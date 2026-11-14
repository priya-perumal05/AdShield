import os
import sys
import io
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.models.schemas import GeminiImageAnalysisRaw, RiskCategory, SuspiciousIndicator
from app.services.risk_engine import score_to_category, evaluate_image_risk
from app.services.gemini_service import (
    GeminiConfigurationError,
    GeminiAuthError,
    GeminiQuotaError,
    GeminiUnavailableError,
    GeminiTimeoutError,
    GeminiResponseError
)

client = TestClient(app)

def create_in_memory_image(format="PNG", size=(200, 200), color=(255, 0, 0), text=None) -> bytes:
    """Generates valid image bytes in memory using Pillow without external test files."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    if text:
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), text, fill=(255, 255, 255))
    img.save(buf, format=format)
    return buf.getvalue()

# Mock AI Responses
MOCK_SCAM_AI_RAW = GeminiImageAnalysisRaw(
    summary="Graphic banner displays deceptive prize claim and urgent payment prompt.",
    estimated_risk_score=88,
    risk_level="HIGH",
    visual_observations=["Bold red banner", "iPhone graphic with 100% off ribbon", "Countdown timer icon"],
    detected_claims=["Claim your free smartphone now", "Pay $1 activation fee"],
    unrealistic_discounts=["100% free with fee"],
    fake_prize_indicators=["Grand prize winner claim"],
    urgent_payment_requests=["Pay $1 fee immediately"],
    suspicious_payment_instructions=["Wire transfer or gift card activation"],
    brand_impersonation=["Apple logo imitation"],
    misleading_representations=["Guaranteed win badge"],
    suspicious_contact_details=[],
    visual_inconsistencies=[],
    sensitive_info_requests=["Credit card request badge"],
    phishing_indicators=["Fake countdown timer"],
    explanation="The banner mimics brand graphics to induce immediate payment under false pretenses.",
    recommendations=["Do not enter payment details", "Report advertisement"]
)

MOCK_SAFE_AI_RAW = GeminiImageAnalysisRaw(
    summary="Standard seasonal promotional banner with standard discounts.",
    estimated_risk_score=15,
    risk_level="LOW",
    visual_observations=["Clean minimalist layout", "Retail clothing collection", "Standard brand logo"],
    detected_claims=["Summer Sale 20% Off"],
    unrealistic_discounts=[],
    fake_prize_indicators=[],
    urgent_payment_requests=[],
    suspicious_payment_instructions=[],
    brand_impersonation=[],
    misleading_representations=[],
    suspicious_contact_details=[],
    visual_inconsistencies=[],
    sensitive_info_requests=[],
    phishing_indicators=[],
    explanation="Standard commercial promotion adhering to standard retail practices.",
    recommendations=["Verify secure checkout on official site"]
)


# Test 1: Valid JPEG image upload
@patch("app.routes.analyze.analyze_image_with_gemini")
@patch("app.routes.analyze.extract_text_from_image")
def test_valid_jpeg_upload(mock_ocr, mock_vision):
    mock_vision.return_value = (MOCK_SCAM_AI_RAW, "gemini-3.5-flash")
    mock_ocr.return_value = {
        "success": True,
        "status": "SUCCESS",
        "text": "CLAIM YOUR FREE IPHONE",
        "confidence": 85.0,
        "word_count": 4,
        "error": None
    }

    jpeg_bytes = create_in_memory_image(format="JPEG", color=(0, 100, 200))
    response = client.post(
        "/api/analyze/image",
        files={"file": ("promo.jpg", jpeg_bytes, "image/jpeg")},
        data={"source_context": "Instagram"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "image/jpeg"
    assert data["risk_score"] == 88
    assert data["risk_category"] == "High"
    assert data["risk_level"] == "HIGH"
    assert data["ocr_status"] == "SUCCESS"
    assert data["extracted_text"] == "CLAIM YOUR FREE IPHONE"
    assert data["gemini_vision_used"] is True
    assert data["ocr_used"] is True


# Test 2: Valid PNG image upload
@patch("app.routes.analyze.analyze_image_with_gemini")
@patch("app.routes.analyze.extract_text_from_image")
def test_valid_png_upload(mock_ocr, mock_vision):
    mock_vision.return_value = (MOCK_SAFE_AI_RAW, "gemini-3.5-flash")
    mock_ocr.return_value = {
        "success": True,
        "status": "SUCCESS",
        "text": "Summer Sale 20% Off",
        "confidence": 92.0,
        "word_count": 4,
        "error": None
    }

    png_bytes = create_in_memory_image(format="PNG", color=(50, 150, 50))
    response = client.post(
        "/api/analyze/image",
        files={"file": ("summer_sale.png", png_bytes, "image/png")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "image/png"
    assert data["risk_score"] == 15
    assert data["risk_category"] == "Low"
    assert data["risk_level"] == "LOW"
    assert len(data["indicators"]) == 0


# Test 3: Valid WEBP image upload
@patch("app.routes.analyze.analyze_image_with_gemini")
@patch("app.routes.analyze.extract_text_from_image")
def test_valid_webp_upload(mock_ocr, mock_vision):
    mock_vision.return_value = (MOCK_SAFE_AI_RAW, "gemini-3.5-flash")
    mock_ocr.return_value = {
        "success": True,
        "status": "SUCCESS",
        "text": "Special Deal",
        "confidence": 80.0,
        "word_count": 2,
        "error": None
    }

    webp_bytes = create_in_memory_image(format="WEBP", color=(100, 100, 100))
    response = client.post(
        "/api/analyze/image",
        files={"file": ("deal.webp", webp_bytes, "image/webp")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "image/webp"
    assert data["risk_score"] <= 30


# Test 4: Unsupported image formats (GIF, BMP, TIFF, SVG) - expect 400
@pytest.mark.parametrize("mime_type, filename", [
    ("image/gif", "banner.gif"),
    ("image/bmp", "banner.bmp"),
    ("image/tiff", "banner.tiff"),
    ("image/svg+xml", "banner.svg"),
])
def test_unsupported_image_format(mime_type, filename):
    dummy_bytes = b"GIF89a\x01\x00\x01\x00\x00\x00\x00!"
    response = client.post(
        "/api/analyze/image",
        files={"file": (filename, dummy_bytes, mime_type)}
    )

    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


# Test 5: Corrupted image file bytes - expect 400
def test_corrupted_image_bytes():
    corrupted_bytes = b"\xff\xd8\xff\xe0CORRUPTED_TRUNCATED_BINARY_DATA"
    response = client.post(
        "/api/analyze/image",
        files={"file": ("corrupt.jpg", corrupted_bytes, "image/jpeg")}
    )

    assert response.status_code == 400
    assert "corrupted" in response.json()["detail"].lower()


# Test 6: Oversized image file (> 10MB) - expect 400
def test_oversized_image_upload():
    # 10MB + 1KB
    large_bytes = b"0" * (10 * 1024 * 1024 + 1024)
    response = client.post(
        "/api/analyze/image",
        files={"file": ("large.png", large_bytes, "image/png")}
    )

    assert response.status_code == 400
    assert "exceeds maximum allowed size" in response.json()["detail"]


# Test 7: Image with detectable text (OCR text extraction)
@patch("app.routes.analyze.analyze_image_with_gemini")
@patch("app.routes.analyze.extract_text_from_image")
def test_image_with_detectable_text(mock_ocr, mock_vision):
    mock_vision.return_value = (MOCK_SCAM_AI_RAW, "gemini-3.5-flash")
    mock_ocr.return_value = {
        "success": True,
        "status": "SUCCESS",
        "text": "You won selected as winner pay $1 shipping fee immediately",
        "confidence": 88.5,
        "word_count": 10,
        "error": None
    }

    png_bytes = create_in_memory_image(format="PNG", text="WINNER PAY $1 FEE")
    response = client.post(
        "/api/analyze/image",
        files={"file": ("winner.png", png_bytes, "image/png")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ocr_status"] == "SUCCESS"
    assert data["ocr_confidence"] == 88.5
    assert data["extracted_text"] is not None
    assert data["findings"]["ocr_word_count"] == 10
    assert data["ocr_used"] is True


# Test 8: Image with no text detected (OCR returns empty, Gemini still runs)
@patch("app.routes.analyze.analyze_image_with_gemini")
@patch("app.routes.analyze.extract_text_from_image")
def test_image_with_no_text_detected(mock_ocr, mock_vision):
    mock_vision.return_value = (MOCK_SAFE_AI_RAW, "gemini-3.5-flash")
    mock_ocr.return_value = {
        "success": True,
        "status": "NO_TEXT_DETECTED",
        "text": None,
        "confidence": None,
        "word_count": 0,
        "error": None
    }

    png_bytes = create_in_memory_image(format="PNG", color=(10, 20, 30))
    response = client.post(
        "/api/analyze/image",
        files={"file": ("scenery.png", png_bytes, "image/png")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ocr_status"] == "NO_TEXT_DETECTED"
    assert data["extracted_text"] is None
    assert data["ocr_used"] is False
    assert data["gemini_vision_used"] is True
    assert data["risk_score"] == 15


# Test 9: Tesseract executable missing/unavailable - graceful fallback, no crash
@patch("app.routes.analyze.analyze_image_with_gemini")
@patch("app.routes.analyze.extract_text_from_image")
def test_tesseract_unavailable_graceful_fallback(mock_ocr, mock_vision):
    mock_vision.return_value = (MOCK_SCAM_AI_RAW, "gemini-3.5-flash")
    mock_ocr.return_value = {
        "success": False,
        "status": "UNAVAILABLE",
        "text": None,
        "confidence": None,
        "word_count": 0,
        "error": "Tesseract OCR executable not found on system."
    }

    png_bytes = create_in_memory_image(format="PNG")
    response = client.post(
        "/api/analyze/image",
        files={"file": ("ad.png", png_bytes, "image/png")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ocr_status"] == "UNAVAILABLE"
    assert data["ocr_used"] is False
    assert data["gemini_vision_used"] is True
    assert data["risk_score"] == 88


# Test 10: Successful Gemini Vision response parsing into Pydantic schema
def test_gemini_vision_pydantic_schema_validation():
    raw_data = {
        "summary": "Suspicious discount advert",
        "estimated_risk_score": 75,
        "risk_level": "HIGH",
        "visual_observations": ["90% off graphic", "Countdown clock"],
        "detected_claims": ["Huge 90% savings"],
        "unrealistic_discounts": ["90% off luxury watch"],
        "fake_prize_indicators": [],
        "urgent_payment_requests": ["Pay now"],
        "suspicious_payment_instructions": [],
        "brand_impersonation": ["Rolex imitation"],
        "misleading_representations": [],
        "suspicious_contact_details": [],
        "visual_inconsistencies": [],
        "sensitive_info_requests": [],
        "phishing_indicators": [],
        "explanation": "High risk of counterfeit goods.",
        "recommendations": ["Do not purchase"]
    }
    parsed = GeminiImageAnalysisRaw(**raw_data)
    assert parsed.estimated_risk_score == 75
    assert parsed.risk_level == "HIGH"
    assert len(parsed.unrealistic_discounts) == 1
    assert parsed.brand_impersonation == ["Rolex imitation"]


# Test 11: Gemini API failure handling (401, 429, 502, 503, 504)
@pytest.mark.parametrize("error_cls, status_code", [
    (GeminiAuthError("Invalid API key"), 401),
    (GeminiQuotaError("Quota exceeded"), 429),
    (GeminiUnavailableError("Model overloaded"), 503),
    (GeminiTimeoutError("Request timed out"), 504),
    (GeminiResponseError("Invalid JSON returned"), 502),
])
@patch("app.routes.analyze.analyze_image_with_gemini")
@patch("app.routes.analyze.extract_text_from_image")
def test_gemini_api_failures(mock_ocr, mock_vision, error_cls, status_code):
    mock_ocr.return_value = {"success": True, "status": "SUCCESS", "text": "Ad", "confidence": 90, "word_count": 1}
    mock_vision.side_effect = error_cls

    png_bytes = create_in_memory_image(format="PNG")
    response = client.post(
        "/api/analyze/image",
        files={"file": ("ad.png", png_bytes, "image/png")}
    )

    assert response.status_code == status_code


# Test 12: Risk score calculation consistency (0-30 Low, 31-60 Medium, 61-100 High)
def test_risk_score_category_consistency():
    assert score_to_category(0) == RiskCategory.LOW
    assert score_to_category(30) == RiskCategory.LOW
    assert score_to_category(31) == RiskCategory.MEDIUM
    assert score_to_category(60) == RiskCategory.MEDIUM
    assert score_to_category(61) == RiskCategory.HIGH
    assert score_to_category(100) == RiskCategory.HIGH


# Test 13: Indicator deduplication between OCR heuristics and Gemini Vision
def test_indicator_deduplication():
    # OCR text containing sensitive info request
    ocr_text = "ENTER YOUR SSN AND PASSWORD TO CLAIM"
    # AI returns duplicate finding for sensitive info requests
    ai_raw = GeminiImageAnalysisRaw(
        summary="Phishing attempt",
        estimated_risk_score=95,
        risk_level="HIGH",
        visual_observations=["Login box"],
        detected_claims=[],
        unrealistic_discounts=[],
        fake_prize_indicators=[],
        urgent_payment_requests=[],
        suspicious_payment_instructions=[],
        brand_impersonation=[],
        misleading_representations=[],
        suspicious_contact_details=[],
        visual_inconsistencies=[],
        sensitive_info_requests=["Enter your SSN and password to claim"],
        phishing_indicators=[],
        explanation="Deceptive form harvesting SSN and password",
        recommendations=["Never submit SSN"]
    )

    assessment, findings, detail = evaluate_image_risk(
        ocr_text=ocr_text,
        ocr_confidence=90.0,
        ocr_status="SUCCESS",
        ai_result=ai_raw
    )

    # Both rule heuristics and AI flagged SSN request, deduplication should prevent duplicates
    descriptions = [ind.description.lower() for ind in assessment.indicators]
    # Check that similar descriptions are not duplicated
    assert len(assessment.indicators) == len(set(ind.title for ind in assessment.indicators))
    assert assessment.risk_score >= 90
    assert assessment.risk_category == RiskCategory.HIGH
