#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/semphr.h>
#include <freertos/queue.h>

#define LED_1_PIN 18
#define LED_2_PIN 19

QueueHandle_t dataQueue;

void taskLedBlinker(void *pvParameters) {
  uint8_t ledPin = *(uint8_t*)pvParameters;
  uint32_t blinkCount;

  for (;;) {
    if (xQueueReceive(dataQueue, &blinkCount, portMAX_DELAY) == pdTRUE) {
      for (uint32_t i = 0; i < blinkCount; i++) {
        digitalWrite(ledPin, HIGH);
        vTaskDelay(pdMS_TO_TICKS(250));
        digitalWrite(ledPin, LOW);
        vTaskDelay(pdMS_TO_TICKS(250));
      }
    }
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(LED_1_PIN, OUTPUT);
  pinMode(LED_2_PIN, OUTPUT);

  dataQueue = xQueueCreate(5, sizeof(uint32_t));
  
  if (dataQueue == NULL) {
    while(1);
  }

  for (uint32_t i = 5; i <= 9; i++) {
    if (xQueueSend(dataQueue, &i, pdMS_TO_TICKS(100)) != pdPASS) {
      Serial.println("Dont send data to queue");
    }
  }

  static uint8_t led1_pin = LED_1_PIN;
  static uint8_t led2_pin = LED_2_PIN;

  xTaskCreate(taskLedBlinker, "LED 1 Blinker", 2048, &led1_pin, 2, NULL);
  xTaskCreate(taskLedBlinker, "LED 2 Blinker", 2048, &led2_pin, 2, NULL);
  
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n'); 
    input.trim(); 
    
    if (input.length() > 0) {
      uint32_t newBlinkCount = input.toInt(); 
      
      if (newBlinkCount > 0) {
        if (xQueueSend(dataQueue, &newBlinkCount, pdMS_TO_TICKS(100)) == pdPASS) {
          Serial.printf("nap so %u vao hang doi\n", newBlinkCount);
        } else {
          Serial.println("khong nap duoc");
        }
      } else {
        Serial.println("nhap so nguyen");
      }
    }
  }
  
  vTaskDelay(pdMS_TO_TICKS(50));
}