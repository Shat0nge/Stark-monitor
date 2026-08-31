#!/bin/bash
set -e

INSTALL_DIR="/home/pi/stark-monitor-v2"
SERVICE_NAME="stark-monitor-v2.service"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
    echo "Запустите: sudo ./deploy.sh"
    exit 1
fi

echo "=== STARK MONITOR V2 INSTALL ==="

mkdir -p "$INSTALL_DIR"

cp "$SCRIPT_DIR"/config.py \
   "$SCRIPT_DIR"/inverter.py \
   "$SCRIPT_DIR"/parser.py \
   "$SCRIPT_DIR"/database.py \
   "$SCRIPT_DIR"/db_sync.py \
   "$SCRIPT_DIR"/monitor.py \
   "$SCRIPT_DIR"/web.py \
   "$INSTALL_DIR"/

cp "$SCRIPT_DIR/config.env.example" "$INSTALL_DIR/"

if [ ! -f "$INSTALL_DIR/config.env" ]; then
    cp "$INSTALL_DIR/config.env.example" "$INSTALL_DIR/config.env"
fi

chmod 644 "$INSTALL_DIR"/*.py
chmod 644 "$INSTALL_DIR"/config.env "$INSTALL_DIR"/config.env.example

echo "Проверка Python..."
cd "$INSTALL_DIR"
python3 -m py_compile \
    config.py \
    inverter.py \
    parser.py \
    database.py \
    db_sync.py \
    monitor.py \
    web.py

echo "Python: OK"

cp "$SCRIPT_DIR/stark-monitor.service" \
   "/etc/systemd/system/$SERVICE_NAME"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo
echo "=== ГОТОВО ==="
echo "Service: $SERVICE_NAME"
systemctl --no-pager --full status "$SERVICE_NAME" || true

echo
echo "Web: http://$(hostname -I | awk '{print $1}'):8080"

echo
echo "Если /dev/ttyUSB0 пока отсутствует — это нормально."
echo "После подключения адаптера сервис продолжит работу автоматически."
