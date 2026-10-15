# Deploy PeerNest on Vercel

This deployment keeps the existing Flask + Jinja frontend and changes the hosted database to PostgreSQL. The app uses SQLite only for local development when `DATABASE_URL` is absent.

## 1. Create a hosted PostgreSQL database

1. Create a project at https://neon.tech/ (or use another hosted PostgreSQL provider).
2. In the provider dashboard, copy the PostgreSQL connection string. Use the pooled connection string if the provider recommends it for serverless apps.
3. Keep the connection string private. It should include the provider's SSL option, commonly `sslmode=require`.

## 2. Set Vercel environment variables

In Vercel, open the PeerNest project → **Settings → Environment Variables** and add:

- `DATABASE_URL` = the PostgreSQL connection string.
- `PEERNEST_SECRET_KEY` = a long random secret.

To generate a secret locally in PowerShell, run:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the generated value into Vercel. Do not commit it to GitHub. Enable it for Production and Preview environments as appropriate. Redeploy after adding or changing variables.

## 3. Import the GitHub repository

1. Open https://vercel.com/new.
2. Import the GitHub repository containing PeerNest.
3. Keep the project root at the repository root (the folder containing `app.py` and `requirements.txt`).
4. Vercel should detect Flask automatically. The project uses root-level `app.py`, `templates/`, and `static/`; no custom `vercel.json` is normally required for current Flask support.
5. Deploy.

## 4. Static files

The existing templates use Flask's static URL helper:

```html
<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
<script defer src="{{ url_for('static', filename='app.js') }}"></script>
```

Keep `static/style.css`, `static/app.js`, and `templates/` at the project root beside `app.py`. Do not hard-code local filesystem paths or use `file:///` URLs. Flask serves the CSS and JavaScript through its `static` endpoint.

## 5. Verify the deployment

1. Open the Vercel deployment URL.
2. Register two accounts.
3. Complete their profiles and add complementary skills.
4. Test Discover, connection requests, accepted connections, messages, session planning, completion, reviews, and progress.
5. Refresh the page and verify records persist.

The app creates its tables in PostgreSQL at startup. A newly created database starts empty. `seed_demo.py` can create the demo accounts if run with `DATABASE_URL` set to the hosted database, but for a public deployment it is safer to register your own demo accounts through the website and avoid sharing default demo passwords.

## 6. Common problems

- **`DATABASE_URL is missing`**: Add the variable in Vercel project settings and redeploy.
- **Database connection/SSL error**: Copy the full provider connection string again; preserve its SSL parameters. Prefer the provider's pooled connection string if recommended.
- **CSS or JS missing**: Confirm the root-level `static/` folder is committed to GitHub and that templates use `url_for('static', filename=...)`.
- **Login does not persist**: Ensure `PEERNEST_SECRET_KEY` is set and stable across deployments; do not change it between requests.
- **No users appear**: PostgreSQL is a separate empty database; local SQLite records are not automatically migrated.

## Data migration note

This setup creates the schema in PostgreSQL but does not copy any records from `data/peernest.db`. If you already have local accounts or messages that you need to preserve, migrate those records separately before using the hosted site.
