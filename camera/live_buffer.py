import cv2
from collections import deque
import threading
import time


class LiveCameraBuffer:
    def __init__(self, buffer_seconds=15, fps=10):
        self.cap = cv2.VideoCapture(0)
        self.fps = fps
        self.buffer_size = buffer_seconds * fps
        self.buffer = deque(maxlen=self.buffer_size)
        self.latest_frame = None
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def _capture_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.latest_frame = frame
                self.buffer.append(frame)
            else:
                time.sleep(0.01)

    def read_frame(self):
        return self.latest_frame

    def get_buffer_frames(self):
        return list(self.buffer)

    def release(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()
