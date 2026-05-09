"""
SVM Classifier Training for Parking Space Detection
Uses HOG features or raw pixel values from parking slot patches
"""

import pickle
import numpy as np
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import cv2
import os
import json
from pathlib import Path
import joblib

print('='*60)
print('SVM Parking Space Classifier - Training')
print('='*60)

# Configuration
DATASET_DIR = 'dataset'
MODEL_SAVE_PATH = 'models/svm_parking.pkl'
SCALER_SAVE_PATH = 'models/svm_scaler.pkl'
USE_HOG = False  # Use raw pixels for faster training
IMG_SIZE = (40, 19)

os.makedirs('models', exist_ok=True)

def extract_features(img_path, use_hog=True):
    """Extract features from image"""
    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    
    if use_hog:
        # HOG features
        winSize = (40, 20)  # Must be multiple of blockSize
        blockSize = (20, 20)
        blockStride = (10, 10)
        cellSize = (10, 10)
        nbins = 9
        
        hog = cv2.HOGDescriptor(winSize, blockSize, blockStride, cellSize, nbins)
        features = hog.compute(img)
        return features.flatten()
    else:
        # Raw pixel values (flattened)
        img_resized = cv2.resize(img, IMG_SIZE)
        return img_resized.flatten()

def load_dataset(split):
    """Load dataset and extract features"""
    X = []
    y = []
    
    # Load empty samples (label = 0)
    empty_dir = Path(f'{DATASET_DIR}/{split}/empty')
    print(f'Loading {split}/empty...')
    for img_file in list(empty_dir.glob('*.png'))[:2000]:  # Limit for speed
        features = extract_features(str(img_file), USE_HOG)
        X.append(features)
        y.append(0)
    
    # Load occupied samples (label = 1)
    occupied_dir = Path(f'{DATASET_DIR}/{split}/occupied')
    print(f'Loading {split}/occupied...')
    for img_file in list(occupied_dir.glob('*.png'))[:2000]:  # Limit for speed
        features = extract_features(str(img_file), USE_HOG)
        X.append(features)
        y.append(1)
    
    return np.array(X), np.array(y)

# Load datasets
print('\nLoading training data...')
X_train, y_train = load_dataset('train')
print(f'  Train: {len(X_train)} samples, {X_train.shape[1]} features')

print('Loading validation data...')
X_val, y_val = load_dataset('val')
print(f'  Val: {len(X_val)} samples')

print('Loading test data...')
X_test, y_test = load_dataset('test')
print(f'  Test: {len(X_test)} samples')

# Normalize features
print('\nNormalizing features...')
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)
X_test_scaled = scaler.transform(X_test)

# Train SVM
print('\nTraining SVM...')
print('  Kernel: RBF')
print('  This may take 2-5 minutes...\n')

svm = SVC(kernel='rbf', C=1.0, gamma='scale', verbose=True)
svm.fit(X_train_scaled, y_train)

print('\n✓ Training complete!')

# Evaluate
print('\nEvaluating...')
y_train_pred = svm.predict(X_train_scaled)
y_val_pred = svm.predict(X_val_scaled)
y_test_pred = svm.predict(X_test_scaled)

train_acc = accuracy_score(y_train, y_train_pred)
val_acc = accuracy_score(y_val, y_val_pred)
test_acc = accuracy_score(y_test, y_test_pred)

test_precision = precision_score(y_test, y_test_pred)
test_recall = recall_score(y_test, y_test_pred)
test_f1 = f1_score(y_test, y_test_pred)

# Save models
joblib.dump(svm, MODEL_SAVE_PATH)
joblib.dump(scaler, SCALER_SAVE_PATH)

print('\n' + '='*60)
print('Training Results:')
print('='*60)
print(f'Train Accuracy: {train_acc:.4f}')
print(f'Val Accuracy:   {val_acc:.4f}')
print(f'Test Accuracy:  {test_acc:.4f}')
print(f'Test Precision: {test_precision:.4f}')
print(f'Test Recall:    {test_recall:.4f}')
print(f'Test F1-Score:  {test_f1:.4f}')
print('='*60)

# Confusion matrix
cm = confusion_matrix(y_test, y_test_pred)
print('\nConfusion Matrix:')
print(f'                Predicted')
print(f'                Empty  Occupied')
print(f'Actual Empty    {cm[0][0]:5d}  {cm[0][1]:5d}')
print(f'Actual Occupied {cm[1][0]:5d}  {cm[1][1]:5d}')

# Save training stats for report
training_stats = {
    'svm': {
        'hyperparameters': {
            'kernel': 'rbf',
            'C': 1.0,
            'gamma': 'scale'
        },
        'metrics': {
            'train_accuracy': float(train_acc),
            'val_accuracy': float(val_acc),
            'test_accuracy': float(test_acc),
            'test_precision': float(test_precision),
            'test_recall': float(test_recall),
            'test_f1': float(test_f1)
        }
    }
}

with open('training_stats.json', 'w', encoding='utf-8') as f:
    json.dump(training_stats, f, indent=2)
print(f'\n✓ Training stats saved to: training_stats.json')

print(f'\n✓ Model saved to: {MODEL_SAVE_PATH}')
print(f'✓ Scaler saved to: {SCALER_SAVE_PATH}')
print('\nNext step: python main_svm.py')
