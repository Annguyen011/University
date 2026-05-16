# GIẢI THÍCH CHI TIẾT MÃ NGUỒN DỰ ÁN (main.cpp)

Tài liệu này sẽ giải thích chi tiết từng phần trong file `src/main.cpp` để giúp những người mới bắt đầu có thể hiểu rõ cách hoạt động của hệ thống, đặc biệt là các khái niệm liên quan đến FreeRTOS.

---

## PHẦN 1: KHAI BÁO VÀ CẤU HÌNH (Dòng 1-70)

Đây là phần khởi đầu của chương trình, nơi chúng ta "nhập khẩu" các thư viện cần thiết, định nghĩa các hằng số và khai báo các biến toàn cục.

### 1.1. Bao gồm thư viện (`#include`)

```cpp
#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>
#include <Adafruit_VL53L0X.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL345_U.h>
```

- **`<Arduino.h>`**: Thư viện cốt lõi của Arduino, cung cấp các hàm cơ bản như `pinMode`, `digitalWrite`, `delay`, v.v.
- **`<Wire.h>`**: Thư viện cho giao tiếp I2C, cần thiết để nói chuyện với các cảm biến và màn hình OLED.
- **`<Adafruit_GFX.h>`**: Thư viện đồ họa cơ bản của Adafruit. Nó cung cấp các hàm để vẽ hình (đường thẳng, hình tròn, chữ nhật) nhưng không trực tiếp điều khiển màn hình.
- **`<Adafruit_SH110X.h>`**: Thư viện "trình điều khiển" (driver) cho màn hình OLED SH1106G. Nó làm việc cùng với `Adafruit_GFX` để hiển thị đồ họa lên màn hình.
- **`<Adafruit_VL53L0X.h>`**: Thư viện driver cho cảm biến khoảng cách laser VL53L0X.
- **`<Adafruit_Sensor.h>`**: Thư viện cảm biến thống nhất của Adafruit. Nó định nghĩa một cấu trúc chung cho dữ liệu cảm biến, giúp code dễ đọc hơn.
- **`<Adafruit_ADXL345_U.h>`**: Thư viện driver cho cảm biến gia tốc ADXL345.

### 1.2. Cấu hình hệ thống (`#define`)

`#define` là một chỉ thị của bộ tiền xử lý, dùng để định nghĩa các hằng số. Khi biên dịch, tất cả những tên này sẽ được thay thế bằng giá trị tương ứng. Việc này giúp code dễ đọc và dễ thay đổi.

```cpp
#define PIN_LED_XANH 18
#define PIN_LED_DO 19
#define DO_SANG               15        // PWM 0-255

#define NGUONG_KHOANG_CACH  150       // mm
#define NGUONG_GIA_TOC      5.0f      // m/s²
#define KHOANG_CACH_TOI_DA  1200      // mm

#define CHU_KY_CAM_BIEN_MS  25        // 40Hz
#define CHU_KY_NHAY_MS      100       // Tốc độ nháy đèn
#define CHU_KY_GIAM_SAT_MS  3000      // 3 giây

#define I2C_SDA               21
#define I2C_SCL               22
#define I2C_TOC_DO            400000UL  // 400kHz Fast Mode
```
- `PIN_...`: Định nghĩa chân GPIO nào của ESP32 được nối với đèn LED.
- `DO_SANG`: Độ sáng của đèn LED khi bật (giá trị PWM từ 0-255).
- `NGUONG_...`: Các giá trị ngưỡng để xác định trạng thái "Nguy hiểm".
- `CHU_KY_...`: Các hằng số thời gian, quy định tần suất hoạt động của các Task.
- `I2C_...`: Cấu hình chân và tốc độ cho bus I2C. `400000UL` là tốc độ "Fast Mode".

### 1.3. Khai báo đối tượng phần cứng

```cpp
Adafruit_SH1106G display(128, 64, &Wire, -1);
Adafruit_VL53L0X  lox;
Adafruit_ADXL345_Unified accel(12345);
```

Ở đây, chúng ta tạo ra các "đối tượng" (object) từ các lớp (class) thư viện đã import. Mỗi đối tượng đại diện cho một linh kiện phần cứng cụ thể.
- `display`: Đối tượng màn hình OLED, với kích thước 128x64, sử dụng bus I2C (`&Wire`).
- `lox`: Đối tượng cảm biến khoảng cách.
- `accel`: Đối tượng cảm biến gia tốc. Số `12345` là một ID cảm biến ngẫu nhiên.

### 1.4. Cấu trúc dữ liệu

```cpp
struct DuLieuCamBien {
  uint16_t khoangCach;
  int8_t   giaTocX;
  int8_t   giaTocY;
  int8_t   giaTocZ;
  bool     nguyHiem;
};
```
- `struct` là một cách để nhóm nhiều biến có liên quan vào một "gói" duy nhất. Ở đây, `DuLieuCamBien` là một gói chứa tất cả thông tin mà Task Cảm biến đọc được trong một lần. Việc này giúp việc truyền dữ liệu giữa các Task trở nên gọn gàng.

### 1.5. Biến đồng bộ và Biến toàn cục

```cpp
SemaphoreHandle_t mutexI2C    = nullptr;
QueueHandle_t     hopThu      = nullptr;
volatile bool     canhBaoNguyHiem = false;

volatile uint32_t nhipCamBien = 0;
volatile uint32_t nhipOLED    = 0;
volatile uint32_t nhipLED     = 0;

TaskHandle_t handleCamBien = nullptr;
TaskHandle_t handleOLED    = nullptr;
TaskHandle_t handleLED     = nullptr;
```
Đây là những biến quan trọng nhất trong việc quản lý đa nhiệm.
- `SemaphoreHandle_t mutexI2C`: Biến này sẽ giữ "chìa khóa" cho bus I2C. Giống như một phòng vệ sinh công cộng chỉ có một chìa khóa, Task nào muốn dùng I2C phải "lấy chìa khóa" (`xSemaphoreTake`), dùng xong phải "trả chìa khóa" (`xSemaphoreGive`). Điều này đảm bảo tại một thời điểm chỉ có một Task được truy cập I2C, tránh xung đột.
- `QueueHandle_t hopThu`: Biến này đại diện cho một "hộp thư" (Queue). Task Cảm biến sẽ "bỏ thư" (dữ liệu) vào hộp thư này, và Task OLED sẽ "lấy thư" ra đọc. Hộp thư này đảm bảo dữ liệu được truyền đi một cách an toàn giữa 2 Task.
- `volatile bool canhBaoNguyHiem`: Biến cờ báo trạng thái nguy hiểm. Từ khóa `volatile` báo cho trình biên dịch biết rằng giá trị của biến này có thể bị thay đổi bởi một "thứ gì đó bên ngoài" (ở đây là một Task khác). Điều này ngăn trình biên dịch thực hiện các tối ưu hóa có thể gây lỗi.
- `volatile uint32_t nhip...`: Các biến "đếm nhịp". Mỗi khi một Task hoàn thành một chu kỳ, nó sẽ tăng biến đếm của mình lên. Task Giám sát sẽ dựa vào các biến này để xem các Task khác có bị "treo" hay không.
- `TaskHandle_t handle...`: Các biến "tay nắm" (handle) của Task. Sau khi tạo một Task, FreeRTOS sẽ trả về một "tay nắm" để chúng ta có thể quản lý Task đó sau này (ví dụ: kiểm tra stack, xóa Task).

---

## PHẦN 2: CÁC HÀM VÀ TÁC VỤ (TASKS) (Dòng 72 - 257)

### 2.1. Task 1: `TaskDocCamBien` (Đọc Cảm biến)

Đây là "bộ não" của hệ thống, chạy trên **Core 0** với **mức ưu tiên cao nhất (3)**.

```cpp
void TaskDocCamBien(void* pv) {
  // ... khai báo biến cục bộ ...
  for (;;) { // Vòng lặp vô tận của Task
    // 1. Giành quyền sử dụng I2C
    xSemaphoreTake(mutexI2C, portMAX_DELAY);

    // 2. Đọc dữ liệu từ 2 cảm biến
    lox.rangingTest(&measure, false);
    accel.getEvent(&event);

    // 3. Trả quyền sử dụng I2C ngay lập tức
    xSemaphoreGive(mutexI2C);

    // 4. Xử lý dữ liệu (không còn chiếm bus I2C)
    duLieu.khoangCach = ...;
    duLieu.giaTocX = (int8_t)event.acceleration.x; // Làm tròn
    // ...
    duLieu.nguyHiem = (duLieu.khoangCach < NGUONG_KHOANG_CACH) || ...;

    // 5. Cập nhật biến cờ toàn cục
    canhBaoNguyHiem = duLieu.nguyHiem;

    // 6. Gửi toàn bộ "gói" dữ liệu vào hộp thư
    xQueueOverwrite(hopThu, &duLieu);

    // 7. Tăng nhịp đếm và tạm nghỉ
    nhipCamBien++;
    vTaskDelay(pdMS_TO_TICKS(CHU_KY_CAM_BIEN_MS));
  }
}
```
- **Kiến trúc quan trọng**: Task này chỉ chiếm `mutexI2C` trong khoảng thời gian ngắn nhất có thể (chỉ để đọc dữ liệu thô). Việc xử lý dữ liệu phức tạp hơn được thực hiện sau khi đã trả `mutex`, giúp bus I2C được rảnh cho các Task khác.
- `xQueueOverwrite`: Nếu hộp thư đã có thư cũ, hàm này sẽ vứt thư cũ đi và thay bằng thư mới. Điều này đảm bảo Task OLED luôn nhận được dữ liệu mới nhất.
- `vTaskDelay`: Hàm này không giống `delay()` thông thường. Nó sẽ "ru ngủ" Task hiện tại và nhường CPU cho các Task khác chạy.

### 2.2. Task 2: `TaskHienThiOLED` (Hiển thị OLED)

Task này chạy trên **Core 1** với **mức ưu tiên 2**. Nhiệm vụ của nó là hiển thị thông tin lên màn hình một cách thông minh.

```cpp
void TaskHienThiOLED(void* pv) {
  DuLieuCamBien cur  = {}; // Dữ liệu hiện tại
  DuLieuCamBien prev = {9998, ...}; // Dữ liệu của lần vẽ trước

  // ... Vẽ khung tĩnh cho màn hình 1 lần duy nhất ...

  for (;;) {
    // 1. Chờ nhận dữ liệu từ hộp thư, tối đa 200ms
    if (xQueueReceive(hopThu, &cur, pdMS_TO_TICKS(200)) != pdPASS) continue;

    bool dirty = false; // Biến cờ "bẩn"

    // 2. Thuật toán "Dirty Check"
    if (cur.nguyHiem != prev.nguyHiem) {
      // ... chỉ vẽ lại dòng trạng thái ...
      dirty = true;
    }
    if (cur.khoangCach != prev.khoangCach) {
      // ... chỉ vẽ lại dòng khoảng cách ...
      dirty = true;
    }
    // ... tương tự cho các thông số khác ...

    // 3. Chỉ cập nhật màn hình vật lý khi có sự thay đổi
    if (dirty) {
      xSemaphoreTake(mutexI2C, portMAX_DELAY);
      display.display(); // Gửi buffer lên màn hình
      xSemaphoreGive(mutexI2C);
      nhipOLED++;
    }

    // 4. Lưu lại dữ liệu vừa vẽ để so sánh cho lần sau
    prev = cur;
  }
}
```
- **Tối ưu hóa**: Task này không vẽ lại toàn bộ màn hình mỗi chu kỳ. Nó so sánh dữ liệu mới (`cur`) với dữ liệu cũ (`prev`). Nếu có một giá trị nào đó thay đổi, nó mới chỉ vẽ lại đúng phần đó và đặt cờ `dirty = true`. Cuối cùng, nếu cờ `dirty` là `true`, nó mới thực sự gửi lệnh cập nhật lên màn hình (`display.display()`). Cách làm này giúp giảm đáng kể việc sử dụng bus I2C, tránh làm chậm Task Cảm biến.

### 2.3. Task 3: `TaskDieuKhienLED` (Điều khiển LED)

Task đơn giản nhất, chạy trên **Core 1** với **mức ưu tiên thấp nhất (1)**.

```cpp
void TaskDieuKhienLED(void* pv) {
  for (;;) {
    if (canhBaoNguyHiem) {
      // Chớp tắt đèn đỏ
    } else {
      // Bật đèn xanh, tắt đèn đỏ
    }
    nhipLED++;
    // ... vTaskDelay ...
  }
}
```
- Task này chỉ làm một việc: liên tục kiểm tra biến cờ `canhBaoNguyHiem` và điều khiển đèn LED cho phù hợp. Nó hoàn toàn độc lập với các Task khác.

### 2.4. Task 4: `TaskGiamSat` (Giám sát hệ thống)

Đây là "bác sĩ" của hệ thống, chạy trên **Core 1** với **mức ưu tiên cao (3)**, chạy định kỳ mỗi 3 giây.

```cpp
void TaskGiamSat(void* pv) {
  uint32_t prevCamBien = 0, prevOLED = 0, prevLED = 0;
  for (;;) {
    vTaskDelay(pdMS_TO_TICKS(CHU_KY_GIAM_SAT_MS));

    // 1. In ra lượng RAM còn trống
    Serial.printf("\n[GIAM SAT] Heap: %u bytes\n", xPortGetFreeHeapSize());

    // 2. Kiểm tra các Task có bị treo không
    Serial.printf("  CamBien : %s\n", (nhipCamBien != prevCamBien) ? "OK" : "!!! TREO !!!");
    // ...

    // 3. Kiểm tra mức sử dụng Stack của từng Task
    Serial.printf("  Stack CamBien: %u words free\n", uxTaskGetStackHighWaterMark(handleCamBien));
    // ...

    // 4. Cập nhật lại các biến đếm nhịp
    prevCamBien = nhipCamBien;
    // ...
  }
}
```
- `xPortGetFreeHeapSize()`: Trả về lượng bộ nhớ Heap (RAM động) còn trống. Theo dõi chỉ số này giúp phát hiện lỗi rò rỉ bộ nhớ (memory leak).
- **Kiểm tra treo (Deadlock)**: Bằng cách so sánh `nhipCamBien` với `prevCamBien`, nếu hai giá trị này bằng nhau sau 3 giây, nghĩa là Task Cảm biến đã không chạy, tức là nó đã bị "treo".
- `uxTaskGetStackHighWaterMark()`: Đây là một hàm gỡ lỗi cực kỳ hữu ích. Mỗi Task khi được tạo sẽ được cấp một vùng nhớ riêng gọi là Stack. Hàm này cho biết lượng Stack "chưa bao giờ được dùng đến". Nếu giá trị này quá nhỏ (vài chục byte), nghĩa là Task đang có nguy cơ bị "tràn Stack", một lỗi rất khó tìm.

---

## PHẦN 3: KHỞI TẠO VÀ VÒNG LẶP CHÍNH (Dòng 259 - 301)

### 3.1. `setup()`

Hàm này chỉ chạy một lần duy nhất khi ESP32 khởi động. Nó có nhiệm vụ thiết lập toàn bộ hệ thống.

```cpp
void setup() {
  // 1. Khởi tạo các giao tiếp cơ bản
  Serial.begin(115200);
  Wire.begin(I2C_SDA, I2C_SCL);
  Wire.setClock(I2C_TOC_DO);

  // 2. Tạo các đối tượng FreeRTOS (Mutex, Queue)
  mutexI2C = xSemaphoreCreateMutex();
  hopThu = xQueueCreate(1, sizeof(DuLieuCamBien));

  // 3. Khởi tạo các driver phần cứng
  display.begin(...);
  lox.begin();
  accel.begin();

  // 4. Cấu hình thêm cho cảm biến
  lox.setMeasurementTimingBudgetMicroSeconds(20000); // Tăng tốc độ đo
  accel.setRange(ADXL345_RANGE_4_G); // Giảm độ nhạy

  // 5. Khởi tạo chân LED
  pinMode(PIN_LED_XANH, OUTPUT);
  pinMode(PIN_LED_DO, OUTPUT);

  // 6. Tạo và khởi chạy các Task
  xTaskCreatePinnedToCore(
      TaskDocCamBien,     // Hàm của Task
      "CamBien",          // Tên Task (để debug)
      4096,               // Kích thước Stack (bytes)
      nullptr,            // Tham số truyền vào Task (không dùng)
      3,                  // Mức ưu tiên
      &handleCamBien,     // Biến để lưu "tay nắm"
      0                   // Ghim Task vào Core 0
  );
  // ... tạo các Task khác tương tự, ghim vào Core 1 ...

  Serial.println("He thong khoi dong thanh cong!");
}
```
- **Thứ tự khởi tạo rất quan trọng**: Phải tạo `mutexI2C` trước khi gọi hàm `.begin()` của bất kỳ thiết bị I2C nào, vì các hàm `.begin()` này cũng sử dụng I2C.
- `xTaskCreatePinnedToCore`: Đây là hàm "thần kỳ" của FreeRTOS trên ESP32. Nó không chỉ tạo ra một Task mà còn "ghim" Task đó vào một lõi CPU cụ thể (Core 0 hoặc Core 1). Việc phân chia Task hợp lý giữa 2 Core giúp hệ thống chạy hiệu quả hơn rất nhiều.

### 3.2. `loop()`

```cpp
void loop() {
  vTaskDelay(portMAX_DELAY); // FreeRTOS quản lý hoàn toàn
}
```
- Trong một dự án dùng FreeRTOS, hàm `loop()` truyền thống của Arduino trở nên vô dụng. Sau khi `setup()` tạo ra các Task, bộ lập lịch (scheduler) của FreeRTOS sẽ toàn quyền điều khiển CPU.
- Chúng ta cho `loop()` (vốn cũng là một Task do Arduino core tạo ra) ngủ vĩnh viễn bằng `vTaskDelay(portMAX_DELAY)` để nó không lãng phí tài nguyên CPU. Toàn bộ logic của chương trình giờ đây nằm trong các Task mà chúng ta đã tạo.