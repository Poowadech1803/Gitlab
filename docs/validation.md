# Validation — Lab 02

## Independent hand calculation (reference circuit)

อินพุต: VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70 V

```
VTH = 12 × 22000 / (100000 + 22000)        = 2.163934 V
RTH = 100000 × 22000 / 122000              = 18032.787 Ω
IB  = (2.163934 − 0.70) / (18032.787 + 101 × 1000)
                                           = 1.463934 / 119032.787
                                           = 1.22986e-5 A  ≈ 12.30 µA
IC  = 100 × IB                             = 1.22986 mA
IE  = 101 × IB                             = 1.24216 mA
VE  = IE × RE                              = 1.24216 V
VB  = VE + VBE                             = 1.94216 V
VC  = 12 − IC × 2200                       = 9.29431 V
VCE = VC − VE                              = 8.05216 V
```

ตรวจ KVL: VCE = VCC − IC·RC − IE·RE = 12 − 2.7057 − 1.2422 = 8.0521 ✓
ตรวจ KCL: IE = IC + IB ✓ (1.22986 + 0.01230 = 1.24216 mA)

ผลจากเว็บตรงกับการคำนวณมือทุกจุดทศนิยม 4 ตำแหน่ง → **ผ่าน A3**

## Validation cases (A4)

| อินพุต | ผลที่คาด |
|---|---|
| R1 = −1000 | Error "R1 ต้องมากกว่า 0 Ω" |
| beta = 0 | Error "β ต้องมากกว่า 0" |
| VCC = "abc" | Error "VCC ต้องเป็นตัวเลข" |
| ไม่กรอก RE | Error "missing RE" |

## Region cases (A5)

| อินพุต | Region | Warning |
|---|---|---|
| R2 = 1 Ω (VTH=0.00012 V < VBE) | cutoff | แจ้งว่าสมการ Forward-Active ใช้ไม่ได้ |
| RC = 100 kΩ (VCE ≈ −inf → clamp ต่ำ) | saturation | แจ้งว่า IC จริงถูกจำกัดโดย RC |

## Automated tests

```
python -m unittest discover -s tests -v
```

- `test_dc_bias.py`: 11 unit tests — reference values, KCL/KVL consistency,
  cutoff, saturation, validation (negative/non-numeric/zero/missing)
- `test_web.py`: 6 HTTP tests ผ่าน Flask test client — GET 200 + form,
  POST backend calculation, error pages, cutoff/saturation warnings
