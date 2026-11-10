"""BJT Common-Emitter Voltage-Divider Bias DC analysis module.

Pure engineering calculations only - no Flask, no HTML, no HTTP.
Forward-Active approximation: constant beta and constant VBE.

Inputs are SI units: volts, ohms, amperes.
"""

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


def _validate(data: dict) -> list:
    """Validate raw form data. Returns a list of Thai/English error messages."""
    errors = []
    required = {"vcc": "VCC", "r1": "R1", "r2": "R2", "rc": "RC",
                "re": "RE", "beta": "beta"}
    for key, label in required.items():
        if key not in data or str(data[key]).strip() == "":
            errors.append(f"กรุณากรอกค่า {label} (missing {label})")
            continue
        try:
            value = float(data[key])
        except (TypeError, ValueError):
            errors.append(f"{label} ต้องเป็นตัวเลข ({label} must be numeric)")
            continue
        if key in ("r1", "r2", "rc", "re") and value <= 0:
            errors.append(f"{label} ต้องมากกว่า 0 Ω ({label} must be > 0 Ω)")
        if key == "vcc" and value <= 0:
            errors.append(f"VCC ต้องมากกว่า 0 V (VCC must be > 0 V)")
        if key == "beta" and value <= 0:
            errors.append(f"β ต้องมากกว่า 0 (beta must be > 0)")
    # VBE optional but if given must be numeric (can be 0 for cutoff check)
    if "vbe" in data and str(data.get("vbe", "")).strip() != "":
        try:
            float(data["vbe"])
        except (TypeError, ValueError):
            errors.append("VBE ต้องเป็นตัวเลข (VBE must be numeric)")
    return errors


def parse_input(data: dict) -> BiasInput:
    """Parse and validate raw form data into a BiasInput.

    Raises ValueError with the first error message if data is invalid.
    """
    errors = _validate(data)
    if errors:
        raise ValueError("; ".join(errors))
    return BiasInput(
        vcc=float(data["vcc"]),
        r1=float(data["r1"]),
        r2=float(data["r2"]),
        rc=float(data["rc"]),
        re=float(data["re"]),
        beta=float(data["beta"]),
        vbe=float(data.get("vbe") or 0.7),
    )


def solve(bias: BiasInput) -> BiasResult:
    """Solve the DC operating point under the forward-active approximation.

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
