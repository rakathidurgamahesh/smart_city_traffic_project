package dao;

import model.CongestionForecast;

import java.sql.*;
import java.util.ArrayList;
import java.util.List;

public class ForecastDAO {

    /** All 24 hourly predictions for one road, ordered by hour. */
    public List<CongestionForecast> findByRoad(int roadId) throws SQLException {
        String sql =
            "SELECT r.road_id, r.road_name, cf.hour_of_day, cf.predicted_volume, cf.congestion_level " +
            "FROM congestion_forecast cf JOIN Road r ON r.road_id = cf.road_id " +
            "WHERE cf.road_id = ? ORDER BY cf.hour_of_day";
        return query(sql, roadId);
    }

    /** Predicted hotspots (HIGH/SEVERE) across all roads — feeds the dashboard's headline view. */
    public List<CongestionForecast> findHotspots() throws SQLException {
        String sql =
            "SELECT r.road_id, r.road_name, cf.hour_of_day, cf.predicted_volume, cf.congestion_level " +
            "FROM congestion_forecast cf JOIN Road r ON r.road_id = cf.road_id " +
            "WHERE cf.congestion_level IN ('HIGH', 'SEVERE') " +
            "ORDER BY cf.predicted_volume DESC";
        return query(sql, null);
    }

    private List<CongestionForecast> query(String sql, Integer roadIdParam) throws SQLException {
        List<CongestionForecast> forecasts = new ArrayList<>();
        try (Connection conn = DatabaseConnection.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            if (roadIdParam != null) {
                ps.setInt(1, roadIdParam);
            }
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    forecasts.add(new CongestionForecast(
                        rs.getInt("road_id"),
                        rs.getString("road_name"),
                        rs.getInt("hour_of_day"),
                        rs.getDouble("predicted_volume"),
                        rs.getString("congestion_level")
                    ));
                }
            }
        }
        return forecasts;
    }
}
