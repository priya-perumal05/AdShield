# AdShield – Comprehensive Viva Examination Questions & Answers
## 40 Technical & Conceptual Questions with Student-Friendly Explanations

---

### Category 1: Project Objective & Architecture

#### Q1: What is the main objective of the AdShield project?
**Answer**: AdShield is an AI-powered cybersecurity platform that detects fraudulent, misleading, and malicious online advertisements. It protects consumers by analyzing ad copy text, visual banner images, and landing page URLs to generate an explainable 0–100 risk score with actionable safety recommendations.

#### Q2: What are the three primary analysis modalities supported by AdShield?
**Answer**: 
1. **Text Analysis**: Evaluates copy for deceptive claims, urgency, and advance-fee lures.
2. **Image Analysis**: Uses Tesseract OCR and Gemini Vision to read text in banners and evaluate visual layout anomalies.
3. **URL Security Analysis**: Inspects target landing pages for phishing indicators, typosquatting, shorteners, and Google Safe Browsing threat records.

#### Q3: Why does AdShield use a database-free architecture?
**Answer**: AdShield deliberately operates without a database (no SQL, MongoDB, or Firebase) to protect user privacy. Analyzed ad content and images are processed ephemerally in RAM and discarded immediately. This eliminates data leakage liabilities, prevents user tracking, and guarantees compliance with data privacy regulations (GDPR/CCPA).

---

### Category 2: Artificial Intelligence, NLP & LLMs

#### Q4: What is the role of Natural Language Processing (NLP) in AdShield?
**Answer**: NLP allows the system to understand the semantic meaning, tone, and intent of advertisement text. Unlike simple keyword search, NLP identifies manipulative psychological patterns such as artificial urgency, manufactured scarcity, and social engineering lures.

#### Q5: What is a Large Language Model (LLM) and how is it used in this project?
**Answer**: An LLM is a deep neural network trained on vast text corpora capable of understanding and generating human-like language. In AdShield, Google Gemini models act as an expert cybersecurity analyst that contextually classifies deceptive ad claims and returns structured threat assessments.

#### Q6: How does AdShield ensure Gemini returns valid JSON instead of conversational text?
**Answer**: AdShield uses the official Google Gen AI SDK (`google-genai`) with structured output enforcement. By setting `response_mime_type="application/json"` and passing a Pydantic class to `response_schema`, Gemini is mathematically constrained to generate output strictly conforming to the JSON schema.

#### Q7: What prompt engineering strategy is used for text analysis?
**Answer**: AdShield uses **system instructions** that define a specialized persona (Senior Cybersecurity Threat Analyst), establish a formal threat evaluation taxonomy (phishing, advance fee, brand impersonation), and mandate objective, fact-based scoring criteria.

---

### Category 3: Google Gemini API & Multi-Model Fallback

#### Q8: Which Gemini models are configured in AdShield, and what is the priority order?
**Answer**:
1. **Priority 1 (Primary)**: `gemini-3.5-flash-lite` (Fastest, highly capable, cost-efficient).
2. **Priority 2 (Fallback 1)**: `gemini-3.1-flash-lite`.
3. **Priority 3 (Fallback 2)**: `gemini-2.5-flash-lite`.

#### Q9: What happens when the primary Gemini model encounters an HTTP 429 error?
**Answer**: HTTP 429 indicates rate-limiting or quota exhaustion. The `GeminiModelManager` intercepts the error, marks the primary model unavailable in an in-memory health registry with a calculated cooldown timer, and immediately executes the request on the next model (`gemini-3.1-flash-lite`) without failing the user's request.

#### Q10: How does AdShield distinguish between daily quota exhaustion (RPD) and per-minute rate limits (RPM/TPM)?
**Answer**: The system inspects Google's error message, details, and quota metrics:
- If keywords like `GenerateContentRequestsPerDay`, `daily`, or `requests per day` appear, it is classified as **`QUOTA_EXHAUSTED_DAILY`** (cooldown until Pacific midnight or Google's `retryDelay`).
- If `tokens per minute` or `GenerateContentTokensPerMinute` appear, it is classified as **`RATE_LIMIT_TPM`** (60s cooldown).
- General requests-per-minute limits are classified as **`RATE_LIMIT_RPM`** (60s cooldown).

#### Q11: How is the daily quota cooldown calculated when Google does not provide a `retryDelay`?
**Answer**: Google Gemini daily quotas reset at midnight Pacific Time (`America/Los_Angeles`). AdShield uses Python's standard library `zoneinfo` to compute the exact seconds remaining from the current timestamp until the next midnight in California, automatically adjusting for Daylight Saving Time (PST vs PDT).

#### Q12: Why are authentication errors (HTTP 401/403) NOT allowed to fallback to other models?
**Answer**: An authentication error indicates that the `GEMINI_API_KEY` itself is invalid, revoked, or unauthorized. Because all configured Gemini models share the same project API key, trying fallback models would produce identical 401 errors. The system halts immediately to prevent wasted requests.

---

### Category 4: Computer Vision & Tesseract OCR

#### Q13: What is OCR, and what technology does AdShield use for it?
**Answer**: Optical Character Recognition (OCR) is the electronic conversion of images of typed or handwritten text into machine-encoded text. AdShield uses **Tesseract OCR 5.4.0** through the `pytesseract` Python wrapper.

#### Q14: Why is Tesseract OCR combined with Gemini Vision?
**Answer**: Defense-in-depth:
- **Tesseract OCR** extracts exact strings (phone numbers, prices, URLs) with high character fidelity and confidence scores.
- **Gemini Vision** understands visual scene context, identifying misaligned counterfeit brand logos, misleading graphic elements, and deceptive background contrast that traditional OCR cannot interpret.

#### Q15: How does AdShield handle an image where no text is found?
**Answer**: If Tesseract detects no text, it returns status `NO_TEXT_DETECTED`. AdShield does not fail; it passes the image to Gemini Vision to evaluate purely visual cues (e.g., logo spoofing or adult content) and completes the assessment normally.

#### Q16: What image formats are supported and what is the maximum upload size?
**Answer**: Supported formats are **JPEG**, **JPG**, **PNG**, and **WEBP**, with a maximum file upload limit of **10 Megabytes (MB)**.

---

### Category 5: URL Security & Google Safe Browsing

#### Q17: What is Google Safe Browsing API v5?
**Answer**: Google Safe Browsing is an industry threat intelligence service that maintains real-time blacklists of unsafe web resources. Version 5 (`urls:search`) accepts a URL and checks whether it is actively flagged for `MALWARE`, `SOCIAL_ENGINEERING` (phishing), or `UNWANTED_SOFTWARE`.

#### Q18: What is SSRF, and how does AdShield protect against it?
**Answer**: Server-Side Request Forgery (SSRF) is an attack where a malicious user provides an internal IP address (like `127.0.0.1` or AWS metadata `169.254.169.254`) hoping the server will query its own internal network. AdShield prevents SSRF by resolving the domain to an IP and blocking private, loopback, and cloud metadata addresses before any network call is made.

#### Q19: What is typosquatting / lookalike domain attack?
**Answer**: Typosquatting is registering common misspellings or visual lookalikes of popular domains (e.g., `paypa1.com` replacing `'l'` with `'1'`). AdShield's heuristic engine detects character substitutions, brand keyword padding, and excessive hyphens.

#### Q20: Why are URL shorteners considered a risk factor?
**Answer**: Services like `bit.ly` or `tinyurl.com` mask the destination domain, preventing users and basic crawlers from seeing the final landing page until clicked. AdShield flags shortened URLs to alert users to inspect the destination before proceeding.

---

### Category 6: Risk Scoring & Heuristics

#### Q21: What is the risk score range in AdShield and what do the tiers mean?
**Answer**: The risk score is an integer between **0 and 100**:
- **0–30 (Low / Green)**: Legitimate commercial ad with verified terms.
- **31–60 (Medium / Yellow)**: Suspicious indicators present; exercise caution.
- **61–100 (High / Red)**: High-confidence malicious advertisement or phishing scam.

#### Q22: What happens to the risk score if Google Safe Browsing confirms a threat?
**Answer**: If Safe Browsing returns a match (`SOCIAL_ENGINEERING` or `MALWARE`), the risk engine enforces an immediate override, elevating the risk score to $\ge 90$ (`High` / `MALICIOUS`), regardless of LLM or heuristic ratings.

#### Q23: What is "graceful degradation" and what is `AssessmentStatus.INSUFFICIENT_DATA`?
**Answer**: If external AI or Safe Browsing APIs are down, graceful degradation ensures the application does not crash. It computes a score using available local heuristics and marks the status as `PARTIAL` or `INSUFFICIENT_DATA` so users know that certain security checks could not be verified.

---

### Category 7: Backend Engineering & FastAPI

#### Q24: Why was FastAPI chosen for the backend instead of Flask or Django?
**Answer**:
1. **Asynchronous Performance**: Native `async/await` support handling concurrent I/O operations without thread blocking.
2. **Automatic Schema Validation**: Built-in integration with Pydantic for strict request/response data typing.
3. **Automatic OpenAPI / Swagger Docs**: Generates interactive documentation at `/docs` out of the box.
4. **Lightweight**: Minimal overhead without database ORM bloat.

#### Q25: What is Pydantic and why is it used?
**Answer**: Pydantic is a data validation library that uses Python type annotations. It enforces data types, validates constraints (e.g., URL format, score between 0 and 100), and automatically parses JSON into structured Python objects.

#### Q26: What is ASGI and Uvicorn?
**Answer**: ASGI stands for Asynchronous Server Gateway Interface. Uvicorn is a lightning-fast ASGI web server implementation for Python that executes FastAPI applications concurrently.

#### Q27: How is CORS configured and why is it important?
**Answer**: Cross-Origin Resource Sharing (CORS) is a browser security mechanism that restricts web pages from making requests to a different domain or port. In AdShield, FastAPI's `CORSMiddleware` explicitly permits requests only from the frontend origin (`http://localhost:5173`).

---

### Category 8: Frontend Engineering & React

#### Q28: Why was Vite chosen instead of Create React App?
**Answer**: Vite leverages native ES modules in the browser during development, providing instant server start and lightning-fast Hot Module Replacement (HMR). Its production build uses Rollup to generate highly optimized, minimal bundle sizes.

#### Q29: What are the advantages of using TypeScript in AdShield?
**Answer**: TypeScript adds static type checking to JavaScript. It catches type errors at compile time, synchronizes response types (`index.ts`) with backend Pydantic schemas, and prevents runtime bugs like accessing non-existent object properties.

#### Q30: How does the frontend inform the user that a model fallback occurred?
**Answer**: When `fallback_used: true` is returned in the API response, the frontend renders an **Amber Notification Banner** (`AlertTriangle`) detailing why the primary model was bypassed, and updates the provenance pill to indicate the active fallback model.

---

### Category 9: Cybersecurity & API Defense

#### Q31: How does AdShield prevent API keys from leaking to users?
**Answer**:
1. Keys are stored strictly on the server in `backend/.env`.
2. `.env` is registered in `.gitignore` to prevent repository leaks.
3. API keys are never passed into frontend build configurations (`VITE_` prefix is prohibited for backend secrets).
4. Automated verification scripts scan frontend distribution builds for API key patterns.

#### Q32: What is an image decompression bomb (zip bomb in images) and how is it mitigated?
**Answer**: An attacker uploads an image with small file size on disk that decompresses into gigabytes in RAM, crashing the server. AdShield mitigates this by enforcing a 10MB upload limit and relying on Pillow's built-in `Image.MAX_IMAGE_PIXELS` safety bounds.

#### Q33: How does AdShield handle malicious or malformed input text?
**Answer**: Text inputs are validated for minimum (5 characters) and maximum (50,000 characters) length, stripped of dangerous null bytes, and evaluated without passing raw input directly into OS command lines or SQL queries.

---

### Category 10: Testing & Project Evaluation

#### Q34: What is the difference between unit testing and integration testing in this project?
**Answer**:
- **Unit Testing**: Tests individual functions in isolation (e.g., regex matching, delay duration parser, Pacific midnight calculator).
- **Integration Testing**: Tests full HTTP route flows (e.g., sending a multipart image request through `/api/analyze/image` and verifying the JSON response).

#### Q35: Why were external API calls mocked in automated test suites?
**Answer**:
1. **Quota Preservation**: Prevents exhausting free-tier Gemini API quotas during development.
2. **Deterministic Results**: External network variability or Google downtime does not cause false test failures.
3. **Execution Speed**: 142 tests execute in under 25 seconds instead of several minutes.

#### Q36: How many automated tests are implemented in AdShield and what is the pass rate?
**Answer**: AdShield features **142 automated backend tests** across 8 test suites with a **100% pass rate** (0 failures).

#### Q37: What is thread-safety and how does `GeminiModelManager` achieve it?
**Answer**: Thread-safety ensures that shared data structures cannot be corrupted when multiple threads access them simultaneously. `GeminiModelManager` uses Python's `threading.Lock()` to synchronize access to the model health dictionary.

#### Q38: What are the main limitations of the current AdShield implementation?
**Answer**:
1. **Static URL Inspection**: It inspects URL strings and Safe Browsing records but does not execute dynamic JavaScript in a headless browser sandbox.
2. **Process-Scoped Memory**: The in-memory model health registry resets if the backend server restarts.
3. **API Dependency**: Real-time multi-modal analysis depends on Google cloud service availability.

#### Q39: What future enhancements can be added to AdShield?
**Answer**:
1. Integrating a sandboxed headless browser (Playwright) to take automated screenshots of landing pages.
2. Developing a browser extension for real-time social media feed ad scanning.
3. Incorporating WHOIS domain age and SSL transparency telemetry.

#### Q40: In one sentence, why is AdShield a complete and unique engineering project?
**Answer**: AdShield combines multi-modal AI reasoning, computer vision OCR, real-time threat intelligence, and an automated zero-downtime model fallback system within a privacy-preserving, database-free architecture.

