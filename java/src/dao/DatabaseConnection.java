package dao;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

/**
 * Single point of JDBC connection setup.
 * Points at the same SQLite file the Python job reads/writes, so both
 * languages share one source of truth (data/traffic.db).
 *
 * Requires the sqlite-jdbc driver jar on the classpath — see java/README.md.
 */
public final class DatabaseConnection {

    // Adjust this path if you run the jar from a different working directory.
    private static final String DB_PATH = "../data/traffic.db";
    private static final String URL = "jdbc:sqlite:" + DB_PATH;

    private DatabaseConnection() { }

    public static Connection getConnection() throws SQLException {
        try {
            Class.forName("org.sqlite.JDBC");
        } catch (ClassNotFoundException e) {
            throw new SQLException(
                "sqlite-jdbc driver not found on classpath. See java/README.md for setup.", e);
        }
        Connection conn = DriverManager.getConnection(URL);
        // Enforce FK constraints the same way schema.sql expects
        conn.createStatement().execute("PRAGMA foreign_keys = ON;");
        return conn;
    }
}
