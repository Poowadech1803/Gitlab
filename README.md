# BJT DC Bias Web App — ENG29 2121 Lab 02

Flask Web Application สำหรับคำนวณ **DC Operating Point** ของวงจรขยาย
BJT Common-Emitter แบบ **Voltage-Divider Bias** (Forward-Active
Approximation: β คงที่, VBE คงที่) โดยการคำนวณทั้งหมดทำใน Python Backend

## โครงสร้างโปรเจกต์

```
transistor-simulator/
├── app.py                  # Flask routes (GET / , POST /calculate)
├── dc_bias.py              # โมดูลคำนวณวิศวกรรม (ไม่รู้จัก HTTP/HTML)
├── templates/index.html    # ฟอร์ม + ผลลัพธ์ (Jinja)
├── static/style.css        # การแสดงผล
├── tests/
│   ├── test_dc_bias.py     # unit tests (engineering math)
│   └── test_web.py         # HTTP tests ผ่าน Flask test client
├── requirements.txt
└── README.md
```

## การติดตั้งและรัน

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate       # Linux / macOS
python -m pip install -r requirements.txt
python -m flask --app app run --debug
```

เปิด Browser ที่ **http://127.0.0.1:5000/** (ต้องรันผ่าน Flask server
เท่านั้น — เปิด `templates/index.html` ตรง ๆ ด้วย `file://` ไม่ได้
เพราะการคำนวณเกิดที่ Python Backend)

## การรัน Automated Tests

```powershell
python -m unittest discover -s tests -v
```

## ค่าอ้างอิง (ตรวจสอบด้วยการคำนวณอิสระ)

VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70 V:

| ปริมาณ | ค่าอ้างอิง |
|---|---|
| VTH | 2.1639 V |
| RTH | 18.033 kΩ |
| IB | 12.30 µA |
| IC | 1.2299 mA |
| IE | 1.2422 mA |
| VE | 1.2422 V |
| VB | 1.9422 V |
| VC | 9.2943 V |
| VCE | 8.0522 V |

## สมการที่ใช้

```
VTH = VCC · R2 / (R1 + R2)
RTH = R1·R2 / (R1 + R2)
IB  = (VTH − VBE) / (RTH + (β+1)·RE)
IC  = β·IB      IE = (β+1)·IB
VE  = IE·RE     VB = VE + VBE
VC  = VCC − IC·RC    VCE = VC − VE
```

## ข้อจำกัดของแบบจำลอง (Model Limitations)

- ใช้ Forward-Active Approximation เท่านั้น (β, VBE คงที่) — ไม่ใช่ SPICE
- กรณี VTH ≤ VBE → แจ้ง **Cutoff warning** และไม่รายงานค่า Q-point
- กรณี VCE < 0.2 V → แจ้ง **Saturation warning** ว่าค่าที่ได้ไม่สะท้อนสภาวะจริง
- ข้อมูลนำเข้า R ≤ 0, β ≤ 0, VCC ≤ 0 หรือไม่ใช่ตัวเลข → แจ้ง Error ไม่ทำให้หน้าเว็บล้ม
