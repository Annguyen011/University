import cv2
import pickle
import os

# --- Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_PATH = os.path.join(SCRIPT_DIR, 'input', 'parking.mp4')
POSITIONS_PATH = os.path.join(SCRIPT_DIR, 'park_positions')

# Parking space parameters
SPACE_WIDTH, SPACE_HEIGHT = 40, 19
EMPTY_THRESHOLD = 0.22  # Ratio of non-zero pixels to be considered empty
TOTAL_PIXELS = SPACE_WIDTH * SPACE_HEIGHT
FONT = cv2.FONT_HERSHEY_COMPLEX_SMALL

# --- Main Functions ---

def check_parking_spaces(img_processed, park_positions, overlay):
    """
    Checks each parking spot, draws on the overlay, and returns the count of empty spots.
    """
    empty_spots = 0

    for x, y in park_positions:
        img_crop = img_processed[y:y + SPACE_HEIGHT, x:x + SPACE_WIDTH]
        count = cv2.countNonZero(img_crop)
        ratio = count / TOTAL_PIXELS

        if ratio < EMPTY_THRESHOLD:
            color = (0, 255, 0)
            empty_spots += 1
        else:
            color = (0, 0, 255)

        # Draw parking spot overlay
        cv2.rectangle(overlay, (x, y), (x + SPACE_WIDTH, y + SPACE_HEIGHT), color, -1)
        cv2.putText(overlay, f"{ratio:.2f}", (x + 2, y + SPACE_HEIGHT - 4), FONT, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    
    return empty_spots

# --- Main Execution ---

cap = cv2.VideoCapture(VIDEO_PATH)

with open(POSITIONS_PATH, 'rb') as f:
    park_positions = pickle.load(f)

cv2.namedWindow('Parking Space Counter', cv2.WINDOW_NORMAL)
cv2.setWindowProperty('Parking Space Counter', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

while True:
    # Loop video if it ends
    if cap.get(cv2.CAP_PROP_POS_FRAMES) == cap.get(cv2.CAP_PROP_FRAME_COUNT):
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    success, frame = cap.read()
    if not success:
        break

    # Create overlay and process the frame
    overlay = frame.copy()
    img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    img_blur = cv2.GaussianBlur(img_gray, (3, 3), 1)
    img_thresh = cv2.adaptiveThreshold(img_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 16)

    # Get empty spot count and update overlay
    empty_count = check_parking_spaces(img_thresh, park_positions, overlay)

    # Blend overlay with the original frame
    alpha = 0.7
    blended_frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    # Display the count of empty spots
    w, h = 220, 60
    cv2.rectangle(blended_frame, (0, 0), (w, h), (255, 0, 255), -1)
    cv2.putText(blended_frame, f"{empty_count}/{len(park_positions)}", (int(w/10), int(h*3/4)), FONT, 2, (255, 255, 255), 2, cv2.LINE_AA)

    cv2.imshow('Parking Space Counter', blended_frame)

    if cv2.waitKey(1) & 0xFF == 27:  # Press ESC to exit
        break

cap.release()
cv2.destroyAllWindows()