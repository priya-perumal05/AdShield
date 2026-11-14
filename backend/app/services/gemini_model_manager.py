import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta, time as dtime
from zoneinfo import ZoneInfo
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from app.utils.config import get_settings
from app.models.schemas import ModelHealthRegistryResponse, ModelStatusDetail
from app.services.gemini_exceptions import (
    GeminiError,
    GeminiConfigurationError,
    GeminiAuthError,
    GeminiQuotaError,
    GeminiUnavailableError,
    GeminiTimeoutError,
    GeminiResponseError
)

logger = logging.getLogger("adshield.gemini.model_manager")

@dataclass
class ModelHealthRecord:
    """In-memory tracking record for a specific Gemini model."""
    model_name: str
    is_available: bool = True
    cooldown_until: Optional[float] = None
    cooldown_reason: Optional[str] = None
    cooldown_duration_seconds: float = 0.0
    last_error_category: Optional[str] = None
    last_error_message: Optional[str] = None
    total_requests: int = 0
    total_successes: int = 0
    total_failures: int = 0
    last_used_at: Optional[float] = None
    last_success_at: Optional[float] = None

    def is_currently_available(self, current_time: float) -> bool:
        if self.is_available:
            return True
        if self.cooldown_until is not None and current_time >= self.cooldown_until:
            # Cooldown expired - recover automatically
            self.is_available = True
            self.cooldown_until = None
            self.cooldown_reason = None
            return True
        return False

    def remaining_cooldown_seconds(self, current_time: float) -> int:
        if self.cooldown_until is not None and self.cooldown_until > current_time:
            return int(self.cooldown_until - current_time)
        return 0


class FallbackMetadata:
    """Metadata detailing the execution of an AI operation with model fallback tracking."""
    def __init__(
        self,
        model_used: str,
        fallback_used: bool = False,
        fallback_reason: Optional[str] = None,
        models_attempted: Optional[List[str]] = None,
        primary_model: Optional[str] = None
    ):
        self.model_used = model_used
        self.fallback_used = fallback_used
        self.fallback_reason = fallback_reason
        self.models_attempted = models_attempted or [model_used]
        self.primary_model = primary_model or model_used

    def __str__(self) -> str:
        return self.model_used

    def __repr__(self) -> str:
        return f"<FallbackMetadata model_used={self.model_used} fallback_used={self.fallback_used}>"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return self.model_used == other
        if isinstance(other, FallbackMetadata):
            return self.model_used == other.model_used
        return False


def parse_duration_value(val: Any) -> Optional[float]:
    """
    Parses a duration into total seconds as a float.
    Handles:
    - dict: {"seconds": 43, "nanos": 518000000} or {"seconds": "43"}
    - int or float: 43 or 43.5
    - strings:
        - "43.518s", "43s", "43 sec", "43 seconds"
        - "18h24m10s", "1h 30m 10s", "45m 12s", "2h", "15m"
        - "43.5"
    """
    if val is None:
        return None

    if isinstance(val, (int, float)):
        return float(val) if val >= 0 else None

    if isinstance(val, dict):
        try:
            sec = float(val.get("seconds", 0) or 0)
            nanos = float(val.get("nanos", 0) or 0)
            total = sec + (nanos / 1_000_000_000.0)
            return total if total >= 0 else None
        except (ValueError, TypeError):
            return None

    if not isinstance(val, str):
        val = str(val)

    s = val.strip()
    if not s:
        return None

    # Check if direct numeric string: "43.5" or "43"
    try:
        num = float(s)
        return num if num >= 0 else None
    except ValueError:
        pass

    # Check compound patterns like "18h24m10s", "1h 30m 10s", "45m", "15s"
    compound_pattern = re.compile(
        r"^(?:(?P<hours>\d+(?:\.\d+)?)\s*h(?:ours?|r)?)?"
        r"\s*(?:(?P<minutes>\d+(?:\.\d+)?)\s*m(?:in(?:ute)?s?)?)?"
        r"\s*(?:(?P<seconds>\d+(?:\.\d+)?)\s*s(?:ec(?:ond)?s?)?)?$",
        re.IGNORECASE
    )
    m = compound_pattern.match(s)
    if m and any(m.groups()):
        h = float(m.group("hours") or 0)
        mins = float(m.group("minutes") or 0)
        secs = float(m.group("seconds") or 0)
        total = h * 3600.0 + mins * 60.0 + secs
        if total >= 0 and any(m.group(k) is not None for k in ("hours", "minutes", "seconds")):
            return total

    # Check standalone single units like "43.518s" or "43.5 seconds"
    sec_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:s|sec|seconds?)", s, re.IGNORECASE)
    if sec_match:
        return float(sec_match.group(1))

    min_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:m|min|minutes?)", s, re.IGNORECASE)
    if min_match:
        return float(min_match.group(1)) * 60.0

    hr_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|hr|hours?)", s, re.IGNORECASE)
    if hr_match:
        return float(hr_match.group(1)) * 3600.0

    return None


PACIFIC_TZ = ZoneInfo("America/Los_Angeles")

def get_seconds_until_pacific_midnight(now: Optional[Union[float, datetime]] = None) -> float:
    """
    Calculates the exact duration in seconds from `now` until the next midnight (00:00:00)
    in the America/Los_Angeles time zone (Pacific Time), when Google Gemini daily quotas reset.
    
    Correctly accounts for Pacific daylight-saving transitions (PST / PDT) via UTC timestamp differentials.
    
    Args:
        now: Optional float timestamp or datetime object. If None, current time is used.
        
    Returns:
        float: Seconds remaining until the next Pacific midnight (minimum 1.0s).
    """
    if now is None:
        now_dt = datetime.now(PACIFIC_TZ)
    elif isinstance(now, (int, float)):
        now_dt = datetime.fromtimestamp(float(now), tz=PACIFIC_TZ)
    elif isinstance(now, datetime):
        if now.tzinfo is None:
            now_dt = now.replace(tzinfo=PACIFIC_TZ)
        else:
            now_dt = now.astimezone(PACIFIC_TZ)
    else:
        now_dt = datetime.now(PACIFIC_TZ)

    next_day = now_dt.date() + timedelta(days=1)
    next_midnight = datetime.combine(next_day, dtime.min, tzinfo=PACIFIC_TZ)

    duration = next_midnight.timestamp() - now_dt.timestamp()
    return max(1.0, float(duration))


class GeminiModelManager:
    """
    Centralized, concurrency-safe Gemini AI Model Manager.
    
    Responsibilities:
    - Maintains primary and fallback model priority order from environment variables.
    - Executes AI model calls sequentially (never parallel).
    - Detects quota exhaustion (RPD vs RPM/TPM), 503 unavailability, 504 timeouts, 404 missing models.
    - Tracks unavailable models in an in-memory health registry with cooldowns.
    - Prevents repeated calls against models currently in cooldown.
    - Re-enables models after their cooldown expires.
    - Halts immediately on authentication/credential failures (401/403) or malformed requests (400).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._registry: Dict[str, ModelHealthRecord] = {}
        self._last_successful_model: Optional[str] = None

    def _get_or_create_record_locked(self, model_name: str) -> ModelHealthRecord:
        if model_name not in self._registry:
            self._registry[model_name] = ModelHealthRecord(model_name=model_name)
        return self._registry[model_name]

    def reset_registry(self) -> None:
        """Clears all health tracking records. Useful for testing."""
        with self._lock:
            self._registry.clear()
            self._last_successful_model = None

    def get_model_priority_list(self) -> List[str]:
        """Returns the configured model priority list (primary followed by fallbacks)."""
        settings = get_settings()
        return settings.model_priority_list

    def extract_retry_delay(self, error: Exception) -> Optional[int]:
        """
        Extracts suggested retry delay in seconds from Google's response details or message.
        Adds a 1-second safety buffer to account for network latency, fractional seconds, and clock skew.
        """
        # 1. Inspect structured details in response_json or direct details attribute
        details_list: List[Any] = []
        response_json = getattr(error, "response_json", None)
        if isinstance(response_json, dict):
            error_obj = response_json.get("error", {})
            if isinstance(error_obj, dict):
                details_list.extend(error_obj.get("details", []) or [])

        direct_details = getattr(error, "details", None)
        if isinstance(direct_details, list):
            details_list.extend(direct_details)

        for d in details_list:
            if isinstance(d, dict):
                delay_val = d.get("retryDelay") or d.get("retry_delay")
                if delay_val is not None:
                    parsed = parse_duration_value(delay_val)
                    if parsed is not None:
                        return int(parsed) + 1

        # 2. Inspect error string / message for explicit retryDelay: ...
        err_str = str(error)
        match_rd = re.search(r"retryDelay[\'\":\s]+([^\'\",\s\}]+)", err_str, re.IGNORECASE)
        if match_rd:
            parsed = parse_duration_value(match_rd.group(1))
            if parsed is not None:
                return int(parsed) + 1

        # 3. Inspect error string / message for "retry in ..." or "retry after ..."
        match_msg = re.search(r"retry\s+(?:in|after)\s+([0-9a-zA-Z\.\s]+?)(?:\.|$|\n|,)", err_str, re.IGNORECASE)
        if match_msg:
            parsed = parse_duration_value(match_msg.group(1))
            if parsed is not None:
                return int(parsed) + 1

        return None

    def classify_error(
        self,
        err: Exception,
        model_name: str,
        now: Optional[Union[float, datetime]] = None
    ) -> Tuple[str, bool, float, str, Optional[int]]:
        """
        Classifies an API exception from Google Gen AI SDK.
        
        Returns:
            (category, can_fallback, cooldown_seconds, reason_msg, retry_delay)
        """
        code = getattr(err, "code", None)
        err_str = str(err)
        response_json = getattr(err, "response_json", None) or {}
        error_obj = response_json.get("error", {}) if isinstance(response_json, dict) else {}
        error_message = error_obj.get("message", err_str)
        details = error_obj.get("details", []) if isinstance(error_obj, dict) else []
        retry_delay = self.extract_retry_delay(err)
        settings = get_settings()

        # 1. Authentication / Permission Error (401 / 403 / API_KEY_INVALID)
        # Auth applies to the entire API key; cannot fallback to other models.
        if code in (401, 403) or "API_KEY_INVALID" in err_str or "unauthenticated" in err_str.lower():
            return (
                "AUTH_ERROR",
                False,
                0.0,
                f"Authentication failed: Invalid or unauthorized API key.",
                None
            )

        # 2. Client-side Malformed Request (400 / INVALID_ARGUMENT)
        # Malformed input is not model-specific; do not switch models automatically.
        if code == 400 or "INVALID_ARGUMENT" in err_str:
            return (
                "INVALID_REQUEST",
                False,
                0.0,
                f"Malformed request or invalid arguments: {error_message}",
                None
            )

        # 3. Quota Exhaustion or Rate Limit (429 / RESOURCE_EXHAUSTED)
        if code == 429 or "RESOURCE_EXHAUSTED" in err_str:
            text_corpus = f"{error_message} {err_str} {details}".lower()

            is_daily = (
                "daily" in text_corpus
                or "per day" in text_corpus
                or "requests per day" in text_corpus
                or "requestsperday" in text_corpus
                or "generatecontentrequestsperday" in text_corpus
                or "rpd" in text_corpus
                or ("free tier" in text_corpus and "day" in text_corpus)
            )

            is_tpm = (
                not is_daily and (
                    "tokens per minute" in text_corpus
                    or "tokens/minute" in text_corpus
                    or "tokens/min" in text_corpus
                    or "tokensperminute" in text_corpus
                    or "generatecontenttokensperminute" in text_corpus
                    or "tpm" in text_corpus
                    or "token quota" in text_corpus
                    or "token limit" in text_corpus
                )
            )

            if is_daily:
                # Daily request quota exhausted (RPD)
                # Requirement 3: If Google provides retryDelay, always prioritize Google's supplied duration.
                # Requirement 1 & 2: When no retryDelay, calculate duration until next midnight in America/Los_Angeles using zoneinfo.
                if retry_delay is not None:
                    cd = float(retry_delay)
                    delay_info = f"Google suggested retry in {int(cd)}s."
                else:
                    cd = get_seconds_until_pacific_midnight(now)
                    delay_info = f"Cooldown until Pacific midnight reset ({int(cd)}s / {cd/3600:.1f}h)."

                return (
                    "QUOTA_EXHAUSTED_DAILY",
                    True,
                    cd,
                    f"Model '{model_name}' daily request quota exhausted (RPD). {delay_info}",
                    retry_delay
                )
            elif is_tpm:
                # Per-minute token rate limit (TPM)
                cd = float(retry_delay) if retry_delay is not None else settings.GEMINI_TPM_COOLDOWN_SECONDS
                delay_info = (
                    f"Google suggested retry in {int(cd)}s."
                    if retry_delay is not None
                    else f"Configured cooldown {int(cd)}s."
                )
                return (
                    "RATE_LIMIT_TPM",
                    True,
                    cd,
                    f"Model '{model_name}' token rate limit reached (TPM). {delay_info}",
                    retry_delay
                )
            else:
                # Per-minute request rate limit (RPM)
                cd = float(retry_delay) if retry_delay is not None else settings.GEMINI_RPM_COOLDOWN_SECONDS
                delay_info = (
                    f"Google suggested retry in {int(cd)}s."
                    if retry_delay is not None
                    else f"Configured cooldown {int(cd)}s."
                )
                return (
                    "RATE_LIMIT_RPM",
                    True,
                    cd,
                    f"Model '{model_name}' request rate limit reached (RPM). {delay_info}",
                    retry_delay
                )

        # 4. Model Unavailable / High Demand (503 / UNAVAILABLE)
        if code == 503 or "UNAVAILABLE" in err_str or "high demand" in err_str.lower():
            cd = float(retry_delay) if retry_delay else 60.0
            return (
                "MODEL_UNAVAILABLE",
                True,
                cd,
                f"Model '{model_name}' temporarily unavailable (503 High Demand).",
                retry_delay
            )

        # 5. Gateway Timeout (504 / DEADLINE_EXCEEDED / Timeout)
        if code == 504 or "DEADLINE_EXCEEDED" in err_str or "timeout" in err_str.lower() or isinstance(err, TimeoutError):
            return (
                "TIMEOUT",
                True,
                60.0,
                f"Model '{model_name}' request timed out (504).",
                None
            )

        # 6. Model Not Found / Unsupported (404 / NOT_FOUND)
        if code == 404 or "NOT_FOUND" in err_str:
            return (
                "MODEL_NOT_FOUND",
                True,
                86400.0,  # 24 hour cooldown; model not accessible in project
                f"Model '{model_name}' is not accessible under the current project/API key (404).",
                None
            )

        # 7. Transient socket / network errors
        is_conn_error = any(term in err_str.lower() for term in [
            "forcibly closed", "connection reset", "connection broken",
            "remoteprotocolerror", "readerror", "winerror 10054"
        ])
        if is_conn_error:
            return (
                "CONNECTION_ERROR",
                True,
                30.0,
                f"Transient connection error communicating with '{model_name}'.",
                None
            )

        # 8. Unclassified Google API Error
        return (
            "API_ERROR",
            True,
            60.0,
            f"Google API error ({code}): {error_message}",
            None
        )

    def execute_with_fallback(
        self,
        operation_name: str,
        call_fn: Callable[[str], Any]
    ) -> Tuple[Any, FallbackMetadata]:
        """
        Executes an AI call sequentially through configured model priority list.
        
        Args:
            operation_name: Name of operation (e.g. 'Text Analysis', 'Vision Analysis', 'URL Analysis')
            call_fn: Function accepting `model_name: str` and returning the parsed/validated result.
            
        Returns:
            (validated_result, FallbackMetadata)
        """
        settings = get_settings()
        if not settings.is_gemini_configured:
            raise GeminiConfigurationError(
                "Gemini API key is not configured. Please add GEMINI_API_KEY in backend/.env to enable live AI analysis."
            )

        priority_list = self.get_model_priority_list()
        if not priority_list:
            priority_list = ["gemini-3.5-flash-lite"]

        primary_model = priority_list[0]
        models_attempted: List[str] = []
        fallback_reasons: List[str] = []
        last_exception: Optional[Exception] = None
        last_category: Optional[str] = None
        now = time.time()

        for idx, candidate_model in enumerate(priority_list):
            current_time = time.time()
            with self._lock:
                rec = self._get_or_create_record_locked(candidate_model)
                is_avail = rec.is_currently_available(current_time)
                rem_cd = rec.remaining_cooldown_seconds(current_time)

            if not is_avail:
                logger.info(
                    f"[{operation_name}] Skipping candidate model '{candidate_model}' "
                    f"(in cooldown for {rem_cd}s: {rec.cooldown_reason})"
                )
                models_attempted.append(candidate_model)
                fallback_reasons.append(f"{candidate_model} in cooldown ({rec.cooldown_reason})")
                continue

            models_attempted.append(candidate_model)

            # Record attempt
            with self._lock:
                rec = self._get_or_create_record_locked(candidate_model)
                rec.total_requests += 1
                rec.last_used_at = time.time()

            logger.info(
                f"[{operation_name}] Executing using model '{candidate_model}' "
                f"(priority index {idx + 1}/{len(priority_list)})..."
            )

            # Up to 1 immediate retry for transient 503/timeout before switching models
            max_model_attempts = 1
            model_attempt = 0
            success = False
            result = None

            while model_attempt <= max_model_attempts:
                try:
                    result = call_fn(candidate_model)
                    success = True
                    break
                except Exception as exc:
                    category, can_fallback, cooldown_sec, reason_msg, retry_delay = self.classify_error(exc, candidate_model)
                    last_category = category
                    last_exception = exc

                    # If AuthError or InvalidRequest: STOP immediately (do NOT fallback)
                    if category == "AUTH_ERROR":
                        with self._lock:
                            rec = self._get_or_create_record_locked(candidate_model)
                            rec.total_failures += 1
                            rec.last_error_category = category
                            rec.last_error_message = reason_msg
                        logger.error(f"[{operation_name}] Critical Auth failure on '{candidate_model}': {reason_msg}")
                        raise GeminiAuthError(f"Invalid Gemini API key. Please verify your GEMINI_API_KEY in backend/.env.")

                    if category == "INVALID_REQUEST":
                        with self._lock:
                            rec = self._get_or_create_record_locked(candidate_model)
                            rec.total_failures += 1
                            rec.last_error_category = category
                            rec.last_error_message = reason_msg
                        logger.error(f"[{operation_name}] Malformed request error on '{candidate_model}': {reason_msg}")
                        raise GeminiError(f"AI analysis request failed: {reason_msg}")

                    # If temporary 503 or transient network error, retry once on this model
                    if category in ("MODEL_UNAVAILABLE", "CONNECTION_ERROR") and model_attempt < max_model_attempts:
                        wait = retry_delay if (retry_delay and retry_delay <= 3) else 1.5
                        logger.warning(f"[{operation_name}] Transient error on '{candidate_model}'. Retrying in {wait}s...")
                        time.sleep(wait)
                        model_attempt += 1
                        continue

                    # Otherwise, record failure on this model and mark cooldown
                    with self._lock:
                        rec = self._get_or_create_record_locked(candidate_model)
                        rec.total_failures += 1
                        rec.is_available = False
                        rec.cooldown_until = time.time() + cooldown_sec
                        rec.cooldown_duration_seconds = cooldown_sec
                        rec.cooldown_reason = reason_msg
                        rec.last_error_category = category
                        rec.last_error_message = reason_msg

                    fallback_reasons.append(f"{candidate_model}: {reason_msg}")
                    logger.warning(
                        f"[{operation_name}] Model '{candidate_model}' failed ({category}). "
                        f"Marked in cooldown for {int(cooldown_sec)}s. Error: {reason_msg}"
                    )
                    break

            if success and result is not None:
                # Record success
                with self._lock:
                    rec = self._get_or_create_record_locked(candidate_model)
                    rec.total_successes += 1
                    rec.is_available = True
                    rec.cooldown_until = None
                    rec.cooldown_reason = None
                    rec.last_success_at = time.time()
                    self._last_successful_model = candidate_model

                fallback_used = (candidate_model != primary_model)
                fallback_reason_str = "; ".join(fallback_reasons) if fallback_used else None

                if fallback_used:
                    logger.info(
                        f"[{operation_name}] Successful fallback to '{candidate_model}'. "
                        f"Reason: {fallback_reason_str}"
                    )

                meta = FallbackMetadata(
                    model_used=candidate_model,
                    fallback_used=fallback_used,
                    fallback_reason=fallback_reason_str,
                    models_attempted=models_attempted,
                    primary_model=primary_model
                )
                return result, meta

        # If we exited the loop without success, all models failed
        logger.error(
            f"[{operation_name}] All configured Gemini models ({', '.join(priority_list)}) "
            f"failed or are in cooldown. Attempted: {models_attempted}."
        )

        all_models_str = ", ".join(models_attempted) if models_attempted else ", ".join(priority_list)
        reasons_summary = "; ".join(fallback_reasons) if fallback_reasons else "All models in cooldown or unavailable."

        if last_category in ("QUOTA_EXHAUSTED_DAILY", "RATE_LIMIT_RPM", "RATE_LIMIT_TPM"):
            raise GeminiQuotaError(
                f"All configured Gemini models ({all_models_str}) exhausted quota or rate limits. {reasons_summary}"
            )
        elif last_category == "MODEL_UNAVAILABLE":
            raise GeminiUnavailableError(
                f"All configured Gemini models ({all_models_str}) are temporarily unavailable. {reasons_summary}"
            )
        elif last_category == "TIMEOUT":
            raise GeminiTimeoutError(
                f"All configured Gemini models ({all_models_str}) timed out. {reasons_summary}"
            )
        else:
            raise GeminiError(
                f"All configured Gemini models ({all_models_str}) failed. {reasons_summary}"
            )

    def get_registry_status(self) -> ModelHealthRegistryResponse:
        """Returns snapshot of model availability and health metrics for the status endpoint."""
        settings = get_settings()
        priority_list = settings.model_priority_list
        primary_model = settings.GEMINI_MODEL or "gemini-3.5-flash-lite"
        now = time.time()

        models_status: Dict[str, ModelStatusDetail] = {}

        with self._lock:
            # Ensure all priority models are tracked
            for m in priority_list:
                self._get_or_create_record_locked(m)

            for m, rec in self._registry.items():
                is_avail = rec.is_currently_available(now)
                rem_cd = rec.remaining_cooldown_seconds(now)

                last_used_iso = (
                    datetime.fromtimestamp(rec.last_used_at, timezone.utc).isoformat()
                    if rec.last_used_at else None
                )
                last_succ_iso = (
                    datetime.fromtimestamp(rec.last_success_at, timezone.utc).isoformat()
                    if rec.last_success_at else None
                )

                models_status[m] = ModelStatusDetail(
                    model_name=m,
                    is_available=is_avail,
                    cooldown_seconds_remaining=rem_cd,
                    cooldown_reason=rec.cooldown_reason,
                    last_error_category=rec.last_error_category,
                    total_requests=rec.total_requests,
                    total_successes=rec.total_successes,
                    total_failures=rec.total_failures,
                    last_used_at=last_used_iso,
                    last_success_at=last_succ_iso
                )

            # Determine current active model (first available in priority list)
            current_active = None
            for m in priority_list:
                rec = self._registry.get(m)
                if rec and rec.is_currently_available(now):
                    current_active = m
                    break

            return ModelHealthRegistryResponse(
                configured_primary_model=primary_model,
                configured_fallback_models=settings.fallback_models_list,
                model_priority=priority_list,
                current_active_model=current_active,
                last_successful_model=self._last_successful_model,
                models_status=models_status
            )


# Global singleton instance
_model_manager = GeminiModelManager()

def get_model_manager() -> GeminiModelManager:
    """Returns the global GeminiModelManager singleton."""
    return _model_manager
