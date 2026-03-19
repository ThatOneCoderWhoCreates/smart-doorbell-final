# event_logger.py — from Repo 2

import os
import cv2
import time
from datetime import datetime
from config import Config


class EventLogger:
    def __init__(self, save_folder=None):
        self.save_folder = save_folder or Config.THREAT_EVENTS_DIR
        os.makedirs(self.save_folder, exist_ok=True)
        self.last_saved_time = 0
        self.cooldown = 10  # seconds between saved stills

    def log_event(self, frame, face_status, dwell_time, score):
        """Save a threat still to disk; returns filepath or None if on cooldown."""
        if time.time() - self.last_saved_time < self.cooldown:
            return None
        self.last_saved_time = time.time()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{face_status}_{timestamp}.jpg"
        filepath = os.path.join(self.save_folder, filename)
        cv2.imwrite(filepath, frame)
        print(f"[ALERT SAVED] {filename}")
        return filepath
