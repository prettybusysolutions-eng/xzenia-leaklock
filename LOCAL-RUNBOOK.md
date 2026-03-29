# LeakLock Local Deployment Runbook

## Setup

1. **Clone repo** and enter project directory:
   ```bash
   git clone <repo-url> && cd projects/xzenia-saas
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Copy or create `.env` file**
   - Ensure you have a `.env` file with at least:
     - `FLASK_SECRET_KEY`
     - Optionally DB, Stripe secrets

## Running the App (Production/WSGI)

1. **Via Gunicorn:**
   ```bash
   source .venv/bin/activate
   gunicorn dashboard:app -w 2 --bind 0.0.0.0:5050 --timeout 90 --log-level info
   ```
   - This will bind to port 5050 and serve the app using WSGI production server.

2. **Health Check/Testing:**
   - Verify health endpoint:
     ```bash
     curl http://localhost:5050/health   # should return OK
     ```
   - Root URL (`/`) and landing page (static)

## App Structure
- `app.py`: Application factory (for Flask/Gunicorn)
- `dashboard.py`: Entrypoint for CLI/run (used by Gunicorn Procfile)
- `routes/`: Blueprints for API, OAuth, scanner, etc
- `models/`, `services/`, `templates/`: Core logic
- `requirements.txt`: All runtime dependencies

## Main Endpoints
- `/health`: Health check (returns OK)
- `/`: Home page (landing)
- `/upload`: Upload billing file
- `/results/<id>`: Scan results
- `/pricing`, `/report/<id>`, `/privacy`, `/terms`: Info

## Common Issues
- **Port 5050 may be busy:** Stop other Flask instances first: `lsof -i :5050`
- **DB creds missing:** Ensure local DB is accessible/configured (`nexus` default)
- **Dependencies missing:** Run setup step above
- **Environment:** Python 3.9–3.11 tested; 3.14 may need updated C extensions for some deps

## Troubleshooting
- **Logs:**
  - Gunicorn output: stderr/stdout in terminal
  - Application logs: `logs/` directory
- **Live reload (dev):**
  ```bash
  FLASK_APP=dashboard.py FLASK_ENV=development flask run
  ```
- **Testing models etc:** See `tests/` folder

---
For deployments (Heroku, Render, etc), see example `Procfile`.
