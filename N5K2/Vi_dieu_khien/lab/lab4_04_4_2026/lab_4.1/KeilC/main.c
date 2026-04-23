#include <reg51.h>

sbit P1_5 = P1^5; // Khai báo chân P1.5

void delay_50ms() {
    TMOD = 0x01;  // Timer 0, Mode 1 (16-bit)
    TH0 = 0x3C;   // N?p giá tr? byte cao
    TL0 = 0xB0;   // N?p giá tr? byte th?p
    TR0 = 1;      // Kh?i d?ng Timer 0 (TCON register)
    while (TF0 == 0); // Ch? c? tràn (TF0) b?t lên
    TR0 = 0;      // T?t Timer 0
    TF0 = 0;      // Xóa c? tràn
}

void main() {
    while(1) {
        P1_5 = ~P1_5; // Ð?o tr?ng thái chân P1.5
        delay_50ms(); // G?i hàm tr? 50ms
    }
}