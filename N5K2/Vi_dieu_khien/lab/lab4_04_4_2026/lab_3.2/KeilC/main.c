#include <reg51.h>

void delay_50ms_T1() {
    TMOD = 0x10;  // Timer 1, Mode 1 (16-bit)
    TH1 = 0x3C;   // N?p giá tr? byte cao
    TL1 = 0xB0;   // N?p giá tr? byte th?p
    TR1 = 1;      // Kh?i d?ng Timer 1
    while (TF1 == 0); // Ch? c? tràn
    TR1 = 0;      // T?t Timer 1
    TF1 = 0;      // Xóa c? tràn
}

void delay_500ms() {
    int i;
    for(i = 0; i < 10; i++) {
        delay_50ms_T1(); // L?p 10 l?n d? du?c 500ms
    }
}

void main() {
    P2 = 0x00; // Kh?i t?o Port 2
    while(1) {
        P2 = ~P2;      // Ð?o tr?ng thái toàn b? các chân Port 2
        delay_500ms(); // Ch? 500ms
    }
}