import cv2
import numpy as np
import uuid
import os
from imwatermark import WatermarkEncoder, WatermarkDecoder

PROTECTED_FOLDER = "protected"

def generate_watermark_id():
    # uuid4 = random unique ID, take first 16 chars
    return str(uuid.uuid4()).replace("-", "")[:16]

def embed_watermark(input_video_path, owner_name):
    """
    Reads video frame by frame.
    Embeds invisible stamp in pixel values.
    Saves new stamped video.
    Returns (watermark_id, output_filename).
    """
    watermark_id = generate_watermark_id()
    wm_text = watermark_id.encode("utf-8")

    cap = cv2.VideoCapture(input_video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    output_filename = f"stamped_{watermark_id}.mp4"
    output_path = os.path.join(PROTECTED_FOLDER, output_filename)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # rivaGan = algorithm for invisible watermarking
    encoder = WatermarkEncoder()
    encoder.set_watermark("bytes", wm_text)

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % 5 == 0:  # stamp every 5th frame
            try:
                frame = encoder.encode(frame, "bgr")
            except Exception:
                pass
        out.write(frame)
        frame_count += 1

    cap.release()
    out.release()
    return watermark_id, output_filename

def detect_watermark(video_path):
    """
    Reads video, tries to extract hidden stamp from frames.
    Returns watermark_id string if found, None otherwise.
    """
    cap = cv2.VideoCapture(video_path)
    decoder = WatermarkDecoder("bytes", 16 * 8)  # 16 chars × 8 bits

    found_ids = []
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % 10 == 0:
            try:
                wm_bytes = decoder.decode(frame, "bgr")
                wm_text = wm_bytes.decode("utf-8", errors="ignore").strip()
                if len(wm_text) == 16 and wm_text.isalnum():
                    found_ids.append(wm_text)
            except Exception:
                pass
        frame_count += 1
        if frame_count > 100:
            break

    cap.release()

    if not found_ids:
        return None

    from collections import Counter
    return Counter(found_ids).most_common(1)[0][0]
