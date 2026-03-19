# core/detector.py

from ultralytics import YOLO
from config import Config


class ObjectDetector:
    def __init__(self, model_path=None):
        path = model_path or Config.YOLO_MODEL_PATH
        self.model = YOLO(path)

    def detect(self, frame):
        """
        Returns:
            {
                "persons": [ {"bbox": (x1,y1,x2,y2), "confidence": float} ],
                "weapon_detected": bool
            }
        """
        results = self.model(frame, verbose=False)
        persons = []
        weapon_detected = False

        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf   = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                if cls_id == 0:
                    persons.append({"bbox": (x1, y1, x2, y2), "confidence": conf})

                if cls_id in (Config.COCO_KNIFE_ID, Config.COCO_SCISSORS_ID):
                    weapon_detected = True

        return {"persons": persons, "weapon_detected": weapon_detected}
