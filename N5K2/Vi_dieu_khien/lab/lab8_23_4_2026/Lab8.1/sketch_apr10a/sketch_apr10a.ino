#include <Servo.h> // Khai báo dùng thư viện có sẵn cho Servo

Servo myServo;  // Tạo một "cái tên" cho động cơ Servo của mình
int pos = 0;    // Tạo một bộ nhớ để lưu góc quay hiện tại, bắt đầu từ 0 độ

void setup() {
  myServo.attach(9); // Khai báo Servo đang được cắm ở chân tín hiệu số 9
}

void loop() {
  // Lệnh for này giúp động cơ quay từ 0 độ đến 180 độ
  for (pos = 0; pos <= 180; pos += 1) { 
    myServo.write(pos); // Ra lệnh cho Servo quay đến góc 'pos'
    
    // ĐÂY LÀ CHỖ ĐIỀU CHỈNH TỐC ĐỘ:
    // Chờ 15 mili-giây rồi mới quay tiếp 1 độ. 
    // Số này càng LỚN thì Servo quay càng CHẬM.
    delay(15); 
  }
  
  // Lệnh for này giúp động cơ quay ngược lại từ 180 độ về 0 độ
  for (pos = 180; pos >= 0; pos -= 1) { 
    myServo.write(pos); 
    delay(15); // Thay đổi số 15 này để thấy tốc độ quay về thay đổi
  }
}