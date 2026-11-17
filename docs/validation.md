# Lab 03 — Browser Validation (A1–A5)

วันที่ตรวจ: 2026-11-17
URL ที่ตรวจ: `http://127.0.0.1:5000/`
วิธีตรวจ: **OpenCode Browser** (`tools.browser.*` — Chromium ใน OpenCode Desktop)
อ่านผลจากหน้าเว็บจริงที่ render หลังกดปุ่ม **Calculate DC Bias** ทุกกรณี
(Playwright MCP ไม่ได้ configure ใน session นี้ จึงใช้ OpenCode Browser ซึ่งเป็นวิธีสำรองที่ใบงานอนุญาต)
หลักฐานเพิ่มเติม: `docs/validation-a5-error.jpeg` (screenshot ของกรณี A5)

ใช้ร่วมกันทุกกรณี: **VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V**
เกณฑ์: |ΔIC| ≤ 0.01 mA, |ΔVCE| ≤ 0.02 V เมื่อเทียบกับค่าอ้างอิงที่ยังไม่ปัดเศษ

## ค่าอ้างอิงอิสระ (คำนวณมือจากสมการในใบงาน ไม่ได้อ่านจาก `dc_bias.py`)

| กรณี | สมการ IB | IB | IC อ้างอิง | VCE อ้างอิง |
|---|---|---|---|---|
| A1 Divider | (VTH−VBE)/(RTH+(β+1)RE), VTH=12·22/122=2.1639 V, RTH=100·22/122=18.0328 kΩ | 12.30 µA | 1.2299 mA | 8.0522 V |
| A2 Fixed | (12−0.70)/1 MΩ | 11.3000 µA | 1.1300 mA | 9.5140 V |
| A3 Emitter RE=1 kΩ | (12−0.70)/(1 MΩ+101·1 kΩ) | 10.2634 µA | 1.0263 mA | 8.7054 V |
| A4 Emitter RE=2 kΩ | (12−0.70)/(1 MΩ+101·2 kΩ) | 9.4010 µA | 0.9401 mA | 8.0328 V |

ค่าอื่นที่ตามมาจาก IB: `IC=β·IB`, `IE=(β+1)·IB`, `VE=IE·RE` (Fixed ใช้ VE=0),
`VB=VE+VBE`, `VC=VCC−IC·RC`, `VCE=VC−VE`

## ผลตรวจ A1–A5

| Case | โหมด / อินพุตที่กรอกในฟอร์ม | คาดหมาย (อิสระ) | เห็นจริงบนหน้าเว็บ | วิธี | สถานะ | หลักฐาน (ข้อความจากหน้าเว็บ) |
|---|---|---|---|---|---|---|
| A1 | Divider · R1=100 kΩ, R2=22 kΩ, RE=1 kΩ (RC=2.2 kΩ, β=100, VBE=0.70 V) | IC 1.2299 mA · VCE 8.0522 V | **IC 1.23 mA · VCE 8.05 V** (VB 1.94 V, VE 1.24 V, VC 9.29 V, IB 12.3 µA) | OpenCode Browser | PASS | หัวข้อ `DC Bias Results — Voltage Divider Bias`; แถว `IC 1.23 mA`, `VCE 8.05 V` — ตรงกับผล Lab 02 เดิม |
| A2 | Fixed · RB=1 MΩ (กรอก RB=1 เลือกหน่วย MΩ; ไม่มีช่อง R1/R2/RE) | IC 1.1300 mA · VCE 9.5140 V | **IC 1.13 mA · VCE 9.51 V** (VB 0.70 V, VE 0.00 V, VC 9.51 V, IB 11.3 µA) | OpenCode Browser | PASS | หัวข้อ `DC Bias Results — Fixed Bias`; แถว `IC 1.13 mA`, `VCE 9.51 V`; สถานะ `Active region approximation OK` |
| A3 | Emitter · RB=1 MΩ, RE=1 kΩ | IC 1.0263 mA · VCE 8.7054 V | **IC 1.03 mA · VCE 8.71 V** (VB 1.74 V, VE 1.04 V, VC 9.74 V, IB 10.3 µA) | OpenCode Browser | PASS | หัวข้อ `DC Bias Results — Emitter Bias`; แถว `IC 1.03 mA`, `VCE 8.71 V` |
| A4 | Emitter · เหมือน A3 เปลี่ยน **เฉพาะ RE เป็น 2 kΩ** | IC 0.9401 mA · VCE 8.0328 V (IC ต้อง **ลด** จาก A3) | **IC 0.94 mA · VCE 8.03 V** (VB 2.60 V, VE 1.90 V, VC 9.93 V, IB 9.4 µA) | OpenCode Browser | PASS | ก่อนเปลี่ยน: `IC 1.03 mA` / `VCE 8.71 V` → หลังเปลี่ยน: `IC 0.94 mA` / `VCE 8.03 V`; ฟอร์มยืนยัน `re = 2`, `re_unit = kohm`, โหมดยังเป็น `emitter` |
| A5 | Fixed · RB=0 (หน่วย MΩ) | ข้อความให้แก้ RB, เว็บไม่ล่ม, ไม่แสดงผลรอบก่อน | **error: `RB ต้องมากกว่า 0 Ω (RB must be > 0 Ω)`**; ไม่มีตารางผล; ไม่มี `0.94 mA` ค้างอยู่ | OpenCode Browser | PASS | หัวข้อ `Input Errors (Fixed Bias) — ข้อผิดพลาดของข้อมูลนำเข้า`; รายการ `RB ต้องมากกว่า 0 Ω (RB must be > 0 Ω)` — ข้อความมาจาก **Flask** (validation ใน `dc_bias.py`) ไม่ใช่ HTML `required` ของฟอร์ม |

## A3 → A4: ทำนายทิศทางก่อนรัน

ทำนายว่า **IC จะลดลง** เมื่อเพิ่ม RE จาก 1 kΩ เป็น 2 kΩ เพราะ

```
IB = (VCC − VBE) / [RB + (β+1)·RE]
```

ตัวหารเพิ่มจาก `1 MΩ + 101 kΩ = 1.101 MΩ` เป็น `1 MΩ + 202 kΩ = 1.202 MΩ`
ขณะที่ตัวตั้งเท่าเดิม (11.3 V) → IB ลดลงจาก 10.2634 µA เป็น 9.4010 µA
และ `IC = β·IB` จึงลดลงตามเป็น 1.0263 mA → 0.9401 mA

ผลที่เห็นจริงบนหน้าเว็บ 1.03 mA → 0.94 mA ตรงทิศทางที่ทำนาย (Δ = −0.09 mA)
และค่า VC เพิ่มขึ้นเล็กน้อยเพราะ IC ลดลง → แรงดันตกบน RC ลดลง (9.74 V → 9.93 V)

## หมายเหตุการตรวจ

- ทุกกรณีใช้การกรอกผ่านฟอร์มจริงในเบราว์เซอร์ + กดปุ่มคำนวณจริง ไม่ได้ใช้ curl หรืออ่าน source แทน
- หลังเปลี่ยนโหมด กด **เปลี่ยนโหมด** แล้วอ่าน snapshot ใหม่ก่อนกรอก (ตามที่ใบงานแนะนำ)
- กรณี A5 พิสูจน์ว่า Flask ตรวจอินพุตเอง: ข้อความ error ถูก render จาก `errors` ที่ `app.py` ส่งกลับ
  และ `result = None` ทำให้ตารางผลหายไป ไม่ใช่ผลเก่าจาก A4
- จำนวน tests ที่ผ่าน: `python -m unittest discover -s tests -v` → **OK 29/29**
  (including tests เดิมของ Lab 02 ทุกตัว)
