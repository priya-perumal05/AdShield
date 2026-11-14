from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl

class AssessmentStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

class RiskCategory(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    INSUFFICIENT_DATA = "Insufficient Data"

class SuspiciousIndicator(BaseModel):
    category: str = Field(..., description="E.g., Pricing, Urgency, Brand, Phishing, Privacy, Manipulation")
    title: str = Field(..., description="Short title of the indicator")
    description: str = Field(..., description="Detailed explanation of the issue")
    severity: str = Field(..., description="LOW, MEDIUM, or HIGH")
    source: str = Field("Rule Heuristics", description="Detection source: Google Safe Browsing, Gemini AI, Tesseract OCR, Heuristic Rules, etc.")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0 (pattern alignment)")

class RiskAssessment(BaseModel):
    risk_score: Optional[int] = Field(None, ge=0, le=100, description="Risk score from 0 to 100, or None if insufficient data")
    risk_category: RiskCategory = Field(..., description="Low, Medium, High, or Insufficient Data")
    risk_level: Optional[str] = Field(None, description="Uppercase risk level: LOW, MEDIUM, HIGH, or INSUFFICIENT_DATA")
    status: AssessmentStatus = Field(AssessmentStatus.COMPLETE, description="Assessment completion status: COMPLETE, PARTIAL, INSUFFICIENT_DATA")
    checks_completed: List[str] = Field(default_factory=list, description="Security checks successfully performed")
    checks_unavailable: List[str] = Field(default_factory=list, description="Services or checks that could not be executed")
    summary: Optional[str] = Field(None, description="Concise summary of findings")
    indicators: List[SuspiciousIndicator] = Field(default_factory=list)
    explanation: str = Field(..., description="AI or heuristic breakdown of the risk determination")
    recommendations: List[str] = Field(default_factory=list, description="Actionable safety guidance for users")
    disclaimer: str = Field(
        default="AdShield risk scores are AI-assisted estimates based on detected patterns and threat intelligence. They should be used for guidance, not definitive proof of fraud.",
        description="Legal/operational disclaimer"
    )

# --- Raw AI Structured Output Schema (Text) ---
class GeminiTextAnalysisRaw(BaseModel):
    summary: str = Field(..., description="High-level summary of the advertisement analysis")
    estimated_risk_score: int = Field(..., ge=0, le=100, description="Estimated risk score from 0 to 100")
    risk_level: str = Field(..., description="Risk tier: LOW, MEDIUM, or HIGH")
    explanation: str = Field(..., description="Detailed contextual reasoning explaining why this ad is safe or suspicious")
    detected_claims: List[str] = Field(default_factory=list, description="Primary claims or promises made in the ad")
    unrealistic_discounts: List[str] = Field(default_factory=list, description="Unrealistic prices, extreme discount claims (e.g. 95% off)")
    fake_prize_indicators: List[str] = Field(default_factory=list, description="Lottery, giveaway, or fake prize patterns")
    urgent_payment_requests: List[str] = Field(default_factory=list, description="Urgent fees, shipping charges for free items, crypto/wire transfer demands")
    misleading_statements: List[str] = Field(default_factory=list, description="Misleading, exaggerated, or unsubstantiated statements")
    suspicious_product_offers: List[str] = Field(default_factory=list, description="Counterfeit goods, miracle cures, or illegal/prohibited products")
    brand_impersonation: List[str] = Field(default_factory=list, description="Impersonation or unauthorized spoofing of recognized brands or companies")
    fake_investment_promises: List[str] = Field(default_factory=list, description="Guaranteed returns, crypto doubling schemes, or get-rich-quick claims")
    phishing_language: List[str] = Field(default_factory=list, description="Social engineering, fake security warnings, or account suspension alerts")
    sensitive_info_requests: List[str] = Field(default_factory=list, description="Solicitations for passwords, PINs, SSNs, or payment credentials")
    manipulative_techniques: List[str] = Field(default_factory=list, description="Artificial scarcity, countdown timers, or emotional manipulation")
    recommended_actions: List[str] = Field(default_factory=list, description="Concrete safety actions for the consumer")

# --- Raw AI Structured Output Schema (Vision & Image) ---
class GeminiImageAnalysisRaw(BaseModel):
    summary: str = Field(..., description="High-level summary of the visual advertisement analysis")
    estimated_risk_score: int = Field(..., ge=0, le=100, description="Estimated risk score from 0 to 100")
    risk_level: str = Field(..., description="Risk tier: LOW, MEDIUM, or HIGH")
    visual_observations: List[str] = Field(default_factory=list, description="Objective visual observations of elements, layout, badges, imagery")
    detected_claims: List[str] = Field(default_factory=list, description="Promotional claims and product pricing visible in image")
    unrealistic_discounts: List[str] = Field(default_factory=list, description="Suspicious or improbable discounts depicted")
    fake_prize_indicators: List[str] = Field(default_factory=list, description="Fake prize, giveaway, or lottery graphics")
    urgent_payment_requests: List[str] = Field(default_factory=list, description="Urgent fees, crypto/wire transfer payment prompts")
    suspicious_payment_instructions: List[str] = Field(default_factory=list, description="Non-standard or suspicious banking/payment instructions")
    brand_impersonation: List[str] = Field(default_factory=list, description="Imitation or unauthorized use of known brands")
    misleading_representations: List[str] = Field(default_factory=list, description="Misleading product depictions or fake endorsements")
    suspicious_contact_details: List[str] = Field(default_factory=list, description="Suspicious emails, phone numbers, or QR codes")
    visual_inconsistencies: List[str] = Field(default_factory=list, description="Inconsistencies between claims and depicted visuals")
    sensitive_info_requests: List[str] = Field(default_factory=list, description="Visual solicitations for passwords, PINs, SSNs, cards")
    phishing_indicators: List[str] = Field(default_factory=list, description="Deceptive UI elements (fake close buttons, play buttons, fake login screens)")
    explanation: str = Field(..., description="Detailed AI explanation of visual and textual findings")
    recommendations: List[str] = Field(default_factory=list, description="Concrete safety actions for the consumer")

# --- Raw AI Structured Output Schema (URL & Phishing) ---
class GeminiUrlAnalysisRaw(BaseModel):
    summary: str = Field(..., description="High-level summary of the URL and domain security evaluation")
    estimated_risk_score: int = Field(..., ge=0, le=100, description="Estimated risk score from 0 to 100")
    risk_level: str = Field(..., description="Risk tier: LOW, MEDIUM, or HIGH")
    detected_brand: Optional[str] = Field(None, description="Identified brand targeted or impersonated, if any")
    is_brand_impersonation: bool = Field(False, description="Whether the URL appears to impersonate a known brand")
    is_lookalike_domain: bool = Field(False, description="Whether the domain appears to be a typo-squatted or lookalike domain")
    is_phishing_login: bool = Field(False, description="Whether URL path indicates credential harvesting or fake login")
    is_suspicious_shortener: bool = Field(False, description="Whether URL utilizes an obscure or suspicious shortener")
    suspicious_patterns: List[str] = Field(default_factory=list, description="Suspicious patterns detected in domain, subdomain, path, or query")
    ad_url_consistency: str = Field(default="Consistent", description="Assessment of consistency between URL destination and ad content")
    explanation: str = Field(..., description="Detailed AI explanation of domain and URL indicators")
    recommendations: List[str] = Field(default_factory=list, description="Safety recommendations for the consumer")

# --- Health Check ---
class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "AdShield Detection API"
    version: str = "1.0.0"
    gemini_configured: bool
    gemini_model: str
    safe_browsing_configured: bool
    tesseract_available: bool
    tesseract_version: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# --- Text Analysis Schemas ---
class TextAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=10000, description="Advertisement text, headline, or message")
    source_context: Optional[str] = Field(None, max_length=200, description="Optional ad platform or context (e.g. Facebook, SMS, Email)")

class TextAnalysisFindings(BaseModel):
    detected_claims: List[str] = Field(default_factory=list)
    unrealistic_discounts: List[str] = Field(default_factory=list)
    fake_prize_indicators: List[str] = Field(default_factory=list)
    urgent_payment_requests: List[str] = Field(default_factory=list)
    misleading_statements: List[str] = Field(default_factory=list)
    suspicious_product_offers: List[str] = Field(default_factory=list)
    brand_impersonation: List[str] = Field(default_factory=list)
    fake_investment_promises: List[str] = Field(default_factory=list)
    phishing_language: List[str] = Field(default_factory=list)
    sensitive_info_requests: List[str] = Field(default_factory=list)
    manipulative_techniques: List[str] = Field(default_factory=list)
    urgency_cues: List[str] = Field(default_factory=list)
    suspicious_patterns: List[str] = Field(default_factory=list)

class TextAnalysisResponse(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    submitted_text_preview: str
    risk_score: Optional[int] = None
    risk_category: RiskCategory
    risk_level: str
    assessment_status: AssessmentStatus = AssessmentStatus.COMPLETE
    checks_completed: List[str] = Field(default_factory=list)
    checks_unavailable: List[str] = Field(default_factory=list)
    summary: str
    indicators: List[SuspiciousIndicator] = Field(default_factory=list)
    explanation: str
    recommendations: List[str] = Field(default_factory=list)
    risk_assessment: RiskAssessment
    findings: TextAnalysisFindings
    gemini_used: bool
    model_used: Optional[str] = None
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    models_attempted: List[str] = Field(default_factory=list)
    primary_model: Optional[str] = None

# --- Image Analysis Schemas ---
class ImageAnalysisDetail(BaseModel):
    summary: str = Field(default="", description="Visual advertisement analysis summary")
    visual_observations: List[str] = Field(default_factory=list, description="Visual observations of elements, layout, logos")
    suspicious_indicators: List[str] = Field(default_factory=list, description="Suspicious visual indicators detected")

class ImageAnalysisFindings(BaseModel):
    extracted_text: Optional[str] = None
    ocr_word_count: int = 0
    ocr_confidence: Optional[float] = None
    visual_description: Optional[str] = None
    visual_observations: List[str] = Field(default_factory=list)
    suspicious_elements: List[str] = Field(default_factory=list)
    ocr_vision_alignment: Optional[str] = None

class ImageAnalysisResponse(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    filename: str
    content_type: str
    file_size_kb: float
    risk_score: Optional[int] = None
    risk_category: RiskCategory
    risk_level: str
    assessment_status: AssessmentStatus = AssessmentStatus.COMPLETE
    checks_completed: List[str] = Field(default_factory=list)
    checks_unavailable: List[str] = Field(default_factory=list)
    summary: str
    extracted_text: Optional[str] = None
    ocr_status: str = "SUCCESS"  # SUCCESS, NO_TEXT_DETECTED, UNAVAILABLE, FAILED
    ocr_confidence: Optional[float] = None
    image_analysis: ImageAnalysisDetail
    indicators: List[SuspiciousIndicator] = Field(default_factory=list)
    explanation: str
    recommendations: List[str] = Field(default_factory=list)
    risk_assessment: RiskAssessment
    findings: ImageAnalysisFindings
    gemini_used: bool = True
    gemini_vision_used: bool = True
    ocr_used: bool = False
    model_used: Optional[str] = None
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    models_attempted: List[str] = Field(default_factory=list)
    primary_model: Optional[str] = None

# --- URL Analysis Schemas ---
class UrlAnalysisDetail(BaseModel):
    summary: str = Field(default="", description="High-level summary of URL analysis")
    is_lookalike_domain: bool = False
    is_brand_impersonation: bool = False
    is_phishing_login: bool = False
    is_suspicious_shortener: bool = False
    detected_brand: Optional[str] = None
    suspicious_patterns: List[str] = Field(default_factory=list)
    ad_url_consistency: Optional[str] = None

class UrlAnalysisRequest(BaseModel):
    url: str = Field(..., min_length=3, max_length=2048, description="Target advertisement destination URL")
    ad_text: Optional[str] = Field(None, max_length=10000, description="Optional advertisement text or copy associated with the URL")
    source_context: Optional[str] = Field(None, max_length=200, description="Optional platform or delivery channel (e.g. Email, Social Media, SMS)")

class UrlAnalysisFindings(BaseModel):
    submitted_url: str
    normalized_url: str
    domain: str
    scheme: str
    port: Optional[int] = None
    has_valid_format: bool
    is_ip_address: bool = False
    is_punycode: bool = False
    decoded_punycode: Optional[str] = None
    is_url_shortener: bool = False
    has_suspicious_tld: bool = False
    subdomain_count: int = 0
    safe_browsing_checked: bool
    safe_browsing_status: str = "UNCONFIGURED"  # MATCH_FOUND, NO_THREAT_FOUND, UNAVAILABLE, UNCONFIGURED
    safe_browsing_verdict: Optional[str] = None
    threat_types: List[str] = Field(default_factory=list)
    heuristic_flags: List[str] = Field(default_factory=list)
    cache_hit: bool = False

class UrlAnalysisResponse(BaseModel):
    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    submitted_url: str
    validated_domain: str
    url_validation_status: str = "VALID"  # VALID, INVALID_FORMAT, REJECTED_PRIVATE_IP
    safe_browsing_status: str = "UNCONFIGURED"  # MATCH_FOUND, NO_THREAT_FOUND, UNAVAILABLE, UNCONFIGURED
    threat_types: List[str] = Field(default_factory=list)
    risk_score: Optional[int] = None
    risk_category: RiskCategory
    risk_level: str
    assessment_status: AssessmentStatus = AssessmentStatus.COMPLETE
    checks_completed: List[str] = Field(default_factory=list)
    checks_unavailable: List[str] = Field(default_factory=list)
    summary: str
    indicators: List[SuspiciousIndicator] = Field(default_factory=list)
    url_analysis: Optional[UrlAnalysisDetail] = None
    explanation: str
    recommendations: List[str] = Field(default_factory=list)
    risk_assessment: RiskAssessment
    findings: UrlAnalysisFindings
    api_verified: bool = False
    gemini_used: bool = False
    model_used: Optional[str] = None
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    models_attempted: List[str] = Field(default_factory=list)
    primary_model: Optional[str] = None
    ai_status: str = "SUCCESS"  # SUCCESS, QUOTA_EXHAUSTED, AUTH_ERROR, UNAVAILABLE, TIMEOUT, UNCONFIGURED, FAILED
    ai_error_message: Optional[str] = None

# --- AI Model Fallback & Status Monitoring Schemas ---
class ModelStatusDetail(BaseModel):
    model_name: str
    is_available: bool = True
    cooldown_seconds_remaining: int = 0
    cooldown_reason: Optional[str] = None
    last_error_category: Optional[str] = None
    total_requests: int = 0
    total_successes: int = 0
    total_failures: int = 0
    last_used_at: Optional[str] = None
    last_success_at: Optional[str] = None

class ModelHealthRegistryResponse(BaseModel):
    configured_primary_model: str
    configured_fallback_models: List[str]
    model_priority: List[str]
    current_active_model: Optional[str]
    last_successful_model: Optional[str]
    models_status: Dict[str, ModelStatusDetail]
