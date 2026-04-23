const int buttonPin = 2; // Chân nối nút bấm
const int ledPin = 13;   // Chân nối đèn LED

int lastButtonState = LOW;
unsigned long pressTime = 0;   
unsigned long releaseTime = 0; 

void setup() {
  pinMode(ledPin, OUTPUT);
  pinMode(buttonPin, INPUT);
  Serial.begin(9600); 
}

void loop() {
  int buttonState = digitalRead(buttonPin);

  // 1. Khi bắt đầu nhấn nút xuống
  if (buttonState == HIGH && lastButtonState == LOW) {
    delay(50); // Chống nhiễu
    pressTime = millis(); // Ghi lại lúc bắt đầu nhấn
  }

  // 2. Khi nhả nút ra
  if (buttonState == LOW && lastButtonState == HIGH) {
    delay(50); 
    releaseTime = millis(); // Ghi lại lúc nhả tay

    long pressDuration = releaseTime - pressTime; // Tính thời gian giữ nút

    if (pressDuration > 1000) { 
      // NẾU NHẤN DÀI (Hơn 1 giây)
      Serial.println("Bấm Dài -> BẬT ĐÈN");
      digitalWrite(ledPin, HIGH); // Lệnh làm đèn sáng
    } 
    else if (pressDuration > 50) {
      // NẾU NHẤN NGẮN
      Serial.println("Bấm Ngắn -> TẮT ĐÈN");
      digitalWrite(ledPin, LOW);  // Lệnh làm đèn tắt
    }
  }
  
  lastButtonState = buttonState;
}