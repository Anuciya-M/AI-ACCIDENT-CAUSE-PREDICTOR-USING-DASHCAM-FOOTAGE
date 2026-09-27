"""
Diagnostic script to test video streaming
Run this to verify the setup is working
"""
import os
import sys

def check_files():
    print("\n" + "="*60)
    print("VIDEO STREAMING DIAGNOSTIC")
    print("="*60 + "\n")
    
    # Check video file
    video_path = r"C:\Users\ANU M\Desktop\AI ACCIDENT CAUSE PREDICTOR USING DASHCAM FOOTAGE\nexar_dataset\train\positive\00959.mp4"
    if os.path.exists(video_path):
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        print(f"✅ Video file exists: {size_mb:.1f} MB")
    else:
        print(f"❌ Video file NOT found!")
        print(f"   Path: {video_path}")
        return False
    
    # Check app files
    files = [
        ("app_fixed.py", "Fixed Flask app (USE THIS)"),
        ("app.py", "Old Flask app (DO NOT USE)"),
        ("main.py", "Processing logic"),
        ("templates/index.html", "Dashboard HTML"),
        ("static/script.js", "Dashboard JavaScript"),
        ("static/static.css", "Dashboard CSS"),
    ]
    
    base = r"C:\Users\ANU M\Desktop\AI ACCIDENT CAUSE PREDICTOR USING DASHCAM FOOTAGE"
    
    print("\n📁 Required Files:")
    for file, desc in files:
        full_path = os.path.join(base, file)
        exists = "✅" if os.path.exists(full_path) else "❌"
        print(f"{exists} {file:<20} - {desc}")
    
    print("\n" + "="*60)
    print("IMPORTANT: Make sure to run app_fixed.py, NOT app.py")
    print("="*60)
    print("\n✅ If all files exist, run:")
    print("   python app_fixed.py")
    print("\n✅ Then open browser:")
    print("   http://127.0.0.1:5000")
    print("\n" + "="*60)

if __name__ == "__main__":
    check_files()
