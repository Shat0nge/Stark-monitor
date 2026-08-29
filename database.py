import sqlite3
import time

DB_PATH = "/home/pi/stark_monitor.db"
RETENTION_DAYS = 90


def connect():
    return sqlite3.connect(DB_PATH)


def save_measurement(v, raw_qpigs=None):
    with connect() as db:
        db.execute("""
        INSERT INTO measurements (
            ts, grid_voltage, grid_frequency, output_voltage, output_frequency,
            load_va, load_w, load_percent, bus_voltage, battery_voltage,
            battery_charge_current, battery_capacity, battery_charge_power,
            pv_charge_current, pv_current, pv_voltage, pv_power,
            pv_calculated_power, temperature, field15, status, field17,
            field18, device_status, raw_qpigs
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            int(time.time()),
            v.get("grid_voltage"),
            v.get("grid_frequency"),
            v.get("output_voltage"),
            v.get("output_frequency"),
            v.get("load_va"),
            v.get("load_w"),
            v.get("load_percent"),
            v.get("bus_voltage"),
            v.get("battery_voltage"),
            v.get("battery_charge_current"),
            v.get("battery_capacity"),
            v.get("battery_charge_power"),
            v.get("pv_charge_current"),
            v.get("pv_current"),
            v.get("pv_voltage"),
            v.get("pv_power"),
            v.get("pv_calculated_power"),
            v.get("temperature"),
            v.get("field15"),
            v.get("status"),
            v.get("field17"),
            v.get("field18"),
            v.get("device_status"),
            raw_qpigs
        ))
        db.commit()


def cleanup():
    cutoff = int(time.time()) - RETENTION_DAYS * 86400

    with connect() as db:
        db.execute(
            "DELETE FROM measurements WHERE ts < ?",
            (cutoff,)
        )
        db.commit()


def history(start_ts, end_ts, metrics, step=0):
    allowed = {
        "grid_voltage",
        "grid_frequency",
        "output_voltage",
        "output_frequency",
        "load_w",
        "load_percent",
        "battery_voltage",
        "battery_capacity",
        "battery_charge_current",
        "pv_current",
        "pv_voltage",
        "pv_power",
        "temperature",
    }

    metrics = [m for m in metrics if m in allowed]

    if not metrics:
        return []

    columns = ", ".join(metrics)

    if step and step > 1:
        sql = f"""
            SELECT
                (ts / ?) * ? AS ts,
                {", ".join(f"AVG({m}) AS {m}" for m in metrics)}
            FROM measurements
            WHERE ts >= ? AND ts <= ?
            GROUP BY (ts / ?)
            ORDER BY ts
        """
        params = (step, step, start_ts, end_ts, step)
    else:
        sql = f"""
            SELECT ts, {columns}
            FROM measurements
            WHERE ts >= ? AND ts <= ?
            ORDER BY ts
        """
        params = (start_ts, end_ts)

    with connect() as db:
        rows = db.execute(sql, params).fetchall()

    result = []

    for row in rows:
        item = {"ts": row[0]}

        for i, metric in enumerate(metrics, 1):
            item[metric] = row[i]

        result.append(item)

    return result
