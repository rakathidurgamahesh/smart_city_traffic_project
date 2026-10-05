"""
Flask backend for the Smart City Traffic dashboard.

Serves:
  - the REST API under /api/*
  - the static frontend (webapp/frontend/) at /

Reads/writes the SAME SQLite DB the Java app and Python forecast job use
(traffic_project/data/traffic.db) — one source of truth across the whole
project, nothing is duplicated.

Run:
    cd webapp/backend
    python3 app.py
Then open http://localhost:5000 in a browser.
"""
import os
import sqlite3
import sys
import numpy as np
from datetime import datetime, timedelta

from flask import Flask, g, jsonify, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "traffic.db")
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))

# Reuse the existing regression job instead of re-implementing it.
sys.path.insert(0, os.path.join(PROJECT_ROOT, "python"))
import congestion_forecast as forecast_job  # noqa: E402

from graph_router import RoadNetworkGraph, multiplier_for_level  # noqa: E402

app = Flask(__name__, static_folder=None)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def rows_to_dicts(rows):
    return [dict(r) for r in rows]


# ---------------------------------------------------------------- frontend

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


# ---------------------------------------------------------------- API

@app.route("/api/summary")
def summary():
    db = get_db()
    roads = db.execute("SELECT COUNT(*) AS c FROM Road").fetchone()["c"]
    sensors = db.execute("SELECT COUNT(*) AS c FROM Sensor").fetchone()["c"]
    readings = db.execute("SELECT COUNT(*) AS c FROM Reading").fetchone()["c"]
    last_forecast = db.execute(
        "SELECT MAX(generated_at) AS t FROM congestion_forecast"
    ).fetchone()["t"]
    return jsonify({
        "roads": roads,
        "sensors": sensors,
        "readings": readings,
        "last_forecast_at": last_forecast,
    })


@app.route("/api/roads")
def list_roads():
    db = get_db()
    rows = db.execute(
        "SELECT road_id, road_name, start_node, end_node, length_km, lane_count FROM Road"
    ).fetchall()
    return jsonify(rows_to_dicts(rows))


@app.route("/api/sensors")
def list_sensors():
    road_id = request.args.get("road_id", type=int)
    db = get_db()
    if road_id:
        rows = db.execute(
            "SELECT sensor_id, road_id, location_desc, sensor_type FROM Sensor WHERE road_id = ?",
            (road_id,),
        ).fetchall()
    else:
        rows = db.execute("SELECT sensor_id, road_id, location_desc, sensor_type FROM Sensor").fetchall()
    return jsonify(rows_to_dicts(rows))


@app.route("/api/readings", methods=["POST"])
def record_reading():
    data = request.get_json(force=True)
    sensor_id = data.get("sensor_id")
    vehicle_count = data.get("vehicle_count")
    avg_speed_kmh = data.get("avg_speed_kmh")

    if sensor_id is None or vehicle_count is None or avg_speed_kmh is None:
        return jsonify({"error": "sensor_id, vehicle_count, avg_speed_kmh are required"}), 400

    db = get_db()
    sensor = db.execute("SELECT sensor_id FROM Sensor WHERE sensor_id = ?", (sensor_id,)).fetchone()
    if sensor is None:
        return jsonify({"error": f"no sensor with id {sensor_id}"}), 404

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = db.execute(
        "INSERT INTO Reading (sensor_id, ts, vehicle_count, avg_speed_kmh) VALUES (?, ?, ?, ?)",
        (sensor_id, ts, vehicle_count, avg_speed_kmh),
    )
    db.commit()
    return jsonify({"reading_id": cur.lastrowid, "ts": ts}), 201


@app.route("/api/aggregate/volume")
def aggregate_volume():
    """DBMS-style aggregation: average vehicle volume per road, busiest first."""
    db = get_db()
    rows = db.execute(
        """
        SELECT r.road_name, ROUND(AVG(rd.vehicle_count), 1) AS avg_volume
        FROM Road r
        JOIN Sensor s ON s.road_id = r.road_id
        JOIN Reading rd ON rd.sensor_id = s.sensor_id
        GROUP BY r.road_id
        ORDER BY avg_volume DESC
        """
    ).fetchall()
    return jsonify(rows_to_dicts(rows))


@app.route("/api/forecast/hotspots")
def forecast_hotspots():
    db = get_db()
    rows = db.execute(
        """
        SELECT r.road_name, cf.hour_of_day, cf.predicted_volume, cf.congestion_level
        FROM congestion_forecast cf
        JOIN Road r ON r.road_id = cf.road_id
        WHERE cf.congestion_level IN ('HIGH', 'SEVERE')
        ORDER BY cf.predicted_volume DESC
        """
    ).fetchall()
    return jsonify(rows_to_dicts(rows))


@app.route("/api/forecast/road/<int:road_id>")
def forecast_for_road(road_id):
    db = get_db()
    rows = db.execute(
        """
        SELECT hour_of_day, predicted_volume, congestion_level
        FROM congestion_forecast
        WHERE road_id = ?
        ORDER BY hour_of_day
        """,
        (road_id,),
    ).fetchall()
    return jsonify(rows_to_dicts(rows))


@app.route("/api/forecast/run", methods=["POST"])
def run_forecast():
    """Re-runs the same regression job used from the command line."""
    db = get_db()
    roads = db.execute("SELECT road_id, road_name FROM Road").fetchall()

    written = 0
    for road in roads:
        hourly_rows = forecast_job.fetch_hourly_averages(db, road["road_id"])
        predictions = forecast_job.fit_and_predict(hourly_rows)
        road_peak = max(predictions.values()) if predictions else 0.0

        for hour, predicted_volume in predictions.items():
            level = forecast_job.classify(predicted_volume, road_peak)
            db.execute(
                """
                INSERT INTO congestion_forecast (road_id, hour_of_day, predicted_volume, congestion_level)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(road_id, hour_of_day)
                DO UPDATE SET predicted_volume = excluded.predicted_volume,
                              congestion_level = excluded.congestion_level,
                              generated_at = datetime('now')
                """,
                (road["road_id"], hour, round(predicted_volume, 1), level),
            )
            written += 1
    db.commit()
    return jsonify({"roads_processed": len(roads), "forecast_rows_written": written})


@app.route("/api/graph")
def graph_data():
    """Nodes/edges for the network diagram, optionally colored by an hour's congestion."""
    hour = request.args.get("hour", type=int)
    db = get_db()
    roads = rows_to_dicts(db.execute(
        "SELECT road_id, road_name, start_node, end_node, length_km FROM Road"
    ).fetchall())

    level_by_road = {}
    if hour is not None:
        rows = db.execute(
            "SELECT road_id, congestion_level FROM congestion_forecast WHERE hour_of_day = ?",
            (hour,),
        ).fetchall()
        level_by_road = {r["road_id"]: r["congestion_level"] for r in rows}

    nodes = sorted({r["start_node"] for r in roads} | {r["end_node"] for r in roads})
    edges = []
    for r in roads:
        edges.append({
            "road_id": r["road_id"],
            "road_name": r["road_name"],
            "source": r["start_node"],
            "target": r["end_node"],
            "length_km": r["length_km"],
            "congestion_level": level_by_road.get(r["road_id"], "UNKNOWN"),
        })
    return jsonify({"nodes": nodes, "edges": edges})


@app.route("/api/route")
def find_route():
    from_node = request.args.get("from")
    to_node = request.args.get("to")
    hour = request.args.get("hour", type=int)

    if not from_node or not to_node or hour is None:
        return jsonify({"error": "from, to and hour query params are required"}), 400

    db = get_db()
    roads = rows_to_dicts(db.execute(
        "SELECT road_id, road_name, start_node, end_node, length_km FROM Road"
    ).fetchall())

    forecast_rows = db.execute(
        "SELECT road_id, congestion_level FROM congestion_forecast WHERE hour_of_day = ?",
        (hour,),
    ).fetchall()
    congestion_multiplier = {
        r["road_id"]: multiplier_for_level(r["congestion_level"]) for r in forecast_rows
    }

    graph = RoadNetworkGraph()
    graph.build(roads, congestion_multiplier)
    result = graph.shortest_path(from_node, to_node)

    if result is None:
        return jsonify({"error": f"no route found between {from_node} and {to_node}"}), 404

    path, total_cost, edges = result
    return jsonify({
        "path": path,
        "total_cost": round(total_cost, 2),
        "hour": hour,
        "segments": [
            {
                "road_name": e["road_name"],
                "road_id": e["road_id"],
                "length_km": e["length_km"],
                "congestion_level": next(
                    (r["congestion_level"] for r in forecast_rows if r["road_id"] == e["road_id"]),
                    "LOW",
                ),
            }
            for e in edges
        ],
    })


# ---------------------------------------------------------------- extended analytics

LEVEL_SCORE = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "SEVERE": 3}
JOIN_RS = "FROM Road r JOIN Sensor s ON s.road_id = r.road_id JOIN Reading rd ON rd.sensor_id = s.sensor_id"


def _current_levels(db):
    hour = datetime.now().hour
    rows = db.execute(
        "SELECT road_id, congestion_level FROM congestion_forecast WHERE hour_of_day = ?", (hour,)
    ).fetchall()
    return hour, {r["road_id"]: r["congestion_level"] for r in rows}


@app.route("/api/kpis")
def kpis():
    """Headline numbers: city speed, congestion index (0-100), busiest road, peak hour, alerts."""
    db = get_db()
    hour, levels = _current_levels(db)
    speed = db.execute("SELECT ROUND(AVG(avg_speed_kmh), 1) AS v FROM Reading").fetchone()["v"]
    busiest = db.execute(
        f"SELECT r.road_name, SUM(rd.vehicle_count) AS t {JOIN_RS} GROUP BY r.road_id ORDER BY t DESC LIMIT 1"
    ).fetchone()
    peak = db.execute(
        "SELECT CAST(strftime('%H', ts) AS INTEGER) AS h, AVG(vehicle_count) AS v "
        "FROM Reading GROUP BY h ORDER BY v DESC LIMIT 1"
    ).fetchone()
    n = len(levels) or 1
    index = round(100 * sum(LEVEL_SCORE.get(l, 0) for l in levels.values()) / (3 * n))
    alerts = sum(1 for l in levels.values() if l in ("HIGH", "SEVERE"))
    return jsonify({
        "current_hour": hour, "avg_speed": speed, "congestion_index": index, "alerts": alerts,
        "busiest_road": busiest["road_name"] if busiest else None,
        "peak_hour": peak["h"] if peak else None,
    })


@app.route("/api/alerts")
def alerts():
    """Live alert feed: roads predicted HIGH/SEVERE this hour + roads with slow recent traffic."""
    db = get_db()
    hour, levels = _current_levels(db)
    names = {r["road_id"]: r["road_name"] for r in db.execute("SELECT road_id, road_name FROM Road")}
    out = [
        {"severity": l, "road": names[rid], "message": f"Predicted {l.lower()} congestion at {hour:02d}:00"}
        for rid, l in levels.items() if l in ("HIGH", "SEVERE")
    ]
    cutoff = (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
    slow = db.execute(
        f"SELECT r.road_name, ROUND(AVG(rd.avg_speed_kmh), 1) AS spd {JOIN_RS} "
        "WHERE rd.ts >= ? GROUP BY r.road_id HAVING spd < 30", (cutoff,)
    ).fetchall()
    out += [{"severity": "SLOW", "road": r["road_name"],
             "message": f"Average speed {r['spd']} km/h over the last 3 hours"} for r in slow]
    out.sort(key=lambda a: a["severity"] != "SEVERE")
    return jsonify(out)


@app.route("/api/roads/detail")
def roads_detail():
    """One row per road: geometry, sensors, averages, forecast peak hour and current level."""
    db = get_db()
    _, levels = _current_levels(db)
    rows = rows_to_dicts(db.execute(
        """
        SELECT r.road_id, r.road_name, r.start_node || ' - ' || r.end_node AS route, r.length_km, r.lane_count,
               COUNT(DISTINCT s.sensor_id) AS sensors, ROUND(AVG(rd.vehicle_count), 1) AS avg_volume,
               ROUND(AVG(rd.avg_speed_kmh), 1) AS avg_speed, MAX(rd.ts) AS last_reading
        FROM Road r LEFT JOIN Sensor s ON s.road_id = r.road_id LEFT JOIN Reading rd ON rd.sensor_id = s.sensor_id
        GROUP BY r.road_id ORDER BY avg_volume DESC
        """
    ).fetchall())
    for r in rows:
        pk = db.execute(
            "SELECT hour_of_day FROM congestion_forecast WHERE road_id = ? ORDER BY predicted_volume DESC LIMIT 1",
            (r["road_id"],),
        ).fetchone()
        r["peak_hour"] = pk["hour_of_day"] if pk else None
        r["current_level"] = levels.get(r["road_id"], "UNKNOWN")
    return jsonify(rows)


@app.route("/api/analytics/hourly")
def analytics_hourly():
    """City-wide actual volume/speed per hour, next to the average regression forecast."""
    db = get_db()
    actual = {r["h"]: r for r in db.execute(
        "SELECT CAST(strftime('%H', ts) AS INTEGER) AS h, ROUND(AVG(vehicle_count), 1) AS volume, "
        "ROUND(AVG(avg_speed_kmh), 1) AS speed FROM Reading GROUP BY h")}
    fc = {r["h"]: r["v"] for r in db.execute(
        "SELECT hour_of_day AS h, ROUND(AVG(predicted_volume), 1) AS v FROM congestion_forecast GROUP BY h")}
    return jsonify([
        {"hour": h, "volume": actual[h]["volume"] if h in actual else None,
         "speed": actual[h]["speed"] if h in actual else None, "forecast": fc.get(h)}
        for h in range(24)
    ])


@app.route("/api/forecast/heatmap")
def forecast_heatmap():
    db = get_db()
    out = []
    for road in db.execute("SELECT road_id, road_name FROM Road"):
        rows = db.execute(
            "SELECT hour_of_day, congestion_level, predicted_volume FROM congestion_forecast "
            "WHERE road_id = ? ORDER BY hour_of_day", (road["road_id"],)).fetchall()
        out.append({"road_name": road["road_name"], "cells": rows_to_dicts(rows)})
    return jsonify(out)


@app.route("/api/readings/recent")
def recent_readings():
    limit = min(request.args.get("limit", 12, type=int), 100)
    rows = get_db().execute(
        f"SELECT rd.reading_id, rd.ts, r.road_name, s.sensor_id, s.sensor_type, rd.vehicle_count, rd.avg_speed_kmh "
        f"{JOIN_RS} ORDER BY rd.ts DESC, rd.reading_id DESC LIMIT ?", (limit,)).fetchall()
    return jsonify(rows_to_dicts(rows))


@app.route("/api/sensors/types")
def sensor_types():
    rows = get_db().execute(
        "SELECT sensor_type, COUNT(*) AS n FROM Sensor GROUP BY sensor_type").fetchall()
    return jsonify(rows_to_dicts(rows))


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"WARNING: {DB_PATH} not found. Run python/generate_sample_data.py first.")
    app.run(debug=True, port=5000)
