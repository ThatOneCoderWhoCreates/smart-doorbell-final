# core/face_recognizer.py — from Repo 2, Config-integrated

import os
import numpy as np
import cv2
import threading
import time
from deepface import DeepFace
from scipy.spatial.distance import cosine
from config import Config


class FaceRecognizer:
    def __init__(self, model_name=None, distance_threshold=None):
        self.model_name = model_name or Config.FACE_MODEL
        self.distance_threshold = distance_threshold or Config.FACE_DISTANCE_THRESHOLD

        self.known_embeddings = []
        self.known_names = []

        self._lock = threading.Lock()
        self._latest_frame = None
        self._latest_results = []
        self._running = False
        self._thread = None
        self._process_interval = 0.15

        self._warm_up_model()

    def _warm_up_model(self):
        try:
            dummy = np.zeros((160, 160, 3), dtype=np.uint8)
            DeepFace.represent(dummy, model_name=self.model_name,
                               enforce_detection=False, detector_backend="skip")
        except Exception:
            pass

    def load_known_faces_from_folder(self, folder_path):
        if not os.path.isdir(folder_path):
            print(f"  [WARN] known_faces folder not found: {folder_path}")
            return

        embeddings, names = [], []
        for entry in os.listdir(folder_path):
            entry_path = os.path.join(folder_path, entry)
            if os.path.isdir(entry_path):
                for img_file in os.listdir(entry_path):
                    if img_file.lower().endswith((".jpg", ".png", ".jpeg")):
                        emb = self._extract_embedding_from_path(os.path.join(entry_path, img_file))
                        if emb is not None:
                            embeddings.append(emb)
                            names.append(entry)
                            print(f"  ✓ Loaded face: {entry} ({img_file})")
            elif entry.lower().endswith((".jpg", ".png", ".jpeg")):
                emb = self._extract_embedding_from_path(entry_path)
                if emb is not None:
                    embeddings.append(emb)
                    names.append(os.path.splitext(entry)[0])
                    print(f"  ✓ Loaded face: {os.path.splitext(entry)[0]}")

        self.known_embeddings = embeddings
        self.known_names = names
        print(f"  Total known face embeddings: {len(embeddings)}")

    def _extract_embedding_from_path(self, img_path):
        try:
            img = cv2.imread(img_path)
            return self._extract_embedding(img) if img is not None else None
        except Exception:
            return None

    def _extract_embedding(self, face_img):
        try:
            result = DeepFace.represent(face_img, model_name=self.model_name,
                                        enforce_detection=False)
            return np.array(result[0]["embedding"])
        except Exception:
            return None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._recognition_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def submit_frame(self, frame):
        with self._lock:
            self._latest_frame = frame.copy()

    def get_results(self):
        with self._lock:
            return list(self._latest_results)

    def _recognition_loop(self):
        while self._running:
            frame = None
            with self._lock:
                if self._latest_frame is not None:
                    frame = self._latest_frame.copy()
            if frame is not None:
                results = self._process_frame(frame)
                with self._lock:
                    self._latest_results = results
            time.sleep(self._process_interval)

    def _process_frame(self, frame):
        try:
            representations = DeepFace.represent(
                img_path=frame, model_name=self.model_name,
                enforce_detection=True, detector_backend="opencv"
            )
        except Exception:
            return []

        results = []
        for rep in representations:
            embedding = np.array(rep["embedding"])
            facial_area = rep["facial_area"]

            best_distance = float("inf")
            best_name = "UNKNOWN"
            for i, known_emb in enumerate(self.known_embeddings):
                dist = cosine(embedding, known_emb)
                if dist < best_distance:
                    best_distance = dist
                    best_name = self.known_names[i]

            if best_distance >= self.distance_threshold:
                best_name = "UNKNOWN"

            results.append({"name": best_name, "box": facial_area})

        return results
