"""
Model Evaluation Script
Evaluates all three models (Traditional CV, SVM, CNN) on test set
Generates metrics and confusion matrices
"""

import cv2
import pickle
import numpy as np
import json
import os
from pathlib import Path
import joblib
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import time

# TensorFlow imports removed as CNN is no longer used
# try:
#     import tensorflow as tf
#     from tensorflow import keras
#     TF_AVAILABLE = True
# except ImportError:
#     TF_AVAILABLE = False
#     print("Warning: TensorFlow not available, CNN evaluation will be skipped")

# Configuration
DATASET_DIR = 'dataset'
TEST_DIR = os.path.join(DATASET_DIR, 'test')
OUTPUT_FILE = 'model_evaluation.json'
IMG_SIZE = (40, 19)
WIDTH, HEIGHT = 40, 19

# Model paths
SVM_MODEL_PATH = 'models/svm_parking.pkl'
SVM_SCALER_PATH = 'models/svm_scaler.pkl'
# CNN_MODEL_PATH removed

def load_test_data():
    """Load test dataset"""
    print("Loading test dataset...")
    X = []
    y = []
    filenames = []
    
    # Load empty samples (label = 0)
    empty_dir = Path(TEST_DIR) / 'empty'
    for img_file in empty_dir.glob('*.png'):
        img = cv2.imread(str(img_file))
        if img is not None and img.shape[:2] == (HEIGHT, WIDTH):
            X.append(img)
            y.append(0)
            filenames.append(str(img_file))
    
    # Load occupied samples (label = 1)
    occupied_dir = Path(TEST_DIR) / 'occupied'
    for img_file in occupied_dir.glob('*.png'):
        img = cv2.imread(str(img_file))
        if img is not None and img.shape[:2] == (HEIGHT, WIDTH):
            X.append(img)
            y.append(1)
            filenames.append(str(img_file))
    
    print(f"  Loaded {len(X)} test samples (Empty: {y.count(0)}, Occupied: {y.count(1)})")
    return np.array(X), np.array(y), filenames

def evaluate_traditional_cv(X_test, y_test):
    """Evaluate Traditional CV method"""
    print("\n" + "="*70)
    print("EVALUATING TRADITIONAL CV")
    print("="*70)
    
    predictions = []
    full_pixels = WIDTH * HEIGHT
    threshold = 0.22
    
    start_time = time.time()
    
    for img in X_test:
        # Preprocessing
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_blur = cv2.GaussianBlur(img_gray, (3, 3), 1)
        img_thresh = cv2.adaptiveThreshold(img_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY_INV, 25, 16)
        
        # Count white pixels
        count = cv2.countNonZero(img_thresh)
        ratio = count / full_pixels
        
        # 0 = empty, 1 = occupied
        pred = 0 if ratio < threshold else 1
        predictions.append(pred)
    
    elapsed = time.time() - start_time
    fps = len(X_test) / elapsed
    
    predictions = np.array(predictions)
    
    # Calculate metrics
    acc = accuracy_score(y_test, predictions)
    prec = precision_score(y_test, predictions, zero_division=0)
    rec = recall_score(y_test, predictions, zero_division=0)
    f1 = f1_score(y_test, predictions, zero_division=0)
    cm = confusion_matrix(y_test, predictions)
    
    results = {
        'accuracy': float(acc),
        'precision': float(prec),
        'recall': float(rec),
        'f1_score': float(f1),
        'confusion_matrix': cm.tolist(),
        'inference_time': float(elapsed),
        'fps': float(fps)
    }
    
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall:    {rec:.4f}")
    print(f"F1-Score:  {f1:.4f}")
    print(f"FPS:       {fps:.1f}")
    print(f"\nConfusion Matrix:")
    print(f"  [[{cm[0][0]:4d} {cm[0][1]:4d}]")
    print(f"   [{cm[1][0]:4d} {cm[1][1]:4d}]]")
    
    return results

def evaluate_svm(X_test, y_test):
    """Evaluate SVM model"""
    print("\n" + "="*70)
    print("EVALUATING SVM")
    print("="*70)
    
    # Check if model exists
    if not os.path.exists(SVM_MODEL_PATH):
        print(f"Model not found: {SVM_MODEL_PATH}")
        return None
    
    # Load model
    print("Loading SVM model...")
    svm = joblib.load(SVM_MODEL_PATH)
    scaler = joblib.load(SVM_SCALER_PATH)
    
    # Extract features
    print("Extracting features...")
    features = []
    for img in X_test:
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_resized = cv2.resize(img_gray, IMG_SIZE)
        features.append(img_resized.flatten())
    
    features = np.array(features)
    features_scaled = scaler.transform(features)
    
    # Predict
    start_time = time.time()
    predictions = svm.predict(features_scaled)
    elapsed = time.time() - start_time
    fps = len(X_test) / elapsed
    
    # Calculate metrics
    acc = accuracy_score(y_test, predictions)
    prec = precision_score(y_test, predictions, zero_division=0)
    rec = recall_score(y_test, predictions, zero_division=0)
    f1 = f1_score(y_test, predictions, zero_division=0)
    cm = confusion_matrix(y_test, predictions)
    
    results = {
        'accuracy': float(acc),
        'precision': float(prec),
        'recall': float(rec),
        'f1_score': float(f1),
        'confusion_matrix': cm.tolist(),
        'inference_time': float(elapsed),
        'fps': float(fps)
    }
    
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall:    {rec:.4f}")
    print(f"F1-Score:  {f1:.4f}")
    print(f"FPS:       {fps:.1f}")
    print(f"\nConfusion Matrix:")
    print(f"  [[{cm[0][0]:4d} {cm[0][1]:4d}]")
    print(f"   [{cm[1][0]:4d} {cm[1][1]:4d}]]")
    
    return results


# CNN_MODEL_PATH removed


if __name__ == '__main__':
    print("="*70)
    print("MODEL EVALUATION SCRIPT")
    print("="*70)
    
    # Load test data
    X_test, y_test, filenames = load_test_data()
    
    if len(X_test) == 0:
        print("\nError: No test data found!")
        exit(1)
    
    # Evaluate all models
    evaluation_results = {}
    
    # Traditional CV
    evaluation_results['traditional_cv'] = evaluate_traditional_cv(X_test, y_test)
    
    # SVM
    svm_results = evaluate_svm(X_test, y_test)
    if svm_results:
        evaluation_results['svm'] = svm_results
    


    
    # Save results
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(evaluation_results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*70)
    print(f"✓ Evaluation complete! Results saved to: {OUTPUT_FILE}")
    print("="*70)
