from flask import Flask, request, render_template, send_file, jsonify
import os
import tempfile
from datetime import datetime
import subprocess
import logging
import traceback
import time
import threading
import json


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def index():
    """Serve the main HTML form page"""
    return render_template('index.html')

@app.route('/progress/<task_id>')
def check_progress(task_id):
    progress_file = os.path.join("reports", f"{task_id}_progress.json")
    
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r') as f:
                content = f.read()
                if not content.strip():  # avoid empty file
                    raise ValueError("Progress file is empty")
                data = json.loads(content)
            return jsonify(data)
        except Exception as e:
            logger.error(f"Failed to read progress: {e}")
            return jsonify({"progress": 0, "message": "Reading progress failed"})
    else:
        return jsonify({"progress": 0, "message": "Starting..."})

@app.route('/download/<task_id>')
def download_report(task_id):
    try:
        # Look for file that matches this task ID
        reports_dir = os.path.join(os.getcwd(), "reports")
        for file in os.listdir(reports_dir):
            if task_id in file and (file.endswith(".html") or file.endswith(".pdf")):
                filepath = os.path.join(reports_dir, file)
                mimetype = "text/html" if file.endswith(".html") else "application/pdf"
                return send_file(filepath, mimetype=mimetype, as_attachment=False)
        return "Report not found", 404
    except Exception as e:
        return f"Error: {e}", 500



@app.route('/generate', methods=['POST'])
def generate_report():
    try:
        participant_id = request.form.get('participant_id')
        start_date = request.form.get('start_date')
        output_format = request.form.get('output_format')

        if not participant_id or not start_date or not output_format:
            return jsonify({"error": "Missing required fields"}), 400

        task_id = str(time.time())
        progress_file = os.path.join("reports", f"{task_id}_progress.json")
        output_filename = f"report_{participant_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        file_extension = ".html" if output_format == "html" else ".pdf"
        output_path = os.path.join("reports", f"{output_filename}{file_extension}")

        os.makedirs("reports", exist_ok=True)

        cmd = [
            "python", 
            "report_generator.py",
            "--participant_id", participant_id,
            "--start_date", start_date,
            "--output_format", output_format,
            "--output_path", output_path,
            "--progress_file", progress_file
        ]

        def run_report():
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    logger.error("Report generation failed with stderr:\n" + result.stderr)

                    with open(progress_file, 'w') as f:
                        json.dump({
                            "progress": -1,
                            "message": f"Report generation failed: {result.stderr.strip()}"
                        }, f)
                    return

                if not os.path.exists(output_path):
                    with open(progress_file, 'w') as f:
                        json.dump({
                            "progress": -1,
                            "message": "Report finished but output file not found."
                        }, f)
                    return

                with open(progress_file, 'w') as f:
                    json.dump({
                        "progress": 100,
                        "message": "Report ready!"
                    }, f)

            except Exception as e:
                logger.error(f"Unexpected error during report generation: {e}")
                with open(progress_file, 'w') as f:
                    json.dump({
                        "progress": -1,
                        "message": f"Unexpected error: {str(e)}"
                    }, f)


        threading.Thread(target=run_report).start()

        return jsonify({"task_id": task_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # For development only - use a production WSGI server in production
    app.run(host='0.0.0.0', port=5000, use_reloader=False)