# AdShield – AI-Powered Fake Advertisement Detection System

> **"Detect Fake Advertisements Before You Trust"**  
> *Analyse advertisements using AI-powered text, image and URL verification.*

AdShield is a full-stack cybersecurity application engineered to identify potentially fraudulent, misleading, and deceptive online advertisements across digital channels, including social media feeds, search engines, mobile SMS, and display banners.

---

## 1. System Architecture & Features

### Multi-Vector AI Detection Engine
- **Text Analysis**: Detects suspicious promotional claims, unrealistic discounts, fake prize/lottery notifications, urgency triggers, and deceptive language patterns using Google Gemini NLP.
- **Image & Graphic Audit**: Extracts embedded typography via **Tesseract OCR** and evaluates graphical deception (fake trust badges, spoofed buttons, counterfeit visuals) with **Gemini Vision**.
- **URL & Domain Integrity**: Evaluates advertising destination links against **Google Safe Browsing v5** and identifies brand spoofing, typosquatting, open redirects, and malicious low-reputation top-level domains.
- **Intelligent Model Fallback**: Dynamic quota manager automatically rotates across Google Gemini model priorities (`gemini-3.5-flash-lite` → `gemini-3.1-flash-lite` → `gemini-2.5-flash-lite`) with DST-aware Pacific midnight cooldown calculations.
- **Risk Assessment Engine**: Consolidates findings into a unified **0 to 100 Risk Score**:
  - **0–30: Low Risk** (Standard promotional practices)
  - **31–60: Medium Risk** (Suspicious claims, structural anomalies, high urgency)
  - **61–100: High Risk** (Deceptive bait, confirmed phishing/malware, counterfeit impersonation)
- **Zero-Database Ephemeral Session**: In-memory React session history without SQL, MongoDB, or Firebase, ensuring zero permanent tracking or content retention.

---

## 2. Technology Stack

- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS 4, Lucide React (Hosted on **Vercel**)
- **Backend**: Python 3.9+, FastAPI, Uvicorn, Pydantic v2, HTTPX (Hosted as a Docker Web Service on **Render**)
- **OCR Engine**: Tesseract OCR (`tesseract-ocr`, `tesseract-ocr-eng`)
- **AI & Security**: Google Gemini API (`google-genai`), Google Safe Browsing API v5 (Protobuf SearchUrls)
- **Testing**: Pytest, FastAPI TestClient (140 tests passing, 100% pass rate)

---

## 3. Project Structure

```
AdShield/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.tsx            # Header with live backend health & subsystem indicator
│   │   │   ├── Footer.tsx            # Cybersecurity footer & legal disclaimer
│   │   │   ├── RiskBadge.tsx         # Color-coded risk badge (Low/Medium/High)
│   │   │   └── ResultDashboard.tsx   # Detailed analysis metrics, gauges & indicators
│   │   ├── pages/
│   │   │   ├── HomePage.tsx          # Cyber defense landing page with radar shield visual
│   │   │   └── AnalyzerPage.tsx      # Multi-vector scanner (Text, Image, URL tabs)
│   │   ├── services/
│   │   │   └── api.ts                # Environment-aware API client (Vite proxy + Render URL)
│   │   ├── types/
│   │   │   └── index.ts              # TypeScript definitions & data contracts
│   │   ├── App.tsx                   # Main stateful application wrapper
│   │   ├── index.css                 # Dark cybersecurity CSS variables & grid overlay
│   │   └── main.tsx                  # Vite React entry point
│   ├── vercel.json                   # Vercel deployment & SPA routing configuration
│   ├── .env.example                  # Frontend environment variables template
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts                # Vite config with dev proxy to FastAPI
│
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI entry point & CORS configuration
│   │   ├── routes/
│   │   │   ├── health.py             # GET /api/health endpoint
│   │   │   ├── analyze.py            # POST /api/analyze/{text,image,url} endpoints
│   │   │   └── models.py             # GET /api/models/health endpoint
│   │   ├── services/
│   │   │   ├── gemini_service.py     # Gemini text, vision & URL integration
│   │   │   ├── gemini_model_manager.py# Automatic model rotation & cooldown handling
│   │   │   ├── ocr_service.py        # Tesseract OCR engine wrapper
│   │   │   ├── safebrowsing_service.py# Google Safe Browsing v5 & SSRF protection
│   │   │   └── risk_engine.py        # Unified 0–100 risk scoring engine
│   │   ├── models/
│   │   │   └── schemas.py            # Pydantic v2 schemas for requests & responses
│   │   └── utils/
│   │       └── config.py             # Pydantic Settings & environment variables
│   ├── tests/                        # 140 automated unit & regression tests
│   ├── Dockerfile                    # Debian-based production container with Tesseract
│   ├── .dockerignore                 # Excludes .env, tests, and caches from Docker
│   ├── requirements.txt              # Python production dependencies
│   └── .env.example                  # Backend environment variables template
│
├── docs/
│   ├── DEPLOYMENT_GUIDE.md           # Step-by-step production deployment instructions
│   ├── SYSTEM_DOCUMENTATION.md       # Comprehensive system architecture document
│   ├── DEMO_GUIDE.md                 # Live evaluation demo script
│   └── IEEE_PROJECT_REPORT.md        # IEEE-format academic project paper
│
├── .gitignore
├── .dockerignore
└── README.md
```

---

## 4. Local Development Setup

### Step 1: Set Up and Run the Backend

1. Navigate to the `backend` folder:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure local environment variables:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to configure your keys:
   - `GEMINI_API_KEY`: Google Gemini API Key from Google AI Studio.
   - `GEMINI_MODEL`: Default `gemini-3.5-flash-lite`.
   - `GEMINI_FALLBACK_MODELS`: `gemini-3.1-flash-lite,gemini-2.5-flash-lite`.
   - `SAFE_BROWSING_API_KEY`: Google Safe Browsing API Key.
   - `TESSERACT_CMD`: Path to `tesseract.exe` on Windows (e.g. `C:\Program Files\Tesseract-OCR\tesseract.exe`).

5. Run backend tests:
   ```bash
   pytest tests
   ```

6. Start FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   - Swagger Documentation: `http://localhost:8000/docs`
   - Health check: `http://localhost:8000/api/health`

### Step 2: Set Up and Run the Frontend

1. In a new terminal, navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Verify production compilation:
   ```bash
   npm run build
   ```

4. Start Vite development server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:5173`. In development mode, Vite automatically proxies `/api` calls to `http://127.0.0.1:8000`.

---

## 5. Production Cloud Deployment

For detailed, beginner-friendly deployment instructions, read [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md).

### Quick Deployment Summary:

| Component | Platform | Configuration |
| :--- | :--- | :--- |
| **Source Code** | **GitHub (Private)** | `git push origin main` (Ensure `.env` files are not committed) |
| **Backend** | **Render (Docker)** | Root Directory: `backend` • Runtime: `Docker` • Health: `/api/health` |
| **Frontend** | **Vercel** | Root Directory: `frontend` • Framework: `Vite` • Output: `dist` |

### Environment Variables Matrix

#### Backend (Render Dashboard → Environment)
| Variable | Value / Format | Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | `AIzaSy...` | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Primary model |
| `GEMINI_FALLBACK_MODELS` | `gemini-3.1-flash-lite,gemini-2.5-flash-lite` | Fallback models chain |
| `SAFE_BROWSING_API_KEY` | `AIzaSy...` | Google Safe Browsing API v5 key |
| `TESSERACT_CMD` | `/usr/bin/tesseract` | Linux system path inside container |
| `CORS_ORIGINS` | `https://your-app.vercel.app,http://localhost:5173` | Allowed frontend origins |
| `DEBUG` | `False` | Production mode |

#### Frontend (Vercel Project Settings → Environment Variables)
| Variable | Value / Format | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `https://adshield-backend.onrender.com` | Deployed Render backend URL |

> [!IMPORTANT]
> Never expose `GEMINI_API_KEY` or `SAFE_BROWSING_API_KEY` in frontend environment variables. All AI reasoning and threat lookups execute securely on the backend.

---

## 6. Zero-Database Architecture Notice

AdShield deliberately utilizes an **in-memory ephemeral architecture**:
- **Zero SQL / NoSQL Databases**: No PostgreSQL, MySQL, MongoDB, Firebase, or Supabase is used.
- **In-Memory Cache**: Safe Browsing URL lookup cache and Gemini model health/cooldown statuses are maintained in Python memory.
- **Stateless Restarts**: When the backend process or Docker container restarts on Render, in-memory caches and model cooldowns reset to clean initial states.
- **Client-Side Session State**: Scan records remain strictly within browser session state and disappear upon closing the tab.

---

## 7. API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Subsystem health check (Gemini, OCR availability & version, Safe Browsing) |
| `GET` | `/api/models/health` | Status and cooldown timers for Gemini model priority chain |
| `POST` | `/api/analyze/text` | Evaluates advertisement copy with Gemini NLP & heuristics |
| `POST` | `/api/analyze/image` | Evaluates ad graphic with Tesseract OCR & Gemini Vision |
| `POST` | `/api/analyze/url` | Audits destination URL using heuristics & Safe Browsing v5 |

---

## 8. Verification & Test Suite

AdShield includes an automated test suite verifying edge cases, mocked AI responses, URL SSRF security, Protobuf Safe Browsing v5 decoding, model fallback rotation, and risk calculation:

```bash
cd backend
pytest tests
```

- **Tests Passed:** 140 passed (0 failed, 100% pass rate)
- **Frontend Build:** `npm run build` passes with 0 TypeScript/compilation errors
- **Security Check:** Zero API credentials hardcoded in codebase or build output
