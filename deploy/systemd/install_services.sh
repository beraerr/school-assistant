#!/bin/bash
set -e

PROJECT_DIR="/root/.openclaw/workspace/school-assistant"
SYSTEMD_DIR="/etc/systemd/system"

mkdir -p "$PROJECT_DIR/logs"

cp "$PROJECT_DIR/deploy/systemd/school-backend.service" "$SYSTEMD_DIR/school-backend.service"
cp "$PROJECT_DIR/deploy/systemd/school-frontend.service" "$SYSTEMD_DIR/school-frontend.service"

systemctl daemon-reload
systemctl enable school-backend.service
systemctl enable school-frontend.service
systemctl restart school-backend.service
systemctl restart school-frontend.service

echo "Services installed and restarted."
systemctl --no-pager --full status school-backend.service | sed -n '1,15p'
systemctl --no-pager --full status school-frontend.service | sed -n '1,15p'
