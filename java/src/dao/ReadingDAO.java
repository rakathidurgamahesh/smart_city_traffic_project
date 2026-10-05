package dao;

import model.Reading;

import java.sql.*;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class ReadingDAO {

    /** Records one new sensor reading. */
    public int insert(Reading reading) throws SQLException {
        String sql = "INSERT INTO Reading (sensor_id, ts, vehicle_count, avg_speed_kmh) VALUES (?, ?, ?, ?)";
        try (Connection conn = DatabaseConnection.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            ps.setInt(1, reading.getSensorId());
            ps.setString(2, reading.getTimestamp());
            ps.setInt(3, reading.getVehicleCount());
            ps.setDouble(4, reading.getAvgSpeedKmh());
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                return keys.next() ? keys.getInt(1) : -1;
            }
        }
    }

    public List<Reading> findBySensor(int sensorId, int limit) throws SQLException {
        String sql = "SELECT reading_id, sensor_id, ts, vehicle_count, avg_speed_kmh " +
                     "FROM Reading WHERE sensor_id = ? ORDER BY ts DESC LIMIT ?";
        List<Reading> readings = new ArrayList<>();
        try (Connection conn = DatabaseConnection.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setInt(1, sensorId);
            ps.setInt(2, limit);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    readings.add(new Reading(
                        rs.getInt("reading_id"),
                        rs.getInt("sensor_id"),
                        rs.getString("ts"),
                        rs.getInt("vehicle_count"),
                        rs.getDouble("avg_speed_kmh")
                    ));
                }
            }
        }
        return readings;
    }

    /**
     * DBMS Unit 2 aggregation: total & average vehicle volume per road,
     * joining Road -> Sensor -> Reading. Returned as roadName -> avgVolume,
     * ordered by traffic volume descending (busiest road first).
     */
    public Map<String, Double> aggregateVolumeByRoad() throws SQLException {
        String sql =
            "SELECT r.road_name, AVG(rd.vehicle_count) AS avg_volume " +
            "FROM Road r " +
            "JOIN Sensor s ON s.road_id = r.road_id " +
            "JOIN Reading rd ON rd.sensor_id = s.sensor_id " +
            "GROUP BY r.road_id " +
            "ORDER BY avg_volume DESC";

        Map<String, Double> result = new LinkedHashMap<>();
        try (Connection conn = DatabaseConnection.getConnection();
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(sql)) {
            while (rs.next()) {
                result.put(rs.getString("road_name"), rs.getDouble("avg_volume"));
            }
        }
        return result;
    }
}
