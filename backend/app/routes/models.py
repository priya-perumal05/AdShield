from fastapi import APIRouter
from app.models.schemas import ModelHealthRegistryResponse
from app.services.gemini_model_manager import get_model_manager

router = APIRouter(prefix="/api/ai", tags=["AI Infrastructure"])

@router.get("/models/status", response_model=ModelHealthRegistryResponse)
def get_ai_models_status():
    """
    Returns the real-time operational status, priority list, and cooldown metrics
    of all configured Gemini AI models in the centralized health registry.
    """
    manager = get_model_manager()
    return manager.get_registry_status()

