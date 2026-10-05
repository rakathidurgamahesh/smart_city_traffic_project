# Smart City Traffic Sensor System

A working prototype: sensors → SQLite DB → Java records/aggregates/dashboards,
Python forecasts congestion by hour and writes it back for Java to display.

```
┌─────────────┐   readings    ┌──────────────┐   SELECT/GROUP BY   ┌────────────────────┐
│ Java OOPJ    │ ───────────▶ │  SQLite DB    │ ◀─────────────────  │ Python regression   │
│ TrafficMonitor│ ◀────────── │ traffic.db   │ ───────────────────▶ │ congestion_forecast │
│ App (dashboard)│  read forecasts            │   INSERT forecast    │        job          │
└─────────────┘               └──────────────┘                      └────────────────────┘
       │
       └── ADSA: RoadNetworkGraph.java — road network as a graph, Dijkstra for
           least-congested routing between intersections
```

## Subject mapping (for your report)

| Subject | Where |
|---|---|
| DBMS Unit 1 (ER model) | `db/er_model.md`, `db/schema.sql` |
| DBMS Unit 2 (SQL aggregation) | `db/schema.sql` (queries 1-3), `ReadingDAO.aggregateVolumeByRoad()`, `congestion_forecast.py` |
| DMGT Unit 2 (relations) | `docs/dmgt_relations.md` |
| ADSA Unit 2 (graph) | `java/src/graph/RoadNetworkGraph.java` — Dijkstra's algorithm |
| OOPJ | `java/src/model/*`, `java/src/dao/*`, `java/src/app/TrafficMonitorApp.java` |
| Python (regression) | `python/congestion_forecast.py` — harmonic (Fourier) linear regression |
| Full-stack dashboard (bonus, not required by the course brief) | `webapp/backend/app.py` (Flask REST API), `webapp/frontend/` (HTML/CSS/JS dashboard) |

## Project layout

```
traffic_project/
├── db/
│   ├── schema.sql        # tables + sample aggregation SQL
│   └── er_model.md       # ER diagram + normalization notes
├── docs/
│   └── dmgt_relations.md
├── python/
│   ├── generate_sample_data.py   # seeds traffic.db with synthetic readings
│   └── congestion_forecast.py    # aggregates + regresses + writes forecast
├── java/
│   └── src/
│       ├── model/    Road.java, Sensor.java, Reading.java, CongestionForecast.java
│       ├── dao/       DatabaseConnection.java, RoadDAO.java, SensorDAO.java,
│       │              ReadingDAO.java, ForecastDAO.java
│       ├── graph/    RoadNetworkGraph.java   (ADSA)
│       └── app/      TrafficMonitorApp.java (console dashboard, entry point)
├── webapp/
│   ├── backend/
│   │   ├── app.py            # Flask REST API + serves the frontend
│   │   ├── graph_router.py   # Python port of the Dijkstra routing logic
│   │   └── requirements.txt
│   └── frontend/
│       ├── index.html        # dashboard layout
│       ├── style.css
│       ├── app.js            # core panels: volume chart, network diagram, forms
│       └── extras.js         # KPIs, trend, heatmap, road drill-down, alerts, live feed
└── data/
    └── traffic.db    # created when you run generate_sample_data.py
```

## Running the Python side (no extra setup — uses stdlib sqlite3 + numpy)

```bash
cd python
python3 generate_sample_data.py 14     # seed 14 days of synthetic readings
python3 congestion_forecast.py         # aggregate + regress + write forecasts
```

You should see per-road peak hour output, and `data/traffic.db` will now have
rows in `congestion_forecast`.

## Running the Java side

The Java code uses plain JDBC against the same SQLite file, so you need the
**sqlite-jdbc** driver jar (one file, no other dependencies):

1. Download it once: https://github.com/xerial/sqlite-jdbc/releases
   (grab `sqlite-jdbc-<version>.jar`, e.g. `sqlite-jdbc-3.46.1.0.jar`)
   and drop it in `java/lib/`.
2. Compile:
   ```bash
   cd java
   mkdir -p bin
   javac -d bin -cp "lib/sqlite-jdbc-3.46.1.0.jar" $(find src -name "*.java")
   ```
3. Run (from the `java/` directory, since `DatabaseConnection` points at `../data/traffic.db`):
   ```bash
   java -cp "bin:lib/sqlite-jdbc-3.46.1.0.jar" app.TrafficMonitorApp
   ```
   (On Windows use `;` instead of `:` in the classpath.)

You'll get a menu to record new readings, view aggregated volume per road,
view predicted hotspots (written by the Python job), and query the
least-congested route between two intersections.

> Note: this sandbox only has a JRE, not a full JDK, so the Java code here was
> written and reviewed carefully but not compiled in this environment — compile
> it once locally with the steps above before your demo, in case of a typo.

## Running the web dashboard (frontend + backend)

A browser-based dashboard sits on top of the same `data/traffic.db` — no
separate database, no duplicated logic (the forecast regression is imported
straight from `python/congestion_forecast.py`, and the routing is a Python
port of the same Dijkstra logic as the Java `RoadNetworkGraph`).

**Setup (one time):**
```bash
cd webapp/backend
pip install -r requirements.txt --break-system-packages   # just Flask
```

**Run it:**
```bash
# make sure the DB exists first:
cd ../../python && python3 generate_sample_data.py 14 && python3 congestion_forecast.py

cd ../webapp/backend
python3 app.py
```
Then open **http://localhost:5000** in a browser. One process serves both the
API and the static dashboard — nothing else to start.

**What the dashboard shows:**
- Summary cards (roads / sensors / readings logged) and a "Re-run forecast"
  button that re-triggers the regression job live.
- A bar chart of average traffic volume per road (Chart.js).
- The road network as a diagram, color-coded by predicted congestion for
  whichever hour you drag the slider to.
- The predicted hotspots table (same data the Java dashboard's option 3 shows).
- A route finder (from-node, to-node, hour) that runs Dijkstra server-side and
  highlights the chosen path on the network diagram.
- A form to record a new sensor reading, which updates the volume chart
  immediately.

**Extended dashboard panels (v2):**
- KPI row: congestion index for the current hour (0-100), average speed, active alerts, busiest road, city peak hour.
- City traffic by hour: actual volume vs regression forecast, with average speed on a second axis.
- Congestion heatmap: every road x 24 hours, colored by predicted level, current hour outlined.
- Road details table: route, length, lanes, sensors, averages, peak hour and current level. Click a row for that road's 24-hour forecast chart.
- Alerts feed (predicted HIGH/SEVERE now, plus slow-speed roads), sensor-type doughnut, and a recent-readings table. Live panels refresh every 30 seconds.

**API endpoints**, if you want to call them directly or extend them:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/summary` | counts + last forecast timestamp |
| GET | `/api/roads` | all roads |
| GET | `/api/sensors?road_id=` | sensors for a road |
| POST | `/api/readings` | record a reading `{sensor_id, vehicle_count, avg_speed_kmh}` |
| GET | `/api/aggregate/volume` | avg volume per road, busiest first |
| GET | `/api/forecast/hotspots` | HIGH/SEVERE predicted rows |
| GET | `/api/forecast/road/<id>` | 24-hour forecast for one road |
| POST | `/api/forecast/run` | re-runs the regression job |
| GET | `/api/graph?hour=` | nodes/edges for the network diagram |
| GET | `/api/route?from=&to=&hour=` | least-congested path between two nodes |
| GET | `/api/kpis` | headline numbers: congestion index, avg speed, alerts, busiest road, peak hour |
| GET | `/api/alerts` | predicted HIGH/SEVERE roads this hour + slow-traffic roads |
| GET | `/api/roads/detail` | per-road geometry, sensors, averages, peak hour, current level |
| GET | `/api/analytics/hourly` | city-wide actual volume/speed per hour + forecast |
| GET | `/api/forecast/heatmap` | all roads x 24 hours of predicted level |
| GET | `/api/readings/recent?limit=` | latest sensor readings |
| GET | `/api/sensors/types` | sensor count by type |

> Note: with only 6 demo roads the network is close to a tree, so a couple of
> node pairs only have one physical route regardless of congestion — the
> congestion weighting still works, there's just nothing to re-route around
> for those specific pairs. Adding more roads (Day 5 of `PLAN.md`) gives the
> router real alternatives to pick between.

## Suggested demo flow for viva/evaluation

1. Run `generate_sample_data.py` live — show the schema getting populated.
2. Run `congestion_forecast.py` — point out the SQL aggregation, then the
   regression, then the forecast rows it writes back.
3. Run the Java app — option 2 (aggregated volume, straight SQL), then
   option 3 (hotspots, reading what Python wrote), then option 4 (Dijkstra
   route avoiding the hour's predicted congestion) to show ADSA + OOPJ tying
   into the same data.
4. Reference `db/er_model.md` and `docs/dmgt_relations.md` for the DBMS/DMGT
   theory questions.

See `PLAN.md` for a day-by-day breakdown to split across your team this week.
