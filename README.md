# PeerNest

PeerNest is a peer-to-peer skill and knowledge exchange platform for students.

## Stack
- Frontend: HTML, CSS, JavaScript, Jinja templates
- Backend: Python + Flask
- Local development database: SQLite
- Hosted deployment database: PostgreSQL (Neon recommended)

## Run locally with SQLite

Python 3.10+ is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000. When `DATABASE_URL` is not set, the app uses `data/peernest.db` for local development.

To create sample demo accounts locally:

```powershell
.\.venv\Scripts\python.exe seed_demo.py
```

Demo credentials: `alex_demo` / `Demo12345!` and `sam_demo` / `Demo12345!`. Use these only for local demonstrations.

## Deploy to Vercel with PostgreSQL

See [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md) for the step-by-step instructions.

When `DATABASE_URL` is set, the app uses PostgreSQL instead of SQLite. Do not rely on a local SQLite file for hosted persistent data.

Required Vercel environment variables:
- `DATABASE_URL`: PostgreSQL connection string from Neon (must include SSL parameters supplied by Neon).
- `PEERNEST_SECRET_KEY`: a long random secret used to sign Flask sessions.

The app's schema is created automatically when it starts. A newly provisioned PostgreSQL database starts empty; local SQLite data is not automatically copied to it.

## Features
- Sign-up/login with hashed passwords and Flask sessions
- Student profiles and teaching/learning skills
- Student discovery and rule-based matching
- Connection requests and accepted connections
- Private messaging between accepted connections
- Session planning and status management
- Session notes, reviews, XP, levels, badges and progress tracking
- Responsive Sage + Cream interface

## Current limitations
This is a hackathon MVP. Email verification, password recovery, live chat updates, moderation/reporting, and verified college membership are not implemented. Matching is rule-based, not AI-powered. Set production secrets and configure suitable access controls before public use.
