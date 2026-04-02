import os
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
# تغيير المفتاح لـ كسر أي حلقة قديمة في متصفحك فوراً
app.secret_key = os.environ.get('SECRET_KEY', "v3_stealth_mining_force_reset_2024")
app.permanent_session_lifetime = timedelta(days=7)

# إعداد قاعدة البيانات لملاءمة Vercel
if os.environ.get('VERCEL'):
    db_path = '/tmp/mining_vault_v3.sqlite'
else:
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'mining_vault_v3.sqlite')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"connect_args": {"timeout": 15}}

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(120), nullable=False)
    xmr_wallet = db.Column(db.String(200))
    xp = db.Column(db.Float, default=10.0)
    rank = db.Column(db.String(20), default="Miner")
    referral_code = db.Column(db.String(20), unique=True, index=True)
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

# --- معالج المستخدم الصارم (Hardened User Checker) ---
def get_user_v3():
    # استخدام مفتاح جلسة جديد v3
    uid = session.get("v3_miner_id")
    if not uid: return None
    try:
        user = User.query.get(uid)
        if not user:
            session.clear()
            return None
        return user
    except:
        session.clear()
        return None

# --- المسارات "النظيفة" (Clean Routes) ل كسر حلقة التوجيه ---

@app.route("/")
def landing_v3():
    # العودة لـ البداية دوماً ل كسر الحلقة ب شكل يدوي
    return render_template("landing.html", ref_code=request.args.get('ref'))

@app.route("/login", methods=["GET", "POST"])
def login_v3():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password")
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            session["v3_miner_id"] = user.id
            session.permanent = True
            return redirect(url_for("node_control"))
        flash("بيانات خاطئة", "error")
    return render_template("login.html")

@app.route("/register", methods=["POST"])
def register_v3():
    u = request.form.get("username", "").strip()
    p = request.form.get("password")
    w = request.form.get("wallet", "Node")
    if User.query.filter_by(username=u).first():
        return redirect(url_for("landing_v3"))
    
    new_user = User(username=u, password=p, xmr_wallet=w, referral_code=str(uuid.uuid4())[:8].upper())
    db.session.add(new_user); db.session.commit()
    session["v3_miner_id"] = new_user.id
    return redirect(url_for("node_control"))

@app.route("/portal/x/node")
def node_control():
    user = get_user_v3()
    if not user: return redirect(url_for("login_v3"))
    top_miners = User.query.order_by(User.xp.desc()).limit(5).all()
    ref_link = f"{request.url_root}?ref={user.referral_code}"
    return render_template("dashboard.html", user=user, top_miners=top_miners, ref_link=ref_link)

# --- تفعيل كل الخانات والممرات ل تقليل الثقل ---

@app.route("/portal/store")
def store():
    user = get_user_v3(); if not user: return redirect(url_for("login_v3"))
    return render_template("store.html", user=user)

@app.route("/portal/store/games")
def store_games():
    user = get_user_v3(); if not user: return redirect(url_for("login_v3"))
    return render_template("games.html", user=user)

@app.route("/api/v2/node/pulse", methods=["POST"])
def pulse_sync():
    user = get_user_v3(); if not user: return jsonify({"status": "fail"})
    user.xp += float(request.json.get("units", 1.66))
    db.session.commit()
    return jsonify({"status": "success", "xp": round(user.xp, 2)})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing_v3"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
