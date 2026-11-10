"""HTTP tests for the Flask routes (A1, A2, A4, A5, A6)."""

import unittest

from app import app


def reference_form(**overrides):
    """Default reference circuit (units handled the same way as the web form)."""
    form = {
        "vcc": "12.0",
        "r1": "100", "r1_unit": "kohm",
        "r2": "22", "r2_unit": "kohm",
        "rc": "2.2", "rc_unit": "kohm",
        "re": "1.0", "re_unit": "kohm",
        "beta": "100",
        "vbe": "0.70",
    }
    form.update({k: str(v) for k, v in overrides.items()})
    return form


class TestWebRoutes(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config["TESTING"] = True

    def _post(self, **overrides):
        return self.client.post("/calculate", data=reference_form(**overrides))

    def test_a1_get_index_returns_200_and_form(self):
        rv = self.client.get("/")
        self.assertEqual(rv.status_code, 200)
        html = rv.get_data(as_text=True)
        self.assertIn("Calculate DC Bias", html)
        self.assertIn('name="vcc"', html)
        self.assertIn('name="beta"', html)
        self.assertIn("Input Parameters", html)
        self.assertIn("DC Bias Results", html)

    def test_a2_post_calculates_via_backend(self):
        rv = self._post()
        self.assertEqual(rv.status_code, 200)
        html = rv.get_data(as_text=True)
        # Reference values computed independently (see tests/test_dc_bias.py).
        self.assertIn("1.94 V", html)   # VB
        self.assertIn("1.24 V", html)   # VE
        self.assertIn("9.29 V", html)   # VC
        self.assertIn("8.05 V", html)   # VCE
        self.assertIn("1.23 mA", html)  # IC
        self.assertIn("12.3 µA", html)  # IB
        self.assertIn("forward-active", html)

    def test_a2_ohm_unit_gives_same_result(self):
        rv = self._post(r1_unit="ohm", r1="100000",
                        r2_unit="ohm", r2="22000",
                        rc_unit="ohm", rc="2200",
                        re_unit="ohm", re="1000")
        self.assertEqual(rv.status_code, 200)
        html = rv.get_data(as_text=True)
        self.assertIn("8.05 V", html)
        self.assertIn("1.23 mA", html)

    def test_a4_invalid_input_shows_error_page_not_crash(self):
        rv = self._post(beta="-5")
        self.assertEqual(rv.status_code, 200)
        html = rv.get_data(as_text=True)
        self.assertIn("ข้อผิดพลาด", html)
        self.assertIn("beta", html)

    def test_a4_non_numeric_input_shows_error(self):
        rv = self._post(vcc="abc")
        self.assertEqual(rv.status_code, 200)
        html = rv.get_data(as_text=True)
        self.assertIn("ต้องเป็นตัวเลข", html)

    def test_a5_cutoff_warning_rendered(self):
        rv = self._post(r2="1")  # VTH = 12*1k/101k << VBE
        self.assertEqual(rv.status_code, 200)
        html = rv.get_data(as_text=True)
        self.assertIn("Cutoff", html)
        self.assertIn("คำเตือน", html)

    def test_a5_saturation_warning_rendered(self):
        rv = self._post(rc="100")  # 100 kΩ pulls VC far below VE
        self.assertEqual(rv.status_code, 200)
        html = rv.get_data(as_text=True)
        self.assertIn("Saturation", html)


if __name__ == "__main__":
    unittest.main()
