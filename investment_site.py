import os
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
# ثبات المفتاح وسرعة الجلسة v4
app.secret_key = os.environ.get('SECRET_KEY', "v4_stealth_mining_ultra_secure_2024")
app.permanent_session_lifetime = timedelta(days=7)

# إعداد قاعدة البيانات v4 المستقرة
if os.environ.get('VERCEL'):
    db_path = '/tmp/vault_v4.sqlite'
else:
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'vault_v4.sqlite')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(120), nullable=False)
    xmr_wallet = db.Column(db.String(200))
    xp = db.Column(db.Float, default=10.0)
    rank = db.Column(db.String(20), default="Miner")
    referral_code = db.Column(db.String(20), unique=True)
    referred_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_referrals = db.Column(db.Integer, default=0)
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

# --- محرك الأمان (Safe Core v4) ---
def get_user_v4():
    uid = session.get("v4_id")
    if not uid: return None
    try:
        user = User.query.get(uid)
        if not user:
            session.clear(); return None
        return user
    except: return None

# --- المسارات والروابط المصححة مئة بالمئة ---

@app.route("/")
@app.route("/join")
def index():
    user = get_user_v4()
    if user: return redirect(url_for("user_dashboard"))
    return render_template("landing.html", ref_code=request.args.get('ref'))

# دعم كافة روابط التسجيل (Register + Sync) لمنع 404
@app.route("/register", methods=["GET", "POST"])
@app.route("/auth/v1/sync", methods=["GET", "POST"])
def auth_register():
    if request.method == "GET": return redirect(url_for("index"))
    
    u = request.form.get("username", "").strip()
    p = request.form.get("password")
    w = request.form.get("wallet", "AutoNode")
    ref = request.form.get("ref_code")
    
    if not u or not p: return redirect(url_for("index"))
    if User.query.filter_by(username=u).first():
        flash("اسم المستخدم موجود سابقاً", "error")
        return redirect(url_for("index"))

    try:
        new_user = User(username=u, password=p, xmr_wallet=w, referral_code=str(uuid.uuid4())[:8].upper())
        if ref:
            referrer = User.query.filter_by(referral_code=ref).first()
            if referrer:
                new_user.referred_by_id = referrer.id
                referrer.total_referrals = (referrer.total_referrals or 0) + 1
        
        db.session.add(new_user); db.session.commit()
        session["v4_id"] = new_user.id
        session.permanent = True
        return redirect(url_for("user_dashboard"))
    except: return redirect(url_for("index"))

@app.route("/login", methods=["GET", "POST"])
def auth_login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password")
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            session["v4_id"] = user.id
            session.permanent = True
            return redirect(url_for("user_dashboard"))
        flash("بيانات خاطئة", "error")
    return render_template("login.html")

@app.route("/portal/home")
def user_dashboard():
    user = get_user_v4()
    if not user: return redirect(url_for("auth_login"))
    top_miners = User.query.order_by(User.xp.desc()).limit(5).all()
    ref_link = f"{request.url_root}?ref={user.referral_code}"
    return render_template("dashboard.html", user=user, top_miners=top_miners, ref_link=ref_link)

# --- تفعيل كل خانات المتجر والأدمن ل تعمل بجانب v4 ---

@app.route("/portal/store")
def store():
    user = get_user_v4(); if not user: return redirect(url_for("auth_login"))
    return render_template("store.html", user=user)

@app.route("/portal/store/games")
def store_games():
    user = get_user_v4(); if not user: return redirect(url_for("auth_login"))
    return render_template("games.html", user=user)

@app.route("/api/v2/node/pulse", methods=["POST"])
def pulse_sync():
    user = get_user_v4(); if not user: return jsonify({"status": "fail"})
    user.xp += float(request.json.get("units", 1.66))
    db.session.commit()
    return jsonify({"status": "success", "xp": round(user.xp, 2)})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
