"""Flask application: BJT Common-Emitter DC Bias web calculator.

Routes:
    GET  /           -> render input form
    POST /calculate  -> validate, solve, render results
"""

from flask import Flask, render_template, request

from dc_bias import parse_input, solve

app = Flask(__name__)

#: Resistance unit multipliers applied before handing values to dc_bias.
UNIT_FACTORS = {"ohm": 1.0, "kohm": 1e3, "mohm": 1e6}

RESISTOR_FIELDS = ("r1", "r2", "rc", "re")


@app.route("/", methods=["GET"])
def index():
    """Render the input form with default values."""
    defaults = {
        "vcc": "12.0",
        "r1": "100", "r1_unit": "kohm",
        "r2": "22", "r2_unit": "kohm",
        "rc": "2.2", "rc_unit": "kohm",
        "re": "1.0", "re_unit": "kohm",
        "beta": "100",
        "vbe": "0.70",
    }
    return render_template("index.html", form=defaults)


@app.route("/calculate", methods=["POST"])
def calculate():
    """Validate the submitted form, solve the DC bias, render results."""
    fields = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")
    data = {k: request.form.get(k, "").strip() for k in fields}
    for key in RESISTOR_FIELDS:
        data[f"{key}_unit"] = request.form.get(f"{key}_unit", "kohm").strip()

    errors = None
    result = None
    try:
        si = dict(data)
        for key in RESISTOR_FIELDS:
            raw = si.get(key, "")
            if not raw:
                continue  # parse_input() reports the missing field
            try:
                value = float(raw)
            except ValueError:
                continue  # parse_input() reports "must be numeric"
            factor = UNIT_FACTORS.get(si.get(f"{key}_unit", "kohm"), 1e3)
            si[key] = str(round(value * factor, 9))
        bias = parse_input(si)
        result = solve(bias)
    except ValueError as exc:
        errors = str(exc).split("; ")

    return render_template(
        "index.html", form=data, result=result, errors=errors
    )


if __name__ == "__main__":
    app.run(debug=True)
