import os
import sys
import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.models.schemas import GeminiUrlAnalysisRaw, RiskCategory
from app.services.safebrowsing_service import (
    validate_and_normalize_url,
    analyze_url_heuristics,
    check_safe_browsing,
    clear_safe_browsing_cache,
    parse_cache_duration,
    _SAFE_BROWSING_CACHE
)
from app.services.risk_engine import score_to_category, evaluate_url_risk
from app.services.gemini_service import (
    GeminiConfigurationError,
    GeminiAuthError,
    GeminiQuotaError,
    GeminiUnavailableError,
    GeminiTimeoutError,
    GeminiResponseError
)

client = TestClient(app)

# Sample Mock AI URL Responses
MOCK_SAFE_URL_AI = GeminiUrlAnalysisRaw(
    summary="Legitimate e-commerce retail destination with standard security credentials.",
    estimated_risk_score=15,
    risk_level="LOW",
    detected_brand=None,
    is_brand_impersonation=False,
    is_lookalike_domain=False,
    is_phishing_login=False,
    is_suspicious_shortener=False,
    suspicious_patterns=[],
    ad_url_consistency="Consistent with promotional clearance sale",
    explanation="The domain is the verified official web property of the advertised retailer.",
    recommendations=["Verify secure lock icon in browser address bar"]
)

MOCK_PHISHING_URL_AI = GeminiUrlAnalysisRaw(
    summary="Deceptive brand-spoofing landing page designed to harvest payment credentials.",
    estimated_risk_score=92,
    risk_level="HIGH",
    detected_brand="PayPal",
    is_brand_impersonation=True,
    is_lookalike_domain=True,
    is_phishing_login=True,
    is_suspicious_shortener=False,
    suspicious_patterns=["Brand name in subdomain", "Suspicious low-reputation TLD .xyz", "Security bait path"],
    ad_url_consistency="Suspicious urgency pattern mismatched from official domain",
    explanation="The URL uses a lookalike structure to simulate PayPal account recovery while hosting on an untrusted domain.",
    recommendations=["Do not enter passwords or payment credentials", "Navigate to official paypal.com directly"]
)


@pytest.fixture(autouse=True)
def reset_cache():
    """Automatically clear in-memory Safe Browsing cache before each test."""
    clear_safe_browsing_cache()


# Test 1: Valid HTTPS URLs
@patch("app.routes.analyze.analyze_url_with_gemini")
@patch("app.routes.analyze.check_safe_browsing")
def test_valid_https_url(mock_sb, mock_gemini):
    mock_gemini.return_value = (MOCK_SAFE_URL_AI, "gemini-3.5-flash")
    mock_sb.return_value = {
        "configured": True,
        "checked": True,
        "is_safe": True,
        "status": "NO_THREAT_FOUND",
        "threat_types": [],
        "message": "No known threat match found in Google Safe Browsing database.",
        "cache_hit": False
    }

    response = client.post("/api/analyze/url", json={
        "url": "https://www.nordstrom.com/browse/sale",
        "ad_text": "Nordstrom summer clearance sale 20% off",
        "source_context": "Social Media"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["url_validation_status"] == "VALID"
    assert data["validated_domain"] == "www.nordstrom.com"
    assert data["findings"]["scheme"] == "https"
    assert data["risk_score"] <= 30
    assert data["risk_category"] == "Low"
    assert data["risk_level"] == "LOW"
    assert data["gemini_used"] is True


# Test 2: Valid HTTP URLs
@patch("app.routes.analyze.analyze_url_with_gemini")
@patch("app.routes.analyze.check_safe_browsing")
def test_valid_http_url(mock_sb, mock_gemini):
    mock_gemini.return_value = (MOCK_SAFE_URL_AI, "gemini-3.5-flash")
    mock_sb.return_value = {
        "configured": True,
        "checked": True,
        "is_safe": True,
        "status": "NO_THREAT_FOUND",
        "threat_types": [],
        "message": "No known threats found.",
        "cache_hit": False
    }

    response = client.post("/api/analyze/url", json={
        "url": "http://example-clearance-outlet.com/deals"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["findings"]["scheme"] == "http"
    # HTTP should be flagged as unencrypted connection
    unencrypted_flags = [f for f in data["findings"]["heuristic_flags"] if "unencrypted" in f.lower() or "http" in f.lower()]
    assert len(unencrypted_flags) > 0


# Test 3: Invalid URLs
@pytest.mark.parametrize("invalid_url", [
    "",
    "   ",
    "http://",
    "https://",
    "ftp://invalidscheme.com",
    "://missing-scheme-and-corrupt",
])
def test_invalid_urls(invalid_url):
    response = client.post("/api/analyze/url", json={"url": invalid_url})
    assert response.status_code in (400, 422)
    assert "detail" in response.json()


# Test 4: IP-address-based URLs
def test_ip_address_based_urls():
    # Public non-reserved IP address should be accepted but flagged
    res = validate_and_normalize_url("http://93.184.216.34/login.php")
    assert res["valid"] is True
    assert res["is_ip_address"] is True
    assert res["domain"] == "93.184.216.34"

    flags = analyze_url_heuristics(res)
    assert any("Direct IP address" in f for f in flags)


# Test 5: Punycode domains
def test_punycode_domains():
    # xn--pple-43d.com resolves to аpple.com (Cyrillic 'а')
    res = validate_and_normalize_url("https://xn--pple-43d.com/store")
    assert res["valid"] is True
    assert res["is_punycode"] is True
    assert res["decoded_punycode"] is not None
    assert "pple" in res["decoded_punycode"]
    assert res["decoded_punycode"] != "apple.com"  # Homograph difference verified

    flags = analyze_url_heuristics(res)
    assert any("Punycode" in f for f in flags)


# Test 6: Suspicious subdomains
def test_suspicious_subdomains():
    res = validate_and_normalize_url("https://paypal.com.account-verify.security-alert.xyz/update")
    assert res["valid"] is True
    assert res["subdomain_count"] >= 3
    assert res["has_suspicious_tld"] is True

    flags = analyze_url_heuristics(res)
    assert any("Excessive subdomain depth" in f for f in flags)
    assert any("Prominent brand name ('paypal')" in f for f in flags)
    assert any("top-level domain (.xyz)" in f for f in flags)


# Test 7: URL shorteners
def test_url_shorteners():
    shorteners = [
        "https://bit.ly/3xYzaBc",
        "https://tinyurl.com/deal50",
        "https://t.co/abc12345"
    ]
    for short_url in shorteners:
        res = validate_and_normalize_url(short_url)
        assert res["valid"] is True
        assert res["is_url_shortener"] is True

        flags = analyze_url_heuristics(res)
        assert any("link shortening service" in f for f in flags)


# Test 8: Safe Browsing threat match
@patch("app.routes.analyze.analyze_url_with_gemini")
@patch("app.routes.analyze.check_safe_browsing")
def test_safe_browsing_threat_match(mock_sb, mock_gemini):
    mock_gemini.return_value = (MOCK_PHISHING_URL_AI, "gemini-3.5-flash")
    mock_sb.return_value = {
        "configured": True,
        "checked": True,
        "is_safe": False,
        "status": "MATCH_FOUND",
        "threat_types": ["SOCIAL_ENGINEERING", "MALWARE"],
        "message": "Google Safe Browsing v5 flagged known threats: SOCIAL_ENGINEERING, MALWARE.",
        "cache_hit": False
    }

    response = client.post("/api/analyze/url", json={
        "url": "https://malicious-phishing-site.xyz/login"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["safe_browsing_status"] == "MATCH_FOUND"
    assert data["threat_types"] == ["SOCIAL_ENGINEERING", "MALWARE"]
    assert data["risk_score"] >= 90
    assert data["risk_category"] == "High"
    assert data["risk_level"] == "HIGH"
    # Threat intelligence indicator must be present
    ti_indicators = [ind for ind in data["indicators"] if ind["category"] == "Threat Intelligence"]
    assert len(ti_indicators) > 0


# Test 9: Safe Browsing no-match response
@patch("app.routes.analyze.analyze_url_with_gemini")
@patch("app.routes.analyze.check_safe_browsing")
def test_safe_browsing_no_match_response(mock_sb, mock_gemini):
    mock_gemini.return_value = (MOCK_SAFE_URL_AI, "gemini-3.5-flash")
    mock_sb.return_value = {
        "configured": True,
        "checked": True,
        "is_safe": True,
        "status": "NO_THREAT_FOUND",
        "threat_types": [],
        "message": "No known threat match found in Google Safe Browsing database.",
        "cache_hit": False
    }

    response = client.post("/api/analyze/url", json={
        "url": "https://www.apple.com/shop"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["safe_browsing_status"] == "NO_THREAT_FOUND"
    assert data["threat_types"] == []
    assert "No known threat match found" in data["findings"]["safe_browsing_verdict"]


# Test 10: Safe Browsing API unavailable
@patch("app.routes.analyze.analyze_url_with_gemini")
@patch("app.routes.analyze.check_safe_browsing")
def test_safe_browsing_api_unavailable(mock_sb, mock_gemini):
    mock_gemini.return_value = (MOCK_SAFE_URL_AI, "gemini-3.5-flash")
    mock_sb.return_value = {
        "configured": True,
        "checked": False,
        "is_safe": None,
        "status": "UNAVAILABLE",
        "threat_types": [],
        "message": "Security database check unavailable (HTTP 503).",
        "cache_hit": False
    }

    response = client.post("/api/analyze/url", json={
        "url": "https://www.example.com"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["safe_browsing_status"] == "UNAVAILABLE"
    assert "unavailable" in data["findings"]["safe_browsing_verdict"].lower()


# Test 11: Safe Browsing quota exhaustion (429)
@patch("app.routes.analyze.analyze_url_with_gemini")
@patch("app.routes.analyze.check_safe_browsing")
def test_safe_browsing_quota_exhaustion(mock_sb, mock_gemini):
    mock_gemini.return_value = (MOCK_SAFE_URL_AI, "gemini-3.5-flash")
    mock_sb.return_value = {
        "configured": True,
        "checked": False,
        "is_safe": None,
        "status": "UNAVAILABLE",
        "threat_types": [],
        "message": "Google Safe Browsing API rate limit or quota exceeded.",
        "cache_hit": False
    }

    response = client.post("/api/analyze/url", json={
        "url": "https://www.example.com"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["safe_browsing_status"] == "UNAVAILABLE"
    assert "quota exceeded" in data["findings"]["safe_browsing_verdict"].lower()


# Test 12: Cache expiration
def test_cache_duration_and_expiration():
    assert parse_cache_duration("300s") == 300.0
    assert parse_cache_duration("3.5s") == 5.0  # Respects min floor of 5s
    assert parse_cache_duration(None) == 300.0

    url = "https://cached-test-domain.com"
    _SAFE_BROWSING_CACHE[url] = {
        "result": {
            "configured": True,
            "checked": True,
            "is_safe": True,
            "status": "NO_THREAT_FOUND",
            "threat_types": [],
            "message": "Cached entry"
        },
        "expires_at": time.time() + 100.0
    }

    import asyncio
    cached_res = asyncio.run(check_safe_browsing(url))
    assert cached_res["cache_hit"] is True

    # Simulate expired cache
    _SAFE_BROWSING_CACHE[url]["expires_at"] = time.time() - 10.0
    clear_safe_browsing_cache()
    assert len(_SAFE_BROWSING_CACHE) == 0


# Test 13: Graceful degradation on Gemini failures (401, 429, 502, 503, 504)
@pytest.mark.parametrize("error_cls, expected_ai_status", [
    (GeminiAuthError("Invalid API key"), "AUTH_ERROR"),
    (GeminiQuotaError("Quota exceeded"), "QUOTA_EXHAUSTED"),
    (GeminiUnavailableError("Model overloaded"), "UNAVAILABLE"),
    (GeminiTimeoutError("Request timed out"), "TIMEOUT"),
    (GeminiResponseError("Invalid JSON returned"), "FAILED"),
])
@patch("app.routes.analyze.analyze_url_with_gemini")
@patch("app.routes.analyze.check_safe_browsing")
def test_gemini_url_analysis_failure(mock_sb, mock_gemini, error_cls, expected_ai_status):
    mock_sb.return_value = {
        "configured": True,
        "checked": True,
        "is_safe": True,
        "status": "NO_THREAT_FOUND",
        "threat_types": [],
        "message": "Clean"
    }
    mock_gemini.side_effect = error_cls

    response = client.post("/api/analyze/url", json={
        "url": "https://www.example.com"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["gemini_used"] is False
    assert data["ai_status"] == expected_ai_status
    assert data["ai_error_message"] is not None
    assert data["safe_browsing_status"] == "NO_THREAT_FOUND"
    assert data["url_analysis"] is None


# Test 14: Risk-score consistency (0-30 Low, 31-60 Medium, 61-100 High)
def test_risk_score_consistency():
    assert score_to_category(0) == RiskCategory.LOW
    assert score_to_category(20) == RiskCategory.LOW
    assert score_to_category(30) == RiskCategory.LOW
    assert score_to_category(31) == RiskCategory.MEDIUM
    assert score_to_category(50) == RiskCategory.MEDIUM
    assert score_to_category(60) == RiskCategory.MEDIUM
    assert score_to_category(61) == RiskCategory.HIGH
    assert score_to_category(85) == RiskCategory.HIGH
    assert score_to_category(100) == RiskCategory.HIGH


# Test 15: Duplicate indicator prevention
def test_duplicate_indicator_prevention():
    heuristic_flags = [
        "Prominent brand name ('paypal') appears in subdomain or path while root domain is different ('security-alert.xyz')",
        "Domain uses high-abuse/low-reputation top-level domain (.xyz)"
    ]
    sb_result = {
        "configured": True,
        "checked": True,
        "is_safe": False,
        "status": "MATCH_FOUND",
        "threat_types": ["SOCIAL_ENGINEERING"],
        "message": "Safe Browsing match"
    }
    ai_raw = GeminiUrlAnalysisRaw(
        summary="Deceptive brand-spoofing landing page",
        estimated_risk_score=95,
        risk_level="HIGH",
        detected_brand="PayPal",
        is_brand_impersonation=True,
        is_lookalike_domain=False,
        is_phishing_login=False,
        is_suspicious_shortener=False,
        suspicious_patterns=[
            "Prominent brand name ('paypal') appears in subdomain or path while root domain is different ('security-alert.xyz')"
        ],
        ad_url_consistency="Mismatched",
        explanation="Phishing page impersonating PayPal",
        recommendations=["Do not enter credentials"]
    )

    assessment, detail = evaluate_url_risk(
        heuristic_flags=heuristic_flags,
        safe_browsing_result=sb_result,
        ai_result=ai_raw
    )

    titles = [ind.title for ind in assessment.indicators]
    # No duplicate titles or exact descriptions
    assert len(titles) == len(set(titles))
    assert assessment.risk_score >= 90
    assert assessment.risk_category == RiskCategory.HIGH


# Test 16: SSRF protection and private IP handling
@pytest.mark.parametrize("private_dest", [
    "http://localhost:8000/admin",
    "http://localhost/dashboard",
    "http://127.0.0.1/sensitive",
    "http://127.0.0.2:8080/internal",
    "http://192.168.1.1/router-login",
    "http://10.0.0.1/credentials",
    "http://172.16.0.50/metrics",
    "http://169.254.169.254/latest/meta-data/",  # Cloud metadata SSRF
    "http://[::1]/private-service",
    "http://0.0.0.0:8000/health",
])
def test_ssrf_protection_and_private_ip_handling(private_dest):
    # 1. Service layer direct rejection
    validation = validate_and_normalize_url(private_dest)
    assert validation["valid"] is False
    assert validation["status"] == "REJECTED_PRIVATE_IP"
    assert "SSRF" in validation["error"]

    # 2. API layer 400 rejection
    response = client.post("/api/analyze/url", json={"url": private_dest})
    assert response.status_code == 400
    assert "SSRF" in response.json()["detail"] or "private" in response.json()["detail"].lower()


# Test 17: Safe Browsing API v5 Protobuf wire format parsing
def test_protobuf_decoding():
    from app.services.safebrowsing_service import parse_search_urls_protobuf

    # Malware sample payload from Safe Browsing v5
    raw_malware = b"\n1\n+testsafebrowsing.appspot.com/s/malware.html\x12\x02\x01\x04\x12\x03\x08\xac\x02"
    threats, cache_sec = parse_search_urls_protobuf(raw_malware)
    assert len(threats) == 1
    assert threats[0]["uri"] == "testsafebrowsing.appspot.com/s/malware.html"
    assert "MALWARE" in threats[0]["threatTypes"]
    assert "POTENTIALLY_HARMFUL_APPLICATION" in threats[0]["threatTypes"]
    assert cache_sec == 300.0

    # Clean / empty response
    clean_raw = b"\x12\x03\x08\xac\x02"
    threats_clean, cache_clean = parse_search_urls_protobuf(clean_raw)
    assert threats_clean == []
    assert cache_clean == 300.0


# Test 18: Safe Browsing success + Gemini quota exceeded
@patch("app.routes.analyze.analyze_url_with_gemini")
@patch("app.routes.analyze.check_safe_browsing")
def test_safe_browsing_success_gemini_quota_exceeded(mock_sb, mock_gemini):
    mock_sb.return_value = {
        "configured": True,
        "checked": True,
        "is_safe": True,
        "status": "NO_THREAT_FOUND",
        "threat_types": [],
        "message": "No threat found",
        "cache_hit": False
    }
    mock_gemini.side_effect = GeminiQuotaError("Daily request quota has been exhausted")

    response = client.post("/api/analyze/url", json={
        "url": "https://www.nordstrom.com/browse/sale"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["gemini_used"] is False
    assert data["ai_status"] == "QUOTA_EXHAUSTED"
    assert "quota" in data["ai_error_message"].lower()
    assert data["safe_browsing_status"] == "NO_THREAT_FOUND"
    assert data["risk_category"] == "Low"
    assert data["url_analysis"] is None


# Test 19: Safe Browsing threat match + Gemini unavailable
@patch("app.routes.analyze.analyze_url_with_gemini")
@patch("app.routes.analyze.check_safe_browsing")
def test_safe_browsing_threat_match_gemini_unavailable(mock_sb, mock_gemini):
    mock_sb.return_value = {
        "configured": True,
        "checked": True,
        "is_safe": False,
        "status": "MATCH_FOUND",
        "threat_types": ["MALWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
        "message": "Flagged as MALWARE",
        "cache_hit": False
    }
    mock_gemini.side_effect = GeminiUnavailableError("Gemini is down")

    response = client.post("/api/analyze/url", json={
        "url": "https://testsafebrowsing.appspot.com/s/malware.html"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["gemini_used"] is False
    assert data["ai_status"] == "UNAVAILABLE"
    assert data["safe_browsing_status"] == "MATCH_FOUND"
    assert "MALWARE" in data["threat_types"]
    assert data["risk_score"] >= 95
    assert data["risk_category"] == "High"
    assert data["risk_level"] == "HIGH"


# Test 20: Safe Browsing no match + Gemini unavailable
@patch("app.routes.analyze.analyze_url_with_gemini")
@patch("app.routes.analyze.check_safe_browsing")
def test_safe_browsing_no_match_gemini_unavailable(mock_sb, mock_gemini):
    mock_sb.return_value = {
        "configured": True,
        "checked": True,
        "is_safe": True,
        "status": "NO_THREAT_FOUND",
        "threat_types": [],
        "message": "Clean destination",
        "cache_hit": False
    }
    mock_gemini.side_effect = GeminiUnavailableError("503 Service Unavailable")

    response = client.post("/api/analyze/url", json={
        "url": "https://www.example.com"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["gemini_used"] is False
    assert data["ai_status"] == "UNAVAILABLE"
    assert data["safe_browsing_status"] == "NO_THREAT_FOUND"
    assert data["risk_score"] <= 30
    assert data["risk_category"] == "Low"


# Test 21: Both services unavailable
@patch("app.routes.analyze.analyze_url_with_gemini")
@patch("app.routes.analyze.check_safe_browsing")
def test_both_services_unavailable(mock_sb, mock_gemini):
    mock_sb.return_value = {
        "configured": True,
        "checked": False,
        "is_safe": None,
        "status": "UNAVAILABLE",
        "threat_types": [],
        "message": "Security database check unavailable",
        "cache_hit": False
    }
    mock_gemini.side_effect = GeminiUnavailableError("Gemini unavailable")

    response = client.post("/api/analyze/url", json={
        "url": "https://www.example.com"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["gemini_used"] is False
    assert data["ai_status"] == "UNAVAILABLE"
    assert data["safe_browsing_status"] == "UNAVAILABLE"
    assert data["findings"]["safe_browsing_checked"] is False
    assert data["api_verified"] is False
    assert "unavailable" in data["explanation"].lower() or "unavailable" in data["summary"].lower()


# Test 22: Successful combined analysis
@patch("app.routes.analyze.analyze_url_with_gemini")
@patch("app.routes.analyze.check_safe_browsing")
def test_successful_combined_analysis(mock_sb, mock_gemini):
    mock_sb.return_value = {
        "configured": True,
        "checked": True,
        "is_safe": True,
        "status": "NO_THREAT_FOUND",
        "threat_types": [],
        "message": "No threat found",
        "cache_hit": False
    }
    mock_gemini.return_value = (MOCK_SAFE_URL_AI, "gemini-3.5-flash")

    response = client.post("/api/analyze/url", json={
        "url": "https://www.nordstrom.com/browse/sale",
        "ad_text": "Nordstrom sale 20% off",
        "source_context": "Social Media"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["gemini_used"] is True
    assert data["ai_status"] == "SUCCESS"
    assert data["model_used"] == "gemini-3.5-flash"
    assert data["url_analysis"] is not None
    assert data["safe_browsing_status"] == "NO_THREAT_FOUND"
    assert data["risk_category"] == "Low"


# Test 23: Fallback heuristic risk scoring rules without AI
def test_fallback_heuristic_scoring_rules():
    from app.services.risk_engine import evaluate_url_risk
    
    # 1. Clean URL + Clean Safe Browsing -> Low risk
    assessment, _ = evaluate_url_risk(
        heuristic_flags=[],
        safe_browsing_result={"is_safe": True, "status": "NO_THREAT_FOUND", "threat_types": []},
        ai_result=None,
        url_info={"is_url_shortener": False}
    )
    assert assessment.risk_score == 10
    assert assessment.risk_category == RiskCategory.LOW

    # 2. Clean Safe Browsing + Multiple suspicious structural heuristics -> Elevated risk (Clean SB alone does not guarantee low risk)
    assessment_heuristics, _ = evaluate_url_risk(
        heuristic_flags=[
            "Direct IP address utilized as destination host",
            "Domain uses high-abuse/low-reputation top-level domain (.xyz)",
            "URL contains sensitive account/security bait keyword: 'verify'"
        ],
        safe_browsing_result={"is_safe": True, "status": "NO_THREAT_FOUND", "threat_types": []},
        ai_result=None,
        url_info={"is_url_shortener": False}
    )
    # 10 + 25 (IP) + 15 (TLD) + 25 (Bait) = 75 -> elevated to >= 75 (Unified 2+ HIGH floor >= 85)
    assert assessment_heuristics.risk_score >= 75
    assert assessment_heuristics.risk_category == RiskCategory.HIGH

    # 3. Confirmed Safe Browsing threat match -> Always HIGH risk (>=95)
    assessment_threat, _ = evaluate_url_risk(
        heuristic_flags=[],
        safe_browsing_result={"is_safe": False, "status": "MATCH_FOUND", "threat_types": ["MALWARE"]},
        ai_result=None,
        url_info={"is_url_shortener": False}
    )
    assert assessment_threat.risk_score >= 95
    assert assessment_threat.risk_category == RiskCategory.HIGH


