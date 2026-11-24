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

## บทบาทของ MCP และเครื่องมือที่ใช้จริง

**MCP (Model Context Protocol)** คือมาตรฐานที่ให้แอป AI รู้ว่ามีเครื่องมืออะไร เรียกใช้เครื่องมือนั้น
และรับผลกลับมา ใน Lab นี้ **OpenCode** เป็นแอปที่มี MCP Client ส่วน **Playwright MCP** เป็น MCP Server
ที่เปิดเครื่องมือควบคุมเบราว์เซอร์ให้เอเจนต์ใช้

เส้นทางข้อมูลตามที่ใบงานอธิบาย:

```
OpenCode (MCP Client)
   │  MCP · ส่งคำสั่ง เปิด URL / กรอก / คลิก / อ่านหน้าเว็บ
   ▼
Playwright MCP (MCP Server)  →  Browser  ←HTTP→  Flask + Python
   ▲                                                  │
   └────────── MCP · ส่ง snapshot กลับ ───────────────┘
```

- เบราว์เซอร์เป็นฝั่งที่ส่งคำขอ **HTTP** ไป Flask และแสดงผลลัพธ์
- OpenCode คุยกับ MCP ผ่านคำสั่งเครื่องมือ **ไม่ใช่ HTTP** — สองเส้นทางนี้ทำหน้าที่ต่างกัน
- `browser-acceptance-check` skill บอก **ขั้นตอน/หลักฐาน** ที่ต้องรายงาน แต่ไม่ได้เปิดเว็บเอง;
  MCP เป็นตัวทำให้เรียกเครื่องมือได้; Flask ยังทำงานเหมือนเดิมและไม่ต้องลง Playwright ใน `requirements.txt`

**เหตุผลที่เปลี่ยนเครื่องมือใน session นี้:** Playwright MCP ไม่ได้ configure ใน OpenCode ของเครื่องนี้
จึงใช้ **OpenCode Browser** (`tools.browser.*` — Chromium ในตัว OpenCode Desktop) ซึ่งเป็น
"Browser Tool ที่มีใน OpenCode Desktop" ตามที่ใบงานอนุญาตให้ใช้เป็นวิธีสำรอง

**เกณฑ์การให้คะแนนเท่ากันทุกวิธี:** ใบงานระบุชัดว่าให้ใช้เกณฑ์ A1–A5 และ tolerance เดียวกัน
โดยระบุวิธีจริงว่าเป็น `Playwright MCP`, `OpenCode Browser` หรือ `Manual` — ไม่มีการลดคะแนน
เพราะใช้ OpenCode Browser แทน Playwright MCP ในครั้งนี้ ผลทุกกรณีในตารางข้างบนจึงเทียบกับ
เกณฑ์เดียวกันกับที่ใช้กับ Playwright MCP ทุกประการ

## การตรวจสมการกับโค้ดที่ AI สร้าง (Rubric ข้อ 1)

AI เขียน `dc_bias.py` ตามสมการ Engineering Electronics แล้วนำกลับมาเทียบทีละสมการ:

| สมการที่เรียน | ที่อยู่ในโค้ด | สิ่งที่ตรวจ |
|---|---|---|
| `IB = (VTH−VBE)/(RTH+(β+1)RE)` | `solve_divider()` | VTH/RTH ตรงมือ 2.163934 V / 18032.787 Ω |
| `IB = (VCC−VBE)/RB` | `solve_fixed()` บรรทัด ~225 | RB=1 MΩ → 11.30 µA ตรงมือ |
| `IB = (VCC−VBE)/[RB+(β+1)RE]` | `solve_emitter()` บรรทัด ~232 | 10.2634 → 9.4010 µA เมื่อ RE 1→2 kΩ |
| `IC=β·IB, IE=(β+1)IB, VE=IE·RE, VC=VCC−IC·RC, VCE=VC−VE` | `_finish()` | ใช้ helper ร่วมกันทั้ง 2 โหมดใหม่ → คีย์/หน่วยเหมือนกัน |
| หน่วย Ω/kΩ/MΩ → Ω | `app.py` `UNIT_FACTORS` + `RESISTOR_FIELDS_BY_MODE[mode]` | แปลงครั้งเดียว ก่อน `parse_input` |
| เลือกฟังก์ชันตามโหมด | `app.py` `SOLVERS[mode](bias)` + `MODE_FIELDS` | ไม่มี silent fallback เมื่อ mode ไม่รู้จัก |

`BiasResult.to_dict()` ส่งผลเป็น **dict** ที่มีคีย์คงที่ทุกโหมด:
`vb, ve, vc, vce` (V), `ic_ma, ie_ma` (mA), `ib_ua` (µA), `region`, `warnings` —
`templates/index.html` อ่านจาก dict นี้โดยตรง (ทดสอบใน `tests/test_dc_bias.py::TestResultDict`)

## นักศึกษาทวนเองอย่างน้อย 1 กรณี (Rubric ข้อ 3)

ทำซ้ำด้วยมือที่หน้า `http://127.0.0.1:5000/` 1 กรณี (แนะนำ A4 เพราะเห็นทิศทางชัด):
เลือก **Emitter** → RB=1 เลือก MΩ → RC=2.2 kΩ → RE=**2** kΩ → β=100 → VBE=0.70
→ กด **Calculate DC Bias** → ต้องเห็น **IC 0.94 mA · VCE 8.03 V**
(ถ้าได้ 1.03 mA / 8.71 V แสดงว่า RE ยังเป็น 1 kΩ — ให้ไล่ ฟอร์ม → ชื่อฟิลด์ → แปลงหน่วย → ฟังก์ชัน → ผล)

*ช่องบันทึกผลที่นักศึกษาทวนเอง: `RE=2 kΩ → IC ______ mA, VCE ______ V, ตรง/ไม่ตรง ______*`

## หมายเหตุการตรวจ

- ทุกกรณีใช้การกรอกผ่านฟอร์มจริงในเบราว์เซอร์ + กดปุ่มคำนวณจริง ไม่ได้ใช้ curl หรืออ่าน source แทน
- หลังเปลี่ยนโหมด กด **เปลี่ยนโหมด** แล้วอ่าน snapshot ใหม่ก่อนกรอก (ตามที่ใบงานแนะนำ)
- กรณี A5 พิสูจน์ว่า Flask ตรวจอินพุตเอง: ข้อความ error ถูก render จาก `errors` ที่ `app.py` ส่งกลับ
  และ `result = None` ทำให้ตารางผลหายไป ไม่ใช่ผลเก่าจาก A4
- จำนวน tests ที่ผ่านหลังเพิ่ม dict interface: `python -m unittest discover -s tests -v` → **OK 30/30**
  (tests เดิม Lab 02 ทุกตัวยังอยู่ครบ + `TestResultDict`)

---

## Lab 04 — Browser Validation (B1–B8)

Controller-observed real Flask server on `http://127.0.0.1:5000/` + ngspice 47-1, in-app
Chrome via **OpenCode Browser** (`tools.browser.*`). The table below transcribes the SDD
ledger verbatim: no result was upgraded, invented or softened. Engine shown in results:
`47-1 (MSYS2 package, upstream ngspice 47)`; SPICE model: `Q1_NPN` from
`spice/q1_npn.model` (local documented Gummel-Poon-style 2N3904 model, **not** the
instructor's Starter Kit model). The CE circuit has **no bypass capacitor**.

| Case | Method / Input | Expected | Observed | Evidence | Status |
|---|---|---|---|---|---|
| B1 | `GET /`, then click **Calculate DC Bias** (`POST /calculate`) with Lab 03 defaults | Lab 03 and Lab 04 both render; DC result matches Lab 03 reference; no `#sim-form` | Lab 03 + Lab 04 rendered; **VB 1.94 V / VE 1.24 V / VC 9.29 V / VCE 8.05 V / IC 1.23 mA**; no `#sim-form` | page snapshot for GET and POST | PASS |
| B2 | Select `dc`, click **Run SPICE simulation** (`POST /simulate`) at defaults | Status success; engine ngspice; version `47-1 (MSYS2 package, upstream ngspice 47)`; model `Q1_NPN`; SPICE and Analytical tables | Status success; engine ngspice; version `47-1 (MSYS2 package, upstream ngspice 47)`; model `Q1_NPN`. SPICE **VB 2.00 V / VE 1.33 V / VC 9.09 V / VCE 7.75 V / IC 1.42 mA** vs Analytical **1.94 / 1.24 / 9.29 / 8.05 / 1.23**. Warning: `i(rc) missing; used -i(vcc) for ic_ma` | page snapshot; `docs/validation-screenshots/b2-dc-desktop.png` | PASS |
| B3 | Change RE 1 → 1.5 kΩ, rerun `dc` | Higher RE raises VE, VC, VCE and lowers IC in both models | SPICE VE 1.33 → 1.39 V, VC 9.09 → 9.98 V, VCE 7.75 → 8.59 V, IC 1.42 → 1.02 mA; Analytical also moved VE 1.24 → 1.31 V and IC 1.23 → 0.86 mA | page snapshot after rerun | PASS |
| B4 | Change analysis to `ac` (**Change analysis**), then **Run SPICE simulation** | Mode switch leaves Status idle, 0 tables and 0 SVG (no ngspice run); run succeeds with labeled Bode SVG and two polylines | After change: Status idle, 0 tables, 0 SVG (no ngspice run). Run: success, Bode SVG with `Frequency (Hz)` / `Gain (dB)` / `Phase (°)`, 2 polylines, `midband_gain_db 1.3762`, `f_low_hz 1.5849`, `f_high_hz None` + "not determined in sweep range" warning | page snapshot; `docs/validation-screenshots/b4-ac-desktop.png` | PASS |
| B5 | Change analysis to `tran`, then **Run SPICE simulation** | Mode switch idle with 0 tables/0 SVG; run succeeds with waveform SVG and inverted phase relation | Idle: 0 tables/0 SVG. Run: success, waveform SVG `Time (ms)` / `Vin, Vout (V)`, 2 polylines, phase relation `inverted`; traces leave the same start point in opposite directions | page snapshot | PASS |
| B6 | Change amp 10 → 50 mV and freq 1 → 2 kHz, rerun `tran` | Polylines and axis ticks rescale; inversion retained | Polyline points changed; voltage ticks +/-0.0117 → +/-0.0586 V; time axis 0..5 → 0..2.5 ms; still inverted | page snapshots before/after | PASS |
| B7 | Set RE=0, rerun `dc` | Status error naming RE; no stale result tables or plots | Status error; error `RE ต้องมากกว่า 0 (RE must be > 0)`; 0 tables; 0 SVG; no stale `SPICE (ngspice)` / `Analytical (Lab 03)` / `Vin, Vout (V)` text | page snapshot after error | PASS |
| B8 | Inspect computed `.sim-layout` on desktop; emulate mobile by forcing the CSS media blocks at a 390 px document width; capture screenshot | Desktop two-column layout; mobile single stacked column with no horizontal overflow | Desktop `.sim-layout` computed 360px 824px; at forced 390px document width: single column 332px, form and output stacked at the same left offset, SVG 310px fits 332px, body `scrollWidth=clientWidth=390`. Harness has no true viewport emulation or window resize, so mobile is a CSSOM-forced check plus screenshot, **not** a native 390px viewport | CSSOM measurements; `docs/validation-screenshots/b8-mobile-css-forced.png` | PASS (caveat) |

**B8 caveat (shared browser tab):** unrelated `POST /simulate` and `POST /calculate` appeared
in the server log mid-run. Every check above re-navigated and used a fresh snapshot, so the
recorded state belongs to the stated step.

B4's AC figures (`midband_gain_db 1.3762`, `f_low_hz 1.5849`) were measured after B3 changed RE from 1 kΩ to 1.5 kΩ, whereas the default-input sample logs in [`docs/spice-samples/README.md`](spice-samples/README.md) (`4.8896 dB`, `1.7783 Hz`) use RE = 1 kΩ.

**Full suite at handoff:** `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
→ `Ran 96 tests` … `OK`. Model provenance, real spikes and the `ic_ma` sign derivation are
in [`docs/spice-samples/README.md`](spice-samples/README.md).

