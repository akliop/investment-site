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

# نماذج البيانات
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
    is_admin = db.Column(db.Boolean, default=False)
    
    # بونص الإحالات
    bonus_5_paid = db.Column(db.Boolean, default=False)
    bonus_10_paid = db.Column(db.Boolean, default=False)
    bonus_30_paid = db.Column(db.Boolean, default=False)
    
    is_active = db.Column(db.Boolean, default=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    order_type = db.Column(db.String(50)) # RECHARGE, CARD, GAME, WITHDRAW, DEPOSIT
    details = db.Column(db.String(200))
    cost_usdt = db.Column(db.Float)
    status = db.Column(db.String(20), default="PENDING") # PENDING, DONE, CANCELLED
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="AKLI").first():
        admin = User(username="AKLI", password="AKLI_MASTER_LOGIN", is_admin=True, referral_code="MASTER")
        db.session.add(admin)
        db.session.commit()

# --- محرك التأمين (Security Pulse) ---
def get_user_safe(uid):
    if not uid: return None
    user = User.query.get(uid)
    if user:
        user.xp = float(user.xp or 10.0)
        user.balance_usdt = float(user.balance_usdt or 0.0)
    return user

# --- المسارات المالية المعدلة لتسجيل الطلبات ---

@app.route("/portal/x/withdraw/request", methods=["POST"])
def process_withdraw():
    user = get_user_safe(session.get("miner_id"))
    if not user: return redirect(url_for("login"))
    amount = float(request.form.get("amount", 0))
    address = request.form.get("address")
    if user.balance_usdt >= amount and amount >= 1.0:
        user.balance_usdt -= amount
        new_order = Order(user_id=user.id, order_type="WITHDRAW", details=f"Address: {address}", cost_usdt=amount)
        db.session.add(new_order)
        db.session.commit()
        flash("تم تقديم طلب السحب! سيتم التحقق من محفظتك.", "success")
    else: flash("رصيد غير كافٍ أو مبلغ غير صالح", "error")
    return redirect(url_for("withdraw"))

@app.route("/portal/x/deposit/notify", methods=["POST"])
def process_deposit():
    user = get_user_safe(session.get("miner_id"))
    if not user: return redirect(url_for("login"))
    txid = request.form.get("txid")
    amount = float(request.form.get("amount", 0))
    new_order = Order(user_id=user.id, order_type="DEPOSIT", details=f"TXID: {txid}", cost_usdt=amount)
    db.session.add(new_order)
    db.session.commit()
    flash("تم إرسال إشعار الإيداع! سيتم إضافة المبلغ بعد التأكيد.", "success")
    return redirect(url_for("deposit"))

# --- مركز الأدمن المنظم (Admin Panel V2) ---

@app.route("/admin/p/dashboard")
def admin_dash():
    u = get_user_safe(session.get("miner_id"))
    if not u or not u.is_admin: return redirect(url_for("node_control"))
    all_users = User.query.all()
    # تقسيم الطلبات لمجموعتين
    store_orders = Order.query.filter(Order.order_type.in_(["RECHARGE", "CARD", "GAME"])).all()
    money_orders = Order.query.filter(Order.order_type.in_(["WITHDRAW", "DEPOSIT"])).all()
    total_xp = db.session.query(db.func.sum(User.xp)).scalar() or 0
    return render_template("admin_dashboard.html", user=u, all_users=all_users, store_orders=store_orders, money_orders=money_orders, total_xp=total_xp)

@app.route("/admin/x/order/complete/<int:oid>")
def admin_complete_order(oid):
    u = get_user_safe(session.get("miner_id"))
    if not u or not u.is_admin: return redirect(url_for("node_control"))
    order = Order.query.get(oid)
    if order:
        if order.order_type == "DEPOSIT" and order.status == "PENDING":
             target = User.query.get(order.user_id)
             if target: target.balance_usdt = (target.balance_usdt or 0.0) + order.cost_usdt
        order.status = "DONE"
        db.session.commit()
    return redirect(url_for("admin_dash"))

# (باقي كود السيرفر يتبع نفس المنطق لضمان استقرار المسارات)
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

@app.route("/auth/v1/sync", methods=["POST"])
def register_v_alt():
    u = request.form.get("username", "").strip()
    p = request.form.get("password")
    if User.query.filter_by(username=u).first(): return redirect(url_for("landing"))
    new_u = User(username=u, password=p, referral_code=str(uuid.uuid4())[:8].upper())
    db.session.add(new_u); db.session.commit()
    session["miner_id"] = new_u.id
    return redirect(url_for("node_control"))

@app.route("/admin/x/user/edit", methods=["POST"])
def admin_edit_user():
    u = get_user_safe(session.get("miner_id"))
    if not u or not u.is_admin: return redirect(url_for("node_control"))
    target = User.query.get(request.form.get("user_id"))
    if target:
        target.xp = float(request.form.get("xp", target.xp))
        target.balance_usdt = float(request.form.get("balance", target.balance_usdt))
        db.session.commit()
    return redirect(url_for("admin_dash"))

@app.route("/portal/x/store/card/purchase", methods=["POST"])
def purchase_card_v2():
    user = get_user_safe(session.get("miner_id"))
    if not user: return redirect(url_for("login"))
    ctype = request.form.get("card_type")
    price = float(request.form.get("price", 999))
    if user.balance_usdt >= price:
        user.balance_usdt -= price
        new_order = Order(user_id=user.id, order_type="CARD", details=f"{ctype}", cost_usdt=price)
        db.session.add(new_order); db.session.commit()
        flash("تم طلب البطاقة!", "success")
    return redirect(url_for("store_cards"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
