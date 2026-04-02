import os
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', "stealth_mining_key_xmr_2024")

# إعداد قاعدة البيانات لملاءمة Vercel
if os.environ.get('VERCEL'):
    db_path = '/tmp/mining_vault.sqlite'
else:
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'mining_vault.sqlite')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# نماذج البيانات المحدثة
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
    # تأمين حساب الأدمن
    if not User.query.filter_by(username="AKLI").first():
        admin = User(username="AKLI", password="AKLI_MASTER_LOGIN", is_admin=True, referral_code="MASTER")
        db.session.add(admin); db.session.commit()

# --- محرك الأمان (Security Shield) ---
def get_user_safe(uid):
    if not uid: return None
    try:
        user = User.query.get(uid)
        if user:
            user.xp = float(user.xp or 10.0)
            user.balance_usdt = float(user.balance_usdt or 0.0)
            user.total_referrals = int(user.total_referrals or 0)
        return user
    except: return None

# --- إصلاح بوابة التسجيل والدخول الشامل (Universal Logic) ---

@app.route("/")
@app.route("/join")
def landing():
    if "miner_id" in session: return redirect(url_for("node_control"))
    return render_template("landing.html", ref_code=request.args.get('ref'))

@app.route("/register", methods=["GET", "POST"])
@app.route("/auth/v1/sync", methods=["GET", "POST"])
def register_logic():
    if request.method == "GET": return redirect(url_for("landing"))
    
    u = request.form.get("username", "").strip()
    p = request.form.get("password")
    w = request.form.get("wallet", "AutoNode")
    ref = request.form.get("ref_code")
    
    if not u or not p:
        flash("بيانات ناقصة يا صديقي", "error")
        return redirect(url_for("landing"))
        
    if User.query.filter_by(username=u).first():
        flash("اسم المستخدم مستخدم بالفعل", "error")
        return redirect(url_for("landing"))

    try:
        new_user = User(
            username=u, password=p, xmr_wallet=w,
            referral_code=str(uuid.uuid4())[:8].upper(),
            balance_usdt=0.0, xp=10.0, total_referrals=0
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
    except Exception as e:
        flash(f"خلل تقني مؤقت: {str(e)}", "error")
        return redirect(url_for("landing"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password")
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            session["miner_id"] = user.id
            session.permanent = True
            return redirect(url_for("node_control"))
        flash("بيانات دخول خاطئة", "error")
    return render_template("login.html")

# --- باقي المسارات (ب حماية Null-Safety) ---

@app.route("/portal/x/node")
def node_control():
    user = get_user_safe(session.get("miner_id"))
    if not user: return redirect(url_for("login"))
    top_miners = User.query.order_by(User.xp.desc()).limit(5).all()
    ref_link = f"{request.url_root}join?ref={user.referral_code}"
    return render_template("dashboard.html", user=user, top_miners=top_miners, ref_link=ref_link)

@app.route("/portal/store")
def store():
    user = get_user_safe(session.get("miner_id"))
    if not user: return redirect(url_for("login"))
    return render_template("store.html", user=user)

@app.route("/portal/store/recharge")
def recharge_algeria():
    user = get_user_safe(session.get("miner_id"))
    if not user: return redirect(url_for("login"))
    return render_template("recharge.html", user=user)

@app.route("/portal/store/cards")
def store_cards():
    user = get_user_safe(session.get("miner_id"))
    if not user: return redirect(url_for("login"))
    return render_template("cards.html", user=user)

@app.route("/portal/store/games")
def store_games():
    user = get_user_safe(session.get("miner_id"))
    if not user: return redirect(url_for("login"))
    return render_template("games.html", user=user)

@app.route("/admin/p/dashboard")
def admin_dash():
    u = get_user_safe(session.get("miner_id"))
    if not u or not u.is_admin: return redirect(url_for("node_control"))
    all_users = User.query.all()
    store_orders = Order.query.filter(Order.order_type.in_(["RECHARGE", "CARD", "GAME"])).all()
    money_orders = Order.query.filter(Order.order_type.in_(["WITHDRAW", "DEPOSIT"])).all()
    total_xp = db.session.query(db.func.sum(User.xp)).scalar() or 0
    return render_template("admin_dashboard.html", user=u, all_users=all_users, store_orders=store_orders, money_orders=money_orders, total_xp=total_xp)

@app.route("/api/v2/node/pulse", methods=["POST"])
def pulse_sync():
    user = get_user_safe(session.get("miner_id"))
    if not user: return jsonify({"status": "fail"})
    reported_xp = float(request.json.get("units", 1.66))
    user.xp += reported_xp
    db.session.commit()
    return jsonify({"status": "success", "xp": round(user.xp, 2)})

@app.route("/portal/deposit")
def deposit():
    user = get_user_safe(session.get("miner_id"))
    if not user: return redirect(url_for("login"))
    return render_template("deposit.html", user=user)

@app.route("/portal/exchange")
def exchange():
    user = get_user_safe(session.get("miner_id"))
    if not user: return redirect(url_for("login"))
    return render_template("exchange.html", user=user)

@app.route("/portal/withdraw")
def withdraw():
    user = get_user_safe(session.get("miner_id"))
    if not user: return redirect(url_for("login"))
    return render_template("withdraw.html", user=user)

@app.route("/portal/referrals")
def referrals():
    user = get_user_safe(session.get("miner_id"))
    if not user: return redirect(url_for("login"))
    ref_link = f"{request.url_root}join?ref={user.referral_code}"
    return render_template("referrals.html", user=user, ref_link=ref_link)

@app.route("/logout")
def logout():
    session.pop("miner_id", None)
    return redirect(url_for("landing"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
