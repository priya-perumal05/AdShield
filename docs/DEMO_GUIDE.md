# AdShield – Project Demonstration Guide
## Comprehensive Student Guide for Live Examination & Project Presentations

---

## 1. Introduction

This guide walks students and presenters step-by-step through setting up, configuring, and demonstrating the **AdShield – AI-Powered Fake Advertisement Detection System**. 

Follow this guide during project demonstrations, viva evaluations, or technical walkthroughs.

---

## 2. Prerequisites & Initial Setup

Ensure the following prerequisites are installed on your demonstration machine:
- **Python**: Version 3.9, 3.10, 3.11, or 3.12.
- **Node.js**: Version 18 or higher (includes `npm`).
- **Tesseract OCR**: Installed on the operating system.
  - Windows: Installed at `C:\Program Files\Tesseract-OCR\tesseract.exe`.
  - Linux/Ubuntu: Installed via `sudo apt install tesseract-ocr`.
  - macOS: Installed via `brew install tesseract`.

---

## 3. How to Configure API Keys

AdShield requires two external Google API keys for full live functionality:
1. **Google Gemini API Key**: For text, image, and URL contextual AI analysis. Obtainable for free at [Google AI Studio](https://aistudio.google.com/).
2. **Google Safe Browsing API Key**: For destination URL reputation checks. Obtainable for free from the [Google Cloud Console](https://console.cloud.google.com/) under the project "Safe Browsing API".

### Configuring `backend/.env`
1. Navigate to the `backend/` directory.
2. If `.env` does not exist, copy `.env.example`:
   ```bash
   cp .env.example .env
   ```
3. Open `backend/.env` in a text editor and fill in your keys:
   ```env
   # Server Configuration
   HOST=0.0.0.0
   PORT=8000
   DEBUG=True

   # CORS Configuration
   CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173

   # Google Gemini API
   GEMINI_API_KEY=AIzaSy...your_real_gemini_key_here
   GEMINI_MODEL=gemini-3.5-flash-lite
   GEMINI_FALLBACK_MODELS=gemini-3.1-flash-lite,gemini-2.5-flash-lite

   # Google Safe Browsing API
   SAFE_BROWSING_API_KEY=AIzaSy...your_real_safe_browsing_key_here

   # Tesseract OCR path (optional on Windows if in PATH)
   TESSERACT_CMD=
   ```
4. Save the file. **Never commit `.env` to Git.**

---

## 4. How to Start the Application

Open **two terminal windows**:

### Terminal 1: Start Backend (FastAPI)
```bash
cd C:\AdShield\backend
# Optional: activate virtual environment if configured
# venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```
Verify backend health in browser: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### Terminal 2: Start Frontend (React + Vite)
```bash
cd C:\AdShield\frontend
npm run dev
```
You should see:
```
  VITE v8.3.5  ready in 250 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```
Open your web browser and navigate to: **`http://localhost:5173`**

---

## 5. Demonstration Walkthrough

Click **"Launch Analyzer"** on the home page or navigate to the Analyzer tab.

---

### Demo Scenario A: Text Advertisement Analysis

The Analyzer provides three convenient pre-loaded sample buttons below the text area:

#### 1. Legitimate Ad Sample (Expected Risk: LOW, 0–25)
- **Action**: Click the **"Genuine Sale"** sample button.
- **Text**: `"Summer clearance sale: 20% off all clothing this weekend at Nordstrom stores and online. Free standard shipping on orders over $89."`
- **Click**: **"Analyze Ad Copy"**.
- **Expected Results**:
  - **Risk Score**: Low ($\sim 10/100$), Green Badge (`SAFE`).
  - **Model Used Badge**: Shows `Gemini 3.5 Flash-Lite – Primary` (Blue Pill).
  - **Key Indicators**: Standard commercial terms, transparent pricing.
  - **Recommendations**: Safe commercial offer.

#### 2. Suspicious Prize Scam (Expected Risk: HIGH, 85–100)
- **Action**: Click the **"Prize Scam"** sample button.
- **Text**: `"CONGRATULATIONS! You have been selected as the WINNER of a $10,000 Walmart Gift Card! Claim within 15 minutes before your reward expires! Click here immediately to verify your identity and pay a small $4.99 processing fee!"`
- **Click**: **"Analyze Ad Copy"**.
- **Expected Results**:
  - **Risk Score**: High ($\sim 95/100$), Red Badge (`CRITICAL`).
  - **Key Indicators Detected**:
    - Fake Prize / Sweepstakes Lure
    - Artificial Urgency / Pressure Tactic (15-minute countdown)
    - Advance Fee Fraud ($4.99 processing fee)
    - Brand Impersonation (Walmart)
  - **Recommendations**: Warns user not to submit payment or personal data.

---

### Demo Scenario B: Image Banner & OCR Analysis

Switch to the **"Image Advertisement"** tab.

#### 1. Upload a Test Banner
- **Action**: Click **"Select Image"** and choose an image banner (JPG, PNG, or WEBP).
- **Click**: **"Analyze Advertisement Image"**.
- **Expected Results**:
  - **Tesseract OCR Extraction**: Extracted text appears in the "Extracted OCR Text" card with confidence score.
  - **Visual Reasoning**: Gemini Vision analyzes layout, logos, and visual inconsistencies.
  - **Unified Score**: Combines text signals with visual layout cues.

#### 2. Corrupted / Unsupported File Rejection Test
- **Action**: Try uploading a `.txt` or `.exe` file.
- **Expected Result**: Immediately rejected with clear error message: *"Unsupported file format. Allowed types: JPG, JPEG, PNG, WEBP."*

---

### Demo Scenario C: Destination URL Analysis

Switch to the **"Destination URL"** tab.

#### 1. Official Google Safe Browsing Test URL (MALICIOUS)
- **Input URL**: `http://testsafebrowsing.appspot.com/s/phishing.html`
- **Click**: **"Analyze Target URL"**.
- **Expected Result**:
  - **Risk Score**: High ($90–95/100$), Red Badge (`MALICIOUS`).
  - **Google Safe Browsing v5 Status**: `MATCH_FOUND: SOCIAL_ENGINEERING`.
  - **Security Findings**: Explicitly flags verified phishing threat.

#### 2. Lookalike Domain / Typosquatting (HIGH RISK)
- **Input URL**: `http://www.paypa1-security-login.com/verify`
- **Click**: **"Analyze Target URL"**.
- **Expected Result**:
  - **Heuristics & AI**: Flags number substitution `'1'` for letter `'l'`, unauthorized brand keyword `paypa1`, insecure HTTP transport.
  - **Risk Score**: High ($80–95/100$).

#### 3. SSRF Protection Test (Private IP Blocked)
- **Input URL**: `http://127.0.0.1:8000/internal` or `http://169.254.169.254/latest/meta-data`
- **Click**: **"Analyze Target URL"**.
- **Expected Result**:
  - Blocked with `HTTP 400`: *"Target points to a private or loopback IP address. Request blocked for security."*

---

## 6. How to Explain the Risk Score

When presenting to evaluators, explain the scoring formula:

1. **Score Scale (0–100)**:
   - **0–30 (Low / Green)**: Minimal risk; standard legitimate commercial ad.
   - **31–60 (Medium / Yellow)**: Suspicious indicators present; exercise caution.
   - **61–100 (High / Red)**: High probability of scam, phishing, or financial fraud.
2. **Weighted Multi-Evidence Fusion**:
   - The score is not just an LLM guess. It is a weighted combination of:
     - Rule-based regex heuristics (30%).
     - LLM contextual reasoning (70% for text).
     - Google Safe Browsing v5 official threat status (overrides to $\ge 90$ if matched).
3. **Indicator Deduplication**:
   - Redundant alerts from OCR and AI are normalized and deduplicated before rendering.

---

## 7. How to Demonstrate Automatic Model Fallback

AdShield's model manager automatically handles API quota exhaustion:

1. **Architecture**:
   - Primary: `gemini-3.5-flash-lite`
   - Fallback 1: `gemini-3.1-flash-lite`
   - Fallback 2: `gemini-2.5-flash-lite`
2. **Live Display**:
   - Under normal operation, the result badge displays: `Gemini 3.5 Flash-Lite – Primary` (Blue Pill).
   - If the primary model encounters rate-limiting or quota exhaustion (HTTP 429), it automatically fails over to `gemini-3.1-flash-lite`.
   - The UI displays an **Amber Notification Banner**:
     *"Primary AI model quota reached. Switched automatically to Gemini 3.1 Flash-Lite."*
   - The provenance badge dynamically changes to: `Gemini 3.1 Flash-Lite – Automatic Fallback` (Amber Warning Pill).
3. **Model Health Monitoring API**:
   - Open a browser tab to: **`http://localhost:8000/api/ai/models/status`**
   - Displays real-time JSON showing:
     - `configured_primary_model`: `"gemini-3.5-flash-lite"`
     - `configured_fallback_models`: `["gemini-3.1-flash-lite", "gemini-2.5-flash-lite"]`
     - `current_active_model`: Active model name.
     - `models_status`: Total requests, successes, failures, and cooldown seconds remaining.

---

## 8. How to Demonstrate Insufficient Evidence / Graceful Fallback

What happens if the internet disconnects or API quota across all models is exhausted?

1. **No Fake "Safe" Scores**: AdShield will **never** claim an ad is safe simply because AI services failed.
2. **Transparent Security Notices**:
   - The system transitions to `AssessmentStatus.PARTIAL` or `INSUFFICIENT_DATA`.
   - AI is listed under `checks_unavailable`.
   - Complete local rule-based heuristics and Safe Browsing checks are preserved.
   - A clear disclaimer is rendered informing the user that AI was unavailable.

---

## 9. Troubleshooting Instructions

| Issue | Root Cause | Solution |
| :--- | :--- | :--- |
| **"Failed to fetch" on frontend** | Backend server is not running on port 8000 | Ensure `uvicorn app.main:app --port 8000` is running in Terminal 1. |
| **"Invalid API key" (HTTP 401)** | Missing or incorrect `GEMINI_API_KEY` in `backend/.env` | Verify the key in `backend/.env` from Google AI Studio. Restart uvicorn. |
| **Tesseract OCR shows "UNAVAILABLE"** | Tesseract executable not found in PATH | Set `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe` in `backend/.env`. |
| **Model shows "in cooldown"** | Daily quota or rate limit triggered | Check `/api/ai/models/status` for seconds remaining until Pacific midnight. Fallback models handle requests automatically. |
| **CORS Error in browser console** | Frontend running on non-default port | Add your port to `CORS_ORIGINS` in `backend/.env` (e.g. `http://localhost:5174`). |

