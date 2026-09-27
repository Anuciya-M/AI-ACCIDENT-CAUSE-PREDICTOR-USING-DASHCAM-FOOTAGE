# object_detection.py
# YOLOv8 + optional DeepSORT tracking with boxes guaranteed to show
# Fallback to detection-only when tracking dependency is unavailable

from ultralytics import YOLO
import cv2
import numpy as np

# Safe deep sort import (optional)
try:
    from deep_sort_realtime.deepsort_tracker import DeepSort
    has_deepsort = True
except Exception as e:
    print(f"[OBJECT_DETECTION] DeepSort import failed: {e}")
    DeepSort = None
    has_deepsort = False

# ==================== INIT MODELS ====================
print("[INIT] Loading YOLO model...")
yolo_model = None
try:
    yolo_model = YOLO("yolov8n.pt")
    yolo_model.fuse()
    print("[INIT] YOLO model loaded!")
except Exception as e:
    print(f"[INIT] YOLO model load failed: {e}")

tracker = None
if has_deepsort and DeepSort is not None:
    try:
        print("[INIT] Initializing DeepSort tracker...")
        tracker = DeepSort(max_age=30, nn_budget=100, embedder="mobilenet", half=False)
        print("[INIT] Tracker initialized!")
    except Exception as e:
        print(f"[INIT] DeepSort init failed: {e}")
        tracker = None

# ==================== HELPER FUNCTIONS ====================
def estimate_distance(bbox_height, frame_h):
    focal_length = 900
    real_height = 1.7
    if bbox_height <= 0:
        return 100.0
    distance = (real_height * focal_length) / bbox_height
    return min(max(distance, 2.0), 150.0)


def draw_styled_box(frame, bbox, label, confidence, color):
    x1, y1, x2, y2 = bbox
    # Outer border for strong visibility
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 4)
    # Inner highlight line
    cv2.rectangle(frame, (x1 + 3, y1 + 3), (x2 - 3, y2 - 3), (255, 255, 255), 1)

    # Label panel with station background and text
    label_text = f"{label} {confidence:.2f}"
    text_size, _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    text_w, text_h = text_size
    text_x, text_y = x1, max(0, y1 - 10)
    cv2.rectangle(frame, (text_x, text_y - text_h - 6), (text_x + text_w + 10, text_y + 4), color, -1)
    cv2.putText(frame, label_text, (text_x + 5, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    # Optional distance line across the center if required for clarity
    cv2.line(frame, ((x1 + x2) // 2, y2), ((x1 + x2) // 2, y2 + 20), color, 2)


# ==================== MAIN FUNCTION ====================
def detect_and_track(frame):
    if frame is None or frame.size == 0:
        print("[DETECT] Invalid frame input!")
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        return dummy_frame, [], {}, 0, 0

    if yolo_model is None:
        print("[DETECT] YOLO model unavailable, returning empty frame")
        return frame, [], {}, 0, 0

    frame = frame.copy()
    h, w = frame.shape[:2]

    try:
        results = yolo_model.predict(
            frame,
            conf=0.15,
            iou=0.45,
            classes=[0, 2, 3, 5, 7],
            verbose=False
        )[0]

        print(f"[DETECT] YOLO found {len(results.boxes)} boxes")
    except Exception as e:
        print(f"[DETECT] ? YOLO failed: {e}")
        return frame, [], {}, 0, 0

    detections = []
    raw_boxes = []
    for r in results.boxes:
        try:
            x1, y1, x2, y2 = map(int, r.xyxy[0])
            conf = float(r.conf[0])
            cls = int(r.cls[0])

            detections.append(((x1, y1, x2 - x1, y2 - y1), conf, cls))
            raw_boxes.append({"bbox": (x1, y1, x2, y2), "conf": conf, "cls": cls, "label": results.names[cls]})
        except Exception as e:
            print(f"[DETECT] Box processing error: {e}")

    tracks = []
    if tracker is not None:
        try:
            if hasattr(tracker, 'update_tracks'):
                tracks = tracker.update_tracks(detections, frame=frame)
            elif hasattr(tracker, 'update'):
                tracks = tracker.update(detections)
            else:
                tracks = []
            print(f"[DETECT] Tracker returned {len(tracks)} tracks")
        except Exception as e:
            print(f"[DETECT] ? Tracker failed ({type(e).__name__}): {e}")
            tracks = []
    else:
        print("[DETECT] No tracker available; running detection-only")

    track_info = {}
    num_persons = 0
    num_vehicles = 0

    for track in tracks:
        try:
            if not track.is_confirmed():
                continue

            track_id = track.track_id
            ltrb = track.to_ltrb()
            x1, y1, x2, y2 = map(int, ltrb)

            det_class = track.det_class
            label = results.names.get(det_class, 'object') if isinstance(results.names, dict) else results.names[det_class]
            dist = estimate_distance(y2 - y1, h)

            x1 = max(0, min(x1, w))
            y1 = max(0, min(y1, h))
            x2 = max(0, min(x2, w))
            y2 = max(0, min(y2, h))

            if label == 'person':
                num_persons += 1
                color = (0, 0, 255)
            elif label in ['car', 'motorcycle', 'bus', 'truck']:
                num_vehicles += 1
                color = (0, 255, 0)
            else:
                color = (255, 0, 0)

            draw_styled_box(frame, (x1, y1, x2, y2), label, track.det_conf or 0.0, color)
            track_info[track_id] = { 'label': label, 'bbox': (x1, y1, x2, y2), 'distance': dist }

        except Exception as e:
            print(f"[DETECT] Track drawing error: {e}")

    if len(tracks) == 0 and len(raw_boxes) > 0:
        for box_data in raw_boxes:
            x1, y1, x2, y2 = box_data['bbox']
            label = box_data['label']
            conf = box_data['conf']

            x1 = max(0, min(x1, w))
            y1 = max(0, min(y1, h))
            x2 = max(0, min(x2, w))
            y2 = max(0, min(y2, h))

            if label == 'person':
                num_persons += 1
                color = (0, 0, 255)
            elif label in ['car', 'motorcycle', 'bus', 'truck']:
                num_vehicles += 1
                color = (0, 255, 0)
            else:
                color = (255, 0, 0)

            draw_styled_box(frame, (x1, y1, x2, y2), label, conf, color)

    if len(tracks) == 0 and len(raw_boxes) == 0:
        cv2.putText(frame, 'NO TRACKS - DETECTOR ACTIVE', (50, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 165, 0), 3)

    print(f"[DETECT] ? Processing complete | Persons: {num_persons}, Vehicles: {num_vehicles}")
    return frame, detections, track_info, num_persons, num_vehicles
