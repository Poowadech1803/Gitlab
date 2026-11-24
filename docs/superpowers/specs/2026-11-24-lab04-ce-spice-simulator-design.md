# Lab 04 — BJT Common-Emitter Amplifier Simulator v1 · Design

วันที่: 2026-11-24
ฐานที่ใช้: `origin/main` @ `0119b44` (Lab 03 เสร็จสมบูรณ์, 29 tests ผ่าน)
ผู้เขียน: OpenCode (AI-assisted lab) — อยู่ระหว่างรออนุมัติก่อนเริ่ม implement

## 1. Intent / ทำไมต้องทำ

ต่อยอด Flask Web App Lab 03 ของ ENG29 2121 ที่มีอยู่แล้วบน GitHub ให้เป็น
**Common-Emitter Amplifier Simulator v1** ตามใบงาน Lab 04 ที่แนบมา โดยไม่เขียนแอปใหม่ทั้งระบบ
และไม่ทำลาย DC Bias 3 แบบเดิม (Fixed / Emitter / Voltage Divider) หรือชุดทดสอบเดิม

 Definition of Done: ใน Browser เลือกวงจร CE Voltage Divider อ้างอิง กรอกค่าชิ้นส่วน/แหล่งสัญญาณ
แล้วรัน **จริง** ด้วย ngspice ได้ทั้ง `.op`, `.ac`, `.tran` เห็นตัวเลขและกราฟที่มีแกน/หน่วย
แยกแยะผล **SPICE** ออกจากผล **Analytical** ของ Lab 03 ได้ มี error state ที่ตรงไปตรงมา
และมีหลักฐาน B1–B8 ใน `docs/validation.md` พร้อม commit ใน repo

## 2. Goals / Non-goals / Anti-goals

**Goals**
- รักษา `app.py` เดิม, `dc_bias.py`, `templates/index.html`, `static/style.css`, `tests/*` ให้ทำงานเหมือนเดิม
- เพิ่ม `spice_engine.py` ที่สร้าง netlist, เรียก ngspice ผ่าน `subprocess.run([...], shell=False, timeout=...)`, อ่านผลจริง
- เพิ่ม Analysis Mode **DC / AC / Transient** สำหรับ CE Voltage Divider อ้างอิงวงจรเดียว (v1)
- ฟอร์มรับค่า/หน่วยชัด: VCC, R1, R2, RC, RE, RL, Cin, Cout, source amplitude (V peak), frequency (Hz)
- กราฟ Bode (frequency / gain dB / phase deg) และ Waveform (time / Vin / Vout) มาจากข้อมูลที่ parse ได้จากการรันจริง
- แสดง engine status (`idle` / `running` / `success` / `error`), ชื่อ ngspice version และ BJT model ที่ใช้จริง
- บันทึกวิธีติดตั้ง/รันใน README และผลตรวจ B1–B8 ใน validation

**Non-goals (ตามใบงาน)**
- Circuit editor แบบลากวาง, ต่อวงจรอิสระ, AC ของทุก bias mode, FET, เขียน SPICE solver เอง
- Animated overlay บนวงจร, emitter bypass capacitor (`CE`), deployment สำหรับผู้ใช้ภายนอก
- การติดตั้ง Impeccable / Playwright MCP (ไม่มีใน session นี้ — ใช้ Browser tool ที่มีอยู่และบันทึกตามความจริง)

**Anti-goals (ต้องไม่เกิด)**
- ตัวเลข gain/frequency/waveform สำเร็จรูป, กราฟ hard-code, หรือผลเก่าค้างพร้อมสถานะ `success`
- ngspice run ล้มเหลวแล้วเว็บยังดูเหมือนสำเร็จ
- ใส่ค่า/ข้อความจากฟอร์มเข้า command โดยไม่ validate
- ลบ/เขียนทับงาน Lab 03 หรือ branch `bjt-ce-bias` เดิม

## 3. Constraints / สภาพแวดล้อมที่ตรวจแล้ว

- Python 3.12.7, Flask ใน `requirements.txt` (`flask>=3.0`)
- `origin/main` มี Lab 03 ครบ (README ระบุ 29 tests ผ่าน) และยังเป็น base ที่ดีที่สุด
- branch `bjt-ce-bias` ในเครื่อง **diverged** จาก `origin/main` → จะไม่ merge/rebase ตอนนี้ ให้สร้าง branch ใหม่
- **ngspice ไม่ได้ติดตั้ง** และ winget ไม่มี package ชื่อ ngspice
- ไม่มี Starter Kit / ไฟล์ `.cir` / model file ใน repo หรือ Downloads
- แหล่งติดตั้งที่ยืนยันแล้ว: หน้า https://ngspice.sourceforge.io/download.html ระบุ stable `ngspice-47`
  สำหรับ Windows 64-bit เป็นไฟล์ `ngspice-47_64.7z` (ต้องมี 7-Zip เพื่อแตกไฟล์ — winget มี `7zip.7zip`)
- ไม่มี Playwright MCP และไม่มี skill `impeccable` ใน session นี้ → ใช้ OpenCode Browser tool + manual UI polish
- GitHub remote อ่านได้ (public) แต่ `gh` ยังไม่ล็อกอิน → commit ได้เฉพาะ local ยัง push ไม่ได้จนกว่าผู้ใช้จะล็อกอิน

## 4. Approaches ที่พิจารณา

| แนวทาง | ข้อดี | ข้อเสีย | สถานะ |
|---|---|---|---|
| A. ติดตั้ง ngspice 47 + ใช้ BJT model ที่เขียน/อ้าง来源ชัดเจนใน repo | ได้ผลจริงครบ B2–B6, ตรง DoD มากที่สุด | ต้องติดตั้ง executable ภายนอกครั้งเดียว; ต้องระบุที่มาของ model เองเพราะไม่มี Starter Kit | **เลือก (ผู้ใช้เลือกข้อ 1)** |
| B. รอ Starter Kit จากอาจารย์แล้วใช้ netlist/model ของอาจารย์ | ตรงตามใบงานที่สุดด้าน provenance | ตอนนี้ยังไม่มีไฟล์ → ทำต่อไม่ได้ | ยังไม่เลือก; ถ้าได้ไฟล์มาทีหลังให้แทนที่ model file |
| C. สร้าง adapter + UI ก่อนโดยยังไม่ติดตั้ง engine | เริ่มเขียนโค้ดได้ทันที | พิสูจน์ผล SPICE ไม่ได้ ต้องบันทึก B2–B6 เป็น NOT RUN | ปฏิเสธ (ผู้ใช้เลือกข้อ 1) |

## 5. สิ่งที่ตัดสินแล้ว (Decisions — เป็นของ builder ไม่ใช่ของผู้ใช้)

1. **Branch**: สร้าง `lab04-ce-simulator` จาก `origin/main` (`0119b44`) ด้วย `git switch -c ... origin/main`
   ไม่แตะ `bjt-ce-bias`; ใช้ git worktree ถ้าต้องการแยก workspace ตาม skill `using-git-worktrees`
2. ** ngspice install**: ติดตั้ง 7-Zip ผ่าน winget ถ้าจำเป็น, โหลด `ngspice-47_64.7z` จาก SourceForge
   แตกไปยัง `%LOCALAPPDATA%\ngspice-47` (นอก repo) engine หา exe ตามลำดับ:
   env `NGSPICE_EXE` → `ngspice` ใน PATH → path ที่พบบ่อย → error พร้อมวิธีตั้งค่า
   **ห้าม commit ไบนารี ngspice**
3. **BJT model**: เนื่องจากไม่มี Starter Kit ให้สร้าง `spice/q1_npn.model` ที่ระบุพารามิเตอร์
   แบบ 2N3904-style ที่พิมพ์ออกมาให้เห็นชัดและอ้างว่าเป็น "local documented model (ไม่ใช่ของอาจารย์)"
   แสดงชื่อโมเดลบนหน้าเว็บและใน validation; ถ้าผู้ใช้ได้ Starter Kit มาภายหลังให้แทนที่ไฟล์นี้และบันทึก version ใหม่
4. **Netlist อ้างอิง** (ชื่อ node): `vcc`, `b`, `c`, `e`, `in`, `out` ; ground = `0`
   - `VCC vcc 0 DC <vcc>`, `VIN in 0 DC 0 AC <amp> SIN(0 <amp> <freq>)`
   - `R1 vcc b`, `R2 b 0`, `RC vcc c`, `RE e 0`, `Q1 c b e Q1_NPN`
   - `Cin in b`, `Cout c out`, `RL out 0` (baseline ไม่มี `CE`)
   - วัด **Vin ที่ node `in`** และ **Vout ที่ node `out`** (หลัง Cout บน RL) — ต้องเขียนให้ชัดใน UI/docs
   - ค่าเริ่มต้นตามใบงาน: VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ,
     RL 10 kΩ, Cin=Cout=10 µF, amp 10 mV peak, freq 1 kHz
5. **Analysis directives**: `.op`, `.ac dec 20 1 10Meg`, `.tran <step> <stop>`
   โดย `stop = max(5 / freq, 1 ms)` และ `step = stop / 2000` (จำกัดจำนวนจุดไม่ให้เกิน ~2001)
6. **การรัน**: `subprocess.run([exe, "-b", "-o", log, "-r", raw, netlist],
   cwd=<tempdir ต่อรอบ>, capture_output=True, text=True, timeout=<30–60 s>, shell=False)`
   ใช้ `tempfile.TemporaryDirectory()` ต่อการรันหนึ่งครั้ง; ไม่ใช้ shell=True; ไม่เขียนไฟล์ลง repo ตอนรัน
7. **การอ่านผล (left to builder ให้ spike ก่อน)**: ให้ทดลองรันจริงครั้งหนึ่งเพื่อยืนยันรูปแบบผล
   ลำดับที่แนะนำ: อ่านตารางจาก `.print` ใน log (`vdb`/`vp` สำหรับ AC, `v(in)`/`v(out)` สำหรับ tran,
   operating point สำหรับ `.op`); ถ้า log ไม่น่าเชื่อถือให้ parse ไฟล์ `-r raw` แทน
   parser ต้องรองรับทั้ง ascii และ binary (sniff float/double จากขนาดไฟล์เทียบ No.Variables × No.Points)
   เก็บ raw/log ตัวอย่างขนาดเล็กไว้เป็นหลักฐานใน `docs/` พร้อมวิธีสร้างซ้ำ (ไม่เก็บ run ทุกครั้ง)
8. **ผลที่คำนวณต่อจากข้อมูลจริง**: DC = `vb=v(b), ve=v(e), vc=v(c), vce=vc-ve, ic` จากกระแสที่ตรวจเครื่องหมาย
   เทียบกับ `i(rc)`/`-i(vcc)` แล้วบันทึกวิธีที่เลือก; AC = `gain_db=vdb(out)-vdb(in)`,
   `phase_deg=vp(out)-vp(in)` ; หา fL/fH จากจุด -3 dB เทียบ midband ถ้ามี ไม่เช่นนั้นแสดง
   "not determined in sweep range" ; Transient = ค่า `time, vin, vout` จริง + สรุปทิศทางเฟสจากข้อมูล
   (เช่น สหสัมพันธ์ระหว่าง vin/vout) ห้ามเดาจากภาพ
9. **กราฟ**: สร้าง **inline SVG server-side** จาก array จริง (ฟังก์ชันใน `plots.py`) ไม่เพิ่ม matplotlib
   ต้องมีแกน+หน่วย+legend: Bode = `Frequency (Hz)` / `Gain (dB)` / `Phase (°)` ;
   Tran = `Time (ms)` / `Vin, Vout (V)` ; ไม่มี placeholder art
10. **Route**: คง `GET /` และ `POST /calculate` เดิมทุกประการ (ต้องผ่าน tests เดิม 29 ตัว)
    เพิ่ม `POST /simulate` สำหรับ SPICE โดยเฉพาะ; ใช้ `action=mode` แบบเดิมสำหรับเปลี่ยน analysis/bias view
    ถ้า error → render หน้าเว็บพร้อม error list, status = error, **result/graph เป็น None เสมอ**
11. **Validation**: ตรวจ B1–B8 ด้วย OpenCode Browser tool (โหลด skill `browser` ก่อนใช้งาน)
    บันทึก Method/Input/Expected/Observed/Evidence/Status ลง `docs/validation.md` ตามความจริง
    ถ้า tool ไม่ได้รันให้เขียน NOT RUN พร้อมเหตุผล ห้ามเขียน PASS
12. **Commit/Push**: commit local บน branch ใหม่เป็นชุด ๆ (engine → web/UI → tests → docs)
    **ยังไม่ push** เพราะ `gh` ไม่ได้ล็อกอิน; แจ้งผู้ใช้ให้ล็อกอินหรือ push เองหลังตรวจแล้ว

## 6. โครงไฟล์ที่คาดว่าจะเปลี่ยน/เพิ่ม

```
spice_engine.py        # ใหม่: validation, netlist builder, runner, parser, SpiceError
plots.py              # ใหม่: SVG จากข้อมูลจริง (Bode + waveform)
spice/q1_npn.model    # ใหม่: local documented BJT model (แทนที่ได้ถ้าได้ Starter Kit)
templates/index.html  # แก้: เพิ่ม section "Lab 04 CE Simulator" + analysis tabs + status + plots
static/style.css      # แก้: responsive 3-column → 2-section, error/status/graph styles
static/app.js         # ไม่บังคับ; ใช้เฉพาะถ้าจำเป็นสำหรับ tab/mode switching
tests/test_spice_engine.py  # ใหม่: validation/netlist/parser/error paths (fixture เล็ก ๆ)
tests/test_lab04_web.py     # ใหม่: route, status, ไม่มี stale result, error
docs/validation.md    # แก้: เพิ่มตาราง B1–B8 + ngspice version + model provenance
README.md             # แก้: install ngspice/7-Zip, environment variable, run steps, SPICE vs Analytical
docs/superpowers/specs/...design.md  # ไฟล์นี้
.gitignore            # ตรวจ/เพิ่ม *.raw *.log เฉพาะรันชั่วคราว (ไม่ commit binary)
```
`dc_bias.py`, `requirements.txt`, `tests/test_dc_bias.py`, `tests/test_web.py` ไม่เปลี่ยนแปลง

## 7. Error paths ที่ต้องมี

| กรณี | พฤติกรรม |
|---|---|
| ค่าไม่ใช่ตัวเลข / ค่าติดลบ / 0 / `nan` / `inf` / amp หรือ freq ผิดช่วง | Error list จาก Flask, status error, ไม่สร้าง netlist |
| หา ngspice.exe ไม่เจอ | Error พร้อม `NGSPICE_EXE` + วิธีติดตั้ง, ไม่มีกราฟ |
| ngspice คืน code ≠ 0 / log มี error | แสดง error ย่อหน้าที่อ่านได้ + ชื่อ log, ไม่มีกราฟ |
| timeout / output ว่าง / parse ไม่ได้ | Error ระบุสาเหตุ, ไม่แสดงผลรอบก่อน |
| เปลี่ยน input แล้วรันใหม่ | ต้องได้ข้อมูลชุดใหม่ (B3/B6) — ห้ามใช้ cache ของรอบก่อน |

## 8. สิ่งที่เหลือให้ builder ตัดสินเอง (ไม่ต้องถามผู้ใช้เพิ่ม)

- รูปแบบผลจริงของ ngspice 47 ในเครื่องนี้ (`.print` log หรือ raw) — ให้ spike แล้วบันทึกที่เลือก
- รายละเอียด CSS ที่พอดีกับหน้าจอ 1280 px และ 390 px
- ว่าจะใช้ `static/app.js` หรือ POST action ธรรมดาสำหรับสลับ tab
- หมายเลข winget package ของ 7-Zip และวิธีดาวน์โหลด SourceForge ที่เสถียรในเครื่องนี้

## 9. หลักฐานที่ต้องส่งท้ายงาน

- `git log` ของ branch ใหม่ + commit SHA
- ผล `python -m unittest discover -s tests -v` (ต้อง OK รวมเดิม + ใหม่)
- ตาราง B1–B8 พร้อม screenshot desktop/mobile จาก Browser จริง
- ข้อความสั้น 3–5 บรรทัด: AI ทำอะไร / นักศึกษาต้องตรวจอะไรเอง (ใส่ใน README)
- หมายเหตุว่า push ยังไม่ทำจนกว่า GitHub auth จะพร้อม
