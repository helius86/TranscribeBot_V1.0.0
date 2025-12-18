# Chapter Generator Frontend

React + Vite + TypeScript + TailwindCSS UI for the Chapter Generator backend.

## Setup
```bash
cd frontend
npm install --cache ../.npm-cache   # optional cache path to avoid permission issues
```

## Run
```bash
npm run dev
```
By default the app points to `http://localhost:8000`. Override with an env var:
```
VITE_API_BASE_URL=http://localhost:8000
```

## Routes
- `/` — create project and paste/upload transcript text.
- `/projects/:id` — view transcript, edit/regenerate chapters, export Bilibili text.
