# motion_detection.py

import cv2
import numpy as np

def compute_motion(prev_gray, gray):

    if prev_gray is None:
        return 0.0

    flow = cv2.calcOpticalFlowFarneback(
        prev_gray, gray, None,
        pyr_scale=0.5,
        levels=3,
        winsize=20,   # REDUCED from 25 for more sensitivity to small motions
        iterations=5,
        poly_n=7,
        poly_sigma=1.5,
        flags=0
    )

    mag, ang = cv2.cartToPolar(flow[...,0], flow[...,1])

    # Remove noise
    mag = cv2.GaussianBlur(mag,(5,5),0)

    # Sudden motion focus (top 30% instead of 20% for more sensitivity)
    thresh = np.percentile(mag, 70)  # INCREASED sensitivity: lower percentile
    high_motion = mag[mag>thresh]

    if len(high_motion) > 0:
        return float(np.mean(high_motion))
    else:
        return float(np.mean(mag))
