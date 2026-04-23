#include <reg51.h>

sbit P2_7 = P2^7; // Khai báo chân P2.7

void main() {
    TMOD = 0x20;  // Timer 1, Mode 2 (8-bit auto-reload)
    TH1 = 0x38;   // Giá tr? n?p l?i t? d?ng cho n?a chu k? (200us)
    TR1 = 1;      // Kh?i d?ng Timer 1
    
    while(1) {
        while (TF1 == 0); // Ch? c? tràn
        TF1 = 0;          // Xóa c? tràn
        P2_7 = ~P2_7;     // Ð?o tr?ng thái chân P2.7
    }
}