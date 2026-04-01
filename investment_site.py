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

# نماذج البيانات
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    xmr_wallet = db.Column(db.String(200))
    xp = db.Column(db.Float, default=0.0)
    rank = db.Column(db.String(20), default="Miner")
    referral_code = db.Column(db.String(20), unique=True)
    referred_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_referrals = db.Column(db.Integer, default=0)
    balance_usdt = db.Column(db.Float, default=0.0)
    
    # بونص الإحالات
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
        flash("يرجى ملء كافة البيانات", "error")
        return redirect(url_for("landing"))
    if User.query.filter_by(username=username).first():
        flash("اسم المستخدم مستخدم بالفعل", "error")
        return redirect(url_for("landing"))

    new_user = User(
        username=username, password=password, xmr_wallet=wallet, 
        referral_code=str(uuid.uuid4())[:8].upper(),
        balance_usdt=0.0, xp=10.0
    )
    if ref_code_from_form:
        referrer = User.query.filter_by(referral_code=ref_code_from_form).first()
        if referrer:
            new_user.referred_by_id = referrer.id
            referrer.total_referrals += 1
            if referrer.total_referrals >= 5 and not referrer.bonus_5_paid:
                referrer.balance_usdt = (referrer.balance_usdt or 0.0) + 0.30
                referrer.bonus_5_paid = True
            # ... (باقي البونصات) ...
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
        flash("خطأ في بيانات الدخول", "error")
    return render_template("login.html")

@app.route("/portal/x/node")
def node_control():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    if not user: return redirect(url_for("landing"))
    top_miners = User.query.order_by(User.xp.desc()).limit(5).all()
    ref_link = f"{request.url_root}join?ref={user.referral_code}"
    return render_template("dashboard.html", user=user, top_miners=top_miners, ref_link=ref_link)

@app.route("/portal/store")
def store():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    return render_template("store.html", user=user)

@app.route("/portal/store/recharge")
def recharge_algeria():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    return render_template("recharge.html", user=user)

@app.route("/portal/x/store/recharge/process", methods=["POST"])
def process_recharge():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    operator = request.form.get("operator")
    phone = request.form.get("phone")
    amount_dzd = request.form.get("amount")
    price_map = {"100": 1.00, "200": 1.70, "300": 2.45}
    cost = price_map.get(amount_dzd, 999)
    if user.balance_usdt >= cost:
        user.balance_usdt -= cost
        db.session.commit()
        flash(f"تم تقديم طلب تعبئة {amount_dzd} دج. سيصلك الرصيد قريباً!", "success")
    else: flash("رصيدك غير كافٍ", "error")
    return redirect(url_for("recharge_algeria"))

@app.route("/portal/store/cards")
def store_cards():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    return render_template("cards.html", user=user)

@app.route("/portal/x/store/card/purchase", methods=["POST"])
def purchase_card():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    card_type = request.form.get("card_type")
    price = float(request.form.get("price", 999))
    if user.balance_usdt >= price:
        user.balance_usdt -= price
        db.session.commit()
        flash(f"تم شراء بطاقة {card_type} بنجاح!", "success")
    else: flash("رصيدك غير كافٍ", "error")
    return redirect(url_for("store_cards"))

@app.route("/portal/store/games")
def store_games():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    return render_template("games.html", user=user)

@app.route("/portal/x/store/game/purchase", methods=["POST"])
def purchase_game():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    game = request.form.get("game")
    item = request.form.get("item")
    price = float(request.form.get("price", 999))
    if user.balance_usdt >= price:
        user.balance_usdt -= price
        db.session.commit()
        flash(f"تم شراء {item} ل لعبة {game} بنجاح! سيتم الشحن لحسابك خلال دقائق.", "success")
    else: flash("رصيدك USDT غير كافٍ لهذه العملية.", "error")
    return redirect(url_for("store_games"))

@app.route("/portal/deposit")
def deposit():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    return render_template("deposit.html", user=user)

@app.route("/portal/exchange")
def exchange():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    return render_template("exchange.html", user=user)

@app.route("/portal/withdraw")
def withdraw():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    return render_template("withdraw.html", user=user)

@app.route("/portal/referrals")
def referrals():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    ref_link = f"{request.url_root}join?ref={user.referral_code}"
    return render_template("referrals.html", user=user, ref_link=ref_link)

@app.route("/api/v2/node/pulse", methods=["POST"])
def pulse_sync():
    if "miner_id" not in session: return jsonify({"status": "fail"})
    user = User.query.get(session["miner_id"])
    if not user: return jsonify({"status": "fail"})
    reported_xp = float(request.json.get("units", 1.66))
    user.xp = (user.xp or 0.0) + reported_xp
    db.session.commit()
    return jsonify({"status": "success", "xp": round(user.xp, 2)})

@app.route("/logout")
def logout():
    session.pop("miner_id", None)
    return redirect(url_for("landing"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
