import cv2
import numpy as np

def detect_lane(frame):
    height, width = frame.shape[:2]
    
    # Blur for noise reduction
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    
    # Stronger edges
    edges = cv2.Canny(blur, 80, 200)
    
    # Better ROI - avoid vehicle bottom
    mask = np.zeros_like(edges)
    polygon = np.array([[
        (int(width * 0.1), height),
        (int(width * 0.9), height),
        (int(width * 0.6), int(height * 0.55)),
        (int(width * 0.4), int(height * 0.55))
    ]], np.int32)
    cv2.fillPoly(mask, polygon, 255)
    cropped_edges = cv2.bitwise_and(edges, mask)
    
    # Stricter Hough parameters - only long, strong lines
    lines = cv2.HoughLinesP(
        cropped_edges,
        rho=2,
        theta=np.pi/180,
        threshold=50,  # Lowered from 100 for better detection
        minLineLength=50,  # Lowered from 100 for better detection
        maxLineGap=100  # Increased from 50 for better continuity
    )
    
    lane_present = False
    if lines is not None:
        lane_present = True
        # Filter lines by slope to avoid horizontal (vehicle edges)
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 == x1:  # Vertical line skip
                continue
            slope = (y2 - y1) / (x2 - x1)
            if abs(slope) < 0.3:  # Too horizontal → likely vehicle edge
                continue
                
            cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 255), 3)  # Yellow for lanes - BOLD

    return frame, lane_present