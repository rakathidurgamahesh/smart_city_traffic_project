package dao;

import model.Road;

import java.sql.*;
import java.util.ArrayList;
import java.util.List;

public class RoadDAO {

    public List<Road> findAll() throws SQLException {
        String sql = "SELECT road_id, road_name, start_node, end_node, length_km, lane_count FROM Road";
        List<Road> roads = new ArrayList<>();
        try (Connection conn = DatabaseConnection.getConnection();
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(sql)) {
            while (rs.next()) {
                roads.add(mapRow(rs));
            }
        }
        return roads;
    }

    public Road findById(int roadId) throws SQLException {
        String sql = "SELECT road_id, road_name, start_node, end_node, length_km, lane_count " +
                     "FROM Road WHERE road_id = ?";
        try (Connection conn = DatabaseConnection.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setInt(1, roadId);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? mapRow(rs) : null;
            }
        }
    }

    private Road mapRow(ResultSet rs) throws SQLException {
        return new Road(
            rs.getInt("road_id"),
            rs.getString("road_name"),
            rs.getString("start_node"),
            rs.getString("end_node"),
            rs.getDouble("length_km"),
            rs.getInt("lane_count")
        );
    }
}
