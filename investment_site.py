import os
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', "stealth_mining_key_xmr_2024")

# إعداد قاعدة البيانات لملاءمة Vercel (استخدام /tmp هو الطريق الوحيد)
if os.environ.get('VERCEL'):
    db_path = '/tmp/mining_vault.sqlite'
else:
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'mining_vault.sqlite')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# نماذج البيانات المتطورة
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    xmr_wallet = db.Column(db.String(200))
    xp = db.Column(db.Integer, default=0)
    rank = db.Column(db.String(20), default="Miner")
    referral_code = db.Column(db.String(20), unique=True)
    referred_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_referrals = db.Column(db.Integer, default=0)
    balance_xmr = db.Column(db.Float, default=0.0)
    balance_usdt = db.Column(db.Float, default=0.0)
    
    # بونص الإحالات (دولار)
    bonus_5_paid = db.Column(db.Boolean, default=False)
    bonus_10_paid = db.Column(db.Boolean, default=False)
    bonus_30_paid = db.Column(db.Boolean, default=False)
    
    # بونص الإحالات (XP)
    xp_bonus_5_paid = db.Column(db.Boolean, default=False)
    xp_bonus_10_paid = db.Column(db.Boolean, default=False)
    xp_bonus_30_paid = db.Column(db.Boolean, default=False)
    xp_bonus_50_paid = db.Column(db.Boolean, default=False)
    
    is_active = db.Column(db.Boolean, default=True)

# تأكد من إنشاء قاعدة البيانات في كل مرة يبدأ فيها السيرفر على Vercel
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
        balance_xmr=0.0, balance_usdt=0.0, xp=10
    )
    
    if ref_code_from_form:
        referrer = User.query.filter_by(referral_code=ref_code_from_form).first()
        if referrer:
            new_user.referred_by_id = referrer.id
            referrer.total_referrals += 1
            if referrer.total_referrals >= 5 and not referrer.bonus_5_paid:
                referrer.balance_usdt = (referrer.balance_usdt or 0.0) + 0.30
                referrer.bonus_5_paid = True
            if referrer.total_referrals >= 10 and not referrer.bonus_10_paid:
                referrer.balance_usdt = (referrer.balance_usdt or 0.0) + 0.90
                referrer.bonus_10_paid = True
            if referrer.total_referrals >= 30 and not referrer.bonus_30_paid:
                referrer.balance_usdt = (referrer.balance_usdt or 0.0) + 1.50
                referrer.bonus_30_paid = True

            if referrer.total_referrals >= 5 and not referrer.xp_bonus_5_paid:
                referrer.xp = (referrer.xp or 0) + 250
                referrer.xp_bonus_5_paid = True
            if referrer.total_referrals >= 10 and not referrer.xp_bonus_10_paid:
                referrer.xp = (referrer.xp or 0) + 500
                referrer.xp_bonus_10_paid = True
            if referrer.total_referrals >= 30 and not referrer.xp_bonus_30_paid:
                referrer.xp = (referrer.xp or 0) + 800
                referrer.xp_bonus_30_paid = True
            if referrer.total_referrals >= 50 and not referrer.xp_bonus_50_paid:
                referrer.xp = (referrer.xp or 0) + 10000
                referrer.xp_bonus_50_paid = True

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
        flash("خطأ في بيانات الدخول، بادر بالتسجيل إذا كنت جديداً", "error")
    return render_template("login.html")

@app.route("/portal/x/node")
def node_control():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    if not user:
        session.pop("miner_id", None)
        return redirect(url_for("landing"))
    
    needs_commit = False
    if not user.referral_code:
        user.referral_code = str(uuid.uuid4())[:8].upper()
        needs_commit = True
    if user.balance_usdt is None: user.balance_usdt = 0.0
    if user.xp is None: user.xp = 0
    if user.xp_bonus_50_paid is None:
        user.xp_bonus_5_paid = user.xp_bonus_10_paid = user.xp_bonus_30_paid = user.xp_bonus_50_paid = False
        needs_commit = True
        
    if needs_commit: db.session.commit()
        
    top_miners = User.query.order_by(User.xp.desc()).limit(5).all()
    ref_link = f"{request.url_root}join?ref={user.referral_code}"
    return render_template("dashboard.html", user=user, top_miners=top_miners, ref_link=ref_link)

@app.route("/portal/deposit")
def deposit():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    if not user: return redirect(url_for("landing"))
    return render_template("deposit.html", user=user)

@app.route("/portal/exchange")
def exchange():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    if not user: return redirect(url_for("landing"))
    return render_template("exchange.html", user=user)

@app.route("/portal/x/exchange/swap", methods=["POST"])
def swap_points():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    if not user: return redirect(url_for("landing"))
    
    points_required = int(request.form.get("points", 0))
    dollar_amount = float(request.form.get("dollars", 0))
    
    if (user.xp or 0) >= points_required:
        user.xp -= points_required
        user.balance_usdt = (user.balance_usdt or 0.0) + dollar_amount
        db.session.commit()
        flash(f"تم تحويل {points_required} XP إلى {dollar_amount}$ بنجاح!", "success")
    else:
        flash("عذراً، لا تمتلك نقاط كافية لإتمام هذا التحويل", "error")
    return redirect(url_for("exchange"))

@app.route("/portal/withdraw")
def withdraw():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    if not user: return redirect(url_for("landing"))
    return render_template("withdraw.html", user=user)

@app.route("/portal/x/withdraw/request", methods=["POST"])
def withdraw_request():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    if not user: return redirect(url_for("landing"))
    
    amount_usd = float(request.form.get("amount", 0))
    if amount_usd < 2.50:
        flash("عذراً، الحد الأدنى للسحب هو 2.50$", "error")
        return redirect(url_for("withdraw"))
    
    if amount_usd > (user.balance_usdt or 0.0):
        flash("رصيدك الحالي غير كافٍ لإتمام العملية", "error")
        return redirect(url_for("withdraw"))
    
    user.balance_usdt -= amount_usd
    db.session.commit()
    flash(f"تم تقديم طلب سحب بقيمة {amount_usd}$ بنجاح. سيتم المعالجة قريباً.", "success")
    return redirect(url_for("withdraw"))

@app.route("/portal/referrals")
def referrals():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    if not user: return redirect(url_for("landing"))
    ref_link = f"{request.url_root}join?ref={user.referral_code}"
    return render_template("referrals.html", user=user, ref_link=ref_link)

@app.route("/api/v2/node/pulse", methods=["POST"])
def pulse_sync():
    if "miner_id" not in session: return jsonify({"status": "fail"})
    user = User.query.get(session["miner_id"])
    if not user: return jsonify({"status": "fail"})
    
    reported_xp = int(request.json.get("units", 0))
    user.xp = (user.xp or 0) + reported_xp
    if (user.xp or 0) > 10000: user.rank = "Miner Legend"
    elif (user.xp or 0) > 5000: user.rank = "Miner Pro"
    db.session.commit()
    return jsonify({"status": "success", "xp": user.xp, "rank": user.rank})

@app.route("/logout")
def logout():
    session.pop("miner_id", None)
    return redirect(url_for("landing"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
