"""
Phase 6 Functional Test Suite for AdShield.
Verifies all functional test scenarios specified in Phase A:
- TEXT: Genuine, Fake Prize, Unrealistic Discount, Urgent Payment, Phishing, Brand Impersonation.
- IMAGE: Genuine, Fake Discount, Prize Banner, Suspicious Payment, No Text, Corrupted, Unsupported.
- URL: Normal HTTPS, Insecure HTTP, Safe Browsing Phishing Test URL, Suspicious Keywords,
       Lookalike Domain, URL Shortener, Invalid URL, Private IP / SSRF.
All external AI and Safe Browsing calls are deterministically mocked to consume 0 live quota.
"""

import io
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.gemini_model_manager import FallbackMetadata
from app.models.schemas import (
    GeminiTextAnalysisRaw,
    GeminiImageAnalysisRaw,
    GeminiUrlAnalysisRaw,
    RiskCategory,
    AssessmentStatus
)

client = TestClient(app)


def _create_test_image(color=(50, 100, 150), width=120, height=120) -> bytes:
    """Creates a valid in-memory PNG image."""
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=color)
    img.save(buf, format="PNG")
    return buf.getvalue()


# ==============================================================================
# 1. TEXT ANALYSIS FUNCTIONAL TESTS
# ==============================================================================

@patch("app.routes.analyze.analyze_text_with_gemini")
def test_text_genuine_advertisement(mock_gemini):
    mock_raw = GeminiTextAnalysisRaw(
        summary="Legitimate promotional advertisement from established retailer.",
        estimated_risk_score=10,
        risk_level="LOW",
        explanation="Standard commercial promotion with realistic discounts and transparent terms.",
        detected_claims=["20% seasonal clearance discount"],
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
        recommended_actions=["Shop via official verified store or website."]
    )
    mock_gemini.return_value = (mock_raw, FallbackMetadata(model_used="gemini-3.5-flash-lite"))

    response = client.post("/api/analyze/text", json={
        "text": "Summer clearance sale: 20% off all clothing this weekend at Nordstrom stores and online."
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] <= 30
    assert data["risk_category"] == "Low"
    assert data["risk_level"] == "LOW"
    assert data["gemini_used"] is True
    assert data["model_used"] == "gemini-3.5-flash-lite"


@patch("app.routes.analyze.analyze_text_with_gemini")
def test_text_fake_prize_winning_ad(mock_gemini):
    mock_raw = GeminiTextAnalysisRaw(
        summary="High-risk lottery / fake prize scam.",
        estimated_risk_score=95,
        risk_level="CRITICAL",
        explanation="Classic advance-fee fake prize lure designed to harvest credentials or fee payments.",
        detected_claims=["Claim $10,000 Walmart Gift Card"],
        unrealistic_discounts=[],
        fake_prize_indicators=["Selected as $10,000 winner without entering lottery"],
        urgent_payment_requests=["Must claim within 15 minutes before forfeiture"],
        misleading_statements=["Guaranteed free reward"],
        suspicious_product_offers=[],
        brand_impersonation=["Walmart"],
        fake_investment_promises=[],
        phishing_language=["Click here immediately to verify account"],
        sensitive_info_requests=["Full legal name, banking routing number"],
        manipulative_techniques=["Artificial urgency", "False scarcity"],
        recommended_actions=["Do not click link. Delete message immediately."]
    )
    mock_gemini.return_value = (mock_raw, FallbackMetadata(model_used="gemini-3.5-flash-lite"))

    response = client.post("/api/analyze/text", json={
        "text": "CONGRATULATIONS! You have been selected as the WINNER of a $10,000 Walmart Gift Card! Click here immediately to claim your prize before it expires!"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 80
    assert data["risk_category"] == "High"
    assert data["risk_level"] == "HIGH"
    assert any("prize" in ind["title"].lower() or "walmart" in ind["description"].lower() for ind in data["indicators"])


@patch("app.routes.analyze.analyze_text_with_gemini")
def test_text_unrealistic_discount_ad(mock_gemini):
    mock_raw = GeminiTextAnalysisRaw(
        summary="Unrealistic 99% discount indicative of counterfeit goods or non-delivery fraud.",
        estimated_risk_score=88,
        risk_level="HIGH",
        explanation="Flagship smartphone offered at a price point below bill-of-materials cost.",
        detected_claims=["iPhone 15 Pro Max for $19"],
        unrealistic_discounts=["99% off luxury flagship"],
        fake_prize_indicators=[],
        urgent_payment_requests=[],
        misleading_statements=["Today only flash clearance"],
        suspicious_product_offers=["Subsidized premium electronics"],
        brand_impersonation=["Apple"],
        fake_investment_promises=[],
        phishing_language=[],
        sensitive_info_requests=[],
        manipulative_techniques=["Extreme discount lure"],
        recommended_actions=["Purchase devices exclusively from authorized Apple resellers."]
    )
    mock_gemini.return_value = (mock_raw, FallbackMetadata(model_used="gemini-3.5-flash-lite"))

    response = client.post("/api/analyze/text", json={
        "text": "Brand new Apple iPhone 15 Pro Max for only $19! 99% discount flash clearance sale today only!"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 75
    assert data["risk_category"] == "High"
    assert data["risk_level"] == "HIGH"


@patch("app.routes.analyze.analyze_text_with_gemini")
def test_text_urgent_payment_message(mock_gemini):
    mock_raw = GeminiTextAnalysisRaw(
        summary="Extortion / urgent cryptocurrency payment demand.",
        estimated_risk_score=98,
        risk_level="CRITICAL",
        explanation="High-pressure tactic demanding untraceable payment methods to prevent service suspension.",
        detected_claims=["Netflix subscription suspended"],
        unrealistic_discounts=[],
        fake_prize_indicators=[],
        urgent_payment_requests=["Send Bitcoin or gift cards within 1 hour"],
        misleading_statements=["Account will be permanently deleted"],
        suspicious_product_offers=[],
        brand_impersonation=["Netflix"],
        fake_investment_promises=[],
        phishing_language=["Pay immediately to recover account"],
        sensitive_info_requests=["Prepaid gift card PIN codes"],
        manipulative_techniques=["Intimidation", "Time pressure"],
        recommended_actions=["Do not send funds. Contact Netflix support through official app."]
    )
    mock_gemini.return_value = (mock_raw, FallbackMetadata(model_used="gemini-3.5-flash-lite"))

    response = client.post("/api/analyze/text", json={
        "text": "URGENT NOTICE: Your Netflix subscription has been suspended! Send cryptocurrency payment or prepaid gift cards within 1 hour to prevent account termination!"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 90
    assert data["risk_category"] == "High"
    assert data["risk_level"] == "HIGH"


@patch("app.routes.analyze.analyze_text_with_gemini")
def test_text_phishing_message(mock_gemini):
    mock_raw = GeminiTextAnalysisRaw(
        summary="Credential harvesting phishing attack targeting Chase banking users.",
        estimated_risk_score=99,
        risk_level="CRITICAL",
        explanation="Fraudulent bank communication designed to capture authentication credentials and PINs.",
        detected_claims=["Account security hold"],
        unrealistic_discounts=[],
        fake_prize_indicators=[],
        urgent_payment_requests=[],
        misleading_statements=["Session locked by security"],
        suspicious_product_offers=[],
        brand_impersonation=["Chase Bank"],
        fake_investment_promises=[],
        phishing_language=["Verify account credentials immediately"],
        sensitive_info_requests=["Username", "Password", "SSN", "Debit card PIN"],
        manipulative_techniques=["Authority impersonation", "Security alarmism"],
        recommended_actions=["Never enter credentials on unverified third-party websites."]
    )
    mock_gemini.return_value = (mock_raw, FallbackMetadata(model_used="gemini-3.5-flash-lite"))

    response = client.post("/api/analyze/text", json={
        "text": "Dear Chase Customer, your online banking session has been locked. Verify your username, password, SSN, and debit card PIN immediately at http://chase-security-verify.net"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 90
    assert data["risk_category"] == "High"
    assert data["risk_level"] == "HIGH"


@patch("app.routes.analyze.analyze_text_with_gemini")
def test_text_brand_impersonation_example(mock_gemini):
    mock_raw = GeminiTextAnalysisRaw(
        summary="Customer support impersonation scam spoofing Amazon.",
        estimated_risk_score=94,
        risk_level="CRITICAL",
        explanation="Fraudulent representative attempting to collect credit card details under false support pretenses.",
        detected_claims=["Unauthorized login detected"],
        unrealistic_discounts=[],
        fake_prize_indicators=[],
        urgent_payment_requests=[],
        misleading_statements=["Account locked due to fraud"],
        suspicious_product_offers=[],
        brand_impersonation=["Amazon"],
        fake_investment_promises=[],
        phishing_language=["Call 1-800-FAKE-NUM or enter card details"],
        sensitive_info_requests=["Credit card number"],
        manipulative_techniques=["Brand spoofing", "Pretexting"],
        recommended_actions=["Contact Amazon exclusively via amazon.com/help."]
    )
    mock_gemini.return_value = (mock_raw, FallbackMetadata(model_used="gemini-3.5-flash-lite"))

    response = client.post("/api/analyze/text", json={
        "text": "Official Amazon Customer Care: We detected unauthorized login. Call 1-800-FAKE-NUM or enter your credit card on amazon-security-help.com."
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 80
    assert data["risk_category"] == "High"
    assert data["risk_level"] == "HIGH"


# ==============================================================================
# 2. IMAGE ANALYSIS FUNCTIONAL TESTS
# ==============================================================================

@patch("app.routes.analyze.analyze_image_with_gemini")
@patch("app.routes.analyze.extract_text_from_image")
def test_image_genuine_product_ad(mock_ocr, mock_vision):
    mock_ocr.return_value = {
        "success": True,
        "status": "SUCCESS",
        "text": "Nike Air Zoom Running Shoes $120 Free Shipping",
        "confidence": 92.5
    }
    mock_vision.return_value = (
        GeminiImageAnalysisRaw(
            summary="Clean athletic footwear advertisement.",
            estimated_risk_score=15,
            risk_level="LOW",
            visual_observations=["Athletic shoes on clean background", "Official Nike typography"],
            detected_claims=["Nike Air Zoom Shoes $120", "Free shipping"],
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
            explanation="Normal retail promotion.",
            recommendations=["Verify purchases via official Nike store."]
        ),
        FallbackMetadata(model_used="gemini-3.5-flash-lite")
    )

    png_bytes = _create_test_image()
    response = client.post("/api/analyze/image", files={"file": ("nike.png", png_bytes, "image/png")})
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] <= 30
    assert data["risk_category"] == "Low"
    assert data["risk_level"] == "LOW"
    assert data["ocr_status"] == "SUCCESS"
    assert data["ocr_used"] is True
    assert data["gemini_vision_used"] is True


@patch("app.routes.analyze.analyze_image_with_gemini")
@patch("app.routes.analyze.extract_text_from_image")
def test_image_fake_discount_banner(mock_ocr, mock_vision):
    mock_ocr.return_value = {
        "success": True,
        "status": "SUCCESS",
        "text": "ROLEX SUBMARINER 99% OFF TODAY $10 ONLY",
        "confidence": 88.0
    }
    mock_vision.return_value = (
        GeminiImageAnalysisRaw(
            summary="Counterfeit luxury watch advertisement banner.",
            estimated_risk_score=92,
            risk_level="HIGH",
            visual_observations=["Low-resolution Rolex crown logo", "Aggressive red discount flash"],
            detected_claims=["Rolex Submariner for $10"],
            unrealistic_discounts=["99% off luxury timepiece"],
            fake_prize_indicators=[],
            urgent_payment_requests=[],
            suspicious_payment_instructions=[],
            brand_impersonation=["Rolex"],
            misleading_representations=["Authentic luxury watch for $10"],
            suspicious_contact_details=[],
            visual_inconsistencies=["Blurred watermark", "Misaligned logo font"],
            sensitive_info_requests=[],
            phishing_indicators=[],
            explanation="Blatant counterfeit lure.",
            recommendations=["Do not provide payment information."]
        ),
        FallbackMetadata(model_used="gemini-3.5-flash-lite")
    )

    png_bytes = _create_test_image()
    response = client.post("/api/analyze/image", files={"file": ("rolex_fake.png", png_bytes, "image/png")})
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 80
    assert data["risk_category"] == "High"
    assert data["risk_level"] == "HIGH"


@patch("app.routes.analyze.analyze_image_with_gemini")
@patch("app.routes.analyze.extract_text_from_image")
def test_image_prize_winning_banner(mock_ocr, mock_vision):
    mock_ocr.return_value = {
        "success": True,
        "status": "SUCCESS",
        "text": "SPIN TO WIN! $1,000,000 CASH PRIZE JACKPOT WINNER",
        "confidence": 85.0
    }
    mock_vision.return_value = (
        GeminiImageAnalysisRaw(
            summary="Fraudulent sweepstakes / gambling lure banner.",
            estimated_risk_score=95,
            risk_level="HIGH",
            visual_observations=["Flashing neon prize wheel", "Exaggerated dollar graphics"],
            detected_claims=["Winner of $1,000,000 cash jackpot"],
            unrealistic_discounts=[],
            fake_prize_indicators=["Unsolicited million dollar lottery winner"],
            urgent_payment_requests=[],
            suspicious_payment_instructions=[],
            brand_impersonation=[],
            misleading_representations=["Guaranteed instant cash payout"],
            suspicious_contact_details=[],
            visual_inconsistencies=["No licensing or regulatory disclosures"],
            sensitive_info_requests=["SSN to claim prize"],
            phishing_indicators=["Redirect to external credential harvester"],
            explanation="High-risk advance fee fraud banner.",
            recommendations=["Never submit personal or financial data to claim unsolicited prizes."]
        ),
        FallbackMetadata(model_used="gemini-3.5-flash-lite")
    )

    png_bytes = _create_test_image()
    response = client.post("/api/analyze/image", files={"file": ("prize_wheel.png", png_bytes, "image/png")})
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 85
    assert data["risk_category"] == "High"
    assert data["risk_level"] == "HIGH"


@patch("app.routes.analyze.analyze_image_with_gemini")
@patch("app.routes.analyze.extract_text_from_image")
def test_image_suspicious_payment_banner(mock_ocr, mock_vision):
    mock_ocr.return_value = {
        "success": True,
        "status": "SUCCESS",
        "text": "PAY VIA WESTERN UNION TO UNLOCK PHONE",
        "confidence": 90.0
    }
    mock_vision.return_value = (
        GeminiImageAnalysisRaw(
            summary="Ransom / unverified wire transfer demand image.",
            estimated_risk_score=96,
            risk_level="HIGH",
            visual_observations=["Padlock graphic", "Western Union logo snippet"],
            detected_claims=["Wire transfer required to release device"],
            unrealistic_discounts=[],
            fake_prize_indicators=[],
            urgent_payment_requests=["Pay within 24 hours"],
            suspicious_payment_instructions=["Wire transfer via Western Union MTCN"],
            brand_impersonation=["Western Union"],
            misleading_representations=["Device locked remotely"],
            suspicious_contact_details=[],
            visual_inconsistencies=[],
            sensitive_info_requests=["Money transfer MTCN number"],
            phishing_indicators=[],
            explanation="Irreversible payment demand scam.",
            recommendations=["Never send wire transfers to unlock devices. Seek certified device repair."]
        ),
        FallbackMetadata(model_used="gemini-3.5-flash-lite")
    )

    png_bytes = _create_test_image()
    response = client.post("/api/analyze/image", files={"file": ("wire_scam.png", png_bytes, "image/png")})
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 85
    assert data["risk_category"] == "High"
    assert data["risk_level"] == "HIGH"


@patch("app.routes.analyze.analyze_image_with_gemini")
@patch("app.routes.analyze.extract_text_from_image")
def test_image_with_no_embedded_text(mock_ocr, mock_vision):
    mock_ocr.return_value = {
        "success": True,
        "status": "NO_TEXT_DETECTED",
        "text": None,
        "confidence": None
    }
    mock_vision.return_value = (
        GeminiImageAnalysisRaw(
            summary="Scenic mountain landscape with no advertising cues.",
            estimated_risk_score=5,
            risk_level="LOW",
            visual_observations=["Nature photograph", "Trees and mountains"],
            detected_claims=[],
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
            explanation="No commercial or suspicious elements present.",
            recommendations=[]
        ),
        FallbackMetadata(model_used="gemini-3.5-flash-lite")
    )

    png_bytes = _create_test_image()
    response = client.post("/api/analyze/image", files={"file": ("nature.png", png_bytes, "image/png")})
    assert response.status_code == 200
    data = response.json()
    assert data["ocr_status"] == "NO_TEXT_DETECTED"
    assert data["extracted_text"] is None
    assert data["ocr_used"] is False
    assert data["gemini_vision_used"] is True
    assert data["risk_score"] <= 20
    assert data["risk_category"] == "Low"


def test_image_corrupted_bytes_rejected():
    corrupted_data = b"NOT_A_VALID_IMAGE_HEADER_12345"
    response = client.post("/api/analyze/image", files={"file": ("bad.png", corrupted_data, "image/png")})
    assert response.status_code == 400
    assert "cannot be decoded" in response.json()["detail"].lower() or "corrupted" in response.json()["detail"].lower()


def test_image_unsupported_format_rejected():
    text_data = b"Plain text file that is not an image."
    response = client.post("/api/analyze/image", files={"file": ("doc.txt", text_data, "text/plain")})
    assert response.status_code == 400
    assert "unsupported file format" in response.json()["detail"].lower() or "allowed types" in response.json()["detail"].lower()


# ==============================================================================
# 3. URL SECURITY FUNCTIONAL TESTS
# ==============================================================================

@patch("app.routes.analyze.check_safe_browsing")
@patch("app.routes.analyze.analyze_url_with_gemini")
def test_url_normal_https(mock_gemini, mock_sb):
    mock_sb.return_value = {
        "configured": True,
        "checked": True,
        "is_safe": True,
        "status": "NO_THREAT_FOUND",
        "threat_types": []
    }
    mock_gemini.return_value = (
        GeminiUrlAnalysisRaw(
            summary="Official Apple product page.",
            estimated_risk_score=5,
            risk_level="LOW",
            detected_brand="Apple",
            is_brand_impersonation=False,
            is_lookalike_domain=False,
            is_phishing_login=False,
            is_suspicious_shortener=False,
            suspicious_patterns=[],
            ad_url_consistency="Consistent with Apple brand",
            explanation="Authentic destination domain with high authority.",
            recommendations=["Domain is verified."]
        ),
        FallbackMetadata(model_used="gemini-3.5-flash-lite")
    )

    response = client.post("/api/analyze/url", json={"url": "https://www.apple.com/iphone"})
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] <= 25
    assert data["risk_category"] == "Low"
    assert data["risk_level"] == "LOW"
    assert data["findings"]["scheme"] == "https"


@patch("app.routes.analyze.check_safe_browsing")
@patch("app.routes.analyze.analyze_url_with_gemini")
def test_url_insecure_http_transport(mock_gemini, mock_sb):
    mock_sb.return_value = {
        "configured": True,
        "checked": True,
        "is_safe": True,
        "status": "NO_THREAT_FOUND",
        "threat_types": []
    }
    mock_gemini.return_value = (
        GeminiUrlAnalysisRaw(
            summary="Unencrypted HTTP connection detected.",
            estimated_risk_score=35,
            risk_level="MEDIUM",
            detected_brand=None,
            is_brand_impersonation=False,
            is_lookalike_domain=False,
            is_phishing_login=False,
            is_suspicious_shortener=False,
            suspicious_patterns=["Insecure HTTP transport"],
            ad_url_consistency="Unknown",
            explanation="Lacks TLS/SSL encryption.",
            recommendations=["Do not enter passwords or payment details over unencrypted HTTP."]
        ),
        FallbackMetadata(model_used="gemini-3.5-flash-lite")
    )

    response = client.post("/api/analyze/url", json={"url": "http://example-discount-shop.com/deal"})
    assert response.status_code == 200
    data = response.json()
    assert data["findings"]["scheme"] == "http"
    assert any("http" in ind["title"].lower() or "insecure" in ind["title"].lower() for ind in data["indicators"])


@patch("app.routes.analyze.check_safe_browsing")
def test_url_google_official_safebrowsing_phishing_test_url(mock_sb):
    """Verifies that Google's documented Safe Browsing phishing test URL is flagged as MALICIOUS/HIGH."""
    mock_sb.return_value = {
        "configured": True,
        "checked": True,
        "is_safe": False,
        "status": "MATCH_FOUND",
        "threat_types": ["SOCIAL_ENGINEERING"]
    }

    response = client.post("/api/analyze/url", json={"url": "http://testsafebrowsing.appspot.com/s/phishing.html"})
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 85
    assert data["risk_category"] == "High"
    assert data["risk_level"] == "HIGH"
    assert "Google Safe Browsing v5" in data["checks_completed"]


@patch("app.routes.analyze.check_safe_browsing")
@patch("app.routes.analyze.analyze_url_with_gemini")
def test_url_suspicious_keywords_and_tld(mock_gemini, mock_sb):
    mock_sb.return_value = {"configured": True, "checked": True, "is_safe": True, "status": "NO_THREAT_FOUND", "threat_types": []}
    mock_gemini.return_value = (
        GeminiUrlAnalysisRaw(
            summary="Suspicious free gift lure on cheap registry TLD.",
            estimated_risk_score=85,
            risk_level="HIGH",
            detected_brand="Apple iPhone",
            is_brand_impersonation=True,
            is_lookalike_domain=False,
            is_phishing_login=False,
            is_suspicious_shortener=False,
            suspicious_patterns=["Excessive hyphens", "Giveaway keyword lure", "Uncommon TLD (.xyz)"],
            ad_url_consistency="Fraudulent lure",
            explanation="Combines giveaway lures with brand keyword.",
            recommendations=["Do not visit domain."]
        ),
        FallbackMetadata(model_used="gemini-3.5-flash-lite")
    )

    response = client.post("/api/analyze/url", json={"url": "http://free-iphone-giveaway-winner2026.xyz/claim"})
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 70
    assert data["risk_category"] == "High"
    assert data["risk_level"] == "HIGH"


@patch("app.routes.analyze.check_safe_browsing")
@patch("app.routes.analyze.analyze_url_with_gemini")
def test_url_lookalike_typosquatting_domain(mock_gemini, mock_sb):
    mock_sb.return_value = {"configured": True, "checked": True, "is_safe": True, "status": "NO_THREAT_FOUND", "threat_types": []}
    mock_gemini.return_value = (
        GeminiUrlAnalysisRaw(
            summary="Typosquatting domain targeting PayPal.",
            estimated_risk_score=92,
            risk_level="HIGH",
            detected_brand="PayPal",
            is_brand_impersonation=True,
            is_lookalike_domain=True,
            is_phishing_login=True,
            is_suspicious_shortener=False,
            suspicious_patterns=["Number substitution '1' for letter 'l'", "Fake security subdomain"],
            ad_url_consistency="High risk spoofing",
            explanation="Typosquatting variation of paypal.com.",
            recommendations=["Do not enter credentials. Verify true domain paypal.com."]
        ),
        FallbackMetadata(model_used="gemini-3.5-flash-lite")
    )

    response = client.post("/api/analyze/url", json={"url": "http://www.paypa1-security.com/login"})
    assert response.status_code == 200
    data = response.json()
    assert data["risk_score"] >= 80
    assert data["risk_category"] == "High"
    assert data["risk_level"] == "HIGH"


@patch("app.routes.analyze.check_safe_browsing")
@patch("app.routes.analyze.analyze_url_with_gemini")
def test_url_shortener_flagged(mock_gemini, mock_sb):
    mock_sb.return_value = {"configured": True, "checked": True, "is_safe": True, "status": "NO_THREAT_FOUND", "threat_types": []}
    mock_gemini.return_value = (
        GeminiUrlAnalysisRaw(
            summary="Shortened URL obscuring final landing domain.",
            estimated_risk_score=60,
            risk_level="MEDIUM",
            detected_brand=None,
            is_brand_impersonation=False,
            is_lookalike_domain=False,
            is_phishing_login=False,
            is_suspicious_shortener=True,
            suspicious_patterns=["Known URL shortener service bit.ly"],
            ad_url_consistency="Unknown destination",
            explanation="Hides actual target web destination.",
            recommendations=["Expand URL using a link unshortener before clicking."]
        ),
        FallbackMetadata(model_used="gemini-3.5-flash-lite")
    )

    response = client.post("/api/analyze/url", json={"url": "https://bit.ly/3xYFakeDeal"})
    assert response.status_code == 200
    data = response.json()
    assert data["findings"]["is_url_shortener"] is True
    assert any("shortener" in ind["title"].lower() for ind in data["indicators"])


def test_url_invalid_format_rejected():
    response = client.post("/api/analyze/url", json={"url": "not-a-valid-url-format"})
    assert response.status_code in (400, 422)


def test_url_private_ip_ssrf_blocked():
    """Confirms SSRF protection blocks loopback and private subnets."""
    response = client.post("/api/analyze/url", json={"url": "http://127.0.0.1:8000/internal"})
    assert response.status_code == 400
    assert "private" in response.json()["detail"].lower() or "loopback" in response.json()["detail"].lower() or "ssrf" in response.json()["detail"].lower()

    response_cloud = client.post("/api/analyze/url", json={"url": "http://169.254.169.254/latest/meta-data"})
    assert response_cloud.status_code == 400
