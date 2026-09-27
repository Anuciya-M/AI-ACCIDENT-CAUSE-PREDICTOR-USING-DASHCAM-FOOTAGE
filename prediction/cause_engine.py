def find_cause(detections, motion_score, lane_present, track_info=None, avg_distance=100.0):
    # Check track_info for pedestrians (detections is a list of tuples from YOLO)
    if track_info:
        for track_id, info in track_info.items():
            if info.get("label") == "person":
                return "🚨 PEDESTRIAN COLLISION RISK"
    
    # Vehicle too close - ACCIDENT DETECTION
    if avg_distance < 30:  # Very close = immediate danger
        return "🚨 IMMINENT COLLISION - Vehicle too close!"
    elif avg_distance < 50:  # Close = high risk
        return "⚠️ COLLISION RISK - Vehicle approaching fast!"

    # Sudden braking or rapid motion
    if motion_score > 2.0:
        return "⚠️ SUDDEN DECELERATION - Emergency braking detected"
    elif motion_score > 1.0:
        return "⚠️ RAPID MOVEMENT - Sudden direction change"

    # Lane drift
    if not lane_present:
        return "⚠️ LANE DEPARTURE - Vehicle drifting"

    # Normal
    return "Normal driving conditions"