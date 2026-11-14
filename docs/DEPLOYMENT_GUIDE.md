# AdShield – Production Cloud Deployment Guide

> **Target Architecture:**  
> • **Code Repository:** Private GitHub Repository  
> • **Frontend Service:** Vercel (React 19 + TypeScript + Vite + Tailwind CSS 4)  
> • **Backend Service:** Render Docker Web Service (Python 3.9 + FastAPI + Uvicorn + Tesseract OCR)  
> • **Database:** None (Zero-persistence in-memory cache & ephemeral session architecture)

---

## Table of Contents

1. [Architecture & Deployment Overview](#1-architecture--deployment-overview)
2. [Step 1: GitHub Private Repository Preparation](#2-step-1-github-private-repository-preparation)
3. [Step 2: Backend Deployment on Render (Docker)](#3-step-2-backend-deployment-on-render-docker)
4. [Step 3: Frontend Deployment on Vercel](#4-step-3-frontend-deployment-on-vercel)
5. [Step 4: End-to-End Verification & Health Checks](#5-step-4-end-to-end-verification--health-checks)
6. [Step 5: Zero-Database Ephemeral Architecture Notice](#6-step-5-zero-database-ephemeral-architecture-notice)
7. [Troubleshooting & Common Questions](#7-troubleshooting--common-questions)

---

## 1. Architecture & Deployment Overview

AdShield separates frontend presentation from backend analysis:

```
[ Browser Client ]
       │
       ▼ (HTTPS)
[ Vercel CDN ] ─── React / Vite Frontend (SPA)
       │
       ▼ (Cross-Origin HTTPS /api requests)
[ Render Cloud ] ─── Docker Container (FastAPI + Uvicorn)
       │                    ├── Tesseract OCR Engine (/usr/bin/tesseract)
       │                    ├── Google Gemini Multi-Modal API (NLP & Vision)
       │                    └── Google Safe Browsing API v5 (SearchUrls)
       ▼
[ Ephemeral RAM ] (In-memory TTL cache & session state — 0 SQL / 0 NoSQL)
```

- **Frontend:** Compiled static assets (`dist/`) distributed via Vercel Edge Network. Communicates with the backend using `VITE_API_BASE_URL`.
- **Backend:** Packaged into a self-contained Debian-based Docker container that installs `tesseract-ocr` and runs FastAPI on dynamic port `$PORT` assigned by Render.
- **CORS Security:** Secured via `CORSMiddleware`, allowing your specific Vercel production origin and preview deployments (`https://*.vercel.app`) without unrestricted wildcards.

---

## 2. Step 1: GitHub Private Repository Preparation

### 2.1 Security & Gitignore Checklist
Before committing any code, verify that:
- [x] `.env` files are excluded by `.gitignore` (`backend/.env`, `frontend/.env`, `*.env`).
- [x] No API keys are hardcoded in frontend source or build artifacts (`frontend/dist`).
- [x] Example templates (`.env.example`) contain placeholders only (`your_gemini_api_key_here`).
- [x] `node_modules/`, `__pycache__/`, `.pytest_cache/`, and virtual environments (`venv/`) are excluded.

### 2.2 Initialize and Push to Private GitHub Repository

Open your terminal in the root directory `c:\AdShield`:

```bash
# 1. Initialize local Git repository (if not already initialized)
git init

# 2. Check git status to ensure .env is NOT staged or tracked
git status

# 3. Add all files tracked by .gitignore
git add .

# 4. Verify that backend/.env is NOT in the staged files list
git status

# 5. Create the initial commit
git commit -m "feat: complete AdShield production-ready release with dark cybersecurity UI"

# 6. Rename default branch to main
git branch -M main

# 7. Link to your private GitHub repository (replace with your actual repository URL)
git remote add origin https://github.com/<your-username>/AdShield.git

# 8. Push to GitHub
git push -u origin main
```

> [!WARNING]
> Ensure your GitHub repository is marked as **Private** to keep your application structure and configuration proprietary.

---

## 3. Step 2: Backend Deployment on Render (Docker)

Render hosts the FastAPI backend inside a containerized environment with native Linux Tesseract OCR installed.

### 3.1 Create Web Service on Render
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Web Service**.
3. Connect your GitHub account and select your **AdShield** repository.
4. Fill in the deployment parameters:

| Setting | Value | Notes |
| :--- | :--- | :--- |
| **Name** | `adshield-backend` | Will generate your URL: `https://adshield-backend.onrender.com` |
| **Region** | Oregon (US West) or closest region | Select region closest to your target users |
| **Branch** | `main` | Production branch |
| **Root Directory** | `backend` | **Important:** Point to the backend directory containing `Dockerfile` |
| **Runtime** | `Docker` | Render automatically uses `backend/Dockerfile` |
| **Instance Type** | Free or Starter | Free tier spins down on inactivity; Starter runs 24/7 |

### 3.2 Configure Render Environment Variables
Under the **Environment Variables** tab, click **Add Environment Variable** and enter the following keys:

| Key | Example Value | Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | `AIzaSy...` | Your Google Gemini API Key from Google AI Studio |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Primary active Gemini model |
| `GEMINI_FALLBACK_MODELS` | `gemini-3.1-flash-lite,gemini-2.5-flash-lite` | Fallback model priority chain |
| `SAFE_BROWSING_API_KEY` | `AIzaSy...` | Google Safe Browsing API Key from Google Cloud |
| `TESSERACT_CMD` | `/usr/bin/tesseract` | Linux system path to Tesseract installed in container |
| `CORS_ORIGINS` | `https://your-app.vercel.app,http://localhost:5173` | Allowed frontend domains (comma-separated) |
| `DEBUG` | `False` | Disable debug mode in production |

> [!NOTE]
> Render automatically injects the `PORT` environment variable (typically `10000`). Our Dockerfile's `CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]` automatically binds to this port.

### 3.3 Configure Health Check
Under **Advanced Settings**:
- **Health Check Path:** `/api/health`
Render periodically polls this endpoint to verify container readiness and ensure zero-downtime rolling deploys.

### 3.4 Deploy & Note Backend URL
Click **Create Web Service**. Render will:
1. Build the Docker image from `backend/Dockerfile`.
2. Install `tesseract-ocr` and Python packages.
3. Start Uvicorn on `$PORT`.
4. Run health check on `/api/health`.

Once deployment succeeds, copy your Render URL:
`https://adshield-backend.onrender.com`

---

## 4. Step 3: Frontend Deployment on Vercel

Vercel provides edge hosting and automatic global CDN distribution for the React frontend.

### 4.1 Import Project to Vercel
1. Log in to [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** → **Project**.
3. Select your GitHub repository **AdShield**.

### 4.2 Configure Build & Output Settings
Configure the project settings in the Vercel setup wizard:

| Setting | Configuration |
| :--- | :--- |
| **Framework Preset** | `Vite` |
| **Root Directory** | Click **Edit** and select `frontend` |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |
| **Install Command** | `npm install` |

### 4.3 Configure Frontend Environment Variables
Expand the **Environment Variables** section and add:

| Key | Value | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `https://adshield-backend.onrender.com` | Your deployed Render backend URL (no trailing slash) |

> [!TIP]
> Do NOT set `GEMINI_API_KEY` or `SAFE_BROWSING_API_KEY` on Vercel. Frontend clients must never hold external provider credentials.

### 4.4 Deploy
Click **Deploy**. Vercel will compile the TypeScript application, optimize assets, and assign a production URL:
`https://adshield.vercel.app`

### 4.5 Update Render CORS Setting
Return to your [Render Dashboard](https://dashboard.render.com) for `adshield-backend`:
1. Navigate to **Environment**.
2. Update `CORS_ORIGINS` to include your new Vercel domain:
   ```env
   CORS_ORIGINS=https://adshield.vercel.app,http://localhost:5173
   ```
3. Save changes (Render will automatically redeploy the service).

---

## 5. Step 4: End-to-End Verification & Health Checks

Once both services are deployed, perform these verification checks:

### 5.1 Backend Direct Health Check
Visit in your browser or curl:
`https://adshield-backend.onrender.com/api/health`

Expected response:
```json
{
  "status": "healthy",
  "service": "AdShield Detection API",
  "version": "1.0.0",
  "gemini_configured": true,
  "gemini_model": "gemini-3.5-flash-lite",
  "safe_browsing_configured": true,
  "tesseract_available": true,
  "tesseract_version": "5.3.0",
  "timestamp": "2026-11-14T12:00:00.000000Z"
}
```
*(Notice: No actual secret keys or credentials are leaked in the response).*

### 5.2 Frontend UI Integration Check
1. Open your Vercel URL: `https://adshield.vercel.app`.
2. Check the top navigation bar:
   - The status indicator should display a glowing green **"Backend Online"** badge.
   - Hovering over the badge reveals the subsystems popover displaying active statuses for Gemini AI, Google Safe Browsing, and Tesseract OCR.
3. Test all 3 modalities:
   - **Text Scanner:** Click **Sample Scam** → Click **Analyse Advertisement**. Confirm the risk score and threat indicators render cleanly.
   - **Image Scanner:** Upload an advertisement banner. Confirm OCR text extraction and Gemini visual findings appear in the report.
   - **URL Scanner:** Click **Sample Phishing URL** → Click **Analyse Advertisement**. Confirm Google Safe Browsing and URL heuristics display.

---

## 6. Step 5: Zero-Database Ephemeral Architecture Notice

AdShield deliberately adheres to a **Zero-Persistence Privacy Standard**:

1. **No External Database:** The application uses no SQL (PostgreSQL, MySQL, SQLite), MongoDB, Firebase, or Supabase.
2. **Ephemeral Caches:**
   - Safe Browsing negative and positive URL query cache is stored in Python in-memory dictionaries with TTL.
   - Model health, cooldown timers, and fallback counters are tracked in-memory inside `gemini_model_manager.py`.
   - When the Render backend process restarts (e.g. idle spin-down or redeploy), in-memory caches and cooldown timers reset cleanly to their initial operational states.
3. **Frontend Session Storage:**
   - Scan history is maintained strictly within active React browser state.
   - Navigating away, clearing session, or closing the browser tab immediately purges scan records.

---

## 7. Troubleshooting & Common Questions

### Q1: CORS error in browser console (`Access to fetch has been blocked by CORS policy`)
- **Cause:** Your Vercel frontend URL is not included in Render's `CORS_ORIGINS` environment variable.
- **Fix:** In Render Dashboard → Environment, add your exact Vercel URL (e.g. `https://adshield.vercel.app`) to `CORS_ORIGINS`. Note: AdShield backend also allows `https://*.vercel.app` preview branches via regex.

### Q2: Tesseract OCR reports `tesseract_available: false` on Render
- **Cause:** The Docker container did not install `tesseract-ocr` or `TESSERACT_CMD` points to an invalid path.
- **Fix:** Verify `backend/Dockerfile` contains `apt-get install -y tesseract-ocr tesseract-ocr-eng` and `TESSERACT_CMD=/usr/bin/tesseract`.

### Q3: Render Free Tier delay on first request
- **Cause:** Render free tier web services spin down after 15 minutes of inactivity. The initial wake-up request may take ~30–50 seconds.
- **Fix:** Subsequent requests respond in milliseconds. For instant response, upgrade the Render service to the "Starter" tier or set up a free uptime monitor (e.g., UptimeRobot) pinging `/api/health` every 10 minutes.

### Q4: Gemini API 429 Quota Exhaustion
- **Cause:** Free tier Gemini daily quota (20 requests/day) has been reached.
- **Fix:** AdShield's automatic fallback manager seamlessly switches to configured fallback models (`gemini-3.1-flash-lite`, `gemini-2.5-flash-lite`). If all models are exhausted, graceful degradation preserves Google Safe Browsing and heuristic analysis without crashing.
