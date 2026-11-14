import os
from pathlib import Path
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE_CANDIDATES = [
    str(_BASE_DIR / ".env"),
    str(Path.cwd() / "backend" / ".env"),
    str(Path.cwd() / ".env"),
    ".env"
]
_ENV_PATH = next((p for p in _ENV_FILE_CANDIDATES if Path(p).exists()), ".env")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "AdShield Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS Origins (comma-separated or list)
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://localhost:4173"
    
    # Gemini Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_FALLBACK_MODELS: str = "gemini-3.1-flash-lite,gemini-2.5-flash-lite"
    GEMINI_DAILY_QUOTA_COOLDOWN_SECONDS: float = 3600.0
    GEMINI_RPM_COOLDOWN_SECONDS: float = 60.0
    GEMINI_TPM_COOLDOWN_SECONDS: float = 60.0
    
    # Google Safe Browsing API Configuration
    SAFE_BROWSING_API_KEY: str = ""
    SAFE_BROWSING_TIMEOUT_SECONDS: float = 6.0
    
    # Tesseract OCR executable path (if custom on Windows)
    TESSERACT_CMD: str = ""

    # Upload constraints
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/jpg", "image/png", "image/webp"]

    @property
    def fallback_models_list(self) -> List[str]:
        if not self.GEMINI_FALLBACK_MODELS:
            return []
        return [m.strip() for m in self.GEMINI_FALLBACK_MODELS.split(",") if m.strip()]

    @property
    def model_priority_list(self) -> List[str]:
        primary = (self.GEMINI_MODEL or "gemini-3.5-flash-lite").strip()
        models = [primary]
        for m in self.fallback_models_list:
            if m not in models:
                models.append(m)
        return models

    @property
    def cors_origin_list(self) -> List[str]:
        default_origins = [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
        ]
        if not self.CORS_ORIGINS or not self.CORS_ORIGINS.strip():
            return default_origins
        configured = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        # Merge configured origins with default development origins
        merged = list(default_origins)
        for orig in configured:
            if orig not in merged:
                merged.append(orig)
        return merged

    @property
    def is_gemini_configured(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip() and not self.GEMINI_API_KEY.startswith("your_"))

    @property
    def is_safe_browsing_configured(self) -> bool:
        return bool(self.SAFE_BROWSING_API_KEY and self.SAFE_BROWSING_API_KEY.strip() and not self.SAFE_BROWSING_API_KEY.startswith("your_"))

@lru_cache()
def get_settings() -> Settings:
    return Settings()
