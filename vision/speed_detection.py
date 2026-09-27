# speed_detection.py
# Vehicle Speed Detection Module
# Tracks object movement between frames and estimates speed in km/h

import cv2
import numpy as np

class SpeedDetector:
    """
    Calculates vehicle speed using optical flow and object tracking
    Assumes standard dashcam calibration
    """
    
    def __init__(self, fps=30.0, camera_width_cm=3000, frame_width=640):
        """
        fps: Frames per second of video
        camera_width_cm: Estimated width that camera sees (in cm) at standard distance (3000cm = 30m at 10m distance, typical 120° FOV dashcam)
        frame_width: Width of video frame in pixels
        """
        self.fps = fps
        self.camera_width_cm = camera_width_cm  # Realistic for dashcam: 30m width at 10m distance (120° FOV)
        self.frame_width = frame_width
        self.pixel_to_cm = camera_width_cm / frame_width  # Conversion factor
        self.track_history = {}  # Store previous positions for speed calculation
        self.last_valid_speeds = {}  # Cache for smoothing
        print(f"[SpeedDetector] Initialized: FPS={fps}, Camera width={camera_width_cm}cm (30m at 10m distance), Pixel-to-CM ratio={self.pixel_to_cm:.4f}")
    
    def estimate_speed_from_distance(self, distance_pixels, time_seconds):
        """
        Calculate speed from pixel distance traveled over time
        Returns speed in km/h
        """
        if time_seconds <= 0:
            return 0.0
        
        # Convert pixel distance to centimeters
        distance_cm = distance_pixels * self.pixel_to_cm
        distance_m = distance_cm / 100
        
        # Speed = distance / time
        speed_ms = distance_m / time_seconds
        
        # Convert m/s to km/h (multiply by 3.6)
        speed_kmh = speed_ms * 3.6
        
        return max(0.0, speed_kmh)
    
    def calculate_object_speed(self, track_info, frame_count):
        """
        Calculate speed for tracked objects
        
        Args:
            track_info: Dict with object tracking data {id: {label, bbox, distance}}
            frame_count: Current frame number
        
        Returns:
            Dict with speed data {id: {speed_kmh, label}}
        """
        speed_data = {}
        time_step = 1.0 / self.fps  # Time between frames in seconds
        
        # If no tracking data, return empty speed data (will show 0 km/h)
        if not track_info:
            return speed_data
        
        for track_id, info in track_info.items():
            bbox = info.get("bbox", (0, 0, 0, 0))
            label = info.get("label", "unknown")
            
            # Get center of bounding box
            current_center_x = (bbox[0] + bbox[2]) / 2.0
            current_center_y = (bbox[1] + bbox[3]) / 2.0
            
            # Store current position
            if track_id not in self.track_history:
                # New track - initialize
                self.track_history[track_id] = {
                    "positions": [(current_center_x, current_center_y)],
                    "frame_counts": [frame_count],
                    "label": label,
                    "smoothed_speed": 0.0
                }
                self.last_valid_speeds[track_id] = 0.0
                speed_data[track_id] = {
                    "speed_kmh": 0.0,
                    "label": label,
                    "center": (current_center_x, current_center_y)
                }
            else:
                history = self.track_history[track_id]
                
                # Keep only last 30 positions for better moving average
                if len(history["positions"]) >= 30:
                    history["positions"] = history["positions"][-30:]
                    history["frame_counts"] = history["frame_counts"][-30:]
                
                # Get previous position and frame
                prev_center_x, prev_center_y = history["positions"][-1]
                prev_frame = history["frame_counts"][-1]
                
                # Calculate pixel distance (more precise with floats)
                pixel_distance = np.sqrt(
                    (current_center_x - prev_center_x)**2 + 
                    (current_center_y - prev_center_y)**2
                )
                
                # Calculate time difference
                frames_diff = frame_count - prev_frame
                time_diff = frames_diff * time_step
                
                # Calculate speed - detect movement as low as 0.3 pixels
                speed_kmh = 0.0
                if time_diff > 0 and pixel_distance >= 0.3:  # Very sensitive threshold
                    speed_kmh = self.estimate_speed_from_distance(pixel_distance, time_diff)
                    # Cap unrealistic speeds (max 200 km/h)
                    speed_kmh = min(speed_kmh, 200.0)
                
                # Apply stronger exponential smoothing for stability
                smoothing_factor = 0.5  # 50% new, 50% old (balanced)
                prev_smooth = history.get("smoothed_speed", 0.0)
                smoothed_speed = (smoothing_factor * speed_kmh) + ((1 - smoothing_factor) * prev_smooth)
                
                # If speed drops below 0.5, trend to zero slowly
                if smoothed_speed < 0.5:
                    smoothed_speed = smoothed_speed * 0.7
                
                history["smoothed_speed"] = smoothed_speed
                self.last_valid_speeds[track_id] = smoothed_speed
                
                # Log significant speeds
                if smoothed_speed > 1.0:
                    print(f"[Speed] ID:{track_id} | {pixel_distance:.2f}px in {time_diff:.4f}s | Raw:{speed_kmh:.2f}km/h → Smooth:{smoothed_speed:.2f}km/h")
                
                # Add to history
                history["positions"].append((current_center_x, current_center_y))
                history["frame_counts"].append(frame_count)
                
                speed_data[track_id] = {
                    "speed_kmh": smoothed_speed,
                    "label": label,
                    "center": (current_center_x, current_center_y)
                }
        
        # Clean up history for disappeared objects
        disappeared_ids = [tid for tid in self.track_history.keys() 
                          if tid not in track_info]
        for tid in disappeared_ids:
            del self.track_history[tid]
            if tid in self.last_valid_speeds:
                del self.last_valid_speeds[tid]
        
        return speed_data
    
    def draw_speed_overlay(self, frame, speed_data, track_info):
        """
        Draw speed information on video frame
        
        Args:
            frame: Video frame
            speed_data: Speed calculation results
            track_info: Object tracking data
        """
        for track_id, speed_info in speed_data.items():
            if track_id not in track_info:
                continue
            
            bbox = track_info[track_id]["bbox"]
            x1, y1, x2, y2 = bbox
            label = speed_info["label"]
            speed_kmh = speed_info["speed_kmh"]
            
            # Choose color based on speed
            if speed_kmh > 80:
                color = (0, 0, 255)  # Red - speeding
            elif speed_kmh > 60:
                color = (0, 165, 255)  # Orange - moderate
            else:
                color = (0, 255, 0)  # Green - safe
            
            # Display speed above bounding box - REMOVED FOR CLEAN VIDEO
            speed_text = f"{speed_kmh:.1f} km/h"
            
            # Text overlay removed - data is sent to dashboard instead
            # Background for text
            # text_size = cv2.getTextSize(speed_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            # cv2.rectangle(frame, 
            #              (x1, y1 - 30), 
            #              (x1 + text_size[0] + 10, y1 - 5),
            #              color, -1)
            
            # Draw text
            # cv2.putText(frame, speed_text, (x1 + 5, y1 - 10),
            #            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Draw label below speed
            # cv2.putText(frame, label.upper(), (x1 + 5, y2 + 20),
            #            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        return frame


def get_max_speed(speed_data):
    """Get maximum speed from all detected objects"""
    if not speed_data:
        return 0.0
    speeds = [info["speed_kmh"] for info in speed_data.values() if info["speed_kmh"] > 0]
    if not speeds:
        return 0.0
    return max(speeds)


def get_avg_speed(speed_data):
    """Get average speed from all detected objects"""
    if not speed_data:
        return 0.0
    speeds = [info["speed_kmh"] for info in speed_data.values() if info["speed_kmh"] > 0]
    if not speeds:
        return 0.0
    return np.mean(speeds) if speeds else 0.0
