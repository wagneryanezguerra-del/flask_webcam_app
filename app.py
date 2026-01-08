from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import base64, re, os
from datetime import datetime
from PIL import Image
import io

app = Flask(__name__)

# --- CONFIGURACIÓN DE SEGURIDAD Y BASE DE DATOS ---
# Usa la variable de entorno de Render o una clave por defecto en local
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave-super-segura')

# Lógica para conectar a PostgreSQL en Render o SQLite en local
uri = os.environ.get("DATABASE_URL", "sqlite:///bambino.db")
if uri and uri.startswith("postgres://"):
    # Corrección obligatoria para SQLAlchemy 1.4+ en Render
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- CONFIGURACIÓN DE CORREO (Usa variables de entorno) ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME", "tu_correo@gmail.com")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD", "tu_app_password")
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
mail = Mail(app)
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

UPLOAD_FOLDER = os.path.join("static", "capturas")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ===== MODELOS =====
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ===== RUTAS =====
@app.route("/")
def home():
    if current_user.is_authenticated:
        return render_template("index.html")
    return render_template("landing.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        new_user = User(username=username, email=email, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Correo o contraseña incorrectos")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/capturar", methods=["POST"])
@login_required
def capturar():
    data = request.get_json()
    imagen_base64 = data.get('imagen')
    imagen_base64 = re.sub('^data:image/.+;base64,', '', imagen_base64)
    imagen_bytes = base64.b64decode(imagen_base64)

    imagen = Image.open(io.BytesIO(imagen_bytes))
    filename = f"{current_user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    imagen.save(filepath, format="PNG")

    foto = Photo(filename=filename, user_id=current_user.id)
    db.session.add(foto)
    db.session.commit()

    return jsonify({"message": "Imagen guardada", "filename": filename})

@app.route("/galeria")
@login_required
def galeria():
    fotos = Photo.query.filter_by(user_id=current_user.id).all()
    rutas = [url_for('static', filename=f"capturas/{foto.filename}") for foto in fotos]
    return render_template("galeria.html", imagenes=rutas)

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        user = User.query.filter_by(email=email).first()
        if user:
            token = s.dumps(email, salt="reset-password")
            link = url_for("reset_password", token=token, _external=True)
            msg = Message("Recuperar contraseña", recipients=[email])
            msg.body = f"Hola {user.username}, usa este enlace para resetear tu contraseña: {link}"
            mail.send(msg)
            return "Se ha enviado un correo con instrucciones."
        return render_template("forgot_password.html", error="Correo no registrado")
    return render_template("forgot_password.html")

@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        email = s.loads(token, salt="reset-password", max_age=3600)
    except:
        return "El enlace ha expirado o es inválido."
    user = User.query.filter_by(email=email).first()
    if request.method == "POST":
        nueva = request.form["password"]
        user.password_hash = bcrypt.generate_password_hash(nueva).decode("utf-8")
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("reset_password.html")

# ===== INICIO DEL SERVIDOR =====
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Crea las tablas en PostgreSQL al arrancar
    
    # Render asigna dinámicamente el puerto
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
