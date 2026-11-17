"""Flask application: BJT Common-Emitter DC Bias web calculator.

Routes:
    GET  /           -> render input form
    POST /calculate  -> validate, solve, render results
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

app = Flask(__name__)

#: Resistance unit multipliers applied before handing values to dc_bias.
UNIT_FACTORS = {"ohm": 1.0, "kohm": 1e3, "mohm": 1e6}

FORM_FIELDS = ("mode", "vcc", "r1", "r2", "rb", "rc", "re", "beta", "vbe")
RESISTOR_FIELDS = ("r1", "r2", "rb", "rc", "re")
SOLVERS = {"divider": solve_divider, "fixed": solve_fixed, "emitter": solve_emitter}


@app.route("/", methods=["GET"])
def index():
    """Render the input form with default values."""
    defaults = {
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
    return render_template("index.html", form=defaults, mode=defaults["mode"])


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
        result = SOLVERS[mode](bias)
    except ValueError as exc:
        errors = str(exc).split("; ")
        result = None

    return render_template(
        "index.html", form=data, result=result, errors=errors, mode=mode
    )


if __name__ == "__main__":
    app.run(debug=True)
