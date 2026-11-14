export type RiskCategory = 'Low' | 'Medium' | 'High' | 'Insufficient Data';

export type AssessmentStatus = 'COMPLETE' | 'PARTIAL' | 'INSUFFICIENT_DATA';

export type SeverityLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export interface SuspiciousIndicator {
  category: string;
  title: string;
  description: string;
  severity: SeverityLevel;
  source?: string;
  confidence?: number | null;
}

export interface RiskAssessment {
  risk_score?: number | null;
  risk_category: RiskCategory;
  risk_level?: string;
  assessment_status?: AssessmentStatus;
  checks_completed?: string[];
  checks_unavailable?: string[];
  summary?: string;
  indicators: SuspiciousIndicator[];
  explanation: string;
  recommendations: string[];
  disclaimer?: string;
}

export interface BackendHealth {
  status: string;
  service: string;
  version: string;
  gemini_configured: boolean;
  gemini_model: string;
  safe_browsing_configured: boolean;
  tesseract_available: boolean;
  timestamp: string;
}

export interface TextAnalysisRequest {
  text: string;
  source_context?: string;
}

export interface TextAnalysisFindings {
  detected_claims: string[];
  unrealistic_discounts: string[];
  fake_prize_indicators: string[];
  urgent_payment_requests?: string[];
  misleading_statements: string[];
  suspicious_product_offers?: string[];
  brand_impersonation?: string[];
  fake_investment_promises?: string[];
  phishing_language?: string[];
  sensitive_info_requests?: string[];
  manipulative_techniques?: string[];
  urgency_cues: string[];
  suspicious_patterns: string[];
}

export interface TextAnalysisResponse {
  id: string;
  timestamp: string;
  submitted_text_preview: string;
  risk_score?: number | null;
  risk_category?: RiskCategory;
  risk_level?: string;
  assessment_status?: AssessmentStatus;
  checks_completed?: string[];
  checks_unavailable?: string[];
  summary?: string;
  indicators?: SuspiciousIndicator[];
  explanation?: string;
  recommendations?: string[];
  risk_assessment: RiskAssessment;
  findings: TextAnalysisFindings;
  gemini_used: boolean;
  model_used?: string;
  fallback_used?: boolean;
  fallback_reason?: string | null;
  models_attempted?: string[];
  primary_model?: string | null;
  ai_status?: string;
  ai_error_message?: string | null;
}

export interface ImageAnalysisDetail {
  summary: string;
  visual_observations: string[];
  suspicious_indicators: string[];
}

export interface ImageAnalysisFindings {
  extracted_text?: string | null;
  ocr_word_count: number;
  ocr_confidence?: number | null;
  visual_description?: string | null;
  visual_observations?: string[];
  suspicious_elements: string[];
  ocr_vision_alignment?: string | null;
}

export interface ImageAnalysisResponse {
  id: string;
  timestamp: string;
  filename: string;
  content_type: string;
  file_size_kb: number;
  risk_score?: number | null;
  risk_category?: RiskCategory;
  risk_level?: string;
  assessment_status?: AssessmentStatus;
  checks_completed?: string[];
  checks_unavailable?: string[];
  summary?: string;
  extracted_text?: string | null;
  ocr_status?: string; // SUCCESS, NO_TEXT_DETECTED, UNAVAILABLE, FAILED
  ocr_confidence?: number | null;
  image_analysis?: ImageAnalysisDetail;
  indicators?: SuspiciousIndicator[];
  explanation?: string;
  recommendations?: string[];
  risk_assessment: RiskAssessment;
  findings: ImageAnalysisFindings;
  gemini_used?: boolean;
  gemini_vision_used: boolean;
  ocr_used: boolean;
  model_used?: string;
  fallback_used?: boolean;
  fallback_reason?: string | null;
  models_attempted?: string[];
  primary_model?: string | null;
  ai_status?: string;
  ai_error_message?: string | null;
}

export interface UrlAnalysisDetail {
  summary: string;
  is_lookalike_domain: boolean;
  is_brand_impersonation: boolean;
  is_phishing_login: boolean;
  is_suspicious_shortener: boolean;
  detected_brand?: string | null;
  suspicious_patterns: string[];
  ad_url_consistency?: string | null;
}

export interface UrlAnalysisRequest {
  url: string;
  ad_text?: string;
  source_context?: string;
}

export interface UrlAnalysisFindings {
  submitted_url: string;
  normalized_url: string;
  domain: string;
  scheme: string;
  port?: number | null;
  has_valid_format: boolean;
  is_ip_address?: boolean;
  is_punycode?: boolean;
  decoded_punycode?: string | null;
  is_url_shortener?: boolean;
  has_suspicious_tld?: boolean;
  subdomain_count?: number;
  safe_browsing_checked: boolean;
  safe_browsing_status?: string; // MATCH_FOUND | NO_THREAT_FOUND | UNAVAILABLE | UNCONFIGURED
  safe_browsing_verdict?: string | null;
  threat_types: string[];
  heuristic_flags: string[];
  cache_hit?: boolean;
}

export interface UrlAnalysisResponse {
  id: string;
  timestamp: string;
  submitted_url: string;
  validated_domain: string;
  url_validation_status?: string;
  safe_browsing_status?: string;
  threat_types: string[];
  risk_score?: number | null;
  risk_category?: RiskCategory;
  risk_level?: string;
  assessment_status?: AssessmentStatus;
  checks_completed?: string[];
  checks_unavailable?: string[];
  summary?: string;
  indicators?: SuspiciousIndicator[];
  url_analysis?: UrlAnalysisDetail | null;
  explanation?: string;
  recommendations?: string[];
  risk_assessment: RiskAssessment;
  findings: UrlAnalysisFindings;
  api_verified: boolean;
  gemini_used?: boolean;
  model_used?: string | null;
  fallback_used?: boolean;
  fallback_reason?: string | null;
  models_attempted?: string[];
  primary_model?: string | null;
  ai_status?: string;
  ai_error_message?: string | null;
}

export type AnalysisResultUnion = 
  | { type: 'text'; data: TextAnalysisResponse }
  | { type: 'image'; data: ImageAnalysisResponse; imagePreviewUrl?: string }
  | { type: 'url'; data: UrlAnalysisResponse };

export interface SessionHistoryEntry {
  id: string;
  type: 'text' | 'image' | 'url';
  title: string;
  timestamp: string;
  riskScore?: number | null;
  riskCategory: RiskCategory;
  result: AnalysisResultUnion;
}

export interface ModelStatusDetail {
  model_name: string;
  is_available: boolean;
  cooldown_seconds_remaining: number;
  cooldown_reason?: string | null;
  last_error_category?: string | null;
  total_requests: number;
  total_successes: number;
  total_failures: number;
  last_used_at?: string | null;
  last_success_at?: string | null;
}

export interface ModelHealthRegistryResponse {
  configured_primary_model: string;
  configured_fallback_models: string[];
  model_priority: string[];
  current_active_model?: string | null;
  last_successful_model?: string | null;
  models_status: Record<string, ModelStatusDetail>;
}
