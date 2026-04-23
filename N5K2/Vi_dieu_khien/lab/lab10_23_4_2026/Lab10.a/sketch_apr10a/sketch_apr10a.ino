#include <LiquidCrystal.h> // Gọi thư viện để dùng màn hình LCD

// Khai báo các chân cắm: RS, E, D4, D5, D6, D7
LiquidCrystal lcd(12, 11, 5, 4, 3, 2);

void setup() {
  lcd.begin(16, 2); // Khởi động màn hình cỡ 16 cột, 2 dòng
  
  lcd.setCursor(0, 0); // Đưa con trỏ nhấp nháy về: Cột 1 (số 0), Dòng 1 (số 0)
  lcd.print("An Nguyen Van"); 
}

void loop() {
  // Bài này chỉ hiện chữ 1 lần lúc bật máy, nên phần loop để trống
}