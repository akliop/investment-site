import os
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', "stealth_mining_key_xmr_2024")
app.permanent_session_lifetime = timedelta(days=7)

# إعداد قاعدة البيانات لملاءمة Vercel
if os.environ.get('VERCEL'):
    db_path = '/tmp/mining_vault.sqlite'
else:
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'mining_vault.sqlite')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"connect_args": {"timeout": 15}}

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(120), nullable=False)
    xmr_wallet = db.Column(db.String(200))
    xp = db.Column(db.Float, default=10.0)
    rank = db.Column(db.String(20), default="Miner")
    referral_code = db.Column(db.String(20), unique=True, index=True)
    balance_usdt = db.Column(db.Float, default=0.0)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    order_type = db.Column(db.String(50))
    details = db.Column(db.String(200))
    cost_usdt = db.Column(db.Float)
    status = db.Column(db.String(20), default="PENDING")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="AKLI").first():
        admin = User(username="AKLI", password="AKLI_MASTER_LOGIN", is_admin=True, referral_code="MASTER")
        db.session.add(admin); db.session.commit()

# --- محرك الأمان الذكي لكسر حلقات التوجيه (Loop Breaker) ---
def get_current_user():
    uid = session.get("miner_id")
    if not uid: return None
    try:
        user = User.query.get(uid)
        if not user:
            session.clear() # مسح الجلسة "الميتة" فوراً ل منع التكرار
            return None
        return user
    except:
        session.clear()
        return None

# --- المسارات المصححة ---

@app.route("/")
@app.route("/join")
def landing():
    user = get_current_user()
    if user: return redirect(url_for("node_control"))
    return render_template("landing.html", ref_code=request.args.get('ref'))

@app.route("/register", methods=["GET", "POST"])
@app.route("/auth/v1/sync", methods=["GET", "POST"])
def register_logic():
    user = get_current_user()
    if user: return redirect(url_for("node_control"))
    if request.method == "GET": return redirect(url_for("landing"))
    
    u = request.form.get("username", "").strip()
    p = request.form.get("password")
    w = request.form.get("wallet", "AutoNode")
    ref = request.form.get("ref_code")
    
    if not u or not p: return redirect(url_for("landing"))
    if User.query.filter_by(username=u).first():
        flash("المستخدم موجود", "error")
        return redirect(url_for("landing"))

    try:
        new_user = User(username=u, password=p, xmr_wallet=w, referral_code=str(uuid.uuid4())[:8].upper())
        db.session.add(new_user); db.session.commit()
        session["miner_id"] = new_user.id
        session.permanent = True
        return redirect(url_for("node_control"))
    except: return redirect(url_for("landing"))

@app.route("/login", methods=["GET", "POST"])
def login():
    user = get_current_user()
    if user: return redirect(url_for("node_control"))
    
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password")
        user_auth = User.query.filter_by(username=u, password=p).first()
        if user_auth:
            session["miner_id"] = user_auth.id
            session.permanent = True
            return redirect(url_for("node_control"))
        flash("خطأ في البيانات", "error")
    return render_template("login.html")

@app.route("/portal/x/node")
def node_control():
    user = get_current_user()
    if not user: return redirect(url_for("login"))
    top_miners = User.query.order_by(User.xp.desc()).limit(5).all()
    ref_link = f"{request.url_root}join?ref={user.referral_code}"
    return render_template("dashboard.html", user=user, top_miners=top_miners, ref_link=ref_link)

# --- باقي المسارات ب استخدام معالج المستخدم الموحد ---
@app.route("/portal/store")
def store():
    user = get_current_user(); if not user: return redirect(url_for("login"))
    return render_template("store.html", user=user)

@app.route("/portal/store/recharge")
def recharge_algeria():
    user = get_current_user(); if not user: return redirect(url_for("login"))
    return render_template("recharge.html", user=user)

@app.route("/portal/store/cards")
def store_cards():
    user = get_current_user(); if not user: return redirect(url_for("login"))
    return render_template("cards.html", user=user)

@app.route("/portal/store/games")
def store_games():
    user = get_current_user(); if not user: return redirect(url_for("login"))
    return render_template("games.html", user=user)

@app.route("/api/v2/node/pulse", methods=["POST"])
def pulse_sync():
    user = get_current_user(); if not user: return jsonify({"status": "fail"})
    try:
        user.xp += float(request.json.get("units", 1.66))
        db.session.commit()
        return jsonify({"status": "success", "xp": round(user.xp, 2)})
    except: return jsonify({"status": "fail"})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
