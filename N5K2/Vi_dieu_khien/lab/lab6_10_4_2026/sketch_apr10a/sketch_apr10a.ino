int ledPin = 9; // 

void setup() { // [cite: 18]
  pinMode(ledPin, OUTPUT); // [cite: 19]
} // [cite: 20]

void loop() { // [cite: 21]
  digitalWrite(ledPin, HIGH); // [cite: 22]
  delay(1000); // [cite: 23]
  digitalWrite(ledPin, LOW); // [cite: 24]
  delay(1000); // [cite: 25]
} // [cite: 26]