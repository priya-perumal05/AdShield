import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import (
    AssessmentStatus,
    RiskCategory,
    SuspiciousIndicator,
    GeminiTextAnalysisRaw,
    GeminiImageAnalysisRaw,
    GeminiUrlAnalysisRaw
)
from app.services.risk_engine import (
    score_to_category,
    deduplicate_indicators,
    calculate_unified_risk_score,
    evaluate_text_risk,
    evaluate_url_risk,
    evaluate_image_risk
)
from app.services.gemini_service import (
    GeminiQuotaError,
    GeminiUnavailableError
)

client = TestClient(app)

MOCK_GENUINE_AI_TEXT = GeminiTextAnalysisRaw(
    summary="Legitimate summer promotional advertisement with standard discounts.",
    estimated_risk_score=10,
    risk_level="LOW",
    explanation="Standard commercial promotion without deceptive urgency, phishing, or unrealistic price claims.",
    detected_claims=["20% off summer apparel"],
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
    recommended_actions=["Enjoy shopping through official store channels."]
)

MOCK_SUSPICIOUS_AI_TEXT = GeminiTextAnalysisRaw(
    summary="Dangerous cryptocurrency doubling phishing attempt requesting credentials.",
    estimated_risk_score=95,
    risk_level="HIGH",
    explanation="The text promises guaranteed crypto returns and asks for urgent payments.",
    detected_claims=["Double your bitcoin in 24 hours"],
    unrealistic_discounts=[],
    fake_prize_indicators=[],
    urgent_payment_requests=["Pay via bitcoin wallet immediately"],
    misleading_statements=["Guaranteed 200% return"],
    suspicious_product_offers=["Crypto multiplier algorithm"],
    brand_impersonation=["Bitcoin Foundation"],
    fake_investment_promises=["Guaranteed double your money"],
    phishing_language=["Enter your private key to verify wallet"],
    sensitive_info_requests=["Wallet private key or PIN"],
    manipulative_techniques=["Only 5 minutes left"],
    recommended_actions=["Do not send crypto or enter credentials."]
)


# Test 1: Genuine advertisement -> Low Risk (0-30)
def test_genuine_advertisement_low_risk():
    text = "Nordstrom Summer Clearance: Enjoy up to 20% off selected designer footwear and apparel. Free shipping on orders over $50."
    assessment, findings = evaluate_text_risk(text, ai_result=MOCK_GENUINE_AI_TEXT)

    assert assessment.status == AssessmentStatus.COMPLETE
    assert assessment.risk_score is not None
    assert assessment.risk_score <= 25
    assert assessment.risk_category == RiskCategory.LOW
    assert assessment.risk_level == "LOW"
    assert "Gemini AI Contextual Analysis" in assessment.checks_completed
    assert len(assessment.checks_unavailable) == 0


# Test 2: Suspicious advertisement -> High Risk (61-100)
def test_suspicious_advertisement_high_risk():
    text = "YOU WON! Claim your free iPhone now! Enter your bank PIN and SSN, then pay via bitcoin for shipping fees."
    assessment, findings = evaluate_text_risk(text, ai_result=MOCK_SUSPICIOUS_AI_TEXT)

    assert assessment.risk_score is not None
    assert assessment.risk_score >= 85
    assert assessment.risk_category == RiskCategory.HIGH
    assert assessment.risk_level == "HIGH"
    assert any(ind.severity == "HIGH" for ind in assessment.indicators)


# Test 3: Confirmed phishing URL (Safe Browsing MATCH_FOUND) -> Always High Risk (>=95)
def test_confirmed_phishing_url():
    assessment, _ = evaluate_url_risk(
        heuristic_flags=[],
        safe_browsing_result={
            "configured": True,
            "checked": True,
            "is_safe": False,
            "status": "MATCH_FOUND",
            "threat_types": ["MALWARE", "SOCIAL_ENGINEERING"]
        },
        ai_result=None,
        url_info={"is_url_shortener": False}
    )

    assert assessment.risk_score is not None
    assert assessment.risk_score >= 95
    assert assessment.risk_category == RiskCategory.HIGH
    assert assessment.risk_level == "HIGH"
    assert any("Threat Intelligence" in ind.category for ind in assessment.indicators)


# Test 4: Suspicious URL without Safe Browsing match -> Heuristics elevate to High Risk
def test_suspicious_url_without_safebrowsing_match():
    assessment, _ = evaluate_url_risk(
        heuristic_flags=[
            "Direct IP address utilized as destination host",
            "Prominent brand name ('paypal') appears in subdomain or path while root domain is different ('security-update.xyz')",
            "URL contains sensitive account/security bait keyword: 'verify'"
        ],
        safe_browsing_result={
            "configured": True,
            "checked": True,
            "is_safe": True,
            "status": "NO_THREAT_FOUND",
            "threat_types": []
        },
        ai_result=None,
        url_info={"is_url_shortener": False}
    )

    # Clean Safe Browsing does not cancel verified high-severity heuristic threats
    assert assessment.risk_score is not None
    assert assessment.risk_score >= 75
    assert assessment.risk_category == RiskCategory.HIGH
    assert assessment.status == AssessmentStatus.PARTIAL


# Test 5: Image with suspicious embedded text (OCR + Heuristics)
def test_image_with_suspicious_embedded_text():
    ocr_text = "CONGRATULATIONS WINNER! Claim free gift card now. Enter your bank pin to verify shipping."
    assessment, findings, detail = evaluate_image_risk(
        ocr_text=ocr_text,
        ocr_confidence=88.5,
        ocr_status="SUCCESS",
        ai_result=None
    )

    assert assessment.risk_score is not None
    assert assessment.risk_score >= 65
    assert assessment.risk_category == RiskCategory.HIGH
    assert assessment.status == AssessmentStatus.PARTIAL
    assert any(ind.source == "Tesseract OCR Heuristics" for ind in assessment.indicators)


# Test 6: Indicator deduplication prevents repeated score boosts
def test_duplicate_indicators_prevention():
    raw_indicators = [
        SuspiciousIndicator(
            category="Brand Impersonation",
            title="Brand Spoofing (PayPal)",
            description="The URL appears to impersonate paypal via deceptive subdomains",
            severity="MEDIUM",
            source="URL Structural Heuristics",
            confidence=0.85
        ),
        SuspiciousIndicator(
            category="Brand Impersonation",
            title="Brand Spoofing or Mimicry (PayPal)",
            description="The URL appears to impersonate paypal via deceptive subdomains",
            severity="HIGH",
            source="Gemini AI Phishing Analysis",
            confidence=0.94
        ),
        SuspiciousIndicator(
            category="Credential Harvesting",
            title="Direct PIN Harvesting",
            description="Requests bank pin",
            severity="HIGH",
            source="Tesseract OCR Heuristics",
            confidence=0.90
        ),
        SuspiciousIndicator(
            category="Credential Harvesting",
            title="Direct PIN Harvesting",
            description="Requests bank pin",
            severity="HIGH",
            source="Gemini Vision AI",
            confidence=0.95
        )
    ]

    deduped = deduplicate_indicators(raw_indicators)
    assert len(deduped) == 2
    # Brand impersonation escalated to HIGH severity and merged sources
    brand_ind = next(ind for ind in deduped if ind.category == "Brand Impersonation")
    assert brand_ind.severity == "HIGH"
    assert "URL Structural Heuristics" in brand_ind.source
    assert "Gemini AI Phishing Analysis" in brand_ind.source
    assert brand_ind.confidence == 0.94

    # Credential Harvesting merged sources
    cred_ind = next(ind for ind in deduped if ind.category == "Credential Harvesting")
    assert "Tesseract OCR Heuristics" in cred_ind.source
    assert "Gemini Vision AI" in cred_ind.source


# Test 7: Gemini quota exhaustion -> Partial analysis without failing request
@patch("app.routes.analyze.analyze_url_with_gemini")
@patch("app.routes.analyze.check_safe_browsing")
def test_gemini_quota_exhaustion_partial_analysis(mock_sb, mock_gemini):
    mock_sb.return_value = {
        "configured": True,
        "checked": True,
        "is_safe": True,
        "status": "NO_THREAT_FOUND",
        "threat_types": [],
        "message": "Clean"
    }
    mock_gemini.side_effect = GeminiQuotaError("Daily request quota has been exhausted")

    response = client.post("/api/analyze/url", json={"url": "https://www.nordstrom.com/sale"})
    assert response.status_code == 200
    data = response.json()
    assert data["assessment_status"] == "PARTIAL"
    assert data["gemini_used"] is False
    assert data["ai_status"] == "QUOTA_EXHAUSTED"
    assert "Google Safe Browsing v5" in data["checks_completed"]
    assert any("Gemini AI Contextual Analysis" in c for c in data["checks_unavailable"])


# Test 8: Safe Browsing unavailable -> Partial analysis
def test_safebrowsing_unavailable_partial_analysis():
    mock_ai_url = GeminiUrlAnalysisRaw(
        summary="Domain appears to be a legitimate major e-commerce provider.",
        estimated_risk_score=15,
        risk_level="LOW",
        explanation="Valid HTTPS domain structure without brand spoofing or credential bait.",
        recommendations=["Shop safely through official channels."]
    )

    assessment, _ = evaluate_url_risk(
        heuristic_flags=[],
        safe_browsing_result={
            "configured": True,
            "checked": False,
            "is_safe": None,
            "status": "UNAVAILABLE",
            "threat_types": []
        },
        ai_result=mock_ai_url,
        url_info={"is_url_shortener": False}
    )

    assert assessment.status == AssessmentStatus.PARTIAL
    assert assessment.risk_score == 15
    assert assessment.risk_category == RiskCategory.LOW
    assert any("Google Safe Browsing v5 (UNAVAILABLE)" in c for c in assessment.checks_unavailable)
    assert "Gemini AI Contextual Analysis" in assessment.checks_completed


# Test 9: Both AI and Threat DB unavailable without decisive heuristics -> INSUFFICIENT_DATA
def test_both_ai_and_threat_database_unavailable_insufficient_data():
    assessment, _ = evaluate_url_risk(
        heuristic_flags=[],
        safe_browsing_result={
            "configured": True,
            "checked": False,
            "is_safe": None,
            "status": "UNAVAILABLE",
            "threat_types": []
        },
        ai_result=None,
        url_info={"is_url_shortener": False}
    )

    # Must NOT show Low Risk when unverified
    assert assessment.status == AssessmentStatus.INSUFFICIENT_DATA
    assert assessment.risk_score is None
    assert assessment.risk_category == RiskCategory.INSUFFICIENT_DATA
    assert assessment.risk_level == "INSUFFICIENT_DATA"
    assert assessment.summary == "Unable to verify – insufficient security data."
    assert "insufficient security data" in assessment.explanation.lower()


# Test 10: Both unavailable BUT decisive heuristics present -> PARTIAL (Elevated Risk)
def test_both_ai_and_threat_database_unavailable_decisive_heuristics():
    assessment, _ = evaluate_url_risk(
        heuristic_flags=["Direct IP address utilized as destination host"],
        safe_browsing_result={
            "configured": True,
            "checked": False,
            "is_safe": None,
            "status": "UNAVAILABLE",
            "threat_types": []
        },
        ai_result=None,
        url_info={"is_url_shortener": False}
    )

    assert assessment.status == AssessmentStatus.PARTIAL
    assert assessment.risk_score is not None
    assert assessment.risk_score >= 65
    assert assessment.risk_category == RiskCategory.HIGH


# Test 11: Risk score boundary consistency
def test_risk_score_boundaries():
    assert score_to_category(0) == RiskCategory.LOW
    assert score_to_category(30) == RiskCategory.LOW
    assert score_to_category(31) == RiskCategory.MEDIUM
    assert score_to_category(60) == RiskCategory.MEDIUM
    assert score_to_category(61) == RiskCategory.HIGH
    assert score_to_category(100) == RiskCategory.HIGH
    assert score_to_category(None) == RiskCategory.INSUFFICIENT_DATA


# Test 12: Conflicting signals: Clean AI score CANNOT cancel verified threat
def test_conflicting_signals_monotonic_threat_floor():
    # Scenario: Hallucinated or compromised AI says score is 15, but Safe Browsing verified MALWARE
    final_score, category, _ = calculate_unified_risk_score(
        indicators=[
            SuspiciousIndicator(
                category="Threat Intelligence",
                title="Verified Threat: MALWARE",
                description="Malware match in Safe Browsing",
                severity="HIGH",
                source="Google Safe Browsing v5",
                confidence=0.98
            )
        ],
        ai_estimated_score=15,
        is_authoritative_threat=True
    )

    assert final_score >= 95
    assert category == RiskCategory.HIGH


# Test 13: Insufficient evidence in text analysis without AI or heuristics
def test_insufficient_evidence_text_without_heuristics():
    assessment, findings = evaluate_text_risk(
        text="A simple benign announcement without promotional trigger words.",
        ai_result=None
    )

    assert assessment.status == AssessmentStatus.INSUFFICIENT_DATA
    assert assessment.risk_score is None
    assert assessment.risk_category == RiskCategory.INSUFFICIENT_DATA
    assert assessment.summary == "Unable to verify – insufficient security data."

