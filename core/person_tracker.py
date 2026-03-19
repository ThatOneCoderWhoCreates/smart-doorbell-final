# core/person_tracker.py — from Repo 2

import time
import uuid


class PersonTracker:
    def __init__(self):
        self.active_persons = {}

    def update_person(self, name):
        current_time = time.time()
        for pid, data in self.active_persons.items():
            if data["name"] == name:
                data["last_seen"] = current_time
                data["dwell"] = current_time - data["first_seen"]
                return pid, data
        person_id = str(uuid.uuid4())
        self.active_persons[person_id] = {
            "name": name,
            "first_seen": current_time,
            "last_seen": current_time,
            "dwell": 0,
        }
        return person_id, self.active_persons[person_id]

    def update_persons(self, names):
        return [self.update_person(name) for name in names]

    def cleanup(self, timeout=5):
        current_time = time.time()
        for pid in [p for p, d in self.active_persons.items()
                    if current_time - d["last_seen"] > timeout]:
            del self.active_persons[pid]
