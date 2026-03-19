import cv2
import os
import subprocess
from datetime import datetime


def record_event(pre_frames, cap, duration=10, fps=10):
    if not pre_frames:
        print("No pre-buffer frames available")
        return None

    now = datetime.now()
    date_path = os.path.join(str(now.year), f"{now.month:02d}", f"{now.day:02d}")
    save_dir = os.path.join(os.getcwd(), "storage", "local", date_path)
    os.makedirs(save_dir, exist_ok=True)

    filename = os.path.join(save_dir, f"event_{now.strftime('%H-%M-%S')}.mp4")

    height, width, _ = pre_frames[0].shape

    process = subprocess.Popen([
        'ffmpeg', '-y',
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-s', f'{width}x{height}',
        '-pix_fmt', 'bgr24',
        '-r', str(fps),
        '-i', '-',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-preset', 'ultrafast',
        '-movflags', '+faststart',
        filename
    ], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    for frame in pre_frames:
        process.stdin.write(frame.tobytes())

    frame_count = duration * fps
    for _ in range(frame_count):
        ret, frame = cap.read()
        if not ret:
            break
        process.stdin.write(frame.tobytes())
        process.stdin.write(frame.tobytes())  # duplicate for slow-mo effect

    process.stdin.close()
    process.wait()
    return filename
