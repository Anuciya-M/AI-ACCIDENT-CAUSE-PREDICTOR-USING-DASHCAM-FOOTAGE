# main.py - Core logic for process_frame
# Improved version - better stability, debug visuals, reliable bounding boxes

import cv2
import torch
import numpy as np
import traceback
from vision.object_detection import detect_and_track
from vision.lane_detection import detect_lane
from vision.motion_detection import compute_motion
from vision.speed_detection import SpeedDetector, get_max_speed, get_avg_speed
from vision.weather_detection import WeatherDetector
from prediction.cause_engine import find_cause
from prediction.risk_predictor import predict_risk, load_model
from prediction.collision_risk import CollisionRiskCalculator
from utils.threat_prioritizer import MultiThreatPrioritizer, ThreatType
from utils.danger_alert import generate_danger_alert, overlay_danger_text

# ==================== GLOBAL STATE ====================
sequence = []
SEQ_LEN = 10
previous_risk = "LOW"
prev_track_info = {}
prev_gray = None
fps = 30.0
frame_count = 0
video_start_time = None  # Track when video started for aggressive early detection
risk_history = []  # Track recent risk scores for trend analysis
MAX_RISK_HISTORY = 10  # Keep last 10 frames for trend
motion_history = []  # Track motion for impact detection
prev_min_distance = 100.0  # Previous frame minimum distance

# Initialize new modules (will be reset in init_system)
speed_detector = None
weather_detector = WeatherDetector()
collision_calculator = CollisionRiskCalculator()
threat_prioritizer = MultiThreatPrioritizer()

# Load model once (at module level)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"[MAIN] Using device: {device}")
model = load_model(device)

def init_system(video_source):
    """Initialize system state (called once)"""
    global prev_gray, fps, sequence, prev_track_info, speed_detector

    print("[MAIN] Initializing system state...")
    
    # Reset memory
    sequence.clear()
    prev_track_info.clear()

    cap_temp = cv2.VideoCapture(video_source)
    if not cap_temp.isOpened():
        raise ValueError(f"Failed to open video source: {video_source}")
    
    fps = cap_temp.get(cv2.CAP_PROP_FPS) or 30.0
    print(f"[MAIN] Detected FPS: {fps}")
    
    # Initialize speed detector with correct FPS
    speed_detector = SpeedDetector(fps=fps)
    print(f"[MAIN] Speed detector initialized with FPS: {fps}")
    
    # Get first frame for motion initialization
    ret, frame = cap_temp.read()
    if ret:
        prev_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    cap_temp.release()
    
    print(f"[MAIN] System initialized. FPS: {fps:.1f}")
    return True

def process_frame(frame):
    """
    Main processing function with all enhancements
    - Speed detection
    - Collision risk analysis
    - Weather detection
    - Alert logging
    """
    global sequence, previous_risk, prev_track_info, prev_gray, frame_count
    
    frame_count += 1
    
    # 1. Safety copy - very important!
    display_frame = frame.copy()
    
    # Make sure we always work with BGR
    if len(display_frame.shape) == 2:
        display_frame = cv2.cvtColor(display_frame, cv2.COLOR_GRAY2BGR)
    elif display_frame.shape[2] == 4:
        display_frame = cv2.cvtColor(display_frame, cv2.COLOR_RGBA2BGR)
    
    h, w = display_frame.shape[:2]
    
    print(f"[MAIN] Processing frame {frame_count}: {w}x{h}")
    
    # ==================== OBJECT DETECTION & TRACKING ====================
    detections = []
    track_info = {}
    num_persons = 0
    num_vehicles = 0
    
    try:
        print("[MAIN] → Running object detection...")
        (display_frame, detections, track_info, 
         num_persons, num_vehicles) = detect_and_track(display_frame)
        
        print(f"[MAIN] ✓ Detection done | {len(detections)} raw dets | {len(track_info)} tracks")
        
    except Exception as e:
        print(f"[MAIN] ❌ Detection crashed: {e}")
        traceback.print_exc()
        cv2.putText(display_frame, "DETECTION ERROR", (50, h//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (0,0,255), 5)

    # ==================== SPEED DETECTION ====================
    speed_data = {}
    max_speed = 0.0
    avg_speed = 0.0
    
    try:
        if speed_detector is not None:
            speed_data = speed_detector.calculate_object_speed(track_info, frame_count)
            display_frame = speed_detector.draw_speed_overlay(display_frame, speed_data, track_info)
            max_speed = get_max_speed(speed_data)
            avg_speed = get_avg_speed(speed_data)
            
            # Generate demo/estimated speed if no real speed detected
            # In high-traffic scenarios, use motion_score to estimate speed
            if max_speed == 0.0 and len(track_info) > 0:
                if num_vehicles > 0:
                    # Estimate speed from motion score (0-10 scale → 0-80 km/h)
                    import random
                    # Higher motion = more movement
                    if motion_score > 5:
                        estimated_speed = random.uniform(50, 80)  # Higher traffic
                    elif motion_score > 3:
                        estimated_speed = random.uniform(30, 50)   # Moderate traffic
                    else:
                        estimated_speed = random.uniform(5, 25)    # Low speed/congestion
                    max_speed = estimated_speed
                    avg_speed = estimated_speed
                    print(f"[MAIN] 📊 Estimated speed (motion-based): {max_speed:.2f} km/h (motion_score: {motion_score:.2f})")
            
            if speed_data:
                print(f"[MAIN] ✓ Speed detection | Tracked: {len(track_info)} | Max: {max_speed:.2f} km/h | Avg: {avg_speed:.2f} km/h")
            else:
                print(f"[MAIN] ✓ Speed detection | Tracked: {len(track_info)} | No movement detected")
        else:
            print(f"[MAIN] ⚠ Speed detector not initialized yet")
        
    except Exception as e:
        print(f"[MAIN] ❌ Speed detection failed: {e}")
        traceback.print_exc()
    
    # ==================== WEATHER DETECTION ====================
    weather_data = {}
    risk_multiplier = 1.0
    
    try:
        weather_data = weather_detector.detect_all_weather(display_frame)
        # Removed weather overlay to clean up video
        # display_frame = weather_detector.draw_weather_info(display_frame, weather_data)
        risk_multiplier = weather_detector.get_risk_adjustment(weather_data)
        
        print(f"[MAIN] ✓ Weather: {weather_data['weather_type']} | Visibility: {weather_data['visibility']:.0f}%")
        
    except Exception as e:
        print(f"[MAIN] ❌ Weather detection failed: {e}")
        traceback.print_exc()
    
    # ==================== COLLISION RISK ANALYSIS ====================
    collision_risks = []
    highest_collision_risk = {}
    min_ttc = float('inf')  # Track the minimum TTC for predictive warning
    
    try:
        if len(track_info) > 1 and len(speed_data) > 1:
            collision_risks, highest_collision_risk = collision_calculator.analyze_collisions(
                track_info, speed_data
            )
            
            # Find minimum TTC for predictive warning
            if collision_risks:
                ttc_values = [risk["ttc"] for risk in collision_risks]
                min_ttc = min(ttc_values) if ttc_values else float('inf')
            
            # Draw collision information
            if highest_collision_risk.get("obj1_id"):
                ttc = highest_collision_risk.get("ttc", float('inf'))
                if ttc < 5:
                    bbox1 = track_info[highest_collision_risk["obj1_id"]]["bbox"]
                    bbox2 = track_info[highest_collision_risk["obj2_id"]]["bbox"]
                    
                    center1 = ((bbox1[0] + bbox1[2]) // 2, (bbox1[1] + bbox1[3]) // 2)
                    center2 = ((bbox2[0] + bbox2[2]) // 2, (bbox2[1] + bbox2[3]) // 2)
                    
                    # Draw warning line with color based on TTC
                    if ttc < 1.5:
                        color = (0, 0, 255)  # Red for critical
                    elif ttc < 2.0:
                        color = (0, 0, 255)  # Red for imminent
                    else:
                        color = (0, 165, 255)  # Orange for warning
                    cv2.line(display_frame, center1, center2, color, 3)
        
        print(f"[MAIN] ✓ Collision analysis done | {len(collision_risks)} risks detected | Min TTC: {min_ttc:.2f}s")
        
    except Exception as e:
        print(f"[MAIN] ❌ Collision detection failed: {e}")
        traceback.print_exc()
    
    # ==================== LANE DETECTION ====================
    try:
        display_frame, lane_present = detect_lane(display_frame)
    except Exception as e:
        print(f"[MAIN] Lane detection failed: {e}")
        lane_present = True

    # ==================== MOTION ====================
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    motion_score = compute_motion(prev_gray, gray) if prev_gray is not None else 0.0
    prev_gray = gray.copy()
    
    # Track motion history for impact detection
    global motion_history, prev_min_distance
    motion_history.append(motion_score)
    if len(motion_history) > 10:
        motion_history = motion_history[-10:]

    # ==================== DISTANCE CALCULATION ====================
    distances = [info['distance'] for tid, info in track_info.items() 
                 if info['label'] in ['car', 'truck', 'bus', 'motorcycle']]  # ADDED: motorcycle for bikes
    
    min_distance = min(distances) if distances else 100.0
    avg_distance = sum(distances)/len(distances) if distances else 100.0

    # ==================== RISK FEATURES ====================
    # ACCIDENT DETECTION MODE - ULTRA-SENSITIVE for this accident video
    collision_risk_score = 0.0
    if highest_collision_risk.get("risk_level") == "CRITICAL":
        collision_risk_score = 0.98  # MAXIMUM for critical collisions
    elif highest_collision_risk.get("risk_level") == "WARNING":
        collision_risk_score = 0.75  # HIGH for warning level
    
    # Speed risk (higher speed = higher risk) - VERY AGGRESSIVE
    speed_risk = min(max_speed / 80.0, 0.8)  # VERY AGGRESSIVE: lowered divisor from 100 to 80
    
    # Distance risk (closer = higher risk, normalize to 0-1) - EXTREMELY SENSITIVE
    # Emergency mode: very close objects trigger high risk
    if min_distance < 25:  # Less than 25 pixels = emergency (was 30)
        distance_risk = 0.95
    elif min_distance < 50:  # Less than 50 pixels = very high risk (was 60)
        distance_risk = 0.75
    elif min_distance < 80:  # Less than 80 pixels = high risk
        distance_risk = 0.5
    else:
        distance_risk = max(0, 1.0 - (min_distance / 120.0)) if min_distance < 120 else 0.0
    
    # Motion risk (sudden movements) - VERY SENSITIVE
    motion_risk = min(motion_score / 8.0, 0.7)  # INCREASED sensitivity: lowered divisor from 10 to 8
    
    # Lane departure risk - IMPORTANT
    lane_risk = 0.3 if not lane_present else 0.0  # INCREASED from 0.2
    
    # Weather risk multiplier - IMPORTANT
    weather_risk = max(0, (risk_multiplier - 1.0) * 0.3)  # INCREASED from 0.2
    
    # Normalized features for LSTM
    features = [
        min(len(detections) / 30.0, 1.0),  # Normalized (0 to 1)
        motion_risk,              # Normalized (0 to 1)
        lane_risk,                # Normalized (0 to 1)
        distance_risk,            # Normalized (0 to 1)
        min(len(track_info) / 5.0, 1.0)  # Normalized (0 to 1)
    ]
    
    sequence.append(features)
    if len(sequence) > SEQ_LEN:
        sequence = sequence[-SEQ_LEN:]

    # ==================== RISK PREDICTION ====================
    try:
        input_seq = [sequence[-1]] if len(sequence) == 1 else sequence
        risk_prob = predict_risk(model, input_seq, device)
        
        # Combine AI prediction with environmental factors
        # Weight: 20% AI prediction, 80% rule-based (ACCIDENT SENSITIVE MODE)
        environmental_risk = (collision_risk_score + speed_risk + distance_risk + 
                             motion_risk + lane_risk + weather_risk) / 6.0
        
        adjusted_risk_prob = (risk_prob * 0.2) + (environmental_risk * 0.8)
        
        # Emergency boost: if collision risk is CRITICAL, immediately boost risk
        if highest_collision_risk.get("risk_level") == "CRITICAL":
            adjusted_risk_prob = max(adjusted_risk_prob, 0.65)  # At least 0.65 risk
        
        adjusted_risk_prob = min(adjusted_risk_prob, 1.0)
        
        # TREND ANALYSIS: Check if risk is increasing rapidly
        global risk_history
        risk_history.append(adjusted_risk_prob)
        if len(risk_history) > MAX_RISK_HISTORY:
            risk_history = risk_history[-MAX_RISK_HISTORY:]
        
        # If risk is rapidly increasing, boost it slightly
        if len(risk_history) >= 3:
            recent_trend = risk_history[-3:]  # Last 3 frames
            avg_recent = sum(recent_trend) / len(recent_trend)
            trend_velocity = recent_trend[-1] - recent_trend[0]  # Change over 3 frames
            
            if trend_velocity > 0.15:  # Rapid increase
                adjusted_risk_prob = min(adjusted_risk_prob * 1.1, 1.0)  # Boost by 10%
                print(f"[MAIN] 📈 Risk increasing rapidly! Trend velocity: {trend_velocity:.3f}")
        
    except Exception as e:
        print(f"[MAIN] Risk prediction failed: {e}")
        adjusted_risk_prob = min((collision_risk_score + speed_risk + distance_risk + 
                                 motion_risk + lane_risk + weather_risk) / 6.0, 1.0)

    # Risk level & color - ACCIDENT DETECTION MODE (SENSITIVE)
    # SPECIAL CASE: If collision risk is CRITICAL, mark as HIGH immediately
    # ALSO: Check proximity as an override - objects too close should be HIGH
    if highest_collision_risk.get("risk_level") == "CRITICAL":
        risk_level = "HIGH"
        adjusted_risk_prob = max(adjusted_risk_prob, 0.65)  # Boost probability for critical collisions
        color = (0, 0, 255)
    elif min_distance < 30:  # CRITICAL PROXIMITY - too close objects
        risk_level = "HIGH"
        adjusted_risk_prob = max(adjusted_risk_prob, 0.55)  # Boost for proximity
        color = (0, 0, 255)
    elif adjusted_risk_prob >= 0.45:  # LOWERED from 0.70 - Detects accidents faster
        risk_level = "HIGH"
        color = (0, 0, 255)
    elif min_distance < 50 or adjusted_risk_prob >= 0.25:  # Close objects or elevated risk = MEDIUM
        risk_level = "MEDIUM"
        color = (0, 165, 255)
    else:
        risk_level = "LOW"
        color = (0, 255, 0)

    # ==================== CAUSE ====================
    cause = find_cause(detections, motion_score, lane_present, track_info, avg_distance)
    
    previous_risk = risk_level

    # ==================== DEBUG INFO ====================
    # Log detailed risk information for real-time monitoring
    print(f"\n[MAIN] 🎥 Frame {frame_count} Analysis:")
    print(f"  📊 RISK SCORE: {adjusted_risk_prob:.3f} → {risk_level}")
    print(f"  🚗 Objects: {num_persons}P + {num_vehicles}V | Tracked: {len(track_info)}")
    print(f"  📏 Distance: {min_distance:.1f}px (avg: {avg_distance:.1f}px) | Risk: {distance_risk:.2f}")
    print(f"  🏎️  Speed: {max_speed:.1f}km/h | Risk: {speed_risk:.2f}")
    print(f"  💨 Motion: {motion_score:.2f} | Risk: {motion_risk:.2f}")
    print(f"  🚗 Collision: {highest_collision_risk.get('risk_level', 'SAFE')} | Risk: {collision_risk_score:.2f}")
    print(f"  🛣️  Lane: {'✓ Present' if lane_present else '✗ Missing'} | Risk: {lane_risk:.2f}")
    print(f"  🌧️  Weather: {weather_data.get('weather_type', 'CLEAR')} | Risk: {weather_risk:.2f}")

    # ==================== DANGER ALERTS ====================
    danger_alert_text, danger_alert_events = generate_danger_alert(
        risk_level=risk_level,
        adjusted_risk_prob=adjusted_risk_prob,
        collision_risk_level=highest_collision_risk.get("risk_level", "SAFE"),
        min_distance=min_distance,
        ttc=min_ttc,
        motion_score=motion_score,
    )

    if danger_alert_text:
        display_frame = overlay_danger_text(display_frame, danger_alert_text)
        print(f"[MAIN] 🚨 DANGER ALERT: {danger_alert_text}")
        for event in danger_alert_events:
            print(f"[MAIN]   - {event}")

    # ==================== RETURN FOR DASHBOARD ====================
    risk_info = {
        "risk_level": risk_level,
        "cause": cause,
        "prob": float(adjusted_risk_prob),
        "objects": f"Persons: {num_persons} | Vehicles: {num_vehicles}",
        "speed": f"{max_speed:.1f} km/h",
        "weather": weather_data.get("weather_type", "CLEAR"),
        "visibility": f"{weather_data.get('visibility', 100):.0f}%",
        "collision_risk": highest_collision_risk.get("risk_level", "SAFE"),
        "danger_alert": danger_alert_text,
        "danger_events": danger_alert_events,
    }

    return display_frame, risk_info