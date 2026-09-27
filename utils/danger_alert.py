import cv2


def generate_danger_alert(risk_level, adjusted_risk_prob, collision_risk_level, min_distance, ttc, motion_score):
    """Return highest-priority danger alert and list of active danger events."""
    alerts = []

    if collision_risk_level == "CRITICAL":
        alerts.append("IMMINENT COLLISION: BRAKE NOW")

    if ttc is not None and ttc < 2.0:
        alerts.append(f"TIME TO COLLISION: {ttc:.1f}s")
    elif ttc is not None and ttc < 5.0:
        alerts.append(f"POTENTIAL COLLISION SOON: {ttc:.1f}s")

    if adjusted_risk_prob >= 0.75:
        alerts.append("EXTREME RISK: TAKE ACTION")
    elif adjusted_risk_prob >= 0.45:
        alerts.append("HIGH RISK: EXERCISE CAUTION")

    if min_distance < 25:
        alerts.append("OBJECT TOO CLOSE: INCREASE DISTANCE")
    elif min_distance < 50:
        alerts.append("CLOSE PROXIMITY: SLOW DOWN")

    if motion_score > 8.0:
        alerts.append("UNSTABLE MOTION: HAZARD DETECTED")

    if not alerts:
        return "", []

    return alerts[0], alerts


def overlay_danger_text(frame, text):
    """Overlay danger text on the video frame."""
    if not text:
        return frame

    h, w = frame.shape[:2]
    y = 50
    cv2.rectangle(frame, (10, y-28), (w-10, y+10), (0,0,255), -1)
    cv2.putText(frame, text, (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
    return frame
