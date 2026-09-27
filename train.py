import os
import cv2
import numpy as np
from tqdm import tqdm
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from prediction.risk_predictor import AccidentLSTM
import pickle
import time

# ==================== CONFIGURATION ====================
# dataset path (nexar_dataset/train)
DATA_DIR = r"C:\Users\ANU M\Desktop\AI ACCIDENT CAUSE PREDICTOR USING DASHCAM FOOTAGE\nexar_dataset\train"

positive_dir = os.path.join(DATA_DIR, "positive")
negative_dir = os.path.join(DATA_DIR, "negative")

# Checkpoint files
PROCESSED_FILE = "processed_videos.pkl"
FINAL_MODEL = "models/accident_model.pth"

# ==================== PROGRESS & RESUME SETUP ====================
if os.path.exists(PROCESSED_FILE):
    with open(PROCESSED_FILE, 'rb') as f:
        processed_videos = pickle.load(f)
    print(f"Resuming training... Already processed {len(processed_videos)} videos")
else:
    processed_videos = set()
    print("Starting fresh training...")

# Count total videos
pos_count = len([f for f in os.listdir(positive_dir) if f.lower().endswith('.mp4')])
neg_count = len([f for f in os.listdir(negative_dir) if f.lower().endswith('.mp4')])
total_videos = pos_count + neg_count
processed = len(processed_videos)
remaining = total_videos - processed

print("\n" + "="*60)
print("DATASET & PROGRESS SUMMARY")
print("="*60)
print(f"Positive (Accident) videos : {pos_count}")
print(f"Negative (Normal) videos   : {neg_count}")
print(f"Total videos               : {total_videos}")
print(f"Already processed          : {processed}")
print(f"Remaining videos           : {remaining}")
print("="*60 + "\n")

if remaining == 0:
    print("All videos already processed! Skipping feature extraction.")
else:
    print("Starting feature extraction from remaining videos...")

# ==================== VISION MODULES ====================
from vision.object_detection import detect_and_track  # Using ByteTrack (faster alternative to DeepSORT for real-time)
from vision.lane_detection import detect_lane
from vision.motion_detection import compute_motion

def extract_features_from_video(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Warning: Could not open {os.path.basename(video_path)}")
        return []
    
    features_seq = []
    prev_gray = None
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or frame_count >= 300:  # ~10 seconds max
            break
        
        frame = cv2.resize(frame, (640, 480))
        
        _, detections, track_info, _, _ = detect_and_track(frame)
        _, lane_present = detect_lane(frame)
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        motion_score = compute_motion(prev_gray, gray) if prev_gray is not None else 0.0
        prev_gray = gray
        
        # track_info holds consistent metadata; detections may be raw tuple output.
        num_persons = sum(1 for t in track_info.values() if t['label'] == 'person')
        num_vehicles = sum(1 for t in track_info.values() if t['label'] in ['car', 'truck', 'bus', 'motorcycle'])
        avg_distance = np.mean([t['distance'] for t in track_info.values()]) if track_info else 100.0
        
        features = [float(num_persons), float(num_vehicles), float(motion_score), float(lane_present), avg_distance / 100.0]
        features_seq.append(features)
        
        frame_count += 1
    
    cap.release()
    return features_seq

# ==================== DATA COLLECTION WITH LIVE PROGRESS ====================
SEQ_LEN = 10
X = []
y = []

extraction_start_time = time.time()
videos_processed_this_run = 0

def process_videos(folder_dir, is_positive):
    global X, y, videos_processed_this_run
    videos = [f for f in os.listdir(folder_dir) if f.lower().endswith('.mp4')]
    folder_type = "Positive (Accident)" if is_positive else "Negative (Normal)"
    
    pbar = tqdm(videos, desc=folder_type, unit="video")
    for video_file in pbar:
        video_path = os.path.join(folder_dir, video_file)
        
        if video_path in processed_videos:
            pbar.set_postfix_str("Skipped (already processed)")
            continue
        
        vid_start = time.time()
        features_seq = extract_features_from_video(video_path)
        vid_time = time.time() - vid_start
        
        if len(features_seq) < SEQ_LEN + 10:
            processed_videos.add(video_path)
            with open(PROCESSED_FILE, 'wb') as f:
                pickle.dump(processed_videos, f)
            pbar.set_postfix_str(f"Short video ({vid_time:.1f}s)")
            continue
        
        # Create sequences
        for i in range(len(features_seq) - SEQ_LEN):
            seq = features_seq[i:i + SEQ_LEN]
            X.append(seq)
            if is_positive:
                y.append(1.0 if i > (len(features_seq) - SEQ_LEN) * 0.7 else 0.5)
            else:
                y.append(0.0)
        
        # Update progress
        processed_videos.add(video_path)
        videos_processed_this_run += 1
        total_processed_now = len(processed_videos)
        remaining_now = total_videos - total_processed_now
        
        elapsed_total = time.time() - extraction_start_time
        avg_time_per_video = elapsed_total / videos_processed_this_run if videos_processed_this_run > 0 else 0
        eta_seconds = remaining_now * avg_time_per_video
        eta_hours = eta_seconds / 3600
        
        with open(PROCESSED_FILE, 'wb') as f:
            pickle.dump(processed_videos, f)
        
        pbar.set_postfix({
            "Done": total_processed_now,
            "Left": remaining_now,
            "ETA": f"{eta_hours:.2f}h",
            "This": f"{vid_time:.1f}s"
        })

# Run processing
if remaining > 0:
    process_videos(positive_dir, is_positive=True)
    process_videos(negative_dir, is_positive=False)
    
    total_extraction_time = time.time() - extraction_start_time
    print(f"\nFeature extraction completed in {total_extraction_time/3600:.2f} hours!")
    print(f"Total sequences collected: {len(X):,}")
else:
    print("All videos processed previously. Loading existing data if needed.")

if len(X) == 0:
    print("No sequences collected! Cannot proceed to training.")
    exit()

# ==================== TRAINING ====================
X = np.array(X, dtype=np.float32)
y = np.array(y, dtype=np.float32)

X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

train_loader = torch.utils.data.DataLoader(
    torch.utils.data.TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train)),
    batch_size=32, shuffle=True
)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"\nTraining on device: {device}")

model = AccidentLSTM(input_size=5, hidden_size=128).to(device)
criterion = nn.BCELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

print("Training started (15 epochs)...\n")

for epoch in range(15):
    model.train()
    train_loss = 0.0
    for batch_x, batch_y in tqdm(train_loader, desc=f"Epoch {epoch+1}/15"):
        batch_x, batch_y = batch_x.to(device), batch_y.to(device)
        
        optimizer.zero_grad()
        outputs = model(batch_x).squeeze()  # FIXED!
        loss = criterion(outputs, batch_y)
        loss.backward()
        optimizer.step()
        
        train_loss += loss.item()
    0
    print(f"Epoch {epoch+1}/15 - Avg Loss: {train_loss/len(train_loader):.4f}")

# Save final model
os.makedirs('models', exist_ok=True)
torch.save(model.state_dict(), FINAL_MODEL)
print(f"\nTraining complete! Trained model saved: {FINAL_MODEL}")
print("Now run 'python app.py' or 'python main.py' for real-time dashboard with English voice alerts.")

# Cleanup
if os.path.exists(PROCESSED_FILE):
    os.remove(PROCESSED_FILE)
    print("Cleanup: processed_videos.pkl removed (training complete)")