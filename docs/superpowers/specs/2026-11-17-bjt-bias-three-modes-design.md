# Lab 03 — BJT DC Bias Web App: สามโหมดในเว็บเดิม

## Intent
ต่อยอด Flask app ของ Lab 2 (โฟลเดอร์ปัจจุบัน) ให้ `POST /calculate` รองรับ
Fixed Bias และ Emitter Bias แบบแหล่งจ่ายเดียว โดยผลของ Voltage Divider เดิม
ต้องไม่เปลี่ยน เป็นงานตามใบงาน `ENG29_2121_Lab03_BJT_Bias_Web_App`

## Goals
- สมการอยู่ในโมดูล Python (`dc_bias.py`) เท่านั้น ไม่ย้ายไป HTML/JS
- ผลทุกโหมดใช้โครงสร้างเดียวกัน: `BiasResult` และชื่อคีย์/หน่วยเดิม
  (`vb`, `ve`, `vc`, `vce` เป็น V; `ic_ma` เป็น mA)
- ตรวจอินพุตและแปลงหน่วย (kΩ/MΩ → Ω) เฉพาะช่องที่โหมดนั้นใช้
- โหมดไม่รู้จัก / ค่าไม่ครบ / ไม่ใช่ตัวเลข / ค่าที่ต้องเป็นบวก ≤ 0 → แจ้ง error
  ไม่แสดงผลเก่าจากรอบก่อน
- ฟอร์มเลือกโหมดแล้วโหลดใหม่ได้ แสดงเฉพาะช่องที่ใช้ ผล/error ระบุโหมด
- ตรวจ A1–A5 ผ่าน Browser จริง แล้วrecord ลง `docs/validation.md`

## Non-goals / Anti-goals
- ไม่ทำ SPICE, DC Load Line, AC/Transient, bypass capacitor
- ไม่สร้าง unittest ใหม่ (คง tests เดิมไว้และต้องผ่าน)
- ไม่สร้างโปรเจกต์ใหม่ / ไม่เขียนสมการใน Jinja template

## Constraints
- โค้ดเดิมที่ต้อง reuse: `app.py` (`/calculate`, `UNIT_FACTORS`, `RESISTOR_FIELDS`),
  `dc_bias.py` (`BiasInput`, `BiasResult`, `_validate`, `parse_input`, `solve`),
  `templates/index.html`, `tests/test_dc_bias.py`
- `solve()` เดิมและ `parse_input()` แบบไม่ระบุโหมดต้องยังใช้ได้เพื่อไม่ให้ tests เดิมพัง
- แบบจำลอง Forward-Active: β และ VBE คงที่; เตือนเมื่อ IB ≤ 0 หรือ VCE ≤ 0.2 V

## Approaches
1. **แก้ต่อในโปรเจกต์เดิม (เลือก)** — ใช้ `BiasResult` และ route เดิมร่วมกัน
   ตัดการซ้ำของฟอร์ม/tests น้อยที่สุด และตรงตามข้อกำหนดใบงาน
2. แยก blueprint/route ใหม่สำหรับ Lab 3 — ต้อง duplication ฟอร์มและค่าอ้างอิง
   กับของเดิม เสี่ยงทำให้ Divider เดิมคลาดเคลื่อน
3. คำนวณใน Jinja/JavaScript — ใบงานห้าม และตรวจยาก

## Design (ตกลงแล้ว)
- `dc_bias.py`: เพิ่ม input สำหรับ Fixed (`RB, RC`) และ Emitter (`RB, RC, RE`);
  ฟังก์ชัน `solve_fixed()`, `solve_emitter()`, `solve_divider()` ใช้ helper ร่วม
  คำนวณ `IC=βIB`, `IE=(β+1)IB`, `VE`, `VB`, `VC`, `VCE` และ warning เหมือนเดิม;
  `solve()` เดิมยังเป็น Divider; `parse_input(data, mode="divider")` รองรับทุกโหมด
- `app.py`: อ่าน `mode` จากฟอร์ม (ค่าเดิม `divider`), whitelist โหมด;
  เลือกช่องบังคับ/หน่วยตามโหมดด้วย `if/elif`, เรียก solver ที่ตรงกัน;
  เมื่อ error ให้ `result=None` เสมอ; ส่ง `mode` ให้ template
- `templates/index.html`: dropdown `mode` + ปุ่ม "เปลี่ยนโหมด" ที่ submit ฟอร์ม
  (ไม่ใช้ JS) แสดงเฉพาะช่องที่ใช้; หัวข้อผล/error บอกโหมดที่เลือก
- `README.md`: อัปเดตวิธีรัน สามโหมด สมการ และตารางอ้างอิงอิสระ
- `docs/validation.md`: ตาราง A1–A5 พร้อมค่าคาดหมาย ผลจริง หน่วย วิธีตรวจ
  และหลักฐานจาก browser

## Left to builder
เขียนแผนเป็นขั้นตอนที่ชัดเจน (writing-plans) แล้ว implement ตามลำดับ:
โมดูลคำนวณ → route → template → ทดสอบเดิม → browser A1–A5 → docs
