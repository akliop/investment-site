import os
from flask import Flask, render_template, request, redirect, session, flash, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import random
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', "stealth_mining_key_xmr_2024")

# إعداد قاعدة بيانات المعدنين
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'mining_vault.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# نماذج البيانات (Mining & Gamification Models)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    xmr_wallet = db.Column(db.String(200))
    hashrate = db.Column(db.Float, default=0.0)
    balance_xmr = db.Column(db.Float, default=0.0)
    xp = db.Column(db.Integer, default=0)
    rank = db.Column(db.String(20), default="Miner")
    total_paid_xmr = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)

class MiningNode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    location = db.Column(db.String(50))
    power = db.Column(db.String(20))
    status = db.Column(db.String(20), default="Online")

# إنشاء قاعدة البيانات وتحديث الرتب
with app.app_context():
    db.create_all()
    # إضافة عقد تعدين افتراضية
    if not MiningNode.query.first():
        nodes = [
            MiningNode(name="Node-Alpha", location="Finland", power="12.5 KH/s"),
            MiningNode(name="Node-Zeta", location="Switzerland", power="45.2 KH/s"),
            MiningNode(name="Node-Stealth", location="Encrypted", power="105.0 KH/s")
        ]
        db.session.add_all(nodes)
        db.session.commit()

# --- المسارات (Routes) ---

@app.route("/")
def index():
    if "miner_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

@app.route("/how-it-works")
def payout_info():
    return render_template("payout_info.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password")
        wallet = request.form.get("wallet")
        
        if not username or not password:
            flash("يرجى ملء كافة البيانات", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(username=username).first():
            flash("اسم المستخدم مستخدم بالفعل", "error")
        else:
            new_user = User(username=username, password=password, xmr_wallet=wallet)
            db.session.add(new_user)
            db.session.commit()
            session["miner_id"] = new_user.id
            return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password")
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["miner_id"] = user.id
            return redirect(url_for("dashboard"))
        flash("خطأ في البيانات", "error")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "miner_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["miner_id"])
    nodes = MiningNode.query.all()
    top_miners = User.query.order_by(User.xp.desc()).limit(5).all()
    return render_template("dashboard.html", user=user, nodes=nodes, top_miners=top_miners)

@app.route("/api/mine", methods=["POST"])
def update_mining():
    if "miner_id" not in session: return jsonify({"success": False})
    user = User.query.get(session["miner_id"])
    
    cpu_limit = float(request.json.get("cpu_limit", 50)) / 100
    hash_speed = (5000 * cpu_limit) + random.uniform(-100, 100)
    
    user.xp += 1 
    user.balance_xmr += (hash_speed * 0.000000001)
    
    if user.xp > 10000: user.rank = "Miner Legend"
    elif user.xp > 5000: user.rank = "Miner Pro"
    elif user.xp > 1000: user.rank = "Miner Silver"

    db.session.commit()
    return jsonify({
        "success": True,
        "xp": user.xp,
        "rank": user.rank,
        "balance": f"{user.balance_xmr:.8f} XMR",
        "progress": min(100, (user.balance_xmr / 0.1) * 100)
    })

@app.route("/api/stats")
def stats():
    if "miner_id" not in session: return jsonify({})
    user = User.query.get(session["miner_id"])
    return jsonify({
        "balance": f"{user.balance_xmr:.8f} XMR",
        "progress": min(100, (user.balance_xmr / 0.1) * 100)
    })

@app.route("/logout")
def logout():
    session.pop("miner_id", None)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
