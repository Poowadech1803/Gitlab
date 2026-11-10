"""Unit tests for the DC bias engineering module."""

import unittest

from dc_bias import BiasInput, solve


def make_bias(**overrides):
    """Default lab reference circuit: VCC=12, R1=100k, R2=22k, RC=2.2k, RE=1k, beta=100."""
    params = dict(vcc=12.0, r1=100e3, r2=22e3, rc=2.2e3, re=1e3, beta=100, vbe=0.70)
    params.update(overrides)
    return BiasInput(**params)


class TestReferenceCircuit(unittest.TestCase):
    """A3: results must match an independent hand calculation."""

    def test_reference_operating_point(self):
        # Independent calculation:
        #   VTH = 12*22k/122k = 2.163934... V
        #   RTH = 100k*22k/122k = 18032.787... Ω
        #   IB  = (2.163934-0.7)/(18032.787+101*1000) = 1.22986e-5 A
        #   IC  = 1.22986e-3 A -> VE = 1.24216 V, VB = 1.94216 V
        #   VC  = 12-1.22986e-3*2200 = 9.29431 V, VCE = 8.05216 V
        r = solve(make_bias())
        self.assertAlmostEqual(r.vth, 2.163934, places=5)
        self.assertAlmostEqual(r.rth, 18032.787, places=2)
        self.assertAlmostEqual(r.ib, 1.22986e-5, places=8)
        self.assertAlmostEqual(r.ic, 1.22986e-3, places=7)
        self.assertAlmostEqual(r.ie, 1.24216e-3, places=7)
        self.assertAlmostEqual(r.ve, 1.242157, places=4)
        self.assertAlmostEqual(r.vb, 1.942157, places=4)
        self.assertAlmostEqual(r.vc, 9.294312, places=4)
        self.assertAlmostEqual(r.vce, 8.052155, places=4)
        self.assertEqual(r.region, "forward-active")
        self.assertEqual(r.warnings, [])

    def test_kcl_consistency(self):
        # IE = IC + IB and VCE = VC - VE must hold exactly.
        r = solve(make_bias())
        self.assertAlmostEqual(r.ie, r.ic + r.ib, places=12)
        self.assertAlmostEqual(r.vce, r.vc - r.ve, places=12)


class TestRegions(unittest.TestCase):
    """A5: cutoff and saturation must produce warnings."""

    def test_cutoff_when_vth_below_vbe(self):
        # R2 tiny -> VTH below VBE -> transistor off.
        r = solve(make_bias(r2=1.0))
        self.assertEqual(r.region, "cutoff")
        self.assertTrue(r.warnings)
        self.assertEqual(r.ib, 0.0)

    def test_saturation_warning_when_vce_low(self):
        # Huge RC pulls VC below VE + 0.2V.
        r = solve(make_bias(rc=100e3))
        self.assertEqual(r.region, "saturation")
        self.assertTrue(any("Saturation" in w or "VCE(sat)" in w for w in r.warnings))

    def test_borderline_active_still_ok(self):
        r = solve(make_bias(rc=4.7e3))
        self.assertEqual(r.region, "forward-active")


class TestValidation(unittest.TestCase):
    """A4: invalid inputs must raise ValueError with clear messages."""

    def test_negative_resistor_rejected(self):
        with self.assertRaises(ValueError):
            from dc_bias import parse_input
            parse_input({"vcc": "12", "r1": "-1000", "r2": "22000",
                         "rc": "2200", "re": "1000", "beta": "100"})
        r = solve(make_bias(re=-5))
        # solve() assumes valid input; validation lives in parse_input.

    def test_non_numeric_rejected(self):
        from dc_bias import parse_input
        with self.assertRaises(ValueError):
            parse_input({"vcc": "twelve", "r1": "100000", "r2": "22000",
                         "rc": "2200", "re": "1000", "beta": "100"})

    def test_zero_beta_rejected(self):
        from dc_bias import parse_input
        with self.assertRaises(ValueError):
            parse_input({"vcc": "12", "r1": "100000", "r2": "22000",
                         "rc": "2200", "re": "1000", "beta": "0"})

    def test_missing_field_rejected(self):
        from dc_bias import parse_input
        with self.assertRaises(ValueError):
            parse_input({"vcc": "12", "r1": "100000", "r2": "22000", "rc": "2200"})


if __name__ == "__main__":
    unittest.main()
