package dao;

import model.Sensor;

import java.sql.*;
import java.util.ArrayList;
import java.util.List;

public class SensorDAO {

    public List<Sensor> findByRoad(int roadId) throws SQLException {
        String sql = "SELECT sensor_id, road_id, location_desc, sensor_type FROM Sensor WHERE road_id = ?";
        List<Sensor> sensors = new ArrayList<>();
        try (Connection conn = DatabaseConnection.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setInt(1, roadId);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    sensors.add(new Sensor(
                        rs.getInt("sensor_id"),
                        rs.getInt("road_id"),
                        rs.getString("location_desc"),
                        rs.getString("sensor_type")
                    ));
                }
            }
        }
        return sensors;
    }

    public int insert(Sensor sensor) throws SQLException {
        String sql = "INSERT INTO Sensor (road_id, location_desc, sensor_type) VALUES (?, ?, ?)";
        try (Connection conn = DatabaseConnection.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            ps.setInt(1, sensor.getRoadId());
            ps.setString(2, sensor.getLocationDesc());
            ps.setString(3, sensor.getSensorType());
            ps.executeUpdate();
            try (ResultSet keys = ps.getGeneratedKeys()) {
                return keys.next() ? keys.getInt(1) : -1;
            }
        }
    }
}
