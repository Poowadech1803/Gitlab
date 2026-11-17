# BJT Bias Three Modes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Extend the existing Lab 2 Flask app so `/calculate` solves Fixed Bias and Emitter Bias in addition to the unchanged Voltage Divider Bias.

**Architecture:** Keep the HTTP layer thin. `dc_bias.py` owns all engineering equations and mode-aware validation; `app.py` only maps form fields to the selected solver; `templates/index.html` shows only fields the selected mode uses. Existing `BiasResult` and all existing tests remain valid.

**Tech Stack:** Python 3.12, Flask, Jinja2, `unittest`

**Spec:** `docs/superpowers/specs/2026-11-17-bjt-bias-three-modes-design.md`

## Global Constraints

- Divider input `solve(BiasInput)` and `parse_input(data)` must keep their current signatures and numeric results.
- All equations stay in `dc_bias.py`; never in `templates/index.html` or JavaScript.
- Resistances arrive in Ω inside solvers. Form units: `ohm`=1, `kohm`=1e3, `mohm`=1e6.
- Result fields/units: `vb`, `ve`, `vc`, `vce` in V; `ic_ma` in mA; `ib_ua` in µA.
- Forward-Active only: warn when `ib <= 0` or `vce <= 0.2` V for the new modes. Do not solve cutoff/saturation regions.
- No new dependencies, no new unittest files, no SPICE/AC/load-line work.
- Existing test command: `python -m unittest discover -s tests -v`.

## Review Focus

- Unknown `mode` value must produce an error, never silently fall back to divider — pinned in Task 2.
- Switching mode (`action=mode`) must clear the previous result — pinned in Task 2.
- Fixed mode must not demand R1/R2/RE; Emitter must demand RE — pinned in Task 1 and Task 2.
- `nan`/`inf` numeric text must be rejected as invalid input — pinned in Task 1.
- Invalid input (e.g. `RB=0`) must show an error and never display the previous run's result — pinned in Task 2.
- `VCE <= 0.2` in Fixed/Emitter must show a model-limitation warning — pinned in Task 1.

---

### Task 1: Mode-aware engineering module

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py` (add cases; keep every existing case)

**Interfaces:**
- Consumes: existing `BiasInput`, `BiasResult`, `_validate`, `parse_input`, `solve`.
- Produces:
  - `MODE_FIELDS: dict[str, tuple[str, ...]]` = `divider`/`fixed`/`emitter` required field names.
  - `RESISTOR_FIELDS_BY_MODE: dict[str, tuple[str, ...]]` = resistor names per mode.
  - `FixedInput(vcc, rb, rc, beta, vbe=0.7)` and `EmitterInput(vcc, rb, rc, re, beta, vbe=0.7)` dataclasses.
  - `parse_input(data: dict, mode: str = "divider") -> BiasInput | FixedInput | EmitterInput`; raises `ValueError` with `"; "`-joined messages in the current style.
  - `solve_fixed(bias: FixedInput) -> BiasResult`, `solve_emitter(bias: EmitterInput) -> BiasResult`, `solve_divider(bias: BiasInput) -> BiasResult`; `solve()` delegates to `solve_divider()`.
  - Shared `_finish(result, vcc, rc, re, ib, beta, vbe, saturation_strict=False)` sets `ic`, `ie`, `ve`, `vb`, `vc`, `vce`, `region`, `warnings`.

- [x] **Step 1: Add failing tests for the new solver interface**

Append to `tests/test_dc_bias.py`:

```python
class TestNewModes(unittest.TestCase):
    def test_fixed_reference(self):
        from dc_bias import FixedInput, solve_fixed
        r = solve_fixed(FixedInput(vcc=12.0, rb=1e6, rc=2.2e3, beta=100, vbe=0.70))
        self.assertAlmostEqual(r.ib, 11.3e-6, places=9)
        self.assertAlmostEqual(r.ic_ma, 1.1300, places=4)
        self.assertAlmostEqual(r.vb, 0.70, places=4)
        self.assertAlmostEqual(r.ve, 0.0, places=4)
        self.assertAlmostEqual(r.vc, 9.5140, places=4)
        self.assertAlmostEqual(r.vce, 9.5140, places=4)

    def test_emitter_reference_and_re_increase_lowers_ic(self):
        from dc_bias import EmitterInput, solve_emitter
        a = solve_emitter(EmitterInput(12.0, 1e6, 2.2e3, 1e3, 100, 0.70))
        b = solve_emitter(EmitterInput(12.0, 1e6, 2.2e3, 2e3, 100, 0.70))
        self.assertAlmostEqual(a.ic_ma, 1.0263, places=4)
        self.assertAlmostEqual(a.vce, 8.7054, places=4)
        self.assertAlmostEqual(b.ic_ma, 0.9401, places=4)
        self.assertAlmostEqual(b.vce, 8.0328, places=4)
        self.assertLess(b.ic, a.ic)

    def test_mode_specific_validation(self):
        from dc_bias import parse_input
        fixed = {"vcc": "12", "rb": "1000000", "rc": "2200", "beta": "100", "vbe": "0.7"}
        self.assertEqual(parse_input(fixed, "fixed").rb, 1e6)  # no R1/R2/RE needed
        with self.assertRaises(ValueError) as e:
            parse_input({**fixed, "rb": "0"}, "fixed")
        self.assertIn("RB", str(e.exception))
        with self.assertRaises(ValueError) as e:
            parse_input({"vcc": "12", "rb": "1000000", "rc": "2200", "beta": "100"}, "emitter")
        self.assertIn("RE", str(e.exception))
        with self.assertRaises(ValueError) as e:
            parse_input(fixed, "unknown")
        self.assertIn("mode", str(e.exception).lower())

    def test_non_finite_rejected(self):
        from dc_bias import parse_input
        for bad in ("nan", "inf", "-inf"):
            with self.assertRaises(ValueError):
                parse_input({"vcc": "12", "rb": bad, "rc": "2200", "beta": "100"}, "fixed")

    def test_new_modes_saturation_warning(self):
        from dc_bias import FixedInput, solve_fixed
        r = solve_fixed(FixedInput(vcc=12.0, rb=1e3, rc=100e3, beta=100, vbe=0.70))
        self.assertEqual(r.region, "saturation")
        self.assertTrue(r.warnings)
```

- [x] **Step 2: Run the tests; confirm they fail**

Run: `python -m unittest discover -s tests -v`
Expected: FAIL with `ImportError`/`AttributeError` for the new names. Existing 15 cases still PASS.

- [x] **Step 3: Implement the module changes in `dc_bias.py`**

Add `MODE_FIELDS`, `RESISTOR_FIELDS_BY_MODE`, `FixedInput`, `EmitterInput`. Make `_validate(data, mode)` use `MODE_FIELDS[mode]`, keep the exact existing message templates (`กรุณากรอกค่า X`, `X ต้องเป็นตัวเลข`, `X ต้องมากกว่า 0 Ω`), and reject non-finite numbers with `math.isfinite`. Raise on unknown mode before field validation. In `parse_input(data, mode="divider")`, construct the input dataclass matching the mode. Implement `_finish()` once and use it from all three solvers; for the new modes treat `ib <= 0` as `region="cutoff"` with a warning and zero currents; use `vce <= 0.2` for the new modes' saturation warning and keep divider's existing `< 0.2` behavior. `solve()` calls `solve_divider()`.

- [x] **Step 4: Run all tests; confirm they pass**

Run: `python -m unittest discover -s tests -v`
Expected: PASS (all existing tests plus the 5 new ones). Confirm divider's `test_reference_operating_point` still passes unchanged.

- [x] **Step 5: Commit**

```bash
git add dc_bias.py tests/test_dc_bias.py
git commit -m "feat(dc_bias): add fixed and emitter bias solvers with mode validation"
```

---

### Task 2: Route dispatch and mode-specific request validation

**Files:**
- Modify: `app.py`
- Test: `tests/test_web.py` (add cases; keep every existing case)

**Interfaces:**
- Consumes: `parse_input(data, mode)`, `solve_fixed`, `solve_emitter`, `solve_divider`, `MODE_FIELDS`, `RESISTOR_FIELDS_BY_MODE`, `BiasResult` from Task 1.
- Produces: `calculate()` in `app.py` reads `mode` (default `"divider"`), accepts `action="mode"` to re-render the form without solving, and always passes `mode` into `render_template`; on errors `result` is `None`.

- [x] **Step 1: Add failing route tests**

Append to `tests/test_web.py`:

```python
class TestModeRoutes(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config["TESTING"] = True

    def test_fixed_post(self):
        rv = self.client.post("/calculate", data={
            "mode": "fixed", "vcc": "12", "rb": "1", "rb_unit": "mohm",
            "rc": "2.2", "rc_unit": "kohm", "beta": "100", "vbe": "0.70"})
        html = rv.get_data(as_text=True)
        self.assertIn("1.13 mA", html)
        self.assertIn("9.51 V", html)

    def test_emitter_post_with_re(self):
        rv = self.client.post("/calculate", data={
            "mode": "emitter", "vcc": "12", "rb": "1", "rb_unit": "mohm",
            "rc": "2.2", "rc_unit": "kohm", "re": "1", "re_unit": "kohm",
            "beta": "100", "vbe": "0.70"})
        html = rv.get_data(as_text=True)
        self.assertIn("1.03 mA", html)
        self.assertIn("8.71 V", html)

    def test_invalid_rb_zero_shows_error_not_stale_result(self):
        rv = self.client.post("/calculate", data={
            "mode": "fixed", "vcc": "12", "rb": "0", "rb_unit": "mohm",
            "rc": "2.2", "rc_unit": "kohm", "beta": "100", "vbe": "0.70"})
        html = rv.get_data(as_text=True)
        self.assertIn("RB", html)
        self.assertIn("ข้อผิดพลาด", html)
        self.assertNotIn("1.13 mA", html)  # no stale numbers from a previous valid run

    def test_unknown_mode_rejected(self):
        rv = self.client.post("/calculate", data={**reference_form(), "mode": "bogus"})
        html = rv.get_data(as_text=True)
        self.assertIn("โหมด", html)
        self.assertNotIn("8.05 V", html)

    def test_mode_switch_has_no_result(self):
        rv = self.client.post("/calculate", data={
            "mode": "fixed", "action": "mode", "vcc": "12", "rb": "1",
            "rb_unit": "mohm", "rc": "2.2", "rc_unit": "kohm",
            "beta": "100", "vbe": "0.70"})
        html = rv.get_data(as_text=True)
        self.assertNotIn("1.13 mA", html)
        self.assertIn('name="vcc"', html)
```

- [x] **Step 2: Run the tests; confirm they fail**

Run: `python -m unittest discover -s tests -v`
Expected: FAIL for the new assertions; original web tests still PASS.

- [x] **Step 3: Implement dispatch in `app.py`**

Read all possible form fields into `data`. Validate the mode against `MODE_FIELDS` keys first. If `action == "mode"`, return `render_template("index.html", form=data, result=None, errors=None, mode=mode)`. Otherwise convert only `RESISTOR_FIELDS_BY_MODE[mode]` using `UNIT_FACTORS`, call `parse_input(si, mode)`, dispatch through an `if/elif` (or explicit dict) to the matching solver, catch `ValueError` into `errors` with `result = None`, and pass `mode` to the template. Keep the existing `/` defaults and add default `mode="divider"`, `rb="1.0"`, `rb_unit="mohm"` for the new form.

- [x] **Step 4: Run all tests; confirm they pass**

Run: `python -m unittest discover -s tests -v`
Expected: PASS. Existing `test_a2_post_calculates_via_backend` still sees `1.23 mA` and `8.05 V` (default mode remains divider).

- [x] **Step 5: Commit**

```bash
git add app.py tests/test_web.py
git commit -m "feat(web): dispatch /calculate by selected bias mode"
```

---

### Task 3: Mode-aware form and result presentation

**Files:**
- Modify: `templates/index.html`, `static/style.css` (only if a new hint/warning style is needed)

**Interfaces:**
- Consumes: `form`, `result`, `errors`, `mode` from Task 2; `BiasResult` fields from Task 1.
- Produces: rendered page where the mode selector survives posts, only relevant resistor fields are shown, and result/error headings name the active mode.

- [x] **Step 1: Add failing template assertions to `tests/test_web.py`**

```python
class TestModeTemplate(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_form_shows_only_mode_fields(self):
        fixed = self.client.post("/calculate", data={
            "mode": "fixed", "action": "mode", "vcc": "12", "rb": "1",
            "rc": "2.2", "beta": "100"}).get_data(as_text=True)
        self.assertIn('name="rb"', fixed)
        self.assertNotIn('name="r1"', fixed)
        emitter = self.client.post("/calculate", data={
            "mode": "emitter", "action": "mode", "vcc": "12", "rb": "1",
            "rc": "2.2", "re": "1", "beta": "100"}).get_data(as_text=True)
        self.assertIn('name="re"', emitter)
        self.assertNotIn('name="r1"', emitter)

    def test_result_and_error_name_the_mode(self):
        html = self.client.post("/calculate", data={
            "mode": "fixed", "vcc": "12", "rb": "1", "rb_unit": "mohm",
            "rc": "2.2", "rc_unit": "kohm", "beta": "100"}).get_data(as_text=True)
        self.assertIn("Fixed Bias", html)
```

- [x] **Step 2: Run the tests; confirm they fail**

Run: `python -m unittest discover -s tests -v`
Expected: FAIL on the conditional-field and mode-label assertions.

- [x] **Step 3: Update `templates/index.html`**

Add a `<select name="mode" id="mode">` with `divider`, `fixed`, `emitter` options marked `selected` from `mode`, and a submit button named `action` with value `mode` labelled "เปลี่ยนโหมด". Wrap R1/R2 in `{% if mode == 'divider' %}`, RB in `{% if mode in ('fixed','emitter') %}`, RE in `{% if mode in ('emitter','divider') %}`. Keep `name`/`id` of all existing inputs unchanged. Keep the existing result table and `BiasResult` properties; add the mode name to the results heading and the error-panel heading. When `result` is `None`, omit the `DC Bias Results` heading (the existing empty-state text may remain).

- [x] **Step 4: Run all tests; confirm they pass**

Run: `python -m unittest discover -s tests -v`
Expected: PASS, including the old Lab 2 assertions (`Input Parameters`, `DC Bias Results` on a successful divider POST, `Calculate DC Bias`).

- [x] **Step 5: Commit**

```bash
git add templates/index.html static/style.css
git commit -m "feat(ui): mode selector and mode-specific bias form fields"
```

---

### Task 4: Verify A1–A5 in a real browser and document the evidence

**Files:**
- Create: `docs/validation.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: the running app at `http://127.0.0.1:5000/` and the independent expected values below (computed by hand from the lab equations, not read from `dc_bias.py`).

Independent reference set (VCC=12 V, RC=2.2 kΩ, β=100, VBE=0.70 V):

| Case | Mode / input | IC expected | VCE expected |
|---|---|---|---|
| A1 | Divider R1=100 kΩ, R2=22 kΩ, RE=1 kΩ | 1.2299 mA | 8.0522 V |
| A2 | Fixed RB=1 MΩ | 1.1300 mA | 9.5140 V |
| A3 | Emitter RB=1 MΩ, RE=1 kΩ | 1.0263 mA | 8.7054 V |
| A4 | Emitter RB=1 MΩ, RE=2 kΩ | 0.9401 mA | 8.0328 V (IC must drop vs A3) |
| A5 | Fixed RB=0 | error naming RB; no result | — |

Tolerance: |ΔIC| ≤ 0.01 mA, |ΔVCE| ≤ 0.02 V versus the unrounded reference.

- [x] **Step 1: Confirm the server reflects the new code**

Run: `python -m unittest discover -s tests -v`, then open `http://127.0.0.1:5000/` in a browser. If the page still has no mode selector, restart the Flask process and reload.

- [x] **Step 2: Run A1–A5 through the browser**

For each case: select the mode, press "เปลี่ยนโหมด" if fields must refresh, fill only the relevant fields with the units shown, press "Calculate DC Bias", and read the rendered result/message. Record the observed IC, VCE (or error text), and the tool actually used (OpenCode Browser / Playwright MCP / Manual). Never use source code or curl as a substitute for a browser observation.

- [x] **Step 3: Write `docs/validation.md`**

Copy the A1–A5 table with columns: case, input, expected (with units), observed (with units), method, status (`PASS`/`FAIL`/`NOT RUN`), evidence (quoted page text or screenshot path). Include at least one quoted result from the page and the A3→A4 IC direction explanation.

- [x] **Step 4: Update `README.md`**

Document the three modes, the equations for Fixed/Emitter, how to run (`python -m flask --app app run`), the validation table location, and which code the AI wrote versus what was checked.

- [x] **Step 5: Commit and report**

```bash
git add docs/validation.md README.md
git commit -m "docs: record Lab 3 mode verification and run instructions"
```

Report the A1–A5 table, the commit SHAs, and any case that was `NOT RUN` with its blocker.
