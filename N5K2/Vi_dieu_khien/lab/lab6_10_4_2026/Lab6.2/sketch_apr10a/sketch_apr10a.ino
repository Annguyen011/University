int ledPins[] = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11};
int numLeds = 10;

void setup() {
  for (int i = 0; i < numLeds; i++) {
    pinMode(ledPins[i], OUTPUT);
  }
}

void loop() {
  // Làm sáng dần tất cả các LED
  for (int brightness = 0; brightness <= 255; brightness += 5) {
    for (int i = 0; i < numLeds; i++) {
      analogWrite(ledPins[i], brightness);
    }
    delay(30); // Độ trễ để mắt người kịp thấy hiệu ứng
  }
  
  // Làm tối dần tất cả các LED
  for (int brightness = 255; brightness >= 0; brightness -= 5) {
    for (int i = 0; i < numLeds; i++) {
      analogWrite(ledPins[i], brightness);
    }
    delay(30);
  }
}