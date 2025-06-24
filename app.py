from __future__ import annotations

import os
import sys
import json
import time
import logging
import threading
import subprocess
import pathlib
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    send_file,
    abort,
)
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
    UserMixin,
)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
import click

from user_repository import DynamoUserRepository, DynamoUser

HAVE_ADMIN = False

# ────────────────────────────────────────────────────────────────────────────
# Application factory
# ────────────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", os.urandom(24).hex()),
    SESSION_COOKIE_SECURE=True,      # Only send over HTTPS
    SESSION_COOKIE_HTTPONLY=True,    # Prevent JavaScript access
    SESSION_COOKIE_SAMESITE='Lax',   # Restrict cross-site usage
)

csrf = CSRFProtect(app)
user_repo = DynamoUserRepository()

# ────────────────────────────────────────────────────────────────────────────
# Paths
# ────────────────────────────────────────────────────────────────────────────
REPORT_ROOT = pathlib.Path(app.root_path) / "reports"   # source scripts
OUTPUT_ROOT = pathlib.Path(app.root_path) / "outputs"   # generated files + progress
OUTPUT_ROOT.mkdir(exist_ok=True)

# ────────────────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("dn‑reports")

# ────────────────────────────────────────────────────────────────────────────
# User model is now in user_repository.py as DynamoUser
# ────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────
# Authentication setup
# ────────────────────────────────────────────────────────────────────────────
login_mgr = LoginManager(app)
login_mgr.login_view = "login"

@login_mgr.user_loader
def load_user(user_id: str):
    return user_repo.get_by_id(user_id)

# ────────────────────────────────────────────────────────────────────────────
# CLI helpers
# ────────────────────────────────────────────────────────────────────────────
@app.cli.group()
def users():
    """User maintenance commands"""

@users.command("add")
@click.argument("username")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.option("--role", type=click.Choice(["user", "analyst", "admin"]), prompt=True)
@click.option("--site", default=None, help="Required for user/analyst; ignored for admin")
def add_user(username, password, role, site):
    if role != "admin" and not site:
        click.echo("Error: --site required for non‑admins"); return
    try:
        user_repo.create_user(
            username=username,
            password=password,
            role=role,
            site=None if role == "admin" else site
        )
        click.echo("✓ user created")
    except ValueError as e:
        click.echo(f"Error: {e}")

@users.command("list")
def list_users():
    for u in user_repo.list_all_users():
        click.echo(f"{u.id[:8]:8} {u.username:15} {u.role:8} {u.site or '-'}")

@users.command("delete")
@click.argument("username")
def delete_user(username):
    n = user_repo.delete_user(username)
    click.echo(f"✓ removed {n} users")

@users.command("passwd")
@click.argument("username")
def passwd(username):
    user = user_repo.get_by_username(username)
    if not user:
        click.echo("No such user"); return
    pw = click.prompt("new password", hide_input=True, confirmation_prompt=True)
    if user_repo.update_password(user.id, user.username, pw):
        click.echo("✓ password updated")
    else:
        click.echo("Error updating password")

@app.cli.command("create-admin")
def create_admin():
    """Bootstrap the very first admin account"""
    username = click.prompt("admin username")
    password = click.prompt("password", hide_input=True, confirmation_prompt=True)
    try:
        user_repo.create_user(username=username, password=password, role="admin")
        click.echo("✓ admin created")
    except ValueError as e:
        click.echo(f"Error: {e}")

# ────────────────────────────────────────────────────────────────────────────
# Helper: discover available report scripts for a user
# ────────────────────────────────────────────────────────────────────────────

def discover_reports_for(user: DynamoUser):
    """Return list[dict] of scripts {'site','file','label'} accessible to user."""
    if user.role == "admin":
        site_dirs = [p for p in REPORT_ROOT.iterdir() if p.is_dir()]
    else:
        site_dir = REPORT_ROOT / (user.site or "")
        site_dirs = [site_dir] if site_dir.is_dir() else []

    reports: list[dict] = []
    for site_dir in site_dirs:
        for file_path in site_dir.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
            reports.append({
                "site": site_dir.name,
                "file": file_path.name,
                "label": f"{site_dir.name} – {file_path.stem}",
            })
    return sorted(reports, key=lambda r: (r["site"], r["file"]))

# ────────────────────────────────────────────────────────────────────────────
# Routes
# ────────────────────────────────────────────────────────────────────────────
@app.before_request
def before_request():
    pass
    # Uncomment for production
    # if not request.is_secure and not app.debug:
    #     url = request.url.replace('http://', 'https://', 1)
    #     return redirect(url, code=301)

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        user = user_repo.get_by_username(request.form["username"].strip())
        if not user or not user.verify(request.form["password"]):
            flash("Invalid credentials", "danger"); return redirect(url_for("login"))
        login_user(user)
        user_repo.update_last_login(user.id, user.username)
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user(); return redirect(url_for("login"))

@app.route("/")
@login_required
def index():
    reports = discover_reports_for(current_user)
    if not reports:
        flash("No reports available", "warning")
    return render_template("index.html", reports=reports, user=current_user)

# ────────────────────────────────────────────────────────────────────────────
# Progress API
# ────────────────────────────────────────────────────────────────────────────
@app.route("/progress/<task_id>")
@login_required
def check_progress(task_id):
    pf = OUTPUT_ROOT / f"{task_id}_progress.json"
    if pf.exists():
        try:
            return jsonify(json.load(pf.open()))
        except Exception:
            pass
    return jsonify(progress=0, message="Starting…")

# ────────────────────────────────────────────────────────────────────────────
# Download endpoint
# ────────────────────────────────────────────────────────────────────────────
@app.route("/download/<task_id>")
@login_required
def download_report(task_id):
    for fp in OUTPUT_ROOT.iterdir():
        if task_id in fp.stem and fp.suffix in (".html", ".pdf"):
            mime = "text/html" if fp.suffix == ".html" else "application/pdf"
            return send_file(fp, mimetype=mime, as_attachment=False)
    abort(404, "Report not found")

# ────────────────────────────────────────────────────────────────────────────
# Generate endpoint
# ────────────────────────────────────────────────────────────────────────────
@app.route("/generate", methods=["POST"])
@login_required
def generate_report():
    participant_id = request.form.get("participant_id")
    start_date     = request.form.get("start_date")
    output_format  = request.form.get("output_format")
    report_id      = request.form.get("report_id")        # “site/script.py”

    if not all([participant_id, start_date, output_format, report_id]):
        return jsonify(error="Missing required fields"), 400

    try:
        site, script_name = report_id.split("/", 1)
    except ValueError:
        return jsonify(error="Bad report id"), 400

    # authorisation
    if current_user.role != "admin" and site != current_user.site:
        return jsonify(error="Not authorised for that site"), 403

    script_path = REPORT_ROOT / site / script_name
    if not script_path.is_file():
        return jsonify(error="Report script not found"), 404

    # filenames
    task_id       = str(time.time_ns())
    script_stem   = script_name.rsplit(".", 1)[0]
    progress_file = OUTPUT_ROOT / f"{task_id}_progress.json"
    ts            = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file   = OUTPUT_ROOT / (
        f"{script_stem}_{site}_{participant_id}_{ts}_{task_id}"
        f"{'.html' if output_format == 'html' else '.pdf'}"
    )

    cmd = [
        sys.executable, str(script_path),
        "--participant_id", participant_id,
        "--start_date",     start_date,
        "--output_format",  output_format,
        "--output_path",    str(output_file),
        "--progress_file",  str(progress_file),
    ]

    # run asynchronously
    def worker():
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            status = {"progress": 100, "message": "Report ready!"}

            if res.returncode != 0:
                status = {"progress": -1,
                          "message": res.stderr.splitlines()[-1] or 'Error'}
            elif not output_file.exists():
                status = {"progress": -1, "message": "Output file missing"}
        except Exception as e:
            status = {"progress": -1, "message": str(e)}

        json.dump(status, progress_file.open("w"))

    threading.Thread(target=worker, daemon=True).start()
    return jsonify(task_id=task_id)

# ────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, use_reloader=False)
