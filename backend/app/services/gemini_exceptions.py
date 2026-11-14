from typing import Optional

class GeminiError(Exception):
    """Base exception for Gemini service errors."""
    pass

class GeminiConfigurationError(GeminiError):
    """Raised when the Gemini API key is missing or unconfigured."""
    pass

class GeminiAuthError(GeminiError):
    """Raised when the Gemini API key is rejected (401/403)."""
    pass

class GeminiQuotaError(GeminiError):
    """Raised when Gemini API quota or rate limits are exhausted (429)."""
    def __init__(self, message: str, retry_delay: Optional[int] = None):
        super().__init__(message)
        self.retry_delay = retry_delay

class GeminiUnavailableError(GeminiError):
    """Raised when the Gemini model is experiencing temporary high demand or downtime (503)."""
    pass

class GeminiTimeoutError(GeminiError):
    """Raised when a request to Gemini times out."""
    pass

class GeminiResponseError(GeminiError):
    """Raised when Gemini returns an empty, unparseable, or schema-invalid response."""
    pass

