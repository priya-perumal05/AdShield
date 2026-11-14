from fastapi import APIRouter
from app.models.schemas import HealthResponse
from app.utils.config import get_settings
from app.services.ocr_service import get_tesseract_details

router = APIRouter(prefix="/api", tags=["System"])

@router.get("/health", response_model=HealthResponse)
def get_health_status():
    """
    Health check endpoint reporting API operational status and subsystem availability
    including Gemini API, Safe Browsing API, and Tesseract OCR engine.
    """
    settings = get_settings()
    tess_details = get_tesseract_details()
    return HealthResponse(
        status="healthy",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        gemini_configured=settings.is_gemini_configured,
        gemini_model=settings.GEMINI_MODEL,
        safe_browsing_configured=settings.is_safe_browsing_configured,
        tesseract_available=tess_details["available"],
        tesseract_version=tess_details.get("version")
    )

