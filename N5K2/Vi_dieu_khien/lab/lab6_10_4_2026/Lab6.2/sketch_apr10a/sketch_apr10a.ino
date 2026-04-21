#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>
#include <Adafruit_VL53L0X.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL345_U.h>

// ==========================================
// CẤU HÌNH HỆ THỐNG - Chỉnh tại đây
// ==========================================
#define PIN_LED_XANH        18
#define PIN_LED_DO          19
#define DO_SANG             15        // PWM 0-255

#define NGUONG_KHOANG_CACH  150       // mm - < giá trị này = nguy hiểm
#define NGUONG_GIA_TOC      5.0f      // m/s² - > giá trị này = xóc mạnh
#define KHOANG_CACH_TOI_DA  1200      // mm - > giá trị này hiển thị "Qua xa"

#define CHU_KY_CAM_BIEN_MS  25        // 40Hz - phản hồi nhanh
#define CHU_KY_NHAY_MS      100       // Nhấp nháy khi nguy hiểm
#define CHU_KY_GIAM_SAT_MS  3000

#define I2C_SDA             21
#define I2C_SCL             22
#define I2C_TOC_DO          400000UL  // 400kHz Fast Mode

// ==========================================
// KHAI BÁO PHẦN CỨNG
// ==========================================
Adafruit_SH1106G display(128, 64, &Wire, -1);
Adafruit_VL53L0X  lox;
Adafruit_ADXL345_Unified accel(12345);

// ==========================================
// CẤU TRÚC DỮ LIỆU
// ==========================================
struct DuLieuCamBien {
  uint16_t khoangCach;
  int8_t   giaTocX;   // Làm tròn 1 chữ số để so sánh dirty check
  int8_t   giaTocY;
  int8_t   giaTocZ;
  bool     nguyHiem;
};

// ==========================================
// BIẾN ĐỒNG BỘ
// ==========================================
SemaphoreHandle_t mutexI2C   = nullptr;  // Bảo vệ bus I2C dùng chung
QueueHandle_t     hopThu     = nullptr;  // Queue 1 slot - luôn lấy frame mới nhất

volatile bool     canhBaoNguyHiem = false;

// Watchdog counters
volatile uint32_t nhipCamBien = 0;
volatile uint32_t nhipOLED    = 0;
volatile uint32_t nhipLED     = 0;

TaskHandle_t handleCamBien = nullptr;
TaskHandle_t handleOLED    = nullptr;
TaskHandle_t handleLED     = nullptr;

// ==========================================
// TIỆN ÍCH: In chuỗi cố định chiều dài
// Tránh ký tự thừa từ lần in trước
// ==========================================
static void printFixed(const char* str, uint8_t width) {
  uint8_t len = strlen(str);
  display.print(str);
  for (uint8_t i = len; i < width; i++) display.print(' ');
}

// ==========================================
// TASK 1: ĐỌC CẢM BIẾN - Core 0, Priority 3
// ==========================================
void TaskDocCamBien(void* pv) {
  DuLieuCamBien duLieu = {};
  VL53L0X_RangingMeasurementData_t measure;
  sensors_event_t event;

  for (;;) {
    // Lấy mutex trước khi dùng I2C
    xSemaphoreTake(mutexI2C, portMAX_DELAY);

    lox.rangingTest(&measure, false);
    accel.getEvent(&event);

    xSemaphoreGive(mutexI2C);

    // Xử lý dữ liệu SAU KHI trả mutex (không chiếm bus)
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

    // Overwrite nếu queue đầy - OLED luôn nhận frame mới nhất
    xQueueOverwrite(hopThu, &duLieu);

    nhipCamBien++;
    vTaskDelay(pdMS_TO_TICKS(CHU_KY_CAM_BIEN_MS));
  }
}

// ==========================================
// TASK 2: OLED - Core 1, Priority 2
// Chỉ vẽ lại khi dữ liệu thay đổi
// ==========================================
void TaskHienThiOLED(void* pv) {
  DuLieuCamBien cur  = {};
  DuLieuCamBien prev = {9998, 0, 0, 0, false}; // Khác cur để vẽ lần đầu

  // Khung tĩnh - vẽ 1 lần, không bao giờ xóa
  display.clearDisplay();
  display.setTextColor(SH110X_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 30);  display.print("Cach:");
  display.setCursor(0, 42);  display.print("X:");
  display.setCursor(43, 42); display.print("Y:");
  display.setCursor(86, 42); display.print("Z:");
  display.setCursor(0, 54);  display.print("Heap:");
  display.display();

  char buf[16];

  for (;;) {
    if (xQueueReceive(hopThu, &cur, pdMS_TO_TICKS(200)) != pdPASS) continue;

    bool dirty = false;

    // --- Trạng thái (dòng lớn) ---
    if (cur.nguyHiem != prev.nguyHiem) {
      xSemaphoreTake(mutexI2C, portMAX_DELAY);
      display.setTextSize(2);
      display.setTextColor(SH110X_WHITE, SH110X_BLACK);
      display.setCursor(0, 0);
      display.print(cur.nguyHiem ? "VA CHAM! " : "AN TOAN  ");
      xSemaphoreGive(mutexI2C);
      dirty = true;
    }

    // --- Khoảng cách ---
    if (cur.khoangCach != prev.khoangCach) {
      xSemaphoreTake(mutexI2C, portMAX_DELAY);
      display.setTextSize(1);
      display.setTextColor(SH110X_WHITE, SH110X_BLACK);
      display.setCursor(30, 30);
      if (cur.khoangCach > KHOANG_CACH_TOI_DA) {
        printFixed("Qua xa   ", 9);
      } else {
        snprintf(buf, sizeof(buf), "%4dmm", cur.khoangCach);
        display.print(buf);
      }
      xSemaphoreGive(mutexI2C);
      dirty = true;
    }

    // --- Gia tốc ---
    if (cur.giaTocX != prev.giaTocX || cur.giaTocY != prev.giaTocY || cur.giaTocZ != prev.giaTocZ) {
      xSemaphoreTake(mutexI2C, portMAX_DELAY);
      display.setTextSize(1);
      display.setTextColor(SH110X_WHITE, SH110X_BLACK);

      display.setCursor(13, 42);
      snprintf(buf, sizeof(buf), "%-4d", cur.giaTocX); display.print(buf);

      display.setCursor(56, 42);
      snprintf(buf, sizeof(buf), "%-4d", cur.giaTocY); display.print(buf);

      display.setCursor(99, 42);
      snprintf(buf, sizeof(buf), "%-4d", cur.giaTocZ); display.print(buf);

      xSemaphoreGive(mutexI2C);
      dirty = true;
    }

    // --- Heap (cập nhật mỗi 3 giây, không cần dirty check) ---
    static uint32_t tLanCuoiHeap = 0;
    uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
    if (now - tLanCuoiHeap > 3000) {
      xSemaphoreTake(mutexI2C, portMAX_DELAY);
      display.setTextSize(1);
      display.setTextColor(SH110X_WHITE, SH110X_BLACK);
      display.setCursor(30, 54);
      snprintf(buf, sizeof(buf), "%5uB", (uint16_t)xPortGetFreeHeapSize());
      display.print(buf);
      xSemaphoreGive(mutexI2C);
      tLanCuoiHeap = now;
      dirty = true;
    }

    // Chỉ gọi display() khi có thứ thay đổi
    if (dirty) {
      xSemaphoreTake(mutexI2C, portMAX_DELAY);
      display.display();
      xSemaphoreGive(mutexI2C);
      nhipOLED++;
    }

    prev = cur;
  }
}

// ==========================================
// TASK 3: LED - Core 1, Priority 1
// ==========================================
void TaskDieuKhienLED(void* pv) {
  for (;;) {
    if (canhBaoNguyHiem) {
      analogWrite(PIN_LED_XANH, 0);
      analogWrite(PIN_LED_DO, DO_SANG);
      vTaskDelay(pdMS_TO_TICKS(CHU_KY_NHAY_MS));
      analogWrite(PIN_LED_DO, 0);
      vTaskDelay(pdMS_TO_TICKS(CHU_KY_NHAY_MS));
    } else {
      analogWrite(PIN_LED_XANH, DO_SANG);
      analogWrite(PIN_LED_DO, 0);
      vTaskDelay(pdMS_TO_TICKS(500));
    }
    nhipLED++;
  }
}

// ==========================================
// TASK 4: GIÁM SÁT (Watchdog) - Core 1, Priority 3
// ==========================================
void TaskGiamSat(void* pv) {
  uint32_t prevCamBien = 0, prevOLED = 0, prevLED = 0;

  for (;;) {
    vTaskDelay(pdMS_TO_TICKS(CHU_KY_GIAM_SAT_MS));

    Serial.printf("\n[GIAM SAT] Heap: %u bytes\n", xPortGetFreeHeapSize());
    Serial.printf("  CamBien : %s\n", (nhipCamBien != prevCamBien) ? "OK" : "!!! TREO !!!");
    Serial.printf("  OLED    : %s\n", (nhipOLED    != prevOLED)    ? "OK" : "Cho du lieu");
    Serial.printf("  LED     : %s\n", (nhipLED     != prevLED)     ? "OK" : "!!! TREO !!!");

    // Stack watermark - phát hiện sớm tràn stack
    Serial.printf("  Stack CamBien: %u words free\n", uxTaskGetStackHighWaterMark(handleCamBien));
    Serial.printf("  Stack OLED   : %u words free\n", uxTaskGetStackHighWaterMark(handleOLED));
    Serial.printf("  Stack LED    : %u words free\n", uxTaskGetStackHighWaterMark(handleLED));

    prevCamBien = nhipCamBien;
    prevOLED    = nhipOLED;
    prevLED     = nhipLED;
  }
}

// ==========================================
// SETUP
// ==========================================
void setup() {
  Serial.begin(115200);

  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(I2C_TOC_DO);

  // Khởi tạo I2C Mutex trước khi dùng bất kỳ thiết bị nào
  mutexI2C = xSemaphoreCreateMutex();
  if (!mutexI2C) { Serial.println("Loi tao Mutex!"); while (1); }

  if (!display.begin(0x3C, true)) { Serial.println("Loi OLED!"); while (1); }
  if (!lox.begin())               { Serial.println("Loi VL53L0X!"); while (1); }
  if (!accel.begin())             { Serial.println("Loi ADXL345!"); while (1); }

  // Tăng tốc độ đo VL53L0X (giảm timing budget = phản hồi nhanh hơn, ít chính xác hơn)
  lox.setMeasurementTimingBudgetMicroSeconds(20000); // 20ms (mặc định 33ms)

  // Giảm độ nhạy nhiễu ADXL345
  accel.setRange(ADXL345_RANGE_4_G);
  accel.setDataRate(ADXL345_DATARATE_100_HZ);

  pinMode(PIN_LED_XANH, OUTPUT);
  pinMode(PIN_LED_DO, OUTPUT);

  // Queue 1 slot với xQueueOverwrite - không bao giờ đọc frame cũ
  hopThu = xQueueCreate(1, sizeof(DuLieuCamBien));
  if (!hopThu) { Serial.println("Loi tao Queue!"); while (1); }

  // Core 0: Cảm biến (tách biệt hoàn toàn khỏi display)
  xTaskCreatePinnedToCore(TaskDocCamBien, "CamBien", 4096, nullptr, 3, &handleCamBien, 0);

  // Core 1: Display + LED + Giám sát
  xTaskCreatePinnedToCore(TaskHienThiOLED, "OLED",    4096, nullptr, 2, &handleOLED,    1);
  xTaskCreatePinnedToCore(TaskDieuKhienLED,"LED",     2048, nullptr, 1, &handleLED,     1);
  xTaskCreatePinnedToCore(TaskGiamSat,    "GiamSat",  2048, nullptr, 3, nullptr,        1);

  Serial.println("He thong khoi dong thanh cong!");
}

void loop() {
  vTaskDelay(portMAX_DELAY); // FreeRTOS quản lý hoàn toàn
}