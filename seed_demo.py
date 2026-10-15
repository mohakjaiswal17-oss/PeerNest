"""Create two safe sample accounts for a PeerNest presentation demo.

Run from the project folder after installing requirements:
    python seed_demo.py

Demo password for both accounts: Demo12345!
"""
from werkzeug.security import generate_password_hash
from app import app, db, init_db

DEMO_PASSWORD = "Demo12345!"


def get_or_create_user(email, username, full_name, bio, teaches, learns):
    conn = db()
    row = conn.execute("SELECT id FROM users WHERE LOWER(username)=LOWER(?)", (username,)).fetchone()
    if row:
        uid = row["id"]
    else:
        cur = conn.execute(
            "INSERT INTO users(email, username, password_hash) VALUES(?,?,?) RETURNING id",
            (email, username, generate_password_hash(DEMO_PASSWORD)),
        )
        uid = cur.fetchone()["id"]

    conn.execute("""INSERT INTO profiles
        (user_id,full_name,college,qualification,branch,study_status,study_year,graduation_year,bio,availability)
        VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING""",
        (uid, full_name, "Arya College of Engineering", "B.Tech", "Computer Science", "Student", "2nd Year", "2029", bio, "Weekends and evenings"))
    conn.execute("""UPDATE profiles SET full_name=?,college=?,qualification=?,branch=?,study_status=?,study_year=?,graduation_year=?,bio=?,availability=? WHERE user_id=?""",
        (full_name, "Arya College of Engineering", "B.Tech", "Computer Science", "Student", "2nd Year", "2029", bio, "Weekends and evenings", uid))

    for name, category, kind, level in teaches + learns:
        conn.execute("INSERT INTO skills(name,category) VALUES(?,?) ON CONFLICT DO NOTHING", (name, category))
        skill = conn.execute("SELECT id FROM skills WHERE LOWER(name)=LOWER(?)", (name,)).fetchone()
        conn.execute("INSERT INTO user_skills(user_id,skill_id,skill_type,level) VALUES(?,?,?,?) ON CONFLICT DO NOTHING", (uid, skill["id"], kind, level))
    conn.commit()
    return uid


with app.app_context():
    init_db()
    alex = get_or_create_user(
        "alex.demo@peernest.local", "alex_demo", "Alex Sharma",
        "I enjoy Python and problem-solving. I want to improve my UI/UX design skills.",
        [("Python", "Programming", "teach", "Intermediate"), ("C", "Programming", "teach", "Intermediate")],
        [("UI/UX Design", "Design", "learn", "Beginner"), ("Figma", "Design", "learn", "Beginner")],
    )
    sam = get_or_create_user(
        "sam.demo@peernest.local", "sam_demo", "Sam Verma",
        "I enjoy designing clean interfaces and would like to learn Python programming.",
        [("UI/UX Design", "Design", "teach", "Intermediate"), ("Figma", "Design", "teach", "Advanced")],
        [("Python", "Programming", "learn", "Beginner"), ("C", "Programming", "learn", "Beginner")],
    )
    conn = db()
    # Reset this demo pair to a pending request so the accept-request flow is easy to show.
    conn.execute("DELETE FROM connections WHERE (user_a=? AND user_b=?) OR (user_a=? AND user_b=?)", (min(alex, sam), max(alex, sam), min(sam, alex), max(sam, alex)))
    conn.execute("DELETE FROM contact_requests WHERE (sender_id=? AND recipient_id=?) OR (sender_id=? AND recipient_id=?)", (alex, sam, sam, alex))
    conn.execute("INSERT INTO contact_requests(sender_id,recipient_id,message,status) VALUES(?,?,?,'pending')", (alex, sam, "Hi Sam! I can help with Python, and I'd love to learn UI/UX from you."))
    conn.commit()
    print("PeerNest demo accounts are ready.")
    print("Alex: alex_demo / Demo12345!")
    print("Sam:  sam_demo  / Demo12345!")
    print("A pending connection request from Alex to Sam has been created.")
    print("Run: python app.py   then open http://127.0.0.1:5000")
