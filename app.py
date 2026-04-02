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
    xp = db.Column(db.Float, default=10.0)
    balance_usdt = db.Column(db.Float, default=0.0)
    referral_code = db.Column(db.String(20), unique=True)
    is_admin = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

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
    p = request.form.get("password")
    if not u or not p: return redirect(url_for("home"))
    if User.query.filter_by(username=u).first(): return redirect(url_for("login"))
    try:
        new_u = User(username=u, password=p, referral_code=str(uuid.uuid4())[:8].upper())
        db.session.add(new_u); db.session.commit()
        session["v20_id"] = new_u.id; session.permanent = True
        return redirect(url_for("dashboard"))
    except: return redirect(url_for("home"))

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

@app.route("/portal/store/games") # "شحن الألعاب"
def games_store():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    return render_template("games.html", user=user)

@app.route("/portal/withdraw") # "سحب" -> يفتح صفحة الإيداع
def withdraw():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    return render_template("recharge.html", user=user)

@app.route("/portal/withdraw/submit", methods=["POST"])
def withdraw_submit():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    flash("تم استلام طلب السحب بنجاح! سيتم معالجته خلال 24 ساعة.", "success")
    return redirect(url_for("withdraw"))

@app.route("/portal/referrals") # "الإحالات"
def referrals():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    return render_template("dashboard.html", user=user) # مدمج في لوحة التحكم

@app.route("/portal/recharge") # "إيداع"
def recharge():
    user = get_v_user()
    if not user: return redirect(url_for("login"))
    return render_template("store.html", user=user) # مدمج في المتجر

# --- محرك التعدين ---
@app.route("/api/v2/node/pulse", methods=["POST"])
def pulse():
    user = get_v_user()
    if not user: return jsonify({"status": "fail"})
    user.xp += float(request.json.get("units", 0.15))
    db.session.commit()
    return jsonify({"status": "success", "xp": round(user.xp, 2)})

@app.route("/sw.js")
def serve_sw():
    content = 'self.addEventListener("fetch", (event) => { });'
    return app.response_class(content, mimetype='application/javascript')

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
