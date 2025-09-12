# app.py
# C:\Users\parit\Desktop\SIH\Backend\app.py
from flask import Flask, request, jsonify, send_from_directory, url_for
from processing import process_image
from vectorize import create_vector
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
        return jsonify({"error": "no image part"}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "no selected file"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "file type not allowed, use png/jpg/jpeg"}), 400

    os.makedirs(TMP_DIR, exist_ok=True)
    # clear previous outputs
    try:
        for name in os.listdir(TMP_DIR):
            p = os.path.join(TMP_DIR, name)
            try:
                if os.path.isfile(p):
                    os.remove(p)
            except Exception:
                pass
    except Exception:
        pass
    filename = secure_filename(file.filename)
    uid = uuid.uuid4().hex
    ext = filename.rsplit('.', 1)[1].lower()
    input_filename = f"{uid}_input.{ext}"
    input_path = os.path.join(TMP_DIR, input_filename)
    file.save(input_path)

    # quick Pillow validation
    try:
        img = Image.open(input_path)
        img.verify()
    except Exception:
        return jsonify({"error": "invalid_image"}), 400

    # Call processing (may return 3 or 4-tuple). Handle both.
    try:
        result = process_image(input_path, debug=True)
    except Exception as e:
        return jsonify({"error": "processing_failed", "message": str(e)}), 500

    # unpack safely
    # result is expected like: (processed_path, dots, polylines [, debug_files])
    if not isinstance(result, (list, tuple)):
        return jsonify({"error": "processing_failed", "message": "invalid return from process_image"}), 500

    processed_path = result[0] if len(result) > 0 else None
    dots = result[1] if len(result) > 1 else []
    polylines = result[2] if len(result) > 2 and result[2] is not None else []
    debug_files = result[3] if len(result) > 3 else None

    # Normalize data -> plain python ints (JSON serializable)
    try:
        dots_list = [(int(x), int(y)) for (x, y) in dots]
    except Exception:
        # fallback: try flattening or empty
        dots_list = []

    try:
        polylines_list = []
        for poly in polylines:
            pts = []
            for (x, y) in poly:
                pts.append((int(x), int(y)))
            if pts:
                polylines_list.append(pts)
    except Exception:
        polylines_list = []

    # Create SVG from dots only (match _input_dotsmask.png semantics)
    svg_path = None
    try:
        svg_filename = f"{uid}_kolam.svg"
        svg_path = create_vector(dots_list, [], out_path=os.path.join(TMP_DIR, svg_filename))
    except Exception as e:
        # if SVG creation fails, continue but report
        return jsonify({"error": "svg_failed", "message": str(e)}), 500

    # Build absolute URLs for client consumption
    def to_url(path):
        if not path:
            return None
        # Accept absolute or relative; always map to /files/<fname>
        base, fname = os.path.split(path)
        return url_for('serve_file', filename=fname, _external=True)

    # Select specific recreated images to highlight
    recreated = []
    if isinstance(debug_files, dict):
        if debug_files.get('line_mask'):
            recreated.append(debug_files['line_mask'])
        if debug_files.get('edges'):
            recreated.append(debug_files['edges'])
        if debug_files.get('dots_mask'):
            recreated.append(debug_files['dots_mask'])

    # Prepare response (limit previews)
    response = {
        "input": to_url(input_path),
        "processed": to_url(processed_path),
        "svg": to_url(svg_path),
        "recreated": [to_url(p) for p in recreated] if recreated else None,
        "dots_count": len(dots_list),
        "dots_preview": dots_list[:50],
        "lines_count": len(polylines_list),
        "lines_preview": polylines_list[:10],  # first 10 polylines
        "debug_files": {k: to_url(v) for k, v in debug_files.items()} if isinstance(debug_files, dict) else None
    }

    return jsonify(response), 200


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)