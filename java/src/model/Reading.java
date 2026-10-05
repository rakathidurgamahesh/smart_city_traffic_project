package model;

public class Reading {
    private final int readingId;
    private final int sensorId;
    private final String timestamp;
    private final int vehicleCount;
    private final double avgSpeedKmh;

    public Reading(int readingId, int sensorId, String timestamp, int vehicleCount, double avgSpeedKmh) {
        this.readingId = readingId;
        this.sensorId = sensorId;
        this.timestamp = timestamp;
        this.vehicleCount = vehicleCount;
        this.avgSpeedKmh = avgSpeedKmh;
    }

    // Constructor for inserting a brand new reading (no id yet)
    public Reading(int sensorId, String timestamp, int vehicleCount, double avgSpeedKmh) {
        this(-1, sensorId, timestamp, vehicleCount, avgSpeedKmh);
    }

    public int getReadingId() { return readingId; }
    public int getSensorId() { return sensorId; }
    public String getTimestamp() { return timestamp; }
    public int getVehicleCount() { return vehicleCount; }
    public double getAvgSpeedKmh() { return avgSpeedKmh; }

    @Override
    public String toString() {
        return String.format("Reading[sensor=%d, %s, count=%d, speed=%.1fkm/h]",
                sensorId, timestamp, vehicleCount, avgSpeedKmh);
    }
}
