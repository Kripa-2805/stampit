import cv2
import os
import numpy as np
import tempfile

def extract_frames(video_path, num_frames=5):
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames == 0:
        cap.release()
        return []

    positions = [int(total_frames * i / (num_frames + 1)) for i in range(1, num_frames + 1)]
    frame_paths = []
    temp_dir = tempfile.mkdtemp()

    for pos in positions:
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ret, frame = cap.read()
        if ret:
            path = os.path.join(temp_dir, f"frame_{pos}.jpg")
            cv2.imwrite(path, frame)
            frame_paths.append(path)

    cap.release()
    return frame_paths

def analyze_frame(frame_path):
    """
    Uses DeepFace to scan face in frame.
    Low face confidence = more suspicious = higher fake score.
    """
    try:
        from deepface import DeepFace
        result = DeepFace.analyze(
            img_path=frame_path,
            actions=["emotion"],
            enforce_detection=False,
            silent=True
        )
        if isinstance(result, list):
            result = result[0]
        face_confidence = result.get("face_confidence", 0.5)
        return max(0, (1 - face_confidence) * 100)
    except Exception:
        return 50.0

def check_pixel_patterns(video_path):
    """
    AI videos are unnaturally smooth (low pixel variation).
    Real camera footage always has natural grain/noise.
    Low std_dev = suspicious.
    """
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 30)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        return 50.0

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    std_dev = np.std(gray.astype(float))

    if std_dev < 10:
        return 85.0
    elif std_dev < 20:
        return 65.0
    elif std_dev < 30:
        return 45.0
    else:
        return 20.0

def detect_deepfake(video_path):
    frames = extract_frames(video_path, num_frames=5)

    if not frames:
        return {"is_fake": False, "confidence": 0, "verdict": "UNABLE TO ANALYZE", "reason": "No frames extracted"}

    scores = []
    for fp in frames:
        score = analyze_frame(fp)
        scores.append(score)
        try:
            os.remove(fp)
        except:
            pass

    avg_score = sum(scores) / len(scores)
    pixel_score = check_pixel_patterns(video_path)
    avg_score = (avg_score * 0.6) + (pixel_score * 0.4)

    is_fake = avg_score > 55
    return {
        "is_fake": is_fake,
        "confidence": round(avg_score, 1),
        "verdict": "FAKE" if is_fake else "REAL",
        "reason": f"Analyzed {len(frames)} frames"
    }
