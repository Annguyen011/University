#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>
#include <Adafruit_VL53L0X.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL345_U.h>
#define PIN_LED_XANH 18
#define PIN_LED_DO 19

#define NGUONG_KHOANG_CACH  150
#define NGUONG_GIA_TOC      5.0f
#define KHOANG_CACH_TOI_DA  1200

#define CHU_KY_CAM_BIEN_MS 25
#define CHU_KY_NHAY_MS 100
#define CHU_KY_GIAM_SAT_MS 3000

#define I2C_SDA 21
#define I2C_SCL 22
#define I2C_TOC_DO 400000UL

Adafruit_SH1106G display(128, 64, &Wire, -1);
Adafruit_VL53L0X  lox;
Adafruit_ADXL345_Unified accel(12345);

struct DuLieuCamBien {
  uint16_t khoangCach;
  int8_t   giaTocX;
  int8_t   giaTocY;
  int8_t   giaTocZ;
  bool     nguyHiem;
};

SemaphoreHandle_t mutexI2C    = nullptr;
QueueHandle_t     hopThu      = nullptr;

volatile bool     canhBaoNguyHiem = false;

volatile uint32_t nhipCamBien = 0;
volatile uint32_t nhipOLED    = 0;
volatile uint32_t nhipLED     = 0;

TaskHandle_t handleCamBien = nullptr;
TaskHandle_t handleOLED    = nullptr;
TaskHandle_t handleLED     = nullptr;

static void printFixed(const char* str, uint8_t width) {
  uint8_t len = strlen(str);
  display.print(str);
  for (uint8_t i = len; i < width; i++) display.print(' ');
}

void TaskDocCamBien(void* pv) {
  DuLieuCamBien duLieu = {};
  VL53L0X_RangingMeasurementData_t measure;
  sensors_event_t event;

  for (;;) {
    xSemaphoreTake(mutexI2C, portMAX_DELAY);

    lox.rangingTest(&measure, false);
    accel.getEvent(&event);

    xSemaphoreGive(mutexI2C);

    duLieu.khoangCach = (measure.RangeStatus != 4)
                          ? measure.RangeMilliMeter
                          : 9999;

    duLieu.giaTocX = (int8_t)event.acceleration.x;
    duLieu.giaTocY = (int8_t)event.acceleration.y;
    duLieu.giaTocZ = (int8_t)event.acceleration.z;

    duLieu.nguyHiem = (duLieu.khoangCach < NGUONG_KHOANG_CACH)
                      || (abs(duLieu.giaTocX) > (int8_t)NGUONG_GIA_TOC)
                      || (abs(duLieu.giaTocY) > (int8_t)NGUONG_GIA_TOC);

    canhBaoNguyHiem = duLieu.nguyHiem;

    xQueueOverwrite(hopThu, &duLieu);

    nhipCamBien++;
    vTaskDelay(pdMS_TO_TICKS(CHU_KY_CAM_BIEN_MS));
  }
}

void TaskHienThiOLED(void* pv) {
  DuLieuCamBien cur  = {};
  DuLieuCamBien prev = {9998, 0, 0, 0, false};

  display.clearDisplay();
  display.setTextColor(SH110X_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 30);  display.print("Cach:");
  display.setCursor(0, 42);  display.print("X:");
  display.setCursor(43, 42); display.print("Y:");
  display.setCursor(86, 42); display.print("Z:");
  display.display();

  char buf[16];

  for (;;) {
    if (xQueueReceive(hopThu, &cur, pdMS_TO_TICKS(200)) != pdPASS) continue;

    bool dirty = false;

    if (cur.nguyHiem != prev.nguyHiem) {
      display.setTextSize(2);
      display.setTextColor(SH110X_WHITE, SH110X_BLACK);
      display.setCursor(0, 0);
      display.print(cur.nguyHiem ? "VA CHAM! " : "AN TOAN  ");
      dirty = true;
    }

    if (cur.khoangCach != prev.khoangCach) {
      display.setTextSize(1);
      display.setTextColor(SH110X_WHITE, SH110X_BLACK);
      display.setCursor(30, 30);
      if (cur.khoangCach > KHOANG_CACH_TOI_DA) {
        printFixed("Qua xa    ", 9);
      } else {
        snprintf(buf, sizeof(buf), "%4dmm", cur.khoangCach);
        display.print(buf);
      }
      dirty = true;
    }

    if (cur.giaTocX != prev.giaTocX || cur.giaTocY != prev.giaTocY || cur.giaTocZ != prev.giaTocZ) {
      display.setTextSize(1);
      display.setTextColor(SH110X_WHITE, SH110X_BLACK);

      display.setCursor(13, 42);
      snprintf(buf, sizeof(buf), "%-4d", cur.giaTocX); display.print(buf);

      display.setCursor(56, 42);
      snprintf(buf, sizeof(buf), "%-4d", cur.giaTocY); display.print(buf);

      display.setCursor(99, 42);
      snprintf(buf, sizeof(buf), "%-4d", cur.giaTocZ); display.print(buf);

      dirty = true;
    }

    if (dirty) {
      xSemaphoreTake(mutexI2C, portMAX_DELAY);
      display.display();
      xSemaphoreGive(mutexI2C);
      nhipOLED++;
    }

    prev = cur;
  }
}

void TaskDieuKhienLED(void* pv) {
  for (;;) {
    if (canhBaoNguyHiem) {
      digitalWrite(PIN_LED_XANH, LOW);
      digitalWrite(PIN_LED_DO, HIGH);
      vTaskDelay(pdMS_TO_TICKS(CHU_KY_NHAY_MS));
      digitalWrite(PIN_LED_DO, LOW);
      vTaskDelay(pdMS_TO_TICKS(CHU_KY_NHAY_MS));
    } else {
      digitalWrite(PIN_LED_XANH, HIGH);
      digitalWrite(PIN_LED_DO, LOW);
      vTaskDelay(pdMS_TO_TICKS(50));
    }
    nhipLED++;
  }
}

void TaskGiamSat(void* pv) {
  uint32_t prevCamBien = 0, prevOLED = 0, prevLED = 0;

  for (;;) {
    vTaskDelay(pdMS_TO_TICKS(CHU_KY_GIAM_SAT_MS));

    Serial.printf("\n[GIAM SAT] Heap: %u bytes\n", xPortGetFreeHeapSize());
    Serial.printf("  CamBien : %s\n", (nhipCamBien != prevCamBien) ? "OK" : "!!! TREO !!!");
    Serial.printf("  OLED    : %s\n", (nhipOLED    != prevOLED)    ? "OK" : "Cho du lieu");
    Serial.printf("  LED     : %s\n", (nhipLED     != prevLED)     ? "OK" : "!!! TREO !!!");

    Serial.printf("  Stack CamBien: %u words free\n", uxTaskGetStackHighWaterMark(handleCamBien));
    Serial.printf("  Stack OLED   : %u words free\n", uxTaskGetStackHighWaterMark(handleOLED));
    Serial.printf("  Stack LED    : %u words free\n", uxTaskGetStackHighWaterMark(handleLED));

    prevCamBien = nhipCamBien;
    prevOLED    = nhipOLED;
    prevLED     = nhipLED;
  }
}

void setup() {
  Serial.begin(115200);

  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(I2C_TOC_DO);

  mutexI2C = xSemaphoreCreateMutex();
  if (!mutexI2C) { Serial.println("Loi tao Mutex!"); while (1); }

  if (!display.begin(0x3C, true)) { Serial.println("Loi OLED!"); while (1); }
  if (!lox.begin())               { Serial.println("Loi VL53L0X!"); while (1); }
  if (!accel.begin())             { Serial.println("Loi ADXL345!"); while (1); }

  lox.setMeasurementTimingBudgetMicroSeconds(20000);

  accel.setRange(ADXL345_RANGE_4_G);
  accel.setDataRate(ADXL345_DATARATE_100_HZ);

  pinMode(PIN_LED_XANH, OUTPUT);
  pinMode(PIN_LED_DO, OUTPUT);

  hopThu = xQueueCreate(1, sizeof(DuLieuCamBien));
  if (!hopThu) { Serial.println("Loi tao Queue!"); while (1); }

  xTaskCreatePinnedToCore(TaskDocCamBien, "CamBien", 4096, nullptr, 3, &handleCamBien, 0);

  xTaskCreatePinnedToCore(TaskHienThiOLED, "OLED",    4096, nullptr, 2, &handleOLED,    1);
  xTaskCreatePinnedToCore(TaskDieuKhienLED,"LED",     2048, nullptr, 1, &handleLED,     1);
  xTaskCreatePinnedToCore(TaskGiamSat,    "GiamSat",  2048, nullptr, 3, nullptr,        1);

  Serial.println("He thong khoi dong thanh cong!");
}

void loop() {
  vTaskDelay(portMAX_DELAY);
}