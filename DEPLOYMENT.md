# EcoSentinel Deployment Guide (Render)

This repository is pre-configured with **Render Blueprints** (`render.yaml`) to deploy both the **FastAPI Reasoning Backend** and the **React + Vite Dashboard** with one click.

---

## Method 1: Automatic One-Click Deploy via Render Blueprint (Recommended)

1. Go to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** $\to$ **Blueprint**.
3. Connect your GitHub repository (`akshit130108/Bit-n-Build` or your fork).
4. Render will detect `render.yaml` and configure both services automatically:
   - **`ecosentinel-backend`**: Python Web Service running `uvicorn main:app --host 0.0.0.0 --port $PORT` on the `/health` endpoint.
   - **`ecosentinel-dashboard`**: React static site building with `npm install && npm run build` and publishing `dist`.
5. Click **Apply**.
6. Both services will build and deploy. Once complete, Render provides your live URLs!

---

## Method 2: Manual Deploy on Render

If you prefer to configure each service manually:

### Step 1: Deploy Backend (Web Service)
1. In Render, click **New +** $\to$ **Web Service**.
2. Connect `akshit130108/Bit-n-Build`.
3. Settings:
   - **Name**: `ecosentinel-backend`
   - **Region**: Any (e.g. Oregon or Frankfurt)
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
   - **Health Check Path**: `/health`
4. Optional Environment Variables:
   - `GFW_API_TOKEN`: *(Optional)* Your Global Fishing Watch API token.
5. Click **Create Web Service**. Copy your backend URL (e.g., `https://ecosentinel-backend.onrender.com`).

### Step 2: Deploy Frontend (Static Site)
1. In Render, click **New +** $\to$ **Static Site**.
2. Connect `akshit130108/Bit-n-Build`.
3. Settings:
   - **Name**: `ecosentinel-dashboard`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
4. Environment Variables:
   - `VITE_API_URL`: `https://<your-backend-name>.onrender.com`
5. Redirects / Rewrites:
   - Add a rewrite rule: Source `/*` $\to$ Destination `/index.html` (Status: `Rewrite`).
6. Click **Create Static Site**.

---

## Method 3: Alternative - Vercel for Frontend

If you want the dashboard on Vercel:
1. Go to [Vercel](https://vercel.com/new).
2. Import `akshit130108/Bit-n-Build`.
3. Set **Root Directory** to `frontend`.
4. Add Environment Variable:
   - `VITE_API_URL` = `https://<your-backend-url>.onrender.com`
5. Click **Deploy**.

---

## Verifying the Live Deployment

1. Open `https://<your-backend>.onrender.com/health` $\to$ Expect `{"status": "healthy"}`.
2. Open `https://<your-dashboard>.onrender.com` $\to$ The Leaflet map should load, and the connection status should indicate **BACKEND ONLINE**.
3. Click **[ 🌲 Simulate Chainsaw ]** $\to$ A new land logging event should appear on the map and in the incident list.
4. Click **[ 🚨 Seed Recurrence Spike ]** $\to$ 3 historical incidents will be seeded, and the 4th incident will surge to `HIGH` risk with `WAITING_FOR_APPROVAL` status.
5. Click **[ ✓ APPROVE & DISPATCH ]** $\to$ The human gate status updates to `APPROVED` and action changes to `DISPATCHED`.
