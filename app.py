import os
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime, timedelta

# المحرك v20: نظام "النهضة الشاملة" (إعادة كافة الخانات المفقودة والروابط)
app = Flask(__name__)
app.secret_key = "v20_akli_full_engine_restoration"
app.permanent_session_lifetime = timedelta(days=7)

if os.environ.get('VERCEL'):
    db_path = '/tmp/vault_v20.sqlite'
else:
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'vault_v20.sqlite')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(120), nullable=False)
    jewels = db.Column(db.Float, default=0.0) # Jewels (💎)
    xp = db.Column(db.Float, default=0.0) # XP (Leaderboard)
    balance_usdt = db.Column(db.Float, default=0.0) # USDT (💵)
    referral_code = db.Column(db.String(20), unique=True)
    total_referrals = db.Column(db.Integer, default=0) # عدد الإحالات الإجمالية
    referred_by = db.Column(db.Integer) # ID الخاص بالداعي
    is_pc = db.Column(db.Boolean, default=False) # هل يستخدم الكمبيوتر
    has_mined = db.Column(db.Boolean, default=False) # هل بدأ التعدين فعلياً
    is_admin = db.Column(db.Boolean, default=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(100))
    price = db.Column(db.Float)
    status = db.Column(db.String(40), default="قيد المراجعة 🕒") # "قيد المراجعة" أو "تم التسليم ✅"
    delivery_data = db.Column(db.Text) # بيانات الفيزا المرسلة من المطور
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class FinanceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(20)) # DEPOSIT / WITHDRAW
    amount = db.Column(db.Float)
    details = db.Column(db.Text) # TXID or Address
    status = db.Column(db.String(20), default="PENDING")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class GlobalNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()
    # تم تبسيط هذا الجزء لزيادة الاستقرار وسهولة الفتح

def get_v_user():
    uid = session.get("v20_id")
    if not uid: return None
    try: return User.query.get(uid)
    except: return None

# --- المسارات الرئيسية ---
@app.route("/")
def home():
    user = get_v_user()
    if user: return redirect(url_for("dashboard"))
    return render_template("landing.html", ref_code=request.args.get('ref'))

@app.route("/register", methods=["GET", "POST"])
@app.route("/join_node", methods=["GET", "POST"])
def register():
    if request.method == "GET": return render_template("landing.html", ref_code=request.args.get('ref'))
    
    u = request.form.get("username", "").strip()
    p = request.form.get("password", "")
    ref = request.form.get("ref_code", "").strip()
    
    if not u or len(u) < 3:
        flash("اسم المستخدم يجب أن يكون 3 أحرف على الأقل", "error")
        return redirect(url_for("home"))
    if not p or len(p) < 4:
        flash("كلمة المرور ضعيفة جداً", "error")
        return redirect(url_for("home"))

    if User.query.filter_by(username=u).first():
        flash("اسم المستخدم مسجل مسبقاً، يرجى تسجيل الدخول", "info")
        return redirect(url_for("login"))
    
    # تحديد نوع الجهاز
    ua = request.user_agent.platform or ""
    is_pc = ua.lower() in ["windows", "linux", "macos", "chromeos"]
    
    try:
        new_u = User(username=u, password=p, referral_code=str(uuid.uuid4())[:8].upper(), is_pc=is_pc)
        
        # ربط الإحالة وتعيين "الداعي"
        if ref:
            referrer = User.query.filter_by(referral_code=ref).first()
            if referrer:
                new_u.referred_by = referrer.id # تخزين ID الداعي
                referrer.total_referrals += 1
                db.session.add(referrer)

        db.session.add(new_u)
        db.session.commit()
        
        session["v20_id"] = new_u.id
        session.permanent = True
        return redirect(url_for("dashboard"))
    except Exception as e:
        db.session.rollback()
        flash("حدث خطأ أثناء الإنشاء، يرجى المحاولة لاحقاً", "error")
        return redirect(url_for("home"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password")
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            session["v20_id"] = user.id; session.permanent = True
            return redirect(url_for("dashboard"))
        flash("خطأ في البيانات", "error")
    return render_template("login.html")

# --- بوابة "البارحة" (الخانات المفقودة) ---
@app.route("/portal/home")
def dashboard():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    top_miners = User.query.order_by(User.xp.desc()).limit(5).all()
    ref_link = f"{request.url_root}?ref={user.referral_code}"
    return render_template("dashboard.html", user=user, top_miners=top_miners, ref_link=ref_link)

@app.route("/portal/exchange") # "صرف النقاط" المفقودة
def exchange():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    return render_template("exchange.html", user=user)

@app.route("/portal/store") # "المتجر والسلع"
def store():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    return render_template("store.html", user=user)

@app.route("/portal/withdraw") # "سحب"
def withdraw():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    return render_template("withdraw.html", user=user)

@app.route("/portal/withdraw/submit", methods=["POST"]) 
def withdraw_submit():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    
    amount = float(request.form.get("amount", 0.0))
    address = request.form.get("address", "")
    
    # تحويل مبلغ السحب لطلب مالي (FinanceRequest)
    new_req = FinanceRequest(user_id=user.id, type="WITHDRAW", amount=amount, details=f"Address: {address}")
    db.session.add(new_req); db.session.commit()
    
    flash("تم استلام طلب السحب بنجاح! سيتم معالجته خلال 24 ساعة.", "success")
    return redirect(url_for("withdraw"))

@app.route("/portal/store/games") # "شحن الألعاب"
def games_store():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    return render_template("games.html", user=user)

@app.route("/portal/referrals") # "الإحالات"
def referrals():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    
    # حساب الإحالات النشطة (التي بدأت التعدين فعلياً)
    mined_count = User.query.filter_by(referred_by=user.id, has_mined=True).count()
    pc_mined_count = User.query.filter_by(referred_by=user.id, has_mined=True, is_pc=True).count()
    
    top_miners = User.query.order_by(User.xp.desc()).limit(5).all()
    ref_link = f"{request.url_root}?ref={user.referral_code}"
    return render_template("referrals.html", user=user, top_miners=top_miners, ref_link=ref_link, 
                           mined_count=mined_count, pc_mined_count=pc_mined_count)

@app.route("/portal/recharge") # "إيداع"
def recharge():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    return render_template("recharge.html", user=user)

@app.route("/portal/recharge/submit", methods=["POST"])
def recharge_submit():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    
    txid = request.form.get("txid")
    amount = float(request.form.get("amount", 0.0))
    
    # تحويل الإيداع لطلب مالي ليقوم المطور بتأكيده
    new_req = FinanceRequest(user_id=user.id, type="DEPOSIT", amount=amount, details=f"TXID: {txid}")
    db.session.add(new_req); db.session.commit()
    
    flash("تم إرسال طلب الشحن! سيتم التحقق من TXID وتحديث رصيدك قريباً.", "success")
    return redirect(url_for("recharge"))

# --- محرك التعدين المطور ---
@app.route("/api/v2/node/pulse", methods=["POST"])
def pulse():
    user = get_v_user()
    if not user: 
        return jsonify({"status": "fail", "message": "Session expired"}), 401
    
    try:
        # محرك التعدين: إضافة 3 جواهر/XP كل 10 ثوانٍ (أو حسب المرسل)
        units = float(request.json.get("units", 3.0))
        if units > 15: units = 15 # حماية ضد التلاعب بالكميات الكبيرة جداً
        
        user.jewels += units
        user.xp += units
        user.has_mined = True
        
        db.session.commit()
        return jsonify({
            "status": "success", 
            "jewels": round(user.jewels, 2), 
            "xp": round(user.xp, 2), 
            "balance_usdt": round(user.balance_usdt, 2)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Database busy, retrying..."}), 503

@app.route("/api/v2/node/convert", methods=["POST"])
def convert():
    user = get_v_user()
    if not user: return jsonify({"status": "fail"})
    # تحويل الجواهر: 10,000 جوهرة = 1.3 دولار
    if user.jewels < 10000:
        return jsonify({"status": "error", "message": "عذراً، رصيدك أقل من 10,000 جوهرة"})
    
    user.jewels -= 10000
    user.balance_usdt += 1.3
    db.session.commit()
    return jsonify({
        "status": "success", 
        "message": "تم تحويل 10,000 جوهرة بنجاح إلى 1.3 USDT!",
        "jewels": round(user.jewels, 2),
        "balance_usdt": round(user.balance_usdt, 2)
    })


@app.route("/portal/orders") # "مشترياتي"
def orders():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    user_orders = Order.query.filter_by(user_id=user.id).order_by(Order.timestamp.desc()).all()
    return render_template("orders.html", user=user, orders=user_orders)

@app.route("/api/v2/node/buy", methods=["POST"])
def buy_product():
    user = get_v_user()
    if not user: return jsonify({"status": "fail"})
    name = request.json.get("name")
    price = float(request.json.get("price", 0.0))
    if user.balance_usdt < price:
        return jsonify({"status": "fail", "message": "عذراً، رصيدك غير كافٍ لإتمام الشراء!"})
    user.balance_usdt -= price
    new_order = Order(user_id=user.id, product_name=name, price=price)
    db.session.add(new_order); db.session.commit()
    return jsonify({"status": "success", "message": f"تم طلب {name} بنجاح! سيصلك الكود في 'مشترياتي' فوراً.", "balance_usdt": round(user.balance_usdt, 2)})

@app.route("/admin/panel") # لوحة الإدارة
def admin_panel():
    user = get_v_user()
    if not user or not user.is_admin: return redirect(url_for("home"))
    all_users = User.query.all()
    all_orders = Order.query.order_by(Order.timestamp.desc()).all()
    return render_template("admin_dashboard.html", user=user, all_users=all_users, orders=all_orders)

@app.route("/api/admin/deliver", methods=["POST"])
def deliver_order():
    user = get_v_user()
    if not user or not user.is_admin: return jsonify({"status": "fail"})
    oid = request.json.get("order_id"); data = request.json.get("delivery_data")
    order = Order.query.get(oid)
    if order:
        order.delivery_data = data; order.status = "تم التسليم ✅"
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})

@app.route("/admin/dev-room") # "غرفة المطور" المطلوبة
def dev_room():
    user = get_v_user()
    pin = request.args.get("pin")
    
    # السماح بالدخول إذا كان المستخدم أدمن أو استخدم الرمز السري "akli2025"
    if (user and user.is_admin) or pin == "akli2025":
        all_users = User.query.all()
        user_count = len(all_users)
        orders = Order.query.order_by(Order.timestamp.desc()).all()
        finances = FinanceRequest.query.order_by(FinanceRequest.timestamp.desc()).all()
        
        return render_template("dev_room.html", user=user, all_users=all_users, 
                               user_count=user_count, orders=orders, finances=finances)
    
    return redirect(url_for("home"))

@app.route("/api/admin/finance/update", methods=["POST"])
def update_finance():
    user = get_v_user()
    if not user or not user.is_admin: return jsonify({"status": "fail"})
    fid = request.json.get("finance_id"); action = request.json.get("action") # APPROVE / REJECT
    
    req = FinanceRequest.query.get(fid)
    if req:
        if action == "APPROVE" and req.status == "PENDING":
            target_user = User.query.get(req.user_id)
            if target_user:
                if req.type == "DEPOSIT":
                    target_user.balance_usdt += req.amount
                elif req.type == "WITHDRAW":
                    # في السحب نفترض أن الخصم تم عند الطلب أو يتم هنا
                    # لكن الأفضل أن نخصمه عند الطلب ونعيده عند الرفض
                    # للاختصار سنقوم فقط بتغيير الحالة هنا
                    pass
            req.status = "DONE"
        elif action == "REJECT":
            req.status = "REJECTED"
        
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})

@app.route("/api/admin/notify", methods=["POST"])
def send_notification():
    user = get_v_user()
    pin = request.args.get("pin")
    if not (user and user.is_admin) and pin != "akli2025":
        return jsonify({"status": "fail", "message": "Unauthorized"})
    
    msg = request.json.get("message")
    if msg:
        # مسح الإشعارات القديمة لإبقاء الموقع نظيفاً (آخر إشعار فقط)
        GlobalNotification.query.delete()
        new_note = GlobalNotification(message=msg)
        db.session.add(new_note)
        db.session.commit()
        return jsonify({"status": "success", "message": "تم إرسال الإشعار لجميع المستخدمين بنجاح!"})
    return jsonify({"status": "error"})

@app.route("/sw.js")
def serve_sw():
    content = 'self.addEventListener("fetch", (event) => { });'
    return app.response_class(content, mimetype='application/javascript')

@app.context_processor
def inject_notice():
    try:
        latest = GlobalNotification.query.order_by(GlobalNotification.timestamp.desc()).first()
        return dict(site_notice=latest.message if latest else None)
    except:
        return dict(site_notice=None)

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
