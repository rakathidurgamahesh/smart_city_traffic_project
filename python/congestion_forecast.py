"""
DBMS Unit 2 (SQL aggregation) + regression forecast.

1. Aggregates raw Reading rows into avg vehicle volume per (road, hour_of_day).
2. Fits a small polynomial regression per road: volume ~ f(hour_of_day).
3. Predicts volume for every hour 0-23 and classifies congestion level.
4. Upserts results into congestion_forecast, which the Java dashboard reads.

Usage:
    python3 congestion_forecast.py
"""
import sqlite3
import os
import numpy as np

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "traffic.db")

# Thresholds as a fraction of each road's own peak predicted volume,
# so classification adapts per-road instead of using one fixed number.
LEVEL_THRESHOLDS = [
    (0.35, "LOW"),
    (0.60, "MODERATE"),
    (0.85, "HIGH"),
    (1.01, "SEVERE"),
]


def classify(volume: float, road_peak: float) -> str:
    if road_peak <= 0:
        return "LOW"
    ratio = volume / road_peak
    for cutoff, label in LEVEL_THRESHOLDS:
        if ratio <= cutoff:
            return label
    return "SEVERE"


def fetch_hourly_averages(conn, road_id):
    """DBMS aggregation: AVG(vehicle_count) GROUP BY hour_of_day for one road."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT CAST(strftime('%H', rd.ts) AS INTEGER) AS hour_of_day,
               AVG(rd.vehicle_count) AS avg_volume
        FROM Sensor s
        JOIN Reading rd ON rd.sensor_id = s.sensor_id
        WHERE s.road_id = ?
        GROUP BY hour_of_day
        ORDER BY hour_of_day
        """,
        (road_id,),
    )
    return cur.fetchall()


def _design_matrix(hours: np.ndarray, n_harmonics: int = 3) -> np.ndarray:
    """
    Builds Fourier (harmonic) regression features for a 24-hour daily cycle:
    [1, sin(2*pi*h/24), cos(2*pi*h/24), sin(4*pi*h/24), cos(4*pi*h/24), ...]
    A plain polynomial in `hour` can only produce a single hump, but real
    traffic has TWO daily peaks (morning + evening) — harmonic regression is
    the standard linear-regression trick for fitting periodic data like this.
    """
    cols = [np.ones_like(hours)]
    for k in range(1, n_harmonics + 1):
        cols.append(np.sin(2 * np.pi * k * hours / 24))
        cols.append(np.cos(2 * np.pi * k * hours / 24))
    return np.column_stack(cols)


def fit_and_predict(hourly_rows):
    """
    Fits volume as a function of hour-of-day using harmonic (Fourier) linear
    regression, solved with least squares. Returns predicted volume for
    hours 0..23. Falls back to a flat average if too little data is present.
    """
    if len(hourly_rows) < 6:
        avg = np.mean([v for _, v in hourly_rows]) if hourly_rows else 0.0
        return {h: avg for h in range(24)}

    hours = np.array([h for h, _ in hourly_rows], dtype=float)
    volumes = np.array([v for _, v in hourly_rows], dtype=float)

    n_harmonics = 3 if len(hourly_rows) >= 8 else 1
    X = _design_matrix(hours, n_harmonics)
    coeffs, *_ = np.linalg.lstsq(X, volumes, rcond=None)

    all_hours = np.arange(24, dtype=float)
    X_all = _design_matrix(all_hours, n_harmonics)
    preds = X_all @ coeffs

    return {int(h): max(0.0, float(p)) for h, p in zip(all_hours, preds)}


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT road_id, road_name FROM Road")
    roads = cur.fetchall()

    total_written = 0
    for road_id, road_name in roads:
        hourly_rows = fetch_hourly_averages(conn, road_id)
        predictions = fit_and_predict(hourly_rows)
        road_peak = max(predictions.values()) if predictions else 0.0

        for hour, predicted_volume in predictions.items():
            level = classify(predicted_volume, road_peak)
            cur.execute(
                """
                INSERT INTO congestion_forecast (road_id, hour_of_day, predicted_volume, congestion_level)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(road_id, hour_of_day)
                DO UPDATE SET predicted_volume = excluded.predicted_volume,
                              congestion_level = excluded.congestion_level,
                              generated_at = datetime('now')
                """,
                (road_id, hour, round(predicted_volume, 1), level),
            )
            total_written += 1

        print(f"[{road_name}] peak predicted volume: {road_peak:.1f} veh, "
              f"hottest hour: {max(predictions, key=predictions.get)}:00")

    conn.commit()
    conn.close()
    print(f"\nWrote/updated {total_written} forecast rows across {len(roads)} roads.")


if __name__ == "__main__":
    main()
