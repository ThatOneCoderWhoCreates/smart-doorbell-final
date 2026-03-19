#!/usr/bin/env python3
"""
run.py — entry point for smart-doorbell-integrated
Usage:
    python run.py                  # default host 0.0.0.0:5000
    python run.py --host 0.0.0.0 --port 8000
"""
import argparse
import os
import subprocess
import sys


def ensure_vapid_keys():
    """Generate VAPID keys if not present (needed for web push)."""
    if not os.path.exists("private_key.pem"):
        print("[SETUP] Generating VAPID keys...")
        try:
            from py_vapid import Vapid
            v = Vapid()
            v.generate_keys()
            v.save_key("private_key.pem")
            v.save_public_key("public_key.pem")
            print("[SETUP] VAPID keys saved to private_key.pem / public_key.pem")
            print("[SETUP] Copy the public key into web/static/app.js → PUBLIC_VAPID_KEY")
        except Exception as e:
            print(f"[WARN] Could not generate VAPID keys: {e}")
            print("       Push notifications will not work until private_key.pem exists.")


def main():
    parser = argparse.ArgumentParser(description="Smart Doorbell Integrated")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--reload", action="store_true", help="Enable hot-reload (dev only)")
    args = parser.parse_args()

    ensure_vapid_keys()

    os.makedirs("storage/local", exist_ok=True)
    os.makedirs("threat_events", exist_ok=True)
    os.makedirs("known_faces", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    import uvicorn
    uvicorn.run(
        "web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
