# 7-Day Plan — Smart City Traffic Sensor System

Assumes a team of 3-4. Adjust names to your actual team; the point is no one
is idle and nothing depends on a teammate finishing first (the schema is the
one shared contract, so lock it on day 1).

## Day 1 — Lock the schema, split work
- Everyone: read through `db/schema.sql` and `db/er_model.md`, agree on any
  changes to the schema **now** (adding a column later is fine; renaming
  tables after Day 2 is not — everything else depends on these names).
- Person A: start on Java model + DAO classes.
- Person B: start on the Python generator/regression scripts.
- Person C: start on the ADSA graph module + report write-up (ER model, DMGT
  relations doc).
- Run `python3 generate_sample_data.py` once so everyone has a `traffic.db`
  to develop against.

## Day 2-3 — Build in parallel
- Java: get `RoadDAO`, `SensorDAO`, `ReadingDAO`, `ForecastDAO` working
  against the seeded DB (start with `findAll`/`aggregateVolumeByRoad`, they're
  the easiest to sanity-check).
- Python: get `congestion_forecast.py` producing sane per-hour predictions —
  plot or print the hourly averages first to eyeball the double rush-hour
  hump before trusting the regression output.
- ADSA: get `RoadNetworkGraph` building from the `Road` table and returning a
  plausible shortest path with plain distance weights before adding the
  congestion multiplier.

## Day 4 — Integrate
- Wire `TrafficMonitorApp`'s menu to the DAOs (this repo already has a
  working version — treat it as a base to extend, not a black box: read
  through it together as a team).
- Confirm the full loop works: seed data → run forecast job → Java dashboard
  shows the same hotspots Python predicted → Java route-finder changes its
  answer when you pick a congested hour vs. a quiet hour.

## Day 5 — Extend / polish (pick 2-3, don't try all of them)
- Add a `RoadDAO.insert()` / simple "add a new road" flow so the dashboard
  isn't read-only.
- Add a second regression feature (e.g. day-of-week, not just hour-of-day) if
  your dataset covers multiple weeks.
- Add unit tests for `RoadNetworkGraph.shortestPath()` with a small hand-built
  graph (this is an easy, safe thing to demo working correctly in a viva).
- If you want a GUI beyond the console: a simple JavaFX or Swing table showing
  `ForecastDAO.findHotspots()` is a manageable stretch goal.

## Day 6 — Report + slides
- Report sections map directly to `README.md`'s subject-mapping table — pull
  the ER diagram from `er_model.md`, the relations discussion from
  `dmgt_relations.md`, and a code walkthrough of `RoadNetworkGraph.java` for
  the ADSA section.
- Screenshot the console dashboard output (aggregated volume, hotspots, and a
  route query) for the report/slides.

## Day 7 — Rehearse the demo + buffer
- Do a full dry run: fresh DB seed → forecast job → Java app, timed.
- Reserve this day as buffer for whatever broke in the dry run — something
  always does.
- Assign who answers which viva question by subject (DBMS/DMGT/ADSA/OOPJ/
  Python) so no one gets cornered on a part they didn't write.
