# main.py — Smart Doorbell Integrated
# Repo 1 (DoorbellSystem / web UI / PIR / recording) +
# Repo 2 (face recognition / weapon detection / threat scoring / Telegram)

from camera.live_buffer import LiveCameraBuffer
from camera.record_event import record_event
from core.detector import ObjectDetector
from core.face_recognizer import FaceRecognizer
from core.person_tracker import PersonTracker
from core.threat import ThreatScoreEngine
from core.audio_detector import AudioDetector
from core.camera_monitor import CameraMonitor
from event_logger import EventLogger
from utils.logger import log
from utils.hardware import HardwareInterface
from utils.telegram_alert import TelegramAlert
import cv2
import time
import threading
from config import Config


class DoorbellSystem:
    def __init__(self, show_window=False):
        self.event_requested = False
        self.running = False
        self.show_window = show_window
        self.idle = True
        self.push_callback = None          # Web UI push notifications (Repo 1)
        self.push_sent_for_event = False
        self.push_sent_time = 0

        # --- Hardware (Repo 1) ---
        self.hardware = HardwareInterface()
        self.hardware.set_pir_callback(self._on_motion)

        # --- Camera ---
        self.camera = None
        self.current_frame = None

        # --- Repo 2: detection pipeline ---
        log("[INIT] Loading object detector...")
        self.detector = ObjectDetector(Config.YOLO_MODEL_PATH)

        log("[INIT] Loading face recognizer...")
        self.recognizer = FaceRecognizer(distance_threshold=Config.FACE_DISTANCE_THRESHOLD)
        self.recognizer.load_known_faces_from_folder(Config.KNOWN_FACES_DIR)

        self.tracker = PersonTracker()
        self.threat_engine = ThreatScoreEngine()
        self.event_logger = EventLogger(save_folder=Config.THREAT_EVENTS_DIR)

        # --- Repo 2: Telegram alerts ---
        self.telegram = TelegramAlert(
            bot_token=Config.TELEGRAM_BOT_TOKEN,
            chat_id=Config.TELEGRAM_CHAT_ID,
            cooldown=Config.TELEGRAM_COOLDOWN
        )

        # --- Repo 2: Audio + camera obstruction monitoring ---
        self.audio_detector = AudioDetector() if Config.ENABLE_AUDIO else None
        self.camera_monitor = CameraMonitor()

        # --- Per-frame state (smoothing) ---
        self._weapon_counter = 0
        self._last_weapon = False
        self._person_boxes = []
        self._frame_count = 0

        # --- FPS tracking ---
        self._fps_counter = 0
        self._fps_value = 0
        self._fps_timer = time.time()

    # ------------------------------------------------------------------
    # Public API (Repo 1 web server calls these)
    # ------------------------------------------------------------------

    def set_push_callback(self, callback):
        self.push_callback = callback

    def request_event(self):
        self.event_requested = True

    def unlock(self):
        log("API Command Received: UNLOCK DOOR")
        self.hardware.unlock_door()

    def lock(self):
        log("API Command Received: LOCK DOOR")
        self.hardware.lock_door()

    def mock_motion(self):
        self.hardware.mock_pir_trigger()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        if self.running:
            return
        self.running = True
        self.camera = LiveCameraBuffer(buffer_seconds=15, fps=10)
        self.recognizer.start()
        # On non-Pi (simulation), skip idle and go straight to active so
        # detection runs immediately without needing a real PIR trigger.
        from utils.hardware import IS_RPI
        if not IS_RPI:
            self.idle = False
            log("Simulation mode: skipping idle, detection active immediately.")
        threading.Thread(target=self._run, daemon=True).start()
        log("System started.")

    def stop(self):
        self.running = False
        self.idle = True
        if self.camera:
            self.camera.release()
            self.camera = None
        self.recognizer.stop()
        if self.audio_detector:
            self.audio_detector.stop()
        if self.show_window:
            cv2.destroyAllWindows()
        self.hardware.cleanup()
        self.current_frame = None
        log("System stopped.")

    def get_frame(self):
        return self.current_frame

    # ------------------------------------------------------------------
    # PIR callback
    # ------------------------------------------------------------------

    def _on_motion(self):
        if self.idle:
            log("System waking up from motion...")
            self.idle = False
            self.push_sent_for_event = False

    # ------------------------------------------------------------------
    # Main detection loop
    # ------------------------------------------------------------------

    def _run(self):
        last_active_time = time.time()

        try:
            while self.running:
                frame = self.camera.read_frame()
                if frame is None:
                    continue

                # Pass-through in idle mode
                if self.idle:
                    self.current_frame = frame
                    time.sleep(0.03)
                    continue

                self._frame_count += 1

                # --- Object detection (every 5 frames for performance) ---
                if self._frame_count % 5 == 0:
                    small = cv2.resize(frame, (640, 360))
                    det_out = self.detector.detect(small)
                    self._last_weapon = det_out["weapon_detected"]

                    h, w = frame.shape[:2]
                    sx, sy = w / 640, h / 360
                    self._person_boxes = [
                        {
                            "bbox": (
                                int(p["bbox"][0] * sx), int(p["bbox"][1] * sy),
                                int(p["bbox"][2] * sx), int(p["bbox"][3] * sy),
                            ),
                            "confidence": p["confidence"],
                        }
                        for p in det_out["persons"]
                    ]

                # --- Weapon smoothing ---
                if self._last_weapon:
                    self._weapon_counter = min(self._weapon_counter + 1, 20)
                else:
                    self._weapon_counter = max(0, self._weapon_counter - 1)
                weapon_detected = self._weapon_counter > 5

                # --- Face recognition (non-blocking background thread) ---
                self.recognizer.submit_frame(frame)
                face_results = self.recognizer.get_results()

                # --- Person tracking ---
                face_names = [r["name"] for r in face_results] if face_results else ["UNKNOWN"]
                tracked = self.tracker.update_persons(face_names)

                # --- Determine worst threat face ---
                worst_face_status, worst_dwell = self._worst_threat(face_results, tracked)

                # --- Audio & camera obstruction ---
                audio_status = self.audio_detector.get_audio_status() if self.audio_detector else "NORMAL"
                camera_status = self.camera_monitor.check_obstruction(frame)

                # --- Threat scoring ---
                result = self.threat_engine.calculate(
                    face_status=worst_face_status,
                    dwell_time=worst_dwell,
                    is_nighttime=self._is_nighttime(),
                    audio_status=audio_status,
                    camera_status=camera_status,
                    weapon_detected=weapon_detected,
                )

                # --- Annotate frame ---
                annotated = self._draw_annotations(
                    frame.copy(), face_results, tracked,
                    weapon_detected, result
                )
                self.current_frame = annotated

                # --- Stay-awake logic ---
                has_activity = bool(face_results) or bool(self._person_boxes)
                if has_activity:
                    last_active_time = time.time()

                # Reset push cooldown after 60 s
                if self.push_sent_for_event and (time.time() - self.push_sent_time > 60):
                    self.push_sent_for_event = False

                # --- Alerts ---
                self._handle_alerts(result, annotated, worst_face_status, worst_dwell, weapon_detected)

                # --- Manual / motion-triggered video recording ---
                if self.event_requested:
                    self.event_requested = False
                    pre_frames = self.camera.get_buffer_frames()
                    video = record_event(pre_frames, self.camera.cap, duration=10, fps=10)
                    log(f"Saved video clip: {video}")

                # --- Return to idle after 30 s inactivity ---
                if time.time() - last_active_time > 30:
                    log("No activity for 30 s. Returning to idle.")
                    self.idle = True

                self.tracker.cleanup()
                time.sleep(0.03)

        except Exception as e:
            log(f"System error: {e}")
            raise

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _worst_threat(self, face_results, tracked):
        """Return (face_status, dwell) for the highest-threat detected face."""
        worst_status = "UNKNOWN"
        worst_dwell = 0

        if not face_results:
            return worst_status, worst_dwell

        # If any UNKNOWN face, pick the one with the longest dwell
        for pid, pdata in tracked:
            if pdata["name"] == "UNKNOWN" and pdata["dwell"] >= worst_dwell:
                worst_dwell = pdata["dwell"]

        # If all known, use the first
        if all(r["name"] != "UNKNOWN" for r in face_results):
            worst_status = face_results[0]["name"]
            worst_dwell = tracked[0][1]["dwell"] if tracked else 0

        return worst_status, worst_dwell

    def _is_nighttime(self):
        """Simple time-based nighttime check (22:00–06:00)."""
        hour = time.localtime().tm_hour
        return hour >= 22 or hour < 6

    def _draw_annotations(self, frame, face_results, tracked, weapon_detected, result):
        """Draw all bounding boxes, labels, HUD, and FPS onto frame."""
        # Person boxes (YOLO)
        for p in self._person_boxes:
            x1, y1, x2, y2 = p["bbox"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
            cv2.putText(frame, f"Person {p['confidence']:.2f}",
                        (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

        # Face boxes — handle both DeepFace facial_area key formats
        for face in face_results:
            box = face["box"]
            name = face["name"]
            # DeepFace may return x/y/w/h or x/y/x2/y2 (facial_area dict)
            x = box.get("x", box.get("left", 0))
            y = box.get("y", box.get("top", 0))
            w = box.get("w", box.get("width", box.get("x2", x+80) - x))
            h = box.get("h", box.get("height", box.get("y2", y+80) - y))
            color = (0, 0, 255) if name == "UNKNOWN" else (0, 255, 0)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

            dwell = next(
                (pd["dwell"] for _, pd in tracked if pd["name"] == name), 0
            )
            label = f"{name} | {int(dwell)}s"
            # Draw label background for readability
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (x, y - lh - 14), (x + lw + 4, y), color, -1)
            cv2.putText(frame, label, (x + 2, y - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        # Weapon alert
        if weapon_detected:
            cv2.putText(frame, "WEAPON DETECTED!", (20, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)

        # Threat HUD
        threat_color = (0, 255, 255) if result.level < 2 else (0, 0, 255)
        cv2.putText(frame,
                    f"Threat: {result.level}  Score: {result.score}",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, threat_color, 2)

        # FPS counter
        self._fps_counter += 1
        elapsed = time.time() - self._fps_timer
        if elapsed >= 1.0:
            self._fps_value = self._fps_counter / elapsed
            self._fps_counter = 0
            self._fps_timer = time.time()
        cv2.putText(frame, f"FPS: {self._fps_value:.1f}",
                    (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 0), 2)

        return frame

    def _handle_alerts(self, result, frame, face_status, dwell, weapon_detected):
        """
        Two alert channels:
          1. Telegram (Repo 2) — direct photo + caption for HIGH THREAT
          2. Web UI push callback (Repo 1) — for SUSPICIOUS and above
        """
        if result.level >= 2:
            # Telegram still image alert
            filepath = self.event_logger.log_event(frame, face_status, dwell, result.score)
            if filepath:
                parts = ["🚨 HIGH THREAT DETECTED", f"Person: {face_status}",
                         f"Dwell: {int(dwell)} sec", f"Score: {result.score}"]
                if weapon_detected:
                    parts.insert(1, "⚠️ WEAPON DETECTED")
                self.telegram.send_alert(filepath, "\n".join(parts))

        if result.level >= 1 and not self.push_sent_for_event and self.push_callback:
            label = f"🚨 {face_status}" if result.level >= 2 else f"⚠️ Suspicious: {face_status}"
            self.push_callback(label)
            self.push_sent_for_event = True
            self.push_sent_time = time.time()
