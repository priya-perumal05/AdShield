# AdShield – Presenter Notes & Slide-by-Slide Script
## Academic Project Evaluation & Demonstration Guide

---

## Presentation Overview & Timing Strategy

| Slide Number | Slide Title | Recommended Time | Core Talking Point |
| :---: | :--- | :---: | :--- |
| **Slide 1** | Title Slide | 1.0 min | Project introduction, team credentials, problem domain |
| **Slide 2** | Abstract | 1.0 min | Malvertising scale, multi-modal concept, privacy focus |
| **Slide 3** | Problem Statement | 1.5 min | 6 key challenges of modern malvertising |
| **Slide 4** | Objectives & Scope | 1.0 min | What AdShield achieves vs explicit boundaries |
| **Slide 5** | Existing vs. Proposed System | 1.5 min | Direct contrast with legacy domain blocklists |
| **Slide 6** | Technology Stack | 1.0 min | FastAPI, React, Gemini SDK, Tesseract, Safe Browsing |
| **Slide 7** | System Architecture | 1.5 min | End-to-end dataflow pipeline & security boundaries |
| **Slide 8** | Text Analysis Modality | 1.0 min | Pydantic schema enforcement & prize scam case study |
| **Slide 9** | Image Analysis & OCR Pipeline | 1.0 min | Tesseract extraction + Gemini Vision scene reasoning |
| **Slide 10** | URL Security & Phishing | 1.0 min | SSRF blocking, Safe Browsing v5 official test URL |
| **Slide 11** | Automatic AI Model Fallback | 1.5 min | 3-tier priority failover, Pacific midnight cooldown |
| **Slide 12** | Unified Risk Dashboard | 1.0 min | 0–100 scale, weighted fusion, ethical disclaimer |
| **Slide 13** | Testing & Engineering Results | 1.0 min | 142 automated tests (100% pass), zero invented ML % |
| **Slide 14** | Conclusion & Future Roadmap | 1.0 min | Project achievements, future headless sandbox, Q&A |
| **Total** | **Complete Presentation** | **~15 minutes** | **Structured, rigorous, academic delivery** |

---

## Slide-by-Slide Presenter Script

### Slide 1: Title Slide (AI-Powered Fake Advertisement Detection System)
> **What to Say:**
> "Good morning respected evaluators, professors, and peers. Today, our team is presenting our capstone engineering project: **AdShield – AI-Powered Fake Advertisement Detection System**.
> 
> As digital commerce has grown, so too has the malicious advertising ecosystem—commonly known as malvertising. Online users encounter deceptive promotional ads, advance-fee prize scams, counterfeit luxury sales, and banking phishing lures across their social media feeds and search engines every single day. 
> 
> Our project introduces a production-ready, multi-modal detection system that inspects ad text, visual image banners, and target destination URLs to provide explainable threat telemetry on a 0 to 100 risk scale. Let us walk you through the architecture, design, and implementation of AdShield."

---

### Slide 2: Abstract (Executive Summary & Core Vision)
> **What to Say:**
> "To understand the motivation behind AdShield, let us examine our abstract on Slide 2.
> 
> The problem is clear: modern fraudulent advertisements deliberately bypass traditional security mechanisms. They evade keyword filters by applying psychological urgency, they hide deceptive claims inside image graphics, and they rotate through short-lived domains that haven't yet been blacklisted.
> 
> AdShield solves this through a hybrid, multi-modal architecture. Instead of evaluating just one attribute, we examine all three pillars: the promotional text copy using Google Gemini Large Language Models, the visual ad banner using Tesseract OCR and Gemini Vision, and the destination landing page using Google Safe Browsing API v5 and SSRF filters.
> 
> A key innovation of our system is our **zero-database, privacy-preserving design**. Ad submissions and images are evaluated ephemerally in RAM and immediately discarded. This ensures sub-2.5-second response times while eliminating data privacy liabilities under regulations like GDPR."

---

### Slide 3: Problem Statement (Threat Landscape)
> **What to Say:**
> "Moving to Slide 3, we have categorized the six critical challenges of modern malvertising that informed our system design:
> 
> 1. **Fake Promotional Ads**: Counterfeit products—such as luxury watches or electronics offered at 90% to 99% below retail—designed to steal payment card credentials.
> 2. **Advance-Fee Prize Scams**: Messages claiming the user won a $10,000 gift card, demanding a small upfront fee ($4.99) or personal details to claim it.
> 3. **Urgent Payment Extortion**: False alerts claiming a streaming or bank account is suspended, demanding immediate cryptocurrency or wire payments.
> 4. **Credential Harvesting**: Sophisticated phishing communications impersonating Chase, PayPal, or Amazon to steal passwords and debit PINs.
> 5. **Visual Text Cloaking**: Threat actors burn deceptive promises directly into JPEG and PNG graphics, knowing that basic web scrapers only read plain HTML text.
> 6. **Cloud API Quota Bottlenecks**: A crucial software engineering problem: cloud AI services enforce strict rate limits (RPM, TPM, and daily quotas). If an application relies on a single model without fallback engineering, any quota spike crashes the entire user experience."

---

### Slide 4: Objectives & Scope (System Scope)
> **What to Say:**
> "Slide 4 establishes our core project objectives alongside our explicit operational scope.
> 
> Our objectives were straightforward: build a multi-modal analyzer for text, images, and URLs; extract embedded image typography using Tesseract OCR 5.4.0; apply Large Language Models with strict JSON schema enforcement; query Google Safe Browsing API v5; and build an automated model fallback system that prevents downtime.
> 
> We also defined clear architectural boundaries:
> - **In Scope**: Evaluating ad text up to 50,000 characters, validating images up to 10 MB, enforcing SSRF protections, and providing automated AI model failover across three Gemini models.
> - **Out of Scope**: We intentionally omit SQL databases and user logins to uphold strict user confidentiality. Furthermore, we inspect URL structure, heuristics, and threat intelligence rather than executing unvetted JavaScript code in a browser sandbox."

---

### Slide 5: Existing System vs. Proposed AdShield System (Comparative Analysis)
> **What to Say:**
> "In Slide 5, we directly contrast traditional advertisement defenses against AdShield across seven key dimensions.
> 
> Traditional systems—such as browser ad-block extensions and DNS sinkholes—are single-dimensional. They look only at domain blacklists. If an ad domain was registered 3 hours ago, blacklists fail completely because they take 12 to 48 hours to update.
> 
> Furthermore, traditional tools completely ignore visual text inside banner images, and when they do inspect text, they use naive keyword matching that generates high false-positive rates on legitimate promotional sales.
> 
> In contrast, AdShield evaluates semantics, visual text, and live threat intelligence simultaneously. Notice our resilience: when an API rate limit occurs, existing tools crash with HTTP 429; AdShield seamlessly switches models in the background. And while existing tools store user history in tracking databases, AdShield operates on a zero-database, privacy-preserving paradigm."

---

### Slide 6: Technology Stack & Engineering Architecture
> **What to Say:**
> "Slide 6 breaks down our technology stack.
> 
> - On the **Frontend**, we selected **React 19** with **TypeScript** and **Vite**. This gives us strict compile-time type safety, synchronized Pydantic interfaces, and lightning-fast Hot Module Replacement.
> - On the **Backend**, we implemented **FastAPI** on Python 3.9+ running under the **Uvicorn ASGI** server. FastAPI provides asynchronous request handling and native data validation through Pydantic v2.
> - For **AI and Computer Vision**, we utilize the official Google Gen AI SDK (`google-genai`), pairing `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, and `gemini-2.5-flash-lite` with **Tesseract OCR 5.4.0** and **Pillow**.
> - For **Security**, we integrated **Google Safe Browsing API v5**, a custom SSRF private subnet resolver, and Python's `zoneinfo` module.
> 
> Notice that there is no database listed here. That is deliberate: AdShield is completely stateless."

---

### Slide 7: System Architecture & Data Flow Pipeline
> **What to Say:**
> "Slide 7 presents our system architecture and end-to-end data pipeline.
> 
> When a user submits an advertisement via the React frontend, the request arrives at our FastAPI REST gateway. Depending on the input modality:
> - **Text ads** pass through rule-based NLP heuristics before routing to our GeminiModelManager.
> - **Image ads** are verified with Pillow to prevent decompression bombs, passed to Tesseract OCR to extract typography, and dispatched to Gemini Vision for visual scene inspection.
> - **Destination URLs** are validated against our SSRF filter to block loopback or cloud metadata probing, queried against Google Safe Browsing API v5, and analyzed for typosquatting.
> 
> Notice the center box: the **GeminiModelManager**. It maintains an in-memory, thread-safe health registry. If the primary model is throttled, it immediately falls back to model 2 or model 3. Finally, our **Unified Risk Engine** fuses all findings into an explainable risk assessment returned to the dashboard."

---

### Slide 8: Modality 1: Text Advertisement Semantic Analysis
> **What to Say:**
> "On Slide 8, we dive into our first analysis modality: Text Advertisement Semantic Analysis.
> 
> Our four-stage pipeline sanitizes inputs, binds formal cybersecurity system instructions, and enforces strict JSON output using Pydantic schemas. The LLM is mathematically constrained by the SDK to return typed JSON fields rather than conversational responses.
> 
> On the right is a verified case study from our functional test suite. We submitted a simulated prize scam claiming the user won a $10,000 Walmart Gift Card with a 15-minute countdown and a $4.99 fee. AdShield flagged the advance-fee fee lure, the artificial urgency, and Walmart brand impersonation, outputting a **High Risk score of 95 out of 100** with clear user guidance."

---

### Slide 9: Modality 2: Image Banner Inspection & Optical Character Recognition
> **What to Say:**
> "Slide 9 covers our second modality: Image Banner Inspection and OCR.
> 
> Threat actors often burn deceptive text inside images so that text crawlers cannot see them. AdShield solves this through a dual-channel pipeline:
> - **Channel 1 (Tesseract OCR 5.4.0)**: Extracts exact text tokens and computes word-level confidence ratings.
> - **Channel 2 (Gemini Vision)**: Evaluates layout anomalies, brand logo fidelity, and deceptive contrast tricks.
> 
> On the right is an illustrative counterfeit luxury ad banner claiming a 'Rolex Submariner 99% Off for $10'. Tesseract OCR extracted the pricing text with 88% confidence, while Gemini Vision flagged the distorted crown logo and unrealistic pricing discrepancy, yielding a **High Risk score of 92 out of 100**."

---

### Slide 10: Modality 3: URL Security, Threat Intel & Phishing Defense
> **What to Say:**
> "Slide 10 details our third modality: Destination URL Security.
> 
> Attackers frequently cloak landing pages behind URL shorteners and lookalike domains. Our defense-in-depth pipeline enforces four layers:
> 1. RFC structural validation and HTTP/HTTPS scheme checks.
> 2. **SSRF protection**: Resolves target hostnames against DNS and blocks queries pointing to private subnets (such as `127.0.0.1` or AWS metadata `169.254.169.254`).
> 3. Heuristic checks detecting lookalike domains (e.g., `paypa1.com` replacing 'l' with '1') and URL shorteners.
> 4. **Google Safe Browsing API v5**: Live lookup against Google's global threat database.
> 
> On the right is a verified test case: when tested with Google's official phishing test URL (`http://testsafebrowsing.appspot.com/s/phishing.html`), Safe Browsing immediately returned a `SOCIAL_ENGINEERING` match, triggering an immediate override to a **High Risk score of 95 out of 100**."

---

### Slide 11: Resilience Engineering: Automatic AI Model Fallback
> **What to Say:**
> "Slide 11 highlights one of our most significant software engineering contributions: our **Automatic AI Model Fallback and Quota Management System**.
> 
> When developing with cloud AI APIs, developers frequently hit rate limits. In AdShield, we established a 3-tier sequential priority chain:
> - **Primary**: `gemini-3.5-flash-lite`
> - **Fallback 1**: `gemini-3.1-flash-lite`
> - **Fallback 2**: `gemini-2.5-flash-lite`
> 
> If the primary model hits HTTP 429 quota exhaustion, our in-memory manager immediately shifts traffic to Fallback 1 without failing the user's request.
> 
> Notice how we handle daily quota resets: Google resets daily quotas at midnight Pacific Time (`America/Los_Angeles`). AdShield uses Python's `zoneinfo` module to calculate the exact seconds remaining until midnight in California, correctly accounting for Daylight Saving Time transitions. Furthermore, exhausted models are strictly bypassed on subsequent requests, meaning zero wasted API calls."

---

### Slide 12: Unified Risk Assessment Dashboard & Explainable Telemetry
> **What to Say:**
> "Slide 12 explains our Unified Risk Assessment Dashboard.
> 
> We synthesize all multi-modal findings into an intuitive 0-to-100 risk score across four tiers:
> - **0 to 30 (Low Risk / Green)**: Legitimate commercial ad with verified terms.
> - **31 to 60 (Medium Risk / Amber)**: Suspicious signals present, such as unencrypted HTTP or missing seller disclosures.
> - **61 to 100 (High Risk / Red)**: High-confidence malvertising, advance-fee scams, or phishing.
> - **Insufficient Data (Grey)**: When critical external services fail, we refuse to provide a false sense of safety.
> 
> Notice our ethical and technical safeguards: our scores are explainable with categorized indicator cards, and we clearly state to users that scores are AI-assisted estimates for guidance, not definitive legal proof of fraud."

---

### Slide 13: System Verification: Comprehensive Engineering Test Results
> **What to Say:**
> "Slide 13 presents our empirical testing results.
> 
> As engineering students, we emphasize strict academic integrity: the metrics shown here represent our **automated software engineering verification suite**, NOT invented machine learning precision/recall percentages.
> 
> Across 8 automated test suites executed via `pytest`, our system achieved:
> - **142 automated tests passed out of 142 collected**—a 100% pass rate in 22.81 seconds.
> - **0 reported failures**.
> - Complete frontend production build passing in 1.34 seconds with Vite.
> - **Zero live API quota consumed during tests**, because all external network calls were verified using deterministic mock fixtures.
> 
> The table on the right breaks down the test coverage across URL security, model fallback, image OCR, text analysis, and unified risk aggregation."

---

### Slide 14: Conclusion & Future Roadmap
> **What to Say:**
> "In conclusion, on Slide 14, AdShield demonstrates an end-to-end, multi-modal, privacy-preserving cybersecurity platform.
> 
> We achieved our core goals: unifying text, image OCR, and URL threat intelligence; replacing opaque binary blocks with explainable 0–100 risk scores; building a zero-downtime model fallback engine; and ensuring complete user privacy through a zero-database architecture.
> 
> Looking ahead, our research roadmap includes:
> 1. Integrating a sandboxed headless browser (using Playwright) to capture dynamic DOM screenshots.
> 2. Developing a lightweight browser extension to evaluate sponsored ads directly within social media feeds.
> 3. Expanding multilingual ad copy models across regional languages.
> 
> Thank you very much for your time and evaluation. We now welcome any questions and technical discussion."

---

## Tips for Answering Evaluator Questions

1. **If asked: 'Why didn\'t you use a database like MongoDB or PostgreSQL?'**
   - *Answer:* "We deliberately designed AdShield on a privacy-by-design principle. When users submit advertisement copy or images to be scanned, storing their submissions in a database creates significant data privacy and GDPR/CCPA compliance risks. By evaluating everything ephemerally in RAM, we achieve sub-millisecond data handling with zero data breach exposure."

2. **If asked: 'What is your machine learning model accuracy?'**
   - *Answer:* "AdShield is a multi-modal security engineering platform that leverages pre-trained Google Gemini foundation models alongside Tesseract OCR and Safe Browsing threat intelligence. Therefore, we evaluate our system through comprehensive software engineering test verification (142 automated tests passing) rather than claiming artificial ML accuracy percentages on small unlabelled datasets."

3. **If asked: 'How do you handle API rate limits?'**
   - *Answer:* "We engineered a concurrency-safe `GeminiModelManager` with a 3-tier fallback chain: `gemini-3.5-flash-lite` fails over to `3.1-flash-lite` and `2.5-flash-lite`. It computes cooldowns dynamically until midnight Pacific Time using Python `zoneinfo`, bypassing exhausted models so user requests never fail."

