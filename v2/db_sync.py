import sqlite3
import subprocess
import time
import shlex

from config import (
    DB_PATH,
    DB_SYNC_ENABLED,
    DB_SYNC_HOST,
    DB_SYNC_PORT,
    DB_SYNC_USER,
    DB_SYNC_DB_PATH,
    DB_SYNC_INTERVAL,
)


COLUMNS = [
    "id", "ts",
    "grid_voltage", "grid_frequency",
    "output_voltage", "output_frequency",
    "load_va", "load_w", "load_percent",
    "bus_voltage", "battery_voltage",
    "battery_charge_current", "battery_capacity",
    "battery_charge_power",
    "pv_charge_current", "pv_current", "pv_voltage",
    "pv_power", "pv_calculated_power",
    "temperature", "field15", "status", "field17",
    "field18", "device_status", "raw_qpigs"
]

COLS = ", ".join(COLUMNS)
PLACEHOLDERS = ", ".join("?" for _ in COLUMNS)


def get_local_last_id():
    db = sqlite3.connect(DB_PATH)
    try:
        row = db.execute(
            "SELECT COALESCE(MAX(id), 0) FROM measurements"
        ).fetchone()
        return int(row[0])
    finally:
        db.close()


def get_remote_last_id():
    remote_code = (
        "import sqlite3; "
        f"db=sqlite3.connect({DB_SYNC_DB_PATH!r}); "
        "print(db.execute("
        "'SELECT COALESCE(MAX(id),0) FROM measurements'"
        ").fetchone()[0]); "
        "db.close()"
    )

    remote_command = "python3 -c " + shlex.quote(remote_code)

    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=8",
        "-p", str(DB_SYNC_PORT),
        f"{DB_SYNC_USER}@{DB_SYNC_HOST}",
        remote_command
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=15
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or "SSH failed"
        )

    output = result.stdout.strip()

    if not output:
        raise RuntimeError("Remote sqlite query returned empty output")

    return int(output)


def fetch_new_rows(after_id):
    db = sqlite3.connect(DB_PATH)

    try:
        return db.execute(
            f"""
            SELECT {COLS}
            FROM measurements
            WHERE id > ?
            ORDER BY id
            """,
            (after_id,)
        ).fetchall()

    finally:
        db.close()


def send_rows(rows):
    if not rows:
        return 0

    payload = "\n".join(
        "\t".join(
            "" if value is None
            else str(value).replace("\t", " ").replace("\n", " ")
            for value in row
        )
        for row in rows
    ) + "\n"

    remote_script = f"""
import sqlite3
import sys

db = sqlite3.connect({DB_SYNC_DB_PATH!r})

columns = {COLUMNS!r}
placeholders = {PLACEHOLDERS!r}

rows = []

for line in sys.stdin:
    parts = line.rstrip("\\n").split("\\t")

    if len(parts) != len(columns):
        continue

    converted = []

    for i, value in enumerate(parts):

        if value == "":
            converted.append(None)

        elif columns[i] in ("id", "ts"):
            converted.append(int(value))

        elif columns[i] in (
            "field15",
            "status",
            "field17",
            "field18",
            "device_status",
            "raw_qpigs"
        ):
            converted.append(value)

        else:
            try:
                converted.append(float(value))
            except ValueError:
                converted.append(value)

    rows.append(tuple(converted))

sql = (
    "INSERT OR IGNORE INTO measurements "
    f"({{', '.join(columns)}}) "
    f"VALUES ({{placeholders}})"
)

try:
    db.execute("BEGIN")
    db.executemany(sql, rows)
    db.commit()
    print(len(rows), flush=True)

except Exception:
    db.rollback()
    raise

finally:
    db.close()
"""

    remote_command = "python3 -c " + shlex.quote(remote_script)

    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=8",
        "-p", str(DB_SYNC_PORT),
        f"{DB_SYNC_USER}@{DB_SYNC_HOST}",
        remote_command
    ]

    result = subprocess.run(
        cmd,
        input=payload,
        capture_output=True,
        text=True,
        timeout=60
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or "sync SSH failed"
        )

    return int(result.stdout.strip() or "0")


def sync_once():
    remote_id = get_remote_last_id()
    local_id = get_local_last_id()

    print(
        f"DB SYNC: remote_id={remote_id}, local_id={local_id}",
        flush=True
    )

    if local_id <= remote_id:
        print(
            "DB SYNC: already up to date",
            flush=True
        )
        return

    rows = fetch_new_rows(remote_id)

    if not rows:
        print(
            "DB SYNC: no rows fetched",
            flush=True
        )
        return

    sent = send_rows(rows)

    print(
        f"DB SYNC: sent {sent} rows, "
        f"ids {rows[0][0]}..{rows[-1][0]}",
        flush=True
    )


def run():
    print(
        f"DB SYNC: enabled, "
        f"target={DB_SYNC_USER}@{DB_SYNC_HOST}:{DB_SYNC_PORT}, "
        f"interval={DB_SYNC_INTERVAL}s",
        flush=True
    )

    while True:
        try:
            sync_once()

        except Exception as e:
            print(
                f"DB SYNC ERROR: {e!r}",
                flush=True
            )

        time.sleep(DB_SYNC_INTERVAL)


if __name__ == "__main__":

    if DB_SYNC_ENABLED:
        run()

    else:
        print(
            "DB SYNC: disabled",
            flush=True
        )
