import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.env")

if os.path.isfile(CONFIG_FILE):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

SERIAL_PORT = os.getenv("STARK_SERIAL_PORT", "/dev/ttyUSB0")
SERIAL_BAUD = int(os.getenv("STARK_SERIAL_BAUD", "2400"))
SERIAL_TIMEOUT = float(os.getenv("STARK_SERIAL_TIMEOUT", "3.0"))

POLL_INTERVAL = float(os.getenv("STARK_POLL_INTERVAL", "2"))
DB_SAVE_INTERVAL = float(os.getenv("STARK_DB_SAVE_INTERVAL", "30"))
CLEANUP_INTERVAL = float(os.getenv("STARK_CLEANUP_INTERVAL", "86400"))

DB_PATH = os.getenv("STARK_DB_PATH", "/home/pi/stark_monitor.db")
RETENTION_DAYS = int(os.getenv("STARK_RETENTION_DAYS", "90"))

WEB_HOST = os.getenv("STARK_WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("STARK_WEB_PORT", "8080"))
