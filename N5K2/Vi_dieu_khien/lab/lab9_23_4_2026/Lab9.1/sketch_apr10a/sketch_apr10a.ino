#include <Servo.h>

Servo myServo;  // Đặt tên cho Servo
const int potPin = A0; // Chân đọc biến trở
int val;        // Biến lưu giá trị đọc được

void setup() {
  myServo.attach(9); // Servo nối chân 9
}

void loop() {
  val = analogRead(potPin);            // Đọc biến trở (trả về 0 - 1023)
  int angle = map(val, 0, 1023, 0, 180); // Chuyển tỉ lệ sang 0 - 180 độ
  
  myServo.write(angle);                // Ra lệnh cho Servo quay theo góc này
  delay(15);                           // Chờ một chút để Servo kịp quay
}