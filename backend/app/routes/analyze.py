import uuid
import logging
import io
from typing import Optional
from PIL import Image
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from app.models.schemas import (
    TextAnalysisRequest,
    TextAnalysisResponse,
    ImageAnalysisResponse,
    ImageAnalysisFindings,
    UrlAnalysisRequest,
    UrlAnalysisResponse,
    UrlAnalysisFindings,
    UrlAnalysisDetail,
    RiskAssessment,
    SuspiciousIndicator
)
from app.utils.config import get_settings
from app.services.gemini_service import (
    analyze_text_with_gemini,
    analyze_image_with_gemini,
    analyze_url_with_gemini,
    GeminiConfigurationError,
    GeminiAuthError,
    GeminiQuotaError,
    GeminiUnavailableError,
    GeminiTimeoutError,
    GeminiResponseError,
    GeminiError
)
from app.services.ocr_service import extract_text_from_image, is_tesseract_available
from app.services.safebrowsing_service import (
    validate_and_normalize_url,
    analyze_url_heuristics,
    check_safe_browsing
)
from app.services.risk_engine import (
    evaluate_text_risk,
    evaluate_url_risk,
    evaluate_image_risk,
    score_to_category
)

logger = logging.getLogger("adshield.api")

router = APIRouter(prefix="/api/analyze", tags=["Analysis"])

@router.post("/text", response_model=TextAnalysisResponse)
async def analyze_text(request: TextAnalysisRequest):
    """
    Analyzes advertisement copy using Google Gemini AI and cybersecurity rule heuristics.
    Detects 10 major threat vectors including unrealistic discounts, urgent payment demands,
    brand impersonation, fake prize lures, and sensitive information harvesting.
    """
    cleaned_text = request.text.strip()
    if len(cleaned_text) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Advertisement text is too short. Please provide at least 5 characters of content to analyze."
        )

    if len(cleaned_text) > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Advertisement text exceeds the maximum allowed length of 10,000 characters."
        )

    try:
        raw_ai_result, ai_meta = analyze_text_with_gemini(cleaned_text, request.source_context)
        model_used = getattr(ai_meta, "model_used", str(ai_meta))
        fallback_used = getattr(ai_meta, "fallback_used", False)
        fallback_reason = getattr(ai_meta, "fallback_reason", None)
        models_attempted = getattr(ai_meta, "models_attempted", [model_used] if model_used else [])
        primary_model = getattr(ai_meta, "primary_model", model_used)
    except GeminiConfigurationError as ce:
        logger.warning(f"Configuration error: {ce}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(ce)
        )
    except GeminiAuthError as ae:
        logger.error(f"Authentication error: {ae}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(ae)
        )
    except GeminiQuotaError as qe:
        logger.warning(f"Quota error: {qe}")
        headers = {}
        if getattr(qe, "retry_delay", None):
            headers["Retry-After"] = str(qe.retry_delay)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(qe),
            headers=headers
        )
    except GeminiUnavailableError as ue:
        logger.warning(f"Model unavailable error: {ue}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(ue)
        )
    except GeminiTimeoutError as te:
        logger.error(f"Timeout error: {te}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(te)
        )
    except GeminiResponseError as re:
        logger.error(f"Response error: {re}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(re)
        )
    except GeminiError as ge:
        logger.error(f"Gemini error: {ge}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI text analysis failed: {str(ge)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in analyze_text: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="An error occurred while communicating with the AI service. Please try again."
        )

    # Evaluate combined risk using the risk engine
    risk_assessment, findings = evaluate_text_risk(
        text=cleaned_text,
        ai_result=raw_ai_result,
        source_context=request.source_context
    )

    analysis_id = f"txt_{uuid.uuid4().hex[:12]}"
    preview = cleaned_text[:200] + ("..." if len(cleaned_text) > 200 else "")

    return TextAnalysisResponse(
        id=analysis_id,
        submitted_text_preview=preview,
        risk_score=risk_assessment.risk_score,
        risk_category=risk_assessment.risk_category,
        risk_level=risk_assessment.risk_level or risk_assessment.risk_category.value.upper(),
        assessment_status=risk_assessment.status,
        checks_completed=risk_assessment.checks_completed,
        checks_unavailable=risk_assessment.checks_unavailable,
        summary=risk_assessment.summary or raw_ai_result.summary,
        indicators=risk_assessment.indicators,
        explanation=risk_assessment.explanation,
        recommendations=risk_assessment.recommendations,
        risk_assessment=risk_assessment,
        findings=findings,
        gemini_used=True,
        model_used=model_used,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        models_attempted=models_attempted,
        primary_model=primary_model
    )

@router.post("/image", response_model=ImageAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    source_context: Optional[str] = Form(None)
):
    """
    Analyzes an uploaded advertisement image (JPG, JPEG, PNG, WEBP) using
    Tesseract OCR for text extraction and Gemini Vision for deep visual inspection.
    """
    settings = get_settings()

    content_type = (file.content_type or "").lower().strip()
    if content_type not in [t.lower() for t in settings.ALLOWED_IMAGE_TYPES]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{file.content_type}'. Allowed types: JPG, JPEG, PNG, WEBP."
        )

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded image file is empty."
        )

    if len(image_bytes) > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {int(settings.MAX_FILE_SIZE_BYTES / (1024*1024))} MB."
        )

    # Validate image file integrity with Pillow
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.verify()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file appears to be corrupted or is not a valid image format."
        )

    # Normalize mime type for Gemini Part
    mime_type = "image/jpeg" if content_type in ["image/jpg", "image/jpeg"] else content_type

    # 1. Perform Tesseract OCR extraction
    ocr_result = extract_text_from_image(image_bytes)
    extracted_text = ocr_result.get("text")
    ocr_status_val = ocr_result.get("status", "FAILED")
    ocr_confidence = ocr_result.get("confidence")
    ocr_used = ocr_status_val == "SUCCESS"

    # 2. Perform Gemini Vision analysis
    try:
        raw_ai_result, ai_meta = analyze_image_with_gemini(
            image_bytes=image_bytes,
            mime_type=mime_type,
            ocr_text=extracted_text,
            source_context=source_context
        )
        model_used = getattr(ai_meta, "model_used", str(ai_meta))
        fallback_used = getattr(ai_meta, "fallback_used", False)
        fallback_reason = getattr(ai_meta, "fallback_reason", None)
        models_attempted = getattr(ai_meta, "models_attempted", [model_used] if model_used else [])
        primary_model = getattr(ai_meta, "primary_model", model_used)
    except GeminiConfigurationError as ce:
        logger.warning(f"Configuration error: {ce}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(ce)
        )
    except GeminiAuthError as ae:
        logger.error(f"Authentication error: {ae}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(ae)
        )
    except GeminiQuotaError as qe:
        logger.warning(f"Quota error: {qe}")
        headers = {}
        if getattr(qe, "retry_delay", None):
            headers["Retry-After"] = str(qe.retry_delay)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(qe),
            headers=headers
        )
    except GeminiUnavailableError as ue:
        logger.warning(f"Model unavailable error: {ue}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(ue)
        )
    except GeminiTimeoutError as te:
        logger.error(f"Timeout error: {te}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(te)
        )
    except GeminiResponseError as re:
        logger.error(f"Response error: {re}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(re)
        )
    except GeminiError as ge:
        logger.error(f"Gemini error: {ge}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI image analysis failed: {str(ge)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in analyze_image: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="An error occurred while communicating with the AI service. Please try again."
        )

    # 3. Combine OCR text heuristics with Gemini Vision analysis
    risk_assessment, findings, image_detail = evaluate_image_risk(
        ocr_text=extracted_text,
        ocr_confidence=ocr_confidence,
        ocr_status=ocr_status_val,
        ai_result=raw_ai_result,
        source_context=source_context
    )

    analysis_id = f"img_{uuid.uuid4().hex[:12]}"
    file_size_kb = round(len(image_bytes) / 1024, 2)

    return ImageAnalysisResponse(
        id=analysis_id,
        filename=file.filename or "uploaded_ad_image",
        content_type=mime_type,
        file_size_kb=file_size_kb,
        risk_score=risk_assessment.risk_score,
        risk_category=risk_assessment.risk_category,
        risk_level=risk_assessment.risk_level or risk_assessment.risk_category.value.upper(),
        assessment_status=risk_assessment.status,
        checks_completed=risk_assessment.checks_completed,
        checks_unavailable=risk_assessment.checks_unavailable,
        summary=risk_assessment.summary or raw_ai_result.summary,
        extracted_text=extracted_text,
        ocr_status=ocr_status_val,
        ocr_confidence=ocr_confidence,
        image_analysis=image_detail,
        indicators=risk_assessment.indicators,
        explanation=risk_assessment.explanation,
        recommendations=risk_assessment.recommendations,
        risk_assessment=risk_assessment,
        findings=findings,
        gemini_used=True,
        gemini_vision_used=True,
        ocr_used=ocr_used,
        model_used=model_used,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        models_attempted=models_attempted,
        primary_model=primary_model
    )

@router.post("/url", response_model=UrlAnalysisResponse)
async def analyze_url(request: UrlAnalysisRequest):
    """
    Analyzes advertisement landing destination URLs for security threats,
    phishing patterns, brand impersonation, and queries Google Safe Browsing API v5.
    """
    settings = get_settings()

    # 1. URL validation, SSRF protection, IDNA/Punycode, and normalization
    normalized = validate_and_normalize_url(request.url)
    if not normalized.get("valid"):
        err_msg = normalized.get("error") or "Invalid URL format. Please provide a valid web address with a domain name."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg
        )

    # 2. Heuristic structural & lexical pattern detection
    heuristic_flags = analyze_url_heuristics(normalized)

    # 3. Google Safe Browsing API v5 threat intelligence lookup
    sb_result = await check_safe_browsing(normalized["normalized_url"])

    # 4. Gemini AI contextual URL & phishing analysis (if configured)
    raw_ai_result = None
    model_used = None
    fallback_used = False
    fallback_reason = None
    models_attempted: List[str] = []
    primary_model = None
    gemini_used = False
    ai_status = "SUCCESS"
    ai_error_message: Optional[str] = None

    if settings.is_gemini_configured:
        try:
            raw_ai_result, ai_meta = analyze_url_with_gemini(
                url=normalized["normalized_url"],
                heuristic_flags=heuristic_flags,
                ad_text=request.ad_text,
                source_context=request.source_context
            )
            gemini_used = True
            model_used = getattr(ai_meta, "model_used", str(ai_meta))
            fallback_used = getattr(ai_meta, "fallback_used", False)
            fallback_reason = getattr(ai_meta, "fallback_reason", None)
            models_attempted = getattr(ai_meta, "models_attempted", [model_used] if model_used else [])
            primary_model = getattr(ai_meta, "primary_model", model_used)
            ai_status = "SUCCESS"
        except GeminiQuotaError as qe:
            logger.warning(f"Gemini quota exhausted during URL analysis: {qe}")
            gemini_used = False
            ai_status = "QUOTA_EXHAUSTED"
            ai_error_message = "Gemini AI daily request quota has been exhausted. Proceeding with Safe Browsing and heuristic verification."
        except GeminiAuthError as ae:
            logger.warning(f"Gemini authentication failed during URL analysis: {ae}")
            gemini_used = False
            ai_status = "AUTH_ERROR"
            ai_error_message = "Gemini AI authentication failed. Proceeding with Safe Browsing and heuristic verification."
        except GeminiUnavailableError as ue:
            logger.warning(f"Gemini model unavailable during URL analysis: {ue}")
            gemini_used = False
            ai_status = "UNAVAILABLE"
            ai_error_message = "Gemini AI model is temporarily unavailable. Proceeding with Safe Browsing and heuristic verification."
        except GeminiTimeoutError as te:
            logger.warning(f"Gemini timed out during URL analysis: {te}")
            gemini_used = False
            ai_status = "TIMEOUT"
            ai_error_message = "Gemini AI analysis timed out. Proceeding with Safe Browsing and heuristic verification."
        except (GeminiConfigurationError, GeminiResponseError, GeminiError) as ge:
            logger.warning(f"Gemini error during URL analysis: {ge}")
            gemini_used = False
            ai_status = "FAILED"
            ai_error_message = f"Gemini AI contextual analysis unavailable ({type(ge).__name__}). Proceeding with Safe Browsing and heuristic verification."
        except Exception as e:
            logger.error(f"Unexpected error in Gemini URL analysis: {e}", exc_info=True)
            gemini_used = False
            ai_status = "FAILED"
            ai_error_message = "Unexpected error querying AI service. Proceeding with Safe Browsing and heuristic verification."
    else:
        gemini_used = False
        ai_status = "UNCONFIGURED"
        ai_error_message = "Gemini AI is not configured. Analysis evaluated using Safe Browsing and heuristic verification."

    # 5. Combined URL risk evaluation
    risk_assessment, url_detail = evaluate_url_risk(
        heuristic_flags=heuristic_flags,
        safe_browsing_result=sb_result,
        ai_result=raw_ai_result,
        url_info=normalized
    )

    findings = UrlAnalysisFindings(
        submitted_url=request.url,
        normalized_url=normalized["normalized_url"],
        domain=normalized["domain"],
        scheme=normalized["scheme"],
        port=normalized.get("port"),
        has_valid_format=True,
        is_ip_address=normalized.get("is_ip_address", False),
        is_punycode=normalized.get("is_punycode", False),
        decoded_punycode=normalized.get("decoded_punycode"),
        is_url_shortener=normalized.get("is_url_shortener", False),
        has_suspicious_tld=normalized.get("has_suspicious_tld", False),
        subdomain_count=normalized.get("subdomain_count", 0),
        safe_browsing_checked=sb_result.get("checked", False),
        safe_browsing_status=sb_result.get("status", "UNCONFIGURED"),
        safe_browsing_verdict=sb_result.get("message"),
        threat_types=sb_result.get("threat_types", []),
        heuristic_flags=heuristic_flags,
        cache_hit=sb_result.get("cache_hit", False)
    )

    analysis_id = f"url_{uuid.uuid4().hex[:12]}"

    return UrlAnalysisResponse(
        id=analysis_id,
        submitted_url=request.url,
        validated_domain=normalized["domain"],
        url_validation_status=normalized.get("status", "VALID"),
        safe_browsing_status=sb_result.get("status", "UNCONFIGURED"),
        threat_types=sb_result.get("threat_types", []),
        risk_score=risk_assessment.risk_score,
        risk_category=risk_assessment.risk_category,
        risk_level=risk_assessment.risk_level or risk_assessment.risk_category.value.upper(),
        assessment_status=risk_assessment.status,
        checks_completed=risk_assessment.checks_completed,
        checks_unavailable=risk_assessment.checks_unavailable,
        summary=risk_assessment.summary,
        indicators=risk_assessment.indicators,
        url_analysis=url_detail if gemini_used else None,
        explanation=risk_assessment.explanation,
        recommendations=risk_assessment.recommendations,
        risk_assessment=risk_assessment,
        findings=findings,
        api_verified=sb_result.get("checked", False),
        gemini_used=gemini_used,
        model_used=model_used if gemini_used else None,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        models_attempted=models_attempted,
        primary_model=primary_model,
        ai_status=ai_status,
        ai_error_message=ai_error_message
    )
