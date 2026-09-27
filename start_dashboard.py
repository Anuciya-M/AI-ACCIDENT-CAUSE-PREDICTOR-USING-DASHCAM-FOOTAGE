#!/usr/bin/env python3
"""
Video Streaming Fixer - Run this file to start the dashboard with video streaming
"""
import os
import subprocess
import sys
import time

def main():
    print("\n" + "="*70)
    print("🚀 AI ACCIDENT CAUSE PREDICTOR - VIDEO STREAMING FIX")
    print("="*70 + "\n")
    
    # Get the current directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print("📁 Working directory:", script_dir)
    print("\n⏳ Starting app_fixed.py...\n")
    
    try:
        # Run the fixed app
        subprocess.run([sys.executable, "app_fixed.py"], check=False)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Try running manually:")
        print("   python app_fixed.py")

if __name__ == "__main__":
    main()
