#!/usr/bin/env bash
# push_to_github.sh
# Usage: ./push_to_github.sh <github_username> <new_repo_name>
#
# Prerequisites:
#   1. gh CLI installed and authenticated (gh auth login)
#      OR manually create the repo on GitHub first
#   2. Git configured with your name/email

set -e

GITHUB_USER="${1:?Usage: $0 <github_username> <new_repo_name>}"
REPO_NAME="${2:?Usage: $0 <github_username> <new_repo_name>}"

echo "==> Initialising git repo..."
git init
git add .
git commit -m "feat: integrate Threat_detection_model into smart-doorbell (complete)


- Replace HumanDetector with YOLOv8 ObjectDetector + DeepFace FaceRecognizer
- Add weapon detection (knife/scissors via COCO), face recognition with whitelist
- Add ThreatScoreEngine with configurable scoring rules
- Add PersonTracker for dwell-time tracking
- Add AudioDetector (pyaudio + FFT, NORMAL / AGGRESSIVE_SHOUTING / LOUD_BANGING)
- Add CameraMonitor obstruction detection
- Add Telegram alert channel alongside existing web-UI push notifications
- Add EventLogger (still-image saves for Telegram) alongside video clip recording
- Unified Config class (config.py) replacing config.yaml + Repo 2 constants
- Preserve all Repo 1 features: DoorbellSystem, PIR/motion, idle/active loop,
  LiveCameraBuffer, record_event, hardware interface, Flask web UI"

echo "==> Creating GitHub repository..."
# Option A — using gh CLI (recommended)
gh repo create "${GITHUB_USER}/${REPO_NAME}" \
    --public \
    --description "Smart doorbell: video/audio/web UI + face recognition + weapon detection + threat scoring" \
    --source=. \
    --remote=origin \
    --push

# Option B — if gh CLI is unavailable, comment out Option A and uncomment below:
# git remote add origin "https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
# git branch -M main
# git push -u origin main

echo ""
echo "✅  Done! Repo available at: https://github.com/${GITHUB_USER}/${REPO_NAME}"
