package app;

import dao.ForecastDAO;
import dao.ReadingDAO;
import dao.RoadDAO;
import dao.SensorDAO;
import graph.RoadNetworkGraph;
import model.CongestionForecast;
import model.Reading;
import model.Road;
import model.Sensor;

import java.sql.SQLException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Scanner;

/**
 * OOPJ: the traffic-monitoring console app.
 * Menu-driven so it can be demoed live: record readings, view aggregated
 * volume (DBMS), view predicted hotspots (from the Python forecast job),
 * and query the least-congested route between two intersections (ADSA).
 */
public class TrafficMonitorApp {

    private static final RoadDAO roadDAO = new RoadDAO();
    private static final SensorDAO sensorDAO = new SensorDAO();
    private static final ReadingDAO readingDAO = new ReadingDAO();
    private static final ForecastDAO forecastDAO = new ForecastDAO();
    private static final DateTimeFormatter TS_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        boolean running = true;

        System.out.println("=== Smart City Traffic Monitor ===");
        while (running) {
            printMenu();
            String choice = scanner.nextLine().trim();
            try {
                switch (choice) {
                    case "1": recordReading(scanner); break;
                    case "2": showAggregatedVolume(); break;
                    case "3": showHotspots(); break;
                    case "4": findRoute(scanner); break;
                    case "0": running = false; break;
                    default: System.out.println("Not a valid option.\n");
                }
            } catch (SQLException e) {
                System.out.println("Database error: " + e.getMessage());
                System.out.println("(Is data/traffic.db built? Run python/generate_sample_data.py first.)\n");
            }
        }
        System.out.println("Goodbye.");
        scanner.close();
    }

    private static void printMenu() {
        System.out.println("1) Record a sensor reading");
        System.out.println("2) View average traffic volume per road");
        System.out.println("3) View predicted hotspots");
        System.out.println("4) Find least-congested route between two intersections");
        System.out.println("0) Exit");
        System.out.print("> ");
    }

    private static void recordReading(Scanner scanner) throws SQLException {
        List<Road> roads = roadDAO.findAll();
        if (roads.isEmpty()) {
            System.out.println("No roads found. Seed the DB first (python/generate_sample_data.py).\n");
            return;
        }
        System.out.println("Roads:");
        roads.forEach(r -> System.out.println("  " + r));

        System.out.print("Enter road_id: ");
        int roadId = Integer.parseInt(scanner.nextLine().trim());

        List<Sensor> sensors = sensorDAO.findByRoad(roadId);
        if (sensors.isEmpty()) {
            System.out.println("That road has no sensors yet.\n");
            return;
        }
        System.out.println("Sensors on this road:");
        sensors.forEach(s -> System.out.println("  " + s));

        System.out.print("Enter sensor_id: ");
        int sensorId = Integer.parseInt(scanner.nextLine().trim());

        System.out.print("Vehicle count: ");
        int vehicleCount = Integer.parseInt(scanner.nextLine().trim());

        System.out.print("Average speed (km/h): ");
        double avgSpeed = Double.parseDouble(scanner.nextLine().trim());

        String now = LocalDateTime.now().format(TS_FORMAT);
        int newId = readingDAO.insert(new Reading(sensorId, now, vehicleCount, avgSpeed));
        System.out.println("Recorded reading #" + newId + " at " + now + "\n");
    }

    private static void showAggregatedVolume() throws SQLException {
        Map<String, Double> volumes = readingDAO.aggregateVolumeByRoad();
        if (volumes.isEmpty()) {
            System.out.println("No readings yet.\n");
            return;
        }
        System.out.println("\nAverage vehicle volume per road (busiest first):");
        volumes.forEach((road, vol) -> System.out.printf("  %-22s %.1f veh/reading%n", road, vol));
        System.out.println();
    }

    private static void showHotspots() throws SQLException {
        List<CongestionForecast> hotspots = forecastDAO.findHotspots();
        if (hotspots.isEmpty()) {
            System.out.println("No forecast data yet. Run python/congestion_forecast.py first.\n");
            return;
        }
        System.out.println("\nPredicted hotspots (HIGH/SEVERE), busiest first:");
        hotspots.forEach(f -> System.out.println("  " + f));
        System.out.println();
    }

    private static void findRoute(Scanner scanner) throws SQLException {
        List<Road> roads = roadDAO.findAll();
        List<CongestionForecast> hotspots = forecastDAO.findHotspots();

        System.out.print("At which hour (0-23) do you want to route for? ");
        int hour = Integer.parseInt(scanner.nextLine().trim());

        // Build road_id -> congestion level for the chosen hour (from all forecast rows, not just hotspots)
        Map<Integer, Double> congestionMultiplier = new HashMap<>();
        for (Road road : roads) {
            List<CongestionForecast> roadForecast = forecastDAO.findByRoad(road.getRoadId());
            roadForecast.stream()
                .filter(f -> f.getHourOfDay() == hour)
                .findFirst()
                .ifPresent(f -> congestionMultiplier.put(
                    road.getRoadId(), RoadNetworkGraph.multiplierForLevel(f.getCongestionLevel())));
        }

        RoadNetworkGraph graph = new RoadNetworkGraph();
        graph.build(roads, congestionMultiplier);

        System.out.print("From intersection node (e.g. N1): ");
        String from = scanner.nextLine().trim();
        System.out.print("To intersection node (e.g. N5): ");
        String to = scanner.nextLine().trim();

        RoadNetworkGraph.RouteResult result = graph.shortestPath(from, to);
        if (result == null) {
            System.out.println("No route found between " + from + " and " + to + ".\n");
            return;
        }
        System.out.println("Least-congested route at " + hour + ":00 -> " + String.join(" -> ", result.path));
        System.out.printf("Effective cost (distance x congestion): %.2f%n%n", result.totalCost);
    }
}
