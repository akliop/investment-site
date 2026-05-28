import os
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime, timedelta

# المحرك v27.1: النسخة الأبدية (Final Eternal Node - REBUILD FORCE)
app = Flask(__name__)
app.secret_key = "v27_eternal_node_key"
app.permanent_session_lifetime = timedelta(days=7)

# إعداد قاعدة البيانات - تأمين الربط الفائق
db_url = os.environ.get('DATABASE_URL') or os.environ.get('NEON_DATABASE_URL')
if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
else:
    db_path = "/tmp/akli_node_v27.sqlite" if os.environ.get('VERCEL') else "akli_node_v27.sqlite"
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PROPAGATE_EXCEPTIONS'] = True

db = SQLAlchemy(app)

@app.errorhandler(500)
def handle_500(e):
    import traceback
    error = traceback.format_exc()
    return f"<h3>ADMIN DEBUG: 500 Internal Server Error</h3><pre>{error}</pre>", 500


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False, index=True) # Username/Gmail
    password = db.Column(db.String(120), nullable=False)
    jewels = db.Column(db.Float, default=0.0)
    xp = db.Column(db.Float, default=0.0)
    balance_usdt = db.Column(db.Float, default=0.0)
    xmr_wallet = db.Column(db.String(200)) # Added missing field
    referral_code = db.Column(db.String(20), unique=True)
    total_referrals = db.Column(db.Integer, default=0)
    referred_by = db.Column(db.Integer)
    is_pc = db.Column(db.Boolean, default=False)
    has_mined = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    mining_rate = db.Column(db.Float, default=0.0)
    vip_package = db.Column(db.String(50), default="FREE")

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(100))
    price = db.Column(db.Float)
    status = db.Column(db.String(40), default="قيد المراجعة 🕒")
    delivery_data = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class FinanceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(20)) # "DEPOSIT" or "WITHDRAW"
    amount = db.Column(db.Float)
    details = db.Column(db.Text)
    status = db.Column(db.String(20), default="PENDING")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class GlobalNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


@app.route("/force_reset") # إعادة ضبط المصنع الشاملة
def force_reset():
    try:
        from sqlalchemy import text
        # كسر كل القيود وحذف جميع الجداول الموجودة في قاعدة البيانات (حتى القديمة)
        db.session.execute(text("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """))
        db.session.commit()
        
        db.create_all()
        return "SUCCESS: Nuclear Reset Complete! Site database has been rebuilt from zero. <a href='/'>Go to Home</a>"
    except Exception as e:
        db.session.rollback()
        return f"ERROR: {str(e)}"

# بوابة الإدارة السرية (من الصورة المرسلة)
@app.route("/admin_gate/<secret>")
def admin_gate(secret):
    if secret == "efon3gkpal":
        user = get_v_user()
        if user:
            user.is_admin = True
            db.session.commit()
            return "SUCCESS: You are now an ADMIN. <a href='/portal/admin_dashboard'>Go to Dashboard</a>"
        return "Log in first, then use this link."
    return "Invalid Secret Key."

@app.route("/easy_admin")
def easy_admin():
    # البحث عن حساب الأدمن أو إنشاؤه
    admin = User.query.filter_by(username="admin_king").first()
    if not admin:
        import uuid
        admin = User(
            username="admin_king", 
            password="123", 
            is_admin=True, 
            referral_code="ADMIN_01",
            balance_usdt=1000.0,
            xp=100.0
        )
        db.session.add(admin)
        db.session.commit()
    
    # تحويله لأدمن إن لم يكن
    admin.is_admin = True
    db.session.commit()
    
    # تسجيل الدخول تلقائياً
    session["v27_id"] = admin.id
    session.permanent = True
    return f"تم تسجيل دخولك كأدمن بنجاح! اسم المستخدم: {admin.username} <br> <a href='/portal/admin_dashboard'>انقر هنا للذهاب للوحة الإدارة</a>"

def get_v_user():
    uid = session.get("v27_id")
    if not uid: return None
    try: return db.session.get(User, uid)
    except: return None

@app.route("/")
def home():
    user = get_v_user()
    if user: return redirect(url_for("dashboard"))
    return render_template("landing.html", ref_code=request.args.get('ref'))

@app.route("/register", methods=["GET", "POST"])
@app.route("/join_node", methods=["GET", "POST"])
def register():
    if request.method == "GET": return redirect(url_for("home"))
    u = request.form.get("username", "").strip()
    p = request.form.get("password", "")
    ref = request.form.get("ref_code", "").strip()
    if not u or not p: return redirect(url_for("home"))
    try:
        if User.query.filter_by(username=u).first():
            flash("هذا الحساب مسجل مسبقاً!", "info")
            return redirect(url_for("login"))
        ua = request.user_agent.platform or ""
        is_pc = ua.lower() in ["windows", "linux", "macos", "chromeos"]
        new_u = User(username=u, password=p, referral_code=str(uuid.uuid4())[:8].upper(), is_pc=is_pc)
        if ref:
            r = User.query.filter_by(referral_code=ref).first()
            if r: 
                new_u.referred_by = r.id; r.total_referrals += 1; db.session.add(r)
        db.session.add(new_u); db.session.commit()
        session["v27_id"] = new_u.id; session.permanent = True
        return redirect(url_for("dashboard"))
    except Exception as e:
        db.session.rollback(); return f"Error during registration: {e}", 500

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password")
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            session["v27_id"] = user.id; session.permanent = True
            return redirect(url_for("dashboard"))
        flash("خطأ في البيانات!", "error")
    return render_template("login.html")

@app.route("/portal/home")
def dashboard():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    return redirect("/portal/scanner")

@app.route("/portal/<page>")
def portal_pages(page):
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    
    # حماية لوحة التحكم
    if page in ["admin_dashboard", "dev_room"] and not user.is_admin:
        return "Access Denied: You are not an admin.", 403

    context = {
        "user": user,
        "ref_link": f"{request.url_root}?ref={user.referral_code}"
    }

    if page == 'referrals':
        context["mined_count"] = User.query.filter_by(referred_by=user.id, has_mined=True).count()
        context["pc_mined_count"] = User.query.filter_by(referred_by=user.id, has_mined=True, is_pc=True).count()
    
    if page == 'admin_dashboard':
        context["orders"] = Order.query.order_by(Order.timestamp.desc()).all()
        context["money_orders"] = FinanceRequest.query.order_by(FinanceRequest.timestamp.desc()).all()
        context["all_users"] = User.query.all()

    if page == 'dev_room':
        context["orders"] = Order.query.order_by(Order.timestamp.desc()).all()
        context["finances"] = FinanceRequest.query.order_by(FinanceRequest.timestamp.desc()).all()
        context["all_users"] = User.query.all()
        context["user_count"] = User.query.count()

    try:
        return render_template(f"{page}.html", **context)
    except Exception as e:
        print(f"Template error: {e}")
        return f"Page {page} not found.", 404

# --- ADMIN API & ROUTES ---

@app.route("/admin/dev-room")
def dev_room_redirect():
    return redirect("/portal/dev_room")

@app.route("/api/admin/deliver", methods=["POST"])
def admin_deliver():
    user = get_v_user()
    if not user or not user.is_admin: return jsonify({"status": "error", "message": "Unauthorized"}), 403
    data = request.json
    order = db.session.get(Order, data.get("order_id"))
    if order:
        order.delivery_data = data.get("delivery_data")
        order.status = "تم التسليم ✅"
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Order not found"})

@app.route("/api/admin/finance/update", methods=["POST"])
def admin_finance_update():
    user = get_v_user()
    if not user or not user.is_admin: return jsonify({"status": "error", "message": "Unauthorized"}), 403
    data = request.json
    f = db.session.get(FinanceRequest, data.get("finance_id"))
    if f:
        action = data.get("action")
        if action == "APPROVE":
            f.status = "DONE"
            target_user = db.session.get(User, f.user_id)
            if target_user and f.type == "DEPOSIT":
                target_user.balance_usdt += f.amount
        else:
            f.status = "REJECTED"
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Request not found"})

@app.route("/api/admin/notify", methods=["POST"])
def admin_notify():
    # التحقق من الـ PIN كما في القالب (akli2025)
    if request.args.get("pin") != "akli2025": return jsonify({"status": "error", "message": "Wrong PIN"}), 403
    msg = request.json.get("message")
    if msg:
        n = GlobalNotification(message=msg)
        db.session.add(n)
        db.session.commit()
        return jsonify({"status": "success", "message": "Notification broadcasted!"})
    return jsonify({"status": "error", "message": "No message"})

@app.route("/admin/x/order/complete/<int:oid>")
def admin_order_complete(oid):
    user = get_v_user()
    if not user or not user.is_admin: return "Unauthorized", 403
    f = db.session.get(FinanceRequest, oid)
    if f:
        f.status = "DONE"
        db.session.commit()
    return redirect("/portal/admin_dashboard")

@app.route("/admin/x/user/edit", methods=["POST"])
def admin_user_edit():
    user = get_v_user()
    if not user or not user.is_admin: return "Unauthorized", 403
    uid = request.form.get("user_id")
    target = db.session.get(User, uid)
    if target:
        xp = request.form.get("xp")
        bal = request.form.get("balance")
        if xp: target.xp = float(xp)
        if bal: target.balance_usdt = float(bal)
        db.session.commit()
    return redirect("/portal/admin_dashboard")

# --- FINANCE SUBMISSIONS ---

@app.route("/portal/recharge/submit", methods=["POST"])
def recharge_submit():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    
    amount = float(request.form.get("amount", 0))
    txid = request.form.get("txid")
    
    if amount < 5.0:
        flash("عذراً، الحد الأدنى للإيداع هو 5 دولار ($5)", "error")
        return redirect("/portal/recharge")
        
    new_req = FinanceRequest(
        user_id=user.id,
        type="DEPOSIT",
        amount=amount,
        details=f"TXID: {txid}",
        status="PENDING"
    )
    db.session.add(new_req)
    db.session.commit()
    flash("تم إرسال طلب الإيداع بنجاح! سيتم التحقق من المعاملة قريباً.", "success")
    return redirect("/portal/home")

@app.route("/portal/withdraw/submit", methods=["POST"])
def withdraw_submit():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    
    amount = float(request.form.get("amount", 0))
    address = request.form.get("address")
    network = request.form.get("network")
    
    if amount < 5.0:
        flash("عذراً، الحد الأدنى للسحب هو 5 دولار ($5)", "error")
        return redirect("/portal/withdraw")
        
    if user.balance_usdt < amount:
        flash("رصيدك الحالي غير كافٍ لإتمام عملية السحب!", "error")
        return redirect("/portal/withdraw")
        
    user.balance_usdt -= amount
    new_req = FinanceRequest(
        user_id=user.id,
        type="WITHDRAW",
        amount=amount,
        details=f"Network: {network} | Address: {address}",
        status="PENDING"
    )
    db.session.add(new_req)
    db.session.commit()
    flash("تم تسجيل طلب السحب بنجاح! سيتم التحويل خلال 24 ساعة.", "success")
    return redirect("/portal/home")

# --- END FINANCE SUBMISSIONS ---

@app.route("/api/v2/node/buy", methods=["POST"])
def buy_product():
    user = get_v_user()
    if not user: return jsonify({"status": "error", "message": "يجب تسجيل الدخول أولاً"}), 401
    
    data = request.json
    name = data.get("name")
    price = float(data.get("price", 0))
    
    if user.balance_usdt < price:
        return jsonify({"status": "error", "message": "رصيدك غير كافٍ!"})
    
    # Check if it's a VIP Package
    vip_packages = {
        "VIP 1 ($5)": {"rate": 8.0, "price": 5.0},
        "VIP 2 ($10)": {"rate": 16.0, "price": 10.0},
        "VIP 3 ($15)": {"rate": 24.0, "price": 15.0},
        "VIP 4 ($30)": {"rate": 30.0, "price": 30.0}
    }
    
    if name in vip_packages:
        package = vip_packages[name]
        user.balance_usdt -= package["price"]
        user.mining_rate = package["rate"]
        user.vip_package = name
        # إضافة سجل في الطلبات لتعريف المستخدم بعملية الشراء
        new_order = Order(user_id=user.id, product_name=f"تفعيل {name}", price=package["price"], status="تم التفعيل تلقائياً ✅")
        db.session.add(new_order)
        db.session.commit()
        return jsonify({"status": "success", "message": f"تم تفعيل باقة {name} بنجاح! قوة التعدين الجديدة: {package['rate']} نقطة/دقيقة"})
    
    # Regular product order
    user.balance_usdt -= price
    new_order = Order(user_id=user.id, product_name=name, price=price)
    db.session.add(new_order)
    db.session.commit()
    
    return jsonify({"status": "success", "message": "تم تقديم طلبك بنجاح! سيتم المراجعة قريباً."})

@app.route("/sw.js")
def serve_sw(): return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.context_processor
def inject_notice():
    try:
        latest = GlobalNotification.query.order_by(GlobalNotification.timestamp.desc()).first()
        return dict(site_notice=latest.message if latest else None)
    except: return dict(site_notice=None)

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("home"))

if __name__ == "__main__": app.run(host='0.0.0.0', port=5000)

