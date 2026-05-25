"""
server.py – Indofood Login Backend
===================================
Stack  : Python 3.10+, Flask, SQLAlchemy (SQLite default)
Install: pip install flask flask-sqlalchemy flask-cors bcrypt PyJWT

Run    : python server.py
API runs on: http://localhost:5000
"""

import os
import re
import uuid
import datetime
import logging

import bcrypt
import jwt
from flask import Flask, request, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# ─── App Configuration ──────────────────────────────────────────────
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # tighten in production

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.config.update(
    SQLALCHEMY_DATABASE_URI   = f"sqlite:///{os.path.join(BASE_DIR, 'indofood.db')}",
    SQLALCHEMY_TRACK_MODIFICATIONS = False,
    SECRET_KEY                = os.environ.get("SECRET_KEY", "indofood-secret-dev-key-change-in-prod"),
    JWT_ALGORITHM             = "HS256",
    JWT_EXPIRE_HOURS          = 8,       # session token lifetime
    JWT_REMEMBER_DAYS         = 30,      # "remember me" token lifetime
    MAX_LOGIN_ATTEMPTS        = 5,       # lockout after N failures
    LOCKOUT_MINUTES           = 15,      # lockout duration
)

db = SQLAlchemy(app)
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


# ─── Models ─────────────────────────────────────────────────────────

class User(db.Model):
    """Tabel utama pengguna."""
    __tablename__ = "users"

    id              = db.Column(db.Integer,     primary_key=True)
    uid             = db.Column(db.String(36),  unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name            = db.Column(db.String(120),  nullable=False)
    email           = db.Column(db.String(200),  unique=True, nullable=False, index=True)
    password_hash   = db.Column(db.String(200),  nullable=False)
    role            = db.Column(db.String(50),   default="user")       # user | admin
    department      = db.Column(db.String(100),  nullable=True)
    is_active       = db.Column(db.Boolean,      default=True)
    email_verified  = db.Column(db.Boolean,      default=False)
    login_attempts  = db.Column(db.Integer,      default=0)
    locked_until    = db.Column(db.DateTime,     nullable=True)
    last_login_at   = db.Column(db.DateTime,     nullable=True)
    created_at      = db.Column(db.DateTime,     default=datetime.datetime.utcnow)
    updated_at      = db.Column(db.DateTime,     default=datetime.datetime.utcnow,
                                onupdate=datetime.datetime.utcnow)

    login_logs = db.relationship("LoginLog", backref="user", lazy="dynamic")

    # ── Password helpers ──────────────────────────────────────────
    def set_password(self, plain: str):
        self.password_hash = bcrypt.hashpw(
            plain.encode(), bcrypt.gensalt(rounds=12)
        ).decode()

    def check_password(self, plain: str) -> bool:
        return bcrypt.checkpw(plain.encode(), self.password_hash.encode())

    # ── Lockout helpers ───────────────────────────────────────────
    def is_locked(self) -> bool:
        if self.locked_until and datetime.datetime.utcnow() < self.locked_until:
            return True
        return False

    def record_failed_attempt(self):
        self.login_attempts += 1
        if self.login_attempts >= app.config["MAX_LOGIN_ATTEMPTS"]:
            self.locked_until = (
                datetime.datetime.utcnow() +
                datetime.timedelta(minutes=app.config["LOCKOUT_MINUTES"])
            )
            log.warning(f"Account locked: {self.email} until {self.locked_until}")
        db.session.commit()

    def reset_attempts(self):
        self.login_attempts = 0
        self.locked_until   = None
        self.last_login_at  = datetime.datetime.utcnow()
        db.session.commit()

    # ── JWT generation ────────────────────────────────────────────
    def generate_token(self, remember: bool = False) -> str:
        delta = (
            datetime.timedelta(days=app.config["JWT_REMEMBER_DAYS"])
            if remember else
            datetime.timedelta(hours=app.config["JWT_EXPIRE_HOURS"])
        )
        payload = {
            "sub":   self.uid,
            "email": self.email,
            "name":  self.name,
            "role":  self.role,
            "iat":   datetime.datetime.utcnow(),
            "exp":   datetime.datetime.utcnow() + delta,
        }
        return jwt.encode(payload, app.config["SECRET_KEY"], algorithm=app.config["JWT_ALGORITHM"])

    def to_dict(self) -> dict:
        return {
            "id":           self.uid,
            "name":         self.name,
            "email":        self.email,
            "role":         self.role,
            "department":   self.department,
            "last_login":   self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at":   self.created_at.isoformat(),
        }


class LoginLog(db.Model):
    """Histori setiap percobaan login."""
    __tablename__ = "login_logs"

    id          = db.Column(db.Integer,  primary_key=True)
    user_id     = db.Column(db.Integer,  db.ForeignKey("users.id"), nullable=True)
    email       = db.Column(db.String(200))
    ip_address  = db.Column(db.String(50))
    user_agent  = db.Column(db.String(300))
    status      = db.Column(db.String(20))   # success | failed | locked
    reason      = db.Column(db.String(200), nullable=True)
    logged_at   = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class PasswordResetToken(db.Model):
    """Token reset password sekali pakai."""
    __tablename__ = "password_reset_tokens"

    id          = db.Column(db.Integer,   primary_key=True)
    user_id     = db.Column(db.Integer,   db.ForeignKey("users.id"), nullable=False)
    token       = db.Column(db.String(64), unique=True, nullable=False)
    expires_at  = db.Column(db.DateTime,  nullable=False)
    used        = db.Column(db.Boolean,   default=False)
    created_at  = db.Column(db.DateTime,  default=datetime.datetime.utcnow)


# ─── Helpers ─────────────────────────────────────────────────────────

def validate_email(email: str) -> bool:
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))


def get_client_ip() -> str:
    return (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or request.remote_addr
        or "unknown"
    )


def log_login(user, status: str, reason: str = None):
    entry = LoginLog(
        user_id    = user.id if user else None,
        email      = user.email if user else request.json.get("email", ""),
        ip_address = get_client_ip(),
        user_agent = request.headers.get("User-Agent", "")[:300],
        status     = status,
        reason     = reason,
    )
    db.session.add(entry)
    db.session.commit()


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, app.config["SECRET_KEY"], algorithms=[app.config["JWT_ALGORITHM"]])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_auth(f):
    """Decorator: endpoint butuh JWT yang valid."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "message": "Token tidak ditemukan."}), 401
        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token)
        if not payload:
            return jsonify({"success": False, "message": "Token tidak valid atau sudah kadaluarsa."}), 401
        user = User.query.filter_by(uid=payload["sub"], is_active=True).first()
        if not user:
            return jsonify({"success": False, "message": "Pengguna tidak ditemukan."}), 401
        g.current_user = user
        return f(*args, **kwargs)
    return decorated


# ─── Routes ──────────────────────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def api_login():
    """
    POST /api/login
    Body: { "email": str, "password": str, "remember": bool }
    """
    data = request.get_json(silent=True) or {}
    email    = (data.get("email")    or "").strip().lower()
    password =  data.get("password") or ""
    remember = bool(data.get("remember", False))

    # ── Basic validation ──────────────────────────────────────
    if not email or not password:
        return jsonify({"success": False, "message": "Email dan password harus diisi."}), 400
    if not validate_email(email):
        return jsonify({"success": False, "message": "Format email tidak valid."}), 400

    # ── Lookup user ───────────────────────────────────────────
    user = User.query.filter_by(email=email).first()

    if not user:
        # Return generic message to prevent email enumeration
        return jsonify({"success": False, "message": "Email atau password salah."}), 401

    if not user.is_active:
        return jsonify({"success": False, "message": "Akun Anda telah dinonaktifkan. Hubungi IT Support."}), 403

    if user.is_locked():
        remaining = int((user.locked_until - datetime.datetime.utcnow()).total_seconds() / 60) + 1
        log_login(user, "locked", f"Akun terkunci {remaining} menit lagi")
        return jsonify({
            "success": False,
            "message": f"Akun terkunci karena terlalu banyak percobaan login. Coba lagi dalam {remaining} menit."
        }), 429

    # ── Verify password ───────────────────────────────────────
    if not user.check_password(password):
        user.record_failed_attempt()
        log_login(user, "failed", "Password salah")
        attempts_left = max(0, app.config["MAX_LOGIN_ATTEMPTS"] - user.login_attempts)
        msg = "Email atau password salah."
        if 0 < attempts_left <= 2:
            msg += f" ({attempts_left} percobaan tersisa sebelum akun dikunci.)"
        return jsonify({"success": False, "message": msg}), 401

    # ── Login successful ──────────────────────────────────────
    user.reset_attempts()
    log_login(user, "success")
    token = user.generate_token(remember=remember)

    log.info(f"Login berhasil: {email} (remember={remember})")
    return jsonify({
        "success":      True,
        "message":      "Login berhasil.",
        "token":        token,
        "user":         user.to_dict(),
        "redirect_url": "/dashboard",
    })


@app.route("/api/logout", methods=["POST"])
@require_auth
def api_logout():
    """
    POST /api/logout
    Header: Authorization: Bearer <token>
    (JWT-based; no server-side invalidation needed for stateless approach)
    """
    log.info(f"Logout: {g.current_user.email}")
    return jsonify({"success": True, "message": "Anda telah keluar."})


@app.route("/api/forgot-password", methods=["POST"])
def api_forgot_password():
    """
    POST /api/forgot-password
    Body: { "email": str }
    """
    data  = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not validate_email(email):
        return jsonify({"success": False, "message": "Format email tidak valid."}), 400

    user = User.query.filter_by(email=email, is_active=True).first()
    if user:
        # Invalidate any existing tokens
        PasswordResetToken.query.filter_by(user_id=user.id, used=False).update({"used": True})

        token_str = uuid.uuid4().hex + uuid.uuid4().hex  # 64-char random token
        reset_token = PasswordResetToken(
            user_id    = user.id,
            token      = token_str,
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=2),
        )
        db.session.add(reset_token)
        db.session.commit()

        # ── In production: send email here ────────────────────
        reset_url = f"http://localhost:5000/reset-password?token={token_str}"
        log.info(f"[RESET LINK] {reset_url}")
        # e.g. send_reset_email(user.email, reset_url)

    # Always return success to prevent email enumeration
    return jsonify({
        "success": True,
        "message": "Jika email terdaftar, instruksi reset password telah dikirim.",
    })


@app.route("/api/me", methods=["GET"])
@require_auth
def api_me():
    """
    GET /api/me
    Header: Authorization: Bearer <token>
    Returns current user profile.
    """
    return jsonify({"success": True, "user": g.current_user.to_dict()})


@app.route("/api/login-history", methods=["GET"])
@require_auth
def api_login_history():
    """
    GET /api/login-history
    Header: Authorization: Bearer <token>
    Returns last 20 login records for the current user.
    """
    logs = (
        LoginLog.query
        .filter_by(user_id=g.current_user.id)
        .order_by(LoginLog.logged_at.desc())
        .limit(20)
        .all()
    )
    return jsonify({
        "success": True,
        "history": [
            {
                "status":     l.status,
                "ip_address": l.ip_address,
                "logged_at":  l.logged_at.isoformat(),
            }
            for l in logs
        ]
    })


# ─── Seed / Utility ──────────────────────────────────────────────────

def seed_demo_users():
    """Buat beberapa akun demo jika database kosong."""
    if User.query.count() > 0:
        return

    demo_accounts = [
        {"name": "Administrator",      "email": "admin@indofood.com",  "password": "admin123",  "role": "admin",  "department": "IT"},
        {"name": "User Indofood",       "email": "user@indofood.com",   "password": "user123",   "role": "user",   "department": "Operations"},
        {"name": "Demo Pengguna",       "email": "demo@perusahaan.com", "password": "demo123",   "role": "user",   "department": "Sales"},
    ]

    for acc in demo_accounts:
        u = User(
            name       = acc["name"],
            email      = acc["email"],
            role       = acc["role"],
            department = acc["department"],
            is_active  = True,
            email_verified = True,
        )
        u.set_password(acc["password"])
        db.session.add(u)

    db.session.commit()
    log.info("✅  Demo accounts created:")
    for acc in demo_accounts:
        log.info(f"    {acc['email']}  /  {acc['password']}")


# ─── Entry Point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_demo_users()

    log.info("🚀  Indofood Login Server running → http://localhost:5000")
    log.info("📦  Database: indofood.db (SQLite)")
    app.run(debug=True, host="0.0.0.0", port=5000)
