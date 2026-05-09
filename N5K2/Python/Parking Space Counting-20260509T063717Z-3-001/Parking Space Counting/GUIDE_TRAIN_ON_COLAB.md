# Hướng dẫn Huấn Luyện (Train) Mô hình Đếm Chỗ Đỗ Xe trên Google Colab

Tài liệu này hướng dẫn bạn cách huấn luyện một mô hình AI (YOLOv8) để tự động nhận diện chỗ đỗ xe trống/có xe bằng Google Colab (miễn phí, không cần máy mạnh).

---

## Phần 1: Chuẩn bị Dữ liệu (Quan trọng nhất)

Máy tính cần học từ ví dụ. Bạn cần chuẩn bị ảnh và "đáp án" (vẽ khung quanh xe/chỗ trống).

1.  **Thu thập ảnh:** Cắt khoảng 50-100 tấm ảnh từ các video bãi đỗ xe khác nhau (dùng tool chụp màn hình hoặc code Python cắt frame).
2.  **Gán nhãn (Labeling):**
    *   Truy cập [Roboflow](https://roboflow.com/) (Tạo tài khoản miễn phí).
    *   Tạo Project mới -> Upload ảnh lên.
    *   Vẽ khung hình chữ nhật và đặt tên (class):
        *   `occupied`: Cho xe đang đỗ.
        *   `empty`: Cho ô đang trống (vạch kẻ). **(Lưu ý: Phần này khó, cần vẽ chính xác vạch kẻ)**.
    *   Sau khi vẽ xong, bấm **Generate Version**.
    *   Chọn **Export Dataset** -> Chọn Format: **YOLOv8** -> Chọn **"Show Download Code"** (lưu lại đoạn code này để dùng ở Bước 2).

---

## Phần 2: Huấn Luyện trên Google Colab

1.  Truy cập [Google Colab](https://colab.research.google.com/).
2.  Tạo **New Notebook**.
3.  Trên menu, chọn **Runtime** -> **Change runtime type** -> Chọn **T4 GPU** -> Save.
4.  Copy lần lượt các đoạn code sau vào từng ô (cell) và bấm nút Play (tam giác) để chạy.

### Bước 2.1: Cài đặt thư viện YOLOv8
```python
# Cài đặt thư viện Ultralytics (chứa YOLO)
!pip install ultralytics
from IPython import display
display.clear_output()
import ultralytics
ultralytics.checks()
```

### Bước 2.2: Tải dữ liệu về (Dùng code từ Roboflow)
Dán đoạn code bạn lấy được ở **Phần 1** vào đây. Nó sẽ trông giống như thế này:
```python
!mkdir datasets
%cd datasets
!pip install roboflow

from roboflow import Roboflow
rf = Roboflow(api_key="KEY_CUA_BAN")
project = rf.workspace("...").project("...")
version = project.version(1)
dataset = version.download("yolov8")
```

### Bước 2.3: Bắt đầu Huấn luyện (Training)
Đây là bước máy học, sẽ mất từ 30 phút - 2 tiếng tùy số lượng ảnh.
```python
%cd /content
# Train model YOLOv8 Nano (bản nhẹ nhất, chạy nhanh)
# epochs=100: Học 100 lần. imgsz=640: Kích thước ảnh.
!yolo task=detect mode=train model=yolov8n.pt data=/content/datasets/QUAN_TRONG/data.yaml epochs=100 imgsz=640
```
*(Lưu ý: Thay `QUAN_TRONG` bằng tên thư mục dataset vừa tải về ở Bước 2.2, thường Colab sẽ hiện bên trái)*

### Bước 2.4: Tải "Trí tuệ" về máy
Sau khi chạy xong, file kết quả sẽ nằm ở đường dẫn kiểu: `runs/detect/train/weights/best.pt`.
```python
from google.colab import files
# Tải file model tốt nhất về máy tính của bạn
files.download('/content/runs/detect/train/weights/best.pt')
```

---

## Phần 3: Chạy thử trên máy của bạn (Local)

Sau khi có file `best.pt`, copy nó vào thư mục dự án `Parking Space Counting`.

Tạo một file Python mới, ví dụ `run_yolo.py`:

```python
from ultralytics import YOLO
import cv2

# Load model bạn vừa train
model = YOLO("best.pt")

# Mở video
cap = cv2.VideoCapture("input/parking.mp4")

while True:
    ret, frame = cap.read()
    if not ret: break

    # Cho model nhận diện
    results = model(frame)

    # Hiển thị kết quả (YOLO tự vẽ khung)
    res_plotted = results[0].plot()

    cv2.imshow("Ket qua", res_plotted)
    if cv2.waitKey(1) == 27: # Esc để thoát
        break

cap.release()
cv2.destroyAllWindows()
```
