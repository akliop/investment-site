import os
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime, timedelta

# المحرك v12 - نظام الصدمة النهائية (Absolute Omega Engine)
app = Flask(__name__)
app.secret_key = str(uuid.uuid4()) # مفتاح عشوائي لكسر الجلسات القديمة
app.permanent_session_lifetime = timedelta(days=7)

# إعداد قاعدة البيانات v12
# إعداد قاعدة البيانات v12 - دعم قاعدة بيانات ثابتة
db_url = os.environ.get('DATABASE_URL') or os.environ.get('NEON_DATABASE_URL')
if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
elif os.environ.get('VERCEL'):
    db_path = '/tmp/vault_v12.sqlite'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
else:
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'vault_v12.sqlite')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(120), nullable=False)
    xp = db.Column(db.Float, default=10.0)
    referral_code = db.Column(db.String(20), unique=True)
    balance_usdt = db.Column(db.Float, default=0.0)
    is_admin = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

def get_sys_user():
    uid = session.get("v12_id")
    if not uid: return None
    try:
        user = User.query.get(uid)
        return user
    except: return None

# المسارات المطلقة (Absolute Routes)
@app.route("/")
def index_h():
    user = get_sys_user()
    if user: return redirect(url_for("portal_home"))
    return render_template("landing.html", ref_code=request.args.get('ref'))

# الرابط الجديد والحتمي لكسر الـ 404
@app.route("/join_node", methods=["POST"])
@app.route("/sync", methods=["POST"])
@app.route("/auth/v1/sync", methods=["GET", "POST"])
def auth_process():
    # الصدمة: تحويل كل الطرق لهذا المعالج
    if request.method == "GET": return redirect(url_for("index_h"))
    
    u = request.form.get("username", "").strip()
    p = request.form.get("password")
    
    if not u or not p: return redirect(url_for("index_h"))
    if User.query.filter_by(username=u).first():
        flash("عذراً، المستخدم محجوز", "error")
        return redirect(url_for("index_h"))

    try:
        new_u = User(username=u, password=p, referral_code=str(uuid.uuid4())[:8].upper())
        db.session.add(new_u); db.session.commit()
        session["v12_id"] = new_u.id
        session.permanent = True
        return redirect(url_for("portal_home"))
    except: return redirect(url_for("index_h"))

@app.route("/login", methods=["GET", "POST"])
def auth_login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password")
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            session["v12_id"] = user.id
            session.permanent = True
            return redirect(url_for("portal_home"))
        flash("خطأ في البيانات", "error")
    return render_template("login.html")

@app.route("/portal/home")
def portal_home():
    user = get_sys_user()
    if not user: return redirect(url_for("auth_login"))
    top_miners = User.query.order_by(User.xp.desc()).limit(5).all()
    ref_link = f"{request.url_root}?ref={user.referral_code}"
    return render_template("dashboard.html", user=user, top_miners=top_miners, ref_link=ref_link)

@app.route("/portal/store")
def portal_store():
    user = get_sys_user(); if not user: return redirect(url_for("auth_login"))
    return render_template("store.html", user=user)

@app.route("/logout")
def auth_logout():
    session.clear()
    return redirect(url_for("index_h"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
