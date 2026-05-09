import cv2
import os

# Create output folder
output_dir = 'input/frames'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Open video
cap = cv2.VideoCapture('input/parking.mp4')
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

print(f"Video FPS: {fps}")
print(f"Total Frames: {total_frames}")

# We want about 30 images total
# Calculate interval to skip frames
interval = int(total_frames / 30)

count = 0
saved_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
        
    if count % interval == 0:
        filename = f"{output_dir}/frame_{saved_count:03d}.jpg"
        cv2.imwrite(filename, frame)
        print(f"Saved: {filename}")
        saved_count += 1
        
    count += 1

cap.release()
print(f"\nDone! Saved {saved_count} images to '{output_dir}'.")
