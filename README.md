# UniPrep

A full-stack study preparation platform with a Django backend and a Vite/React frontend.

## Overview

- **Backend:** Django REST API with JWT auth, multi-app architecture, channels support, and AI integrations.
- **Frontend:** React + Vite UI for admin, student workflows, and analytics.
- **Purpose:** Manage exam prep content, exam blueprints, collaborative study features, and RAG-based study materials.

## Repository structure

- `uniprep_backend/` - Django backend app and API.
- `uniprep-frontend/` - React/Vite frontend application.
- `venv/` - local Python virtual environment (ignored by git).

## Features

- User authentication and custom user model
- Exam question management and blueprint generation
- Analytics and collaboration tools
- RAG search and AI-assisted study material generation
- WebSocket support with Django Channels

## Getting started

### Backend setup

1. Create a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/Scripts/activate
   ```
2. Install backend dependencies:
   ```bash
   pip install -r uniprep_backend/requirements.txt
   ```
3. Create a `.env` file in `uniprep_backend/` and add required variables.
4. Apply migrations:
   ```bash
   python uniprep_backend/manage.py migrate
   ```
5. Run the development server:
   ```bash
   python uniprep_backend/manage.py runserver
   ```

### Frontend setup

1. Install dependencies:
   ```bash
   cd uniprep-frontend
   npm install
   ```
2. Run the frontend dev server:
   ```bash
   npm run dev
   ```

## Environment variables

Create `uniprep_backend/.env` with the following values:

```dotenv
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=uniprep_db
DB_USER=root
DB_PASSWORD=uniprep1
DB_HOST=localhost
DB_PORT=3306
REDIS_URL=redis://localhost:6379/0
GEMINI_API_KEY=
QDRANT_URL=
QDRANT_API_KEY=
QDRANT_COLLECTION_NAME=uniprep_study_materials
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openrouter/free
OPENROUTER_SITE_URL=http://localhost:5173
OPENROUTER_APP_NAME=UniPrep AI
```

> `uniprep_backend/.env` is ignored by git and should never be committed.

## Notes

- The repo is configured to ignore local environment files and virtual environments.
- If you are deploying, set `DEBUG=False` and configure allowed hosts.
- Rotate credentials if any secret values were previously pushed.

## Useful commands

- Backend migrations: `python uniprep_backend/manage.py migrate`
- Create superuser: `python uniprep_backend/manage.py createsuperuser`
- Frontend build: `npm run build`
- Run frontend preview: `npm run preview`

## Contact

For more details, inspect the backend app folders and frontend pages in the repository.
