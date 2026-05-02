"""
SVM-based Parking Space Counter
Main inference script using trained SVM model
"""

import cv2
import pickle
import numpy as np
import joblib

# Configuration
VIDEO_PATH = 'input/parking.mp4'
POSITIONS_FILE = 'park_positions'
SVM_MODEL_PATH = 'models/svm_parking.pkl'
SCALER_PATH = 'models/svm_scaler.pkl'
WIDTH, HEIGHT = 40, 19
IMG_SIZE = (40, 19)

# Load SVM model and scaler
print('Loading SVM model...')
svm = joblib.load(SVM_MODEL_PATH)
scaler = joblib.load(SCALER_PATH)
print('✓ Model loaded!')

# Load parking positions
with open(POSITIONS_FILE, 'rb') as f:
    park_positions = pickle.load(f)

print(f'✓ Loaded {len(park_positions)} parking positions')

# Open video
cap = cv2.VideoCapture(VIDEO_PATH)

font = cv2.FONT_HERSHEY_COMPLEX_SMALL

def extract_features(img):
    """Extract raw pixel features from grayscale patch"""
    # Resize and flatten to match training
    img_resized = cv2.resize(img, IMG_SIZE)
    return img_resized.flatten()

def parking_space_counter_svm(frame, overlay):
    """Check parking spaces using SVM model"""
    counter = 0
    
    for position in park_positions:
        x, y = position
        
        # Extract patch
        patch = frame[y:y+HEIGHT, x:x+WIDTH]
        
        # Skip invalid patches
        if patch.shape[0] != HEIGHT or patch.shape[1] != WIDTH:
            continue
        
        # Convert to grayscale
        patch_gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
        
        # Extract raw pixel features
        features = extract_features(patch_gray)
        features_scaled = scaler.transform([features])
        
        # Predict
        prediction = svm.predict(features_scaled)[0]
        
        # 0 = empty, 1 = occupied
        if prediction == 0:
            color = (0, 255, 0)  # Green - Empty
            counter += 1
        else:
            color = (0, 0, 255)  # Red - Occupied
        
        # Draw on overlay
        cv2.rectangle(overlay, position, (position[0] + WIDTH, position[1] + HEIGHT), color, -1)
    
    return counter

print('\n✓ Starting SVM inference...')
print('  Press ESC to quit\n')

import time
frame_count = 0
start_time = time.time()

while True:
    # Video looping
    if cap.get(cv2.CAP_PROP_POS_FRAMES) == cap.get(cv2.CAP_PROP_FRAME_COUNT):
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    _, frame = cap.read()
    overlay = frame.copy()
    
    # Run SVM inference
    counter = parking_space_counter_svm(frame, overlay)
    
    # Alpha blending
    alpha = 0.7
    frame_new = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
    
    # Draw counter box
    w, h = 220, 60
    cv2.rectangle(frame_new, (0, 0), (w, h), (255, 0, 255), -1)
    cv2.putText(frame_new, f"{counter}/{len(park_positions)}", (int(w / 10), int(h * 3 / 4)), 
                font, 2, (255, 255, 255), 2, cv2.LINE_AA)
    
    # Display
    cv2.namedWindow('SVM Parking Counter', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('SVM Parking Counter', 1280, 720)
    cv2.imshow('SVM Parking Counter', frame_new)
    
    # FPS counter
    frame_count += 1
    if frame_count % 30 == 0:
        elapsed = time.time() - start_time
        fps = frame_count / elapsed
        print(f'FPS: {fps:.1f} | Free: {counter}/{len(park_positions)}')
    
    if cv2.waitKey(10) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()

# Final stats
elapsed = time.time() - start_time
avg_fps = frame_count / elapsed
print(f'\n✓ Inference complete')
print(f'  Frames processed: {frame_count}')
print(f'  Average FPS: {avg_fps:.1f}')
