"""
Flask app for AI Accident Cause Predictor Dashboard
Fixed version with proper video streaming and dashboard updates
Updated: Removed frame skip for real-time play (add sleep for FPS control), force AI every frame if fast, fallback to raw video if slow.
Added: Video loop, extra debug overlays, frame copy safety, adjusted sleep for smoother streaming.
"""

from flask import Flask, render_template, Response, jsonify
import cv2
import threading
import time
import numpy as np
import traceback
from collections import deque
from datetime import datetime, timedelta

app = Flask(__name__)

# Global state
cap = None
process_frame_func = None
lock = threading.Lock()
system_ready = False
system_error = None
frames_generated = 0
total_frame_time = 0.0
frame_time_samples = 0

# Simple fallback for demo mode
def simple_process_frame(frame):
    """Fallback frame processor when AI is not available"""
    display_frame = frame.copy()
    cv2.putText(display_frame, "DEMO MODE - No AI", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
    
    return display_frame, {
        "risk_level": "LOW",
        "cause": "Demo Mode",
        "prob": 0.25,
        "objects": "Video Streaming Active",
        "speed": "0 km/h",
        "weather": "CLEAR",
        "visibility": "100%",
        "collision_risk": "SAFE"
    }

# Dashboard data with separate lock for thread safety
dashboard_lock = threading.Lock()
last_risk_level = "LOW"
last_alert_time = 0
alert_counter = 0  # Counter to generate unique alert IDs
alert_history = deque(maxlen=100)  # Keep last 100 alerts for statistics
high_risk_count = 0
medium_risk_count = 0
low_risk_count = 0
alerts_count_last_hour = 0
dashboard_data = {
    "risk_level": "INITIALIZING",
    "cause": "Loading AI models...",
    "prob": 0.0,
    "objects": "System starting...",
    "speed": "0 km/h",
    "weather": "CLEAR",
    "visibility": "100%",
    "collision_risk": "SAFE",
    "new_alert": None,
    "frames_processed": 0,
    "avg_latency_ms": 0.0,
    "stream_fps": 0.0,
    "system_load": "0%",
    "device": "CPU",
    "gpu_available": False,
    "stats_last_hour": {
        "total_alerts": 0,
        "high_risk_events": 0,
        "medium_risk_events": 0,
        "low_risk_events": 0
    },
    "timestamp": time.time()
}

VIDEO_PATH = r"C:\Users\ANU M\Desktop\AI ACCIDENT CAUSE PREDICTOR USING DASHCAM FOOTAGE\nexar_dataset\train\positive\00007.mp4"  # Update this path to your video file
def init_system():
    """Initialize AI models in background"""
    global cap, process_frame_func, system_ready, system_error
    
    try:
        # Initialize video capture FIRST - this is critical
        print("\n⏳ INITIALIZING VIDEO STREAM...")
        cap = cv2.VideoCapture(VIDEO_PATH)
        if not cap.isOpened():
            raise ValueError(f"Failed to open video: {VIDEO_PATH}")
        print(f"✓ Video stream ready: {VIDEO_PATH}\n")
        
        # Mark system as ready immediately with just video
        system_ready = True
        
        # Now try to load AI models in background
        print("⏳ LOADING AI MODELS IN BACKGROUND...")
        print("   This may take 30-60 seconds...\n")
        
        try:
            print("[INIT] Loading YOLO model...")
            from main import process_frame
            
            # Verify the function exists
            if callable(process_frame):
                process_frame_func = process_frame
                print("✓ AI models loaded successfully!")
                
                # Update dashboard to show we're ready
                with dashboard_lock:
                    dashboard_data.update({
                        "risk_level": "LOW",
                        "cause": "System ready - analyzing...",
                        "prob": 0.0,
                        "objects": "Waiting for detections...",
                        "timestamp": time.time()
                    })
                print("✓ Dashboard updated - system ready!")
            else:
                raise ValueError("process_frame is not callable")
            
        except Exception as e:
            print(f"\n❌ AI load failed: {e}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            print("\n⚠ Running in video-only mode (no AI analysis)\n")
            
            # CRITICAL FIX: Set to simple_process_frame immediately
            process_frame_func = simple_process_frame
            
            # Update dashboard for fallback mode
            with dashboard_lock:
                dashboard_data.update({
                    "risk_level": "DEMO",
                    "cause": "Running in demo mode (no AI)",
                    "prob": 0.25,
                    "objects": "Demo Mode Active",
                    "timestamp": time.time()
                })
            
    except Exception as e:
        system_error = str(e)
        print(f"❌ System init failed: {e}")
        traceback.print_exc()

def gen_frames():
    """Generator for MJPEG stream - fixed with loop, copy, debug overlay"""
    global cap, frames_generated, process_frame_func, last_risk_level, last_alert_time, total_frame_time, frame_time_samples, alert_counter, alert_history, high_risk_count, medium_risk_count, low_risk_count, alerts_count_last_hour
    
    if cap is None:
        print("[APP] ❌ Video capture not initialized!")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_delay = max(0.01, 1.0 / fps)  # For real-time playback
    
    print("[APP] 🎬 Starting video stream with FPS:", fps)
    
    while True:
        frame_start = time.time()
        try:
            with lock:
                ret, frame = cap.read()
                if not ret:
                    # Loop video
                    print("[APP] 🔄 Looping video...")
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
            
            # Safety copy
            frame = frame.copy()
            
            # Resize for consistent streaming (640x480)
            frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_LINEAR)
            
            # Process frame if func available
            if process_frame_func:
                try:
                    frame, risk_info = process_frame_func(frame)
                    
                    # Generate alert based on risk level
                    current_risk = str(risk_info.get("risk_level", "LOW"))
                    current_cause = str(risk_info.get("cause", "Normal"))
                    new_alert = None
                    current_time = time.time()
                    
                    # Track statistics
                    if current_risk == "HIGH":
                        high_risk_count += 1
                    elif current_risk == "MEDIUM":
                        medium_risk_count += 1
                    else:
                        low_risk_count += 1
                    
                    # Generate alert every 3 seconds when risk is HIGH or MEDIUM
                    if current_risk in ["HIGH", "MEDIUM"] and (current_time - last_alert_time > 3):
                        alert_counter += 1  # Increment counter to make each alert unique
                        new_alert = {
                            "message": f"⚠️ {current_risk}: {current_cause}",
                            "id": alert_counter,  # Unique ID for each alert
                            "timestamp": current_time,
                            "risk_level": current_risk
                        }
                        alert_history.append({"timestamp": current_time, "risk_level": current_risk, "cause": current_cause})
                        alerts_count_last_hour += 1
                        last_alert_time = current_time
                    
                    # Calculate last hour statistics
                    one_hour_ago = current_time - 3600
                    recent_alerts = [a for a in alert_history if a["timestamp"] > one_hour_ago]
                    high_alerts = sum(1 for a in recent_alerts if a["risk_level"] == "HIGH")
                    medium_alerts = sum(1 for a in recent_alerts if a["risk_level"] == "MEDIUM")
                    
                    # Update dashboard data
                    with dashboard_lock:
                        dashboard_data.update({
                            "risk_level": current_risk,
                            "cause": current_cause,
                            "prob": float(risk_info.get("prob", 0.0)),
                            "objects": str(risk_info.get("objects", "No detections")),
                            "speed": str(risk_info.get("speed", "0 km/h")),
                            "weather": str(risk_info.get("weather", "CLEAR")),
                            "visibility": str(risk_info.get("visibility", "100%")),
                            "collision_risk": str(risk_info.get("collision_risk", "SAFE")),
                            "new_alert": new_alert,
                            "stats_last_hour": {
                                "total_alerts": len(recent_alerts),
                                "high_risk_events": high_alerts,
                                "medium_risk_events": medium_alerts,
                                "low_risk_events": len(recent_alerts) - high_alerts - medium_alerts
                            },
                            "timestamp": current_time
                        })
                    
                    last_risk_level = current_risk
                    
                except Exception as ai_error:
                    print(f"[APP] ⚠ AI processing error: {ai_error}, using fallback")
                    frame, risk_info = simple_process_frame(frame)
                    with dashboard_lock:
                        dashboard_data.update({
                            "risk_level": str(risk_info.get("risk_level", "LOW")),
                            "cause": str(risk_info.get("cause", "Error")),
                            "prob": float(risk_info.get("prob", 0.0)),
                            "objects": str(risk_info.get("objects", "Demo")),
                            "speed": str(risk_info.get("speed", "0 km/h")),
                            "weather": str(risk_info.get("weather", "CLEAR")),
                            "visibility": str(risk_info.get("visibility", "100%")),
                            "collision_risk": str(risk_info.get("collision_risk", "SAFE")),
                            "timestamp": time.time()
                        })
            else:
                # Fallback when AI not ready yet
                frame, risk_info = simple_process_frame(frame)
                
                # Update with fallback data
                with dashboard_lock:
                    dashboard_data.update({
                        "risk_level": str(risk_info.get("risk_level", "LOW")),
                        "cause": str(risk_info.get("cause", "Demo")),
                        "prob": float(risk_info.get("prob", 0.0)),
                        "objects": str(risk_info.get("objects", "Demo")),
                        "speed": str(risk_info.get("speed", "0 km/h")),
                        "weather": str(risk_info.get("weather", "CLEAR")),
                        "visibility": str(risk_info.get("visibility", "100%")),
                        "collision_risk": str(risk_info.get("collision_risk", "SAFE")),
                        "new_alert": None,
                        "timestamp": time.time()
                    })
            
            # Encode frame with quality control
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_time = time.time() - frame_start
            total_frame_time += frame_time
            frame_time_samples += 1
            avg_latency_ms = (total_frame_time / frame_time_samples) * 1000
            stream_fps = (1.0 / frame_time) if frame_time > 0 else fps

            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n' + 
                       frame_bytes + b'\r\n')
                frames_generated += 1

                # Update live stats each frame
                with dashboard_lock:
                    dashboard_data.update({
                        "frames_processed": frames_generated,
                        "avg_latency_ms": round(avg_latency_ms, 2),
                        "stream_fps": round(stream_fps, 2),
                        "system_load": f"{min(99, int((frame_time / frame_delay) * 100))}%"
                    })

                if frames_generated % 30 == 0:
                    print(f"[APP] 📺 Streamed {frames_generated} frames | Avg latency {avg_latency_ms:.1f}ms | Stream FPS {stream_fps:.1f}")
            else:
                print(f"[APP] ❌ Encoding failed!")
            
        except Exception as e:
            print(f"[APP] ❌ Processing error: {e}")
            traceback.print_exc()
            continue
        
        # Sleep for FPS control (skip sleep when processing already exceeded frame time)
        sleep_time = max(0.0, frame_delay - (time.time() - frame_start))
        time.sleep(sleep_time)

# Start background init
init_thread = threading.Thread(target=init_system, daemon=True)
init_thread.start()

# ============== FLASK ROUTES ==============

@app.route('/')
def index():
    """Serve dashboard HTML"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    status_text = "READY" if (system_ready and cap is not None) else "INITIALIZING"
    if system_error:
        status_text = "ERROR"
    
    with dashboard_lock:
        o = {
            "ready": system_ready,
            "error": system_error,
            "status": status_text,
            "frames": frames_generated,
            "ai_ready": process_frame_func is not None,
            "frames_processed": dashboard_data.get("frames_processed", frames_generated),
            "avg_latency_ms": dashboard_data.get("avg_latency_ms", 0.0),
            "stream_fps": dashboard_data.get("stream_fps", 0.0),
            "system_load": dashboard_data.get("system_load", "0%")
        }
    return jsonify(o)

@app.route('/video_feed')
def video_feed():
    """Stream MJPEG video with proper headers"""
    return Response(gen_frames(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame',
                    headers={'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
                             'Cache-Control': 'no-cache, no-store, must-revalidate',
                             'Pragma': 'no-cache',
                             'Expires': '0'})

@app.route('/data')
def get_data():
    """Get current dashboard data"""
    with dashboard_lock:
        # Return a copy to avoid modifications
        data = dict(dashboard_data)
    return jsonify(data)

@app.route('/statistics')
def get_statistics():
    """Get statistics endpoint for legacy frontend"""
    with dashboard_lock:
        stats = dashboard_data.get("stats_last_hour", {})
        return jsonify({
            "critical": stats.get("high_risk_events", 0),
            "warning": stats.get("medium_risk_events", 0),
            "total": stats.get("total_alerts", 0)
        })

@app.route('/alerts')
def get_alerts():
    """Get recent alerts endpoint for legacy frontend"""
    with dashboard_lock:
        # Convert alert history to format expected by frontend
        recent_alerts = []
        # Process alerts in reverse order to show most recent first
        for alert in list(alert_history)[-10:]:
            level = alert.get("risk_level", "LOW")
            level_display = "CRITICAL" if level == "HIGH" else "WARNING" if level == "MEDIUM" else "INFO"
            
            recent_alerts.append({
                "level": level_display,
                "type": "ACCIDENT",
                "cause": alert.get("cause", "Unknown"),
                "message": f"{level_display}: {alert.get('cause', 'Unknown')}",
                "timestamp": alert.get("timestamp", time.time())
            })
        
        return jsonify({
            "recent": recent_alerts,
            "count": len(recent_alerts)
        })

# ============== START SERVER ==============

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 AI ACCIDENT CAUSE PREDICTOR - DASHCAM ANALYSIS SYSTEM")
    print("="*70)
    print("📊 Dashboard URL: http://127.0.0.1:5000")
    print("⏳ Initializing AI models in background thread...")
    print("   This may take 30-60 seconds")
    print("="*70 + "\n")
    
    # Start Flask server
    app.run(debug=False, threaded=True, port=5000, host='0.0.0.0')