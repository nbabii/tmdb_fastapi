# TMDB FastAPI Project

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python run.py
```

Or directly with uvicorn:

```bash
uvicorn app.main:app --reload
```

API docs available at: http://localhost:8000/api/v1/openapi.json  
Interactive docs (Swagger): http://localhost:8000/docs  
ReDoc: http://localhost:8000/redoc

## Project Structure

```
tmdb/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/   # Route handlers
│   │       └── router.py    # API router aggregator
│   ├── core/
│   │   └── config.py        # App settings (env-based)
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── services/            # Business logic
│   └── main.py              # FastAPI app factory
├── tests/
├── .env.example
├── requirements.txt
└── run.py
```
