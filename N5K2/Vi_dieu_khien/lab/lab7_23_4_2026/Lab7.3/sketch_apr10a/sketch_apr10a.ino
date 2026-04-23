const int buttonPin = 2; // Chân số 2 nối với nút bấm
const int ledPin = 13;   // Chân số 13 nối với đèn LED

int lastButtonState = LOW; // Trạng thái nút bấm lúc trước

void setup() {
  pinMode(ledPin, OUTPUT);  // Khai báo chân LED là đầu ra
  pinMode(buttonPin, INPUT);// Khai báo chân nút bấm là đầu vào
}

void loop() {
  int buttonState = digitalRead(buttonPin); // Đọc xem nút có được bấm không

  // Nếu trạng thái nút bị thay đổi
  if (buttonState != lastButtonState) {
    delay(50); // Chờ 50 mili-giây để chống nhiễu (Debounce)
    buttonState = digitalRead(buttonPin); // Đọc lại cho chắc chắn

    if (buttonState == HIGH) {
      digitalWrite(ledPin, HIGH); // Bật đèn
    } else {
      digitalWrite(ledPin, LOW);  // Tắt đèn
    }
  }
  lastButtonState = buttonState; // Lưu lại trạng thái nút bấm
}