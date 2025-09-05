from __future__ import annotations

import os
import sys
import json
import time
import logging
import pathlib
from datetime import datetime
import boto3

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
)
from flask_wtf.csrf import CSRFProtect
import click

from user_repository import DynamoUserRepository, DynamoUser
from parameter_store import parameter_store

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

# AWS clients
ecs_client = boto3.client('ecs')
s3_client = boto3.client('s3')

# ────────────────────────────────────────────────────────────────────────────
# Paths and Configuration
# ────────────────────────────────────────────────────────────────────────────
OUTPUT_ROOT = pathlib.Path(app.root_path) / "outputs"   # local temp files for compatibility
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
# Helper: discover available reports for a user
# ────────────────────────────────────────────────────────────────────────────

def discover_reports_for(user: DynamoUser):
    """Return list[dict] of reports {'site','file','label'} accessible to user."""
    # For now, hardcode the available reports. Later this could be dynamic
    all_reports = [
        {
            "site": "bidmc",
            "file": "social_media_dn_report.py",
            "label": "BIDMC – Social Media DN Report",
        }
    ]
    
    if user.role == "admin":
        return all_reports
    else:
        # Filter reports by user's site
        return [r for r in all_reports if r["site"] == user.site]

# ────────────────────────────────────────────────────────────────────────────
# Routes
# ────────────────────────────────────────────────────────────────────────────
@app.route("/service/healthz")
def healthz():
    return jsonify({
        "status": "healthy",
        "service": "data-reports"
    }), 200

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
    try:
        bucket_name = parameter_store.get_parameter('REPORT_BUCKET')
        
        # Search for progress file in the hierarchical structure
        response = s3_client.list_objects_v2(
            Bucket=bucket_name, 
            Prefix=f'progress/',
            Delimiter='/'
        )
        
        # Find the progress file for this task_id
        for obj in response.get('Contents', []):
            if obj['Key'].endswith(f'{task_id}.json'):
                progress_response = s3_client.get_object(Bucket=bucket_name, Key=obj['Key'])
                return jsonify(json.loads(progress_response['Body'].read()))
        
        return jsonify(progress=0, message="Starting…")
    except Exception as e:
        logger.error(f"Progress check error: {e}")
        return jsonify(progress=0, message="Error checking progress")

# ────────────────────────────────────────────────────────────────────────────
# Download endpoint
# ────────────────────────────────────────────────────────────────────────────
@app.route("/download/<task_id>")
@login_required
def download_report(task_id):
    try:
        bucket_name = parameter_store.get_parameter('REPORT_BUCKET')
        
        # List objects to find the report file
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=f'outputs/')
        
        for obj in response.get('Contents', []):
            if task_id in obj['Key'] and obj['Key'].endswith(('.html', '.pdf')):
                # Generate presigned URL for download
                url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket_name, 'Key': obj['Key']},
                    ExpiresIn=3600
                )
                return redirect(url)
        
        abort(404, "Report not found")
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        abort(500, "Error retrieving report")

# ────────────────────────────────────────────────────────────────────────────
# Generate endpoint
# ────────────────────────────────────────────────────────────────────────────
@app.route("/generate", methods=["POST"])
@login_required
def generate_report():
    participant_id = request.form.get("participant_id")
    start_date = request.form.get("start_date")
    output_format = request.form.get("output_format")
    report_id = request.form.get("report_id")  # "site/script.py"

    if not all([participant_id, start_date, output_format, report_id]):
        return jsonify(error="Missing required fields"), 400

    try:
        site, script_name = report_id.split("/", 1)
    except ValueError:
        return jsonify(error="Bad report id"), 400

    # authorization
    if current_user.role != "admin" and site != current_user.site:
        return jsonify(error="Not authorised for that site"), 403

    # Generate task ID and S3 paths
    task_id = str(time.time_ns())
    script_stem = script_name.rsplit(".", 1)[0]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        bucket_name = parameter_store.get_parameter('REPORT_BUCKET')
        output_key = f"outputs/{site}/{script_stem}/{script_stem}_{participant_id}_{ts}_{task_id}.{output_format}"
        progress_key = f"progress/{site}/{script_stem}/{task_id}.json"
        
        output_path = f"s3://{bucket_name}/{output_key}"
        progress_file = f"s3://{bucket_name}/{progress_key}"

        # Get ECS configuration
        cluster_name = parameter_store.get_parameter('ECS_CLUSTER')
        subnet_id = parameter_store.get_parameter('SUBNET_ID')
        security_group_id = parameter_store.get_parameter('SECURITY_GROUP_ID')
        
        # Get LAMP credentials from Parameter Store
        lamp_access_key = parameter_store.get_parameter('LAMP_ACCESS_KEY')
        lamp_secret_key = parameter_store.get_parameter('LAMP_SECRET_KEY')
        lamp_server_address = parameter_store.get_parameter('LAMP_SERVER_ADDRESS')

        # Run ECS task
        response = ecs_client.run_task(
            cluster=cluster_name,
            taskDefinition=f'lamp-data-reports-dev',
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': [subnet_id],
                    'securityGroups': [security_group_id],
                    'assignPublicIp': 'ENABLED'
                }
            },
            overrides={
                'containerOverrides': [
                    {
                        'name': 'data-reports',
                        'environment': [
                            {'name': 'LAMP_ACCESS_KEY', 'value': lamp_access_key},
                            {'name': 'LAMP_SECRET_KEY', 'value': lamp_secret_key},
                            {'name': 'LAMP_SERVER_ADDRESS', 'value': lamp_server_address},
                            {'name': 'TASK_ID', 'value': task_id}
                        ],
                        'command': [
                            '--participant_id', participant_id,
                            '--start_date', start_date,
                            '--output_format', output_format,
                            '--output_path', output_path,
                            '--progress_file', progress_file,
                        ]
                    }
                ]
            }
        )
        
        logger.info(f"Started ECS task for report {report_id}, task_id: {task_id}")
        return jsonify(task_id=task_id)
        
    except Exception as e:
        logger.error(f"Failed to start ECS task: {e}")
        return jsonify(error="Failed to start report generation"), 500

# ────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), use_reloader=False)