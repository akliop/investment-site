import os
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
# مفتاح أمان حديدي v6 لكسر أي تعليق
app.secret_key = os.environ.get('SECRET_KEY', "v6_mega_stable_mining_engine_2024")
app.permanent_session_lifetime = timedelta(days=7)

# إعداد قاعدة البيانات v6 الأكثر استقراراً
if os.environ.get('VERCEL'):
    db_path = '/tmp/vault_v6.sqlite'
else:
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'vault_v6.sqlite')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# نماذج البيانات المتكاملة (لا تحذف أبداً)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(120), nullable=False)
    xp = db.Column(db.Float, default=10.0)
    balance_usdt = db.Column(db.Float, default=0.0)
    referral_code = db.Column(db.String(20), unique=True)
    is_admin = db.Column(db.Boolean, default=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
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

# --- محرك الأمان v6 ---
def get_v6_user():
    uid = session.get("v6_id")
    if not uid: return None
    try:
        user = User.query.get(uid)
        if not user:
            session.clear(); return None
        return user
    except: return None

# --- الروابط الفولاذية (Iron Routes) ---

@app.route("/")
def index():
    user = get_v6_user()
    if user: return redirect(url_for("dashboard"))
    return render_template("landing.html", ref_code=request.args.get('ref'))

@app.route("/sync", methods=["GET", "POST"])
@app.route("/auth/v1/sync", methods=["GET", "POST"])
@app.route("/register", methods=["GET", "POST"])
def auth_register_sync():
    if request.method == "GET": return redirect(url_for("index"))
    u = request.form.get("username", "").strip()
    p = request.form.get("password")
    if not u or not p: return redirect(url_for("index"))
    if User.query.filter_by(username=u).first():
        flash("المستخدم موجود", "error")
        return redirect(url_for("index"))
    try:
        new_user = User(username=u, password=p, referral_code=str(uuid.uuid4())[:8].upper())
        db.session.add(new_user); db.session.commit()
        session["v6_id"] = new_user.id
        return redirect(url_for("dashboard"))
    except: return redirect(url_for("index"))

@app.route("/login", methods=["GET", "POST"])
def auth_login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password")
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            session["v6_id"] = user.id
            return redirect(url_for("dashboard"))
        flash("خطأ دخول", "error")
    return render_template("login.html")

@app.route("/portal/home")
def dashboard():
    user = get_v6_user()
    if not user: return redirect(url_for("auth_login"))
    top_miners = User.query.order_by(User.xp.desc()).limit(5).all()
    ref_link = f"{request.url_root}?ref={user.referral_code}"
    return render_template("dashboard.html", user=user, top_miners=top_miners, ref_link=ref_link)

# تفعيل كل الخدمات والممرات لضمان الاستقرار
@app.route("/portal/store")
def store():
    user = get_v6_user(); if not user: return redirect(url_for("auth_login"))
    return render_template("store.html", user=user)

@app.route("/portal/store/games")
def store_games():
    user = get_v6_user(); if not user: return redirect(url_for("auth_login"))
    return render_template("games.html", user=user)

@app.route("/api/v2/node/pulse", methods=["POST"])
def pulse():
    user = get_v6_user(); if not user: return jsonify({"status": "fail"})
    user.xp += float(request.json.get("units", 1.66))
    db.session.commit()
    return jsonify({"status": "success", "xp": round(user.xp, 2)})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
