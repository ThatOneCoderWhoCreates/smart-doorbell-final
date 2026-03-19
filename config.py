# config.py — Unified configuration for smart-doorbell-integrated
# Merges Repo 1's config.yaml fields and Repo 2's config constants

import os

class Config:
    # ------------------------------------------------------------------
    # Camera
    # ------------------------------------------------------------------
    CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", 0))
    BUFFER_SECONDS = int(os.getenv("BUFFER_SECONDS", 15))
    CAMERA_FPS = int(os.getenv("CAMERA_FPS", 10))

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------
    YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
    KNOWN_FACES_DIR = os.getenv("KNOWN_FACES_DIR", "known_faces")
    FACE_DISTANCE_THRESHOLD = float(os.getenv("FACE_DISTANCE_THRESHOLD", 0.5))
    FACE_MODEL = os.getenv("FACE_MODEL", "Facenet")

    # COCO class IDs for weapon detection
    COCO_KNIFE_ID = 43       # knife
    COCO_SCISSORS_ID = 76    # scissors

    # ------------------------------------------------------------------
    # Threat scoring thresholds
    # ------------------------------------------------------------------
    FACE_SCORES = {
        "UNKNOWN":  3,
        "COVERED":  5,
        # Known names score 0 by default (not a threat)
    }
    DWELL_SCORE_THRESHOLD = 30      # seconds before dwell penalty kicks in
    DWELL_SCORE_POINTS    = 2
    UNKNOWN_LONG_DWELL_SECONDS = 60
    UNKNOWN_LONG_DWELL_BONUS   = 2
    NIGHT_SCORE          = 2
    COVERED_NIGHT_BONUS  = 3
    AUDIO_SCORES = {
        "NORMAL":              0,
        "AGGRESSIVE_SHOUTING": 2,
        "LOUD_BANGING":        3,
    }
    CAMERA_OBSTRUCTION_SCORE = 5
    WEAPON_BASE_SCORE = 4
    WEAPON_MIN_LEVEL  = 1
    NORMAL_MAX_SCORE     = 3
    SUSPICIOUS_MAX_SCORE = 6
    THREAT_LEVELS = {0: "NORMAL", 1: "SUSPICIOUS", 2: "HIGH"}

    # ------------------------------------------------------------------
    # Alerts — Telegram (Repo 2)
    # ------------------------------------------------------------------
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   "YOUR_CHAT_ID_HERE")
    TELEGRAM_COOLDOWN  = int(os.getenv("TELEGRAM_COOLDOWN", 30))   # seconds

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------
    THREAT_EVENTS_DIR = os.getenv("THREAT_EVENTS_DIR", "threat_events")

    # ------------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------------
    ENABLE_AUDIO = os.getenv("ENABLE_AUDIO", "true").lower() == "true"

    # ------------------------------------------------------------------
    # Web server (Repo 1)
    # ------------------------------------------------------------------
    WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
    WEB_PORT = int(os.getenv("WEB_PORT", 5000))

    # ------------------------------------------------------------------
    # Hardware
    # ------------------------------------------------------------------
    PIR_PIN     = int(os.getenv("PIR_PIN", 17))
    LOCK_PIN    = int(os.getenv("LOCK_PIN", 27))
    UNLOCK_PIN  = int(os.getenv("UNLOCK_PIN", 22))
    MOCK_HARDWARE = os.getenv("MOCK_HARDWARE", "false").lower() == "true"
