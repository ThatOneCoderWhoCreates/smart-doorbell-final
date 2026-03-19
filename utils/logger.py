from datetime import datetime
import os


def log(message):
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} - {message}"
    print(line)
    with open("logs/system.log", "a") as f:
        f.write(line + "\n")
