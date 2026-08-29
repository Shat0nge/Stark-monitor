import time
import threading
from datetime import datetime

import inverter
import parser
import database
import web

INTERVAL = 2
DB_SAVE_INTERVAL = 30
CLEANUP_INTERVAL = 86400

last_db_save = 0
last_cleanup = 0

state = {
    "online": False,
    "raw": "",
    "updated": "-",
    "v": {}
}

lock = threading.Lock()


def poll_once():
    raw = inverter.query("QPIGS")
    parsed = parser.parse_qpigs(raw)
    return raw, parsed


def update_state(raw, parsed):
    global last_db_save, last_cleanup

    if parsed is None:
        with lock:
            state["online"] = False

        web.set_state(
            False,
            raw.decode("ascii", errors="replace").strip(),
            datetime.now().strftime("%H:%M:%S"),
            {}
        )
        return

    now = time.time()
    updated = datetime.now().strftime("%H:%M:%S")
    raw_text = raw.decode("ascii", errors="replace").strip()

    with lock:
        state["online"] = True
        state["raw"] = raw_text
        state["updated"] = updated
        state["v"] = parsed

    web.set_state(
        True,
        raw_text,
        updated,
        parsed
    )

    if now - last_db_save >= DB_SAVE_INTERVAL:
        database.save_measurement(parsed, raw_text)
        last_db_save = now

    if now - last_cleanup >= CLEANUP_INTERVAL:
        database.cleanup()
        last_cleanup = now


def web_thread():
    try:
        web.start_server()
    except Exception as e:
        print("WEB ERROR:", repr(e), flush=True)


def run():
    print("STARK monitor starting", flush=True)

    threading.Thread(
        target=web_thread,
        daemon=True
    ).start()

    while True:
        try:
            raw, parsed = poll_once()
            update_state(raw, parsed)

        except Exception as e:
            print("POLL ERROR:", repr(e), flush=True)

            with lock:
                state["online"] = False

            web.set_state(
                False,
                "",
                datetime.now().strftime("%H:%M:%S"),
                {}
            )

        time.sleep(INTERVAL)


if __name__ == "__main__":
    run()
