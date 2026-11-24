"""Pure inline-SVG plots for the AC and transient points from ngspice.

The functions in this module never run a simulator and hold no circuit state:
they only map the numeric values in the point dictionaries onto an SVG
viewBox. Every coordinate and tick label comes from those values; labels and
colours are fixed literals, escaped before they are embedded.
"""

from __future__ import annotations

import math
from html import escape

_XMLNS = "http://www.w3.org/2000/svg"

# Constant plot-area insets keep the centre independent of the sample values.
_INSET_LEFT = 70.0
_INSET_RIGHT = 70.0
_INSET_TOP = 45.0
_INSET_BOTTOM = 50.0

_AXIS_COLOR = "#666666"
_TEXT_COLOR = "#222222"
_GAIN_COLOR = "#1f77b4"
_PHASE_COLOR = "#d62728"
_VIN_COLOR = "#1f77b4"
_VOUT_COLOR = "#2ca02c"


def _fmt(value: float) -> str:
    """Compact numeric text that never contains markup characters."""
    return f"{value:g}"


def _map(value: float, low: float, high: float,
         start: float, end: float) -> float:
    """Linear map; a degenerate range puts the value at the range centre."""
    if high == low:
        return (start + end) / 2.0
    return start + (value - low) / (high - low) * (end - start)


def _map_y(value: float, low: float, high: float,
           top: float, bottom: float) -> float:
    """Linear map with SVG's y axis inverted; degenerate ranges are centred."""
    if high == low:
        return (top + bottom) / 2.0
    return bottom - (value - low) / (high - low) * (bottom - top)


def _ticks(low: float, high: float) -> list[float]:
    """Three evenly spaced tick values, with duplicates removed."""
    values: list[float] = []
    for value in (low, (low + high) / 2.0, high):
        if not values or value != values[-1]:
            values.append(value)
    return values


def _line(x1: float, y1: float, x2: float, y2: float,
          color: str = _AXIS_COLOR, thickness: float = 1.0) -> str:
    return (
        f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
        f'stroke="{color}" stroke-width="{thickness:g}"/>'
    )


def _text(x: float, y: float, label: str, anchor: str = "middle",
          color: str = _TEXT_COLOR, transform: str = "") -> str:
    rotated = f' transform="{escape(transform, quote=True)}"' if transform else ""
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" '
        f'fill="{color}"{rotated}>{escape(label)}</text>'
    )


def _polyline(coordinates: list[tuple[float, float]], color: str) -> str:
    points = " ".join(f"{x:.3f},{y:.3f}" for x, y in coordinates)
    return (
        f'<polyline points="{points}" fill="none" stroke="{color}" '
        'stroke-width="2"/>'
    )


def _svg(width: int, height: int, body: list[str]) -> str:
    header = (
        f'<svg xmlns="{_XMLNS}" viewBox="0 0 {_fmt(width)} {_fmt(height)}" '
        'role="img">'
    )
    return "\n".join((header, *body, "</svg>"))


def bode_svg(points: list[dict], width: int = 720, height: int = 280) -> str:
    """Render gain and phase against log10 frequency as inline SVG.

    Gain uses the left linear axis and phase the right linear axis. Invalid
    samples are ignored; with no usable samples the result is an empty string.
    """
    data: list[tuple[float, float, float, float]] = []
    for point in points or []:
        try:
            frequency = float(point["freq_hz"])
            gain = float(point["gain_db"])
            phase = float(point["phase_deg"])
        except (KeyError, TypeError, ValueError):
            continue
        if frequency <= 0.0 or not all(
            math.isfinite(value) for value in (frequency, gain, phase)
        ):
            continue
        data.append((math.log10(frequency), frequency, gain, phase))
    if not data:
        return ""

    left = _INSET_LEFT
    right = width - _INSET_RIGHT
    top = _INSET_TOP
    bottom = height - _INSET_BOTTOM
    middle_y = (top + bottom) / 2.0

    log_freqs = [sample[0] for sample in data]
    gains = [sample[2] for sample in data]
    phases = [sample[3] for sample in data]
    freq_low, freq_high = min(log_freqs), max(log_freqs)
    gain_low, gain_high = min(gains), max(gains)
    phase_low, phase_high = min(phases), max(phases)

    def px(log_frequency: float) -> float:
        return _map(log_frequency, freq_low, freq_high, left, right)

    def gain_y(value: float) -> float:
        return _map_y(value, gain_low, gain_high, top, bottom)

    def phase_y(value: float) -> float:
        return _map_y(value, phase_low, phase_high, top, bottom)

    gain_line = [
        (px(sample[0]), gain_y(sample[2])) for sample in data
    ]
    phase_line = [
        (px(sample[0]), phase_y(sample[3])) for sample in data
    ]

    body = [
        _line(left, bottom, right, bottom),
        _line(left, top, left, bottom),
        _line(right, top, right, bottom),
    ]
    for value in _ticks(gain_low, gain_high):
        y = gain_y(value)
        body.append(_line(left - 5.0, y, left, y))
        body.append(_text(left - 9.0, y + 4.0, _fmt(value), anchor="end"))
    for value in _ticks(phase_low, phase_high):
        y = phase_y(value)
        body.append(_line(right, y, right + 5.0, y))
        body.append(_text(right + 9.0, y + 4.0, _fmt(value), anchor="start"))
    for log_frequency in _ticks(freq_low, freq_high):
        x = px(log_frequency)
        body.append(_line(x, bottom, x, bottom + 5.0))
        body.append(_text(x, bottom + 18.0, _fmt(10.0 ** log_frequency)))

    body.extend((
        _text((left + right) / 2.0, height - 8.0, "Frequency (Hz)"),
        _text(18.0, middle_y, "Gain (dB)",
              transform=f"rotate(-90 18.00 {middle_y:.2f})"),
        _text(width - 18.0, middle_y, "Phase (°)", color=_PHASE_COLOR,
              transform=f"rotate(90 {width - 18.0:.2f} {middle_y:.2f})"),
        _line(left, 22.0, left + 18.0, 22.0, color=_GAIN_COLOR, thickness=2.0),
        _text(left + 24.0, 26.0, "Gain (dB)", anchor="start", color=_GAIN_COLOR),
        _line(left + 140.0, 22.0, left + 158.0, 22.0,
              color=_PHASE_COLOR, thickness=2.0),
        _text(left + 164.0, 26.0, "Phase (°)", anchor="start",
              color=_PHASE_COLOR),
        _polyline(gain_line, _GAIN_COLOR),
        _polyline(phase_line, _PHASE_COLOR),
    ))
    return _svg(width, height, body)


def waveform_svg(points: list[dict], width: int = 720,
                 height: int = 280) -> str:
    """Render Vin and Vout against time in milliseconds as inline SVG.

    Both series share one linear voltage axis. Invalid samples are ignored;
    with no usable samples the result is an empty string.
    """
    data: list[tuple[float, float, float]] = []
    for point in points or []:
        try:
            time_s = float(point["time_s"])
            vin = float(point["vin_v"])
            vout = float(point["vout_v"])
        except (KeyError, TypeError, ValueError):
            continue
        if not all(math.isfinite(value) for value in (time_s, vin, vout)):
            continue
        data.append((time_s * 1000.0, vin, vout))
    if not data:
        return ""

    left = _INSET_LEFT
    right = width - _INSET_RIGHT
    top = _INSET_TOP
    bottom = height - _INSET_BOTTOM
    middle_y = (top + bottom) / 2.0

    times_ms = [sample[0] for sample in data]
    voltages = [voltage for sample in data for voltage in (sample[1], sample[2])]
    time_low, time_high = min(times_ms), max(times_ms)
    voltage_low, voltage_high = min(voltages), max(voltages)

    def px(time_ms: float) -> float:
        return _map(time_ms, time_low, time_high, left, right)

    def voltage_y(value: float) -> float:
        return _map_y(value, voltage_low, voltage_high, top, bottom)

    vin_line = [
        (px(sample[0]), voltage_y(sample[1])) for sample in data
    ]
    vout_line = [
        (px(sample[0]), voltage_y(sample[2])) for sample in data
    ]

    body = [
        _line(left, bottom, right, bottom),
        _line(left, top, left, bottom),
    ]
    for value in _ticks(voltage_low, voltage_high):
        y = voltage_y(value)
        body.append(_line(left - 5.0, y, left, y))
        body.append(_text(left - 9.0, y + 4.0, _fmt(value), anchor="end"))
    for value in _ticks(time_low, time_high):
        x = px(value)
        body.append(_line(x, bottom, x, bottom + 5.0))
        body.append(_text(x, bottom + 18.0, _fmt(value)))

    body.extend((
        _text((left + right) / 2.0, height - 8.0, "Time (ms)"),
        _text(18.0, middle_y, "Vin, Vout (V)",
              transform=f"rotate(-90 18.00 {middle_y:.2f})"),
        _line(left, 22.0, left + 18.0, 22.0, color=_VIN_COLOR, thickness=2.0),
        _text(left + 24.0, 26.0, "Vin", anchor="start", color=_VIN_COLOR),
        _line(left + 140.0, 22.0, left + 158.0, 22.0,
              color=_VOUT_COLOR, thickness=2.0),
        _text(left + 164.0, 26.0, "Vout", anchor="start", color=_VOUT_COLOR),
        _polyline(vin_line, _VIN_COLOR),
        _polyline(vout_line, _VOUT_COLOR),
    ))
    return _svg(width, height, body)
