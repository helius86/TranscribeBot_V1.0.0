# Chapter Generator (MVP)

Local-first web app to parse timestamped transcripts, generate chapters, and export in Bilibili format.

## Backend (FastAPI + SQLite)

### Setup
1. Create and activate a Python 3.10+ virtual environment.
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. (Optional) Copy the example env file and adjust:
   ```bash
   cp .env.example .env
   ```
   - Set `VOLCENGINE_API_KEY` (or `ARK_API_KEY`) / `VOLCENGINE_MODEL` if you want real LLM-based chapter generation (defaults to stub when missing).

### Run
```bash
uvicorn backend.main:app --reload
```
API will be available at `http://localhost:8000` with docs at `/docs`.

## Frontend

React + Vite + TypeScript + Tailwind will live in `frontend/` (to be added). Basic flow:
- Install dependencies (`npm install` or `yarn`) inside `frontend/`.
- Start dev server (`npm run dev`).

## Notes
- Database defaults to `sqlite:///./app.db` in the project root. Override via `DATABASE_URL` in `.env`.
- Stubbed LLM helpers live in `backend/services/llm_chapter_generator.py` and can be swapped for real APIs later.

## Quick start (one command per terminal)
- Terminal 1 (backend):
  ```bash
  ./start_all.sh backend
  ```
- Terminal 2 (frontend):
  ```bash
  ./start_all.sh frontend
  ```
