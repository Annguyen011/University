#include <reg52.h>

sbit BUTTON = P3^0; // Nút nh?n ? chân P3.0

// Mã LED 7 do?n Anode chung (0-9)
unsigned char code led_code[] = {0xC0, 0xF9, 0xA4, 0xB0, 0x99, 0x92, 0x82, 0xF8, 0x80, 0x90};

void delay(unsigned int ms) {
    unsigned int i, j;
    for(i = 0; i < ms; i++)
        for(j = 0; j < 120; j++);
}

void main() {
    int count = 0;
    BUTTON = 1;           // Ð?t P3.0 làm chân nh?n tín hi?u
    P2 = led_code[count]; // Xu?t s? 0 ra Port 2 (vì b?n n?i LED vào P2)

    while(1) {
        if (BUTTON == 0) {     // N?u nút du?c ?n
            delay(20);         // Ð?i 20ms d? ch?ng d?i phím
            if (BUTTON == 0) { 
                count++;       // Tang s? lên 1
                if (count > 9) {
                    count = 0; // Quá 9 thì quay l?i 0
                }
                P2 = led_code[count]; // Hi?n th? s? m?i ra Port 2
                
                while (BUTTON == 0);  // Ð?i th? nút ra m?i d?m ti?p
            }
        }
    }
}