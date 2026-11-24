"""Flask application: BJT Common-Emitter DC Bias web calculator.

Routes:
    GET  /           -> render input form
    POST /calculate  -> validate, solve, render results
    POST /simulate   -> validate, run ngspice, render SPICE vs analytical
"""

from flask import Flask, render_template, request

from dc_bias import (
    MODE_FIELDS,
    RESISTOR_FIELDS_BY_MODE,
    parse_input,
    solve_divider,
    solve_fixed,
    solve_emitter,
)
from plots import bode_svg, waveform_svg
from spice_engine import SpiceError, parse_sim_form, run_analysis

app = Flask(__name__)

#: Resistance unit multipliers applied before handing values to dc_bias.
UNIT_FACTORS = {"ohm": 1.0, "kohm": 1e3, "mohm": 1e6}

FORM_FIELDS = ("mode", "vcc", "r1", "r2", "rb", "rc", "re", "beta", "vbe")
RESISTOR_FIELDS = ("r1", "r2", "rb", "rc", "re")
SOLVERS = {"divider": solve_divider, "fixed": solve_fixed, "emitter": solve_emitter}

#: Lab 03 form defaults, shared by GET / and the simulation page shell.
INDEX_DEFAULTS = {
    "mode": "divider",
    "vcc": "12.0",
    "r1": "100", "r1_unit": "kohm",
    "r2": "22", "r2_unit": "kohm",
    "rb": "1.0", "rb_unit": "mohm",
    "rc": "2.2", "rc_unit": "kohm",
    "re": "1.0", "re_unit": "kohm",
    "beta": "100",
    "vbe": "0.70",
}

SIM_FIELDS = (
    "analysis", "vcc", "r1", "r2", "rc", "re", "rl",
    "cin", "cout", "amp", "freq",
)
SIM_DEFAULTS = {
    "analysis": "dc", "vcc": "12", "r1": "100", "r2": "22",
    "rc": "2.2", "re": "1", "rl": "10", "cin": "10",
    "cout": "10", "amp": "10", "freq": "1",
}


@app.route("/", methods=["GET"])
def index():
    """Render the input form with default values."""
    return render_template(
        "index.html", form=INDEX_DEFAULTS, mode=INDEX_DEFAULTS["mode"],
        sim_form=SIM_DEFAULTS, sim_status="idle",
        sim_result=None, sim_errors=None,
        bode_svg=None, wave_svg=None, analytical_ref=None,
    )


@app.route("/calculate", methods=["POST"])
def calculate():
    """Validate the submitted form, solve the DC bias, render results."""
    data = {k: request.form.get(k, "").strip() for k in FORM_FIELDS}
    for key in RESISTOR_FIELDS:
        data[f"{key}_unit"] = request.form.get(f"{key}_unit", "kohm").strip()

    mode = data.get("mode") or "divider"
    errors = None
    result = None

    if mode not in MODE_FIELDS:
        errors = [f"โหมดไม่รู้จัก (unknown mode: {mode}) — ใช้ divider, fixed หรือ emitter"]
        return render_template(
            "index.html", form=data, result=result, errors=errors, mode=mode
        )

    # Changing mode only refreshes the form; it is not a solve attempt.
    if request.form.get("action") == "mode":
        return render_template(
            "index.html", form=data, result=None, errors=None, mode=mode
        )

    try:
        si = dict(data)
        for key in RESISTOR_FIELDS_BY_MODE[mode]:
            raw = si.get(key, "")
            if not raw:
                continue  # parse_input() reports the missing field
            try:
                value = float(raw)
            except ValueError:
                continue  # parse_input() reports "must be numeric"
            factor = UNIT_FACTORS.get(si.get(f"{key}_unit", "kohm"), 1e3)
            si[key] = str(round(value * factor, 9))
        bias = parse_input(si, mode)
        # Solvers hand back a dict with fixed keys/units for every mode.
        result = SOLVERS[mode](bias).to_dict()
    except ValueError as exc:
        errors = str(exc).split("; ")
        result = None

    return render_template(
        "index.html", form=data, result=result, errors=errors, mode=mode
    )


@app.route("/simulate", methods=["POST"])
def simulate():
    """Validate the simulation form, run ngspice, render its result."""
    sim_form = {key: request.form.get(key, "").strip() for key in SIM_FIELDS}

    def page(status, errors=None, result=None, bode=None, wave=None, analytical=None):
        """Render the shared page; every failure path clears result/graphs."""
        return render_template(
            "index.html", form=INDEX_DEFAULTS, mode=INDEX_DEFAULTS["mode"],
            result=None, errors=None,
            sim_form=sim_form, sim_status=status, sim_errors=errors,
            sim_result=result, bode_svg=bode, wave_svg=wave,
            analytical_ref=analytical,
        )

    # Changing the analysis only refreshes the form; it is not a run attempt.
    if request.form.get("action") == "mode":
        return page("idle")

    try:
        sim = parse_sim_form(sim_form)
    except ValueError as exc:
        return page("error", errors=str(exc).split("; "))

    try:
        sim_result = run_analysis(sim)
    except SpiceError as exc:
        return page("error", errors=[str(exc)])

    bode = wave = analytical = None
    if sim.analysis == "dc":
        # Lab 03's divider approximation, always with its documented β/VBE.
        analytical = solve_divider(parse_input({
            "vcc": str(sim.vcc), "r1": str(sim.r1), "r2": str(sim.r2),
            "rc": str(sim.rc), "re": str(sim.re),
            "beta": "100", "vbe": "0.70",
        }, "divider")).to_dict()
    elif sim.analysis == "ac":
        bode = bode_svg(sim_result["data"])
    elif sim.analysis == "tran":
        wave = waveform_svg(sim_result["data"])

    return page("success", result=sim_result, bode=bode, wave=wave,
                analytical=analytical)


if __name__ == "__main__":
    app.run(debug=True)
