# AI Accident Cause Predictor using Dashcam Footage

An AI-powered system that analyzes dashcam video footage to detect, predict, and explain the causes of road accidents in real time. The system combines computer vision (lane, motion, object, speed, and weather detection) with an AI reasoning layer to generate human-readable accident cause reports and collision risk scores.

## ✨ Features

- 🚗 **Object & Motion Detection** — Detects vehicles, pedestrians, and obstacles using YOLO-based models
- 🛣️ **Lane Detection** — Identifies lane boundaries and lane-departure events
- 🌦️ **Weather Detection** — Estimates weather/visibility conditions from footage
- ⚡ **Speed Estimation** — Approximates vehicle speed from frame-to-frame motion
- ⚠️ **Collision Risk Prediction** — Scores real-time collision risk from detected signals
- 🧠 **AI Cause Engine** — Uses an LLM (OpenAI / Gemini) to generate a natural-language explanation of *why* an accident occurred
- 📊 **Dashboard** — Web dashboard (React frontend + Python backend) to upload footage and view analysis/reports

## 🗂️ Project Structure
├── accident-detector-app/ # Full-stack app (React frontend + backend)
│ ├── frontend/ # React dashboard (Dashboard.jsx, api.js)
│ └── backend/ # Backend services (database, API)
├── vision/ # Computer vision modules
│ ├── lane_detection.py
│ ├── motion_detection.py
│ ├── object_detection.py
│ ├── speed_detection.py
│ └── weather_detection.py
├── prediction/ # Risk & cause prediction logic
│ ├── cause_engine.py
│ ├── collision_risk.py
│ └── risk_predictor.py
├── utils/ # Helper utilities
│ ├── danger_alert.py
│ └── threat_prioritizer.py
├── static/ # CSS/JS for the web UI
├── templates/ # HTML templates
├── main.py # Main entry point
├── train.py # Model training script
├── start_dashboard.py # Launches the dashboard
├── requirements.txt # Python dependencies
└── run_dashboard.bat # Windows launcher script


## 🛠️ Tech Stack

- **Computer Vision:** OpenCV, YOLOv8 (Ultralytics)
- **Backend:** Python (FastAPI/Flask)
- **Frontend:** React
- **AI Reasoning:** OpenAI API / Google Gemini API
- **Database:** SQLite

## 📦 Dataset

This project is built and evaluated using the **Nexar Dashcam Collision Prediction Dataset**.

> ⚠️ The dataset is **not included** in this repository due to its large size.

To use this project, download the dataset separately and place it in a `nexar_dataset/` folder at the project root:

- Dataset source: [Nexar Dashcam Collision Prediction Dataset](https://www.kaggle.com/) *(add the exact Kaggle/competition link you used here)*
- After downloading, your folder structure should look like:

nexar_dataset/
├── test-private/
├── sample_submission.csv
├── solution.csv
└── evaluate_submission.py


## 🧠 Model Weights

Pretrained weights (e.g. `yolov8n.pt`) and trained models (`models/`) are also excluded from version control. On first run:
- YOLOv8 base weights will auto-download via the `ultralytics` package, **or**
- Place your own trained weights in the `models/` folder as documented in `train.py`

## ⚙️ Setup

1. **Clone the repository**
```bash
   git clone https://github.com/<your-username>/<your-repo>.git
   cd <your-repo>
```

2. **Create a virtual environment**
```bash
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   source .venv/bin/activate   # macOS/Linux
```

3. **Install dependencies**
```bash
   pip install -r requirements.txt
```

4. **Set up environment variables**

   Create a `.env` file in the project root (this file is git-ignored and must never be committed):
```env
   OPENAI_API_KEY=your_openai_key_here
   GEMINI_API_KEY=your_gemini_key_here
   USE_GEMINI=true
```

5. **Download the dataset** (see Dataset section above) and place it in `nexar_dataset/`

## ▶️ Usage

**Run the dashboard:**
```bash
python start_dashboard.py
```
or on Windows:
```bash
run_dashboard.bat
```

**Run standalone detection/diagnostics:**
```bash
python main.py
python diagnose_video.py
```

**Train a model:**
```bash
python train.py
```

## 🧪 Testing

```bash
python test_all_modules.py
python test_accident_detection.py
python verify_system.py
```

## 🔐 Security Note

- Never commit your `.env` file or API keys to version control
- Rotate any API keys immediately if accidentally exposed
- This repo's `.gitignore` already excludes `.env`, datasets, model weights, and cache files
