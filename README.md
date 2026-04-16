# DataCart AI

Interactive product discovery app for budget shopping queries like `phones under 10k` or `laptops under 30000`.

## What It Does

- Natural-language product search
- Budget-aware filtering and ranking
- Interactive landing page and search dashboard
- Product detail modal with fit explanation
- Saved list and radar-style comparison
- CSV dataset export
- Price-drop reminder storage
- Live outbound marketplace search links

## Stack

- Frontend: HTML, CSS, JavaScript, Chart.js
- Backend: FastAPI, Python

## Run Locally

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend

Serve the `frontend` folder with any static server. One simple option:

```bash
cd frontend
python -m http.server 5173
```

Then open:

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8000`

## Project Structure

```text
backend/
  app/
    api/routes.py
    catalog.py
    main.py
frontend/
  app.js
  index.html
  style.css
docker-compose.yml
```
