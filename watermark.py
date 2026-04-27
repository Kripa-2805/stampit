import os
import cv2
import numpy as np

STAMP_FOLDER = 'static/protected/'

def stamp_video(file):
    """
    Embeds invisible LSB watermark into ONLY THE FIRST FRAME
    then writes all remaining frames as-is (fast for large videos).
    """
    if not os.path.exists(STAMP_FOLDER):
        os.makedirs(STAMP_FOLDER)

    filename = file.filename
    input_path = os.path.join(STAMP_FOLDER, 'original_' + filename)
    output_path = os.path.join(STAMP_FOLDER, 'stamped_' + filename)

    file.save(input_path)

    SECRET = "STAMPIT_VERIFIED"
    secret_bits = ''.join(format(ord(c), '08b') for c in SECRET)

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"Warning: Could not open {filename}. Returning original.")
        return input_path

    fps    = cap.get(cv2.CAP_PROP_FPS) or 24
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        # Only stamp the FIRST frame — invisible, instant, same security
        if frame_count == 0:
            frame = _embed_lsb(frame, secret_bits)
        out.write(frame)
        frame_count += 1

    cap.release()
    out.release()
    os.remove(input_path)

    print(f"✅ Stamped {filename} — {frame_count} frames, stamp on frame 0.")
    return output_path


def verify_stamp(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return False
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return False
    return "STAMPIT_VERIFIED" in _extract_lsb(frame)


def _embed_lsb(frame, secret_bits):
    flat = frame[:, :, 0].flatten().astype(np.uint8)
    for i, bit in enumerate(secret_bits):
        if i >= len(flat):
            break
        flat[i] = (flat[i] & 0xFE) | int(bit)
    frame[:, :, 0] = flat.reshape(frame.shape[:2])
    return frame


def _extract_lsb(frame):
    flat = frame[:, :, 0].flatten()
    bits = [str(int(p) & 1) for p in flat[:128]]
    chars = []
    for i in range(0, len(bits), 8):
        byte = ''.join(bits[i:i+8])
        if len(byte) == 8:
            chars.append(chr(int(byte, 2)))
    return ''.join(chars)
