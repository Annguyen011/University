import cv2
import pickle
import os
import numpy as np
import matplotlib.pyplot as plt
from math import sqrt

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_PATH = os.path.join(SCRIPT_DIR, 'input', 'parking.mp4')
POSITIONS_PATH = os.path.join(SCRIPT_DIR, 'park_positions')

# Kích thước đồng bộ cho cả Picker và Counter
SPACE_WIDTH, SPACE_HEIGHT = 40, 23 
EMPTY_THRESHOLD = 0.22  
TOTAL_PIXELS = SPACE_WIDTH * SPACE_HEIGHT
FONT = cv2.FONT_HERSHEY_COMPLEX_SMALL

# --- Global Variables ---
park_positions = []
pt1_x, pt1_y, pt2_x, pt2_y = None, None, None, None
history = []

def load_positions():
    global park_positions
    if os.path.exists(POSITIONS_PATH):
        with open(POSITIONS_PATH, 'rb') as f:
            park_positions = pickle.load(f)
    else:
        park_positions = []

def save_positions():
    with open(POSITIONS_PATH, 'wb') as f:
        pickle.dump(park_positions, f)

def mouse_events(event, x, y, flag, param):
    """Xử lý sự kiện chuột cho chế độ thiết lập bãi đỗ"""
    global pt1_x, pt1_y, pt2_x, pt2_y, park_positions

    if event == cv2.EVENT_LBUTTONDOWN:
        pt1_x, pt1_y = x, y

    elif event == cv2.EVENT_LBUTTONUP:
        pt2_x, pt2_y = x, y
        parking_spaces = int((sqrt((pt2_x - pt1_x) ** 2 + (pt2_y - pt1_y) ** 2)) / SPACE_HEIGHT)
        if parking_spaces == 0:
            park_positions.append((x, y))
        else:
            for i in range(parking_spaces):
                park_positions.append((pt1_x, pt1_y + i * SPACE_HEIGHT))
        save_positions()

    if event == cv2.EVENT_RBUTTONDOWN:
        for i, position in enumerate(park_positions):
            x1, y1 = position
            if x1 < x < x1 + SPACE_WIDTH and y1 < y < y1 + SPACE_HEIGHT:
                park_positions.pop(i)
        save_positions()

def main():
    global park_positions
    load_positions()

    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"Lỗi: Không thể mở video tại {VIDEO_PATH}")
        return

    cv2.namedWindow('Parking Tracker', cv2.WINDOW_NORMAL)
    cv2.setWindowProperty('Parking Tracker', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.setMouseCallback('Parking Tracker', mouse_events)

    # Vào chế độ Edit ngay nếu file dữ liệu rỗng
    edit_mode = len(park_positions) == 0 

    success, first_frame = cap.read()
    if not success:
        return

    while True:
        if edit_mode:
            img = first_frame.copy()
            for pos in park_positions:
                cv2.rectangle(img, (pos[0], pos[1]), (pos[0] + SPACE_WIDTH, pos[1] + SPACE_HEIGHT), (255, 0, 255), 2)
            
            # Hướng dẫn trên màn hình
            cv2.putText(img, "EDIT MODE: Trai-Click -> Them | Phai-Click -> Xoa", (10, 30), FONT, 1.2, (0, 0, 255), 2)
            cv2.putText(img, "Nhan 'ENTER' de bat dau nhan dien", (10, 70), FONT, 1.2, (0, 0, 255), 2)
            cv2.imshow('Parking Tracker', img)
            
            key = cv2.waitKey(1) & 0xFF
            if key == 13 or key == 32:  # Enter hoặc Space
                edit_mode = False
            elif key == 27:  # ESC
                break
        else:
            if cap.get(cv2.CAP_PROP_POS_FRAMES) == cap.get(cv2.CAP_PROP_FRAME_COUNT):
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

            success, frame = cap.read()
            if not success:
                break

            img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            img_blur = cv2.GaussianBlur(img_gray, (3, 3), 1)
            img_thresh = cv2.adaptiveThreshold(img_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 16)

            empty_spots = 0
            for x, y in park_positions:
                # Chống crash khi vùng ảnh nằm ngoài khung hình
                if y + SPACE_HEIGHT <= frame.shape[0] and x + SPACE_WIDTH <= frame.shape[1]:
                    img_crop = img_thresh[y:y + SPACE_HEIGHT, x:x + SPACE_WIDTH]
                    count = cv2.countNonZero(img_crop)
                    ratio = count / TOTAL_PIXELS
                    
                    color = (0, 255, 0) if ratio < EMPTY_THRESHOLD else (0, 0, 255)
                    empty_spots += (1 if ratio < EMPTY_THRESHOLD else 0)

                    # Tối ưu ROI Blending: Vẽ đè trong suốt chỉ tại đúng tọa độ xe đỗ (tiết kiệm CPU)
                    roi = frame[y:y+SPACE_HEIGHT, x:x+SPACE_WIDTH]
                    colored_rect = np.full(roi.shape, color, dtype=np.uint8)
                    cv2.addWeighted(roi, 0.6, colored_rect, 0.4, 0, roi)
                    
                    cv2.rectangle(frame, (x, y), (x + SPACE_WIDTH, y + SPACE_HEIGHT), color, 1)
                    cv2.putText(frame, f"{ratio:.2f}", (x, y + SPACE_HEIGHT - 3), FONT, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            
            
            total_spots = len(park_positions)
            occupied_spots = total_spots - empty_spots
            history.append(occupied_spots) # Lưu lại số xe đang đỗ để làm báo cáo cuối
            
            # Hiển thị HUD thông thường
            cv2.rectangle(frame, (0, 0), (320, 80), (0, 0, 0), -1)
            cv2.putText(frame, f"Empty: {empty_spots}/{total_spots}", (10, 35), FONT, 1.5, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(frame, "Nhan 'e' de chinh sua baii do", (10, 70), FONT, 1, (255, 255, 0), 1, cv2.LINE_AA)
            
            cv2.imshow('Parking Tracker', frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('e') or key == ord('E'):
                edit_mode = True
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Reset video về frame đầu để vẽ mượt hơn
                success, first_frame = cap.read()
            elif key == 27:
                break

    cap.release()
    cv2.destroyAllWindows()

    # --- Hiển thị báo cáo tổng kết sau khi tắt video ---
    if history and len(park_positions) > 0:
        if HAS_MATPLOTLIB:
            plt.figure(figsize=(10, 5))
            plt.plot(history, label="So xe dang do", color="red", linewidth=2)
            plt.title("Bao cao: So luong xe trong bai theo thoi gian")
            plt.xlabel("Thoi gian (Frames)")
            plt.ylabel("So luong xe")
            plt.legend()
            plt.grid(True)
            
            # Lưu biểu đồ thành file ảnh tự động
            report_path = os.path.join(SCRIPT_DIR, 'report.png')
            plt.savefig(report_path, bbox_inches='tight')
            print(f"\n[Thanh cong] Bieu do da duoc luu tai: {report_path}\n")
            
            plt.show()
        else:
            print("Vui long cai dat thu vien matplotlib (pip install matplotlib) de xem bieu do thong ke cuoi cung.")

if __name__ == '__main__':
    main()