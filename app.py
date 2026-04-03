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

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False, index=True) # Gmail
    password = db.Column(db.String(120), nullable=False)
    jewels = db.Column(db.Float, default=0.0)
    xp = db.Column(db.Float, default=0.0)
    balance_usdt = db.Column(db.Float, default=0.0)
    referral_code = db.Column(db.String(20), unique=True)
    total_referrals = db.Column(db.Integer, default=0)
    referred_by = db.Column(db.Integer)
    is_pc = db.Column(db.Boolean, default=False)
    has_mined = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)

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
    type = db.Column(db.String(20))
    amount = db.Column(db.Float)
    details = db.Column(db.Text)
    status = db.Column(db.String(20), default="PENDING")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class GlobalNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# تهيئة الجداول بنظام v27
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"DB Error: {e}")

@app.route("/force_reset") # رابط سري لإصلاح الأخطاء يدوياً
def force_reset():
    try:
        db.drop_all()
        db.create_all()
        return "SUCCESS: Site Database Repaired! Go to Login now."
    except Exception as e:
        return f"ERROR: {str(e)}"

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
    top_miners = User.query.order_by(User.xp.desc()).limit(5).all()
    ref_link = f"{request.url_root}?ref={user.referral_code}"
    return render_template("dashboard.html", user=user, top_miners=top_miners, ref_link=ref_link)

@app.route("/portal/exchange")
@app.route("/portal/store")
@app.route("/portal/withdraw")
@app.route("/portal/referrals")
@app.route("/portal/orders")
def portal_pages():
    user = get_v_user(); if not user: return redirect(url_for("login"))
    p = request.path.split("/")[-1]
    # حساب الإحالات للـ Referrals
    mined_count = 0; pc_mined_count = 0
    if p == 'referrals':
        mined_count = User.query.filter_by(referred_by=user.id, has_mined=True).count()
        pc_mined_count = User.query.filter_by(referred_by=user.id, has_mined=True, is_pc=True).count()
    
    return render_template(f"{p}.html", user=user, mined_count=mined_count, pc_mined_count=pc_mined_count,
                           top_miners=User.query.order_by(User.xp.desc()).limit(5).all(),
                           ref_link=f"{request.url_root}?ref={user.referral_code}")

@app.route("/api/v2/node/pulse", methods=["POST"])
def pulse():
    user = get_v_user()
    if not user: return jsonify({"status": "fail"}), 401
    u = float(request.json.get("units", 3.0))
    user.jewels += u; user.xp += u; user.has_mined = True
    db.session.commit()
    return jsonify({"status": "success", "jewels": round(user.jewels, 2), "xp": round(user.xp, 2), "balance_usdt": round(user.balance_usdt, 2)})

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
