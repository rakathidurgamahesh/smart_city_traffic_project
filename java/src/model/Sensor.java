package model;

public class Sensor {
    private final int sensorId;
    private final int roadId;
    private final String locationDesc;
    private final String sensorType;

    public Sensor(int sensorId, int roadId, String locationDesc, String sensorType) {
        this.sensorId = sensorId;
        this.roadId = roadId;
        this.locationDesc = locationDesc;
        this.sensorType = sensorType;
    }

    public int getSensorId() { return sensorId; }
    public int getRoadId() { return roadId; }
    public String getLocationDesc() { return locationDesc; }
    public String getSensorType() { return sensorType; }

    @Override
    public String toString() {
        return String.format("Sensor#%d[road=%d, %s, %s]", sensorId, roadId, locationDesc, sensorType);
    }
}
