# utils/telegram_alert.py — from Repo 2

import time
import requests


class TelegramAlert:
    def __init__(self, bot_token, chat_id, cooldown=30):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.cooldown = cooldown
        self._last_sent = 0

    def send_alert(self, image_path, caption):
        now = time.time()
        if now - self._last_sent < self.cooldown:
            return False
        self._last_sent = now
        url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
        try:
            with open(image_path, "rb") as photo:
                resp = requests.post(url, data={"chat_id": self.chat_id, "caption": caption},
                                     files={"photo": photo}, timeout=10)
            ok = resp.status_code == 200
            if not ok:
                print(f"[TELEGRAM] Failed: {resp.text}")
            return ok
        except Exception as e:
            print(f"[TELEGRAM] Error: {e}")
            return False
