from flask import Flask, request, render_template, send_file, jsonify
import os
import tempfile
from datetime import datetime
import subprocess
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def index():
    """Serve the main HTML form page"""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_report():
    try:
        # Extract form data
        participant_id = request.form.get('participant_id')
        start_date = request.form.get('start_date')
        output_format = request.form.get('output_format')
        
        logger.info(f"Received request: ID={participant_id}, Date={start_date}, Format={output_format}")
        
        # Validate inputs
        if not participant_id or not start_date or not output_format:
            return jsonify({"error": "Missing required fields"}), 400
        
        # Create a reports directory in current working directory
        reports_dir = os.path.join(os.getcwd(), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        # Define output files with extensions already included
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"report_{participant_id}_{timestamp}"
        
        # Include extension in the output path that's passed to the generator
        file_extension = ".html" if output_format == "html" else ".pdf"
        output_path = os.path.join(reports_dir, f"{output_filename}{file_extension}")
        
        logger.info(f"Output path: {output_path}")
        
        # Run the generator script
        cmd = [
            "python", 
            "report_generator.py",
            "--participant_id", participant_id,
            "--start_date", start_date,
            "--output_format", output_format,
            "--output_path", output_path  # Path with extension
        ]
        
        logger.info(f"Executing command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Print stdout/stderr for debugging
        logger.info(f"Script stdout: {result.stdout}")
        logger.error(f"Script stderr: {result.stderr}")
        
        if result.returncode != 0:
            return jsonify({"error": f"Report generation failed: {result.stderr}"}), 500
        
        # Check if the exact file exists
        if not os.path.exists(output_path):
            # List directory contents for debugging
            logger.error(f"Directory contents: {os.listdir(reports_dir)}")
            return jsonify({"error": "Output file was not created"}), 500
        
        logger.info(f"File found, serving: {output_path}")
        
        # Return file to user
        mimetype = "text/html" if output_format == "html" else "application/pdf"
        return send_file(
            output_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=f"{output_filename}{file_extension}"
        )
            
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    # For development only - use a production WSGI server in production
    app.run(debug=True, host='0.0.0.0', port=5000)