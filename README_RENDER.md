Deploying to Render

Overview
- This project has two parts:
  - `backend/` — Flask API that uses Gemini AI and handles file uploads
  - `frontend/` — Vite React app

Backend (Render - Web Service)
1. In Render, create a new "Web Service".
2. Connect your GitHub repo and select the `main` branch.
3. Set the "Root Directory" to `backend`.
4. Build command: `pip install -r requirements.txt` (Render will auto-install from `requirements.txt`)
5. Start command: `gunicorn app:app -b 0.0.0.0:$PORT` (Procfile is provided)
6. Add an Environment Variable `GEMINI_API_KEY` in Render (your API key from Google).
7. Optional: set `FLASK_DEBUG` to `False`.

Frontend (Render - Static Site)
1. Create a new "Static Site" on Render.
2. Connect your GitHub repo and select the `main` branch.
3. Set the "Root Directory" to `frontend`.
4. Build command: `npm install && npm run build` (or `yarn && yarn build`).
5. Publish directory: `dist` (Vite outputs to `dist` by default).

CORS and API URL
- Ensure the frontend calls the backend URL provided by Render (use full URL or environment variable).
- The backend has CORS enabled for all origins; consider restricting it in production.

Notes
- `backend/.env` is ignored and will not be pushed to your repo.
- The backend uses `PORT` provided by Render; `gunicorn` will bind to that port.
- If you prefer Docker, create a Dockerfile for each service and use Render's Docker deployment.

Commands (local testing)
```bash
# Run backend locally
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
export GEMINI_API_KEY="your_key"
python backend/app.py

# Build frontend locally
cd frontend
npm install
npm run build
```
