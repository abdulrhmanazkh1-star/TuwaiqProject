from functools import wraps
from urllib.parse import urlparse

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.models import User, db

auth_bp = Blueprint("auth", __name__)


@auth_bp.app_errorhandler(403)
def forbidden(_error):
    return render_template("auth/forbidden.html"), 403


@auth_bp.before_app_request
def load_and_require_user():
    endpoint = request.endpoint or ""
    if endpoint.startswith("static") or endpoint in {"auth.login", "auth.login_user", "auth.login_admin", "auth.register", "auth.register_admin"}:
        g.logged_in_user = None
        return
    user_id = session.get("user_id")
    g.logged_in_user = db.session.get(User, user_id) if user_id else None
    if not g.logged_in_user or not g.logged_in_user.is_active:
        session.pop("user_id", None)
        g.logged_in_user = None
        return redirect(url_for("auth.login", next=request.full_path if request.query_string else request.path))


@auth_bp.app_context_processor
def inject_user():
    return {"logged_in_user": getattr(g, "logged_in_user", None)}


def roles_required(*roles):
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not getattr(g, "logged_in_user", None):
                return redirect(url_for("auth.login"))
            if g.logged_in_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorate


def _safe_next(target):
    if not target:
        return url_for("main.home")
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc or not target.startswith("/") or target.startswith("//"):
        return url_for("main.home")
    return target


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if getattr(g, "logged_in_user", None):
        return redirect(url_for("main.home"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "user")
        user = User.query.filter_by(username=username).first()
        if role not in {"user", "admin"} or not user or user.role != role or not user.is_active or not check_password_hash(user.password_hash, password):
            flash("تعذر تسجيل الدخول. تحقق من اسم المستخدم وكلمة المرور ونوع الحساب.", "err")
        else:
            session.clear()
            session["user_id"] = user.id
            return redirect(_safe_next(request.form.get("next")))
    return render_template("auth/login.html", next_url=_safe_next(request.args.get("next")))


def _login_for_role(role):
    if getattr(g, "logged_in_user", None):
        return redirect(url_for("main.home"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if not user or user.role != role or not user.is_active or not check_password_hash(user.password_hash, password):
            flash("تعذر تسجيل الدخول. تحقق من اسم المستخدم وكلمة المرور.", "err")
        else:
            session.clear()
            session["user_id"] = user.id
            return redirect(_safe_next(request.form.get("next")))
    return render_template("auth/login_form.html", role=role, next_url=_safe_next(request.args.get("next")))


@auth_bp.route("/login/user", methods=["GET", "POST"])
def login_user():
    return _login_for_role("user")


@auth_bp.route("/login/admin", methods=["GET", "POST"])
def login_admin():
    return _login_for_role("admin")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if getattr(g, "logged_in_user", None):
        return redirect(url_for("main.home"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if len(username) < 3 or len(username) > 80:
            flash("اسم المستخدم يجب أن يكون بين 3 و80 حرفاً.", "err")
        elif len(password) < 8:
            flash("كلمة المرور يجب ألا تقل عن 8 أحرف.", "err")
        elif User.query.filter_by(username=username).first():
            flash("اسم المستخدم مستخدم مسبقاً.", "err")
        else:
            user = User(username=username, password_hash=generate_password_hash(password), role="user")
            db.session.add(user)
            db.session.commit()
            session.clear()
            session["user_id"] = user.id
            flash("تم إنشاء حساب المستخدم بنجاح.", "success")
            return redirect(url_for("main.home"))
    return render_template("auth/register.html")


@auth_bp.route("/register/admin", methods=["GET", "POST"])
def register_admin():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if len(username) < 3 or len(username) > 80:
            flash("اسم المستخدم يجب أن يكون بين 3 و80 حرفاً.", "err")
        elif len(password) < 8:
            flash("كلمة المرور يجب ألا تقل عن 8 أحرف.", "err")
        elif User.query.filter_by(username=username).first():
            flash("اسم المستخدم مستخدم مسبقاً.", "err")
        else:
            db.session.add(User(username=username, password_hash=generate_password_hash(password), role="admin"))
            db.session.commit()
            flash("تم إنشاء حساب المدير. يمكنك تسجيل الدخول به الآن.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register_admin.html")


@auth_bp.post("/logout")
def logout():
    session.clear()
    flash("تم تسجيل الخروج بنجاح.", "success")
    return redirect(url_for("auth.login"))


def bootstrap_admin():
    username = (current_app.config.get("ADMIN_USERNAME") or "").strip()
    password = current_app.config.get("ADMIN_PASSWORD") or ""
    if not username or not password or User.query.filter_by(username=username).first():
        return
    db.session.add(User(username=username, password_hash=generate_password_hash(password), role="admin"))
    db.session.commit()
