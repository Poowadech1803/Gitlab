# Reflection — Lab 02

## สิ่งที่ได้เรียนรู้

1. **Frontend vs Backend**: เข้าใจแล้วว่าเปิด `templates/index.html` ตรง ๆ
   ด้วย `file://` ไม่เท่ากับการรัน Flask เพราะ `{{ ... }}` ในไฟล์เป็น Jinja
   placeholder ที่ server ต้อง render และการคำนวณเกิดที่ Python
   ไม่ใช่ใน browser

2. **ฟอร์มส่งข้อมูลไป Python อย่างไร**: `<form method="post" action="/calculate">`
   ทำให้ browser ส่ง HTTP POST request พร้อม form data ไปที่ Flask route
   `/calculate` ซึ่งดึงค่าด้วย `request.form.get(...)` แล้วเรียก `solve()`

3. **แก้สมการใน dc_bias.py แล้วต้องแก้ HTML ไหม**: ไม่ต้อง — template
   แสดงเฉพาะผลลัพธ์ผ่านตัวแปร การแยก module ทำให้แก้ physics ที่เดียว
   ผลเปลี่ยนทั้งเว็บอัตโนมัติ (แต่ถ้าเพิ่ม output ใหม่ต้องเพิ่มแถวใน template)

4. **ทำไมต้องมี Warning ใน region ที่แบบจำลองใช้ไม่ได้**: เพราาะสมการ
   Forward-Active สมมติ junction นำแบบเส้นตรง ถ้าอุปกรณ์ตัดหรืออิ่มตัวจริง
   ผลที่ได้จะผิด (เช่น IC ติดลบหรือ VCE ติดลบ) การแจ้งเตือนป้องกันการ
   นำค่าไปใช้โดยไม่รู้ว่าไม่สะท้อนสภาวะจริงของวงจร

## ปัญหาที่พบและวิธีแก้

- ค่าที่แสดงบนหน้าเว็บต้อง format ทศนิยมให้อ่านง่าย แก้ด้วย
  Jinja filter `"%.3f"|format(...)` ร่วมกับ property `ic_ma`, `ib_ua`
  ใน dataclass เพื่อแปลงหน่วยให้ถูกต้อง (A → mA/µA)

## สิ่งที่อยากทำต่อ (Week 3+)
- เพิ่ม Fixed Bias และ Emitter Bias
- วาด circuit diagram ด้วย SVG ในหน้าผลลัพธ์
- DC load line plot ด้วย matplotlib
