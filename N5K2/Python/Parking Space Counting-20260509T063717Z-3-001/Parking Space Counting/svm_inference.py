import cv2
import pickle
import os
import joblib

def predict_space(img_crop, model, scaler, img_size=(40, 19)):
    """ Dự đoán trạng thái một ô đỗ xe từ ảnh thực tế """
    if len(img_crop.shape) == 3:
        img_crop = cv2.cvtColor(img_crop, cv2.COLOR_BGR2GRAY)
        
    img_crop = cv2.resize(img_crop, img_size)
    flat_features = img_crop.flatten().reshape(1, -1)
    scaled_features = scaler.transform(flat_features)
    
    return model.predict(scaled_features)[0] == 1

def main():
    """Khối thực thi chính: Chỉ chạy Inference trực tiếp trên Video"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(script_dir, 'models', 'svm_parking.pkl')
    scaler_path = os.path.join(script_dir, 'models', 'svm_scaler.pkl')
    
    # Khởi tạo mô hình
    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        print("Lỗi: Không tìm thấy file mô hình. Vui lòng chạy file 'svm_train.py' trước để huấn luyện.")
        return
    else:
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        print("Đã tải mô hình SVM thành công!")

    # Chạy Inference trên Video
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
        # Lặp lại video nếu hết
        if cap.get(cv2.CAP_PROP_POS_FRAMES) == cap.get(cv2.CAP_PROP_FRAME_COUNT):
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
        ret, frame = cap.read()
        if not ret: break
        
        overlay = frame.copy()
        counter = 0
        
        for pos in park_positions:
            x, y = pos
            img_crop = frame[y:y+height, x:x+width]
            
            # Predict trạng thái
            is_occupied = predict_space(img_crop, model, scaler)
            
            if not is_occupied:
                color = (0, 255, 0) # Xanh - Trống
                counter += 1
            else:
                color = (0, 0, 255) # Đỏ - Có xe
                
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