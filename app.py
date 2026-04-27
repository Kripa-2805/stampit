import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from dotenv import load_dotenv
import watermark, deepfake, crawler, dmca, database
import youtube_analysis

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "stampit_secret_123")

# --- ROUTES ---

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username and password:
            session['user'] = username
            return redirect(url_for('dashboard'))
        flash("Please enter username and password.")
    return render_template('login.html')

@app.route('/signup', methods=['POST'])
def signup():
    fullname = request.form.get('fullname')
    email = request.form.get('email')
    password = request.form.get('password')
    flash("Account created successfully! Please login.")
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    stats = database.get_user_stats()
    analysis = session.pop('analysis_result', None)
    stamp_msg = session.pop('stamp_msg', None)
    return render_template('dashboard.html', stats=stats, analysis=analysis, stamp_msg=stamp_msg)

@app.route('/upload', methods=['POST'])
def upload():
    if 'user' not in session:
        return redirect(url_for('login'))
    file = request.files.get('video')
    if file and file.filename:
        try:
            stamped_path = watermark.stamp_video(file)
            database.store_video(stamped_path)
            session['stamp_msg'] = {
                "success": True,
                "message": "Video stamped & secured!",
                "filename": os.path.basename(stamped_path)
            }
        except Exception as e:
            session['stamp_msg'] = {"success": False, "message": f"Stamping failed: {str(e)}"}
    else:
        session['stamp_msg'] = {"success": False, "message": "No file selected."}
    return redirect(url_for('dashboard'))

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'user' not in session:
        return redirect(url_for('login'))
    url = request.form.get('video_url', '').strip()
    if not url:
        session['analysis_result'] = {"error": "Please paste a YouTube URL."}
    else:
        result = youtube_analysis.analyze_youtube_url(url)
        session['analysis_result'] = result
    return redirect(url_for('dashboard'))


@app.route('/generate_dmca', methods=['POST'])
def generate_dmca():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # Grabbing simulated data for the demo
    stolen_url = request.form.get('stolen_url', 'https://youtube.com/watch?v=suspicious_copy')
    original_url = request.form.get('original_url', 'StampIt Protected Library')
    
    try:
        filename = dmca.generate_takedown(session['user'], stolen_url, original_url)
        filepath = os.path.join('static/notices/', filename)
        flash("DMCA Takedown Notice generated successfully!")
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        flash(f"Error generating DMCA: {str(e)}")
        return redirect(url_for('dashboard'))

@app.route('/download/<filename>')
def download(filename):
    if 'user' not in session:
        return redirect(url_for('login'))
    filepath = os.path.join('static/protected', filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    flash("File not found.")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('landing'))

if __name__ == "__main__":
    app.run(debug=True)

