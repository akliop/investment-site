import os
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import random
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', "stealth_mining_key_xmr_2024")

# إعداد قاعدة البيانات لملاءمة Vercel (ملاحظة: البيانات قد تفقد عند إعادة تشغيل السيرفر في Vercel)
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
    is_active = db.Column(db.Boolean, default=True)

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
    
    if not username or not password:
        flash("يرجى ملء كافة البيانات", "error")
        return redirect(url_for("landing"))

    if User.query.filter_by(username=username).first():
        flash("اسم المستخدم مستخدم بالفعل", "error")
        return redirect(url_for("landing"))

    new_user = User(
        username=username, password=password, xmr_wallet=wallet, 
        referral_code=str(uuid.uuid4())[:8].upper()
    )
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
    
    # حماية ضد بيانات Vercel المتطايرة: إذا لم يتم العثور على المستخدم، اخرج بهدوء
    if not user:
        session.pop("miner_id", None)
        return redirect(url_for("landing"))
    
    if not user.referral_code:
        user.referral_code = str(uuid.uuid4())[:8].upper()
        db.session.commit()
        
    top_miners = User.query.order_by(User.xp.desc()).limit(5).all()
    ref_link = f"{request.url_root}join?ref={user.referral_code}"
    return render_template("dashboard.html", user=user, top_miners=top_miners, ref_link=ref_link)

@app.route("/portal/deposit")
def deposit():
    if "miner_id" not in session: return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    if not user: return redirect(url_for("landing"))
    return render_template("deposit.html")

@app.route("/api/v2/node/pulse", methods=["POST"])
def pulse_sync():
    if "miner_id" not in session: return jsonify({"status": "fail"})
    user = User.query.get(session["miner_id"])
    if not user: return jsonify({"status": "fail"})
    
    reported_xp = int(request.json.get("units", 0))
    reported_balance = float(request.json.get("delta", 0.0))
    
    user.xp += reported_xp
    user.balance_xmr += reported_balance
    
    if user.xp > 10000: user.rank = "Miner Legend"
    elif user.xp > 5000: user.rank = "Miner Pro"
    elif user.xp > 1000: user.rank = "Miner Silver"
    db.session.commit()
    return jsonify({"status": "success", "xp": user.xp, "rank": user.rank})

@app.route("/logout")
def logout():
    session.pop("miner_id", None)
    return redirect(url_for("landing"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
