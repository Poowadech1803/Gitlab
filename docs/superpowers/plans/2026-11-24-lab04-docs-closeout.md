# Lab 04 Documentation Close-out Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Lab 04 handoff complete on GitHub: repo URL + commit SHA, install/run steps, B1–B8 table visible at repo root, honest UI polish record with real screenshots, consolidated references/limitations, and the 3–5 line AI/student note.

**Architecture:** Docs-only change on `main`. Mirror the existing B1–B8 table from `docs/validation.md` into `README.md` instead of rewriting results. Append one new section to `docs/validation.md`. Reference the already-pushed implementation snapshot `e9b2ffb` so the docs never contain their own future SHA.

**Tech Stack:** Markdown, Git, PowerShell, Python unittest (verification only).

**Spec:** `docs/superpowers/specs/2026-11-24-lab04-docs-closeout-design.md`

## Global Constraints

- Repository URL verbatim: `https://github.com/Poowadech1803/Gitlab`
- Lab 04 implementation snapshot SHA verbatim: `e9b2ffb`
- Engine label verbatim: `47-1 (MSYS2 package, upstream ngspice 47)`
- Model verbatim: `Q1_NPN`
- Screenshot paths verbatim: `docs/validation-screenshots/b2-dc-desktop.png`, `docs/validation-screenshots/b4-ac-desktop.png`, `docs/validation-screenshots/b8-mobile-css-forced.png`
- UI polish commit verbatim: `e578b43`
- Playwright MCP and Impeccable must remain recorded as **NOT RUN**
- B1–B8 numbers/statuses must be copied, never re-derived or edited
- No application source or test files may change
- Use `.venv\Scripts\python.exe` for Python commands

## Review Focus

- **README table drifts from validation:** pin by copying rows B1–B8 verbatim from `docs/validation.md`; verify with a text search for `| B1 |` … `| B8 |` in both files (Task 1 Step 4).
- **Self-referential SHA:** README must say `e9b2ffb` is the implementation snapshot, not the docs commit; verify by searching README for the exact SHA and the word `snapshot` (Task 1 Step 4).
- **Fake UI evidence / false tool claims:** no before/after screenshot is invented; Impeccable stays `NOT RUN`; verify by grep for `NOT RUN` and by confirming only the three committed screenshot paths are referenced (Task 1 Step 4, Task 3 Step 2).
- **Accidental rewrite of validation results:** `git diff docs/validation.md` must show additions only; verify with `git diff --numstat docs/validation.md` (Task 2 Step 3).
- **App regression:** full suite must still report `Ran 96 tests` … `OK` (Task 3 Step 1).

---

### Task 1: README handoff block

**Files:**
- Modify: `README.md` (append inside/after the existing `## Lab 04 — ngspice CE Simulator (B1–B8)` section)
- Read-only: `docs/validation.md:133-142`, `docs/spice-samples/README.md`

**Interfaces:**
- Consumes: B1–B8 markdown rows exactly as written in `docs/validation.md`
- Produces: a README subsection containing URL, SHA, install/run commands, mirrored table, UI record, screenshots, AI/student note

- [ ] **Step 1: Add handoff identity block**
  Append a subsection titled `### Handoff identity` containing:
  - `Repository: https://github.com/Poowadech1803/Gitlab`
  - `Lab 04 implementation snapshot (commit SHA): e9b2ffb`
  - one sentence: this SHA is the pushed code snapshot before the documentation-only commit, so the docs do not contain their own SHA.

- [ ] **Step 2: Add/verify install and run commands**
  Ensure the Lab 04 section already contains: `python -m venv .venv`, `python -m pip install -r requirements.txt`, the MSYS2 ngspice package name and SHA256, `$env:NGSPICE_EXE = ...`, PATH prepend, `python -m flask --app app run`, and `http://127.0.0.1:5000/`. If any item is missing, add it; do not duplicate an existing identical line.

- [ ] **Step 3: Mirror B1–B8 and add UI/student notes**
  - Add `### B1–B8 validation summary (mirrored from docs/validation.md)` and paste rows B1–B8 verbatim, including the table header/separator.
  - Add `### UI polish record (no Impeccable run)` stating: Impeccable = NOT RUN; actual polish came from commit `e578b43` (`static/app.js`, `static/style.css`, `templates/index.html`); manual desktop/mobile inspection + task-scoped code review were used; no fabricated before/after pair exists.
  - Reference the three screenshot paths with Markdown image links.
  - Add `### AI และสิ่งที่นักศึกษาตรวจเอง` with exactly 4 short lines: AI created `spice_engine.py`/`plots.py`/`/simulate`/SVG; AI added docs/tests; student must verify unit conversion, one hand calculation vs `dc_bias.py`, real ngspice values vs Analytical, and B1–B8 via browser.

- [ ] **Step 4: Verify README content**
  Run:
  ```powershell
  Select-String -Path README.md -Pattern '\| B[1-8] \|'
  Select-String -Path README.md -Pattern 'e9b2ffb','NOT RUN','e578b43','b2-dc-desktop.png','b4-ac-desktop.png','b8-mobile-css-forced.png'
  ```
  Expected: 8 B-row matches and all six literal strings present.

### Task 2: Validation references and limitations

**Files:**
- Modify: `docs/validation.md` (append after the existing `Full suite at handoff` paragraph)

**Interfaces:**
- Consumes: existing B1–B8 table and `docs/spice-samples/README.md` facts
- Produces: one new `### References`, `### Observed discrepancies`, `### Limitations` block; no edits above it

- [ ] **Step 1: Append references**
  Add `### References` listing: the Lab 04 handout (`Lab04_BJT_Amplifier_Simulator_2-2569.html`), ngspice 47 MSYS2 package provenance + SHA256, `docs/spice-samples/README.md`, `dc_bias.py` (Analytical β=100, VBE=0.70), and this design/plan.

- [ ] **Step 2: Append discrepancies and limitations**
  Add `### Observed discrepancies` with: SPICE vs Analytical numbers from B2, B4 AC figures after RE=1.5 kΩ vs sample logs at RE=1 kΩ, and `-i(vcc)` approximation for `ic_ma`.
  Add `### Limitations` with: no bypass capacitor, model is local Q1_NPN not instructor Starter Kit, version label from package metadata (CLI banner unavailable), B8 CSSOM-forced mobile check, Playwright MCP/Impeccable NOT RUN, `f_high` not determined in sweep range.

- [ ] **Step 3: Verify additions only**
  Run:
  ```powershell
  git diff --numstat -- docs/validation.md
  ```
  Expected: additions > 0, deletions = 0.

### Task 3: Verify, commit, push

**Files:**
- Modify: none (verification and VCS only)

- [ ] **Step 1: Run full suite**
  Run: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
  Expected: `Ran 96 tests` and `OK`, exit 0.

- [ ] **Step 2: Diff hygiene**
  Run: `git diff --check`
  Expected: no output, exit 0. Confirm `git status --short` lists only the three intended docs files.

- [ ] **Step 3: Commit and push**
  ```bash
  git add README.md docs/validation.md docs/superpowers/specs/2026-11-24-lab04-docs-closeout-design.md docs/superpowers/plans/2026-11-24-lab04-docs-closeout.md
  git commit -m "docs: complete Lab 04 handoff and mirror B1-B8 into README"
  git push origin main
  ```

- [ ] **Step 4: Verify remote**
  Fetch `https://raw.githubusercontent.com/Poowadech1803/Gitlab/main/README.md` and confirm `| B1 |` through `| B8 |` are present; report local and remote SHA equality.
