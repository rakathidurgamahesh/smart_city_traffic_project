-- ============================================================
-- Smart City Traffic Sensor System — Database Schema
-- Subject mapping: DBMS Unit 1 (ER Model -> Relations), Unit 2 (SQL, aggregation)
-- Works on SQLite (used by the demo) and MySQL (minor type tweaks noted inline)
-- ============================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------
-- ROAD: a stretch of road identified by two intersection nodes.
-- Doubles as the "vertex/edge" data ADSA uses for the road-network graph.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Road (
    road_id       INTEGER PRIMARY KEY AUTOINCREMENT,   -- MySQL: INT AUTO_INCREMENT
    road_name     TEXT NOT NULL,
    start_node    TEXT NOT NULL,      -- e.g. intersection name/code, used as graph vertex
    end_node      TEXT NOT NULL,      -- graph vertex
    length_km     REAL NOT NULL,
    lane_count    INTEGER NOT NULL DEFAULT 2
);

-- ---------------------------------------------------------------
-- SENSOR: a physical sensor installed on a Road (1 Road -> many Sensors)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Sensor (
    sensor_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    road_id       INTEGER NOT NULL,
    location_desc TEXT,
    sensor_type   TEXT CHECK (sensor_type IN ('INDUCTIVE_LOOP','CAMERA','RADAR')) DEFAULT 'INDUCTIVE_LOOP',
    installed_on  TEXT DEFAULT (date('now')),
    FOREIGN KEY (road_id) REFERENCES Road(road_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------
-- READING: raw telemetry from a Sensor (1 Sensor -> many Readings)
-- This is the high-volume fact table.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Reading (
    reading_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id     INTEGER NOT NULL,
    ts            TEXT NOT NULL,      -- ISO timestamp 'YYYY-MM-DD HH:MM:SS'
    vehicle_count INTEGER NOT NULL,
    avg_speed_kmh REAL NOT NULL,
    FOREIGN KEY (sensor_id) REFERENCES Sensor(sensor_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_reading_sensor_ts ON Reading(sensor_id, ts);

-- ---------------------------------------------------------------
-- CONGESTION_FORECAST: written by the Python regression job.
-- One predicted row per Road per hour-of-day.
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS congestion_forecast (
    forecast_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    road_id           INTEGER NOT NULL,
    hour_of_day       INTEGER NOT NULL CHECK (hour_of_day BETWEEN 0 AND 23),
    predicted_volume  REAL NOT NULL,       -- predicted vehicle count for that hour
    congestion_level  TEXT CHECK (congestion_level IN ('LOW','MODERATE','HIGH','SEVERE')),
    generated_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (road_id) REFERENCES Road(road_id) ON DELETE CASCADE,
    UNIQUE(road_id, hour_of_day)   -- forecast job upserts one row per road+hour
);

-- ============================================================
-- Sample aggregation queries (DBMS Unit 2) — put these in your report
-- ============================================================

-- 1. Total & average traffic volume per road, all-time
-- SELECT r.road_name,
--        COUNT(rd.reading_id)      AS total_readings,
--        SUM(rd.vehicle_count)     AS total_vehicles,
--        ROUND(AVG(rd.vehicle_count),2) AS avg_vehicles_per_reading,
--        ROUND(AVG(rd.avg_speed_kmh),2) AS avg_speed
-- FROM Road r
-- JOIN Sensor s   ON s.road_id = r.road_id
-- JOIN Reading rd ON rd.sensor_id = s.sensor_id
-- GROUP BY r.road_id
-- ORDER BY total_vehicles DESC;

-- 2. Hourly traffic volume per road (feeds the Python regression)
-- SELECT r.road_id, r.road_name,
--        CAST(strftime('%H', rd.ts) AS INTEGER) AS hour_of_day,
--        AVG(rd.vehicle_count) AS avg_volume
-- FROM Road r
-- JOIN Sensor s   ON s.road_id = r.road_id
-- JOIN Reading rd ON rd.sensor_id = s.sensor_id
-- GROUP BY r.road_id, hour_of_day
-- ORDER BY r.road_id, hour_of_day;

-- 3. Current predicted hotspots (for the Java dashboard)
-- SELECT r.road_name, cf.hour_of_day, cf.predicted_volume, cf.congestion_level
-- FROM congestion_forecast cf
-- JOIN Road r ON r.road_id = cf.road_id
-- WHERE cf.congestion_level IN ('HIGH','SEVERE')
-- ORDER BY cf.predicted_volume DESC;
