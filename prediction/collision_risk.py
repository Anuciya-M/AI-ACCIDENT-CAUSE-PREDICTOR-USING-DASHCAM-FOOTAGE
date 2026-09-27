# collision_risk.py
# Collision Risk Prediction Module
# Calculates Time-to-Collision (TTC) and collision probability

import numpy as np

class CollisionRiskCalculator:
    """
    Predicts collision risk using Time-to-Collision (TTC) algorithm
    Analyzes relative distances and speeds between objects
    """
    
    def __init__(self):
        self.ttc_threshold_critical = 1.5  # seconds - LOWERED from 2.0 for faster detection
        self.ttc_threshold_warning = 3.0   # seconds - LOWERED from 5.0 for earlier warning
        self.min_distance_pixels = 50  # Minimum distance to consider collision
    
    def calculate_ttc(self, obj1_bbox, obj2_bbox, obj1_speed, obj2_speed):
        """
        Calculate Time-to-Collision (TTC) between two objects
        
        Args:
            obj1_bbox: (x1, y1, x2, y2) - bounding box 1
            obj2_bbox: (x1, y1, x2, y2) - bounding box 2
            obj1_speed: Speed of object 1 (km/h)
            obj2_speed: Speed of object 2 (km/h)
        
        Returns:
            ttc: Time to collision in seconds (infinite if no collision)
        """
        # Get centers
        center1_x = (obj1_bbox[0] + obj1_bbox[2]) / 2
        center1_y = (obj1_bbox[1] + obj1_bbox[3]) / 2
        center2_x = (obj2_bbox[0] + obj2_bbox[2]) / 2
        center2_y = (obj2_bbox[1] + obj2_bbox[3]) / 2
        
        # Distance between centers (pixels)
        distance = np.sqrt((center2_x - center1_x)**2 + (center2_y - center1_y)**2)
        
        # Relative speed (km/h)
        relative_speed = abs(obj1_speed - obj2_speed)
        
        # Convert speed to pixels per second
        # Assuming 640px width = 300cm (3 meters)
        pixels_per_meter = 640 / (3 * 100)  # pixels per cm
        relative_speed_pixels_per_sec = (relative_speed * 1000) / (3.6 * 100) * pixels_per_meter
        
        # Calculate TTC
        if relative_speed_pixels_per_sec <= 0:
            return float('inf')  # Moving apart or same speed
        
        ttc = distance / relative_speed_pixels_per_sec
        
        return max(0, ttc)
    
    def get_collision_risk_level(self, ttc):
        """
        Determine risk level based on TTC
        
        Returns: ("CRITICAL", "WARNING", "SAFE")
        """
        if ttc <= self.ttc_threshold_critical:
            return "CRITICAL"
        elif ttc <= self.ttc_threshold_warning:
            return "WARNING"
        else:
            return "SAFE"
    
    def analyze_collisions(self, track_info, speed_data):
        """
        Analyze potential collisions between all object pairs
        
        Args:
            track_info: Dict of tracked objects
            speed_data: Dict of speed calculations
        
        Returns:
            collision_risks: List of collision risks
            highest_risk: Dict of most critical collision
        """
        collision_risks = []
        highest_risk = {
            "ttc": float('inf'),
            "risk_level": "SAFE",
            "obj1_id": None,
            "obj2_id": None,
            "obj1_label": None,
            "obj2_label": None
        }
        
        track_ids = list(track_info.keys())
        
        # Check all pairs
        for i in range(len(track_ids)):
            for j in range(i + 1, len(track_ids)):
                id1, id2 = track_ids[i], track_ids[j]
                
                bbox1 = track_info[id1]["bbox"]
                bbox2 = track_info[id2]["bbox"]
                label1 = track_info[id1]["label"]
                label2 = track_info[id2]["label"]
                
                # Get speeds
                speed1 = speed_data.get(id1, {}).get("speed_kmh", 0)
                speed2 = speed_data.get(id2, {}).get("speed_kmh", 0)
                
                # Calculate distance
                center1_x = (bbox1[0] + bbox1[2]) / 2
                center1_y = (bbox1[1] + bbox1[3]) / 2
                center2_x = (bbox2[0] + bbox2[2]) / 2
                center2_y = (bbox2[1] + bbox2[3]) / 2
                
                distance = np.sqrt((center2_x - center1_x)**2 + (center2_y - center1_y)**2)
                
                # Only consider nearby objects
                if distance > 300:  # Too far
                    continue
                
                # Calculate TTC
                ttc = self.calculate_ttc(bbox1, bbox2, speed1, speed2)
                
                # Get risk level
                risk_level = self.get_collision_risk_level(ttc)
                
                # Store collision risk
                collision_risks.append({
                    "obj1_id": id1,
                    "obj2_id": id2,
                    "obj1_label": label1,
                    "obj2_label": label2,
                    "ttc": ttc,
                    "distance_px": distance,
                    "speed1": speed1,
                    "speed2": speed2,
                    "risk_level": risk_level
                })
                
                # Update highest risk
                if ttc < highest_risk["ttc"]:
                    highest_risk = {
                        "ttc": ttc,
                        "risk_level": risk_level,
                        "obj1_id": id1,
                        "obj2_id": id2,
                        "obj1_label": label1,
                        "obj2_label": label2,
                        "distance_px": distance,
                        "speed1": speed1,
                        "speed2": speed2
                    }
        
        return collision_risks, highest_risk
    
    def get_collision_summary(self, collision_risks):
        """
        Summarize collision risks
        
        Returns: Dict with critical, warning, and safe counts
        """
        summary = {
            "critical": len([r for r in collision_risks if r["risk_level"] == "CRITICAL"]),
            "warning": len([r for r in collision_risks if r["risk_level"] == "WARNING"]),
            "safe": len([r for r in collision_risks if r["risk_level"] == "SAFE"]),
            "total": len(collision_risks)
        }
        return summary
