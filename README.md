# Smart Doorbell — Integrated

Combines **[smart-doorbell](https://github.com/ThatOneCoderWhoCreates/smart-doorbell)** (web UI, audio/video, PIR hardware) with **[Threat_detection_model](https://github.com/Msjariwala/Threat_detection_model)** (face recognition, weapon detection, threat scoring, Telegram alerts).

---

## What changed

| Area | Before (Repo 1) | After (Integrated) |
|---|---|---|
| Video / detection | Basic `HumanDetector` (YOLOv8 person only) | YOLOv8 persons + **weapon detection** (knife, scissors) |
| Face recognition | None | DeepFace (Facenet) with known-faces whitelist |
| Threat scoring | Binary suspicious/not | Multi-factor score: face, dwell, night, audio, weapon, obstruction |
| Person tracking | None | Dwell-time tracker per identity |
| Audio | None | FFT-based: NORMAL / AGGRESSIVE_SHOUTING / LOUD_BANGING |
| Camera obstruction | None | Mean/variance/delta detection |
| Alerts | Web-UI push callback | **Both** Telegram photo alerts + web-UI push |
| Event storage | Video clips (10 s) | Video clips (web UI) + JPEG stills (Telegram) |
| Config | `config.yaml` | Unified `config.py` (env-var overridable) |

---

## Project structure

```
smart-doorbell-integrated/
├── main.py                  # DoorbellSystem — unified entry point
├── config.py                # All config in one place
├── event_logger.py          # Threat still-image saver (Telegram)
├── requirements.txt
├── push_to_github.sh        # One-command GitHub publish
│
├── core/                    # From Repo 2
│   ├── detector.py          # YOLOv8 person + weapon
│   ├── face_recognizer.py   # DeepFace background thread
│   ├── person_tracker.py    # Dwell-time per identity
│   ├── threat.py            # Scoring engine
│   ├── audio_detector.py    # PyAudio + FFT
│   └── camera_monitor.py    # Obstruction detection
│
├── camera/                  # From Repo 1
│   ├── live_buffer.py       # 15-second rolling frame buffer
│   └── record_event.py      # Video clip recorder
│
├── utils/
│   ├── logger.py            # From Repo 1
│   ├── hardware.py          # PIR / lock GPIO (Repo 1)
│   └── telegram_alert.py    # From Repo 2
│
├── web/                     # From Repo 1 (Flask UI — unchanged)
├── known_faces/             # Add subdirectory per person, or flat .jpg files
├── threat_events/           # Auto-created; stores alert stills
└── yolov8n.pt               # One shared model file
```

---

## Setup

```bash
pip install -r requirements.txt
```

### Configure

Edit `config.py` or set environment variables:

```bash
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
export ENABLE_AUDIO=true           # false on systems without a mic
export MOCK_HARDWARE=true          # true when not running on Raspberry Pi
```

### Add known faces

```
known_faces/
  Alice/
    photo1.jpg
    photo2.jpg
  Bob.jpg
```

### Run

```bash
python main.py
# or via Repo 1's web server entry point:
python web/app.py
```

---

## Push to GitHub

```bash
chmod +x push_to_github.sh
./push_to_github.sh <your_github_username> smart-doorbell-integrated
```

Requires [GitHub CLI (`gh`)](https://cli.github.com/) authenticated.

---

## Known integration decisions / tradeoffs

| Issue | Decision |
|---|---|
| Two separate `main.py` files | Repo 1's `DoorbellSystem` class kept as the host; Repo 2's loop moved inside `_run()` |
| Duplicate `yolov8n.pt` | One shared file in root |
| `config.yaml` vs Repo 2 constants | Unified `Config` class; all values env-var overridable |
| Two notification channels | Both kept — Telegram for direct device alerts, push callback for web UI |
| Repo 2 `main.py` had hardcoded Telegram credentials | Moved to `Config`; set via env vars |
| `pyaudio` on macOS/Windows | May need `brew install portaudio` or `conda install pyaudio`; set `ENABLE_AUDIO=false` to skip |
| `deepface` first-run model download | ~500 MB downloaded on first launch (Facenet weights) |
