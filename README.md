# BJT DC Bias Web App — ENG29 2121 Lab 03

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจรขยาย BJT Common-Emitter
แบบเลือกได้ 3 โหมด: **Voltage Divider Bias**, **Fixed Bias** และ **Emitter Bias**
(แหล่งจ่ายเดียว) ใช้ Forward-Active Approximation (β คงที่, VBE คงที่)
การคำนวณทั้งหมดอยู่ใน Python Backend (`dc_bias.py`) ไม่มีสมการใน HTML/JavaScript

Lab 02 เดิม (Voltage Divider) ยังให้ผลเหมือนเดิมสำหรับอินพุตชุดเดิม และชุดทดสอบเดิมยังผ่านทุกตัว

## โครงสร้างโปรเจกต์

```
transistor-simulator/
├── app.py                  # Flask routes: GET / , POST /calculate (เลือก solver ตามโหมด)
├── dc_bias.py              # โมดูลคำนวณวิศวกรรม (ไม่รู้จัก HTTP/HTML)
├── templates/index.html    # ฟอร์ม + ผลลัพธ์ (Jinja) แสดงเฉพาะช่องของโหมดที่เลือก
├── static/style.css        # การแสดงผล
├── tests/
│   ├── test_dc_bias.py     # unit tests (สมการ + validation ทุกโหมด)
│   └── test_web.py         # HTTP tests ผ่าน Flask test client
├── docs/
│   ├── validation.md             # ตาราง A1–A5 จากการตรวจผ่าน Browser จริง
│   └── validation-a5-error.jpeg  # หลักฐาน screenshot กรณี A5
├── requirements.txt
└── README.md
```

## การติดตั้งและรัน

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate       # Linux / macOS
python -m pip install -r requirements.txt
python -m flask --app app run
```

เปิด Browser ที่ **http://127.0.0.1:5000/**
(ต้องรันผ่าน Flask server เท่านั้น — เปิด `templates/index.html` ตรง ๆ ด้วย `file://` ไม่ได้
เพราะการคำนวณเกิดที่ Python Backend)

ในฟอร์ม:

1. เลือก **Bias mode** (Voltage Divider / Fixed / Emitter) แล้วกด **เปลี่ยนโหมด**
   — หน้าจะโหลดใหม่และแสดงเฉพาะช่องที่โหมดนั้นใช้
2. กรอกค่าตามหน่วยที่แสดงข้างช่อง (Ω / kΩ / MΩ แปลงเป็น Ω ครั้งเดียวที่ `app.py`)
3. กด **Calculate DC Bias** — ผล/error จะระบุชื่อโหมดที่เลือกเสมอ และผลเก่าจะไม่หลงเหลือเมื่ออินพุตผิด

## การรัน Automated Tests

```powershell
python -m unittest discover -s tests -v
```

ผลล่าสุด: **OK 29/29** (tests เดิม Lab 02 ยังอยู่ครบ + tests ใหม่ของ Lab 03)

## สามโหมดและสมการที่ใช้

ทุกโหมดรับ `VCC, RC, β, VBE` เหมือนกัน ต่างกันที่ตัวต้านทานและสมการ IB

| โหมด | ช่องที่ใช้ | IB |
|---|---|---|
| Voltage Divider Bias | R1, R2, RC, RE | `(VTH − VBE) / [RTH + (β+1)·RE]` |
| Fixed Bias | RB, RC | `(VCC − VBE) / RB` |
| Emitter Bias | RB, RC, RE | `(VCC − VBE) / [RB + (β+1)·RE]` |

โดย `VTH = VCC·R2/(R1+R2)` และ `RTH = R1·R2/(R1+R2)` (เฉพาะ Divider)

ค่าที่ตามมาจาก IB (helper ร่วม `_finish` ใน `dc_bias.py`):

```
IC = β·IB        IE = (β+1)·IB
VE = IE·RE       (Fixed Bias ใช้ VE = 0 V)
VB = VE + VBE
VC = VCC − IC·RC
VCE = VC − VE
```

หน่วยที่ส่งกลับเหมือนทุกโหมด: `vb, ve, vc, vce` เป็น **V**, `ic_ma` เป็น **mA**,
`ib_ua` เป็น **µA**, `ie_ma` เป็น **mA** (ใช้ `BiasResult` ตัวเดียวทั้ง 3 โหมด)

## ค่าอ้างอิงอิสระ (คำนวณมือ ไม่ได้อ่านจากโปรแกรม)

ใช้ชุดเดียวกับใบงาน: VCC=12 V, RC=2.2 kΩ, β=100, VBE=0.70 V

| กรณี | อินพุตเพิ่ม | IC อ้างอิง | VCE อ้างอิง |
|---|---|---|---|
| Divider (Lab 02) | R1=100 kΩ, R2=22 kΩ, RE=1 kΩ | 1.2299 mA | 8.0522 V |
| Fixed | RB=1 MΩ | 1.1300 mA | 9.5140 V |
| Emitter | RB=1 MΩ, RE=1 kΩ | 1.0263 mA | 8.7054 V |
| Emitter | RB=1 MΩ, RE=2 kΩ | 0.9401 mA | 8.0328 V |

ตารางผลจริงที่อ่านจาก browser พร้อมหลักฐาน: [`docs/validation.md`](docs/validation.md)

## ข้อจำกัดของแบบจำลอง (Model Limitations)

- ใช้ Forward-Active Approximation เท่านั้น (β, VBE คงที่) — ไม่ใช่ SPICE,
  ไม่ทำ DC Load Line / AC / Transient / bypass capacitor
- แยกแยะ "อินพุตผิด" กับ "แบบจำลองใช้ไม่ได้":
  - ข้อมูลไม่ครบ / ไม่ใช่ตัวเลข / ไม่จำกัด (`nan`, `inf`) / ค่าที่ต้องเป็นบวก ≤ 0 → **Error** (ไม่แสดงผล)
  - IB ≤ 0 หรือ VCE ≤ 0.2 V (โหมดใหม่) → **warning** ว่าแบบจำลอง Forward-Active อาจใช้ไม่ได้
    (ไม่พยายามหาค่าจริงใน Cutoff/Saturation)
- โหมดที่ไม่รู้จัก → แจ้ง error ทันที ไม่เดาเป็น Divider

## ใครทำอะไร (AI-assisted lab)

- **AI เขียนโค้ด**: `dc_bias.py` (Fixed/Emitter solvers + mode validation), `app.py`
  (dispatch ตามโหมด + แปลงหน่วยเฉพาะช่องที่ใช้), `templates/index.html` + `static/style.css`
  (mode selector, conditional fields), README และ `docs/validation.md`
- **สิ่งที่ต้องตรวจด้วยความเข้าใจ**: สมการ IB ของแต่ละโหมด, การแปลง kΩ/MΩ → Ω
  (จุดเดียวใน `app.py`), ชื่อคีย์/หน่วยของ `BiasResult`, ข้อความ error/warning,
  และค่าอ้างอิงอิสระในตารางข้างบน
- จุดเลือกฟังก์ชันอยู่ที่ `app.py` → `SOLVERS[mode](bias)`; แปลงหน่วยอยู่ที่ลูป
  `RESISTOR_FIELDS_BY_MODE[mode]` ใน `calculate()`
