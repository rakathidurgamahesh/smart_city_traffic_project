package model;

/** Row written by the Python regression job, read by the Java dashboard. */
public class CongestionForecast {
    private final int roadId;
    private final String roadName; // joined in for display convenience
    private final int hourOfDay;
    private final double predictedVolume;
    private final String congestionLevel;

    public CongestionForecast(int roadId, String roadName, int hourOfDay,
                               double predictedVolume, String congestionLevel) {
        this.roadId = roadId;
        this.roadName = roadName;
        this.hourOfDay = hourOfDay;
        this.predictedVolume = predictedVolume;
        this.congestionLevel = congestionLevel;
    }

    public int getRoadId() { return roadId; }
    public String getRoadName() { return roadName; }
    public int getHourOfDay() { return hourOfDay; }
    public double getPredictedVolume() { return predictedVolume; }
    public String getCongestionLevel() { return congestionLevel; }

    @Override
    public String toString() {
        return String.format("%-22s %02d:00  vol=%-7.1f level=%s",
                roadName, hourOfDay, predictedVolume, congestionLevel);
    }
}
