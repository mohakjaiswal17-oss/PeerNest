import os, re, sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from functools import wraps
from urllib.parse import urlparse
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, abort
from werkzeug.security import generate_password_hash, check_password_hash

ROOT = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "data", "peernest.db")
app = Flask(__name__)
secret_key = os.environ.get("PEERNEST_SECRET_KEY")
if os.environ.get("VERCEL") and not secret_key:
    raise RuntimeError("Set PEERNEST_SECRET_KEY in Vercel Environment Variables before deploying.")
app.config.update(
    SECRET_KEY=secret_key or "dev-only-change-this-secret",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("VERCEL")),
)

class PgDatabase:
    """Small adapter preserving the execute/fetch API used by this Flask app."""
    def __init__(self, connection):
        self.connection = connection

    @staticmethod
    def _sql(statement):
        # The app's parameterized SQL uses SQLite-style ? placeholders.
        # psycopg2 uses %s placeholders.
        return statement.replace("?", "%s")

    def execute(self, statement, params=()):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(self._sql(statement), params)
        return cursor

    def executemany(self, statement, params):
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        cursor.executemany(self._sql(statement), params)
        return cursor

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


class SQLiteDatabase:
    """SQLite adapter used for local development when DATABASE_URL is not set."""
    def __init__(self, connection):
        self.connection = connection

    def execute(self, statement, params=()):
        return self.connection.execute(statement, params)

    def executemany(self, statement, params):
        return self.connection.executemany(statement, params)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


def db():
    if "db" not in g:
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            g.db = PgDatabase(psycopg2.connect(database_url))
        else:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            connection = sqlite3.connect(DB_PATH)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            g.db = SQLiteDatabase(connection)
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    conn = g.pop("db", None)
    if conn:
        conn.close()


POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (CURRENT_TIMESTAMP::text)
);
CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_uq ON users (LOWER(email));
CREATE UNIQUE INDEX IF NOT EXISTS users_username_lower_uq ON users (LOWER(username));
CREATE TABLE IF NOT EXISTS profiles (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    full_name TEXT DEFAULT '', college TEXT DEFAULT '', qualification TEXT DEFAULT '',
    branch TEXT DEFAULT '', study_status TEXT DEFAULT 'Student', study_year TEXT DEFAULT '',
    graduation_year TEXT DEFAULT '', bio TEXT DEFAULT '', github_url TEXT DEFAULT '',
    linkedin_url TEXT DEFAULT '', portfolio_url TEXT DEFAULT '', availability TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS skills (
    id BIGSERIAL PRIMARY KEY, name TEXT NOT NULL, category TEXT DEFAULT 'Other'
);
CREATE UNIQUE INDEX IF NOT EXISTS skills_name_lower_uq ON skills (LOWER(name));
CREATE TABLE IF NOT EXISTS user_skills (
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    skill_id BIGINT REFERENCES skills(id) ON DELETE CASCADE,
    skill_type TEXT CHECK(skill_type IN ('teach','learn')),
    level TEXT DEFAULT 'Beginner',
    PRIMARY KEY(user_id,skill_id,skill_type)
);
CREATE TABLE IF NOT EXISTS contact_requests (
    id BIGSERIAL PRIMARY KEY,
    sender_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    recipient_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL, status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (CURRENT_TIMESTAMP::text),
    UNIQUE(sender_id,recipient_id)
);
CREATE TABLE IF NOT EXISTS connections (
    id BIGSERIAL PRIMARY KEY,
    user_a BIGINT REFERENCES users(id) ON DELETE CASCADE,
    user_b BIGINT REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT DEFAULT (CURRENT_TIMESTAMP::text),
    UNIQUE(user_a,user_b), CHECK(user_a < user_b)
);
CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    connection_id BIGINT REFERENCES connections(id) ON DELETE CASCADE,
    sender_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    body TEXT NOT NULL, created_at TEXT DEFAULT (CURRENT_TIMESTAMP::text)
);
CREATE TABLE IF NOT EXISTS sessions (
    id BIGSERIAL PRIMARY KEY,
    requester_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    partner_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    skill TEXT NOT NULL, model TEXT CHECK(model IN ('exchange','mentoring')),
    topic TEXT DEFAULT '', proposed_at TEXT DEFAULT '', duration INTEGER DEFAULT 60,
    status TEXT DEFAULT 'pending', created_at TEXT DEFAULT (CURRENT_TIMESTAMP::text),
    completed_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS reviews (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT REFERENCES sessions(id) ON DELETE CASCADE,
    reviewer_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    reviewee_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER CHECK(rating BETWEEN 1 AND 5), body TEXT DEFAULT '',
    created_at TEXT DEFAULT (CURRENT_TIMESTAMP::text), UNIQUE(session_id,reviewer_id)
);
CREATE TABLE IF NOT EXISTS session_feedback (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT REFERENCES sessions(id) ON DELETE CASCADE,
    author_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    body TEXT NOT NULL, created_at TEXT DEFAULT (CURRENT_TIMESTAMP::text)
);
CREATE TABLE IF NOT EXISTS xp_events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    session_id BIGINT REFERENCES sessions(id) ON DELETE CASCADE,
    event_key TEXT NOT NULL, points INTEGER NOT NULL,
    created_at TEXT DEFAULT (CURRENT_TIMESTAMP::text),
    UNIQUE(user_id,session_id,event_key)
);
CREATE TABLE IF NOT EXISTS user_badges (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    badge_key TEXT NOT NULL, earned_at TEXT DEFAULT (CURRENT_TIMESTAMP::text),
    UNIQUE(user_id,badge_key)
);
"""


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_uq ON users (LOWER(email));
CREATE UNIQUE INDEX IF NOT EXISTS users_username_lower_uq ON users (LOWER(username));
CREATE TABLE IF NOT EXISTS profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    full_name TEXT DEFAULT '', college TEXT DEFAULT '', qualification TEXT DEFAULT '',
    branch TEXT DEFAULT '', study_status TEXT DEFAULT 'Student', study_year TEXT DEFAULT '',
    graduation_year TEXT DEFAULT '', bio TEXT DEFAULT '', github_url TEXT DEFAULT '',
    linkedin_url TEXT DEFAULT '', portfolio_url TEXT DEFAULT '', availability TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS skills (id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT DEFAULT 'Other');
CREATE UNIQUE INDEX IF NOT EXISTS skills_name_lower_uq ON skills (LOWER(name));
CREATE TABLE IF NOT EXISTS user_skills (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    skill_id INTEGER REFERENCES skills(id) ON DELETE CASCADE,
    skill_type TEXT CHECK(skill_type IN ('teach','learn')),
    level TEXT DEFAULT 'Beginner', PRIMARY KEY(user_id,skill_id,skill_type)
);
CREATE TABLE IF NOT EXISTS contact_requests (
    id INTEGER PRIMARY KEY, sender_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    recipient_id INTEGER REFERENCES users(id) ON DELETE CASCADE, message TEXT NOT NULL,
    status TEXT DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sender_id,recipient_id)
);
CREATE TABLE IF NOT EXISTS connections (
    id INTEGER PRIMARY KEY, user_a INTEGER REFERENCES users(id) ON DELETE CASCADE,
    user_b INTEGER REFERENCES users(id) ON DELETE CASCADE, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_a,user_b), CHECK(user_a < user_b)
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY, connection_id INTEGER REFERENCES connections(id) ON DELETE CASCADE,
    sender_id INTEGER REFERENCES users(id) ON DELETE CASCADE, body TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY, requester_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    partner_id INTEGER REFERENCES users(id) ON DELETE CASCADE, skill TEXT NOT NULL,
    model TEXT CHECK(model IN ('exchange','mentoring')), topic TEXT DEFAULT '',
    proposed_at TEXT DEFAULT '', duration INTEGER DEFAULT 60, status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP, completed_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY, session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    reviewer_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    reviewee_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER CHECK(rating BETWEEN 1 AND 5), body TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(session_id,reviewer_id)
);
CREATE TABLE IF NOT EXISTS session_feedback (
    id INTEGER PRIMARY KEY, session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES users(id) ON DELETE CASCADE, body TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS xp_events (
    id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
    event_key TEXT NOT NULL, points INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id,session_id,event_key)
);
CREATE TABLE IF NOT EXISTS user_badges (
    id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    badge_key TEXT NOT NULL, earned_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id,badge_key)
);
"""


def init_db():
    d = db()
    schema = POSTGRES_SCHEMA if os.environ.get("DATABASE_URL") else SQLITE_SCHEMA
    for statement in schema.split(";"):
        if statement.strip():
            d.execute(statement)
    d.executemany(
        "INSERT INTO skills(name,category) VALUES(?,?) ON CONFLICT DO NOTHING",
        [
            ("Python","Programming"),("C","Programming"),("C++","Programming"),
            ("Java","Programming"),("JavaScript","Programming"),("HTML & CSS","Web Development"),
            ("Flask","Web Development"),("SQL","Database"),("UI/UX Design","Design"),
            ("Figma","Design"),("Graphic Design","Design"),("Video Editing","Creative"),
            ("Public Speaking","Communication"),("Excel","Productivity"),("DSA","Programming"),
            ("Photography","Creative"),("Machine Learning","AI & Data"),("Git & GitHub","Tools")
        ]
    )
    d.commit()

@app.before_request
def load_user():
    g.user = None
    if session.get("uid"):
        g.user = db().execute("""SELECT u.id,u.email,u.username,p.full_name,p.college,p.qualification,p.study_year
          FROM users u LEFT JOIN profiles p ON p.user_id=u.id WHERE u.id=?""",(session["uid"],)).fetchone()

@app.context_processor
def globals_for_templates():
    return {"current_user":g.get("user"),"badge_labels":{"first_lesson":"First Lesson","knowledge_sharer":"Knowledge Sharer","curious_mind":"Curious Mind","exchange_pro":"Skill Exchange Pro"}}

def login_required(fn):
    @wraps(fn)
    def wrapped(*args,**kwargs):
        if not g.user:
            flash("Please log in to continue.","info")
            return redirect(url_for("login",next=request.path))
        return fn(*args,**kwargs)
    return wrapped

def profile(uid):
    return db().execute("SELECT u.id,u.email,u.username,u.created_at,p.* FROM users u JOIN profiles p ON p.user_id=u.id WHERE u.id=?",(uid,)).fetchone()

def skills(uid, kind=None):
    sql="SELECT s.id,s.name,s.category,us.skill_type,us.level FROM user_skills us JOIN skills s ON s.id=us.skill_id WHERE us.user_id=?"
    args=[uid]
    if kind: sql+=" AND us.skill_type=?"; args.append(kind)
    return db().execute(sql+" ORDER BY s.name",args).fetchall()

def connection(uid, other):
    a,b=sorted((uid,other))
    return db().execute("SELECT * FROM connections WHERE user_a=? AND user_b=?",(a,b)).fetchone()

def create_connection(uid, other):
    a,b=sorted((uid,other))
    db().execute("INSERT INTO connections(user_a,user_b) VALUES(?,?) ON CONFLICT DO NOTHING",(a,b))

def valid_url(value, domain=None):
    try:
        p=urlparse(value)
        return p.scheme in ("http","https") and bool(p.netloc) and (not domain or p.netloc.lower().split(":")[0]==domain or p.netloc.lower().endswith("."+domain))
    except Exception: return False

def xp(uid, key=None):
    q="SELECT COALESCE(SUM(points),0) n FROM xp_events WHERE user_id=?"
    args=[uid]
    if key: q+=" AND event_key=?"; args.append(key)
    return db().execute(q,args).fetchone()["n"]

def level(points):
    stages=[(0,"Level 1","Beginner"),(100,"Level 2","Helper"),(300,"Level 3","Mentor"),(650,"Level 4","Guide"),(1100,"Level 5","Community Star")]
    cur=stages[0]; nxt=None
    for i,s in enumerate(stages):
        if points>=s[0]: cur=s; nxt=stages[i+1] if i+1<len(stages) else None
    return {"level":cur[1],"title":cur[2],"points":points,"next":nxt[0] if nxt else None,"remaining":max(0,nxt[0]-points) if nxt else 0,"progress":min(100,int((points-cur[0])/(nxt[0]-cur[0])*100)) if nxt else 100}

def xp_summary(uid):
    return {"teaching":level(xp(uid,"teach")),"learning":level(xp(uid,"learn")),"total":xp(uid)}

def badges(uid):
    d=db()
    counts={k:d.execute("SELECT COUNT(*) n FROM xp_events WHERE user_id=? AND event_key=?",(uid,k)).fetchone()["n"] for k in ("teach","learn","exchange")}
    for key, ok in [("first_lesson",counts["teach"]+counts["learn"]>=1),("knowledge_sharer",counts["teach"]>=5),("curious_mind",counts["learn"]>=5),("exchange_pro",counts["exchange"]>=5)]:
        if ok: d.execute("INSERT INTO user_badges(user_id,badge_key) VALUES(?,?) ON CONFLICT DO NOTHING",(uid,key))
    d.commit()
    return d.execute("SELECT badge_key,earned_at FROM user_badges WHERE user_id=? ORDER BY earned_at DESC",(uid,)).fetchall()

def suggestions(uid, q="", category="", limit=50):
    me=profile(uid); teach={s["id"] for s in skills(uid,"teach")}; learn={s["id"] for s in skills(uid,"learn")}
    people=db().execute("""SELECT u.id,u.username,p.full_name,p.college,p.qualification,p.branch,p.study_year,p.graduation_year,p.study_status,p.bio,p.github_url,p.linkedin_url,p.portfolio_url,
      (SELECT AVG(r.rating) FROM reviews r WHERE r.reviewee_id=u.id) rating,(SELECT COUNT(*) FROM reviews r WHERE r.reviewee_id=u.id) review_count
      FROM users u JOIN profiles p ON p.user_id=u.id WHERE u.id!=?""",(uid,)).fetchall()
    result=[]
    for row in people:
        pid=row["id"]; pt={s["id"] for s in skills(pid,"teach")}; pl={s["id"] for s in skills(pid,"learn")}
        overlap=len(teach & pl)+len(learn & pt)
        same=bool(me["college"] and row["college"] and me["college"].strip().casefold()==row["college"].strip().casefold())
        score=min(100,overlap*25+(20 if same else 0))
        combined=list(skills(pid,"teach"))+list(skills(pid,"learn"))
        searchable=" ".join(str(row[k] or "") for k in ("username","full_name","college","qualification","branch","bio"))+" "+" ".join(s["name"]+" "+s["category"] for s in combined)
        if q and q.casefold() not in searchable.casefold(): continue
        if category and not any(s["category"]==category for s in combined): continue
        d=dict(row); d.update(match_score=score,college_match=same,teach_skills=skills(pid,"teach"),learn_skills=skills(pid,"learn"),shared=overlap)
        result.append(d)
    result.sort(key=lambda p:(p["match_score"],p["rating"] or 0,p["full_name"] or p["username"]),reverse=True)
    return result[:limit]

@app.route("/")
def index():
    return redirect(url_for("dashboard")) if g.user else render_template("index.html")

@app.route("/signup",methods=["GET","POST"])
def signup():
    if g.user: return redirect(url_for("dashboard"))
    if request.method=="POST":
        email=request.form.get("email","").strip().lower(); username=request.form.get("username","").strip(); password=request.form.get("password",""); confirm=request.form.get("confirm_password","")
        error=None
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email): error="Enter a valid email address."
        elif not re.fullmatch(r"[A-Za-z0-9_.-]{3,30}",username): error="Username must be 3–30 characters (letters, numbers, dots, underscores, hyphens)."
        elif len(password)<8: error="Password must be at least 8 characters."
        elif password!=confirm: error="Passwords do not match."
        if error: flash(error,"error")
        else:
            try:
                cur=db().execute("INSERT INTO users(email,username,password_hash) VALUES(?,?,?) RETURNING id",(email,username,generate_password_hash(password)))
                new_uid=cur.fetchone()["id"]
                db().execute("INSERT INTO profiles(user_id,full_name) VALUES(?,?)",(new_uid,username)); db().commit()
                session.clear(); session["uid"]=new_uid
                flash("Welcome to PeerNest. Let's build your profile.","success"); return redirect(url_for("edit_profile"))
            except (sqlite3.IntegrityError, psycopg2.IntegrityError):
                db().rollback(); flash("That email or username is already registered.","error")
    return render_template("auth.html",mode="signup")

@app.route("/login",methods=["GET","POST"])
def login():
    if g.user: return redirect(url_for("dashboard"))
    if request.method=="POST":
        email=request.form.get("email","").strip().lower(); password=request.form.get("password","")
        u=db().execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
        if not u or not check_password_hash(u["password_hash"],password): flash("Email or password is incorrect.","error")
        else:
            session.clear(); session["uid"]=u["id"]; flash("Welcome back!","success")
            return redirect(request.args.get("next") or url_for("dashboard"))
    return render_template("auth.html",mode="login")

@app.post("/logout")
@login_required
def logout():
    session.clear(); flash("You have logged out.","info"); return redirect(url_for("index"))

@app.route("/profile/edit",methods=["GET","POST"])
@login_required
def edit_profile():
    p=profile(g.user["id"])
    if request.method=="POST":
        vals={k:request.form.get(k,"").strip() for k in ["full_name","college","qualification","branch","study_status","study_year","graduation_year","bio","github_url","linkedin_url","portfolio_url","availability"]}
        vals["full_name"]=vals["full_name"][:80]; vals["college"]=vals["college"][:120]; vals["qualification"]=vals["qualification"][:120]; vals["branch"]=vals["branch"][:100]; vals["bio"]=vals["bio"][:600]; vals["availability"]=vals["availability"][:250]
        error=None
        if not vals["full_name"] or not vals["college"] or not vals["qualification"]: error="Name, college, and qualification are required."
        elif vals["study_status"] not in ("Student","Graduate"): error="Choose a valid status."
        elif vals["github_url"] and not valid_url(vals["github_url"],"github.com"): error="Enter a valid GitHub profile URL."
        elif vals["linkedin_url"] and not valid_url(vals["linkedin_url"],"linkedin.com"): error="Enter a valid LinkedIn profile URL."
        elif vals["portfolio_url"] and not valid_url(vals["portfolio_url"]): error="Portfolio URL must start with http:// or https://."
        elif vals["graduation_year"] and not re.fullmatch(r"\d{4}",vals["graduation_year"]): error="Graduation year should contain four digits."
        if error: flash(error,"error")
        else:
            db().execute("""UPDATE profiles SET full_name=?,college=?,qualification=?,branch=?,study_status=?,study_year=?,graduation_year=?,bio=?,github_url=?,linkedin_url=?,portfolio_url=?,availability=? WHERE user_id=?""",(*[vals[k] for k in ["full_name","college","qualification","branch","study_status","study_year","graduation_year","bio","github_url","linkedin_url","portfolio_url","availability"]],g.user["id"]))
            db().commit(); flash("Profile saved.","success"); return redirect(url_for("dashboard"))
    return render_template("profile_edit.html",profile=p)

@app.route("/skills",methods=["GET","POST"])
@login_required
def manage_skills():
    if request.method=="POST":
        action=request.form.get("action")
        if action=="remove":
            try:
                db().execute("DELETE FROM user_skills WHERE user_id=? AND skill_id=? AND skill_type=?",(g.user["id"],int(request.form["skill_id"]),request.form["skill_type"])); db().commit(); flash("Skill removed.","success")
            except (ValueError,KeyError): flash("Invalid skill.","error")
        else:
            name=request.form.get("skill_name","").strip()[:60]; kind=request.form.get("skill_type","teach"); level_name=request.form.get("level","Beginner"); category=request.form.get("category","Other")[:60]
            if not name or kind not in ("teach","learn") or level_name not in ("Beginner","Intermediate","Advanced"): flash("Enter a valid skill and options.","error")
            else:
                db().execute("INSERT INTO skills(name,category) VALUES(?,?) ON CONFLICT DO NOTHING",(name,category)); s=db().execute("SELECT id FROM skills WHERE LOWER(name)=LOWER(?)",(name,)).fetchone()
                db().execute("INSERT INTO user_skills(user_id,skill_id,skill_type,level) VALUES(?,?,?,?) ON CONFLICT(user_id,skill_id,skill_type) DO UPDATE SET level=EXCLUDED.level",(g.user["id"],s["id"],kind,level_name)); db().commit(); flash("Skill added.","success")
        return redirect(url_for("manage_skills"))
    return render_template("skills.html",teach=skills(g.user["id"],"teach"),learn=skills(g.user["id"],"learn"))

@app.route("/dashboard")
@login_required
def dashboard():
    uid=g.user["id"]; p=profile(uid)
    if not p["college"] or not p["qualification"]: flash("Complete your profile to get recommendations.","info"); return redirect(url_for("edit_profile"))
    d=db(); stats={
      "connections":d.execute("SELECT COUNT(*) n FROM connections WHERE user_a=? OR user_b=?",(uid,uid)).fetchone()["n"],
      "sessions":d.execute("SELECT COUNT(*) n FROM sessions WHERE (requester_id=? OR partner_id=?) AND status='completed'",(uid,uid)).fetchone()["n"],
      "teaching":d.execute("SELECT COUNT(*) n FROM xp_events WHERE user_id=? AND event_key='teach'",(uid,)).fetchone()["n"],
      "learning":d.execute("SELECT COUNT(*) n FROM xp_events WHERE user_id=? AND event_key='learn'",(uid,)).fetchone()["n"]}
    pending=d.execute("SELECT COUNT(*) n FROM contact_requests WHERE recipient_id=? AND status='pending'",(uid,)).fetchone()["n"]
    return render_template("dashboard.html",profile=p,teach=skills(uid,"teach"),learn=skills(uid,"learn"),suggestions=suggestions(uid,limit=4),stats=stats,pending=pending,xp=xp_summary(uid),badges=badges(uid))

@app.route("/discover")
@login_required
def discover():
    q=request.args.get("q","").strip()[:80]; category=request.args.get("category","").strip()
    cats=[r["category"] for r in db().execute("SELECT DISTINCT category FROM skills ORDER BY category").fetchall()]
    return render_template("discover.html",people=suggestions(g.user["id"],q,category,60),q=q,category=category,categories=cats)

@app.route("/people/<int:uid>")
@login_required
def person(uid):
    if uid==g.user["id"]: return redirect(url_for("edit_profile"))
    p=profile(uid)
    if not p: abort(404)
    d=db(); rating=d.execute("SELECT AVG(rating) avg,COUNT(*) n FROM reviews WHERE reviewee_id=?",(uid,)).fetchone()
    reviews=d.execute("SELECT r.*,u.username,p.full_name FROM reviews r JOIN users u ON u.id=r.reviewer_id JOIN profiles p ON p.user_id=u.id WHERE r.reviewee_id=? ORDER BY r.created_at DESC LIMIT 8",(uid,)).fetchall()
    existing=d.execute("SELECT * FROM contact_requests WHERE (sender_id=? AND recipient_id=?) OR (sender_id=? AND recipient_id=?) ORDER BY id DESC LIMIT 1",(g.user["id"],uid,uid,g.user["id"])).fetchone()
    return render_template("person.html",person=p,teach=skills(uid,"teach"),learn=skills(uid,"learn"),rating=rating,reviews=reviews,connected=connection(g.user["id"],uid),existing=existing,xp=xp_summary(uid),badges=badges(uid))

@app.post("/connect/<int:uid>")
@login_required
def connect(uid):
    if uid==g.user["id"] or not profile(uid): abort(404)
    if connection(g.user["id"],uid): flash("You're already connected.","info"); return redirect(url_for("connections"))
    msg=request.form.get("message","").strip()[:500]
    if not msg: flash("Add a short introduction first.","error"); return redirect(url_for("person",uid=uid))
    d=db()
    incoming=d.execute("SELECT * FROM contact_requests WHERE sender_id=? AND recipient_id=? AND status='pending'",(uid,g.user["id"])).fetchone()
    outgoing=d.execute("SELECT * FROM contact_requests WHERE sender_id=? AND recipient_id=? AND status='pending'",(g.user["id"],uid)).fetchone()
    if incoming:
        d.execute("UPDATE contact_requests SET status='accepted' WHERE id=?",(incoming["id"],)); create_connection(uid,g.user["id"]); d.commit(); flash("You both wanted to connect. You're connected now.","success")
    elif outgoing: flash("Your request is already pending.","info")
    else:
        prior=d.execute("SELECT id FROM contact_requests WHERE sender_id=? AND recipient_id=?",(g.user["id"],uid)).fetchone()
        if prior:
            d.execute("UPDATE contact_requests SET message=?,status='pending',created_at=CURRENT_TIMESTAMP WHERE id=?",(msg,prior["id"]))
        else:
            d.execute("INSERT INTO contact_requests(sender_id,recipient_id,message) VALUES(?,?,?)",(g.user["id"],uid,msg))
        d.commit(); flash("Contact request sent.","success")
    return redirect(url_for("person",uid=uid))

@app.route("/requests",methods=["GET","POST"])
@login_required
def requests_page():
    d=db(); uid=g.user["id"]
    if request.method=="POST":
        try: rid=int(request.form.get("request_id","0"))
        except ValueError: abort(400)
        r=d.execute("SELECT * FROM contact_requests WHERE id=? AND recipient_id=? AND status='pending'",(rid,uid)).fetchone()
        action=request.form.get("action")
        if not r: flash("That request is no longer pending.","error")
        elif action=="accept":
            d.execute("UPDATE contact_requests SET status='accepted' WHERE id=?",(rid,)); create_connection(r["sender_id"],r["recipient_id"]); d.commit(); flash("Request accepted. You can now message each other.","success")
        elif action=="decline": d.execute("UPDATE contact_requests SET status='declined' WHERE id=?",(rid,)); d.commit(); flash("Request declined.","info")
        return redirect(url_for("requests_page"))
    incoming=d.execute("""SELECT cr.*,u.username,p.full_name,p.college FROM contact_requests cr JOIN users u ON u.id=cr.sender_id JOIN profiles p ON p.user_id=u.id WHERE cr.recipient_id=? AND cr.status='pending' ORDER BY cr.created_at DESC""",(uid,)).fetchall()
    outgoing=d.execute("""SELECT cr.*,u.username,p.full_name,p.college FROM contact_requests cr JOIN users u ON u.id=cr.recipient_id JOIN profiles p ON p.user_id=u.id WHERE cr.sender_id=? AND cr.status IN ('pending','accepted','declined') ORDER BY cr.created_at DESC""",(uid,)).fetchall()
    return render_template("requests.html",incoming=incoming,outgoing=outgoing)

@app.route("/connections")
@login_required
def connections():
    uid=g.user["id"]
    rows=db().execute("""SELECT c.id connection_id,CASE WHEN c.user_a=? THEN c.user_b ELSE c.user_a END other_id,u.username,p.full_name,p.college,
      (SELECT body FROM messages m WHERE m.connection_id=c.id ORDER BY m.id DESC LIMIT 1) last_message
      FROM connections c JOIN users u ON u.id=CASE WHEN c.user_a=? THEN c.user_b ELSE c.user_a END JOIN profiles p ON p.user_id=u.id
      WHERE c.user_a=? OR c.user_b=? ORDER BY COALESCE((SELECT MAX(m.id) FROM messages m WHERE m.connection_id=c.id),c.id) DESC""",(uid,uid,uid,uid)).fetchall()
    return render_template("connections.html",connections=rows)

@app.route("/messages/<int:cid>",methods=["GET","POST"])
@login_required
def chat(cid):
    uid=g.user["id"]; d=db()
    c=d.execute("SELECT * FROM connections WHERE id=? AND (user_a=? OR user_b=?)",(cid,uid,uid)).fetchone()
    if not c: abort(404)
    other_id=c["user_b"] if c["user_a"]==uid else c["user_a"]; other=profile(other_id)
    if request.method=="POST":
        body=request.form.get("body","").strip()[:2000]
        if body: d.execute("INSERT INTO messages(connection_id,sender_id,body) VALUES(?,?,?)",(cid,uid,body)); d.commit(); return redirect(url_for("chat",cid=cid))
        flash("Write a message first.","error")
    msgs=d.execute("SELECT m.*,u.username,p.full_name FROM messages m JOIN users u ON u.id=m.sender_id JOIN profiles p ON p.user_id=u.id WHERE m.connection_id=? ORDER BY m.id LIMIT 300",(cid,)).fetchall()
    return render_template("chat.html",connection=c,other=other,messages=msgs)

@app.route("/sessions",methods=["GET","POST"])
@login_required
def sessions_page():
    d=db(); uid=g.user["id"]
    if request.method=="POST":
        action=request.form.get("action")
        try: sid=int(request.form.get("session_id","0")) if action!="create" else 0
        except ValueError: abort(400)
        if action=="create":
            try: partner=int(request.form.get("partner_id","0")); duration=int(request.form.get("duration","60"))
            except ValueError: flash("Choose a valid partner and duration.","error"); return redirect(url_for("sessions_page"))
            skill=request.form.get("skill","").strip()[:100]; model=request.form.get("model","mentoring"); topic=request.form.get("topic","").strip()[:500]; when=request.form.get("proposed_at","").strip()[:40]
            if partner==uid or not connection(uid,partner): flash("Connect with this student before requesting a session.","error")
            elif not skill or model not in ("exchange","mentoring") or duration not in (30,45,60,90,120): flash("Check the session details.","error")
            else: d.execute("INSERT INTO sessions(requester_id,partner_id,skill,model,topic,proposed_at,duration) VALUES(?,?,?,?,?,?,?)",(uid,partner,skill,model,topic,when,duration)); d.commit(); flash("Session request sent.","success")
            return redirect(url_for("sessions_page"))
        s=d.execute("SELECT * FROM sessions WHERE id=? AND (requester_id=? OR partner_id=?)",(sid,uid,uid)).fetchone()
        if not s: abort(404)
        if action=="accept" and s["partner_id"]==uid and s["status"]=="pending": d.execute("UPDATE sessions SET status='accepted' WHERE id=?",(sid,)); d.commit(); flash("Session accepted.","success")
        elif action=="decline" and s["partner_id"]==uid and s["status"]=="pending": d.execute("UPDATE sessions SET status='declined' WHERE id=?",(sid,)); d.commit(); flash("Session declined.","info")
        elif action=="start" and s["status"]=="accepted": d.execute("UPDATE sessions SET status='ongoing' WHERE id=?",(sid,)); d.commit(); flash("Session started.","success")
        elif action=="complete" and s["status"] in ("accepted","ongoing"):
            d.execute("UPDATE sessions SET status='completed',completed_at=CURRENT_TIMESTAMP WHERE id=?",(sid,))
            events=([(s["requester_id"],"teach",50),(s["requester_id"],"learn",40),(s["partner_id"],"teach",50),(s["partner_id"],"learn",40),(s["requester_id"],"exchange",60),(s["partner_id"],"exchange",60)] if s["model"]=="exchange" else [(s["requester_id"],"learn",40),(s["partner_id"],"teach",50)])
            for person_id,key,points in events: d.execute("INSERT INTO xp_events(user_id,session_id,event_key,points) VALUES(?,?,?,?) ON CONFLICT DO NOTHING",(person_id,sid,key,points))
            d.commit(); badges(s["requester_id"]); badges(s["partner_id"]); flash("Session completed. XP awarded!","success")
        elif action=="cancel" and s["status"] in ("pending","accepted") and uid in (s["requester_id"],s["partner_id"]): d.execute("UPDATE sessions SET status='cancelled' WHERE id=?",(sid,)); d.commit(); flash("Session cancelled.","info")
        return redirect(url_for("sessions_page"))
    rows=d.execute("""SELECT s.*,u1.username requester_username,p1.full_name requester_name,u2.username partner_username,p2.full_name partner_name
      FROM sessions s JOIN users u1 ON u1.id=s.requester_id JOIN profiles p1 ON p1.user_id=u1.id JOIN users u2 ON u2.id=s.partner_id JOIN profiles p2 ON p2.user_id=u2.id
      WHERE s.requester_id=? OR s.partner_id=? ORDER BY CASE s.status WHEN 'pending' THEN 0 WHEN 'accepted' THEN 1 WHEN 'ongoing' THEN 2 ELSE 3 END,s.id DESC""",(uid,uid)).fetchall()
    conns=d.execute("""SELECT c.id,CASE WHEN c.user_a=? THEN c.user_b ELSE c.user_a END other_id,u.username,p.full_name,p.college FROM connections c JOIN users u ON u.id=CASE WHEN c.user_a=? THEN c.user_b ELSE c.user_a END JOIN profiles p ON p.user_id=u.id WHERE c.user_a=? OR c.user_b=?""",(uid,uid,uid,uid)).fetchall()
    reviewable={r["id"] for r in d.execute("""SELECT s.id FROM sessions s WHERE s.status='completed' AND (s.requester_id=? OR s.partner_id=?) AND NOT EXISTS(SELECT 1 FROM reviews r WHERE r.session_id=s.id AND r.reviewer_id=?)""",(uid,uid,uid)).fetchall()}
    return render_template("sessions.html",sessions=rows,connections=conns,reviewable=reviewable)

@app.route("/sessions/<int:sid>/feedback",methods=["GET","POST"])
@login_required
def feedback(sid):
    d=db(); uid=g.user["id"]; s=d.execute("SELECT * FROM sessions WHERE id=? AND (requester_id=? OR partner_id=?)",(sid,uid,uid)).fetchone()
    if not s: abort(404)
    if s["status"] not in ("accepted","ongoing","completed"): flash("Feedback is available after a session is accepted.","error"); return redirect(url_for("sessions_page"))
    if request.method=="POST":
        body=request.form.get("body","").strip()[:1000]
        if body: d.execute("INSERT INTO session_feedback(session_id,author_id,body) VALUES(?,?,?)",(sid,uid,body)); d.commit(); flash("Progress note saved.","success"); return redirect(url_for("feedback",sid=sid))
        flash("Write a progress note first.","error")
    notes=d.execute("SELECT f.*,u.username,p.full_name FROM session_feedback f JOIN users u ON u.id=f.author_id JOIN profiles p ON p.user_id=u.id WHERE f.session_id=? ORDER BY f.id DESC",(sid,)).fetchall()
    return render_template("feedback.html",session=s,notes=notes)

@app.route("/reviews/<int:sid>",methods=["GET","POST"])
@login_required
def review(sid):
    d=db(); uid=g.user["id"]; s=d.execute("SELECT * FROM sessions WHERE id=? AND (requester_id=? OR partner_id=?)",(sid,uid,uid)).fetchone()
    if not s: abort(404)
    if s["status"]!="completed": flash("You can review a session after completion.","error"); return redirect(url_for("sessions_page"))
    if d.execute("SELECT id FROM reviews WHERE session_id=? AND reviewer_id=?",(sid,uid)).fetchone(): flash("You've already reviewed this session.","info"); return redirect(url_for("sessions_page"))
    other=profile(s["partner_id"] if s["requester_id"]==uid else s["requester_id"])
    if request.method=="POST":
        try: rating=int(request.form.get("rating","5"))
        except ValueError: rating=0
        body=request.form.get("body","").strip()[:1000]
        if rating not in range(1,6): flash("Choose a rating from 1 to 5.","error")
        else: d.execute("INSERT INTO reviews(session_id,reviewer_id,reviewee_id,rating,body) VALUES(?,?,?,?,?)",(sid,uid,other["user_id"],rating,body)); d.commit(); flash("Thanks for your feedback.","success"); return redirect(url_for("sessions_page"))
    return render_template("review.html",session=s,other=other)

@app.route("/progress")
@login_required
def progress():
    uid=g.user["id"]; d=db(); x=xp_summary(uid); b=badges(uid)
    events=d.execute("SELECT event_key,points,created_at FROM xp_events WHERE user_id=? ORDER BY id DESC LIMIT 20",(uid,)).fetchall()
    counts={k:d.execute("SELECT COUNT(*) n FROM xp_events WHERE user_id=? AND event_key=?",(uid,k)).fetchone()["n"] for k in ("teach","learn","exchange")}
    return render_template("progress.html",xp=x,badges=b,events=events,counts=counts)

@app.errorhandler(404)
def not_found(e): return render_template("404.html"),404

with app.app_context(): init_db()

if __name__=="__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG")=="1")
