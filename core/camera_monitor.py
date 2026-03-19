# core/camera_monitor.py — from Repo 2

import cv2
import numpy as np


class CameraMonitor:
    def __init__(self, dark_threshold=40, variance_threshold=15):
        self.dark_threshold = dark_threshold
        self.variance_threshold = variance_threshold
        self.previous_mean = None

    def check_obstruction(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_intensity = np.mean(gray)
        variance = np.var(gray)
        obstructed = (
            mean_intensity < self.dark_threshold
            or variance < self.variance_threshold
            or (self.previous_mean is not None
                and abs(mean_intensity - self.previous_mean) > 80)
        )
        self.previous_mean = mean_intensity
        return "OBSTRUCTED" if obstructed else "NORMAL"
