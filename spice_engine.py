"""Validation, netlist construction and ngspice support for the CE simulator.

This module owns no Flask code. All circuit values held by :class:`SimInput`
are SI (Ω, F, V, Hz) after :func:`parse_sim_form` converts the web form's
kΩ / µF / mV / kHz units.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import struct
import subprocess
import tempfile
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


ENGINE_VERSION = "47-1 (MSYS2 package, upstream ngspice 47)"
MODEL_LABEL = "Q1_NPN (local documented 2N3904-style model)"

_MAX_EXCERPT = 4000
_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_NAMED_RE = re.compile(rf"([A-Za-z][A-Za-z0-9_()]*)\s*=\s*({_NUMBER})")
_NUM_RE = re.compile(_NUMBER)


def _text(value: object) -> str:
    """Decode process output that may arrive as bytes or text."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _excerpt(text: str) -> str:
    """Keep error/result snippets short enough to be readable in the UI."""
    return text.strip()[:_MAX_EXCERPT]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def _parse_named_values(text: str) -> dict[str, float]:
    """Collect ``name = value`` assignments from an ngspice op log."""
    return {
        match.group(1).lower(): float(match.group(2))
        for match in _NAMED_RE.finditer(text)
    }


def _parse_numeric_rows(text: str, width: int) -> list[list[float]]:
    """Collect tabular rows with at least ``width`` leading numeric columns."""
    rows: list[list[float]] = []
    for line in text.splitlines():
        tokens = _NUM_RE.findall(line)
        if len(tokens) < width:
            continue
        row = [float(token) for token in tokens[:width]]
        if all(math.isfinite(value) for value in row):
            rows.append(row)
    return rows


def _dc_data(sim: SimInput, values: Mapping[str, float], warnings: list[str]) -> dict:
    """Derive node voltages and collector current from named op values."""
    try:
        vb, ve, vc = (values[key] for key in ("v(b)", "v(e)", "v(c)"))
    except KeyError as exc:
        raise ValueError(f"missing DC node voltage {exc.args[0]}") from None
    if not all(math.isfinite(value) for value in (vb, ve, vc)):
        raise ValueError("non-finite DC node voltage")

    if "i(rc)" in values and math.isfinite(values["i(rc)"]):
        ic_ma = abs(values["i(rc)"]) * 1000.0
    elif "i(vcc)" in values and math.isfinite(values["i(vcc)"]):
        ic_ma = abs(-values["i(vcc)"]) * 1000.0
        warnings.append("i(rc) missing; used -i(vcc) for ic_ma")
    else:
        ic_ma = (sim.vcc - vc) / sim.rc * 1000.0
        warnings.append("i(rc) and i(vcc) missing; used RC voltage drop for ic_ma")
    if not math.isfinite(ic_ma):
        raise ValueError("non-finite collector current")

    return {"vb": vb, "ve": ve, "vc": vc, "vce": vc - ve, "ic_ma": ic_ma}


def _ac_points(rows: list[list[float]]) -> list[dict]:
    """Convert index/freq/vdb/vp table rows into gain and phase differences."""
    if not rows:
        raise ValueError("no AC rows")
    return [
        {
            "freq_hz": row[1],
            "gain_db": row[3] - row[2],
            "phase_deg": row[5] - row[4],
        }
        for row in rows
    ]


def _ac_summary(points: list[dict], warnings: list[str]) -> dict:
    """Find midband gain and the nearest -3 dB sample on each side."""
    mid_index = max(range(len(points)), key=lambda i: points[i]["gain_db"])
    midband = points[mid_index]["gain_db"]
    cutoff = midband - 3.0

    low = next(
        (
            points[i]["freq_hz"]
            for i in range(mid_index - 1, -1, -1)
            if points[i]["gain_db"] <= cutoff
        ),
        None,
    )
    high = next(
        (
            points[i]["freq_hz"]
            for i in range(mid_index + 1, len(points))
            if points[i]["gain_db"] <= cutoff
        ),
        None,
    )
    if low is None:
        warnings.append("f_low_hz not determined in sweep range")
    if high is None:
        warnings.append("f_high_hz not determined in sweep range")
    return {"midband_gain_db": midband, "f_low_hz": low, "f_high_hz": high}


def _tran_points(rows: list[list[float]]) -> list[dict]:
    """Convert index/time/v(in)/v(out) table rows into point dictionaries."""
    if not rows:
        raise ValueError("no transient rows")
    return [
        {"time_s": row[1], "vin_v": row[2], "vout_v": row[3]}
        for row in rows
    ]


def _tran_summary(points: list[dict]) -> dict:
    """Classify input/output phase from mean-centred correlation."""
    xs = [point["vin_v"] for point in points]
    ys = [point["vout_v"] for point in points]
    mx = math.fsum(xs) / len(xs)
    my = math.fsum(ys) / len(ys)
    dx = [value - mx for value in xs]
    dy = [value - my for value in ys]
    denom = math.sqrt(math.fsum(x * x for x in dx) * math.fsum(y * y for y in dy))
    corr = math.fsum(x * y for x, y in zip(dx, dy)) / denom if denom else 0.0
    if corr < -0.2:
        relation = "inverted"
    elif corr > 0.2:
        relation = "in-phase"
    else:
        relation = "unclear"
    return {"phase_relation": relation}


def _parse_log(sim: SimInput, text: str, warnings: list[str]) -> tuple[dict, dict]:
    """Parse the primary (-o log / stdout) representation of one analysis."""
    if sim.analysis == "dc":
        return _dc_data(sim, _parse_named_values(text), warnings), {}
    if sim.analysis == "ac":
        points = _ac_points(_parse_numeric_rows(text, 6))
        return points, _ac_summary(points, warnings)
    points = _tran_points(_parse_numeric_rows(text, 4))
    return points, _tran_summary(points)


def _raw_int(header: str, label: str) -> int:
    match = re.search(rf"{re.escape(label)}\s*:\s*(\d+)", header)
    if match is None:
        raise ValueError(f"raw file lacks {label}")
    return int(match.group(1))


def _raw_columns(blob: bytes) -> dict[str, list[float]]:
    """Read variable columns from an ASCII or binary ngspice raw file."""
    if not blob:
        raise ValueError("empty raw file")
    # The first 4/8 bytes identify a header-bearing raw file; a bare binary
    # blob carries no variable names and cannot be mapped to circuit nodes.
    if not blob[:8].decode("ascii", errors="replace").lstrip().startswith(
        ("Title:", "Plotna", "No. Var", "Flags:")
    ):
        raise ValueError("raw file has no recognisable header")
    header = blob[:4096].decode("utf-8", errors="replace")
    nvar = _raw_int(header, "No. Variables")
    npoints = _raw_int(header, "No. Points")
    if nvar < 1 or npoints < 1:
        raise ValueError("raw file has no variables or points")

    if "Variables:" not in header:
        raise ValueError("raw file lacks Variables section")
    var_block = header.split("Variables:", 1)[1]
    var_block = var_block.split("Values:", 1)[0].split("Binary:", 1)[0]
    names: list[str] = []
    for line in var_block.splitlines():
        fields = line.strip().split()
        if len(fields) >= 2 and fields[0].isdigit():
            names.append(fields[1].lower())
    if len(names) != nvar:
        raise ValueError("raw variable list does not match No. Variables")

    if "Binary:" in header:
        payload = blob.split(b"Binary:", 1)[1].lstrip(b"\r\n")
        if payload[:1] == b"\x00":  # ngspice pad byte before the doubles
            payload = payload[1:]
        count = nvar * npoints
        if len(payload) < count * 8:
            raise ValueError("truncated binary raw data")
        values = list(struct.unpack(f"<{count}d", payload[:count * 8]))
    else:
        if "Values:" not in header:
            raise ValueError("raw file has neither Values nor Binary section")
        values_text = blob.decode("utf-8", errors="replace").split("Values:", 1)[1]
        rows: list[list[float]] = []
        for line in values_text.splitlines():
            fields = [field.strip() for field in line.replace(",", " ").split() if field.strip()]
            if not fields or not fields[0].isdigit():
                continue
            row = [float(field) for field in fields[1:1 + nvar]]
            if len(row) != nvar:
                raise ValueError("malformed ASCII raw row")
            rows.append(row)
        if len(rows) < npoints:
            raise ValueError("ASCII raw data has too few points")
        values = [value for row in rows[:npoints] for value in row]

    if not all(math.isfinite(value) for value in values):
        raise ValueError("non-finite raw value")
    return {
        name: [values[index * npoints + point] for point in range(npoints)]
        for index, name in enumerate(names)
    }


def _parse_raw(sim: SimInput, columns: Mapping[str, list[float]],
               warnings: list[str]) -> tuple[dict, dict]:
    """Map raw-file variable columns onto the analysis result shape."""
    if sim.analysis == "dc":
        values = {name: seq[0] for name, seq in columns.items()}
        return _dc_data(sim, values, warnings), {}

    if sim.analysis == "ac":
        names = ("vdb(in)", "vdb(out)", "vp(in)", "vp(out)")
        if any(name not in columns for name in names):
            raise ValueError("raw AC file lacks vdb/vp variables")
        npoints = len(columns[names[0]])
        freqs = columns.get("freq", [float(index) for index in range(npoints)])
        points = [
            {
                "freq_hz": freqs[index],
                "gain_db": columns["vdb(out)"][index] - columns["vdb(in)"][index],
                "phase_deg": columns["vp(out)"][index] - columns["vp(in)"][index],
            }
            for index in range(npoints)
        ]
        return points, _ac_summary(points, warnings)

    names = ("time", "v(in)", "v(out)")
    if any(name not in columns for name in names):
        raise ValueError("raw transient file lacks time/v(in)/v(out) variables")
    points = [
        {
            "time_s": columns["time"][index],
            "vin_v": columns["v(in)"][index],
            "vout_v": columns["v(out)"][index],
        }
        for index in range(len(columns["time"]))
    ]
    return points, _tran_summary(points)


def _is_command_name(exe: str) -> bool:
    """A bare command name is resolved by the OS; a path must exist."""
    separators = {os.path.sep, os.path.altsep or os.path.sep, "/", "\\"}
    return not any(sep in exe for sep in separators)


def run_analysis(sim: SimInput, exe: str | None = None,
                 timeout: float = 60.0) -> dict:
    """Run one ngspice analysis and return its parsed, labelled result.

    Every failure raises :class:`SpiceError`; a success dict never carries
    ``data=None``. The simulator runs in a fresh temporary directory with a
    child ``PATH`` that can find ngspice's DLLs.
    """
    if exe is None:
        exe = find_ngspice()
    elif _is_command_name(exe) is False and not Path(exe).is_file():
        raise SpiceError(f"ngspice executable not found: {exe}")

    model_path = Path(__file__).resolve().parent / "spice" / "q1_npn.model"
    if not model_path.is_file():
        raise SpiceError(f"SPICE model file missing: {model_path}")

    with tempfile.TemporaryDirectory() as workdir:
        netlist = Path(workdir) / "ce.cir"
        log_path = Path(workdir) / "ngspice.log"
        raw_path = Path(workdir) / "ngspice.raw"
        netlist.write_text(build_netlist(sim, str(model_path)), encoding="utf-8")

        child_env = os.environ.copy()
        exe_dir = os.path.dirname(os.path.abspath(exe))
        child_env["PATH"] = exe_dir + os.pathsep + child_env.get("PATH", "")
        command = [exe, "-b", "-o", str(log_path), "-r", str(raw_path), str(netlist)]

        try:
            process = subprocess.run(
                command, shell=False, cwd=workdir, capture_output=True,
                text=True, timeout=timeout, env=child_env,
            )
        except subprocess.TimeoutExpired as exc:
            partial = _text(exc.output)
            raise SpiceError(
                f"ngspice timed out after {timeout}s\n{_excerpt(partial)}"
            ) from None

        log_text = _text(process.stdout) + "\n" + _read_text(log_path)
        stderr_text = _text(process.stderr)
        error_excerpt = _excerpt(log_text + "\n" + stderr_text)
        if process.returncode != 0:
            raise SpiceError(
                f"ngspice exited with code {process.returncode}\n{error_excerpt}"
            )

        raw_blob = raw_path.read_bytes() if raw_path.is_file() else b""
        try:
            warnings: list[str] = []
            data, summary = _parse_log(sim, log_text, warnings)
        except (ValueError, KeyError, IndexError, TypeError):
            try:
                warnings = []
                data, summary = _parse_raw(sim, _raw_columns(raw_blob), warnings)
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise SpiceError(
                    f"no parseable {sim.analysis} output: {exc}\n{error_excerpt}"
                ) from None

        return {
            "analysis": sim.analysis,
            "status": "success",
            "engine": "ngspice",
            "version": ENGINE_VERSION,
            "model": MODEL_LABEL,
            "data": data,
            "warnings": warnings,
            "log_excerpt": _excerpt(log_text),
            "summary": summary,
        }
