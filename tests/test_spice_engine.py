"""Unit tests for simulation form validation and ngspice discovery."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from spice_engine import (
    SimInput, SpiceError, build_netlist, find_ngspice, parse_sim_form,
)


VALID_FORM = {
    "analysis": "dc",
    "vcc": "12",
    "r1": "100", "r2": "22", "rc": "2.2", "re": "1", "rl": "10",
    "cin": "10", "cout": "10",
    "amp": "10", "freq": "1",
}

MODEL_PATH = str(Path("spice") / "q1_npn.model")


class TestParseSimForm(unittest.TestCase):
    """A4: the web form must become finite, positive SI values or one error list."""

    def test_parse_sim_form_defaults_are_si(self):
        sim = parse_sim_form(VALID_FORM)
        self.assertEqual(sim.analysis, "dc")
        self.assertEqual(sim.vcc, 12.0)
        self.assertEqual(sim.r1, 100_000.0)
        self.assertEqual(sim.r2, 22_000.0)
        self.assertEqual(sim.rc, 2_200.0)
        self.assertEqual(sim.re, 1_000.0)
        self.assertEqual(sim.rl, 10_000.0)
        self.assertEqual(sim.cin, 10e-6)
        self.assertEqual(sim.cout, 10e-6)
        self.assertEqual(sim.amp, 0.010)
        self.assertEqual(sim.freq, 1_000.0)
        self.assertIsInstance(sim, SimInput)

    def test_parse_sim_form_rejects_zero_re_and_bad_source(self):
        with self.assertRaises(ValueError) as cm:
            parse_sim_form({**VALID_FORM, "re": "0", "amp": "0", "freq": "-1"})
        msg = str(cm.exception)
        self.assertIn("RE", msg)
        self.assertIn("amp", msg)
        self.assertIn("freq", msg)
        # All three faults must be reported together, not one at a time.
        self.assertEqual(len(msg.split("; ")), 3)

    def test_unknown_analysis_rejected(self):
        with self.assertRaises(ValueError) as cm:
            parse_sim_form({**VALID_FORM, "analysis": "bogus"})
        msg = str(cm.exception)
        self.assertIn("bogus", msg)
        self.assertIn("analysis", msg)

    def test_non_numeric_rejected(self):
        with self.assertRaises(ValueError) as cm:
            parse_sim_form({**VALID_FORM, "vcc": "twelve"})
        self.assertIn("VCC", str(cm.exception))

    def test_non_finite_rejected(self):
        for bad in ("nan", "inf", "-inf"):
            with self.subTest(bad=bad), self.assertRaises(ValueError) as cm:
                parse_sim_form({**VALID_FORM, "vcc": bad})
            self.assertIn("VCC", str(cm.exception))

    def test_missing_and_blank_values_rejected(self):
        form = {key: value for key, value in VALID_FORM.items() if key != "cin"}
        form["rl"] = "   "
        with self.assertRaises(ValueError) as cm:
            parse_sim_form(form)
        msg = str(cm.exception)
        self.assertIn("Cin", msg)
        self.assertIn("RL", msg)

    def test_every_numeric_field_must_be_strictly_positive(self):
        labels = {
            "vcc": "VCC", "r1": "R1", "r2": "R2", "rc": "RC", "re": "RE",
            "rl": "RL", "cin": "Cin", "cout": "Cout", "amp": "amp",
            "freq": "freq",
        }
        for field, label in labels.items():
            with self.subTest(field=field), self.assertRaises(ValueError) as cm:
                parse_sim_form({**VALID_FORM, field: "0"})
            self.assertIn(label, str(cm.exception))

    def test_analysis_is_stripped_and_lowercased(self):
        sim = parse_sim_form({**VALID_FORM, "analysis": "  AC  "})
        self.assertEqual(sim.analysis, "ac")

    def test_overflow_after_unit_conversion_rejected(self):
        with self.assertRaises(ValueError) as cm:
            parse_sim_form({**VALID_FORM, "r1": "1e307"})  # 1e307 kΩ is not finite in Ω
        msg = str(cm.exception)
        self.assertIn("R1", msg)
        self.assertIn("finite", msg)


class TestFindNgspice(unittest.TestCase):
    """B1: discovery is deterministic and never requires a running simulator."""

    def test_explicit_env_path_wins(self):
        with tempfile.TemporaryDirectory() as root:
            exe = Path(root) / "ngspice.exe"
            exe.write_text("not really an executable", encoding="utf-8")
            env = {"NGSPICE_EXE": str(exe), "LOCALAPPDATA": str(Path(root) / "other")}
            with mock.patch.dict(os.environ, env, clear=True), \
                    mock.patch("spice_engine.shutil.which", return_value=None):
                self.assertEqual(find_ngspice(), str(exe))

    def test_missing_explicit_env_path_does_not_fall_back(self):
        with tempfile.TemporaryDirectory() as root:
            missing = str(Path(root) / "missing" / "ngspice.exe")
            env = {"NGSPICE_EXE": missing, "LOCALAPPDATA": root}
            with mock.patch.dict(os.environ, env, clear=True), \
                    mock.patch("spice_engine.shutil.which", return_value="C:\\bin\\ngspice.exe"):
                with self.assertRaises(SpiceError) as cm:
                    find_ngspice()
            self.assertIn(missing, str(cm.exception))

    def test_which_is_used_when_env_is_absent(self):
        env = {"PATH": "C:\\bin"}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch("spice_engine.shutil.which", return_value="C:\\bin\\ngspice.exe"):
            self.assertEqual(find_ngspice(), "C:\\bin\\ngspice.exe")

    def test_common_windows_install_is_found(self):
        with tempfile.TemporaryDirectory() as root:
            exe = Path(root) / "ngspice-47" / "clang64" / "bin" / "ngspice.exe"
            exe.parent.mkdir(parents=True)
            exe.write_text("not really an executable", encoding="utf-8")
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": root}, clear=True), \
                    mock.patch("spice_engine.shutil.which", return_value=None):
                self.assertEqual(find_ngspice(), str(exe))

    def test_not_found_error_mentions_ngspice_exe(self):
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": root}, clear=True), \
                    mock.patch("spice_engine.shutil.which", return_value=None):
                with self.assertRaises(SpiceError) as cm:
                    find_ngspice()
        self.assertIn("NGSPICE_EXE", str(cm.exception))


class TestBuildNetlist(unittest.TestCase):
    """B2-B6: one netlist contains exactly the requested analysis and SI values."""

    def test_build_netlist_dc_has_only_op_and_include(self):
        sim = parse_sim_form({**VALID_FORM, "analysis": "dc"})
        net = build_netlist(sim, MODEL_PATH)
        self.assertIn(".op", net)
        self.assertIn(".print op v(b) v(e) v(c) i(rc) i(vcc)", net)
        self.assertNotIn(".ac", net)
        self.assertNotIn(".tran", net)
        self.assertIn("R1 vcc b 100000", net)
        self.assertIn(".include spice/q1_npn.model", net)
        self.assertIn("Q1_NPN", net)
        self.assertIn(".end", net)

    def test_build_netlist_emits_full_circuit(self):
        net = build_netlist(parse_sim_form(VALID_FORM), MODEL_PATH)
        for line in (
            "VCC vcc 0 DC 12",
            "VIN in 0 DC 0 AC 0.01 SIN(0 0.01 1000)",
            "R1 vcc b 100000",
            "R2 b 0 22000",
            "RC vcc c 2200",
            "RE e 0 1000",
            "RL out 0 10000",
            "Q1 c b e Q1_NPN",
            "Cin in b 1e-05",
            "Cout c out 1e-05",
        ):
            with self.subTest(line=line):
                self.assertIn(line, net)
        self.assertNotIn("CE e 0", net)  # baseline has no emitter bypass cap

    def test_ac_directive(self):
        net = build_netlist(parse_sim_form({**VALID_FORM, "analysis": "ac"}), MODEL_PATH)
        self.assertIn(".ac dec 20 1 10Meg", net)
        self.assertIn(".print ac vdb(in) vdb(out) vp(in) vp(out)", net)
        self.assertNotIn(".op", net)
        self.assertNotIn(".tran", net)

    def test_tran_directive_uses_frequency(self):
        net = build_netlist(parse_sim_form({**VALID_FORM, "analysis": "tran"}), MODEL_PATH)
        # freq = 1 kHz -> stop = 5/1000 = 5 ms, step = 5 ms/2000 = 2.5 µs.
        self.assertIn(".tran 2.5e-06 0.005", net)
        self.assertIn(".print tran v(in) v(out)", net)
        self.assertNotIn(".op", net)
        self.assertNotIn(".ac", net)

    def test_tran_directive_respects_one_millisecond_floor(self):
        form = {**VALID_FORM, "analysis": "tran", "freq": "1000"}  # 1 MHz
        net = build_netlist(parse_sim_form(form), MODEL_PATH)
        # 5/1 MHz = 5 µs < 1 ms floor -> stop = 1 ms, step = 0.5 µs.
        self.assertIn(".tran 5e-07 0.001", net)

    def test_form_text_never_reaches_command(self):
        with self.assertRaises(ValueError):
            parse_sim_form({**VALID_FORM, "vcc": "12; .tran 1 1"})
        net = build_netlist(parse_sim_form({**VALID_FORM, "r1": "1e2"}), MODEL_PATH)
        self.assertIn("R1 vcc b 100000", net)
        self.assertNotIn("1e2", net)
        self.assertNotIn(".tran", net)


if __name__ == "__main__":
    unittest.main()
