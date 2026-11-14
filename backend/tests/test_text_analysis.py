import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.models.schemas import GeminiTextAnalysisRaw, RiskCategory
from app.services.risk_engine import score_to_category, evaluate_text_risk
from app.services.gemini_service import (
    GeminiConfigurationError,
    GeminiAuthError,
    GeminiQuotaError,
    GeminiUnavailableError,
    GeminiTimeoutError,
    GeminiResponseError
)

client = TestClient(app)

# Sample Mock AI Responses
MOCK_SCAM_AI_RAW = GeminiTextAnalysisRaw(
    summary="The advertisement exhibits multiple critical scam indicators including fake prize lures and urgent fees.",
    estimated_risk_score=90,
    risk_level="HIGH",
    explanation="The copy claims the recipient won an iPhone 15 Pro Max and demands an immediate $1 fee within 15 minutes.",
    detected_claims=["Winner of an iPhone 15 Pro Max", "Requires $1 shipping fee"],
    unrealistic_discounts=["100% off retail price with $1 fee"],
    fake_prize_indicators=["Selected as today's grand prize winner"],
    urgent_payment_requests=["Pay $1 fee immediately within 15 minutes"],
    misleading_statements=["Only 2 items left for claim"],
    suspicious_product_offers=[],
    brand_impersonation=["Apple iPhone 15 Pro Max giveaway"],
    fake_investment_promises=[],
    phishing_language=["Click here immediately to claim your prize"],
    sensitive_info_requests=["Confirm shipping address and payment"],
    manipulative_techniques=["15-minute countdown urgency"],
    recommended_actions=["Do not pay any fees", "Verify on Apple's official website", "Report the SMS as spam"]
)

MOCK_GENUINE_AI_RAW = GeminiTextAnalysisRaw(
    summary="Legitimate promotional copy from a known retailer with reasonable seasonal discounts.",
    estimated_risk_score=15,
    risk_level="LOW",
    explanation="The advertisement promotes a standard 20% discount on clothing with standard free shipping thresholds.",
    detected_claims=["20% off selected styles across womenswear", "Free shipping on orders over $89"],
    unrealistic_discounts=[],
    fake_prize_indicators=[],
    urgent_payment_requests=[],
    misleading_statements=[],
    suspicious_product_offers=[],
    brand_impersonation=[],
    fake_investment_promises=[],
    phishing_language=[],
    sensitive_info_requests=[],
    manipulative_techniques=[],
    recommended_actions=["Ensure checkout is completed through official retailer domain"]
)

# 1. Suspicious Advertisement Text Test
@patch("app.routes.analyze.analyze_text_with_gemini")
def test_suspicious_ad_analysis(mock_gemini):
    mock_gemini.return_value = (MOCK_SCAM_AI_RAW, "gemini-3.8-flash")

    response = client.post("/api/analyze/text", json={
        "text": "CONGRATULATIONS! You won an Apple iPhone 15 Pro Max! Pay $1 shipping fee immediately within 15 minutes before prize expires!",
        "source_context": "SMS / WhatsApp"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 61
    assert data["risk_category"] == "High"
    assert data["risk_level"] == "HIGH"
    assert "fake prize" in data["summary"].lower() or "scam" in data["summary"].lower()
    assert len(data["indicators"]) > 0
    assert len(data["recommendations"]) > 0
    assert data["gemini_used"] is True
    assert data["model_used"] == "gemini-3.8-flash"

# 2. Genuine-Looking Advertisement Text Test
@patch("app.routes.analyze.analyze_text_with_gemini")
def test_genuine_ad_analysis(mock_gemini):
    mock_gemini.return_value = (MOCK_GENUINE_AI_RAW, "gemini-3.8-flash")

    response = client.post("/api/analyze/text", json={
        "text": "Summer clearance sale at Nordstrom. Enjoy 20% off selected styles across womenswear. Free shipping on orders over $89.",
        "source_context": "Social Media"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] <= 30
    assert data["risk_category"] == "Low"
    assert data["risk_level"] == "LOW"
    assert data["gemini_used"] is True

# 3. Empty and Short Input Validation
def test_empty_and_short_input_validation():
    # Empty string
    res1 = client.post("/api/analyze/text", json={"text": ""})
    assert res1.status_code == 422 or res1.status_code == 400

    # Short string (< 5 chars)
    res2 = client.post("/api/analyze/text", json={"text": "Hey"})
    assert res2.status_code == 422 or res2.status_code == 400

    # Whitespace only
    res3 = client.post("/api/analyze/text", json={"text": "      "})
    assert res3.status_code == 400

# 4. Input Length Limit Validation (> 10000 characters)
def test_oversized_input_validation():
    long_text = "Free discount offer! " * 600  # > 12000 chars
    res = client.post("/api/analyze/text", json={"text": long_text})
    assert res.status_code == 422 or res.status_code == 400

# 5. Invalid API Configuration Test
@patch("app.routes.analyze.analyze_text_with_gemini")
def test_unconfigured_api_error(mock_gemini):
    mock_gemini.side_effect = GeminiConfigurationError("Gemini API key is not configured.")

    res = client.post("/api/analyze/text", json={"text": "Claim your discount coupon now at store."})
    assert res.status_code == 503
    assert "Gemini API key is not configured" in res.json()["detail"]

# 6. Gemini API Errors (Quota, Auth, Unavailable)
@patch("app.routes.analyze.analyze_text_with_gemini")
def test_gemini_quota_exceeded(mock_gemini):
    mock_gemini.side_effect = GeminiQuotaError("Gemini API rate limit exceeded.")

    res = client.post("/api/analyze/text", json={"text": "Exclusive flash sale on sneakers."})
    assert res.status_code == 429
    assert "rate limit exceeded" in res.json()["detail"].lower()

@patch("app.routes.analyze.analyze_text_with_gemini")
def test_gemini_auth_error(mock_gemini):
    mock_gemini.side_effect = GeminiAuthError("Invalid Gemini API key.")

    res = client.post("/api/analyze/text", json={"text": "Exclusive flash sale on sneakers."})
    assert res.status_code == 401
    assert "Invalid Gemini API key" in res.json()["detail"]

@patch("app.routes.analyze.analyze_text_with_gemini")
def test_gemini_model_unavailable(mock_gemini):
    mock_gemini.side_effect = GeminiUnavailableError("Gemini model is currently experiencing high demand.")

    res = client.post("/api/analyze/text", json={"text": "Exclusive flash sale on sneakers."})
    assert res.status_code == 503
    assert "high demand" in res.json()["detail"]

@patch("app.routes.analyze.analyze_text_with_gemini")
def test_gemini_timeout_error(mock_gemini):
    mock_gemini.side_effect = GeminiTimeoutError("The request to Gemini API timed out.")

    res = client.post("/api/analyze/text", json={"text": "Exclusive flash sale on sneakers."})
    assert res.status_code == 504
    assert "timed out" in res.json()["detail"].lower()

@patch("app.routes.analyze.analyze_text_with_gemini")
def test_gemini_invalid_structured_response(mock_gemini):
    mock_gemini.side_effect = GeminiResponseError("Gemini output does not match expected schema.")

    res = client.post("/api/analyze/text", json={"text": "Exclusive flash sale on sneakers."})
    assert res.status_code == 502
    assert "does not match expected schema" in res.json()["detail"]

# 7. Risk Score and Category Consistency Tests
def test_risk_score_consistency():
    # Low Risk: 0 to 30
    assert score_to_category(0) == RiskCategory.LOW
    assert score_to_category(15) == RiskCategory.LOW
    assert score_to_category(30) == RiskCategory.LOW

    # Medium Risk: 31 to 60
    assert score_to_category(31) == RiskCategory.MEDIUM
    assert score_to_category(45) == RiskCategory.MEDIUM
    assert score_to_category(60) == RiskCategory.MEDIUM

    # High Risk: 61 to 100
    assert score_to_category(61) == RiskCategory.HIGH
    assert score_to_category(85) == RiskCategory.HIGH
    assert score_to_category(100) == RiskCategory.HIGH

def test_evaluate_text_risk_consistency():
    assessment, findings = evaluate_text_risk(
        text="Normal sale 10% off at supermarket",
        ai_result=MOCK_GENUINE_AI_RAW
    )
    assert 0 <= assessment.risk_score <= 100
    assert assessment.risk_category == score_to_category(assessment.risk_score)
    assert assessment.risk_level == assessment.risk_category.value.upper()
