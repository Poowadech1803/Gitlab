"""HTTP tests for the Flask routes (A1, A2, A4, A5, A6)."""

import unittest

from app import app


class TestWebRoutes(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config["TESTING"] = True

    def _post(self, **overrides):
        form = {"vcc": "12", "r1": "100000", "r2": "22000",
                "rc": "2200", "re": "1000", "beta": "100", "vbe": "0.70"}
        form.update({k: str(v) for k, v in overrides.items()})
        return self.client.post("/calculate", data=form)

    def test_a1_get_index_returns_200_and_form(self):
        rv = self.client.get("/")
        self.assertEqual(rv.status_code, 200)
        html = rv.get_data(as_text=True)
        self.assertIn("Calculate DC Bias", html)
        self.assertIn('name="vcc"', html)
        self.assertIn('name="beta"', html)

    def test_a2_post_calculates_via_backend(self):
        rv = self._post()
        self.assertEqual(rv.status_code, 200)
        html = rv.get_data(as_text=True)
        # Reference values computed independently (see test_dc_bias.py).
        self.assertIn("1.942", html)   # VB
        self.assertIn("1.242", html)   # VE
        self.assertIn("9.294", html)   # VC
        self.assertIn("8.052", html)   # VCE
        self.assertIn("1.2299", html)  # IC in mA
        self.assertIn("forward-active", html)

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
        rv = self._post(r2="1")
        self.assertEqual(rv.status_code, 200)
        html = rv.get_data(as_text=True)
        self.assertIn("Cutoff", html)
        self.assertIn("คำเตือน", html)

    def test_a5_saturation_warning_rendered(self):
        rv = self._post(rc="100000")
        self.assertEqual(rv.status_code, 200)
        html = rv.get_data(as_text=True)
        self.assertIn("Saturation", html)


if __name__ == "__main__":
    unittest.main()
