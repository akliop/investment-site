import os
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime, timedelta

# المحرك v14 (نظام الاستمرارية الموحد) - PWA & Root Support
app = Flask(__name__)
app.secret_key = "v14_akli_pwa_stealth_engine"
app.permanent_session_lifetime = timedelta(days=7)

if os.environ.get('VERCEL'):
    db_path = '/tmp/vault_v14.sqlite'
else:
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'vault_v14.sqlite')

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

def get_v_user():
    uid = session.get("v14_id")
    if not uid:
        return None
    try:
        user = User.query.get(uid)
        return user
    except:
        return None

# خدمة سكريبت الـ PWA الصامت
@app.route("/sw.js")
def serve_sw():
    content = 'self.addEventListener("fetch", (event) => { });'
    return app.response_class(content, mimetype='application/javascript')

@app.route("/")
def home():
    user = get_v_user()
    if user:
        return redirect(url_for("dashboard"))
    return render_template("landing.html", ref_code=request.args.get('ref'))

@app.route("/sync", methods=["GET", "POST"])
@app.route("/join_node", methods=["GET", "POST"])
@app.route("/auth/v1/sync", methods=["GET", "POST"])
def auth_sync():
    if request.method == "GET":
        return redirect(url_for("home"))
    
    u = request.form.get("username", "").strip()
    p = request.form.get("password")
    
    if not u or not p:
        return redirect(url_for("home"))
        
    if User.query.filter_by(username=u).first():
        flash("المستخدم موجود", "error")
        return redirect(url_for("home"))

    try:
        new_u = User(username=u, password=p, referral_code=str(uuid.uuid4())[:8].upper())
        db.session.add(new_u); db.session.commit()
        session["v14_id"] = new_u.id
        session.permanent = True
        return redirect(url_for("dashboard"))
    except:
        return redirect(url_for("home"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password")
        user = User.query.filter_by(username=u, password=p).first()
        if user:
            session["v14_id"] = user.id
            session.permanent = True
            return redirect(url_for("dashboard"))
        flash("بيانات خاطئة", "error")
    return render_template("login.html")

@app.route("/portal/home")
def dashboard():
    user = get_v_user()
    if not user:
        return redirect(url_for("login"))
    top_miners = User.query.order_by(User.xp.desc()).limit(5).all()
    ref_link = f"{request.url_root}?ref={user.referral_code}"
    return render_template("dashboard.html", user=user, top_miners=top_miners, ref_link=ref_link)

@app.route("/portal/store")
def store():
    user = get_v_user()
    if not user:
        return redirect(url_for("login"))
    return render_template("store.html", user=user)

@app.route("/api/v2/node/pulse", methods=["POST"])
def pulse():
    user = get_v_user()
    if not user:
        return jsonify({"status": "fail"})
    user.xp += float(request.json.get("units", 0.15))
    db.session.commit()
    return jsonify({"status": "success", "xp": round(user.xp, 2)})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
