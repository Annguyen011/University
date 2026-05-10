import cv2
import numpy as np
import pickle
import os

def preprocess_full_frame(frame):
    """Tiền xử lý toàn bộ khung hình để tối ưu tốc độ tính toán (Thay vì xử lý từng ô)"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 1)
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 25, 16)
    return thresh

def main():
    """Khối thực thi chính: Đọc video, nhận diện và hiển thị"""
    # Lấy đường dẫn thư mục chứa file script hiện tại
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
    full_pixels = width * height
    empty_threshold = 0.22
    font = cv2.FONT_HERSHEY_COMPLEX_SMALL

    print("Bắt đầu nhận diện bằng Traditional CV. Nhấn ESC để thoát.")

    while True:
        # Lặp lại video nếu hết
        if cap.get(cv2.CAP_PROP_POS_FRAMES) == cap.get(cv2.CAP_PROP_FRAME_COUNT):
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
        ret, frame = cap.read()
        if not ret: break
        
        overlay = frame.copy()
        counter = 0
        
        # Tiền xử lý 1 lần cho cả frame
        img_thresh = preprocess_full_frame(frame)
        
        # Duyệt qua từng vị trí bãi đỗ
        for pos in park_positions:
            x, y = pos
            # Cắt ảnh nhị phân đã qua xử lý
            img_crop = img_thresh[y:y+height, x:x+width]
            
            # Đếm pixel trắng và tính tỷ lệ
            count = cv2.countNonZero(img_crop)
            ratio = count / full_pixels
            
            # Phân loại
            if ratio < empty_threshold:
                color = (0, 255, 0)  # Xanh - Trống
                counter += 1
            else:
                color = (0, 0, 255)  # Đỏ - Có xe
                
            cv2.rectangle(overlay, pos, (pos[0]+width, pos[1]+height), color, -1)
            cv2.putText(overlay, f"{ratio:.2f}", (x, y + height - 2), font, 0.6, (255, 255, 255), 1)
            
        # Tạo hiệu ứng trong suốt
        alpha = 0.7
        frame_new = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)
        
        # Hiển thị số lượng chỗ trống
        cv2.rectangle(frame_new, (0, 0), (220, 60), (255, 0, 255), -1)
        cv2.putText(frame_new, f"{counter}/{len(park_positions)}", (20, 45), font, 2, (255, 255, 255), 2)
        
        cv2.imshow('Traditional CV - Parking Space Counting', frame_new)
        if cv2.waitKey(1) & 0xFF == 27:
            break
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()