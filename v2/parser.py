def _float(x, default=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _int(x, default=0):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def parse_qpigs(raw):
    if raw is None:
        return None

    if isinstance(raw, bytes):
        text = raw.decode("ascii", errors="replace").strip()
    else:
        text = str(raw).strip()

    if not text.startswith("("):
        return None

    text = text[1:]

    # Убираем хвост CRC/служебные символы после полезных полей.
    parts = text.split()

    # Для QPIGS нам нужны первые 21 числовых/текстовых полей.
    if len(parts) < 21:
        return None

    try:
        grid_voltage = _float(parts[0])
        grid_frequency = _float(parts[1])
        output_voltage = _float(parts[2])
        output_frequency = _float(parts[3])

        load_va = _float(parts[4])
        load_w = _float(parts[5])
        load_percent = _float(parts[6])

        bus_voltage = _float(parts[7])
        battery_voltage = _float(parts[8])

        battery_charge_current = _float(parts[9])
        battery_capacity = _float(parts[10])

        # ВАЖНО:
        # QPIGS field 11 = heatsink temperature.
        temperature = _float(parts[11])

        # QPIGS field 12 = PV input current.
        pv_current = _float(parts[12])

        # QPIGS field 13 = PV input voltage.
        pv_voltage = _float(parts[13])

        # QPIGS field 14 = SCC voltage.
        scc_voltage = _float(parts[14])

        # QPIGS field 15 = battery discharge current.
        battery_discharge_current = _float(parts[15])

        status = parts[16]

        field17 = parts[17]
        field18 = parts[18]

        # QPIGS field 19 = PV charging power.
        pv_power = _float(parts[19])

        device_status = parts[20]

        # Расчётная мощность PV по U * I.
        pv_calculated_power = pv_voltage * pv_current

        # Мощность заряда АКБ по U * I.
        battery_charge_power = battery_voltage * battery_charge_current

        return {
            "grid_voltage": grid_voltage,
            "grid_frequency": grid_frequency,
            "output_voltage": output_voltage,
            "output_frequency": output_frequency,

            "load_va": load_va,
            "load_w": load_w,
            "load_percent": load_percent,

            "bus_voltage": bus_voltage,
            "battery_voltage": battery_voltage,
            "battery_charge_current": battery_charge_current,
            "battery_capacity": battery_capacity,

            "temperature": temperature,

            "pv_current": pv_current,
            "pv_voltage": pv_voltage,
            "scc_voltage": scc_voltage,
            "battery_discharge_current": battery_discharge_current,

            "status": status,
            "field17": field17,
            "field18": field18,

            "pv_power": pv_power,
            "device_status": device_status,

            "battery_charge_power": battery_charge_power,
            "pv_calculated_power": pv_calculated_power,
        }

    except Exception:
        return None
