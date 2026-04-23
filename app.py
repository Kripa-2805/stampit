import os
import uuid
from flask import Flask, request, jsonify, render_template, send_file

# Import all our custom modules
from database import init_db, save_protected_video, get_all_protected_videos, \
                     get_all_detections, get_stats, save_detection, mark_dmca_generated
from watermark import embed_watermark, detect_watermark
from deepfake import detect_deepfake
from crawler import crawl_for_stolen_videos
from dmca import generate_dmca_notice

# Create Flask app
app = Flask(__name__)

# Folder where uploaded (original) videos are temporarily stored
UPLOAD_FOLDER = "uploads"
PROTECTED_FOLDER = "protected"
NOTICES_FOLDER = "notices"
ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv"}  # Only these video formats allowed

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # Max upload size: 500MB

def allowed_file(filename):
    # Check if file extension is in our allowed list
    # "video.mp4".rsplit(".", 1) → ["video", "mp4"]
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ─────────────────────────────────────────────
# ROUTE 1: Home Page
# ─────────────────────────────────────────────
@app.route("/")
def index():
    # render_template() looks for index.html in the templates/ folder
    return render_template("index.html")

# ─────────────────────────────────────────────
# ROUTE 2: Protect a Video (Upload + Watermark)
# ─────────────────────────────────────────────
@app.route("/protect", methods=["POST"])
def protect_video():
    """
    Receives uploaded video + owner name.
    Stamps it with invisible watermark.
    Saves to database.
    Returns watermark ID and protected filename.
    """
    # Check if file was actually included in the request
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    file = request.files["video"]       # The uploaded video file
    owner_name = request.form.get("owner_name", "Unknown")  # Owner name from form

    # Check file is valid
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Use MP4, AVI, MOV, or MKV"}), 400

    # Save uploaded file temporarily
    # We add a UUID prefix to avoid name conflicts
    unique_prefix = str(uuid.uuid4())[:8]
    original_filename = f"{unique_prefix}_{file.filename}"
    upload_path = os.path.join(UPLOAD_FOLDER, original_filename)
    file.save(upload_path)  # Save to disk

    try:
        # Embed the invisible watermark stamp
        watermark_id, protected_filename = embed_watermark(upload_path, owner_name)

        # Save record to database
        save_protected_video(
            original_filename=file.filename,
            protected_filename=protected_filename,
            watermark_id=watermark_id,
            owner_name=owner_name
        )

        # Delete original upload (we only need the protected version)
        os.remove(upload_path)

        return jsonify({
            "success": True,
            "watermark_id": watermark_id,
            "protected_filename": protected_filename,
            "message": f"Video protected! Stamp ID: {watermark_id}"
        })

    except Exception as e:
        return jsonify({"error": f"Protection failed: {str(e)}"}), 500

# ─────────────────────────────────────────────
# ROUTE 3: Check a Video for Deepfake
# ─────────────────────────────────────────────
@app.route("/detect-fake", methods=["POST"])
def detect_fake():
    """
    Receives a video.
    Runs deepfake detection on it.
    Returns verdict (REAL or FAKE) with confidence score.
    """
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    file = request.files["video"]

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    # Save uploaded file temporarily for analysis
    temp_filename = f"temp_{uuid.uuid4()}.mp4"
    temp_path = os.path.join(UPLOAD_FOLDER, temp_filename)
    file.save(temp_path)

    try:
        # Run deepfake detection
        result = detect_deepfake(temp_path)

        # Save detection to database if it's fake
        if result["is_fake"]:
            save_detection(
                video_url=f"uploaded_file_{file.filename}",
                detection_type="fake",
                confidence=result["confidence"]
            )

        # Clean up temp file
        os.remove(temp_path)

        return jsonify({
            "success": True,
            "verdict": result["verdict"],
            "confidence": result["confidence"],
            "is_fake": result["is_fake"],
            "reason": result["reason"]
        })

    except Exception as e:
        return jsonify({"error": f"Detection failed: {str(e)}"}), 500

# ─────────────────────────────────────────────
# ROUTE 4: Check a Video for Stolen Watermark
# ─────────────────────────────────────────────
@app.route("/check-watermark", methods=["POST"])
def check_watermark():
    """
    Receives a suspicious video.
    Checks if it contains our invisible stamp.
    Returns which original video it belongs to.
    """
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    file = request.files["video"]
    temp_path = os.path.join(UPLOAD_FOLDER, f"check_{uuid.uuid4()}.mp4")
    file.save(temp_path)

    try:
        # Detect watermark in the video
        found_id = detect_watermark(temp_path)
        os.remove(temp_path)

        if found_id:
            # Look up which original video this watermark belongs to
            all_videos = get_all_protected_videos()
            matched_video = None
            for v in all_videos:
                if v["watermark_id"] == found_id:
                    matched_video = v
                    break

            return jsonify({
                "success": True,
                "watermark_found": True,
                "watermark_id": found_id,
                "original_video": matched_video,
                "message": "This video contains a Sports Shield watermark!"
            })
        else:
            return jsonify({
                "success": True,
                "watermark_found": False,
                "message": "No watermark detected in this video"
            })

    except Exception as e:
        return jsonify({"error": f"Check failed: {str(e)}"}), 500

# ─────────────────────────────────────────────
# ROUTE 5: Scan YouTube for Stolen Videos
# ─────────────────────────────────────────────
@app.route("/crawl", methods=["POST"])
def crawl():
    """
    Takes owner name + filename + watermark ID.
    Searches YouTube for potential stolen copies.
    Returns list of suspicious videos.
    """
    data = request.get_json()  # Parse JSON body from request
    owner_name = data.get("owner_name")
    original_filename = data.get("original_filename")
    watermark_id = data.get("watermark_id")

    if not all([owner_name, original_filename, watermark_id]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        suspicious_videos = crawl_for_stolen_videos(owner_name, original_filename, watermark_id)

        return jsonify({
            "success": True,
            "suspicious_count": len(suspicious_videos),
            "suspicious_videos": suspicious_videos
        })

    except Exception as e:
        return jsonify({"error": f"Crawl failed: {str(e)}"}), 500

# ─────────────────────────────────────────────
# ROUTE 6: Generate DMCA Notice PDF
# ─────────────────────────────────────────────
@app.route("/generate-dmca", methods=["POST"])
def generate_dmca():
    """
    Generates a DMCA takedown notice PDF for a detected stolen video.
    Returns the PDF file for download.
    """
    data = request.get_json()
    owner_name = data.get("owner_name")
    stolen_url = data.get("stolen_url")
    original_filename = data.get("original_filename")
    watermark_id = data.get("watermark_id")
    detection_id = data.get("detection_id", "manual")

    if not all([owner_name, stolen_url, original_filename, watermark_id]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        pdf_path, pdf_filename = generate_dmca_notice(
            owner_name, stolen_url, original_filename, watermark_id, detection_id
        )

        # Mark detection as having DMCA generated
        if detection_id != "manual":
            mark_dmca_generated(detection_id)

        # send_file() sends the PDF as a downloadable file
        return send_file(
            pdf_path,
            as_attachment=True,  # Forces browser to download instead of display
            download_name=pdf_filename,
            mimetype="application/pdf"
        )

    except Exception as e:
        return jsonify({"error": f"DMCA generation failed: {str(e)}"}), 500

# ─────────────────────────────────────────────
# ROUTE 7: Dashboard Data (for frontend)
# ─────────────────────────────────────────────
@app.route("/dashboard-data")
def dashboard_data():
    """Returns all data needed for the dashboard."""
    return jsonify({
        "stats": get_stats(),
        "protected_videos": get_all_protected_videos(),
        "detections": get_all_detections()
    })

# ─────────────────────────────────────────────
# ROUTE 8: Download a Protected Video
# ─────────────────────────────────────────────
@app.route("/download/<filename>")
def download_protected(filename):
    """Serves a protected (watermarked) video for download."""
    file_path = os.path.join(PROTECTED_FOLDER, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    return send_file(file_path, as_attachment=True)

# ─────────────────────────────────────────────
# Start the app
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Create folders if they don't exist
    for folder in [UPLOAD_FOLDER, PROTECTED_FOLDER, NOTICES_FOLDER]:
        os.makedirs(folder, exist_ok=True)

    # Initialize database (creates tables if needed)
    init_db()

    # Run Flask development server
    # debug=True means server auto-restarts when you edit code
    # host="0.0.0.0" means accessible from any device on your network
    app.run(debug=True, host="0.0.0.0", port=5000)
