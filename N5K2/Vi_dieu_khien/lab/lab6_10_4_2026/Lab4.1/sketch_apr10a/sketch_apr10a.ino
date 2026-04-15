// Khai báo mảng chứa 10 chân kết nối với LED
int ledPins[] = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11};
int numLeds = 10; // Tổng số LED

void setup() {
  // Cài đặt tất cả 10 chân là OUTPUT
  for (int i = 0; i < numLeds; i++) {
    pinMode(ledPins[i], OUTPUT);
  }
}

void loop() {
  // Vòng lặp chạy từ LED 1 đến 10 (từ trái sang phải)
  for (int i = 0; i < numLeds; i++) {
    digitalWrite(ledPins[i], HIGH); // Bật LED
    delay(100);                     // Đợi 0.1 giây
    digitalWrite(ledPins[i], LOW);  // Tắt LED
  }
  
  // Vòng lặp chạy ngược lại từ LED 9 về LED 2 (tránh lặp lại ở 2 đầu)
  for (int i = numLeds - 2; i > 0; i--) {
    digitalWrite(ledPins[i], HIGH);
    delay(100);
    digitalWrite(ledPins[i], LOW);
  }
}