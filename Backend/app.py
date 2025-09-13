# app.py
# C:\Users\parit\Desktop\SIH\Backend\app.py
from flask import Flask, request, jsonify, send_from_directory, url_for
from processing import process_image
from vectorize import create_vector, create_vector_from_dotsmask
from werkzeug.utils import secure_filename
import os, uuid
from flask_cors import CORS
from PIL import Image

app = Flask(__name__)
CORS(app)   # dev only

# limit uploads (16 MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TMP_DIR = os.path.join(BASE_DIR, 'tmp')


@app.route('/')
def home():
    return "The KOLAM Backend is running successfully !!"


@app.route('/files/<path:filename>')
def serve_file(filename):
    # Serve files from tmp directory
    return send_from_directory(TMP_DIR, filename)

@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({"error": "no_file"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "no_filename"}), 400
        
    # Save uploaded file
    filename = secure_filename(file.filename)
    input_path = os.path.join('tmp', filename)
    file.save(input_path)

    try:
        # Process the image
        out_path, dots, polylines, debug = process_image(input_path)
        
        # Create response data with full URLs
        data = {
            "success": True,
            "dots_count": len(dots),
            "lines_count": len(polylines),
            "files": {
                "original": f"/files/{filename}",
                "processed": f"/files/input_processed.png",
                "recreated": f"/files/input_recreated.png" if os.path.exists('tmp/input_recreated.png') else None,
                "svg": f"/files/output.svg" if os.path.exists('tmp/output.svg') else None
            }
        }
        
        return jsonify(data)

    except Exception as e:
        print("Error processing image:", str(e))
        return jsonify({"error": "processing_failed", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))