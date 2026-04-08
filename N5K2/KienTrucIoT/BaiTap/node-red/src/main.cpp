#include <Arduino.h>

#define LED1    18
#define LED2    19
#define PIR_PIN 23

volatile bool special_mode = false;
unsigned long special_mode_start = 0;
unsigned long last_blink_normal = 0;
unsigned long last_blink_special = 0;
bool normal_state = false;
int led1_count = 0;
int led2_count = 0;
bool led1_current = false;
bool led2_current = false;
int current_step = 0;

void TaskBlinkControl(void *pvParameters);
void TaskSensorMonitor(void *pvParameters);

void setup() {
  Serial.begin(9600);

  pinMode(LED1, OUTPUT);
  pinMode(LED2, OUTPUT);
  pinMode(PIR_PIN, INPUT);

  xTaskCreate(
    TaskBlinkControl,
    "Task_BlinkControl",
    2048,
    NULL,
    1,
    NULL
  );

  xTaskCreate(
    TaskSensorMonitor,
    "Task_SensorMonitor",
    2048,
    NULL,
    2,
    NULL
  );
}

void loop() {
  vTaskDelay(pdMS_TO_TICKS(1000));
}

void TaskBlinkControl(void *pvParameters) {
  unsigned long current_time;
  
  for (;;) {
    current_time = millis();
    
    if (special_mode == false) {
      if (current_time - last_blink_normal >= 500) {
        last_blink_normal = current_time;
        normal_state = !normal_state;
        digitalWrite(LED1, normal_state);
        digitalWrite(LED2, normal_state);
      }
    }
    else {
      unsigned long elapsed = current_time - special_mode_start;
      
      if (elapsed >= 30000) {
        special_mode = false;
        digitalWrite(LED1, LOW);
        digitalWrite(LED2, LOW);
        normal_state = false;
        last_blink_normal = current_time;
        led1_count = 0;
        led2_count = 0;
        current_step = 0;
        Serial.println("Tro lai che do binh thuong");
      }
      else {
        if (current_time - last_blink_special >= 500) {
          last_blink_special = current_time;
          
          if (current_step == 0) {
            digitalWrite(LED1, HIGH);
            digitalWrite(LED2, HIGH);
            Serial.println("Buoc 1: LED1 ON, LED2 ON");
            current_step = 1;
          }
          else if (current_step == 1) {
            digitalWrite(LED1, LOW);
            digitalWrite(LED2, LOW);
            Serial.println("Buoc 2: LED1 OFF, LED2 OFF");
            current_step = 2;
          }
          else if (current_step == 2) {
            digitalWrite(LED1, LOW);
            digitalWrite(LED2, HIGH);
            Serial.println("Buoc 3: LED1 OFF, LED2 ON");
            current_step = 3;
          }
          else if (current_step == 3) {
            digitalWrite(LED1, LOW);
            digitalWrite(LED2, LOW);
            Serial.println("Buoc 4: LED1 OFF, LED2 OFF");
            current_step = 0;
          }
        }
      }
    }
    
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

void TaskSensorMonitor(void *pvParameters) {
  bool last_motion = false;
  
  for (;;) {
    bool motion = digitalRead(PIR_PIN);
    
    if (motion == HIGH && last_motion == LOW && special_mode == false) {
      special_mode = true;
      special_mode_start = millis();
      last_blink_special = millis();
      led1_count = 0;
      led2_count = 0;
      current_step = 0;
      digitalWrite(LED1, LOW);
      digitalWrite(LED2, LOW);
      Serial.println("Phat hien chuyen dong - LED1 nhay 1 lan, LED2 nhay 2 lan trong 30s");
    }
    
    last_motion = motion;
    vTaskDelay(pdMS_TO_TICKS(50));
  }
}
//Chế độ bình thường: LED1 và LED2 nháy cùng chu kỳ 0.5s
//Khi có cảm biến:
//Chu kỳ nháy 0.5s cho cả 2 LED
//LED1 nháy 1 lần: Sáng 0.5s → Tắt 0.5s
//LED2 nháy 2 lần: Sáng 0.5s → Tắt 0.5s → Sáng 0.5s → Tắt 0.5s
//Lặp lại trong 30s
//Sau 30s: Trở về chế độ bình thường

//Led 1,2 cùng nháy chung chu kỳ 0.5s, khi có giá trị từ cảm biến , led 1 nháy 1s, led 2 nháy 2s, nháy trong vòng 30s và trở về ban đầu