import time
from datetime import datetime, timezone, timedelta, time as dtime
from zoneinfo import ZoneInfo
import pytest
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from app.main import app
from app.services.gemini_model_manager import (
    GeminiModelManager,
    get_model_manager,
    FallbackMetadata,
    parse_duration_value,
    get_seconds_until_pacific_midnight,
    PACIFIC_TZ
)
from app.services.gemini_exceptions import (
    GeminiError,
    GeminiAuthError,
    GeminiQuotaError,
    GeminiUnavailableError,
    GeminiTimeoutError,
    GeminiResponseError
)
from app.models.schemas import (
    GeminiTextAnalysisRaw,
    GeminiImageAnalysisRaw,
    GeminiUrlAnalysisRaw,
    AssessmentStatus,
    RiskCategory
)

client = TestClient(app)

class MockGoogleAPIError(Exception):
    """Simulates google.genai.errors.APIError."""
    def __init__(self, code: int, message: str, details: list = None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.details = details or []
        self.response_json = {
            "error": {
                "code": code,
                "message": message,
                "status": "RESOURCE_EXHAUSTED" if code == 429 else ("UNAVAILABLE" if code == 503 else "ERROR"),
                "details": self.details
            }
        }

MOCK_TEXT_AI_DATA = GeminiTextAnalysisRaw(
    summary="Text advert analyzed successfully.",
    estimated_risk_score=15,
    risk_level="LOW",
    explanation="Standard commercial promotion without fraud cues.",
    detected_claims=["Sale"],
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
    recommended_actions=["Shop through official channels."]
)

MOCK_IMAGE_AI_DATA = GeminiImageAnalysisRaw(
    summary="Image ad analyzed successfully.",
    estimated_risk_score=20,
    risk_level="LOW",
    visual_observations=["Seasonal retail banner"],
    detected_claims=["20% off"],
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
    explanation="Clean layout.",
    recommendations=["Verify website lock."]
)

MOCK_URL_AI_DATA = GeminiUrlAnalysisRaw(
    summary="Destination URL analyzed successfully.",
    estimated_risk_score=10,
    risk_level="LOW",
    detected_brand=None,
    is_brand_impersonation=False,
    is_lookalike_domain=False,
    is_phishing_login=False,
    is_suspicious_shortener=False,
    suspicious_patterns=[],
    ad_url_consistency="Consistent",
    explanation="Standard verified domain.",
    recommendations=["Verify SSL."]
)


@pytest.fixture(autouse=True)
def reset_manager_registry():
    """Reset model manager registry before each test."""
    manager = get_model_manager()
    manager.reset_registry()
    yield
    manager.reset_registry()


# Test 1: Primary model success
def test_primary_model_success():
    manager = GeminiModelManager()
    with patch.object(manager, "get_model_priority_list", return_value=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]):
        def mock_call(model_name: str):
            assert model_name == "gemini-3.5-flash-lite"
            return {"status": "success", "model": model_name}

        result, meta = manager.execute_with_fallback("Test Operation", mock_call)
        assert result["status"] == "success"
        assert meta.model_used == "gemini-3.5-flash-lite"
        assert meta.fallback_used is False
        assert meta.fallback_reason is None
        assert meta.models_attempted == ["gemini-3.5-flash-lite"]
        assert meta.primary_model == "gemini-3.5-flash-lite"


# Test 2: Primary model quota exceeded; first fallback succeeds
def test_primary_quota_exceeded_first_fallback_succeeds():
    manager = GeminiModelManager()
    with patch.object(manager, "get_model_priority_list", return_value=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]):
        def mock_call(model_name: str):
            if model_name == "gemini-3.5-flash-lite":
                raise MockGoogleAPIError(429, "Daily request quota exceeded for model gemini-3.5-flash-lite.")
            return {"status": "success", "model": model_name}

        result, meta = manager.execute_with_fallback("Test Operation", mock_call)
        assert result["status"] == "success"
        assert meta.model_used == "gemini-3.1-flash-lite"
        assert meta.fallback_used is True
        assert "daily request quota exhausted" in meta.fallback_reason.lower()
        assert meta.models_attempted == ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]


# Test 3: Primary and first fallback exhausted; second fallback succeeds
def test_primary_and_first_fallback_exhausted_second_succeeds():
    manager = GeminiModelManager()
    with patch.object(manager, "get_model_priority_list", return_value=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]):
        def mock_call(model_name: str):
            if model_name in ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite"):
                raise MockGoogleAPIError(429, f"Quota exceeded for {model_name}")
            return {"status": "success", "model": model_name}

        result, meta = manager.execute_with_fallback("Test Operation", mock_call)
        assert result["status"] == "success"
        assert meta.model_used == "gemini-2.5-flash-lite"
        assert meta.fallback_used is True
        assert meta.models_attempted == ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]


# Test 4: All models exhausted
def test_all_models_exhausted_raises_quota_error():
    manager = GeminiModelManager()
    with patch.object(manager, "get_model_priority_list", return_value=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]):
        def mock_call(model_name: str):
            raise MockGoogleAPIError(429, f"Daily quota exhausted for {model_name}")

        with pytest.raises(GeminiQuotaError) as exc_info:
            manager.execute_with_fallback("Test Operation", mock_call)

        assert "exhausted quota" in str(exc_info.value).lower()


# Test 5: Model recovers after cooldown
def test_model_recovers_after_cooldown():
    manager = GeminiModelManager()
    with patch.object(manager, "get_model_priority_list", return_value=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]):
        call_count = {"primary": 0, "fallback": 0}

        def mock_call(model_name: str):
            if model_name == "gemini-3.5-flash-lite":
                call_count["primary"] += 1
                if call_count["primary"] == 1:
                    # Fail on first call with a 1-second retryDelay
                    raise MockGoogleAPIError(429, "Rate limit reached", details=[{"@type": "google.rpc.RetryInfo", "retryDelay": "1s"}])
                return {"status": "recovered"}
            call_count["fallback"] += 1
            return {"status": "fallback"}

        # 1. First execution: primary fails, falls back to gemini-3.1-flash-lite
        res1, meta1 = manager.execute_with_fallback("Op1", mock_call)
        assert meta1.model_used == "gemini-3.1-flash-lite"
        assert meta1.fallback_used is True

        # 2. Immediate second execution: primary is still in cooldown, automatically skipped!
        res2, meta2 = manager.execute_with_fallback("Op2", mock_call)
        assert meta2.model_used == "gemini-3.1-flash-lite"
        assert "in cooldown" in meta2.fallback_reason

        # 3. Wait for cooldown to expire (> 2 seconds)
        time.sleep(2.1)

        # 4. Third execution: primary has recovered and is selected again
        res3, meta3 = manager.execute_with_fallback("Op3", mock_call)
        assert meta3.model_used == "gemini-3.5-flash-lite"
        assert meta3.fallback_used is False


# Test 6: RPM throttling extraction
def test_rpm_throttling_retry_delay():
    manager = GeminiModelManager()
    err = MockGoogleAPIError(429, "Rate limit exceeded (5 requests/minute). Please retry in 12s.", details=[
        {"@type": "google.rpc.RetryInfo", "retryDelay": "12s"}
    ])
    cat, can_fb, cooldown, reason, retry_delay = manager.classify_error(err, "gemini-3.5-flash-lite")
    assert cat == "RATE_LIMIT_RPM"
    assert can_fb is True
    assert retry_delay == 13
    assert cooldown == 13.0


# Test 7: Daily quota exhaustion extraction calculates cooldown until Pacific midnight
def test_daily_quota_exhaustion_classification():
    manager = GeminiModelManager()
    err = MockGoogleAPIError(429, "Resource has been exhausted (e.g. check quota). Daily requests per day limit exceeded.")
    cat, can_fb, cooldown, reason, retry_delay = manager.classify_error(err, "gemini-3.5-flash-lite")
    assert cat == "QUOTA_EXHAUSTED_DAILY"
    assert can_fb is True
    assert retry_delay is None
    assert cooldown > 0.0
    assert "Pacific midnight reset" in reason


# Test 8: 503 model unavailability
def test_503_model_unavailability_fallback():
    manager = GeminiModelManager()
    with patch.object(manager, "get_model_priority_list", return_value=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]):
        def mock_call(model_name: str):
            if model_name == "gemini-3.5-flash-lite":
                raise MockGoogleAPIError(503, "The model is experiencing temporary high demand.")
            return {"status": "success", "model": model_name}

        result, meta = manager.execute_with_fallback("Test Operation", mock_call)
        assert meta.model_used == "gemini-3.1-flash-lite"
        assert meta.fallback_used is True
        assert "503" in meta.fallback_reason or "high demand" in meta.fallback_reason.lower()


# Test 9: 504 timeout fallback
def test_504_timeout_fallback():
    manager = GeminiModelManager()
    with patch.object(manager, "get_model_priority_list", return_value=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]):
        def mock_call(model_name: str):
            if model_name == "gemini-3.5-flash-lite":
                raise TimeoutError("Deadline exceeded connecting to model")
            return {"status": "success", "model": model_name}

        result, meta = manager.execute_with_fallback("Test Operation", mock_call)
        assert meta.model_used == "gemini-3.1-flash-lite"
        assert meta.fallback_used is True


# Test 10: Invalid API credentials halts immediately without fallback
def test_invalid_api_credentials_halts_immediately():
    manager = GeminiModelManager()
    with patch.object(manager, "get_model_priority_list", return_value=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]):
        attempted = []

        def mock_call(model_name: str):
            attempted.append(model_name)
            raise MockGoogleAPIError(401, "API_KEY_INVALID")

        with pytest.raises(GeminiAuthError):
            manager.execute_with_fallback("Test Operation", mock_call)

        # Crucial requirement: Must halt immediately and NOT attempt fallbacks on auth error
        assert attempted == ["gemini-3.5-flash-lite"]


# Test 11: Invalid requests (HTTP 400) do not switch models
def test_invalid_requests_halt_without_switching():
    manager = GeminiModelManager()
    with patch.object(manager, "get_model_priority_list", return_value=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]):
        attempted = []

        def mock_call(model_name: str):
            attempted.append(model_name)
            raise MockGoogleAPIError(400, "INVALID_ARGUMENT: Unsupported temperature range")

        with pytest.raises(GeminiError):
            manager.execute_with_fallback("Test Operation", mock_call)

        assert attempted == ["gemini-3.5-flash-lite"]


# Test 12: Fallback structured JSON validation
def test_fallback_structured_json_validation():
    manager = GeminiModelManager()
    with patch.object(manager, "get_model_priority_list", return_value=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]):
        def mock_call(model_name: str):
            if model_name == "gemini-3.5-flash-lite":
                raise MockGoogleAPIError(429, "Quota exhausted")
            # Returns valid Pydantic model
            return MOCK_TEXT_AI_DATA

        result, meta = manager.execute_with_fallback("Text Test", mock_call)
        assert isinstance(result, GeminiTextAnalysisRaw)
        assert result.summary == "Text advert analyzed successfully."
        assert meta.model_used == "gemini-3.1-flash-lite"
        assert meta.fallback_used is True


# Test 13: Text analysis fallback via route
@patch("app.routes.analyze.analyze_text_with_gemini")
def test_text_analysis_endpoint_fallback(mock_analyze):
    meta = FallbackMetadata(
        model_used="gemini-3.1-flash-lite",
        fallback_used=True,
        fallback_reason="Primary model gemini-3.5-flash-lite daily quota exhausted",
        models_attempted=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"],
        primary_model="gemini-3.5-flash-lite"
    )
    mock_analyze.return_value = (MOCK_TEXT_AI_DATA, meta)

    response = client.post("/api/analyze/text", json={"text": "Summer clearance sale 20% off all designer apparel."})
    assert response.status_code == 200
    data = response.json()
    assert data["model_used"] == "gemini-3.1-flash-lite"
    assert data["fallback_used"] is True
    assert "daily quota exhausted" in data["fallback_reason"].lower()
    assert data["models_attempted"] == ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
    assert data["primary_model"] == "gemini-3.5-flash-lite"


# Test 14: Image analysis fallback via route
@patch("app.routes.analyze.analyze_image_with_gemini")
@patch("app.routes.analyze.extract_text_from_image")
def test_image_analysis_endpoint_fallback(mock_ocr, mock_vision):
    mock_ocr.return_value = {"success": True, "status": "NO_TEXT_DETECTED", "text": None, "confidence": None}
    meta = FallbackMetadata(
        model_used="gemini-3.1-flash-lite",
        fallback_used=True,
        fallback_reason="Primary model gemini-3.5-flash-lite daily quota exhausted",
        models_attempted=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"],
        primary_model="gemini-3.5-flash-lite"
    )
    mock_vision.return_value = (MOCK_IMAGE_AI_DATA, meta)

    # Generate valid in-memory PNG using Pillow
    from PIL import Image
    import io
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=(100, 150, 200))
    img.save(buf, format="PNG")
    valid_png = buf.getvalue()

    response = client.post(
        "/api/analyze/image",
        files={"file": ("test.png", valid_png, "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["model_used"] == "gemini-3.1-flash-lite"
    assert data["fallback_used"] is True
    assert data["models_attempted"] == ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]


# Test 15: URL analysis fallback via route
@patch("app.routes.analyze.analyze_url_with_gemini")
@patch("app.routes.analyze.check_safe_browsing")
def test_url_analysis_endpoint_fallback(mock_sb, mock_gemini):
    mock_sb.return_value = {
        "configured": True,
        "checked": True,
        "is_safe": True,
        "status": "NO_THREAT_FOUND",
        "threat_types": []
    }
    meta = FallbackMetadata(
        model_used="gemini-3.1-flash-lite",
        fallback_used=True,
        fallback_reason="Primary model gemini-3.5-flash-lite daily quota exhausted",
        models_attempted=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"],
        primary_model="gemini-3.5-flash-lite"
    )
    mock_gemini.return_value = (MOCK_URL_AI_DATA, meta)

    response = client.post("/api/analyze/url", json={"url": "https://www.nordstrom.com/sale"})
    assert response.status_code == 200
    data = response.json()
    assert data["gemini_used"] is True
    assert data["model_used"] == "gemini-3.1-flash-lite"
    assert data["fallback_used"] is True
    assert data["models_attempted"] == ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]


# Test 16: Concurrent request handling
def test_concurrent_request_handling():
    manager = GeminiModelManager()
    with patch.object(manager, "get_model_priority_list", return_value=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]):
        def worker(thread_id: int):
            def mock_call(m: str):
                if thread_id % 2 == 1 and m == "gemini-3.5-flash-lite":
                    raise MockGoogleAPIError(429, "Rate limit")
                return {"thread": thread_id, "model": m}

            return manager.execute_with_fallback(f"Concurrent-{thread_id}", mock_call)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker, i) for i in range(16)]
            results = [f.result() for f in futures]

        assert len(results) == 16
        for res, meta in results:
            assert meta.model_used in ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite")


# Test 17: Incorrect model configuration (404 Not Found)
def test_incorrect_model_configuration():
    manager = GeminiModelManager()
    with patch.object(manager, "get_model_priority_list", return_value=["invalid-model-name", "gemini-3.5-flash-lite"]):
        def mock_call(m: str):
            if m == "invalid-model-name":
                raise MockGoogleAPIError(404, "Model not found or unsupported")
            return {"status": "success", "model": m}

        res, meta = manager.execute_with_fallback("Test Config", mock_call)
        assert meta.model_used == "gemini-3.5-flash-lite"
        assert meta.fallback_used is True
        assert "404" in meta.fallback_reason


# Test 18: No fabricated results when all models fail
@patch("app.routes.analyze.analyze_url_with_gemini")
@patch("app.routes.analyze.check_safe_browsing")
def test_no_fabricated_results_when_all_models_fail(mock_sb, mock_gemini):
    mock_sb.return_value = {
        "configured": True,
        "checked": True,
        "is_safe": True,
        "status": "NO_THREAT_FOUND",
        "threat_types": []
    }
    mock_gemini.side_effect = GeminiQuotaError("All configured Gemini models exhausted quota.")

    response = client.post("/api/analyze/url", json={"url": "https://www.target.com/clearance"})
    assert response.status_code == 200
    data = response.json()
    assert data["gemini_used"] is False
    assert data["model_used"] is None
    assert data["ai_status"] == "QUOTA_EXHAUSTED"
    assert data["url_analysis"] is None  # No fabricated AI detail
    assert "Google Safe Browsing v5" in data["checks_completed"]
    assert any("Gemini AI Contextual Analysis" in c for c in data["checks_unavailable"])


# Test 19: AI Models Status Endpoint
def test_ai_models_status_endpoint():
    response = client.get("/api/ai/models/status")
    assert response.status_code == 200
    data = response.json()
    assert "configured_primary_model" in data
    assert "configured_fallback_models" in data
    assert "model_priority" in data
    assert "models_status" in data
    assert len(data["model_priority"]) >= 1


# Test 20: Comprehensive retryDelay parsing across string, compound, dict, and message formats
def test_retry_delay_parsing_various_formats():
    manager = GeminiModelManager()

    # 1. Direct parse_duration_value tests
    assert parse_duration_value("43.518s") == 43.518
    assert parse_duration_value("15s") == 15.0
    assert parse_duration_value("3600s") == 3600.0
    assert parse_duration_value("18h24m10s") == (18 * 3600 + 24 * 60 + 10)
    assert parse_duration_value("1h 30m 10s") == (3600 + 30 * 60 + 10)
    assert parse_duration_value("45m 12s") == (45 * 60 + 12)
    assert parse_duration_value("2h") == 7200.0
    assert parse_duration_value("15 minutes") == 900.0
    assert parse_duration_value("45 seconds") == 45.0
    assert parse_duration_value({"seconds": 45, "nanos": 500000000}) == 45.5
    assert parse_duration_value({"seconds": "120"}) == 120.0
    assert parse_duration_value(60) == 60.0
    assert parse_duration_value(None) is None
    assert parse_duration_value("invalid text") is None

    # 2. Extract from structured details in MockGoogleAPIError
    err1 = MockGoogleAPIError(429, "Rate limit reached", details=[
        {"@type": "google.rpc.RetryInfo", "retryDelay": "43.518s"}
    ])
    assert manager.extract_retry_delay(err1) == 44

    err_compound = MockGoogleAPIError(429, "Daily quota limit reached", details=[
        {"@type": "google.rpc.RetryInfo", "retryDelay": "18h24m10s"}
    ])
    assert manager.extract_retry_delay(err_compound) == (18 * 3600 + 24 * 60 + 10) + 1

    err_dict = MockGoogleAPIError(429, "Token rate limit reached", details=[
        {"@type": "google.rpc.RetryInfo", "retryDelay": {"seconds": 30, "nanos": 0}}
    ])
    assert manager.extract_retry_delay(err_dict) == 31

    # 3. Extract from error message strings
    err_msg1 = Exception("Resource has been exhausted (e.g. check quota). Please retry in 43.518s.")
    assert manager.extract_retry_delay(err_msg1) == 44

    err_msg2 = Exception("Daily quota exceeded. Please retry in 18h24m10s.")
    assert manager.extract_retry_delay(err_msg2) == (18 * 3600 + 24 * 60 + 10) + 1

    err_msg3 = Exception("Rate limit reached. retryDelay: '3600s'")
    assert manager.extract_retry_delay(err_msg3) == 3601

    err_msg4 = Exception("Resource exhausted without retry advice")
    assert manager.extract_retry_delay(err_msg4) is None


# Test 21: Daily quota uses Google's actual retryDelay rather than fixed 3600s
def test_daily_quota_uses_provided_retry_delay():
    manager = GeminiModelManager()
    # Google explicitly provides retryDelay="7200s" (2 hours)
    err = MockGoogleAPIError(
        429,
        "Quota exceeded for quota metric 'GenerateContentRequestsPerDay' and limit 'GenerateContentRequestsPerDayPerProjectPerModel'.",
        details=[{"@type": "google.rpc.RetryInfo", "retryDelay": "7200s"}]
    )
    cat, can_fb, cooldown, reason, retry_delay = manager.classify_error(err, "gemini-3.5-flash-lite")
    assert cat == "QUOTA_EXHAUSTED_DAILY"
    assert can_fb is True
    assert retry_delay == 7201
    assert cooldown == 7201.0  # Uses actual retry delay rather than fixed 3600s
    assert "Google suggested retry in 7201s" in reason


# Test 22: Daily quota without retryDelay calculates cooldown until next Pacific midnight
def test_daily_quota_without_retry_delay_uses_pacific_midnight():
    manager = GeminiModelManager()
    err = MockGoogleAPIError(
        429,
        "Quota exceeded for quota metric 'GenerateContentRequestsPerDay'. No delay provided."
    )
    # Mock fixed time: 22:00 (10:00 PM) on 2026-01-15 in America/Los_Angeles
    fixed_time = datetime(2026, 1, 15, 22, 0, 0, tzinfo=PACIFIC_TZ)
    # Next midnight is 2026-01-16 00:00:00 (exactly 2 hours / 7200 seconds later)

    cat, can_fb, cooldown, reason, retry_delay = manager.classify_error(err, "gemini-3.5-flash-lite", now=fixed_time)
    assert cat == "QUOTA_EXHAUSTED_DAILY"
    assert can_fb is True
    assert retry_delay is None
    assert cooldown == 7200.0  # Exactly 2 hours until midnight Pacific
    assert "Pacific midnight reset" in reason
    assert "7200s" in reason


# Test 23: Distinguish Daily Quota (RPD) vs TPM vs RPM
def test_distinguish_rpd_tpm_and_rpm():
    manager = GeminiModelManager()

    # 1. RPD: GenerateContentRequestsPerDay
    err_rpd = MockGoogleAPIError(
        429,
        "Quota exceeded for quota metric 'GenerateContentRequestsPerDay' and limit 'GenerateContentRequestsPerDayPerProjectPerModel'.",
        details=[{"@type": "google.rpc.RetryInfo", "retryDelay": "1800s"}]
    )
    cat, can_fb, cd, reason, _ = manager.classify_error(err_rpd, "gemini-3.5-flash-lite")
    assert cat == "QUOTA_EXHAUSTED_DAILY"
    assert cd == 1801.0

    # 2. TPM: GenerateContentTokensPerMinute
    err_tpm = MockGoogleAPIError(
        429,
        "Quota exceeded for quota metric 'GenerateContentTokensPerMinute' and limit 'GenerateContentTokensPerMinutePerProjectPerModel'.",
        details=[{"@type": "google.rpc.RetryInfo", "retryDelay": "20s"}]
    )
    cat_tpm, can_fb_tpm, cd_tpm, reason_tpm, _ = manager.classify_error(err_tpm, "gemini-3.5-flash-lite")
    assert cat_tpm == "RATE_LIMIT_TPM"
    assert can_fb_tpm is True
    assert cd_tpm == 21.0
    assert "token rate limit reached (TPM)" in reason_tpm

    # 3. RPM: GenerateContentRequestsPerMinute
    err_rpm = MockGoogleAPIError(
        429,
        "Quota exceeded for quota metric 'GenerateContentRequestsPerMinute' and limit 'GenerateContentRequestsPerMinutePerProjectPerModel'.",
        details=[{"@type": "google.rpc.RetryInfo", "retryDelay": "15s"}]
    )
    cat_rpm, can_fb_rpm, cd_rpm, reason_rpm, _ = manager.classify_error(err_rpm, "gemini-3.5-flash-lite")
    assert cat_rpm == "RATE_LIMIT_RPM"
    assert can_fb_rpm is True
    assert cd_rpm == 16.0
    assert "request rate limit reached (RPM)" in reason_rpm


# Test 24: Never repeatedly retry exhausted models during active cooldown
def test_never_repeatedly_retry_exhausted_models():
    manager = GeminiModelManager()
    with patch.object(manager, "get_model_priority_list", return_value=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]):
        call_tracker = {"gemini-3.5-flash-lite": 0, "gemini-3.1-flash-lite": 0}

        def mock_call(model_name: str):
            call_tracker[model_name] += 1
            if model_name == "gemini-3.5-flash-lite":
                # Primary fails with daily quota exhaustion
                raise MockGoogleAPIError(
                    429,
                    "Quota exceeded for quota metric 'GenerateContentRequestsPerDay'.",
                    details=[{"@type": "google.rpc.RetryInfo", "retryDelay": "3600s"}]
                )
            return {"status": "ok", "model": model_name}

        # 1. First execution: Primary is called once, fails, enters 3601s cooldown, falls back to secondary
        res1, meta1 = manager.execute_with_fallback("Op1", mock_call)
        assert meta1.model_used == "gemini-3.1-flash-lite"
        assert meta1.fallback_used is True
        assert call_tracker["gemini-3.5-flash-lite"] == 1
        assert call_tracker["gemini-3.1-flash-lite"] == 1

        # 2. Execute 10 consecutive requests while primary is in cooldown
        for i in range(2, 12):
            res_i, meta_i = manager.execute_with_fallback(f"Op{i}", mock_call)
            assert meta_i.model_used == "gemini-3.1-flash-lite"
            assert meta_i.fallback_used is True
            assert "in cooldown" in meta_i.fallback_reason

        # CRITICAL INVARIANT: The exhausted model MUST NEVER be retried while in cooldown!
        assert call_tracker["gemini-3.5-flash-lite"] == 1  # Exactly 1 call, NEVER repeatedly called!
        assert call_tracker["gemini-3.1-flash-lite"] == 11


# Test 25: Model recovery after cooldown expires
def test_model_recovery_after_cooldown_expires():
    manager = GeminiModelManager()
    with patch.object(manager, "get_model_priority_list", return_value=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]):
        call_tracker = {"gemini-3.5-flash-lite": 0, "gemini-3.1-flash-lite": 0}

        def mock_call(model_name: str):
            call_tracker[model_name] += 1
            if model_name == "gemini-3.5-flash-lite":
                if call_tracker["gemini-3.5-flash-lite"] == 1:
                    # Fails on call 1 with a short 0.2s retryDelay
                    raise MockGoogleAPIError(429, "Rate limit reached", details=[{"@type": "google.rpc.RetryInfo", "retryDelay": "0.2s"}])
                return {"status": "success", "model": model_name}
            return {"status": "fallback", "model": model_name}

        # First request: primary fails, cooldown set to ~1.2s
        res1, meta1 = manager.execute_with_fallback("Op1", mock_call)
        assert meta1.model_used == "gemini-3.1-flash-lite"
        assert call_tracker["gemini-3.5-flash-lite"] == 1

        # Second request immediate: primary is skipped
        res2, meta2 = manager.execute_with_fallback("Op2", mock_call)
        assert meta2.model_used == "gemini-3.1-flash-lite"
        assert call_tracker["gemini-3.5-flash-lite"] == 1  # Not retried!

        # Wait for cooldown to expire (> 1.25s)
        time.sleep(1.3)

        # Third request: primary has recovered and is called again
        res3, meta3 = manager.execute_with_fallback("Op3", mock_call)
        assert meta3.model_used == "gemini-3.5-flash-lite"
        assert meta3.fallback_used is False
        assert call_tracker["gemini-3.5-flash-lite"] == 2


# Test 26: Pacific midnight calculation during PST (Standard Time, UTC-8)
def test_pacific_midnight_cooldown_during_pst():
    manager = GeminiModelManager()
    # Fixed PST time: 2026-01-15 14:30:00 PST (2:30 PM)
    pst_now = datetime(2026, 1, 15, 14, 30, 0, tzinfo=PACIFIC_TZ)
    # Next midnight is 2026-01-16 00:00:00 PST -> Exactly 9.5 hours (34,200 seconds)
    expected_seconds = 9.5 * 3600.0

    seconds = get_seconds_until_pacific_midnight(pst_now)
    assert seconds == expected_seconds == 34200.0

    err = MockGoogleAPIError(429, "Daily request quota exceeded (RPD).")
    cat, can_fb, cd, reason, retry_delay = manager.classify_error(err, "gemini-3.5-flash-lite", now=pst_now)
    assert cat == "QUOTA_EXHAUSTED_DAILY"
    assert cd == 34200.0
    assert retry_delay is None
    assert "Pacific midnight reset" in reason
    assert "34200s" in reason


# Test 27: Pacific midnight calculation during PDT (Daylight Saving Time, UTC-7)
def test_pacific_midnight_cooldown_during_pdt():
    manager = GeminiModelManager()
    # Fixed PDT time: 2026-07-20 18:00:00 PDT (6:00 PM)
    pdt_now = datetime(2026, 7, 20, 18, 0, 0, tzinfo=PACIFIC_TZ)
    # Next midnight is 2026-07-21 00:00:00 PDT -> Exactly 6.0 hours (21,600 seconds)
    expected_seconds = 6.0 * 3600.0

    seconds = get_seconds_until_pacific_midnight(pdt_now)
    assert seconds == expected_seconds == 21600.0

    err = MockGoogleAPIError(429, "Quota exceeded for GenerateContentRequestsPerDay.")
    cat, can_fb, cd, reason, retry_delay = manager.classify_error(err, "gemini-3.5-flash-lite", now=pdt_now)
    assert cat == "QUOTA_EXHAUSTED_DAILY"
    assert cd == 21600.0
    assert retry_delay is None
    assert "Pacific midnight reset" in reason
    assert "21600s" in reason


# Test 28: Pacific daylight-saving Spring Forward transition (PST -> PDT)
def test_pacific_midnight_cooldown_spring_forward_dst_transition():
    manager = GeminiModelManager()
    # Spring Forward date in 2026: Sunday, March 8, 2026
    # Clocks jump forward at 02:00:00 PST to 03:00:00 PDT (1 hour lost)
    # Suppose error occurs at 01:00:00 PST on Sunday, March 8, 2026
    spring_now = datetime(2026, 3, 8, 1, 0, 0, tzinfo=PACIFIC_TZ)
    # Next midnight is Monday, March 9, 2026 00:00:00 PDT
    # Total elapsed wall-clock hours = 22.0 hours (79,200 seconds)
    expected_seconds = 22.0 * 3600.0

    seconds = get_seconds_until_pacific_midnight(spring_now)
    assert seconds == expected_seconds == 79200.0

    err = MockGoogleAPIError(429, "Daily requests per day limit exceeded.")
    cat, can_fb, cd, reason, retry_delay = manager.classify_error(err, "gemini-3.5-flash-lite", now=spring_now)
    assert cat == "QUOTA_EXHAUSTED_DAILY"
    assert cd == 79200.0
    assert retry_delay is None
    assert "79200s" in reason


# Test 29: Pacific daylight-saving Fall Back transition (PDT -> PST)
def test_pacific_midnight_cooldown_fall_back_dst_transition():
    manager = GeminiModelManager()
    # Fall Back date in 2026: Sunday, November 1, 2026
    # Clocks fall back at 02:00:00 PDT to 01:00:00 PST (1 hour repeated)
    # Suppose error occurs at 00:30:00 PDT on Sunday, November 1, 2026
    fall_now = datetime(2026, 11, 1, 0, 30, 0, tzinfo=PACIFIC_TZ)
    # Next midnight is Monday, November 2, 2026 00:00:00 PST
    # Total elapsed wall-clock hours = 24.5 hours (88,200 seconds)
    expected_seconds = 24.5 * 3600.0

    seconds = get_seconds_until_pacific_midnight(fall_now)
    assert seconds == expected_seconds == 88200.0

    err = MockGoogleAPIError(429, "Daily request quota exhausted.")
    cat, can_fb, cd, reason, retry_delay = manager.classify_error(err, "gemini-3.5-flash-lite", now=fall_now)
    assert cat == "QUOTA_EXHAUSTED_DAILY"
    assert cd == 88200.0
    assert retry_delay is None
    assert "88200s" in reason


# Test 30: RPM and TPM cooldown handling remains unchanged (does not use Pacific midnight)
def test_rpm_and_tpm_remain_unchanged_by_pacific_midnight():
    manager = GeminiModelManager()
    fixed_time = datetime(2026, 1, 15, 12, 0, 0, tzinfo=PACIFIC_TZ)

    # 1. RPM error without retryDelay -> Uses GEMINI_RPM_COOLDOWN_SECONDS (60.0s), NOT 12h (43200s)
    err_rpm = MockGoogleAPIError(429, "Rate limit exceeded (GenerateContentRequestsPerMinute).")
    cat_rpm, _, cd_rpm, reason_rpm, _ = manager.classify_error(err_rpm, "gemini-3.5-flash-lite", now=fixed_time)
    assert cat_rpm == "RATE_LIMIT_RPM"
    assert cd_rpm == 60.0  # Kept unchanged!
    assert "request rate limit reached (RPM)" in reason_rpm

    # 2. TPM error without retryDelay -> Uses GEMINI_TPM_COOLDOWN_SECONDS (60.0s), NOT 12h (43200s)
    err_tpm = MockGoogleAPIError(429, "Rate limit exceeded (GenerateContentTokensPerMinute).")
    cat_tpm, _, cd_tpm, reason_tpm, _ = manager.classify_error(err_tpm, "gemini-3.5-flash-lite", now=fixed_time)
    assert cat_tpm == "RATE_LIMIT_TPM"
    assert cd_tpm == 60.0  # Kept unchanged!
    assert "token rate limit reached (TPM)" in reason_tpm


