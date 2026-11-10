"""Flask application: BJT Common-Emitter DC Bias web calculator.

Routes:
    GET  /           -> render input form
    POST /calculate  -> validate, solve, render results
"""

from flask import Flask, render_template, request

from dc_bias import BiasInput, BiasResult, parse_input, solve

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    """Render the input form with default values."""
    defaults = {
        "vcc": "12", "r1": "100000", "r2": "22000",
        "rc": "2200", "re": "1000", "beta": "100", "vbe": "0.70",
    }
    return render_template("index.html", form=defaults)


@app.route("/calculate", methods=["POST"])
def calculate():
    """Validate the submitted form, solve the DC bias, render results."""
    fields = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")
    data = {k: request.form.get(k, "").strip() for k in fields}

    errors = None
    result = None
    try:
        bias = parse_input(data)
        result = solve(bias)
    except ValueError as exc:
        errors = str(exc).split("; ")

    return render_template(
        "index.html", form=data, result=result, errors=errors
    )


if __name__ == "__main__":
    app.run(debug=True)
