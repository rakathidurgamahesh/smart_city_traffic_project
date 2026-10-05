"""
Generates realistic-looking synthetic sensor readings so the team can demo
end-to-end (Java dashboard + Python forecast) without waiting on real hardware.

Usage:
    python3 generate_sample_data.py [days]
"""
import sqlite3
import random
import sys
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "traffic.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")

ROADS = [
    # road_name,           start_node, end_node,  length_km, lanes, base_volume, peak_multiplier
    ("Kakinada",            "N1", "N2", 3.2, 4, 40, 3.0),
    ("Yanam",               "N2", "N3", 6.5, 6, 60, 2.2),
    ("Tuni",                "N1", "N4", 6.1, 6, 55, 2.0),
    ("Amalapuram",          "N3", "N5", 2.4, 2, 25, 3.5),
    ("Rajahmundry",         "N4", "N6", 9.0, 6, 70, 1.6),
    ("Konaseema",           "N2", "N5", 1.8, 2, 20, 2.8),
]

SENSOR_TYPES = ["INDUCTIVE_LOOP", "CAMERA", "RADAR"]


def rush_hour_factor(hour: int) -> float:
    """Morning (8-10) and evening (17-19.5) rush; light traffic overnight."""
    if 8 <= hour <= 10:
        return 1.0 + 0.9 * (1 - abs(hour - 9) / 1.5)
    if 17 <= hour <= 20:
        return 1.0 + 1.1 * (1 - abs(hour - 18.5) / 2.0)
    if 0 <= hour <= 5:
        return 0.25
    return 0.6


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    cur = conn.cursor()

    # Reset for a clean re-run
    for tbl in ("Reading", "Sensor", "Road", "congestion_forecast"):
        cur.execute(f"DELETE FROM {tbl}")

    road_ids = []
    for name, s, e, length, lanes, base_vol, peak_mult in ROADS:
        cur.execute(
            "INSERT INTO Road (road_name, start_node, end_node, length_km, lane_count) VALUES (?,?,?,?,?)",
            (name, s, e, length, lanes),
        )
        road_ids.append((cur.lastrowid, base_vol, peak_mult))

    sensor_ids = []
    for road_id, base_vol, peak_mult in road_ids:
        n_sensors = random.randint(1, 3)
        for i in range(n_sensors):
            cur.execute(
                "INSERT INTO Sensor (road_id, location_desc, sensor_type) VALUES (?,?,?)",
                (road_id, f"KM marker {i+1}", random.choice(SENSOR_TYPES)),
            )
            sensor_ids.append((cur.lastrowid, road_id, base_vol, peak_mult))

    start = datetime.now() - timedelta(days=days)
    n_rows = 0
    for sensor_id, road_id, base_vol, peak_mult in sensor_ids:
        t = start
        end = datetime.now()
        while t < end:
            factor = rush_hour_factor(t.hour) * peak_mult
            noise = random.uniform(0.85, 1.15)
            vehicle_count = max(0, int(base_vol * factor * noise + random.gauss(0, 3)))
            avg_speed = max(8.0, 60 - (vehicle_count / (base_vol * peak_mult + 1)) * 40 + random.gauss(0, 2))
            cur.execute(
                "INSERT INTO Reading (sensor_id, ts, vehicle_count, avg_speed_kmh) VALUES (?,?,?,?)",
                (sensor_id, t.strftime("%Y-%m-%d %H:%M:%S"), vehicle_count, round(avg_speed, 1)),
            )
            n_rows += 1
            t += timedelta(minutes=15)

    conn.commit()
    conn.close()
    print(f"Seeded {len(road_ids)} roads, {len(sensor_ids)} sensors, {n_rows} readings over {days} days.")
    print(f"DB written to: {os.path.abspath(DB_PATH)}")


if __name__ == "__main__":
    main()
