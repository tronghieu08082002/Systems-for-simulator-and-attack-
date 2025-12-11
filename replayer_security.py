 #!/usr/bin/env python3			
"""
Hybrid Canonical CSV Replayer for SECURITY/FACILITIES ZONE
---------------------------------------------------------
- Zone: SECURITY (~40 devices concept)
- Keeps original device list and logic
Usage:
  python3 replayer_security.py --indir datasets --broker 10.12.112.191 --port 8883
"""

from __future__ import annotations
import argparse, json, os, random, threading, time
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import pandas as pd
import paho.mqtt.client as mqtt
import ssl

# -----------------------------------------------------------------------------
# Canonical column candidates
# -----------------------------------------------------------------------------
TIMESTAMP_CANDIDATES = [
    "timestamp", "ts", "time", "frame.time_epoch", "frame.time_relative",
    "Time", "SniffTimestamp"
]
MSGTYP_CANDIDATES = ["mqtt.msgtype", "msg_type", "message_type", "packet_type", "mqtt.msgtype_str"]

# -----------------------------------------------------------------------------
# Zone & tenancy
# -----------------------------------------------------------------------------
TENANT = "security"
ZONE = "security"

# -----------------------------------------------------------------------------
# Device set cho Production Floor (original full list, unchanged)
# -----------------------------------------------------------------------------
DEVICES = [
    # -------- DoorLock --------
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door1", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door2", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door3", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door4", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door5", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door6", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door7", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door8", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door9", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door10", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door11", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door12", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door13", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door14", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door15", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door16", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door17", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door18", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door19", "door123"),
    ("DoorLock", "DoorlockMQTTset.csv", "security-sensor_door20", "door123"),

    # -------- CO-Gas --------
    ("CO-Gas", "CO-GasMQTTset.csv", "security-sensor_co1", "co123"),
    ("CO-Gas", "CO-GasMQTTset.csv", "security-sensor_co2", "co123"),
    ("CO-Gas", "CO-GasMQTTset.csv", "security-sensor_co3", "co123"),
    ("CO-Gas", "CO-GasMQTTset.csv", "security-sensor_co4", "co123"),
    ("CO-Gas", "CO-GasMQTTset.csv", "security-sensor_co5", "co123"),

    # -------- AirQuality --------
    ("AirQuality", "air-quality_gotham.csv", "security-sensor_air1", "air123"),
    ("AirQuality", "air-quality_gotham.csv", "security-sensor_air2", "air123"),
    ("AirQuality", "air-quality_gotham.csv", "security-sensor_air3", "air123"),
    ("AirQuality", "air-quality_gotham.csv", "security-sensor_air4", "air123"),
    ("AirQuality", "air-quality_gotham.csv", "security-sensor_air5", "air123"),

    # -------- Smoke --------
    ("Smoke", "SmokeMQTTset.csv", "security-sensor_smoke1", "smoke123"),
    ("Smoke", "SmokeMQTTset.csv", "security-sensor_smoke2", "smoke123"),
    ("Smoke", "SmokeMQTTset.csv", "security-sensor_smoke3", "smoke123"),

    # -------- FlameSensor --------
    ("FlameSensor", "Edge-IIoTset_flame_sensor.csv", "security-sensor_flame1", "flame123"),
    ("FlameSensor", "Edge-IIoTset_flame_sensor.csv", "security-sensor_flame2", "flame123"),


]

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
def mk_client(client_id: str, username: Optional[str] = None, password: Optional[str] = None) -> mqtt.Client:
    """Create MQTT client with TLS and optional username/password."""
    c = mqtt.Client(client_id=client_id)
    if username:
        c.username_pw_set(username, password)

    ca_path = os.path.join(os.path.dirname(__file__), "certs", "ca-cert.pem")
    if not os.path.exists(ca_path):
        print(f"[WARN] CA certificate not found at {ca_path}. TLS may fail.")

    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_path if os.path.exists(ca_path) else None)
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    c.tls_set_context(ctx)
    return c


def resolve_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _parse_timestamp_series(ts: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(ts):
        s = ts.astype(float)
        if s.dropna().median() > 1e12:
            s = s / 1000.0
        return s
    dt = pd.to_datetime(ts, errors="coerce", utc=True)
    return dt.view("int64") / 1e9


def _median_interval(seconds: pd.Series) -> float:
    diffs = seconds.diff().dropna()
    if diffs.empty:
        return 1.0
    diffs = diffs[diffs > 0]
    if diffs.empty:
        return 1.0
    return float(diffs.median())


def _is_publish(row: pd.Series, msgtype_col: Optional[str]) -> bool:
    if not msgtype_col or msgtype_col not in row or pd.isna(row[msgtype_col]):
        return True
    v = row[msgtype_col]
    try:
        if str(v).strip().isdigit():
            return int(v) == 3
    except Exception:
        pass
    s = str(v).lower()
    return ("publish" in s) and ("command" not in s) and ("req" not in s)


def random_value_for_device(username: str) -> float:
    ranges: dict[str, Tuple[float, float]] = {
        "security-sensor_door1": (0, 1),
        "security-sensor_co1": (0.0, 50.0),
        "security-sensor_air1": (0.0, 150.0),
        "security-sensor_smoke1": (0.0, 10.0),
        "security-sensor_flame1": (0, 1),
        "security-sensor_motion": (0, 1),
    }
    lo, hi = ranges.get(username, (0.0, 100.0))
    val = random.uniform(lo, hi)
    return round(val, 3 if hi <= 1 else 2 if hi <= 100 else 1)

# -----------------------------------------------------------------------------
# Device thread
# -----------------------------------------------------------------------------
def device_thread(device_name: str, csv_path: str, broker: str, port: int,
                  username: Optional[str], password: Optional[str],
                  speed_factor: float, min_interval: float):
    topic = f"factory/{TENANT}/{username}/telemetry"
    client_id = f"{ZONE}-{username}-replayer"
    client = mk_client(client_id, username, password)

    # connect with retry
    connected = False
    while not connected:
        try:
            client.connect(broker, port, keepalive=60)
            client.loop_start()
            connected = True
            print(f"[{ZONE}:{device_name}] Connected to {broker}:{port}")
        except Exception as e:
            print(f"[{ZONE}:{device_name}] Connection failed, retrying in 5s: {e}")
            time.sleep(5)

    # load csv
    try:
        df = pd.read_csv(csv_path, low_memory=False)
        print(f"[{ZONE}:{device_name}] Loaded {len(df)} rows from {csv_path}")
    except Exception as e:
        print(f"[{ZONE}:{device_name}] Error loading CSV: {e}")
        client.loop_stop()
        client.disconnect()
        return

    ts_col = resolve_column(df, TIMESTAMP_CANDIDATES)
    msg_col = resolve_column(df, MSGTYP_CANDIDATES)

    if not ts_col:
        print(f"[{ZONE}:{device_name}] No timestamp column found; using 1.0s default interval.")
        seconds = pd.Series(range(len(df)), dtype=float)
        base_interval = 1.0
    else:
        seconds = _parse_timestamp_series(df[ts_col])
        base_interval = _median_interval(seconds)
        if pd.isna(seconds).all():
            seconds = pd.Series(range(len(df)), dtype=float)
            base_interval = 1.0

    # precompute intervals
    intervals = []
    for i in range(len(df)):
        if i < len(df) - 1 and ts_col and pd.notna(seconds.iloc[i]) and pd.notna(seconds.iloc[i+1]):
            delta = float(seconds.iloc[i+1] - seconds.iloc[i])
        else:
            delta = base_interval
        if not (delta > 0):
            delta = base_interval
        delta = max(delta / max(speed_factor, 1e-6), min_interval)
        intervals.append(delta)

    # publish loop
    i = 0
    try:
        while True:
            row = df.iloc[i]
            if _is_publish(row, msg_col):
                payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "value": random_value_for_device(username),
                    "client_id": client_id,
                    "zone": ZONE,
                }
                try:
                    client.publish(topic, json.dumps(payload))
                    print(f"[{ZONE}:{device_name}] Row {i+1}/{len(df)} → published: {payload}")
                except Exception as e:
                    print(f"[{ZONE}:{device_name}] Publish error: {e}")
            else:
                print(f"[{ZONE}:{device_name}] Row {i+1}/{len(df)} skipped (msgtype not publish)")
            time.sleep(intervals[i])
            i = (i + 1) % len(df)
    finally:
        client.loop_stop()
        client.disconnect()

# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="CSV Replayer (Security Zone)")
    parser.add_argument("--indir", default="datasets", help="Folder containing device CSV files")
    parser.add_argument("--broker", default="emqx", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=8883, help="MQTT broker port")
    parser.add_argument("--speed-factor", type=float, default=1.0)
    parser.add_argument("--min-interval", type=float, default=0.05)
    args = parser.parse_args()

    print("CSV Replayer (Security Zone) Starting...")
    print(f"Broker: {args.broker}:{args.port}")
    print(f"Data directory: {args.indir}")
    print(f"Speed factor: {args.speed_factor}")
    print("=" * 70)

    threads: List[threading.Thread] = []
    for name, fname, username, password in DEVICES:
        path = os.path.join(args.indir, fname)
        if not os.path.exists(path):
            print(f"Missing {path} - skipping {name}")
            continue
        t = threading.Thread(
            target=device_thread,
            args=(name, path, args.broker, args.port, username, password, args.speed_factor, args.min_interval),
            daemon=True,
        )
        t.start()
        threads.append(t)
        print(f"Started {name} → topic factory/{TENANT}/{name}/telemetry (file: {fname}, user: {username})")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping replayer...")

if __name__ == "__main__":
    main()

