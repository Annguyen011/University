#include <LiquidCrystal.h>

LiquidCrystal lcd(12, 11, 5, 4, 3, 2);

void setup() {
  lcd.begin(16, 2); 
  
  // 1. In chữ "Hello"
  lcd.setCursor(4, 0); // Vị trí thứ 5 (ghi là 4), Dòng 1 (ghi là 0)
  lcd.print("Hello");
  
  // 2. In tên của bạn
  lcd.setCursor(0, 1); // Vị trí thứ 1 (ghi là 0), Dòng 2 (ghi là 1)
  lcd.print("An Van Nguyen"); 
}

void loop() {
}