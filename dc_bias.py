"""BJT Common-Emitter Voltage-Divider Bias DC analysis module.

Pure engineering calculations only - no Flask, no HTML, no HTTP.
Forward-Active approximation: constant beta and constant VBE.

Inputs are SI units: volts, ohms, amperes.
"""

import math
from dataclasses import dataclass, field


@dataclass
class BiasInput:
    """Circuit parameters for the NPN common-emitter voltage-divider bias."""

    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float = 0.7


@dataclass
class FixedInput:
    """Circuit parameters for fixed bias: RB from VCC to base, emitter grounded."""

    vcc: float
    rb: float
    rc: float
    beta: float
    vbe: float = 0.7


@dataclass
class EmitterInput:
    """Circuit parameters for single-supply emitter bias: RB, RC and RE."""

    vcc: float
    rb: float
    rc: float
    re: float
    beta: float
    vbe: float = 0.7


@dataclass
class BiasResult:
    """DC operating point and validity warnings."""

    vb: float = 0.0
    ve: float = 0.0
    vc: float = 0.0
    vce: float = 0.0
    vth: float = 0.0
    rth: float = 0.0
    ib: float = 0.0  # amperes
    ic: float = 0.0  # amperes
    ie: float = 0.0  # amperes
    region: str = "forward-active"
    warnings: list = field(default_factory=list)

    @property
    def ic_ma(self) -> float:
        return self.ic * 1000.0

    @property
    def ib_ua(self) -> float:
        return self.ib * 1e6

    @property
    def ie_ma(self) -> float:
        return self.ie * 1000.0


MODE_FIELDS = {
    "divider": ("vcc", "r1", "r2", "rc", "re", "beta"),
    "fixed": ("vcc", "rb", "rc", "beta"),
    "emitter": ("vcc", "rb", "rc", "re", "beta"),
}

RESISTOR_FIELDS_BY_MODE = {
    "divider": ("r1", "r2", "rc", "re"),
    "fixed": ("rb", "rc"),
    "emitter": ("rb", "rc", "re"),
}

_LABELS = {"vcc": "VCC", "r1": "R1", "r2": "R2", "rb": "RB", "rc": "RC",
           "re": "RE", "beta": "beta"}


def _validate(data: dict, mode: str = "divider") -> list:
    """Validate the fields required by ``mode``. Returns error messages."""
    errors = []
    required = MODE_FIELDS[mode]
    resistors = RESISTOR_FIELDS_BY_MODE[mode]
    for key in required:
        label = _LABELS[key]
        if key not in data or str(data[key]).strip() == "":
            errors.append(f"กรุณากรอกค่า {label} (missing {label})")
            continue
        try:
            value = float(data[key])
        except (TypeError, ValueError):
            errors.append(f"{label} ต้องเป็นตัวเลข ({label} must be numeric)")
            continue
        if not math.isfinite(value):
            errors.append(f"{label} ต้องเป็นจำนวนจำกัด ({label} must be finite)")
            continue
        if key in resistors and value <= 0:
            errors.append(f"{label} ต้องมากกว่า 0 Ω ({label} must be > 0 Ω)")
        if key == "vcc" and value <= 0:
            errors.append(f"VCC ต้องมากกว่า 0 V (VCC must be > 0 V)")
        if key == "beta" and value <= 0:
            errors.append(f"β ต้องมากกว่า 0 (beta must be > 0)")
    # VBE optional but if given must be numeric and finite (can be 0)
    if "vbe" in data and str(data.get("vbe", "")).strip() != "":
        try:
            vbe = float(data["vbe"])
            if not math.isfinite(vbe):
                raise ValueError("not finite")
        except (TypeError, ValueError):
            errors.append("VBE ต้องเป็นตัวเลข (VBE must be numeric)")
    return errors


def parse_input(data: dict, mode: str = "divider"):
    """Parse and validate raw form data into the input dataclass for ``mode``.

    Raises ValueError with all validation messages joined by "; ".
    """
    if mode not in MODE_FIELDS:
        raise ValueError(f"โหมดไม่รู้จัก (unknown mode: {mode}) — ใช้ divider, fixed หรือ emitter")
    errors = _validate(data, mode)
    if errors:
        raise ValueError("; ".join(errors))
    values = {key: float(data[key]) for key in MODE_FIELDS[mode]}
    values["vbe"] = float(data.get("vbe") or 0.7)
    if mode == "fixed":
        return FixedInput(**values)
    if mode == "emitter":
        return EmitterInput(**values)
    return BiasInput(**values)


def solve_divider(bias: BiasInput) -> BiasResult:
    """Solve the voltage-divider DC operating point (forward-active).

    VTH = VCC * R2 / (R1 + R2)
    RTH = R1*R2 / (R1 + R2)
    IB  = (VTH - VBE) / (RTH + (beta+1)*RE)
    IC  = beta*IB ; IE = (beta+1)*IB
    VE  = IE*RE ; VB = VE + VBE ; VC = VCC - IC*RC ; VCE = VC - VE
    """
    result = BiasResult()
    result.vth = bias.vcc * bias.r2 / (bias.r1 + bias.r2)
    result.rth = bias.r1 * bias.r2 / (bias.r1 + bias.r2)

    # Cutoff check: divider voltage cannot turn the base junction on.
    if result.vth <= bias.vbe:
        result.region = "cutoff"
        result.warnings.append(
            f"VTH = {result.vth:.3f} V ≤ VBE = {bias.vbe:.3f} V "
            "→ ทรานซิสเตอร์อยู่ใน Cutoff (ไม่นำกระแส) ค่าที่คำนวณ "
            "จากสมการ Forward-Active ใช้ไม่ได้ (IB จะเป็นลบ)"
        )
        return result

    result.ib = (result.vth - bias.vbe) / (result.rth + (bias.beta + 1) * bias.re)
    result.ic = bias.beta * result.ib
    result.ie = (bias.beta + 1) * result.ib
    result.ve = result.ie * bias.re
    result.vb = result.ve + bias.vbe
    result.vc = bias.vcc - result.ic * bias.rc
    result.vce = result.vc - result.ve

    # Saturation check: forward-active needs VCE comfortably above VCE(sat).
    if result.vce < 0.2:
        result.region = "saturation"
        result.warnings.append(
            f"VCE = {result.vce:.3f} V ต่ำกว่า 0.2 V (ใกล้ VCE(sat)) "
            "→ ทรานซิสเตอร์เข้าสู่ Saturation ผลจากสมการ Forward-Active "
            "ไม่สะท้อนสภาวะจริง (IC จริงจะถูกจำกัดโดย RC)"
        )
    return result


def _finish(result: BiasResult, vcc: float, rc: float, re: float,
            ib: float, beta: float, vbe: float,
            saturation_strict: bool = False) -> BiasResult:
    """Complete the operating point from IB and apply model-limit warnings."""
    if ib <= 0:
        result.region = "cutoff"
        result.vc = vcc
        result.vce = vcc
        result.warnings.append(
            f"IB = {ib * 1e6:.3f} µA ≤ 0 → ทรานซิสเตอร์อยู่ใน Cutoff "
            "ค่าจากสมการ Forward-Active ใช้ไม่ได้"
        )
        return result

    result.ib = ib
    result.ic = beta * ib
    result.ie = (beta + 1) * ib
    result.ve = result.ie * re
    result.vb = result.ve + vbe
    result.vc = vcc - result.ic * rc
    result.vce = result.vc - result.ve

    too_low = result.vce <= 0.2 if saturation_strict else result.vce < 0.2
    if too_low:
        result.region = "saturation"
        result.warnings.append(
            f"VCE = {result.vce:.3f} V ต่ำกว่า 0.2 V (ใกล้ VCE(sat)) "
            "→ ทรานซิสเตอร์เข้าสู่ Saturation ผลจากสมการ Forward-Active "
            "ไม่สะท้อนสภาวะจริง (IC จริงจะถูกจำกัดโดย RC)"
        )
    return result


def solve_fixed(bias: FixedInput) -> BiasResult:
    """Fixed bias: IB = (VCC − VBE) / RB, emitter at ground."""
    ib = (bias.vcc - bias.vbe) / bias.rb
    return _finish(BiasResult(), bias.vcc, bias.rc, 0.0, ib,
                   bias.beta, bias.vbe, saturation_strict=True)


def solve_emitter(bias: EmitterInput) -> BiasResult:
    """Emitter bias: IB = (VCC − VBE) / [RB + (β+1)RE]."""
    ib = (bias.vcc - bias.vbe) / (bias.rb + (bias.beta + 1) * bias.re)
    return _finish(BiasResult(), bias.vcc, bias.rc, bias.re, ib,
                   bias.beta, bias.vbe, saturation_strict=True)


def solve(bias: BiasInput) -> BiasResult:
    """Backwards-compatible entry point for the Lab 2 divider circuit."""
    return solve_divider(bias)
