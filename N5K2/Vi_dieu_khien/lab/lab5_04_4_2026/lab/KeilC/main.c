#include <reg51.h>

// M?ng ch?a mã Hex d? hi?n th? các s? t? 0 d?n 9 trên LED 7 do?n Anot chung (Common Anode)
unsigned char code seg7[] = {0xC0, 0xF9, 0xA4, 0xB0, 0x99, 0x92, 0x82, 0xF8, 0x80, 0x90};
unsigned char count = 0; // Bi?n d?m s?n ph?m

// Hàm ph?c v? Ng?t ngoài 0 (N?i v?i nút nh?n)
void EX0_ISR() interrupt 0 {
    count++; // Tang bi?n d?m
    if (count > 9) {
        count = 0; // N?u l?n hon 9 thì reset v? 0
    }
    P2 = seg7[count]; // C?p nh?t s? m?i ra Port 2
}

void main() {
    P2 = seg7[0]; // Kh?i t?o hi?n th? s? 0 ban d?u
    
    // Thi?t l?p ng?t ngoài 0
    IT0 = 1;      // C?u hình ng?t kích ho?t b?ng su?n âm (Edge-triggered)
    EX0 = 1;      // Cho phép ng?t ngoài 0
    EA = 1;       // Cho phép ng?t toàn c?c
    
    while(1) {
        // Vi di?u khi?n n?m ch?, khi nào b?m nút thì nh?y vào hàm ng?t EX0_ISR
    }
}