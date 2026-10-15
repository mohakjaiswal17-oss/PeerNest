# PeerNest

A Flask + SQLite MVP for a free peer-to-peer skill exchange platform for college students and recent graduates.

## Features
- Signup/login with unique email and username, hashed passwords, Flask sessions
- Student profile with college, qualification, branch/year, bio, GitHub, LinkedIn and portfolio links
- Skills to teach and skills to learn
- Discovery search, skill categories, match score and same-college recommendations
- Contact requests and accepted connections
- Persistent private messages for connected students
- Session requests for mutual exchange or free mentoring
- Session accept/decline/start/complete/cancel actions
- Progress notes and final session reviews
- Separate teaching and learning XP, levels, and milestone badges
- Responsive Sage + Cream design

## Run locally (Python 3.10+)
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000. SQLite database is created automatically in `data/peernest.db`.

## Test the flow
1. Register two different accounts.
2. Complete both profiles and add skills.
3. Use Discover to send a contact request; sign in to the other account and accept it from Requests.
4. Send messages in Connections.
5. Request a session, accept it as the partner, then complete it.
6. Review the other participant and check Progress for XP and badges.

## Limitations / safety
This is a local hackathon MVP, not a production-ready deployment. Before deployment, set a long random `PEERNEST_SECRET_KEY` environment variable; the development fallback is not suitable for production. Example PowerShell: `$env:PEERNEST_SECRET_KEY = "replace-with-a-long-random-secret"`.
Email verification, password reset, live chat updates, rate limiting, moderation/reporting tools, and verified college membership are not included. College-based recommendations use user-entered institution names and do not verify enrollment. Private email and phone details are not shown on public profiles.


## Presentation demo

For prefilled sample accounts and a step-by-step walkthrough, see [DEMO_GUIDE.md](DEMO_GUIDE.md). Run `python seed_demo.py` after installing requirements to create the demo accounts.
