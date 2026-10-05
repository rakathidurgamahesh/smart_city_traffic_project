package model;

/** Mirrors the Road table. OOPJ: plain encapsulated data class. */
public class Road {
    private final int roadId;
    private final String roadName;
    private final String startNode;
    private final String endNode;
    private final double lengthKm;
    private final int laneCount;

    public Road(int roadId, String roadName, String startNode, String endNode,
                double lengthKm, int laneCount) {
        this.roadId = roadId;
        this.roadName = roadName;
        this.startNode = startNode;
        this.endNode = endNode;
        this.lengthKm = lengthKm;
        this.laneCount = laneCount;
    }

    public int getRoadId() { return roadId; }
    public String getRoadName() { return roadName; }
    public String getStartNode() { return startNode; }
    public String getEndNode() { return endNode; }
    public double getLengthKm() { return lengthKm; }
    public int getLaneCount() { return laneCount; }

    @Override
    public String toString() {
        return String.format("Road#%d[%s: %s -> %s, %.1fkm, %d lanes]",
                roadId, roadName, startNode, endNode, lengthKm, laneCount);
    }
}
