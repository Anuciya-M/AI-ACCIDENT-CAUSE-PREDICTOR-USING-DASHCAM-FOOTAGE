# weather_detection.py
# Weather Detection Module
# Detects rain, fog, snow, and adverse weather conditions from video

import cv2
import numpy as np

class WeatherDetector:
    """
    Detects weather conditions from dashcam footage
    Analyzes image characteristics to identify rain, fog, snow
    """
    
    def __init__(self):
        self.blur_threshold = 100  # Brightness variance threshold
        self.rain_threshold = 0.15  # Pixel variance for rain detection
        self.fog_threshold = 50  # Fog detection threshold
    
    def detect_rain(self, frame):
        """
        Detect rain in video frame
        Rain causes streaks and increases noise in specific patterns
        
        Returns: (is_raining, rain_intensity 0-1)
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Apply edge detection to find rain streaks
            edges = cv2.Canny(gray, 50, 150)
            
            # Dilate to connect rain streaks
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 10))
            dilated = cv2.dilate(edges, kernel, iterations=2)
            
            # Count rain-like patterns
            rain_pixels = np.count_nonzero(dilated)
            total_pixels = dilated.shape[0] * dilated.shape[1]
            rain_ratio = rain_pixels / total_pixels
            
            # Check for vertical line clusters (rain streaks)
            rain_intensity = min(rain_ratio * 10, 1.0)
            is_raining = rain_intensity > self.rain_threshold
            
            return is_raining, rain_intensity
        
        except Exception as e:
            print(f"[WEATHER] Rain detection error: {e}")
            return False, 0.0
    
    def detect_fog(self, frame):
        """
        Detect fog or haze
        Fog causes low contrast and reduced visibility
        
        Returns: (is_foggy, fog_intensity 0-1)
        """
        try:
            # Convert to HSV for better analysis
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            v_channel = hsv[:, :, 2]
            
            # Low contrast indicates fog
            contrast = np.std(v_channel)
            
            # Fog makes colors washed out (low saturation)
            s_channel = hsv[:, :, 1]
            saturation = np.mean(s_channel)
            
            # Calculate fog intensity
            fog_intensity = max(0, (150 - contrast) / 150)  # Lower contrast = more fog
            
            is_foggy = fog_intensity > 0.4 and saturation < 80
            
            return is_foggy, fog_intensity
        
        except Exception as e:
            print(f"[WEATHER] Fog detection error: {e}")
            return False, 0.0
    
    def detect_snow(self, frame):
        """
        Detect snow
        Snow appears as white particles and increases brightness
        
        Returns: (is_snowing, snow_intensity 0-1)
        """
        try:
            # Convert to HSV
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Define white color range (snow is white)
            lower_white = np.array([0, 0, 200])
            upper_white = np.array([180, 50, 255])
            
            # Create mask for white pixels
            white_mask = cv2.inRange(hsv, lower_white, upper_white)
            
            # Count white pixels
            white_pixels = np.count_nonzero(white_mask)
            total_pixels = white_mask.shape[0] * white_mask.shape[1]
            white_ratio = white_pixels / total_pixels
            
            # Snow creates uniform white regions
            snow_intensity = min(white_ratio * 10, 1.0)
            is_snowing = snow_intensity > 0.2
            
            return is_snowing, snow_intensity
        
        except Exception as e:
            print(f"[WEATHER] Snow detection error: {e}")
            return False, 0.0
    
    def analyze_visibility(self, frame):
        """
        Analyze overall visibility
        
        Returns: visibility_score (0-100, where 100 is perfect visibility)
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Calculate edge density (sharp images have more edges)
            edges = cv2.Canny(gray, 100, 200)
            edge_density = np.count_nonzero(edges) / (edges.shape[0] * edges.shape[1])
            
            # Calculate contrast
            contrast = np.std(gray)
            
            # Visibility score based on contrast and edges
            visibility_score = min(100, (contrast / 50 + edge_density * 500) / 2)
            
            return max(0, min(100, visibility_score))
        
        except Exception as e:
            print(f"[WEATHER] Visibility analysis error: {e}")
            return 50.0
    
    def detect_all_weather(self, frame):
        """
        Comprehensive weather detection
        
        Returns: dict with all weather information
        """
        is_raining, rain_intensity = self.detect_rain(frame)
        is_foggy, fog_intensity = self.detect_fog(frame)
        is_snowing, snow_intensity = self.detect_snow(frame)
        visibility = self.analyze_visibility(frame)
        
        # Determine primary weather condition
        weather_type = "CLEAR"
        if is_raining and rain_intensity > fog_intensity and rain_intensity > snow_intensity:
            weather_type = "RAIN"
        elif is_snowing and snow_intensity > rain_intensity and snow_intensity > fog_intensity:
            weather_type = "SNOW"
        elif is_foggy and fog_intensity > rain_intensity and fog_intensity > snow_intensity:
            weather_type = "FOG"
        elif visibility < 40:
            weather_type = "LOW_VISIBILITY"
        
        return {
            "weather_type": weather_type,
            "is_raining": is_raining,
            "rain_intensity": rain_intensity,
            "is_foggy": is_foggy,
            "fog_intensity": fog_intensity,
            "is_snowing": is_snowing,
            "snow_intensity": snow_intensity,
            "visibility": visibility
        }
    
    def draw_weather_info(self, frame, weather_data):
        """
        Draw weather information on frame
        """
        h, w = frame.shape[:2]
        
        weather_type = weather_data["weather_type"]
        visibility = weather_data["visibility"]
        
        # Determine color based on conditions
        if visibility < 40:
            color = (0, 0, 255)  # Red - dangerous
            bg_color = (0, 0, 200)
        elif visibility < 60:
            color = (0, 165, 255)  # Orange - caution
            bg_color = (0, 100, 200)
        else:
            color = (0, 255, 0)  # Green - good
            bg_color = (0, 150, 0)
        
        # Draw weather status box
        cv2.rectangle(frame, (w - 250, 10), (w - 10, 100), bg_color, -1)
        
        # Weather type
        cv2.putText(frame, f"Weather: {weather_type}", (w - 240, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Visibility
        cv2.putText(frame, f"Visibility: {visibility:.0f}%", (w - 240, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # Individual conditions
        y_offset = 85
        conditions = []
        if weather_data["is_raining"]:
            conditions.append(f"Rain: {weather_data['rain_intensity']:.1%}")
        if weather_data["is_foggy"]:
            conditions.append(f"Fog: {weather_data['fog_intensity']:.1%}")
        if weather_data["is_snowing"]:
            conditions.append(f"Snow: {weather_data['snow_intensity']:.1%}")
        
        for condition in conditions[:2]:  # Show max 2 conditions
            cv2.putText(frame, condition, (w - 240, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            y_offset += 20
        
        return frame
    
    def get_risk_adjustment(self, weather_data):
        """
        Get risk adjustment multiplier based on weather
        Higher multiplier = more dangerous conditions
        
        Returns: risk_multiplier (1.0 to 3.0)
        """
        visibility = weather_data["visibility"]
        
        # Base multiplier on visibility
        if visibility > 80:
            return 1.0  # Normal conditions
        elif visibility > 60:
            return 1.2  # Slightly reduced visibility
        elif visibility > 40:
            return 1.5  # Moderate conditions
        else:
            return 2.5  # Severe conditions
