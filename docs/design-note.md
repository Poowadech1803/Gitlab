# Design Note — Lab 02

## เป้าหมาย
Flask Web App คำนวณ DC Bias ของวงจร BJT Common-Emitter
Voltage-Divider Bias โดยแยก Logic / Route / Template / Test ออกจากกัน

## การตัดสินใจออกแบบหลัก

1. **dc_bias.py เป็น pure module** — ไม่ import Flask ไม่รู้จัก HTTP/HTML
   เพื่อให้ทดสอบสมการวิศวกรรมแยกจากเว็บได้ (ตามโจทย์ section 04)
2. **parse_input() แยกจาก solve()** — validation เกิดที่ route layer
   ก่อนส่งเข้าสมการ เจอค่าผิดจะไม่ทำให้เว็บล้ม (500)
3. **dataclass BiasInput/BiasResult** — หน่วยชัดเจน (V, Ω, A) ทั้งหมด SI
   แปลงเป็น mA/µA เฉพาะตอนแสดงผล (property ic_ma, ib_ua)
4. **Region detection แบบง่าย** —
   - VTH ≤ VBE → cutoff (คืนค่าศูนย์ + warning)
   - VCE < 0.2 V → saturation warning (ยังแสดงค่าพร้อมคำเตือนว่าไม่น่าเชื่อถือ)
5. **สอง route**: GET / (ฟอร์มเปล่า + default), POST /calculate (คำนวณ)
   แทนการใช้ route เดียว เพื่อให้ URL ชัดเจนตาม acceptance A2

## สิ่งที่ตัดออก (out of scope Week 2)
- AC / transient / Bode plot / signal generator
- bias types อื่น (fixed bias, emitter bias) — สัปดาห์ถัดไป
- SPICE solver
