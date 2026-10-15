# PeerNest — Quick Hackathon Demo Guide

## 1. Start the app

Open this folder in VS Code, then run these commands in the terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python seed_demo.py
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

If PowerShell blocks virtual-environment activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 2. Demo accounts

Both accounts use the same demo password. These are sample accounts, not real users.

| Username | Password | Skills taught | Skills to learn |
|---|---|---|---|
| `alex_demo` | `Demo12345!` | Python, C | UI/UX Design, Figma |
| `sam_demo` | `Demo12345!` | UI/UX Design, Figma | Python, C |

Both sample profiles use Arya College of Engineering to demonstrate the same-college matching bonus.

## 3. Suggested 3–5 minute walkthrough

1. **Dashboard:** Sign in as `alex_demo`; show profile summary, progress, and recommended students.
2. **Discover:** Open Discover and point out Sam's complementary skills and match score. Explain that matching is rule-based, not AI-powered.
3. **Connection requests:** Log out, sign in as `sam_demo`, open Requests, and accept Alex's pending request.
4. **Messaging:** Open Connections and send Alex a short message.
5. **Session planner:** Log in as Alex again, open Sessions, choose Sam, enter `Python basics`, choose Mutual exchange or Free mentoring, set a date/time, and send the request.
6. **Accept session:** Log in as Sam and accept the request under Sessions.
7. **Progress and reviews:** Start/complete the session and show the XP/progress changes. Then optionally leave a star rating.

Use two separate browser profiles (or one normal window and one incognito window) to avoid repeatedly logging in and out. If using two browser profiles, open the app URL in both and sign into a different demo account in each.

## 4. File map for judges

- `app.py` — Flask routes, database schema, authentication, matchmaking, sessions, messaging, reviews, and XP logic.
- `templates/` — HTML pages rendered by Flask/Jinja.
- `static/style.css` — Sage + Cream responsive styling.
- `static/app.js` — small frontend interactions.
- `seed_demo.py` — creates the two presentation accounts and a pending connection request.
- `data/peernest.db` — generated automatically; not included in the ZIP.

## 5. Be accurate about scope

Implemented in this MVP: profiles, skill lists, rule-based discovery, connection requests, messaging between accepted connections, session planning, progress notes, reviews, XP, levels, and badges.

Future scope: shared resource uploads/workspace, email verification, password recovery, live chat updates, stronger moderation, and production deployment hardening.

The demo accounts are for local demonstration only. Change the development secret key and add further protections before any public deployment.
