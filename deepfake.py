import cv2        # OpenCV - for extracting frames from video
import os
import numpy as np
import tempfile     # Built-in - creates temporary files/folders

def extract_frames(video_path, num_frames=5):
    """
    Extracts a few sample frames from the video as image files.
    We don't analyze the whole video - just sample frames.
    Returns list of image file paths.
    """
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))  # total number of frames

    if total_frames == 0:
        cap.release()
        return []

    # Pick evenly spaced frame positions to sample
    # e.g. for 100 frames and 5 samples: positions = [10, 30, 50, 70, 90]
    positions = [int(total_frames * i / (num_frames + 1)) for i in range(1, num_frames + 1)]

    frame_paths = []
    temp_dir = tempfile.mkdtemp()  # Create a temporary folder to save frames

    for pos in positions:
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)  # Jump to this frame position
        ret, frame = cap.read()
        if ret:
            # Save this frame as a jpg image file
            frame_path = os.path.join(temp_dir, f"frame_{pos}.jpg")
            cv2.imwrite(frame_path, frame)
            frame_paths.append(frame_path)

    cap.release()
    return frame_paths

def analyze_frame_for_fake(frame_path):
    """
    Analyzes one frame to check if face looks real or AI-generated.
    Uses DeepFace library which has pre-trained models.
    Returns a score: higher = more likely fake.
    """
    try:
        from deepface import DeepFace

        # DeepFace.analyze() detects faces and analyzes them
        # actions=["emotion"] is lightweight - we just need face detection quality
        result = DeepFace.analyze(
            img_path=frame_path,
            actions=["emotion"],   # analyze emotion (this forces deep face scan)
            enforce_detection=False,  # Don't crash if no face found
            silent=True
        )

        # If DeepFace could analyze it normally, face looks real
        # We look at detection confidence as a proxy
        if isinstance(result, list):
            result = result[0]

        # Face region detection confidence - lower confidence = more suspicious
        face_confidence = result.get("face_confidence", 0.5)

        # Invert: low face confidence → high fake score
        fake_score = max(0, (1 - face_confidence) * 100)
        return fake_score

    except Exception as e:
        # If DeepFace fails completely, return neutral score
        return 50.0

def detect_deepfake(video_path):
    """
    Main function - takes a video path, returns:
    - is_fake: True or False
    - confidence: 0-100 (how sure we are it's fake)
    - verdict: "REAL" or "FAKE"
    """

    # Step 1: Extract sample frames from the video
    frames = extract_frames(video_path, num_frames=5)

    if not frames:
        # No frames extracted - can't analyze
        return {
            "is_fake": False,
            "confidence": 0,
            "verdict": "UNABLE TO ANALYZE",
            "reason": "Could not extract frames from video"
        }

    # Step 2: Analyze each frame and collect scores
    scores = []
    for frame_path in frames:
        score = analyze_frame_for_fake(frame_path)
        scores.append(score)

        # Clean up temp frame file after use
        try:
            os.remove(frame_path)
        except:
            pass

    # Step 3: Average all frame scores
    avg_score = sum(scores) / len(scores)

    # Step 4: Also check for unnatural pixel patterns
    # Real videos from cameras have natural noise; AI videos often have unnatural smoothness
    pixel_score = check_pixel_patterns(video_path)
    avg_score = (avg_score * 0.6) + (pixel_score * 0.4)  # Weighted average

    # Step 5: Decide verdict
    # Above 55 = likely fake (conservative threshold to reduce false alarms)
    is_fake = avg_score > 55

    return {
        "is_fake": is_fake,
        "confidence": round(avg_score, 1),
        "verdict": "FAKE" if is_fake else "REAL",
        "reason": f"Analysis based on {len(frames)} sampled frames"
    }

def check_pixel_patterns(video_path):
    """
    AI-generated videos often have unnaturally smooth/uniform pixel patterns.
    Real camera footage always has some grain/noise.
    This checks for that.
    Returns 0-100 fake score based on pixel analysis.
    """
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 30)  # Jump to frame 30
    ret, frame = cap.read()
    cap.release()

    if not ret:
        return 50.0

    # Convert to grayscale for simpler analysis
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Calculate standard deviation - measures how much pixel values vary
    # Real videos: high variation (natural noise) → lower fake score
    # AI videos: low variation (too smooth) → higher fake score
    std_dev = np.std(gray.astype(float))

    # Map std_dev to fake score
    # Very low std (< 10) = very suspicious
    # Normal std (> 40) = probably real
    if std_dev < 10:
        return 85.0
    elif std_dev < 20:
        return 65.0
    elif std_dev < 30:
        return 45.0
    else:
        return 20.0
