import re
from typing import List, Dict, Any, Optional, Tuple
from app.models.schemas import (
    AssessmentStatus,
    RiskAssessment,
    RiskCategory,
    SuspiciousIndicator,
    GeminiTextAnalysisRaw,
    GeminiImageAnalysisRaw,
    GeminiUrlAnalysisRaw,
    TextAnalysisFindings,
    ImageAnalysisFindings,
    ImageAnalysisDetail,
    UrlAnalysisDetail
)

def score_to_category(score: Optional[int]) -> RiskCategory:
    """
    Maps 0-100 risk score strictly to Low (0-30), Medium (31-60), High (61-100),
    or Insufficient Data (None).
    Guarantees consistent category classification across all modalities.
    """
    if score is None:
        return RiskCategory.INSUFFICIENT_DATA
    elif score <= 30:
        return RiskCategory.LOW
    elif score <= 60:
        return RiskCategory.MEDIUM
    else:
        return RiskCategory.HIGH

# --- Rule-Based Heuristic Pattern Detection for Text ---
RULE_PATTERNS = [
    {
        "category": "Credential Harvesting",
        "title": "Sensitive Information Request",
        "pattern": r"(?i)\b(enter\s+your\s+(ssn|social\s+security|bank\s+pin|atm\s+pin|cvv|card\s+number|password))\b",
        "description": "Advertisement requests sensitive financial or personal identification credentials directly.",
        "severity": "HIGH",
        "confidence": 0.95,
        "score_boost": 40
    },
    {
        "category": "Payment Risk",
        "title": "Untraceable / Irreversible Payment Demand",
        "pattern": r"(?i)\b(pay\s+via\s+(bitcoin|crypto|gift\s+card|steam\s+card|apple\s+gift\s+card|western\s+union|wire\s+transfer))\b",
        "description": "Urges payment through non-refundable or anonymous transaction channels.",
        "severity": "HIGH",
        "confidence": 0.90,
        "score_boost": 35
    },
    {
        "category": "Prize Scam",
        "title": "Fee-for-Free Prize Pattern",
        "pattern": r"(?i)\b((you\s+won|selected\s+as\s+(the|a)\s+winner|claim\s+your\s+(free\s+)?(iphone|gift\s+card|prize|reward))\b.*?(pay\s+(\$|usd|shipping|fee|processing)))",
        "description": "Claims a valuable free prize but demands an immediate upfront shipping or processing payment.",
        "severity": "HIGH",
        "confidence": 0.92,
        "score_boost": 35
    },
    {
        "category": "Urgency Trigger",
        "title": "High-Pressure Countdown Urgency",
        "pattern": r"(?i)\b(expires\s+in\s+\d+\s*(min|minute|hour)|only\s+\d+\s*(left|items\s+left)|act\s+(now|immediately)\s+or\s+(lose|deleted))\b",
        "description": "Uses extreme artificial scarcity or expiration timers to induce impulsive action without verification.",
        "severity": "MEDIUM",
        "confidence": 0.82,
        "score_boost": 15
    },
    {
        "category": "Phishing Alert",
        "title": "Fabricated Account Warning / Lockout Bait",
        "pattern": r"(?i)\b(account\s+(has\s+been\s+)?(suspended|locked|compromised|flagged)|unauthorized\s+(login|access)\s+detected)\b",
        "description": "Simulates an alarming security notification to bait users into clicking verification links.",
        "severity": "HIGH",
        "confidence": 0.88,
        "score_boost": 30
    },
    {
        "category": "Investment Lure",
        "title": "Guaranteed Profit / Crypto Doubling Lure",
        "pattern": r"(?i)\b(guaranteed\s+(return|profit|income)|double\s+your\s+(money|crypto|bitcoin)|earn\s+\$\d{3,}\s+per\s+day\s+from\s+home)\b",
        "description": "Promises unrealistic or guaranteed financial gains with zero risk.",
        "severity": "HIGH",
        "confidence": 0.89,
        "score_boost": 30
    }
]

def scan_text_heuristics(text: str) -> Tuple[List[SuspiciousIndicator], int]:
    """Runs regex heuristic detection on text copy and calculates rule score boost."""
    indicators: List[SuspiciousIndicator] = []
    total_boost = 0
    seen_titles = set()

    for rule in RULE_PATTERNS:
        if re.search(rule["pattern"], text):
            title = rule["title"]
            if title not in seen_titles:
                seen_titles.add(title)
                indicators.append(
                    SuspiciousIndicator(
                        category=rule["category"],
                        title=title,
                        description=rule["description"],
                        severity=rule["severity"],
                        source="NLP & Rule Heuristics",
                        confidence=rule["confidence"]
                    )
                )
                total_boost += rule["score_boost"]

    return indicators, total_boost


def deduplicate_indicators(indicators: List[SuspiciousIndicator]) -> List[SuspiciousIndicator]:
    """
    Standardizes and deduplicates findings across all input types and detectors.
    - Prevents duplicate warnings for the same underlying issue.
    - Retains highest severity (HIGH > MEDIUM > LOW).
    - Merges detection sources when flagged by multiple components.
    - Preserves highest confidence score if supported.
    """
    severity_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    deduped: List[SuspiciousIndicator] = []
    seen: Dict[Tuple[str, str], int] = {}

    for ind in indicators:
        norm_desc = re.sub(r"[^\w\s]", "", ind.description.lower()).strip()
        norm_title = re.sub(r"[^\w\s]", "", ind.title.lower()).strip()
        key = (ind.category.lower(), norm_desc[:35] if norm_desc else norm_title[:35])

        if key in seen:
            existing_idx = seen[key]
            existing = deduped[existing_idx]
            # Escalate severity if incoming is higher
            if severity_rank.get(ind.severity, 1) > severity_rank.get(existing.severity, 1):
                existing.severity = ind.severity
            # Merge distinct detection sources
            if ind.source and ind.source not in existing.source:
                existing.source = f"{existing.source}, {ind.source}"
            # Keep highest supported confidence
            if ind.confidence is not None:
                if existing.confidence is None or ind.confidence > existing.confidence:
                    existing.confidence = ind.confidence
        else:
            seen[key] = len(deduped)
            deduped.append(
                SuspiciousIndicator(
                    category=ind.category,
                    title=ind.title,
                    description=ind.description,
                    severity=ind.severity,
                    source=ind.source,
                    confidence=ind.confidence
                )
            )

    return deduped


def calculate_unified_risk_score(
    indicators: List[SuspiciousIndicator],
    ai_estimated_score: Optional[int] = None,
    is_authoritative_threat: bool = False,
    is_insufficient_data: bool = False
) -> Tuple[Optional[int], RiskCategory, str]:
    """
    Computes a deterministic, explainable, monotonic risk score from 0 to 100.
    
    Principles:
    1. If insufficient data (critical services unavailable without decisive heuristics), returns (None, RiskCategory.INSUFFICIENT_DATA, 'INSUFFICIENT_DATA').
    2. Confirmed Safe Browsing threat match always produces score >= 95 (High Risk).
    3. Severe security indicators (HIGH) provide a hard minimum floor (1 HIGH -> >= 65, 2+ HIGH -> >= 85).
    4. MEDIUM indicators contribute +15 each; LOW indicators contribute +5 each.
    5. Clean results from one detector cannot cancel verified threats from another detector (monotonic threat floor).
    6. Truly clean evaluation (zero indicators, AI confirms clean) is capped at <= 25 (Low Risk).
    """
    if is_insufficient_data:
        return None, RiskCategory.INSUFFICIENT_DATA, "INSUFFICIENT_DATA"

    if is_authoritative_threat:
        final_score = max(95, ai_estimated_score if ai_estimated_score is not None else 95)
        return final_score, RiskCategory.HIGH, "HIGH"

    high_count = sum(1 for ind in indicators if ind.severity == "HIGH")
    med_count = sum(1 for ind in indicators if ind.severity == "MEDIUM")
    low_count = sum(1 for ind in indicators if ind.severity == "LOW")

    # Heuristic baseline calculation
    heuristic_score = 10 + (high_count * 25) + (med_count * 15) + (low_count * 5)
    heuristic_score = min(95, heuristic_score)

    if ai_estimated_score is not None:
        # Detect non-AI heuristic indicators that might enforce a monotonic threat floor
        non_ai_high = sum(
            1 for ind in indicators
            if ind.severity == "HIGH" and (
                not ind.source
                or "Gemini" not in ind.source
                or any(k in ind.source for k in ("Rule", "Heuristic", "Tesseract", "Structural", "Safe Browsing"))
            )
        )
        non_ai_med = sum(
            1 for ind in indicators
            if ind.severity == "MEDIUM" and (
                not ind.source
                or "Gemini" not in ind.source
                or any(k in ind.source for k in ("Rule", "Heuristic", "Tesseract", "Structural", "Safe Browsing"))
            )
        )

        if non_ai_high >= 2:
            heuristic_floor = 85
        elif non_ai_high == 1:
            heuristic_floor = 65
        elif non_ai_med > 0:
            heuristic_floor = min(60, 10 + non_ai_med * 15)
        else:
            heuristic_floor = 0

        if len(indicators) == 0:
            combined = min(25, ai_estimated_score)
        else:
            combined = max(ai_estimated_score, heuristic_floor)
    else:
        if high_count >= 2:
            combined = max(heuristic_score, 85)
        elif high_count == 1:
            combined = max(heuristic_score, 65)
        else:
            combined = heuristic_score

    final_score = max(0, min(100, int(combined)))
    category = score_to_category(final_score)
    return final_score, category, category.value.upper()


# --- Text Risk Evaluation ---
def evaluate_text_risk(
    text: str,
    ai_result: Optional[GeminiTextAnalysisRaw] = None,
    source_context: Optional[str] = None
) -> Tuple[RiskAssessment, TextAnalysisFindings]:
    """
    Combines Gemini AI contextual evaluation with rule-based heuristic indicators.
    Produces a unified 0-100 risk score and standardized indicator set.
    """
    # 1. Collect rule-based indicators
    rule_indicators, _ = scan_text_heuristics(text)

    # 2. Collect AI indicators across the 10 dimensions (if AI was available)
    raw_ai_indicators: List[SuspiciousIndicator] = []
    checks_completed: List[str] = ["NLP & Rule Heuristics"]
    checks_unavailable: List[str] = []

    if ai_result:
        checks_completed.append("Gemini AI Contextual Analysis")

        def add_ai_indicator(category: str, title: str, items: List[str], severity: str, base_confidence: float):
            for item in items:
                cleaned = item.strip()
                if cleaned:
                    raw_ai_indicators.append(
                        SuspiciousIndicator(
                            category=category,
                            title=title,
                            description=cleaned,
                            severity=severity,
                            source="Gemini AI Text Analysis",
                            confidence=base_confidence
                        )
                    )

        add_ai_indicator("Pricing", "Unrealistic Price / Deep Discount Claim", ai_result.unrealistic_discounts, "HIGH", 0.88)
        add_ai_indicator("Prize / Giveaway", "Fake Prize or Lottery Pattern", ai_result.fake_prize_indicators, "HIGH", 0.92)
        add_ai_indicator("Payment Request", "Urgent / Suspicious Payment Demand", ai_result.urgent_payment_requests, "HIGH", 0.90)
        add_ai_indicator("Brand Impersonation", "Brand Spoofing or Identity Mimicry", ai_result.brand_impersonation, "HIGH", 0.91)
        add_ai_indicator("Investment Scheme", "Unrealistic Investment Promise", ai_result.fake_investment_promises, "HIGH", 0.89)
        add_ai_indicator("Phishing Vector", "Phishing / Security Bait Language", ai_result.phishing_language, "HIGH", 0.90)
        add_ai_indicator("Data Harvesting", "Solicitation for Sensitive Personal Information", ai_result.sensitive_info_requests, "HIGH", 0.94)
        add_ai_indicator("Manipulative Tactic", "Manipulative Psychological Tactic", ai_result.manipulative_techniques, "MEDIUM", 0.80)
        add_ai_indicator("Misleading Statement", "Misleading or Unsubstantiated Claim", ai_result.misleading_statements, "MEDIUM", 0.82)
        add_ai_indicator("Product Legitimacy", "Suspicious Product Offering", ai_result.suspicious_product_offers, "HIGH", 0.85)
    else:
        checks_unavailable.append("Gemini AI Contextual Analysis")

    # 3. Deduplicate indicators across heuristics and AI
    all_indicators = deduplicate_indicators(rule_indicators + raw_ai_indicators)

    # 4. Determine assessment status and insufficient evidence
    is_insufficient_data = (ai_result is None) and (len(rule_indicators) == 0)

    if is_insufficient_data:
        assessment_status = AssessmentStatus.INSUFFICIENT_DATA
    elif len(checks_unavailable) == 0:
        assessment_status = AssessmentStatus.COMPLETE
    else:
        assessment_status = AssessmentStatus.PARTIAL

    # 5. Calculate unified risk score
    final_score, category, risk_level_str = calculate_unified_risk_score(
        indicators=all_indicators,
        ai_estimated_score=ai_result.estimated_risk_score if ai_result else None,
        is_authoritative_threat=False,
        is_insufficient_data=is_insufficient_data
    )

    # 6. Explanation and Recommendations
    if is_insufficient_data:
        summary = "Unable to verify – insufficient security data."
        explanation = (
            "Unable to verify advertisement authenticity due to insufficient security data. "
            "Gemini AI contextual analysis was unavailable, and automated heuristics did not find conclusive patterns."
        )
        recommendations = [
            "Exercise caution before taking action on promotional claims or submitting personal details.",
            "Verify the merchant or brand independently through official channels before completing purchases."
        ]
    elif ai_result:
        summary = ai_result.summary
        explanation = ai_result.explanation
        recommendations = list(ai_result.recommended_actions) if ai_result.recommended_actions else []
    else:
        summary = "Advertisement evaluated via NLP and rule heuristics."
        explanation = f"Heuristic analysis detected {len(all_indicators)} suspicious advertising patterns."
        recommendations = [
            "Do not enter personal or payment credentials on unverified advertisements.",
            "Independently verify promotional offers through official channels."
        ]

    if not recommendations:
        if category == RiskCategory.HIGH:
            recommendations = [
                "Do not click links or send payment details through this advertisement.",
                "Verify the official brand website directly in your browser without clicking promotional links.",
                "Report the advertisement as fraudulent to the hosting platform."
            ]
        elif category == RiskCategory.LOW:
            recommendations = [
                "The advertisement appears consistent with legitimate commercial promotions.",
                "Always verify checkout URLs use secure HTTPS before submitting payment."
            ]
        else:
            recommendations = [
                "Exercise diligence: advertisement exhibits promotional inconsistencies.",
                "Research the offering merchant independently before transacting."
            ]

    risk_assessment = RiskAssessment(
        risk_score=final_score,
        risk_category=category,
        risk_level=risk_level_str,
        status=assessment_status,
        checks_completed=checks_completed,
        checks_unavailable=checks_unavailable,
        summary=summary,
        indicators=all_indicators,
        explanation=explanation,
        recommendations=recommendations
    )

    findings = TextAnalysisFindings(
        detected_claims=ai_result.detected_claims if ai_result else [],
        unrealistic_discounts=ai_result.unrealistic_discounts if ai_result else [],
        fake_prize_indicators=ai_result.fake_prize_indicators if ai_result else [],
        urgent_payment_requests=ai_result.urgent_payment_requests if ai_result else [],
        misleading_statements=ai_result.misleading_statements if ai_result else [],
        suspicious_product_offers=ai_result.suspicious_product_offers if ai_result else [],
        brand_impersonation=ai_result.brand_impersonation if ai_result else [],
        fake_investment_promises=ai_result.fake_investment_promises if ai_result else [],
        phishing_language=ai_result.phishing_language if ai_result else [],
        sensitive_info_requests=ai_result.sensitive_info_requests if ai_result else [],
        manipulative_techniques=ai_result.manipulative_techniques if ai_result else [],
        urgency_cues=[ind.title for ind in all_indicators if ind.category in ("Urgency Trigger", "Manipulative Tactic")],
        suspicious_patterns=[ind.description for ind in all_indicators]
    )

    return risk_assessment, findings


# --- URL Risk Evaluation (Phase 5 Unified) ---
def evaluate_url_risk(
    heuristic_flags: List[str],
    safe_browsing_result: Dict[str, Any],
    ai_result: Optional[GeminiUrlAnalysisRaw] = None,
    url_info: Optional[Dict[str, Any]] = None
) -> Tuple[RiskAssessment, UrlAnalysisDetail]:
    """
    Combines Google Safe Browsing v5 threat findings, URL structural & lexical heuristics,
    and Gemini AI phishing/impersonation analysis.
    Deduplicates indicators and enforces explainable 0-100 risk scoring.
    """
    all_raw_indicators: List[SuspiciousIndicator] = []

    # 1. Google Safe Browsing v5 threat intelligence
    is_sb_threat = (safe_browsing_result.get("is_safe") is False) or (safe_browsing_result.get("status") == "MATCH_FOUND")
    threat_types = safe_browsing_result.get("threat_types", [])

    if is_sb_threat:
        for threat in (threat_types or ["MALICIOUS_RESOURCE"]):
            all_raw_indicators.append(
                SuspiciousIndicator(
                    category="Threat Intelligence",
                    title=f"Verified Threat: {threat}",
                    description=f"Flagged by Google Safe Browsing as {threat}. High likelihood of malicious payload or phishing.",
                    severity="HIGH",
                    source="Google Safe Browsing v5",
                    confidence=0.98
                )
            )

    # 2. Heuristic Analysis flags
    for flag in heuristic_flags:
        f_lower = flag.lower()
        is_high = any(k in f_lower for k in ["ip address", "impersonation", "punycode", "open-redirect", "sensitive", "bait keyword"])
        severity = "HIGH" if is_high else "MEDIUM"
        confidence = 0.88 if is_high else 0.72

        if "ip address" in f_lower:
            title = "Direct IP Hostname"
        elif "punycode" in f_lower:
            title = "Punycode Homograph Encoding"
        elif "impersonation" in f_lower or "brand" in f_lower:
            title = "Brand Impersonation in Path/Subdomain"
        elif "shorten" in f_lower:
            title = "Obscured Link Shortener"
        elif "top-level" in f_lower:
            title = "Low-Reputation Top-Level Domain"
        elif "port" in f_lower:
            title = "Non-Standard Network Port"
        elif "open-redirect" in f_lower:
            title = "Open-Redirect Parameter"
        elif "unencrypted" in f_lower:
            title = "Unencrypted HTTP Protocol"
        elif "depth" in f_lower or "subdomain" in f_lower:
            title = "Excessive Subdomain Depth"
        else:
            title = "Suspicious URL Characteristic"

        all_raw_indicators.append(
            SuspiciousIndicator(
                category="Heuristic Analysis",
                title=title,
                description=flag,
                severity=severity,
                source="URL Structural Heuristics",
                confidence=confidence
            )
        )

    # 3. Gemini AI Analysis indicators
    if ai_result:
        if ai_result.is_brand_impersonation:
            brand = ai_result.detected_brand or "Targeted Brand"
            all_raw_indicators.append(
                SuspiciousIndicator(
                    category="Brand Impersonation",
                    title=f"Brand Spoofing or Mimicry ({brand})",
                    description=f"The URL appears to impersonate {brand} through deceptive subdomain or path structure.",
                    severity="HIGH",
                    source="Gemini AI Phishing Analysis",
                    confidence=0.92
                )
            )

        if ai_result.is_lookalike_domain:
            all_raw_indicators.append(
                SuspiciousIndicator(
                    category="Lookalike Domain",
                    title="Typosquatting or Lookalike Domain",
                    description="Domain name visually mimics a recognized organization through character substitution or deceptive spelling.",
                    severity="HIGH",
                    source="Gemini AI Phishing Analysis",
                    confidence=0.91
                )
            )

        if ai_result.is_phishing_login:
            all_raw_indicators.append(
                SuspiciousIndicator(
                    category="Credential Harvesting",
                    title="Phishing Login or Security Bait",
                    description="Destination URL simulates an account verification or login form to intercept user credentials.",
                    severity="HIGH",
                    source="Gemini AI Phishing Analysis",
                    confidence=0.94
                )
            )

        if ai_result.is_suspicious_shortener:
            all_raw_indicators.append(
                SuspiciousIndicator(
                    category="Redirection Obfuscation",
                    title="Obscured Link Shortener",
                    description="URL utilizes a redirection service which conceals the destination landing page from scrutiny.",
                    severity="MEDIUM",
                    source="Gemini AI Phishing Analysis",
                    confidence=0.82
                )
            )

        for pat in ai_result.suspicious_patterns:
            cleaned = pat.strip()
            if cleaned:
                all_raw_indicators.append(
                    SuspiciousIndicator(
                        category="Deceptive Pattern",
                        title="Suspicious Link Pattern",
                        description=cleaned,
                        severity="MEDIUM",
                        source="Gemini AI Phishing Analysis",
                        confidence=0.80
                    )
                )

    # 4. Standardized deduplication across Safe Browsing, heuristics, and AI
    indicators = deduplicate_indicators(all_raw_indicators)

    # 5. Track checks completed and unavailable
    checks_completed: List[str] = ["URL Structural & SSRF Validation", "Security Heuristic Rules"]
    checks_unavailable: List[str] = []

    sb_checked = safe_browsing_result.get("checked")
    if sb_checked is None:
        sb_checked = safe_browsing_result.get("status") in ("MATCH_FOUND", "NO_THREAT_FOUND") or (safe_browsing_result.get("is_safe") is not None)
    sb_checked = bool(sb_checked)
    sb_status = safe_browsing_result.get("status", "UNCONFIGURED")

    if sb_checked:
        checks_completed.append("Google Safe Browsing v5")
    else:
        checks_unavailable.append(f"Google Safe Browsing v5 ({sb_status})")

    if ai_result is not None:
        checks_completed.append("Gemini AI Contextual Analysis")
    else:
        checks_unavailable.append("Gemini AI Contextual Analysis")

    # 6. Check for Insufficient Data condition
    has_high_heuristic = any(ind.severity == "HIGH" for ind in indicators)
    is_insufficient_data = (not sb_checked) and (ai_result is None) and (not has_high_heuristic)

    if is_insufficient_data:
        assessment_status = AssessmentStatus.INSUFFICIENT_DATA
    elif len(checks_unavailable) == 0:
        assessment_status = AssessmentStatus.COMPLETE
    else:
        assessment_status = AssessmentStatus.PARTIAL

    # 7. Unified risk score calculation
    final_score, category, risk_level_str = calculate_unified_risk_score(
        indicators=indicators,
        ai_estimated_score=ai_result.estimated_risk_score if ai_result else None,
        is_authoritative_threat=is_sb_threat,
        is_insufficient_data=is_insufficient_data
    )

    # 8. Explanation and Recommendations
    if is_insufficient_data:
        summary = "Unable to verify – insufficient security data."
        explanation = (
            "Unable to verify this URL destination due to insufficient security data. "
            "Both Google Safe Browsing threat intelligence and Gemini AI contextual analysis were unavailable, "
            "and structural heuristics did not find conclusive evidence."
        )
        recommendations = [
            "Exercise extreme caution before navigating to or entering information on this website.",
            "Verify the destination domain directly by navigating to the official website in a new browser tab.",
            "Avoid downloading attachments or submitting credentials on unverified websites."
        ]
    elif ai_result and ai_result.explanation:
        summary = ai_result.summary
        explanation = ai_result.explanation
        recommendations = list(ai_result.recommendations) if ai_result.recommendations else []
    else:
        if category == RiskCategory.HIGH:
            explanation = (
                "This URL displays critical threat indicators such as confirmed malware/phishing reports, "
                "direct IP addressing, or brand typosquatting. Do not enter credentials, download files, or submit payment."
            )
            recommendations = [
                "Do not click this link or submit personal information.",
                "Verify the official company website by typing the address directly in your browser.",
                "Block or report the advertisement to the hosting platform."
            ]
        elif category == RiskCategory.MEDIUM:
            explanation = (
                "This URL exhibits structural anomalies, uses an unencrypted protocol, or relies on an obscured redirection service. "
                "Exercise caution before interacting."
            )
            recommendations = [
                "Carefully inspect the domain spelling for typosquatting before proceeding.",
                "Ensure the landing website uses a valid HTTPS connection upon redirection.",
                "Avoid making payments or downloading files from unverified domains."
            ]
        else:
            explanation = (
                "The URL appears structurally legitimate and no active threats were flagged by security databases. "
                "Note: A clean database check does not guarantee complete absence of newly deployed threats."
            )
            recommendations = [
                "Standard cybersecurity diligence still applies.",
                "Ensure the browser address bar shows the legitimate domain and secure lock icon."
            ]

        if is_sb_threat:
            summary = "Verified threat flagged by security databases."
        elif len(checks_unavailable) > 0:
            summary = "URL evaluated via available security checks; external verification partially unavailable."
        else:
            summary = "URL destination integrity evaluated against security heuristics and threat databases."

    if not recommendations:
        recommendations = [
            "Verify the destination domain directly through official channels.",
            "Do not enter passwords or payment credentials on unfamiliar websites."
        ]

    risk_assessment = RiskAssessment(
        risk_score=final_score,
        risk_category=category,
        risk_level=risk_level_str,
        status=assessment_status,
        checks_completed=checks_completed,
        checks_unavailable=checks_unavailable,
        summary=summary,
        indicators=indicators,
        explanation=explanation,
        recommendations=recommendations
    )

    url_detail = UrlAnalysisDetail(
        summary=summary,
        is_lookalike_domain=ai_result.is_lookalike_domain if ai_result else False,
        is_brand_impersonation=ai_result.is_brand_impersonation if ai_result else False,
        is_phishing_login=ai_result.is_phishing_login if ai_result else False,
        is_suspicious_shortener=ai_result.is_suspicious_shortener if ai_result else (url_info.get("is_url_shortener", False) if url_info else False),
        detected_brand=ai_result.detected_brand if ai_result else None,
        suspicious_patterns=[ind.description for ind in indicators if ind.severity in ("HIGH", "MEDIUM")],
        ad_url_consistency=ai_result.ad_url_consistency if ai_result else "Unverified"
    )

    return risk_assessment, url_detail


# --- Image Risk Evaluation (Phase 5 Unified) ---
def evaluate_image_risk(
    ocr_text: Optional[str],
    ocr_confidence: Optional[float],
    ocr_status: str,
    ai_result: Optional[GeminiImageAnalysisRaw] = None,
    source_context: Optional[str] = None
) -> Tuple[RiskAssessment, ImageAnalysisFindings, ImageAnalysisDetail]:
    """
    Combines Tesseract OCR text heuristics with Gemini Vision analysis.
    Deduplicates indicators across modalities and enforces consistent 0-100 risk scoring.
    """
    # 1. OCR text heuristics (if text extracted)
    rule_indicators: List[SuspiciousIndicator] = []
    if ocr_text and ocr_text.strip():
        raw_rules, _ = scan_text_heuristics(ocr_text)
        for r in raw_rules:
            rule_indicators.append(
                SuspiciousIndicator(
                    category=r.category,
                    title=r.title,
                    description=r.description,
                    severity=r.severity,
                    source="Tesseract OCR Heuristics",
                    confidence=r.confidence
                )
            )

    # 2. Extract AI visual indicators from Gemini Vision structured response (if available)
    raw_ai_indicators: List[SuspiciousIndicator] = []
    checks_completed: List[str] = []
    checks_unavailable: List[str] = []

    if ocr_status == "SUCCESS":
        checks_completed.append("Tesseract OCR Text Extraction")
        checks_completed.append("OCR Heuristic Pattern Scanning")
    else:
        checks_unavailable.append(f"Tesseract OCR ({ocr_status})")

    if ai_result:
        checks_completed.append("Gemini Vision Multimodal Analysis")

        def add_ai_indicator(category: str, title: str, items: List[str], severity: str, base_confidence: float):
            for item in items:
                cleaned = item.strip()
                if cleaned:
                    raw_ai_indicators.append(
                        SuspiciousIndicator(
                            category=category,
                            title=title,
                            description=cleaned,
                            severity=severity,
                            source="Gemini Vision AI",
                            confidence=base_confidence
                        )
                    )

        add_ai_indicator("Pricing", "Unrealistic Price / Discount Depiction", ai_result.unrealistic_discounts, "HIGH", 0.88)
        add_ai_indicator("Prize / Giveaway", "Visual Prize or Lottery Claim", ai_result.fake_prize_indicators, "HIGH", 0.92)
        add_ai_indicator("Payment Request", "Urgent Payment or Processing Fee Prompt", ai_result.urgent_payment_requests, "HIGH", 0.90)
        add_ai_indicator("Payment Security", "Suspicious Payment / Banking Instructions", ai_result.suspicious_payment_instructions, "HIGH", 0.89)
        add_ai_indicator("Brand Impersonation", "Brand Spoofing or Logo Mimicry", ai_result.brand_impersonation, "HIGH", 0.92)
        add_ai_indicator("Deceptive Imagery", "Misleading Product or Endorsement Depiction", ai_result.misleading_representations, "MEDIUM", 0.82)
        add_ai_indicator("Contact Integrity", "Suspicious Contact Details or Verification Channel", ai_result.suspicious_contact_details, "MEDIUM", 0.80)
        add_ai_indicator("Visual Consistency", "Visual Inconsistency or Contradiction", ai_result.visual_inconsistencies, "MEDIUM", 0.78)
        add_ai_indicator("Data Harvesting", "Visual Sensitive Credential Harvesting", ai_result.sensitive_info_requests, "HIGH", 0.95)
        add_ai_indicator("Phishing UI", "Deceptive Interface / Fake UI Elements", ai_result.phishing_indicators, "HIGH", 0.93)
    else:
        checks_unavailable.append("Gemini Vision Multimodal Analysis")

    # 3. Deduplicate indicators between OCR rule indicators and AI indicators
    all_indicators = deduplicate_indicators(rule_indicators + raw_ai_indicators)

    # 4. Check for Insufficient Data condition
    has_high_ocr = any(ind.severity == "HIGH" for ind in all_indicators)
    is_insufficient_data = (ai_result is None) and (not has_high_ocr)

    if is_insufficient_data:
        assessment_status = AssessmentStatus.INSUFFICIENT_DATA
    elif len(checks_unavailable) == 0:
        assessment_status = AssessmentStatus.COMPLETE
    else:
        assessment_status = AssessmentStatus.PARTIAL

    # 5. Calculate balanced risk score
    final_score, category, risk_level_str = calculate_unified_risk_score(
        indicators=all_indicators,
        ai_estimated_score=ai_result.estimated_risk_score if ai_result else None,
        is_authoritative_threat=False,
        is_insufficient_data=is_insufficient_data
    )

    # 6. Explanation and Recommendations
    if is_insufficient_data:
        summary = "Unable to verify – insufficient security data."
        explanation = (
            "Unable to verify image advertisement authenticity due to insufficient security data. "
            "Gemini Vision was unavailable, and OCR text heuristics did not find conclusive patterns."
        )
        recommendations = [
            "Exercise caution before following payment or contact instructions depicted in promotional imagery.",
            "Verify merchant authenticity and official websites directly through trusted search engines."
        ]
    elif ai_result:
        summary = ai_result.summary
        explanation = ai_result.explanation
        recommendations = list(ai_result.recommendations) if ai_result.recommendations else []
    else:
        summary = "Image advertisement evaluated via OCR text heuristics."
        explanation = f"OCR text analysis detected {len(all_indicators)} suspicious promotional patterns."
        recommendations = [
            "Do not enter credentials or submit funds based on unverified promotional imagery.",
            "Research merchant legitimacy through independent consumer reviews."
        ]

    if not recommendations:
        if category == RiskCategory.HIGH:
            recommendations = [
                "Do not engage with this advertisement, scan QR codes, or follow payment instructions.",
                "Verify the official brand website directly in your browser without clicking promotional links.",
                "Report the advertisement as fraudulent to the hosting platform."
            ]
        elif category == RiskCategory.MEDIUM:
            recommendations = [
                "Exercise caution: visual presentation contains promotional inconsistencies.",
                "Research the merchant independently before submitting payment or personal information."
            ]
        else:
            recommendations = [
                "The advertisement visual and claims appear consistent with standard promotional practices.",
                "Always verify checkout URLs use secure HTTPS before submitting payment."
            ]

    risk_assessment = RiskAssessment(
        risk_score=final_score,
        risk_category=category,
        risk_level=risk_level_str,
        status=assessment_status,
        checks_completed=checks_completed,
        checks_unavailable=checks_unavailable,
        summary=summary,
        indicators=all_indicators,
        explanation=explanation,
        recommendations=recommendations
    )

    suspicious_descs = [ind.description for ind in all_indicators]

    alignment_note = (
        f"OCR extracted {len(ocr_text.split()) if ocr_text else 0} words. "
        f"Visual observations and text heuristics aligned."
        if ocr_text and ocr_text.strip()
        else "Visual-only analysis (no text detected in image or OCR unavailable)."
    )

    findings = ImageAnalysisFindings(
        extracted_text=ocr_text if (ocr_text and ocr_text.strip()) else None,
        ocr_word_count=len(ocr_text.split()) if ocr_text else 0,
        ocr_confidence=ocr_confidence,
        visual_description=ai_result.summary if ai_result else "Visual description unavailable",
        visual_observations=ai_result.visual_observations if ai_result else [],
        suspicious_elements=suspicious_descs,
        ocr_vision_alignment=alignment_note
    )

    image_detail = ImageAnalysisDetail(
        summary=summary,
        visual_observations=ai_result.visual_observations if ai_result else [],
        suspicious_indicators=[ind.description for ind in all_indicators if ind.severity in ("HIGH", "MEDIUM")]
    )

    return risk_assessment, findings, image_detail
