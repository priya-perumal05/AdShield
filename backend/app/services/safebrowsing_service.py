"""
AdShield Advanced URL Security & Phishing Detection Engine.

Integrates with Google Safe Browsing API v5 (urls:search endpoint).

IMPORTANT USAGE & REGULATORY NOTICE:
Google Safe Browsing is strictly intended for non-commercial use.
If this system is deployed for commercial or enterprise applications,
Google mandates the use of Google Cloud Web Risk API instead.
See: https://developers.google.com/safe-browsing/reference/rest/v5/urls/search
"""

import re
import time
import logging
import ipaddress
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs
import idna
import httpx

from app.utils.config import get_settings

logger = logging.getLogger("adshield.safebrowsing")

# Official Google Safe Browsing API v5 URL lookup endpoint
SAFE_BROWSING_V5_ENDPOINT = "https://safebrowsing.googleapis.com/v5/urls:search"

# In-memory TTL cache for Safe Browsing responses (avoids duplicate calls and respects cacheDuration)
_SAFE_BROWSING_CACHE: Dict[str, Dict[str, Any]] = {}

# High abuse / low reputation top-level domains frequently abused in spam & phishing campaigns
SUSPICIOUS_TLDS = {
    ".top", ".xyz", ".club", ".work", ".click", ".buzz", ".fit", ".rest",
    ".gq", ".ml", ".cf", ".tk", ".ga", ".bar", ".monster", ".cam",
    ".live", ".loan", ".surf", ".download", ".racing", ".bid"
}

# Recognized brands commonly spoofed or typo-squatted in fake ad landing URLs
BRAND_KEYWORDS = [
    "paypal", "apple", "google", "microsoft", "amazon", "netflix",
    "facebook", "instagram", "chase", "bankofamerica", "wellsfargo",
    "walmart", "target", "bestbuy", "ebay", "usps", "fedex", "dhl", "ups"
]

# Prominent URL shortener services that obscure the destination landing domain
URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd",
    "buff.ly", "cutt.ly", "rebrand.ly", "tiny.cc", "shorturl.at",
    "rb.gy", "bl.ink", "qr.ae"
}

# Query parameters commonly associated with open-redirect vulnerabilities
REDIRECT_QUERY_PARAMS = {
    "url", "redirect", "redirect_url", "redirect_uri", "next",
    "dest", "destination", "return", "return_to", "target", "r", "to", "link"
}

# Suspicious words frequently placed in phishing paths or parameters
SUSPICIOUS_PATH_KEYWORDS = [
    "verify", "secure-login", "security-alert", "free-gift", "claim-reward",
    "claim-prize", "account-update", "confirm-identity", "billing-update",
    "reactivate", "suspend", "unlock-account", "wallet-connect"
]


def clear_safe_browsing_cache() -> None:
    """Clears the in-memory Safe Browsing TTL cache (useful for testing)."""
    _SAFE_BROWSING_CACHE.clear()


def get_cached_safe_browsing(url: str) -> Optional[Dict[str, Any]]:
    """Retrieves an unexpired cache entry if available."""
    entry = _SAFE_BROWSING_CACHE.get(url)
    if entry:
        if time.time() < entry["expires_at"]:
            return entry["result"]
        else:
            del _SAFE_BROWSING_CACHE[url]
    return None


def parse_cache_duration(duration_str: Optional[str], default_seconds: float = 300.0) -> float:
    """Parses Google API duration format (e.g. '300s', '3.5s') into seconds."""
    if not duration_str:
        return default_seconds
    try:
        clean_str = duration_str.strip().rstrip("s")
        return max(5.0, float(clean_str))
    except (ValueError, TypeError):
        return default_seconds


def validate_and_normalize_url(raw_url: str) -> Dict[str, Any]:
    """
    Validates, parses, and normalizes a user-submitted URL.
    Enforces SSRF protection by rejecting private, loopback, and reserved IP ranges.
    Performs IDNA/Punycode decoding and shortener detection.
    
    SECURITY PRINCIPLE:
    This function parses the URL string locally. It NEVER executes network navigation
    or content scraping against the user URL, strictly eliminating SSRF hazards.
    """
    url = (raw_url or "").strip()
    if not url:
        return {
            "valid": False,
            "status": "INVALID_EMPTY",
            "normalized_url": "",
            "domain": "",
            "scheme": "",
            "error": "The provided URL is empty."
        }

    # Check if a non-http(s) scheme was explicitly provided
    if "://" in url:
        scheme_prefix = url.split("://")[0].lower().strip()
        if scheme_prefix not in ("http", "https"):
            return {
                "valid": False,
                "status": "INVALID_SCHEME",
                "normalized_url": url,
                "domain": "",
                "scheme": scheme_prefix,
                "error": f"Unsupported protocol '{scheme_prefix}://'. Only HTTP and HTTPS are permitted."
            }
    elif not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
    except Exception as e:
        return {
            "valid": False,
            "status": "INVALID_FORMAT",
            "normalized_url": url,
            "domain": "",
            "scheme": "",
            "error": f"Failed to parse URL: {str(e)}"
        }

    hostname = (parsed.hostname or "").lower().strip()
    scheme = (parsed.scheme or "").lower().strip()

    if scheme not in ("http", "https"):
        return {
            "valid": False,
            "status": "INVALID_SCHEME",
            "normalized_url": url,
            "domain": hostname,
            "scheme": scheme,
            "error": f"Unsupported protocol '{scheme}'. Only HTTP and HTTPS are permitted."
        }

    # 1. SSRF Protection: Check for localhost or private / reserved IP addresses
    clean_host = hostname.strip("[]")  # Strip brackets from IPv6
    is_localhost = clean_host in ("localhost", "localhost.localdomain", "127.0.0.1", "::1", "0.0.0.0")

    is_ip = False
    ip_obj = None
    try:
        ip_obj = ipaddress.ip_address(clean_host)
        is_ip = True
    except ValueError:
        is_ip = False

    # Check for valid domain structure (must contain dot or be a valid IP / localhost)
    if not hostname or ("." not in hostname and not is_ip and not is_localhost):
        return {
            "valid": False,
            "status": "INVALID_HOSTNAME",
            "normalized_url": url,
            "domain": hostname,
            "scheme": scheme,
            "error": "Invalid URL format. Please provide a valid web address with a domain name."
        }

    if is_localhost or (is_ip and (
        ip_obj.is_loopback
        or ip_obj.is_private
        or ip_obj.is_reserved
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_unspecified
    )):
        return {
            "valid": False,
            "status": "REJECTED_PRIVATE_IP",
            "normalized_url": url,
            "domain": hostname,
            "scheme": scheme,
            "is_ip_address": True,
            "error": "URL references a private, loopback, or reserved destination which is blocked for security (SSRF prevention)."
        }

    # 2. Punycode & IDNA Processing
    is_punycode = False
    decoded_punycode = None
    if "xn--" in hostname:
        try:
            decoded_punycode = idna.decode(hostname)
            is_punycode = True
        except Exception:
            is_punycode = True
            decoded_punycode = hostname

    # 3. URL Shortener Detection
    is_url_shortener = hostname in URL_SHORTENERS

    # 4. Domain & Subdomain Breakdown
    subdomain_parts = hostname.split(".")
    subdomain_count = max(0, len(subdomain_parts) - 2) if len(subdomain_parts) >= 2 else 0

    has_suspicious_tld = any(hostname.endswith(tld) for tld in SUSPICIOUS_TLDS)

    return {
        "valid": True,
        "status": "VALID",
        "normalized_url": url,
        "domain": hostname,
        "scheme": scheme,
        "port": parsed.port,
        "path": parsed.path or "",
        "query": parsed.query or "",
        "is_ip_address": is_ip,
        "is_punycode": is_punycode,
        "decoded_punycode": decoded_punycode,
        "is_url_shortener": is_url_shortener,
        "has_suspicious_tld": has_suspicious_tld,
        "subdomain_count": subdomain_count,
        "error": None
    }


def analyze_url_heuristics(url_info: Dict[str, Any]) -> List[str]:
    """
    Examines structural and lexical indicators of phishing, typo-squatting,
    and deceptive advertising redirect chains.
    """
    flags: List[str] = []
    hostname = url_info.get("domain", "").lower()
    url = url_info.get("normalized_url", "").lower()
    path = url_info.get("path", "").lower()
    query = url_info.get("query", "").lower()

    # 1. Direct Public IP Address as Hostname
    if url_info.get("is_ip_address"):
        flags.append("Direct IP address used as hostname instead of a registered domain")

    # 2. Punycode / IDNA Homograph Character Encoding
    if url_info.get("is_punycode"):
        decoded = url_info.get("decoded_punycode")
        flags.append(f"Domain utilizes Punycode (IDNA) encoding ('{hostname}' resolves to '{decoded}') which may indicate homograph character spoofing")

    # 3. Link Shortener Service
    if url_info.get("is_url_shortener"):
        flags.append("URL utilizes a link shortening service which obscures the final landing destination")

    # 4. Low-Reputation / High-Abuse TLD
    for tld in SUSPICIOUS_TLDS:
        if hostname.endswith(tld):
            flags.append(f"Domain uses high-abuse/low-reputation top-level domain ({tld})")
            break

    # 5. Non-Standard Port Specified
    port = url_info.get("port")
    if port and port not in (80, 443):
        flags.append(f"Non-standard network port ({port}) specified, which is atypical for legitimate commercial advertisers")

    # 6. Brand Impersonation in Subdomains or Path
    for brand in BRAND_KEYWORDS:
        if brand in hostname or brand in path:
            parts = hostname.split(".")
            root_domain = ".".join(parts[-2:]) if len(parts) >= 2 else hostname
            if brand not in root_domain:
                flags.append(f"Prominent brand name ('{brand}') appears in subdomain or path while root domain is different ('{root_domain}')")
                break

    # 7. Excessive Subdomain Depth
    if url_info.get("subdomain_count", 0) >= 3:
        flags.append(f"Excessive subdomain depth ({url_info.get('subdomain_count')} levels) frequently utilized to obfuscate phishing destinations")

    # 8. Open Redirect Parameters
    if query:
        parsed_q = parse_qs(query)
        for param in REDIRECT_QUERY_PARAMS:
            if param in parsed_q:
                val = parsed_q[param][0] if parsed_q[param] else ""
                if "http://" in val or "https://" in val or "//" in val:
                    flags.append(f"URL contains open-redirect parameter ('{param}={val[:30]}...') often exploited in phishing redirect chains")
                    break

    # 9. High-Risk Phishing Keywords in Path or Query
    for term in SUSPICIOUS_PATH_KEYWORDS:
        if term in path or term in query:
            flags.append(f"URL contains sensitive account/security bait keyword: '{term}'")
            break

    # 10. Unencrypted HTTP Protocol
    if url_info.get("scheme") == "http":
        flags.append("Unencrypted connection (HTTP). Legitimate commercial advertisers typically use HTTPS.")

    # 11. Unusually Long URL
    if len(url) > 130:
        flags.append(f"Unusually long URL ({len(url)} characters) frequently associated with obfuscated tracking or phishing parameters")

    return flags


def _parse_varint(buffer: bytes, offset: int) -> Tuple[int, int]:
    """Decodes a protobuf varint integer from a binary buffer."""
    result = 0
    shift = 0
    while offset < len(buffer):
        b = buffer[offset]
        offset += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return result, offset


THREAT_TYPE_NAMES = {
    0: "THREAT_TYPE_UNSPECIFIED",
    1: "MALWARE",
    2: "SOCIAL_ENGINEERING",
    3: "UNWANTED_SOFTWARE",
    4: "POTENTIALLY_HARMFUL_APPLICATION"
}


def parse_search_urls_protobuf(content: bytes) -> Tuple[List[Dict[str, Any]], float]:
    """
    Parses Google Safe Browsing API v5 binary Protocol Buffer (SearchUrlsResponse).
    Proto definition:
      message SearchUrlsResponse {
        repeated ThreatUri threats = 1;
        google.protobuf.Duration cache_duration = 2;
      }
      message ThreatUri {
        string uri = 1;
        repeated ThreatType threat_types = 2; // enum
      }
    """
    threats: List[Dict[str, Any]] = []
    cache_seconds = 300.0
    offset = 0
    total_len = len(content)

    try:
        while offset < total_len:
            tag, offset = _parse_varint(content, offset)
            field_num = tag >> 3
            wire_type = tag & 0x07

            if wire_type == 2:  # length-delimited
                length, offset = _parse_varint(content, offset)
                chunk = content[offset:offset + length]
                offset += length

                if field_num == 1:
                    # ThreatUri message
                    sub_offset = 0
                    uri = ""
                    threat_types = []
                    while sub_offset < len(chunk):
                        sub_tag, sub_offset = _parse_varint(chunk, sub_offset)
                        sub_field = sub_tag >> 3
                        sub_wire = sub_tag & 0x07
                        if sub_wire == 2:
                            sub_len, sub_offset = _parse_varint(chunk, sub_offset)
                            sub_val = chunk[sub_offset:sub_offset + sub_len]
                            sub_offset += sub_len
                            if sub_field == 1:
                                uri = sub_val.decode("utf-8", errors="ignore")
                            elif sub_field == 2:  # packed enum list
                                for b in sub_val:
                                    threat_types.append(THREAT_TYPE_NAMES.get(b, f"THREAT_TYPE_{b}"))
                        elif sub_wire == 0:  # varint enum
                            val, sub_offset = _parse_varint(chunk, sub_offset)
                            if sub_field == 2:
                                threat_types.append(THREAT_TYPE_NAMES.get(val, f"THREAT_TYPE_{val}"))
                    threats.append({"uri": uri, "threatTypes": threat_types})

                elif field_num == 2:
                    # google.protobuf.Duration (field 1: int64 seconds)
                    sub_offset = 0
                    while sub_offset < len(chunk):
                        sub_tag, sub_offset = _parse_varint(chunk, sub_offset)
                        sub_field = sub_tag >> 3
                        sub_wire = sub_tag & 0x07
                        if sub_wire == 0:
                            val, sub_offset = _parse_varint(chunk, sub_offset)
                            if sub_field == 1:
                                cache_seconds = float(val)
                        elif sub_wire == 2:
                            sub_len, sub_offset = _parse_varint(chunk, sub_offset)
                            sub_offset += sub_len
            elif wire_type == 0:
                _, offset = _parse_varint(content, offset)
            else:
                break
    except Exception as e:
        logger.warning(f"Failed to fully parse Safe Browsing protobuf response: {e}")

    return threats, cache_seconds


async def check_safe_browsing(url: str) -> Dict[str, Any]:
    """
    Checks the URL against Google Safe Browsing API v5 using the official `urls:search` endpoint.
    Maintains an in-memory TTL cache with support for positive and negative result caching.
    
    Returns structured dictionary:
    - configured: bool
    - checked: bool
    - is_safe: Optional[bool]
    - status: 'MATCH_FOUND' | 'NO_THREAT_FOUND' | 'UNAVAILABLE' | 'UNCONFIGURED'
    - threat_types: List[str]
    - message: str
    - cache_hit: bool
    """
    settings = get_settings()

    # 1. Check in-memory TTL cache first
    cached = get_cached_safe_browsing(url)
    if cached:
        logger.debug(f"Safe Browsing cache hit for '{url}' (status={cached.get('status')})")
        res = dict(cached)
        res["cache_hit"] = True
        return res

    # 2. Check if API key is configured
    if not settings.is_safe_browsing_configured:
        return {
            "configured": False,
            "checked": False,
            "is_safe": None,
            "status": "UNCONFIGURED",
            "threat_types": [],
            "message": "Google Safe Browsing API key is not configured in backend/.env.",
            "cache_hit": False
        }

    api_key = settings.SAFE_BROWSING_API_KEY
    timeout_sec = getattr(settings, "SAFE_BROWSING_TIMEOUT_SECONDS", 6.0)

    # 3. Call Safe Browsing API v5 (urls:search)
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.get(
                SAFE_BROWSING_V5_ENDPOINT,
                params={"key": api_key, "urls": url}
            )

            # A. Successful response (200 OK)
            if resp.status_code == 200:
                threats: List[Dict[str, Any]] = []
                duration_sec = 300.0

                try:
                    data = resp.json()
                    threats = data.get("threats", [])
                    cache_duration_str = data.get("cacheDuration", "300s")
                    duration_sec = parse_cache_duration(cache_duration_str, 300.0)
                except Exception:
                    # Google Safe Browsing API v5 returns binary application/x-protobuf
                    threats, duration_sec = parse_search_urls_protobuf(resp.content)

                if threats:
                    # Collect all reported threat types
                    threat_types_set = set()
                    for threat in threats:
                        for tt in threat.get("threatTypes", []):
                            threat_types_set.add(tt)
                        if threat.get("threatType"):
                            threat_types_set.add(threat.get("threatType"))

                    threat_types = sorted(list(threat_types_set)) or ["UNSPECIFIED_THREAT"]
                    result = {
                        "configured": True,
                        "checked": True,
                        "is_safe": False,
                        "status": "MATCH_FOUND",
                        "threat_types": threat_types,
                        "message": f"Google Safe Browsing v5 flagged known threats: {', '.join(threat_types)}.",
                        "cache_hit": False
                    }
                else:
                    # Empty threats array: No known threat match found
                    result = {
                        "configured": True,
                        "checked": True,
                        "is_safe": True,
                        "status": "NO_THREAT_FOUND",
                        "threat_types": [],
                        "message": "No known threat match found in Google Safe Browsing database.",
                        "cache_hit": False
                    }

                # Store in TTL cache (both positive matches and negative results are cached)
                _SAFE_BROWSING_CACHE[url] = {
                    "result": result,
                    "expires_at": time.time() + duration_sec
                }
                return result

            # B. Rate Limit / Quota Exhaustion (429)
            elif resp.status_code == 429:
                logger.warning(f"Google Safe Browsing API rate limit or quota exceeded (HTTP 429).")
                return {
                    "configured": True,
                    "checked": False,
                    "is_safe": None,
                    "status": "UNAVAILABLE",
                    "threat_types": [],
                    "message": "Google Safe Browsing API rate limit or quota exceeded.",
                    "cache_hit": False
                }

            # C. Authentication / Configuration Error (400, 403)
            elif resp.status_code in (400, 401, 403):
                logger.error(f"Google Safe Browsing API authentication error (HTTP {resp.status_code}): {resp.text}")
                return {
                    "configured": True,
                    "checked": False,
                    "is_safe": None,
                    "status": "UNAVAILABLE",
                    "threat_types": [],
                    "message": f"Google Safe Browsing API authentication error (HTTP {resp.status_code}).",
                    "cache_hit": False
                }

            # D. Server error (500, 502, 503)
            else:
                logger.error(f"Google Safe Browsing API returned HTTP {resp.status_code}: {resp.text}")
                return {
                    "configured": True,
                    "checked": False,
                    "is_safe": None,
                    "status": "UNAVAILABLE",
                    "threat_types": [],
                    "message": f"Security database check unavailable (HTTP {resp.status_code}).",
                    "cache_hit": False
                }

    except (httpx.TimeoutException, TimeoutError) as te:
        logger.warning(f"Timeout querying Google Safe Browsing API: {te}")
        return {
            "configured": True,
            "checked": False,
            "is_safe": None,
            "status": "UNAVAILABLE",
            "threat_types": [],
            "message": "Security database check unavailable (Request timed out).",
            "cache_hit": False
        }
    except Exception as e:
        logger.error(f"Unexpected error querying Google Safe Browsing API: {e}", exc_info=True)
        return {
            "configured": True,
            "checked": False,
            "is_safe": None,
            "status": "UNAVAILABLE",
            "threat_types": [],
            "message": f"Security database check unavailable ({str(e)}).",
            "cache_hit": False
        }
