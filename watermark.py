import cv2           # OpenCV - reads and writes video frames
import numpy as np   # NumPy - handles image data as arrays of numbers
import uuid          # Built-in Python - generates unique IDs
import os
from imwatermark import WatermarkEncoder, WatermarkDecoder  # invisible-watermark library

PROTECTED_FOLDER = "protected"  # folder where stamped videos go

def generate_watermark_id():
    # uuid4() generates a completely random unique string like "a3f9-2b1c-..."
    # We take first 16 characters to keep it short
    return str(uuid.uuid4()).replace("-", "")[:16]

def embed_watermark(input_video_path, owner_name):
    """
    Takes a video file path, stamps it with invisible watermark,
    saves new stamped video, returns the unique stamp ID
    """

    # Step 1: Generate unique stamp ID for this video
    watermark_id = generate_watermark_id()
    # Convert stamp ID string into bytes (binary) - watermark needs binary data
    wm_text = watermark_id.encode("utf-8")

    # Step 2: Open the original video using OpenCV
    cap = cv2.VideoCapture(input_video_path)

    # Read video properties so our output video matches the original
    fps = cap.get(cv2.CAP_PROP_FPS)               # frames per second (e.g. 30)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))   # video width in pixels
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) # video height in pixels

    # Step 3: Set up output video file
    output_filename = f"protected_{watermark_id}.mp4"
    output_path = os.path.join(PROTECTED_FOLDER, output_filename)

    # VideoWriter creates a new video file
    # cv2.VideoWriter_fourcc sets video format (mp4v = MP4)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Step 4: Set up watermark encoder
    # "rivaGan" is the algorithm used for invisible watermarking
    encoder = WatermarkEncoder()
    encoder.set_watermark("bytes", wm_text)  # tell encoder what to stamp

    frame_count = 0
    while True:
        ret, frame = cap.read()  # ret=True if frame read successfully, frame = actual image
        if not ret:
            break  # No more frames, video is done

        # Only stamp every 5th frame to save processing time
        # Watermark will still be detectable even if not on every frame
        if frame_count % 5 == 0:
            try:
                # encode() actually embeds the invisible stamp into this frame
                # bgr means Blue-Green-Red color format (how OpenCV stores images)
                frame = encoder.encode(frame, "bgr")
            except Exception:
                pass  # If stamping fails on one frame, just skip it

        out.write(frame)  # Write this frame to output video
        frame_count += 1

    # Step 5: Close everything properly
    cap.release()   # Close input video
    out.release()   # Close output video (saves it to disk)

    return watermark_id, output_filename

def detect_watermark(video_path):
    """
    Checks a video for our invisible stamp.
    Returns the watermark ID if found, or None if not found.
    """

    cap = cv2.VideoCapture(video_path)
    decoder = WatermarkDecoder("bytes", 16 * 8)  # 16 chars * 8 bits each

    found_ids = []  # Collect all watermarks found across frames

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Only check every 10th frame for speed
        if frame_count % 10 == 0:
            try:
                # decode() reads the hidden stamp from this frame
                wm_bytes = decoder.decode(frame, "bgr")
                wm_text = wm_bytes.decode("utf-8", errors="ignore").strip()
                # Only keep it if it looks like a valid ID (16 alphanumeric chars)
                if len(wm_text) == 16 and wm_text.isalnum():
                    found_ids.append(wm_text)
            except Exception:
                pass

        frame_count += 1
        if frame_count > 100:  # Check max 100 frames for speed
            break

    cap.release()

    if not found_ids:
        return None

    # Return the most commonly found watermark ID across frames
    # (majority vote - more reliable than single frame)
    from collections import Counter
    most_common = Counter(found_ids).most_common(1)[0][0]
    return most_common
