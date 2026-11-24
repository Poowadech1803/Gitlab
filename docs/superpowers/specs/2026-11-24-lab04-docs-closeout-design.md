# Lab 04 — Documentation close-out · Design

วันที่: 2026-11-24
Base: `main` @ `e9b2ffb` (โค้ด Lab 04 ครบ + design spec เดิม; push แล้ว)

## Intent

ปิดเอกสารที่ผู้ใช้ขอให้ครบ และทำให้ตาราง B1–B8 เห็นทันทีที่เปิด repository
โดยไม่แตะพฤติกรรมแอปหรือแต่งหลักฐานใหม่

## Goals

- `README.md`: ใส่ Repository URL + Commit SHA สำหรับ Lab 04 อย่างชัดเจน,
  ขั้นติดตั้ง Python dependencies/ngspice, วิธีรัน server และ browser,
  **copy ตาราง B1–B8 มาแสดงใน README**, บันทึกการปรับ UI จาก commit `e578b43`
  พร้อม screenshot จริง 3 ไฟล์, และบันทึก 3–5 บรรทัด AI/nักศึกษา
- `docs/validation.md`: คงตาราง B1–B8 เดิมทุกตัวอักษร แต่เพิ่มหมวด
  แหล่งอ้างอิง / ความคลาดเคลื่อน / ข้อจำกัดแบบรวมศูนย์
- ไม่เปลี่ยน `app.py`, `dc_bias.py`, `spice_engine.py`, `plots.py`, tests
- Verification: `unittest discover -s tests` ต้องยัง 96/96 OK, `git diff --check` สะอาด,
  push แล้วตรวจ raw GitHub ว่า README มีตาราง B1–B8

## Non-goals / Anti-goals

- ไม่แก้โค้ดหรือสร้าง screenshot ก่อน/หลังปลอม
- ไม่ claims ว่า Playwright MCP หรือ Impeccable เคยรัน (ยังเป็น **NOT RUN** ตามความจริง)
- ไม่เขียน SHA ของ commit เอกสารชุดนี้ลงไปเอง (self-referential) —ใช้อ้างอิง `e9b2ffb`
  เป็น “Lab 04 implementation snapshot”

## Approaches

1. **Docs-only commit บน `main` (เลือก)** — อ้าง SHA `e9b2ffb`, copy ตาราง B1–B8 ลง README,
   แก้เฉพาะ docs. ตรงที่สุด, ไม่ rewrite history, ไม่ต้อง PR
2. Amend commit เก่า (ไม่เลือก) — เปลี่ยน SHA ที่เคย push และยัง self-referential อยู่ดี
3. แยก branch + PR (ไม่เลือก) — `gh` ยังไม่ authenticated และผู้ใช้ต้องการ push ตรง ๆ เหมือนเดิม

## Decisions

- ใช้ `e9b2ffb` เป็น commit อ้างอิง Lab 04 (stable หลัง push)
- หลักฐาน UI = บันทึกการปรับจาก `e578b43` + `b2-dc-desktop.png`, `b4-ac-desktop.png`,
  `b8-mobile-css-forced.png`; ไม่มี before/after คู่จริงจึงไม่สร้างขึ้นมาเอง
- หมวดREFERENC/ข้อจำกัดรวมข้อมูลจาก `docs/spice-samples/README.md` และ validation เดิม
- ทุกผลลัพธ์ B1–B8 ต้องคงตัวเลขเดิมเป๊ะ ไม่ปรับแต่ง

## Files

- `README.md`
- `docs/validation.md`
- `docs/superpowers/specs/2026-11-24-lab04-docs-closeout-design.md`

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
git diff --check
git add ... ; git commit ... ; git push origin main
```

หลัง push ตรวจ `https://raw.githubusercontent.com/Poowadech1803/Gitlab/main/README.md`
ว่ามี `| B1 |` ถึง `| B8 |` ครบ
