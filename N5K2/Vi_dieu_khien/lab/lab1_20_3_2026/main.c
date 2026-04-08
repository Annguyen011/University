#include <REGX52.H>

void Delay(unsigned int var); // Khai báo hàm tr?

void main (void)
{
    while(1)
    {
        P1 = 0x00;      // Ðua Port 1 v? m?c th?p (VD: Sáng LED)
        Delay(1000);    // G?i hàm tr?
        P1 = 0xFF;      // Ðua Port 1 lên m?c cao (VD: T?t LED)
        Delay(1000);    // G?i hàm tr?
    }
}

// Ð?nh nghia hàm tr?
void Delay(unsigned int var)
{
    while(var--);
}