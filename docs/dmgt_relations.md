# DMGT Unit 2 — Relations, mapped onto the schema

A relational database table *is* a mathematical relation, so this is mostly about
naming what you already built in `schema.sql` in DMGT terms for your report/viva.

## Reading as a relation
`Reading ⊆ Sensor_ID × Timestamp × VehicleCount × AvgSpeed`

- It's a subset of the Cartesian product of the attribute domains — not every
  combination exists, only the ones actually recorded.
- **Functional dependency**: `reading_id → {sensor_id, ts, vehicle_count, avg_speed_kmh}`
  (the key determines every other attribute — this is what makes it 3NF).

## Road–Sensor as a relation
`Installed_On ⊆ Road × Sensor`, restricted to a **function** from Sensor to Road
(each sensor belongs to exactly one road, but a road maps to many sensors) —
i.e. `road_id: Sensor → Road` is a many-to-one function, not a general relation.

## Road network as a graph (ties into ADSA)
The `Road` table's `(start_node, end_node)` pair is literally an edge in a graph
`G = (V, E)` where `V` = set of intersections and `E` = set of roads. This is the
same data used by `RoadNetworkGraph.java` for shortest/least-congested-path
queries — one relation, two subjects, no duplicate modeling effort. Worth a line
in your report: *"the Road relation and the ADSA graph are the same underlying
structure viewed two ways."*

## Composition example
`hotspot_hour(r) = { h | (r, h) ∈ CongestionForecast ∧ congestion_level(r,h) ∈ {HIGH, SEVERE} }`
— i.e. the set of hours where a road is predicted congested is a *selection*
(relational algebra σ) over `CongestionForecast`, which is exactly the SQL query
in `schema.sql` (#3) and exactly what `DashboardService.getHotspots()` in the
Java app returns. Good one-liner to drop in the viva if asked to connect DMGT
to the implementation.
