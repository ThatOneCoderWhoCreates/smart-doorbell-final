import os
import time
import asyncio
import json
import cv2

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pywebpush import webpush, WebPushException
import aiofiles

from main import DoorbellSystem

app = FastAPI()

# -------------------------
# Static files & templates
# -------------------------
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# -------------------------
# Ngrok bypass middleware
# -------------------------
@app.middleware("http")
async def add_ngrok_bypass_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

# -------------------------
# App state
# -------------------------
system = DoorbellSystem(show_window=False)
subscriptions = []
pcs = set()
active_audio_sockets = set()
is_shutting_down = False

# Alert queue
alert_queue = []
ALERT_MAX_AGE = 300  # 5 minutes
current_alert = {"id": 0, "message": None}

# -------------------------
# Lifecycle
# -------------------------
@app.on_event("startup")
async def startup_event():
    print("Doorbell System ready. Waiting for manual start.")

@app.on_event("shutdown")
async def shutdown_event():
    global is_shutting_down
    is_shutting_down = True
    system.stop()
    for pc in pcs:
        await pc.close()
    pcs.clear()
    for ws in list(active_audio_sockets):
        try:
            await ws.close()
        except Exception:
            pass

# -------------------------
# UI routes
# -------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/recordings_page", response_class=HTMLResponse)
async def recordings_page(request: Request):
    return templates.TemplateResponse("recordings.html", {"request": request})

# -------------------------
# Video storage — iOS-safe range requests
# -------------------------
@app.get("/storage/{video_path:path}")
async def stream_video(video_path: str, request: Request):
    file_path = os.path.join("storage/local", video_path)
    if not os.path.exists(file_path):
        return HTMLResponse(status_code=404)

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("Range", None)

    if range_header:
        byte1, byte2 = range_header.replace("bytes=", "").split("-")
        start = int(byte1)
        end = int(byte2) if byte2 else file_size - 1
    else:
        start = 0
        end = file_size - 1

    chunk_size = (end - start) + 1

    async def file_iterator(path, s, size):
        async with aiofiles.open(path, "rb") as f:
            await f.seek(s)
            yield await f.read(size)

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
        "Content-Type": "video/mp4",
    }
    return StreamingResponse(
        file_iterator(file_path, start, chunk_size),
        headers=headers,
        status_code=206 if range_header else 200,
    )

# -------------------------
# System control
# -------------------------
@app.get("/start")
async def start():
    system.start()
    return JSONResponse({"status": "started"})

@app.get("/stop")
async def stop():
    system.stop()
    global current_alert
    current_alert = {"id": 0, "message": None}
    alert_queue.clear()
    return JSONResponse({"status": "stopped"})

@app.get("/api/status")
async def get_status():
    return JSONResponse({"status": "started" if system.running else "stopped"})

@app.get("/trigger")
async def trigger():
    system.request_event()
    return JSONResponse({"status": "triggered"})

@app.post("/api/unlock")
async def unlock_door():
    system.unlock()
    return JSONResponse({"status": "door_unlocked"})

@app.post("/api/lock")
async def lock_door():
    system.lock()
    return JSONResponse({"status": "door_locked"})

@app.post("/api/pir-trigger")
async def trigger_pir():
    system.mock_motion()
    system.request_event()
    return JSONResponse({"status": "motion_simulated_and_recording_started"})

# -------------------------
# Push subscriptions
# -------------------------
@app.post("/api/subscribe")
async def subscribe(request: Request):
    sub = await request.json()
    if sub not in subscriptions:
        subscriptions.append(sub)
    print(f"Registered push subscription. Total: {len(subscriptions)}")
    return JSONResponse({"status": "subscribed"})

# -------------------------
# Recordings
# -------------------------
@app.get("/api/recordings")
async def get_recordings(sort: str = "newest", filter_date: str = None):
    try:
        base_dir = "storage/local"
        videos = []
        for root, _, files in os.walk(base_dir):
            for file in files:
                if file.endswith((".mp4", ".webm", ".avi")):
                    filepath = os.path.join(root, file)
                    if os.path.getsize(filepath) == 0:
                        continue
                    rel_path = os.path.relpath(filepath, base_dir).replace("\\", "/")
                    if filter_date:
                        parts = filter_date.split("-")
                        if len(parts) == 3:
                            y, m, d = parts
                            if f"{y}/{m}/{d}" not in rel_path:
                                continue
                    videos.append({"path": rel_path, "time": os.path.getmtime(filepath)})
        videos.sort(key=lambda x: x["time"], reverse=(sort != "oldest"))
        return JSONResponse({"recordings": [v["path"] for v in videos]})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.delete("/api/recordings/{video_path:path}")
async def delete_recording(video_path: str):
    try:
        if ".." in video_path:
            return JSONResponse({"error": "Invalid path"}, status_code=400)
        file_path = os.path.join("storage/local", video_path)
        if os.path.exists(file_path):
            os.remove(file_path)
            return JSONResponse({"status": "deleted"})
        return JSONResponse({"error": "File not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# -------------------------
# Alerts
# -------------------------
@app.get("/api/latest_alert")
async def get_latest_alert():
    return JSONResponse(current_alert)

@app.get("/api/alerts")
async def get_alerts(since: float = 0):
    now = time.time()
    active = [a for a in alert_queue if now - a["time"] < ALERT_MAX_AGE]
    alert_queue.clear()
    alert_queue.extend(active)
    return JSONResponse({"alerts": [a for a in alert_queue if a["time"] > since]})

def send_push_notification(message_text: str):
    global current_alert
    now = time.time()
    current_alert = {"id": now, "message": message_text}
    alert_queue.append({"time": now, "message": message_text})
    print(f"ALERT: {message_text} → pushing to {len(subscriptions)} device(s)")
    for sub in subscriptions.copy():
        try:
            webpush(
                subscription_info=sub,
                data=message_text,
                vapid_private_key="private_key.pem",
                vapid_claims={"sub": "mailto:admin@smartdoorbell.local"},
            )
        except WebPushException as ex:
            print("WebPush Error:", repr(ex))
            if ex.response and ex.response.status_code in (404, 410):
                subscriptions.remove(sub)
        except Exception as e:
            print("Push failed:", e)

system.set_push_callback(send_push_notification)

# -------------------------
# MJPEG video stream
# -------------------------
async def generate_frames():
    import numpy as np

    def idle_frame():
        img = np.full((480, 640, 3), 30, dtype=np.uint8)
        cv2.putText(img, "SYSTEM IDLE - WAITING FOR MOTION",
                    (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        _, buf = cv2.imencode(".jpg", img)
        return buf.tobytes()

    idle_bytes = idle_frame()

    while not is_shutting_down:
        frame = system.get_frame()
        if frame is not None:
            _, buf = cv2.imencode(".jpg", frame)
            frame_bytes = buf.tobytes()
            delay = 0.03
        else:
            frame_bytes = idle_bytes
            delay = 0.1

        yield (
            b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
            + frame_bytes
            + b"\r\n"
        )
        await asyncio.sleep(delay)

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )

# -------------------------
# Intercom — role-aware PTT
# -------------------------
#
# Protocol (client → server):
#   1. First message after connect: JSON  {"type": "register", "role": "mobile"|"desktop"}
#   2. PTT press:                   JSON  {"type": "ptt_start"}
#   3. Audio chunks while held:     binary (raw Int16 PCM, 16 kHz mono)
#   4. PTT release:                 JSON  {"type": "ptt_stop"}
#
# Server → client:
#   - Binary audio frames (forwarded from the other role)
#   - JSON {"type": "ptt_state", "talker": "mobile"|"desktop"|null}
#     sent to ALL clients whenever PTT state changes so the UI can show who is live

import json as _json

class IntercomClient:
    def __init__(self, ws: WebSocket, role: str):
        self.ws = ws
        self.role = role          # "mobile" or "desktop"
        self.is_talking = False

# role → list of clients (multiple tabs/devices per role are allowed)
intercom_clients: dict[str, list[IntercomClient]] = {"mobile": [], "desktop": []}
intercom_lock = asyncio.Lock()


async def _broadcast_ptt_state(talker_role: str | None):
    """Tell all connected clients who is currently talking."""
    msg = _json.dumps({"type": "ptt_state", "talker": talker_role}).encode()
    for role_clients in intercom_clients.values():
        for c in list(role_clients):
            try:
                await c.ws.send_bytes(msg)
            except Exception:
                pass


@app.get("/api/intercom/status")
async def intercom_status():
    """REST poll fallback so the UI can show PTT state without a WS."""
    talker = None
    for role, clients in intercom_clients.items():
        if any(c.is_talking for c in clients):
            talker = role
            break
    return JSONResponse({"talker": talker})


@app.websocket("/ws/audio")
async def websocket_audio(websocket: WebSocket):
    await websocket.accept()
    active_audio_sockets.add(websocket)

    client: IntercomClient | None = None

    try:
        while True:
            # Use receive() and inspect the message type properly
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

            # ── JSON control frame (sent as text) ───────────────────────
            if message.get("text"):
                try:
                    msg = _json.loads(message["text"])
                except Exception:
                    continue

                kind = msg.get("type")

                if kind == "register":
                    role = msg.get("role", "mobile")
                    if role not in intercom_clients:
                        role = "mobile"
                    client = IntercomClient(websocket, role)
                    async with intercom_lock:
                        intercom_clients[role].append(client)
                    print(f"[Intercom] {role} connected ({len(intercom_clients[role])} total)")

                elif kind == "ptt_start" and client:
                    async with intercom_lock:
                        client.is_talking = True
                    await _broadcast_ptt_state(client.role)
                    print(f"[Intercom] PTT start — {client.role}")

                elif kind == "ptt_stop" and client:
                    async with intercom_lock:
                        client.is_talking = False
                    await _broadcast_ptt_state(
                        next(
                            (r for r, cs in intercom_clients.items()
                             if any(c.is_talking for c in cs)),
                            None
                        )
                    )
                    print(f"[Intercom] PTT stop  — {client.role}")

            # ── Binary audio frame ───────────────────────────────────────
            elif message.get("bytes"):
                if client is None or not client.is_talking:
                    continue

                audio_bytes = message["bytes"]
                target_role = "desktop" if client.role == "mobile" else "mobile"

                for target in list(intercom_clients.get(target_role, [])):
                    try:
                        await target.ws.send_bytes(audio_bytes)
                    except Exception:
                        intercom_clients[target_role].remove(target)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[Intercom] WS error: {e}")
    finally:
        active_audio_sockets.discard(websocket)
        if client:
            async with intercom_lock:
                try:
                    intercom_clients[client.role].remove(client)
                except ValueError:
                    pass
            if client.is_talking:
                await _broadcast_ptt_state(None)
            print(f"[Intercom] {client.role} disconnected")
