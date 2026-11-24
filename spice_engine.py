"""Validation, netlist construction and ngspice support for the CE simulator.

This module owns no Flask code. All circuit values held by :class:`SimInput`
are SI (Ω, F, V, Hz) after :func:`parse_sim_form` converts the web form's
kΩ / µF / mV / kHz units.
"""

from __future__ import annotations

import math
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class SpiceError(Exception):
    """Raised when ngspice cannot be located or a simulation fails."""


@dataclass(frozen=True)
class SimInput:
    """Validated, SI-unit simulation inputs for one ngspice run."""

    analysis: str
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    rl: float
    cin: float
    cout: float
    amp: float
    freq: float


# (form key, error label, SI numerator, SI denominator). The ratios keep the
# documented factors (1e3, 1e-6, 1e-3) without binary rounding surprises such
# as 10 * 1e-6 != 10e-6.
_NUMERIC_FIELDS = (
    ("vcc", "VCC", 1, 1),          # V -> V
    ("r1", "R1", 1_000, 1),        # kΩ -> Ω
    ("r2", "R2", 1_000, 1),
    ("rc", "RC", 1_000, 1),
    ("re", "RE", 1_000, 1),
    ("rl", "RL", 1_000, 1),
    ("cin", "Cin", 1, 1_000_000),  # µF -> F
    ("cout", "Cout", 1, 1_000_000),
    ("amp", "amp", 1, 1_000),      # mV peak -> V peak
    ("freq", "freq", 1_000, 1),    # kHz -> Hz
)

_ANALYSES = ("dc", "ac", "tran")


def _positive(label: str, raw: object, numerator: float, denominator: float) -> float:
    """Convert one form value to SI; raise a labelled ValueError if unusable."""
    text = "" if raw is None else str(raw).strip()
    if not text:
        raise ValueError(f"{label} ต้องกรอกค่า (missing {label})")
    try:
        value = float(text)
    except ValueError:
        raise ValueError(f"{label} ต้องเป็นตัวเลข ({label} must be numeric)") from None
    if not math.isfinite(value):
        raise ValueError(f"{label} ต้องเป็นจำนวนจำกัด ({label} must be finite)")
    if value <= 0:
        raise ValueError(f"{label} ต้องมากกว่า 0 ({label} must be > 0)")
    si_value = value * numerator / denominator
    if not math.isfinite(si_value) or si_value <= 0:
        raise ValueError(f"{label} ต้องเป็นจำนวนจำกัด ({label} must be finite in SI)")
    return si_value


def parse_sim_form(form: Mapping[str, str]) -> SimInput:
    """Validate the simulation form and convert every value to SI units.

    All faults are reported together as one ``ValueError`` whose messages are
    joined by ``"; "`` so the web layer can show a complete error list.
    """
    errors: list[str] = []
    raw_analysis = form.get("analysis")
    analysis = "" if raw_analysis is None else str(raw_analysis).strip().lower()
    if analysis not in _ANALYSES:
        errors.append(
            f"analysis ไม่รู้จัก (unknown analysis: {raw_analysis!r}) "
            "— ใช้ dc, ac หรือ tran"
        )

    values: dict[str, float] = {}
    for key, label, numerator, denominator in _NUMERIC_FIELDS:
        try:
            values[key] = _positive(label, form.get(key), numerator, denominator)
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        raise ValueError("; ".join(errors))
    return SimInput(analysis=analysis, **values)


def find_ngspice() -> str:
    """Locate ngspice: ``NGSPICE_EXE`` → PATH → common Windows install paths."""
    configured = os.environ.get("NGSPICE_EXE", "").strip()
    if configured:
        if not os.path.isfile(configured):
            raise SpiceError(f"NGSPICE_EXE points to a missing file: {configured}")
        return configured

    on_path = shutil.which("ngspice")
    if on_path:
        return on_path

    common_roots = []
    localappdata = os.environ.get("LOCALAPPDATA", "").strip()
    if localappdata:
        common_roots.append(Path(localappdata))
    for root in common_roots:
        for relative in (
            Path("ngspice-47") / "clang64" / "bin" / "ngspice.exe",
            Path("ngspice-47") / "Spice64" / "bin" / "ngspice.exe",
        ):
            candidate = root / relative
            if candidate.is_file():
                return str(candidate)

    raise SpiceError(
        "ngspice not found. Install ngspice 47 or set NGSPICE_EXE "
        "to the full path of ngspice.exe."
    )


def _fmt(value: float) -> str:
    """Stable SI-safe numeric rendering for netlist entries."""
    return f"{value:.6g}"


def build_netlist(sim: SimInput, model_path: str) -> str:
    """Render one ngspice netlist for exactly the selected analysis."""
    if sim.analysis == "dc":
        directives = (".op", ".print op v(b) v(e) v(c) i(rc) i(vcc)")
    elif sim.analysis == "ac":
        directives = (
            ".ac dec 20 1 10Meg",
            ".print ac vdb(in) vdb(out) vp(in) vp(out)",
        )
    elif sim.analysis == "tran":
        stop = max(5.0 / sim.freq, 1e-3)
        step = stop / 2000.0
        directives = (f".tran {_fmt(step)} {_fmt(stop)}", ".print tran v(in) v(out)")
    else:
        raise ValueError(f"analysis ไม่รู้จัก (unknown analysis: {sim.analysis!r})")

    amp = _fmt(sim.amp)
    lines = (
        "* CE amplifier - local documented Q1_NPN model",
        f"VCC vcc 0 DC {_fmt(sim.vcc)}",
        f"VIN in 0 DC 0 AC {amp} SIN(0 {amp} {_fmt(sim.freq)})",
        f"R1 vcc b {_fmt(sim.r1)}",
        f"R2 b 0 {_fmt(sim.r2)}",
        f"RC vcc c {_fmt(sim.rc)}",
        f"RE e 0 {_fmt(sim.re)}",
        f"RL out 0 {_fmt(sim.rl)}",
        "Q1 c b e Q1_NPN",
        f"Cin in b {_fmt(sim.cin)}",
        f"Cout c out {_fmt(sim.cout)}",
        f".include {Path(model_path).as_posix()}",
        *directives,
        ".end",
        "",
    )
    return "\n".join(lines)
