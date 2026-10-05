package graph;

import model.Road;

import java.util.*;

/**
 * ADSA Unit 2: the road network modeled as a weighted, undirected graph.
 * Vertices = intersection nodes (Road.start_node / Road.end_node).
 * Edges    = roads, weighted by an "effective cost" that combines physical
 *            length with predicted congestion, so Dijkstra naturally routes
 *            around predicted hotspots instead of just taking the shortest
 *            physical path.
 */
public class RoadNetworkGraph {

    /** One directed traversal option out of a node. */
    public static class Edge {
        public final String to;
        public final Road road;
        public final double weight;

        Edge(String to, Road road, double weight) {
            this.to = to;
            this.road = road;
            this.weight = weight;
        }
    }

    private final Map<String, List<Edge>> adjacency = new HashMap<>();

    /**
     * @param congestionMultiplier maps road_id -> a cost multiplier for its
     *                             currently predicted congestion (e.g. LOW=1.0,
     *                             MODERATE=1.5, HIGH=2.5, SEVERE=4.0). Pass an
     *                             empty map to route by raw distance only.
     */
    public void build(List<Road> roads, Map<Integer, Double> congestionMultiplier) {
        adjacency.clear();
        for (Road road : roads) {
            double multiplier = congestionMultiplier.getOrDefault(road.getRoadId(), 1.0);
            double weight = road.getLengthKm() * multiplier;

            adjacency.computeIfAbsent(road.getStartNode(), k -> new ArrayList<>())
                     .add(new Edge(road.getEndNode(), road, weight));
            adjacency.computeIfAbsent(road.getEndNode(), k -> new ArrayList<>())
                     .add(new Edge(road.getStartNode(), road, weight));
        }
    }

    public static double multiplierForLevel(String congestionLevel) {
        switch (congestionLevel) {
            case "SEVERE":  return 4.0;
            case "HIGH":    return 2.5;
            case "MODERATE":return 1.5;
            default:        return 1.0; // LOW or unknown
        }
    }

    /** Result of a route query: the ordered path and its total effective cost. */
    public static class RouteResult {
        public final List<String> path;
        public final double totalCost;
        public RouteResult(List<String> path, double totalCost) {
            this.path = path;
            this.totalCost = totalCost;
        }
    }

    /**
     * Dijkstra's algorithm — finds the lowest-cost path between two
     * intersection nodes using whatever weights build() was given
     * (plain distance, or congestion-adjusted distance).
     */
    public RouteResult shortestPath(String from, String to) {
        Map<String, Double> dist = new HashMap<>();
        Map<String, String> prev = new HashMap<>();
        PriorityQueue<String> pq = new PriorityQueue<>(Comparator.comparingDouble(dist::get));

        for (String node : adjacency.keySet()) {
            dist.put(node, Double.POSITIVE_INFINITY);
        }
        if (!dist.containsKey(from) || !dist.containsKey(to)) {
            return null; // unknown node
        }
        dist.put(from, 0.0);
        pq.add(from);

        Set<String> visited = new HashSet<>();
        while (!pq.isEmpty()) {
            String current = pq.poll();
            if (!visited.add(current)) continue;
            if (current.equals(to)) break;

            for (Edge edge : adjacency.getOrDefault(current, Collections.emptyList())) {
                double newDist = dist.get(current) + edge.weight;
                if (newDist < dist.get(edge.to)) {
                    dist.put(edge.to, newDist);
                    prev.put(edge.to, current);
                    pq.add(edge.to);
                }
            }
        }

        if (dist.get(to) == Double.POSITIVE_INFINITY) {
            return null; // no path
        }

        LinkedList<String> path = new LinkedList<>();
        for (String at = to; at != null; at = prev.get(at)) {
            path.addFirst(at);
            if (at.equals(from)) break;
        }
        return new RouteResult(path, dist.get(to));
    }
}
