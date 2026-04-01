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

# نماذج البيانات (Mining Models)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    xmr_wallet = db.Column(db.String(200)) # عنوان محفظة Monero
    hashrate = db.Column(db.Float, default=0.0) # سرعة التعدين الحالية (H/s)
    balance_xmr = db.Column(db.Float, default=0.0) # الرصيد المجمع بالـ XMR
    total_paid_xmr = db.Column(db.Float, default=0.0) # إجمالي ما تم دفعه للمحفظة
    is_active = db.Column(db.Boolean, default=True)

class MiningNode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    location = db.Column(db.String(50))
    power = db.Column(db.String(20)) # e.g. 1500 H/s
    status = db.Column(db.String(20), default="Online")

# إنشاء قاعدة البيانات في بيئة التطبيق
with app.app_context():
    db.create_all()
    # إضافة عقد تعدين افتراضية عالمية
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

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        wallet = request.form.get("wallet")
        
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
        username = request.form.get("username")
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
    # محاكاة زيادة بسيطة في التعدين عند التحديث
    if user.hashrate > 0:
        added_profit = (user.hashrate * 0.00000001) * random.uniform(0.8, 1.2)
        user.balance_xmr += added_profit
        db.session.commit()
        
    return render_template("dashboard.html", user=user, nodes=nodes)

@app.route("/api/stats")
def stats():
    # لجلب البيانات حية عبر AJAX (Hashrate real-time)
    if "miner_id" not in session: return jsonify({})
    user = User.query.get(session["miner_id"])
    return jsonify({
        "hashrate": f"{user.hashrate:,.2f} H/s",
        "balance": f"{user.balance_xmr:.8f} XMR",
        "progress": min(100, (user.balance_xmr / 0.1) * 100) # نسبة الوصول لـ 0.1 XMR
    })

@app.route("/logout")
def logout():
    session.pop("miner_id", None)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
