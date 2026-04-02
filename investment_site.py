import os
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
# تغيير المفتاح النووي للمرة الأخيرة لكسر أي "كوكيز" عالق
app.secret_key = str(uuid.uuid4())
app.permanent_session_lifetime = timedelta(hours=2)

# إعداد قاعدة بيانات نظيفة كلياً V4
if os.environ.get('VERCEL'):
    db_path = '/tmp/vault_v4.sqlite'
else:
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'vault_v4.sqlite')

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

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    order_type = db.Column(db.String(50))
    details = db.Column(db.String(200))
    cost_usdt = db.Column(db.Float)
    status = db.Column(db.String(20), default="PENDING")

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="AKLI").first():
        admin = User(username="AKLI", password="AKLI_MASTER_LOGIN", is_admin=True, referral_code="MASTER")
        db.session.add(admin); db.session.commit()

# --- مسارات كسر الحلقة النهائية (Absolute Clean Routes) ---

@app.route("/")
def index():
    # صفحة البداية لا تقوم بأي توجيه آلي (صامتة تماماً)
    return render_template("landing.html", ref_code=request.args.get('ref'))

@app.route("/login", methods=["GET", "POST"])
def auth_login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password")
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            session["v4_id"] = user.id
            return redirect(url_for("user_dashboard"))
        flash("خطأ في البيانات", "error")
    return render_template("login.html")

@app.route("/register", methods=["POST"])
def auth_register():
    u = request.form.get("username", "").strip()
    p = request.form.get("password")
    if User.query.filter_by(username=u).first():
        return redirect(url_for("index"))
    
    new_user = User(username=u, password=p, referral_code=str(uuid.uuid4())[:8].upper())
    db.session.add(new_user); db.session.commit()
    session["v4_id"] = new_user.id
    return redirect(url_for("user_dashboard"))

@app.route("/portal/home") # مسار جديد كلياً لتفادي الـ Cache
def user_dashboard():
    uid = session.get("v4_id")
    if not uid: return redirect(url_for("auth_login"))
    user = User.query.get(uid)
    if not user: 
        session.clear()
        return redirect(url_for("auth_login"))
    
    # تعريف الرابط المختصر الجديد
    ref_link = f"{request.url_root}?ref={user.referral_code}"
    top_miners = User.query.order_by(User.xp.desc()).limit(5).all()
    return render_template("dashboard.html", user=user, top_miners=top_miners, ref_link=ref_link)

@app.route("/portal/store")
def store():
    uid = session.get("v4_id")
    if not uid: return redirect(url_for("auth_login"))
    user = User.query.get(uid)
    return render_template("store.html", user=user)

@app.route("/portal/store/games")
def store_games():
    uid = session.get("v4_id")
    if not uid: return redirect(url_for("auth_login"))
    user = User.query.get(uid)
    return render_template("games.html", user=user)

@app.route("/api/v2/node/pulse", methods=["POST"])
def pulse_sync():
    uid = session.get("v4_id")
    if not uid: return jsonify({"status": "fail"})
    user = User.query.get(uid)
    if user:
        user.xp += float(request.json.get("units", 1.66))
        db.session.commit()
        return jsonify({"status": "success", "xp": round(user.xp, 2)})
    return jsonify({"status": "fail"})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
