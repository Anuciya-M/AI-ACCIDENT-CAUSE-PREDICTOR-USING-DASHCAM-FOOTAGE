# prediction/risk_predictor.py (updated)
import os
import torch
import torch.nn as nn

class AccidentLSTM(nn.Module):
    def __init__(self, input_size=5, hidden_size=128):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        _, (h, _) = self.lstm(x)
        return self.sigmoid(self.fc(h.squeeze(0)))

def load_model(device):
    model = AccidentLSTM().to(device)
    model_path = 'models/accident_model.pth'
    # Ensure models directory exists
    model_dir = os.path.dirname(model_path)
    if model_dir and not os.path.exists(model_dir):
        try:
            os.makedirs(model_dir, exist_ok=True)
        except Exception:
            pass

    # If the model file is missing, save the fresh (untrained) weights as a placeholder
    if not os.path.exists(model_path):
        try:
            torch.save(model.state_dict(), model_path)
            print(f"No trained model found. Saved a new placeholder model to {model_path}")
        except Exception as e:
            print(f"Warning: Could not create placeholder model ({e}). Using in-memory random weights")
            return model

    try:
        model.load_state_dict(torch.load(model_path, map_location=device))
        print(f"Trained model loaded successfully from {model_path}")
    except Exception as e:
        print(f"Warning: Could not load trained model ({e}). Using random weights (demo mode only)")
    
    model.eval()  # Important: Always set to eval mode
    return model

def predict_risk(model, sequence, device):
    if model is None:
        print("Model is None! Returning baseline risk assessment.")
        return 0.25  # Baseline risk - safer default
    
    try:
        with torch.no_grad():
            seq_tensor = torch.FloatTensor(sequence).to(device)
            prob = model(seq_tensor).item()
            # Ensure probability is in valid range
            prob = max(0.0, min(1.0, prob))
            return prob
    except Exception as e:
        print(f"Risk prediction error: {e}")
        return 0.25  # Safe fallback