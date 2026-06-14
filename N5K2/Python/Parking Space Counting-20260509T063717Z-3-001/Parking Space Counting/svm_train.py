import cv2
import os
import joblib
from pathlib import Path
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.join(script_dir, 'dataset')
    model_path = os.path.join(script_dir, 'models', 'svm_parking.pkl')
    scaler_path = os.path.join(script_dir, 'models', 'svm_scaler.pkl')
    img_size = (40, 19)

    print("Đang đọc dữ liệu huấn luyện (tối đa 2000 mẫu mỗi loại để cân bằng)...")
    X_train, y_train = [], []
    
    for label, class_name in enumerate(['empty', 'occupied']):
        folder = Path(dataset_dir) / 'train' / class_name
        if not folder.exists():
            print(f"Lỗi: Không tìm thấy thư mục {folder}. Vui lòng chuẩn bị dữ liệu trước.")
            return
            
        for img_file in list(folder.glob('*.png'))[:2000]:
            img = cv2.imread(str(img_file), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                img = cv2.resize(img, img_size)
                X_train.append(img.flatten())
                y_train.append(label)
                
    if not X_train:
        print("Không có dữ liệu huấn luyện!")
        return
        
    print("Bắt đầu chuẩn hóa và huấn luyện SVM (vui lòng đợi 1-2 phút)...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    
    model = SVC(kernel='rbf', C=1.0, gamma='scale')
    model.fit(X_train_scaled, y_train)
    
    os.makedirs(os.path.join(script_dir, 'models'), exist_ok=True)
    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)
    print("Huấn luyện hoàn tất và đã lưu mô hình!")

if __name__ == '__main__':
    main()