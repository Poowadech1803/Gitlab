"""HTTP tests for the Lab 04 SPICE route and the Lab 03 regression."""

import unittest
from unittest import mock

from app import app
from spice_engine import SpiceError


VALID_SIM_FORM = {
    "analysis": "dc",
    "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
    "rl": "10", "cin": "10", "cout": "10", "amp": "10", "freq": "1",
}

CALC_FORM = {
    "mode": "divider", "vcc": "12.0",
    "r1": "100", "r1_unit": "kohm",
    "r2": "22", "r2_unit": "kohm",
    "rc": "2.2", "rc_unit": "kohm",
    "re": "1.0", "re_unit": "kohm",
    "beta": "100", "vbe": "0.70",
}

# Complete engine results: every field run_analysis() returns, with DC values
# deliberately different from the independent Lab 03 analytical reference.
DC_RESULT = {
    "analysis": "dc",
    "status": "success",
    "engine": "ngspice",
    "version": "47-1 (MSYS2 package, upstream ngspice 47)",
    "model": "Q1_NPN (local documented 2N3904-style model)",
    "data": {"vb": 2.00, "ve": 1.30, "vc": 9.00, "vce": 7.70, "ic_ma": 1.10},
    "warnings": [],
    "log_excerpt": "v(b) = 2.0, v(e) = 1.3, v(c) = 9.0",
    "summary": {},
}

AC_RESULT = {
    "analysis": "ac",
    "status": "success",
    "engine": "ngspice",
    "version": "47-1 (MSYS2 package, upstream ngspice 47)",
    "model": "Q1_NPN (local documented 2N3904-style model)",
    "data": [
        {"freq_hz": 1000.0, "gain_db": 18.0, "phase_deg": -175.0},
        {"freq_hz": 10000.0, "gain_db": 22.0, "phase_deg": -172.0},
        {"freq_hz": 100000.0, "gain_db": 2.0, "phase_deg": -190.0},
    ],
    "warnings": [],
    "log_excerpt": "ac sweep complete",
    "summary": {"midband_gain_db": 22.0, "f_low_hz": 1000.0, "f_high_hz": 100000.0},
}

TRAN_RESULT = {
    "analysis": "tran",
    "status": "success",
    "engine": "ngspice",
    "version": "47-1 (MSYS2 package, upstream ngspice 47)",
    "model": "Q1_NPN (local documented 2N3904-style model)",
    "data": [
        {"time_s": 0.0, "vin_v": 0.01, "vout_v": -0.50},
        {"time_s": 0.0005, "vin_v": -0.01, "vout_v": 0.50},
        {"time_s": 0.001, "vin_v": 0.01, "vout_v": -0.50},
    ],
    "warnings": [],
    "log_excerpt": "tran sweep complete",
    "summary": {"phase_relation": "inverted"},
}


class TestSimulateRoute(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def _post(self, **overrides):
        data = dict(VALID_SIM_FORM)
        data.update(overrides)
        return self.client.post("/simulate", data=data)

    def test_simulate_dc_success_shows_status_and_model(self):
        with mock.patch("app.run_analysis", return_value=DC_RESULT):
            html = self._post().get_data(as_text=True)
        self.assertIn("success", html)
        self.assertIn("ngspice", html)
        self.assertIn("SPICE (ngspice)", html)
        self.assertIn("Analytical (Lab 03)", html)
        # SPICE numbers are distinct from the hand-checked Lab 03 reference.
        self.assertIn("2.00 V", html)
        self.assertIn("1.10 mA", html)
        for expected in ("1.94 V", "1.24 V", "9.29 V", "8.05 V", "1.23 mA"):
            self.assertIn(expected, html)

    def test_simulate_invalid_re_shows_error_no_stale(self):
        with mock.patch("app.run_analysis",
                        side_effect=AssertionError("validation must precede ngspice")):
            html = self._post(re="-1", cin="abc").get_data(as_text=True)
        self.assertIn("error", html)
        self.assertIn("RE ต้องมากกว่า 0", html)
        self.assertIn("Cin ต้องเป็นตัวเลข", html)
        self.assertNotIn("2.00 V", html)
        self.assertNotIn("Analytical (Lab 03)", html)
        self.assertNotIn("Frequency (Hz)", html)
        self.assertNotIn("Vin, Vout (V)", html)

    def test_simulate_engine_error_shows_error_no_stale(self):
        message = "ngspice not found. Install ngspice 47 or set NGSPICE_EXE"
        with mock.patch("app.run_analysis", side_effect=SpiceError(message)):
            html = self._post().get_data(as_text=True)
        self.assertIn("error", html)
        self.assertIn(message, html)
        self.assertNotIn("2.00 V", html)
        self.assertNotIn("Analytical (Lab 03)", html)
        self.assertNotIn("Frequency (Hz)", html)
        self.assertNotIn("Vin, Vout (V)", html)

    def test_simulate_ac_shows_bode_only_not_analytical(self):
        with mock.patch("app.run_analysis", return_value=AC_RESULT):
            html = self._post(analysis="ac").get_data(as_text=True)
        self.assertIn("success", html)
        self.assertIn("Frequency (Hz)", html)
        self.assertIn("Gain (dB)", html)
        self.assertIn("Phase (°)", html)
        self.assertNotIn("Analytical (Lab 03)", html)
        self.assertNotIn("Time (ms)", html)

    def test_simulate_tran_shows_waveform_only_not_analytical(self):
        with mock.patch("app.run_analysis", return_value=TRAN_RESULT):
            html = self._post(analysis="tran").get_data(as_text=True)
        self.assertIn("success", html)
        self.assertIn("Time (ms)", html)
        self.assertIn("Vin, Vout (V)", html)
        self.assertNotIn("Analytical (Lab 03)", html)
        self.assertNotIn("Frequency (Hz)", html)

    def test_simulate_mode_switch_does_not_run_engine(self):
        with mock.patch("app.run_analysis",
                        side_effect=AssertionError("mode switch must not run ngspice")):
            html = self._post(analysis="ac", action="mode").get_data(as_text=True)
        self.assertIn("idle", html)
        self.assertNotIn("Frequency (Hz)", html)
        self.assertNotIn("error", html)

    def test_get_index_exposes_sim_defaults_and_idle_status(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("Lab 04 · CE Amplifier Simulator", html)
        self.assertIn('name="analysis"', html)
        self.assertIn('name="rl"', html)
        self.assertIn('value="12"', html)
        self.assertIn("idle", html)

    def test_calculate_regression_still_passes(self):
        html = self.client.post("/calculate", data=CALC_FORM).get_data(as_text=True)
        self.assertIn("1.94 V", html)
        self.assertIn("1.23 mA", html)
        self.assertIn("forward-active", html)
        self.assertNotIn("Lab 04 · CE Amplifier Simulator", html)


if __name__ == "__main__":
    unittest.main()
