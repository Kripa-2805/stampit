import os
import uuid
from flask import Flask, request, jsonify, render_template, send_file, session, redirect, url_for

from database import (init_db, create_user, verify_user, get_user_by_id,
                      save_protected_video, get_user_protected_videos,
                      save_detection, get_user_detections, get_user_stats,
                      mark_dmca_generated)
from watermark import embed_watermark, detect_watermark
from deepfake import detect_deepfake
from crawler import crawl_for_stolen_videos
from dmca import generate_dmca_notice

app = Flask(__name__)
# Secret key used to encrypt session cookies
# In production use a long random string — this keeps sessions secure
app.secret_key = "stampit_secret_key_change_this_in_production_2024"

UPLOAD_FOLDER = "uploads"
PROTECTED_FOLDER = "protected"
NOTICES_FOLDER = "notices"
ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv"}
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB max

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_current_user():
    # Check if user is logged in by looking at session
    # session is like a secure cookie that stores user_id
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(user_id)

def login_required(f):
    # Decorator — wraps routes that need login
    # If not logged in → return 401 error
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Please login first", "redirect": "/"}), 401
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    # If already logged in → go to dashboard
    if session.get("user_id"):
        return redirect("/dashboard")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect("/")
    user = get_current_user()
    return render_template("dashboard.html", user=user)

@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not all([username, email, password]):
        return jsonify({"error": "All fields required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    user_id, error = create_user(username, email, password)
    if error:
        return jsonify({"error": error}), 400

    # Auto login after signup — store user_id in session
    session["user_id"] = user_id
    session["username"] = username
    return jsonify({"success": True, "username": username})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = verify_user(username, password)
    if not user:
        return jsonify({"error": "Wrong username or password"}), 401

    # Store user info in session (encrypted cookie)
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return jsonify({"success": True, "username": user["username"]})

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()  # Delete all session data = logged out
    return jsonify({"success": True})

# ─────────────────────────────────────────────
# PROTECTED ROUTES (need login)
# ─────────────────────────────────────────────

@app.route("/api/protect", methods=["POST"])
@login_required
def protect_video():
    user = get_current_user()

    if "video" not in request.files:
        return jsonify({"error": "No video file"}), 400

    file = request.files["video"]
    owner_name = request.form.get("owner_name", user["username"])

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Use MP4, AVI, MOV or MKV"}), 400

    unique_prefix = str(uuid.uuid4())[:8]
    original_filename = f"{unique_prefix}_{file.filename}"
    upload_path = os.path.join(UPLOAD_FOLDER, original_filename)
    file.save(upload_path)

    try:
        watermark_id, protected_filename = embed_watermark(upload_path, owner_name)
        save_protected_video(user["id"], file.filename, protected_filename, watermark_id, owner_name)
        os.remove(upload_path)

        return jsonify({
            "success": True,
            "watermark_id": watermark_id,
            "protected_filename": protected_filename,
            "message": f"Video stamped! ID: {watermark_id}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/detect-fake", methods=["POST"])
@login_required
def detect_fake():
    user = get_current_user()

    if "video" not in request.files:
        return jsonify({"error": "No video file"}), 400

    file = request.files["video"]
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    temp_path = os.path.join(UPLOAD_FOLDER, f"tmp_{uuid.uuid4()}.mp4")
    file.save(temp_path)

    try:
        result = detect_deepfake(temp_path)
        if result["is_fake"]:
            save_detection(user["id"], f"upload:{file.filename}", "fake", result["confidence"])
        os.remove(temp_path)
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/check-watermark", methods=["POST"])
@login_required
def check_watermark():
    user = get_current_user()

    if "video" not in request.files:
        return jsonify({"error": "No video file"}), 400

    file = request.files["video"]
    temp_path = os.path.join(UPLOAD_FOLDER, f"chk_{uuid.uuid4()}.mp4")
    file.save(temp_path)

    try:
        found_id = detect_watermark(temp_path)
        os.remove(temp_path)

        if found_id:
            # Check if this watermark belongs to current user
            user_videos = get_user_protected_videos(user["id"])
            matched = next((v for v in user_videos if v["watermark_id"] == found_id), None)
            return jsonify({
                "success": True,
                "watermark_found": True,
                "watermark_id": found_id,
                "original_video": matched,
                "belongs_to_you": matched is not None
            })
        else:
            return jsonify({"success": True, "watermark_found": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/crawl", methods=["POST"])
@login_required
def crawl():
    user = get_current_user()
    data = request.get_json()
    owner_name = data.get("owner_name")
    original_filename = data.get("original_filename")
    watermark_id = data.get("watermark_id")

    if not all([owner_name, original_filename, watermark_id]):
        return jsonify({"error": "Missing fields"}), 400

    try:
        results = crawl_for_stolen_videos(user["id"], owner_name, original_filename, watermark_id)
        return jsonify({"success": True, "suspicious_count": len(results), "suspicious_videos": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/generate-dmca", methods=["POST"])
@login_required
def generate_dmca():
    data = request.get_json()
    owner_name = data.get("owner_name")
    stolen_url = data.get("stolen_url")
    original_filename = data.get("original_filename")
    watermark_id = data.get("watermark_id")
    detection_id = data.get("detection_id", "manual")

    if not all([owner_name, stolen_url, original_filename, watermark_id]):
        return jsonify({"error": "Missing fields"}), 400

    try:
        pdf_path, pdf_filename = generate_dmca_notice(
            owner_name, stolen_url, original_filename, watermark_id, detection_id
        )
        if detection_id != "manual":
            mark_dmca_generated(detection_id)
        return send_file(pdf_path, as_attachment=True,
                         download_name=pdf_filename, mimetype="application/pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/dashboard-data")
@login_required
def dashboard_data():
    user = get_current_user()
    return jsonify({
        "stats": get_user_stats(user["id"]),
        "protected_videos": get_user_protected_videos(user["id"]),
        "detections": get_user_detections(user["id"])
    })

@app.route("/download/<filename>")
@login_required
def download_protected(filename):
    file_path = os.path.join(PROTECTED_FOLDER, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    return send_file(file_path, as_attachment=True)

if __name__ == "__main__":
    for folder in [UPLOAD_FOLDER, PROTECTED_FOLDER, NOTICES_FOLDER]:
        os.makedirs(folder, exist_ok=True)
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
