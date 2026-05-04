from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from authlib.integrations.flask_client import OAuth
import razorpay

# ==============================
# LOAD ENV
# ==============================
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or "dev_secret_key"

# ==============================
# CLOUDINARY CONFIG
# ==============================
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# ==============================
# RAZORPAY
# ==============================
client = razorpay.Client(auth=(
    os.getenv("RAZORPAY_KEY"),
    os.getenv("RAZORPAY_SECRET")
))

# ==============================
# GOOGLE LOGIN
# ==============================
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# ==============================
# DB INIT
# ==============================
def init_db():
    with sqlite3.connect("users.db", timeout=30) as conn:
        c = conn.cursor()

        c.execute("PRAGMA journal_mode=WAL;")

        c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            email TEXT,
            password TEXT,
            profile_pic TEXT DEFAULT '',
            is_premium INTEGER DEFAULT 0
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            image TEXT,
            amount TEXT,
            details TEXT,
            category TEXT,
            likes INTEGER DEFAULT 0
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS saved (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            idea_id INTEGER
        )
        ''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            amount TEXT
        )
        ''')

init_db()

# ==============================
# HOME
# ==============================
@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")

    with sqlite3.connect("users.db", timeout=30) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM ideas ORDER BY id DESC")
        ideas = c.fetchall()

    return render_template("home.html", ideas=ideas)

# ==============================
# SIGNUP
# ==============================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        hashed_password = generate_password_hash(request.form["password"])

        with sqlite3.connect("users.db", timeout=30) as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (username,email,password) VALUES (?,?,?)",
                (request.form["username"], request.form["email"], hashed_password)
            )

        return redirect("/login")

    return render_template("signup.html")

# ==============================
# LOGIN
# ==============================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        with sqlite3.connect("users.db", timeout=30) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email=?", (request.form["email"],))
            user = c.fetchone()

        if user and check_password_hash(user[3], request.form["password"]):
            session["user"] = user[2]   # ✅ FIXED
            return redirect("/")
        else:
            return "Invalid login ❌"

    return render_template("login.html")

# ==============================
# GOOGLE LOGIN
# ==============================
@app.route("/login/google")
def google_login():
    nonce = os.urandom(16).hex()
    session["nonce"] = nonce

    return google.authorize_redirect(
        url_for("authorize", _external=True),
        nonce=nonce
    )

@app.route("/authorize")
def authorize():
    token = google.authorize_access_token()

    nonce = session.get("nonce")
    user = google.parse_id_token(token, nonce=nonce)
    session.pop("nonce", None)

    with sqlite3.connect("users.db", timeout=30) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=?", (user["email"],))
        existing = c.fetchone()

        if not existing:
            c.execute(
                "INSERT INTO users (username,email,password) VALUES (?,?,?)",
                (user["name"], user["email"], generate_password_hash("google_auth"))
            )

    session["user"] = user["email"]
    return redirect("/")

# ==============================
# LOGOUT
# ==============================
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

# ==============================
# UPLOAD
# ==============================
@app.route('/upload', methods=['POST'])
def upload():
    if "user" not in session:
        return redirect("/login")

    file = request.files.get('file')
    amount = request.form.get('amount')
    details = request.form.get('details')
    category = request.form.get('category') or "Idea"

    if file and amount and details:
        result = cloudinary.uploader.upload(file)
        image_url = result["secure_url"]

        with sqlite3.connect("users.db", timeout=30) as conn:
            c = conn.cursor()
            c.execute("""
            INSERT INTO ideas (username, image, amount, details, category)
            VALUES (?, ?, ?, ?, ?)
            """, (session["user"], image_url, amount, details, category))

    return redirect("/")

# ==============================
# LIKE
# ==============================
@app.route("/like/<int:id>")
def like(id):
    with sqlite3.connect("users.db", timeout=30) as conn:
        c = conn.cursor()
        c.execute("UPDATE ideas SET likes = likes + 1 WHERE id=?", (id,))
    return redirect(request.referrer)

# ==============================
# SAVE
# ==============================
@app.route("/save/<int:idea_id>")
def save(idea_id):
    if "user" not in session:
        return redirect("/login")

    with sqlite3.connect("users.db", timeout=30) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM saved WHERE username=? AND idea_id=?",
                  (session["user"], idea_id))

        if not c.fetchone():
            c.execute("INSERT INTO saved (username, idea_id) VALUES (?,?)",
                      (session["user"], idea_id))

    return redirect(request.referrer)

# ==============================
# PAYMENT
# ==============================
@app.route("/payment")
def payment():
    if "user" not in session:
        return redirect("/login")

    with sqlite3.connect("users.db", timeout=30) as conn:
        c = conn.cursor()
        c.execute("""
        SELECT saved.id, ideas.image, ideas.amount, ideas.details
        FROM saved
        JOIN ideas ON saved.idea_id = ideas.id
        WHERE saved.username=?
        """, (session["user"],))

        items = c.fetchall()

    total = 0
    for i in items:
        try:
            total += int(str(i[2]).replace("₹", "").strip())
        except:
            print("Invalid amount:", i[2])

    return render_template("payment.html", items=items, total=total)

# ==============================
# CREATE ORDER
# ==============================
@app.route("/create-order", methods=["POST"])
def create_order():
    amount = int(request.form["amount"]) * 100

    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    return jsonify(dict(order))   # ✅ FIXED

# ==============================
# IDEAS PAGE
# ==============================
@app.route("/ideas")
def ideas_page():
    if "user" not in session:
        return redirect("/login")

    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM ideas WHERE username=?", (session["user"],))
        user_ideas = c.fetchall()

    return render_template("ideas.html", ideas=user_ideas)
#==============================

@app.route("/update-profile", methods=["POST"])
def update_profile():
    if "user" not in session:
        return redirect("/login")

    username = request.form.get("username")
    email = request.form.get("email")

    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE users 
            SET username=?, email=? 
            WHERE email=?
        """, (username, email, session["user"]))

    session["user"] = email
    return redirect("/settings")

# ==============================
# SETTINGS PAGE
# ==============================
@app.route("/settings", methods=["GET", "POST"])
def settings():
    if "user" not in session:
        return redirect("/login")

    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()

        if request.method == "POST":
            username = request.form.get("username")
            email = request.form.get("email")

            c.execute("""
                UPDATE users 
                SET username=?, email=? 
                WHERE email=?
            """, (username, email, session["user"]))

            session["user"] = email

        c.execute("SELECT username, email FROM users WHERE email=?", (session["user"],))
        user = c.fetchone()

    print("USER DATA:", user)   # 👈 ADD THIS

    user_data = {
        "username": user[0] if user else "",
        "email": user[1] if user else ""
    }

    return render_template("settings.html", user=user_data)
# ==============================
# SUCCESS
# ==============================
@app.route("/success")
def success():
    return render_template("success.html")

# ==============================
# RUN
# ==============================
if __name__ == "__main__":
    app.run()