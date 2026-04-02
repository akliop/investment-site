import os
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
# تسريع الجلسات وتأمينها
app.secret_key = os.environ.get('SECRET_KEY', "stealth_mining_key_xmr_2024")
app.permanent_session_lifetime = timedelta(days=7) # البقاء مسجلاً لمدة أسبوع

# إعداد قاعدة البيانات لملاءمة Vercel (تحسين الـ IO)
if os.environ.get('VERCEL'):
    db_path = '/tmp/mining_vault.sqlite'
else:
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'mining_vault.sqlite')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"connect_args": {"timeout": 15}} # تسريع الاستجابة

db = SQLAlchemy(app)

# نماذج البيانات المسرعة
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(120), nullable=False)
    xmr_wallet = db.Column(db.String(200))
    xp = db.Column(db.Float, default=10.0)
    rank = db.Column(db.String(20), default="Miner")
    referral_code = db.Column(db.String(20), unique=True, index=True)
    referred_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_referrals = db.Column(db.Integer, default=0)
    balance_usdt = db.Column(db.Float, default=0.0)
    is_admin = db.Column(db.Boolean, default=False)
    
    bonus_5_paid = db.Column(db.Boolean, default=False)
    bonus_10_paid = db.Column(db.Boolean, default=False)
    bonus_30_paid = db.Column(db.Boolean, default=False)
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
    # تأمين الدخول السريع للأدمن
    if not User.query.filter_by(username="AKLI").first():
        admin = User(username="AKLI", password="AKLI_MASTER_LOGIN", is_admin=True, referral_code="MASTER")
        db.session.add(admin); db.session.commit()

# --- محرك الأمان السريع (Fast Security Pulse) ---
def get_user_fast(uid):
    if not uid: return None
    try:
        user = User.query.get(uid)
        if user:
            user.xp = float(user.xp or 10.0)
            user.balance_usdt = float(user.balance_usdt or 0.0)
        return user
    except: return None

# --- المسارات الذكية (Smart Routes) ---

@app.route("/")
@app.route("/join")
def landing():
    # توجيه فوري للمسجلين لتقليل الثقل
    if "miner_id" in session: return redirect(url_for("node_control"))
    return render_template("landing.html", ref_code=request.args.get('ref'))

@app.route("/register", methods=["GET", "POST"])
@app.route("/auth/v1/sync", methods=["GET", "POST"])
def register_logic():
    if "miner_id" in session: return redirect(url_for("node_control")) # حماية من التكرار
    if request.method == "GET": return redirect(url_for("landing"))
    
    u = request.form.get("username", "").strip()
    p = request.form.get("password")
    w = request.form.get("wallet", "AutoNode")
    ref = request.form.get("ref_code")
    
    if not u or not p: return redirect(url_for("landing")) # اختصار ل تسريع الاستجابة
        
    if User.query.filter_by(username=u).first():
        flash("اسم المستخدم موجود سابقاً", "error")
        return redirect(url_for("landing"))

    try:
        new_user = User(
            username=u, password=p, xmr_wallet=w,
            referral_code=str(uuid.uuid4())[:8].upper()
        )
        if ref:
            referrer = User.query.filter_by(referral_code=ref).first()
            if referrer:
                new_user.referred_by_id = referrer.id
                referrer.total_referrals = (referrer.total_referrals or 0) + 1
        
        db.session.add(new_user)
        db.session.commit()
        session["miner_id"] = new_user.id
        session.permanent = True
        return redirect(url_for("node_control"))
    except: return redirect(url_for("landing"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if "miner_id" in session: return redirect(url_for("node_control"))
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password")
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            session["miner_id"] = user.id
            session.permanent = True
            return redirect(url_for("node_control"))
        flash("بيانات خاطئة", "error")
    return render_template("login.html")

@app.route("/portal/x/node")
def node_control():
    user = get_user_fast(session.get("miner_id"))
    if not user: return redirect(url_for("login"))
    top_miners = User.query.order_by(User.xp.desc()).limit(5).all()
    ref_link = f"{request.url_root}join?ref={user.referral_code}"
    return render_template("dashboard.html", user=user, top_miners=top_miners, ref_link=ref_link)

# --- باقي المسارات ب تحسين الـ Redirects ل تقليل زمن التحميل ---

@app.route("/portal/store")
def store():
    user = get_user_fast(session.get("miner_id"))
    if not user: return redirect(url_for("login"))
    return render_template("store.html", user=user)

@app.route("/api/v2/node/pulse", methods=["POST"])
def pulse_sync():
    user = get_user_fast(session.get("miner_id"))
    if not user: return jsonify({"status": "fail"})
    try:
        val = float(request.json.get("units", 1.66))
        user.xp += val
        db.session.commit()
        return jsonify({"status": "success", "xp": round(user.xp, 2)})
    except: return jsonify({"status": "fail"})

@app.route("/logout")
def logout():
    session.clear() # تنظيف كامل للجلسات ل تسريع الاستجابة
    return redirect(url_for("landing"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
