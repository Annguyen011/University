#include <Arduino.h>         
#include <WiFi.h>
#include <PubSubClient.h>

// 1. THÔNG TIN MẠNG VÀ MÁY CHỦ (Đã được cập nhật)
const char* ssid = "Wifi";                     // Tên WiFi của bạn
const char* password = "1223334444";           // Mật khẩu WiFi của bạn
const char* mqtt_server = "192.168.102.15";    // Địa chỉ IP máy tính Node-RED

WiFiClient espClient;
PubSubClient client(espClient);

// 2. KHAI BÁO CHÂN CẮM ĐÈN LED
const int led1 = 18;
const int led2 = 19;
const int led3 = 21;

// Hàm kết nối WiFi
void setup_wifi() {
  Serial.begin(9600);
  delay(10);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

// Hàm nhận lệnh từ Node-RED để bật/tắt đèn
void callback(char* topic, byte* payload, unsigned int length) {
  // Đọc tin nhắn gửi tới
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  // Dùng số "1" để BẬT, "0" để TẮT
  if (String(topic) == "dieukhien/led18") {
    if (message == "1") digitalWrite(led1, HIGH);
    if (message == "0") digitalWrite(led1, LOW);
  }
  if (String(topic) == "dieukhien/led19") {
    if (message == "1") digitalWrite(led2, HIGH);
    if (message == "0") digitalWrite(led2, LOW);
  }
  if (String(topic) == "dieukhien/led21") {
    if (message == "1") digitalWrite(led3, HIGH);
    if (message == "0") digitalWrite(led3, LOW);
  }
}

// Hàm duy trì kết nối MQTT
void reconnect() {
  while (!client.connected()) {
    if (client.connect("ESP32_NhaCuaToi")) {
      // Đăng ký nhận tin nhắn từ 3 kênh (topic) này
      client.subscribe("dieukhien/led18");
      client.subscribe("dieukhien/led19");
      client.subscribe("dieukhien/led21");
    } else {
      delay(5000);
    }
  }
}

void setup() {
  // Cài đặt các chân LED là đầu ra
  pinMode(led1, OUTPUT);
  pinMode(led2, OUTPUT);
  pinMode(led3, OUTPUT);

  setup_wifi();
  client.setServer(mqtt_server, 1883); // 1883 là cổng mặc định của MQTT
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop(); // Giữ cho MQTT luôn chạy
}