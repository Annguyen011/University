"""
Dataset Creator for CNN & SVM Parking Space Classifier
Extracts parking slot ROI patches from video and uses Traditional CV model for semi-automatic labeling
"""

import cv2
import pickle
import numpy as np
import os
from pathlib import Path

# Configuration
VIDEO_PATH = 'input/parking.mp4'
POSITIONS_FILE = 'park_positions'
OUTPUT_DIR = 'dataset'
WIDTH, HEIGHT = 40, 19
FRAMES_TO_SAMPLE = 200  # Sample 200 frames from video
THRESHOLD_RATIO = 0.22  # Same as Traditional CV model

# Create dataset directories
def create_dirs():
    for split in ['train', 'val', 'test']:
        for label in ['occupied', 'empty']:
            Path(f'{OUTPUT_DIR}/{split}/{label}').mkdir(parents=True, exist_ok=True)
    print(f'✓ Created dataset directories in {OUTPUT_DIR}/')

# Load parking positions
with open(POSITIONS_FILE, 'rb') as f:
    park_positions = pickle.load(f)

print(f'Loaded {len(park_positions)} parking positions')

# Open video
cap = cv2.VideoCapture(VIDEO_PATH)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f'Video: {total_frames} frames')

# Sample frames uniformly
frame_indices = np.linspace(0, total_frames-1, FRAMES_TO_SAMPLE, dtype=int)

create_dirs()

# Extract and label patches
sample_count = {'occupied': 0, 'empty': 0}
patch_id = 0

full_pixels = WIDTH * HEIGHT

for frame_idx in frame_indices:
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    
    if not ret:
        continue
    
    # Preprocess same as Traditional CV
    img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    img_blur = cv2.GaussianBlur(img_gray, (3, 3), 1)
    img_thresh = cv2.adaptiveThreshold(img_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 25, 16)
    
    # Extract patches for each parking spot
    for pos in park_positions:
        x, y = pos
        
        # Extract RGB patch from original frame
        patch_rgb = frame[y:y+HEIGHT, x:x+WIDTH]
        
        # Extract processed patch for labeling
        patch_processed = img_thresh[y:y+HEIGHT, x:x+WIDTH]
        
        # Skip if patch is too small (edge cases)
        if patch_rgb.shape[0] != HEIGHT or patch_rgb.shape[1] != WIDTH:
            continue
        
        # Auto-label using Traditional CV logic
        count = cv2.countNonZero(patch_processed)
        ratio = count / full_pixels
        label = 'empty' if ratio < THRESHOLD_RATIO else 'occupied'
        
        # Determine split (70% train, 15% val, 15% test)
        rand = np.random.random()
        if rand < 0.70:
            split = 'train'
        elif rand < 0.85:
            split = 'val'
        else:
            split = 'test'
        
        # Save patch
        filename = f'{OUTPUT_DIR}/{split}/{label}/patch_{patch_id:05d}.png'
        cv2.imwrite(filename, patch_rgb)
        
        sample_count[label] += 1
        patch_id += 1
    
    # Progress
    if (frame_idx - frame_indices[0]) % 20 == 0:
        print(f'Progress: {frame_idx}/{total_frames} frames processed...')

cap.release()

# Print statistics
print('\n' + '='*50)
print('Dataset Creation Complete!')
print('='*50)
print(f'Total patches: {patch_id}')
print(f'  Occupied: {sample_count["occupied"]} ({sample_count["occupied"]/patch_id*100:.1f}%)')
print(f'  Empty: {sample_count["empty"]} ({sample_count["empty"]/patch_id*100:.1f}%)')
print(f'\nDataset saved to: {OUTPUT_DIR}/')
print('\nReady for:')
print('  - python train_svm.py')
print('  - python train_cnn.py')
