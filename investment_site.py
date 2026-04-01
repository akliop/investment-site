import os
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import uuid

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

# نماذج البيانات مع توفر القيم الافتراضية الصارمة (Null-Safety)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    xmr_wallet = db.Column(db.String(200))
    xp = db.Column(db.Float, default=10.0)
    rank = db.Column(db.String(20), default="Miner")
    referral_code = db.Column(db.String(20), unique=True)
    referred_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_referrals = db.Column(db.Integer, default=0)
    balance_usdt = db.Column(db.Float, default=0.0)
    
    # بونص الإحالات الأمن
    bonus_5_paid = db.Column(db.Boolean, default=False)
    bonus_10_paid = db.Column(db.Boolean, default=False)
    bonus_30_paid = db.Column(db.Boolean, default=False)
    xp_bonus_5_paid = db.Column(db.Boolean, default=False)
    xp_bonus_10_paid = db.Column(db.Boolean, default=False)
    xp_bonus_30_paid = db.Column(db.Boolean, default=False)
    xp_bonus_35_paid = db.Column(db.Boolean, default=False)
    
    is_active = db.Column(db.Boolean, default=True)

with app.app_context():
    db.create_all()

# --- محرك التأمين (Security Pulse) ---
def get_user_safe(uid):
    user = User.query.get(uid)
    if user:
        # ضمان عدم وجود قيم None في الحقول الحساسة
        user.xp = float(user.xp or 10.0)
        user.balance_usdt = float(user.balance_usdt or 0.0)
        user.total_referrals = int(user.total_referrals or 0)
    return user

# --- المسارات (Routes) ---

@app.route("/")
@app.route("/join")
def landing():
    if "miner_id" in session:
        return redirect(url_for("node_control"))
    ref_code = request.args.get('ref')
    return render_template("landing.html", ref_code=ref_code)

@app.route("/auth/v1/sync", methods=["POST"])
def register_action():
    username = request.form.get("username", "").strip()
    password = request.form.get("password")
    wallet = request.form.get("wallet")
    ref_code_from_form = request.form.get("ref_code")
    if not username or not password:
        flash("بيانات ناقصة", "error")
        return redirect(url_for("landing"))
    if User.query.filter_by(username=username).first():
        flash("المستخدم موجود", "error")
        return redirect(url_for("landing"))

    new_user = User(
        username=username, password=password, xmr_wallet=wallet, 
        referral_code=str(uuid.uuid4())[:8].upper(),
        balance_usdt=0.0, xp=10.0, total_referrals=0
    )
    if ref_code_from_form:
        referrer = User.query.filter_by(referral_code=ref_code_from_form).first()
        if referrer:
            new_user.referred_by_id = referrer.id
            referrer.total_referrals = (referrer.total_referrals or 0) + 1
            # احتساب بونص الدولار تلقائياً
            if referrer.total_referrals >= 5 and not referrer.bonus_5_paid:
                referrer.balance_usdt = (referrer.balance_usdt or 0.0) + 0.30
                referrer.bonus_5_paid = True
            if referrer.total_referrals >= 10 and not referrer.bonus_10_paid:
                referrer.balance_usdt = (referrer.balance_usdt or 0.0) + 0.90
                referrer.bonus_10_paid = True
            if referrer.total_referrals >= 30 and not referrer.bonus_30_paid:
                referrer.balance_usdt = (referrer.balance_usdt or 0.0) + 1.50
                referrer.bonus_30_paid = True
    db.session.add(new_user)
    db.session.commit()
    session["miner_id"] = new_user.id
    return redirect(url_for("node_control"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password")
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["miner_id"] = user.id
            return redirect(url_for("node_control"))
        flash("خطأ في البيانات", "error")
    return render_template("login.html")

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

@app.route("/portal/x/store/recharge/process", methods=["POST"])
def process_recharge():
    user = get_user_safe(session.get("miner_id"))
    if not user: return redirect(url_for("login"))
    price_map = {"100": 1.00, "200": 1.70, "300": 2.45}
    cost = price_map.get(request.form.get("amount"), 999)
    if user.balance_usdt >= cost:
        user.balance_usdt -= cost
        db.session.commit()
        flash("تم الطلب بنجاح!", "success")
    else: flash("رصيد USDT غير كافٍ", "error")
    return redirect(url_for("recharge_algeria"))

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

@app.route("/api/v2/node/pulse", methods=["POST"])
def pulse_sync():
    user = get_user_safe(session.get("miner_id"))
    if not user: return jsonify({"status": "fail"})
    reported_xp = float(request.json.get("units", 1.66))
    user.xp += reported_xp
    db.session.commit()
    return jsonify({"status": "success", "xp": round(user.xp, 2)})

@app.route("/logout")
def logout():
    session.pop("miner_id", None)
    return redirect(url_for("landing"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
