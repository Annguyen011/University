import cv2
import numpy as np
import pickle
import os
import joblib
from pathlib import Path
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler

class ParkingSVM:
    def __init__(self):
        # Cấu hình SVM bám sát kiến trúc trong báo cáo (Kernel: rbf, C: 1.0, gamma: scale)
        self.model = SVC(kernel='rbf', C=1.0, gamma='scale')
        self.scaler = StandardScaler()
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(self.script_dir, 'models', 'svm_parking.pkl')
        self.scaler_path = os.path.join(self.script_dir, 'models', 'svm_scaler.pkl')
        self.img_size = (40, 19)

    def load_model(self):
        """Tải mô hình đã được huấn luyện sẵn"""
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            return True
        return False

    def train(self, dataset_dir=None):
        """
        Đọc dữ liệu từ folder, huấn luyện và lưu mô hình SVM.
        """
        if dataset_dir is None:
            dataset_dir = os.path.join(self.script_dir, 'dataset')
        print("Đang đọc dữ liệu huấn luyện (tối đa 2000 mẫu mỗi loại để cân bằng)...")
        X_train, y_train = [], []
        
        for label, class_name in enumerate(['empty', 'occupied']):
            folder = Path(dataset_dir) / 'train' / class_name
            if not folder.exists():
                print(f"Lỗi: Không tìm thấy thư mục {folder}. Vui lòng chạy create_dataset.py trước.")
                return False
                
            for img_file in list(folder.glob('*.png'))[:2000]:
                img = cv2.imread(str(img_file), cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    img = cv2.resize(img, self.img_size)
                    X_train.append(img.flatten())
                    y_train.append(label)
                    
        print("Bắt đầu chuẩn hóa và huấn luyện SVM (vui lòng đợi 1-2 phút)...")
        X_train_scaled = self.scaler.fit_transform(X_train)
        self.model.fit(X_train_scaled, y_train)
        
        os.makedirs(os.path.join(self.script_dir, 'models'), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        print("Huấn luyện hoàn tất và đã lưu mô hình!")
        return True

    def predict(self, img_crop):
        """ Dự đoán (Inference) trạng thái một ô đỗ xe từ ảnh thực tế """
        if len(img_crop.shape) == 3:
            img_crop = cv2.cvtColor(img_crop, cv2.COLOR_BGR2GRAY)
            
        img_crop = cv2.resize(img_crop, self.img_size)
        # Trích xuất Flatten (1x760) và Chuẩn hóa 
        flat_features = img_crop.flatten().reshape(1, -1)
        scaled_features = self.scaler.transform(flat_features)
        
        # 4. Prediction -> Trả về True nếu là 1 (Occupied), False nếu là 0 (Empty)
        return self.model.predict(scaled_features)[0] == 1

def main():
    """Khối thực thi chính: Huấn luyện (nếu chưa có) và Chạy Video Inference"""
    svm_system = ParkingSVM()
    
    # Khởi tạo mô hình
    if not svm_system.load_model():
        print("Chưa có mô hình. Bắt đầu quá trình huấn luyện...")
        if not svm_system.train():
            return
    else:
        print("Đã tải mô hình SVM thành công!")

    # Chạy Inference trên Video
    script_dir = os.path.dirname(os.path.abspath(__file__))
    park_positions_path = os.path.join(script_dir, 'park_positions')
    video_path = os.path.join(script_dir, 'input', 'parking.mp4')

    try:
        with open(park_positions_path, 'rb') as f:
            park_positions = pickle.load(f)
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file '{park_positions_path}'.")
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Lỗi: Không tìm thấy video '{video_path}'.")
        return

    width, height = 40, 19
    font = cv2.FONT_HERSHEY_COMPLEX_SMALL

    print("Bắt đầu nhận diện bằng SVM. Nhấn ESC để thoát.")

    while True:
        if cap.get(cv2.CAP_PROP_POS_FRAMES) == cap.get(cv2.CAP_PROP_FRAME_COUNT):
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
        ret, frame = cap.read()
        if not ret: break
        
        overlay = frame.copy()
        counter = 0
        
        for pos in park_positions:
            x, y = pos
            img_crop = frame[y:y+height, x:x+width]
            
            # Predict
            is_occupied = svm_system.predict(img_crop)
            
            if not is_occupied:
                color = (0, 255, 0) # Trống
                counter += 1
            else:
                color = (0, 0, 255) # Có xe
                
            cv2.rectangle(overlay, pos, (pos[0]+width, pos[1]+height), color, -1)
            
        alpha = 0.7
        frame_new = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        
        cv2.rectangle(frame_new, (0, 0), (220, 60), (255, 0, 255), -1)
        cv2.putText(frame_new, f"{counter}/{len(park_positions)}", (20, 45), font, 2, (255, 255, 255), 2)
        
        cv2.imshow('SVM - Parking Space Counting', frame_new)
        if cv2.waitKey(1) & 0xFF == 27:
            break
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()