#include <LiquidCrystal.h>

LiquidCrystal lcd(12, 11, 5, 4, 3, 2);

void setup() {
  lcd.begin(16, 2);
  lcd.setCursor(0, 0);
  lcd.print("Nhom robocha"); 
}

void loop() {
  // Lệnh for này làm màn hình dịch sang TRÁI 16 lần
  for (int i = 0; i < 16; i++) {
    lcd.scrollDisplayLeft(); // Đẩy chữ sang trái 1 ô
    delay(300);              // Chờ 0.3 giây để mắt nhìn kịp
  }
  
  // Lệnh for này làm màn hình dịch sang PHẢI 16 lần (để quay về)
  for (int i = 0; i < 16; i++) {
    lcd.scrollDisplayRight(); // Đẩy chữ sang phải 1 ô
    delay(300);               // Chờ 0.3 giây
  }
}