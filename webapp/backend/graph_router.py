"""
Python port of java/src/graph/RoadNetworkGraph.java so the web dashboard can
find least-congested routes without needing the Java app running.
Same idea: roads are edges between intersection nodes, weighted by
length_km * congestion_multiplier(level for the chosen hour).
"""
import heapq
from collections import defaultdict

LEVEL_MULTIPLIER = {
    "SEVERE": 4.0,
    "HIGH": 2.5,
    "MODERATE": 1.5,
    "LOW": 1.0,
}


def multiplier_for_level(level: str) -> float:
    return LEVEL_MULTIPLIER.get(level, 1.0)


class RoadNetworkGraph:
    def __init__(self):
        self.adjacency = defaultdict(list)  # node -> [(neighbor, weight, road_dict)]

    def build(self, roads, congestion_multiplier: dict):
        """
        roads: list of dicts with road_id, road_name, start_node, end_node, length_km
        congestion_multiplier: {road_id: multiplier} for the hour being routed
        """
        self.adjacency.clear()
        for road in roads:
            mult = congestion_multiplier.get(road["road_id"], 1.0)
            weight = road["length_km"] * mult
            self.adjacency[road["start_node"]].append((road["end_node"], weight, road))
            self.adjacency[road["end_node"]].append((road["start_node"], weight, road))

    def shortest_path(self, start: str, end: str):
        """Dijkstra's algorithm. Returns (path_nodes, total_cost, edges_used) or None."""
        if start not in self.adjacency or end not in self.adjacency:
            return None

        dist = {node: float("inf") for node in self.adjacency}
        prev = {}
        prev_road = {}
        dist[start] = 0.0
        pq = [(0.0, start)]
        visited = set()

        while pq:
            d, node = heapq.heappop(pq)
            if node in visited:
                continue
            visited.add(node)
            if node == end:
                break
            for neighbor, weight, road in self.adjacency[node]:
                nd = d + weight
                if nd < dist[neighbor]:
                    dist[neighbor] = nd
                    prev[neighbor] = node
                    prev_road[neighbor] = road
                    heapq.heappush(pq, (nd, neighbor))

        if dist[end] == float("inf"):
            return None

        path = [end]
        edges = []
        node = end
        while node != start:
            edges.append(prev_road[node])
            node = prev[node]
            path.append(node)
        path.reverse()
        edges.reverse()
        return path, dist[end], edges
