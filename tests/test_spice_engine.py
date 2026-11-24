"""Unit tests for simulation form validation and ngspice discovery."""

import math
import os
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest import mock

from spice_engine import (
    SimInput, SpiceError, build_netlist, find_ngspice, parse_sim_form,
    run_analysis,
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


DC_SIM = parse_sim_form(VALID_FORM)
AC_SIM = parse_sim_form({**VALID_FORM, "analysis": "ac"})
TRAN_SIM = parse_sim_form({**VALID_FORM, "analysis": "tran"})


def _ngspice_available() -> bool:
    """Skip-safe availability probe: find_ngspice() itself can raise."""
    try:
        find_ngspice()
    except SpiceError:
        return False
    return True


FAKE_LOG_OP = (
    "v(b) = 1.900000e+00\n"
    "v(e) = 1.200000e+00\n"
    "v(c) = 9.300000e+00\n"
)

FAKE_LOG_AC = (
    "Index freq vdb(in) vdb(out) vp(in) vp(out)\n"
    "0 1.000000e+01 2.000000e+01 2.000000e+01 0.000000e+00 -1.000000e+01\n"
    "1 1.000000e+02 2.000000e+01 4.500000e+01 0.000000e+00 -2.000000e+01\n"
    "2 1.000000e+03 2.000000e+01 5.000000e+01 0.000000e+00 -3.000000e+01\n"
    "3 1.000000e+04 2.000000e+01 4.500000e+01 0.000000e+00 -2.000000e+01\n"
)

FAKE_LOG_AC_MISSING_LOW = (
    "Index freq vdb(in) vdb(out) vp(in) vp(out)\n"
    "0 1.000000e+01 2.000000e+01 4.850000e+01 0.000000e+00 -1.000000e+01\n"
    "1 1.000000e+02 2.000000e+01 4.800000e+01 0.000000e+00 -2.000000e+01\n"
    "2 1.000000e+03 2.000000e+01 5.000000e+01 0.000000e+00 -3.000000e+01\n"
    "3 1.000000e+04 2.000000e+01 4.500000e+01 0.000000e+00 -2.000000e+01\n"
)

TRAN_VIN = [1.0, 0.0, -1.0, 0.0, 1.0]


def _tran_log(vout):
    """Build a tabular .print tran log with hand-chosen vin/vout samples."""
    lines = ["Index time v(in) v(out)"]
    for index, (vin, out) in enumerate(zip(TRAN_VIN, vout)):
        lines.append(
            f"{index} {index * 1e-4:.6e} {vin:.6e} {out:.6e}"
        )
    return "\n".join(lines) + "\n"


RAW_DC_ASCII = (
    b"Title: CE DC\n"
    b"Plotname: Operating Point\n"
    b"Flags: real\n"
    b"No. Variables: 4\n"
    b"No. Points: 1\n"
    b"Variables:\n"
    b"\t0\tv(b)\tvoltage\n"
    b"\t1\tv(e)\tvoltage\n"
    b"\t2\tv(c)\tvoltage\n"
    b"\t3\ti(rc)\tdevice_current\n"
    b"Values:\n"
    b"\t0\t1.900000e+00, 1.200000e+00, 9.300000e+00, -1.500000e-03\n"
)

RAW_DC_BINARY = (
    b"Title: CE DC\n"
    b"Plotname: Operating Point\n"
    b"Flags: real\n"
    b"No. Variables: 4\n"
    b"No. Points: 1\n"
    b"Variables:\n"
    b"\t0\tv(b)\tvoltage\n"
    b"\t1\tv(e)\tvoltage\n"
    b"\t2\tv(c)\tvoltage\n"
    b"\t3\ti(rc)\tdevice_current\n"
    b"Binary:\n"
    + b"\x00" + struct.pack("<4d", 1.9, 1.2, 9.3, -1.5e-3)
)

# Captured banner shape from a real -r run: no .print table is emitted, but
# the raw-file path contains digits that must not become transient data rows.
REAL_TRAN_LOG_BANNER_ONLY = (
    "Note: No compatibility mode selected!\n"
    "Circuit: * ce amplifier - local documented q1_npn model\n"
    'binary raw file "C:\\Users\\B6807092\\AppData\\Local\\Temp\\tmp6c9q2v8l\\ngspice.raw"\n'
    "No. of Data Rows : 2008\n"
)

# Captured from ngspice 47-1: real raw files have no pad byte after "Binary:"
# and expose voltage-source branch currents, not i(rc).
RAW_DC_REAL_NO_PAD = (
    b"Title: * ce amplifier - local documented q1_npn model\n"
    b"Date: Tue Nov 24 17:53:04  2026\n"
    b"Command: ngspice-47, Build Mon Sep  7 15:41:53 UTC 2026\n"
    b"Plotname: Operating Point\n"
    b"Flags: real\n"
    b"No. Variables: 8\n"
    b"No. Points: 1       \n"
    b"Variables:\n"
    b"\t0\tv(vcc)\tvoltage\n"
    b"\t1\tv(in)\tvoltage\n"
    b"\t2\tv(b)\tvoltage\n"
    b"\t3\tv(c)\tvoltage\n"
    b"\t4\tv(e)\tvoltage\n"
    b"\t5\tv(out)\tvoltage\n"
    b"\t6\ti(vin)\tcurrent\n"
    b"\t7\ti(vcc)\tcurrent\n"
    b"Binary:\n"
    + struct.pack(
        "<8d",
        12.0, 0.0, 2.0036744962966377, 9.087216255157696,
        1.3328797437738196, 0.0, 0.0, -0.0014239558663289907,
    )
)

RAW_TRAN_MULTIPOINT_ASCII = (
    b"Title: CE TRAN\n"
    b"Plotname: Transient Analysis\n"
    b"Flags: real\n"
    b"No. Variables: 4\n"
    b"No. Points: 3\n"
    b"Variables:\n"
    b"\t0\ttime\ttime\n"
    b"\t1\tv(in)\tvoltage\n"
    b"\t2\tv(out)\tvoltage\n"
    b"\t3\ti(vcc)\tdevice_current\n"
    b"Values:\n"
    b"\t0\t0.000000e+00, 1.000000e+00, -2.000000e+00, -1.000000e-03\n"
    b"\t1\t1.000000e-04, 0.000000e+00, 0.000000e+00, -2.000000e-03\n"
    b"\t2\t2.000000e-04, -1.000000e+00, 2.000000e+00, -3.000000e-03\n"
)

RAW_AC_COMPLEX_BINARY = (
    b"Title: CE AC\n"
    b"Plotname: AC Analysis\n"
    b"Flags: complex\n"
    b"No. Variables: 3\n"
    b"No. Points: 2\n"
    b"Variables:\n"
    b"\t0\tfrequency\tfrequency\n"
    b"\t1\tv(in)\tvoltage\n"
    b"\t2\tv(out)\tvoltage\n"
    b"Binary:\n"
    + b"\x00" + struct.pack(
        "<12d",
        100.0, 0.0, 1.0, 0.0, 2.0, 0.0,
        1000.0, 0.0, 1.0, 0.0, 0.0, -4.0,
    )
)

RAW_AC_NO_FREQ_ASCII = (
    b"Title: CE AC\n"
    b"Plotname: AC Analysis\n"
    b"Flags: real\n"
    b"No. Variables: 4\n"
    b"No. Points: 2\n"
    b"Variables:\n"
    b"\t0\tvdb(in)\tvoltage\n"
    b"\t1\tvdb(out)\tvoltage\n"
    b"\t2\tvp(in)\tvoltage\n"
    b"\t3\tvp(out)\tvoltage\n"
    b"Values:\n"
    b"\t0\t2.000000e+01, 4.000000e+01, 0.000000e+00, -2.000000e+01\n"
    b"\t1\t2.000000e+01, 5.000000e+01, 0.000000e+00, -3.000000e+01\n"
)

# Real AC binary raw files carry uninitialised imaginary parts in the
# frequency column; only the real part is meaningful (observed 47-1 output).
RAW_AC_REAL_COMPLEX_GARBAGE_FREQ_IMAG = (
    b"Title: CE AC\n"
    b"Plotname: AC Analysis\n"
    b"Flags: complex\n"
    b"No. Variables: 3\n"
    b"No. Points: 2\n"
    b"Variables:\n"
    b"\t0\tfrequency\tfrequency\tgrid=3\n"
    b"\t1\tv(in)\tvoltage\n"
    b"\t2\tv(out)\tvoltage\n"
    b"Binary:\n"
    + struct.pack(
        "<12d",
        1.0, 2.5640290219155525e262, 0.01, 0.0, 0.0076352, 0.0,
        10.0, 9.53378641872868e172, 0.01, 0.0, 0.0173492, 0.0,
    )
)

RAW_AC_COMPLEX_NO_VOUT_BINARY = (
    b"Title: CE AC\n"
    b"Plotname: AC Analysis\n"
    b"Flags: complex\n"
    b"No. Variables: 2\n"
    b"No. Points: 1\n"
    b"Variables:\n"
    b"\t0\tfrequency\tfrequency\n"
    b"\t1\tv(in)\tvoltage\n"
    b"Binary:\n"
    + b"\x00" + struct.pack("<4d", 1000.0, 0.0, 1.0, 0.0)
)


def _fake_run(*, stdout="", stderr="", returncode=0, log_text=None, raw_bytes=None):
    """Stand in for the ngspice process, optionally writing its -o/-r files."""
    def fake(cmd, **kwargs):
        for flag, payload in (("-o", log_text), ("-r", raw_bytes)):
            if payload is None:
                continue
            path = Path(cmd[cmd.index(flag) + 1])
            if isinstance(payload, bytes):
                path.write_bytes(payload)
            else:
                path.write_text(payload, encoding="utf-8")
        return CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)

    return fake


class TestRunAnalysis(unittest.TestCase):
    """A7-A9: runner output, real-log parsing and all failure paths."""

    def test_run_analysis_op_parses_fake_log(self):
        with mock.patch("spice_engine.subprocess.run",
                        return_value=CompletedProcess([], 0, stdout=FAKE_LOG_OP)):
            out = run_analysis(DC_SIM, exe="fake-ngspice")
        self.assertEqual(out["status"], "success")
        self.assertEqual(out["analysis"], "dc")
        self.assertEqual(out["engine"], "ngspice")
        self.assertEqual(out["version"], "47-1 (MSYS2 package, upstream ngspice 47)")
        self.assertEqual(out["model"], "Q1_NPN (local documented 2N3904-style model)")
        self.assertAlmostEqual(out["data"]["vb"], 1.9)
        self.assertAlmostEqual(out["data"]["ve"], 1.2)
        self.assertAlmostEqual(out["data"]["vc"], 9.3)
        self.assertAlmostEqual(out["data"]["vce"], 8.1)
        self.assertAlmostEqual(out["data"]["ic_ma"], 1.227272727, places=5)
        self.assertEqual(len(out["warnings"]), 1)
        self.assertIn("RC", out["warnings"][0])
        self.assertEqual(out["summary"], {})
        self.assertIn("v(b) = 1.900000e+00", out["log_excerpt"])

    def test_run_analysis_prefers_i_rc_when_present(self):
        log = FAKE_LOG_OP + "i(rc) = -1.500000e-03\ni(vcc) = -1.600000e-03\n"
        with mock.patch("spice_engine.subprocess.run",
                        return_value=CompletedProcess([], 0, stdout=log)):
            out = run_analysis(DC_SIM, exe="fake-ngspice")
        self.assertAlmostEqual(out["data"]["ic_ma"], 1.5)
        self.assertEqual(out["warnings"], [])

    def test_run_analysis_falls_back_to_i_vcc(self):
        log = FAKE_LOG_OP + "i(vcc) = -2.500000e-03\n"
        with mock.patch("spice_engine.subprocess.run",
                        return_value=CompletedProcess([], 0, stdout=log)):
            out = run_analysis(DC_SIM, exe="fake-ngspice")
        self.assertAlmostEqual(out["data"]["ic_ma"], 2.5)
        self.assertEqual(len(out["warnings"]), 1)
        self.assertIn("i(vcc)", out["warnings"][0])

    def test_run_analysis_raises_on_nonzero(self):
        failed = CompletedProcess([], 1, stdout=FAKE_LOG_OP, stderr="simulation aborted")
        with mock.patch("spice_engine.subprocess.run", return_value=failed):
            with self.assertRaises(SpiceError) as cm:
                run_analysis(DC_SIM, exe="fake-ngspice")
        self.assertIn("simulation aborted", str(cm.exception))
        self.assertIn("v(b) = 1.900000e+00", str(cm.exception))

    def test_empty_log_no_stale_result(self):
        good = CompletedProcess([], 0, stdout=FAKE_LOG_OP)
        empty = CompletedProcess([], 0, stdout="")
        with mock.patch("spice_engine.subprocess.run", return_value=good):
            first = run_analysis(DC_SIM, exe="fake-ngspice")
        self.assertEqual(first["status"], "success")
        with mock.patch("spice_engine.subprocess.run", return_value=empty):
            with self.assertRaises(SpiceError) as cm:
                run_analysis(DC_SIM, exe="fake-ngspice")
        self.assertIn("dc", str(cm.exception))

    def test_missing_exe(self):
        with tempfile.TemporaryDirectory() as root:
            missing = str(Path(root) / "missing" / "ngspice.exe")
            with mock.patch("spice_engine.subprocess.run",
                            side_effect=AssertionError("should not start a process")):
                with self.assertRaises(SpiceError) as cm:
                    run_analysis(DC_SIM, exe=missing)
            self.assertIn(missing, str(cm.exception))

    def test_timeout_raises(self):
        timeout = subprocess.TimeoutExpired("ngspice", 0.25, output=FAKE_LOG_OP)
        with mock.patch("spice_engine.subprocess.run", side_effect=timeout):
            with self.assertRaises(SpiceError) as cm:
                run_analysis(DC_SIM, exe="fake-ngspice", timeout=0.25)
        self.assertIn("timed out", str(cm.exception))
        self.assertIn("v(b) = 1.900000e+00", str(cm.exception))

    def test_ac_log_parses_rows(self):
        with mock.patch("spice_engine.subprocess.run",
                        side_effect=_fake_run(log_text=FAKE_LOG_AC)):
            out = run_analysis(AC_SIM, exe="fake-ngspice")
        self.assertEqual(out["status"], "success")
        self.assertEqual(len(out["data"]), 4)
        self.assertAlmostEqual(out["data"][0]["freq_hz"], 10.0)
        self.assertAlmostEqual(out["data"][2]["gain_db"], 30.0)
        self.assertAlmostEqual(out["data"][2]["phase_deg"], -30.0)
        self.assertAlmostEqual(out["summary"]["midband_gain_db"], 30.0)
        self.assertAlmostEqual(out["summary"]["f_low_hz"], 100.0)
        self.assertAlmostEqual(out["summary"]["f_high_hz"], 10000.0)
        self.assertEqual(out["warnings"], [])

    def test_ac_missing_cutoff_says_not_determined(self):
        with mock.patch("spice_engine.subprocess.run",
                        side_effect=_fake_run(log_text=FAKE_LOG_AC_MISSING_LOW)):
            out = run_analysis(AC_SIM, exe="fake-ngspice")
        self.assertIsNone(out["summary"]["f_low_hz"])
        self.assertAlmostEqual(out["summary"]["f_high_hz"], 10000.0)
        self.assertEqual(len(out["warnings"]), 1)
        self.assertIn("not determined in sweep range", out["warnings"][0])

    def test_tran_log_parses_rows(self):
        log = _tran_log([-2.0, 0.0, 2.0, 0.0, -2.0])
        with mock.patch("spice_engine.subprocess.run",
                        side_effect=_fake_run(log_text=log)):
            out = run_analysis(TRAN_SIM, exe="fake-ngspice")
        self.assertEqual(out["status"], "success")
        self.assertEqual(len(out["data"]), 5)
        self.assertAlmostEqual(out["data"][0]["time_s"], 0.0)
        self.assertAlmostEqual(out["data"][0]["vin_v"], 1.0)
        self.assertAlmostEqual(out["data"][0]["vout_v"], -2.0)
        self.assertAlmostEqual(out["data"][4]["time_s"], 4e-4)
        self.assertAlmostEqual(out["data"][4]["vout_v"], -2.0)
        self.assertEqual(out["summary"]["phase_relation"], "inverted")

    def test_tran_summary_uses_correlation_for_phase_relation(self):
        cases = (
            ([2.0, 0.0, -2.0, 0.0, 2.0], "in-phase"),
            ([0.0, 1.0, 0.0, -1.0, 0.0], "unclear"),
        )
        for vout, expected in cases:
            with self.subTest(expected=expected):
                with mock.patch("spice_engine.subprocess.run",
                                side_effect=_fake_run(log_text=_tran_log(vout))):
                    out = run_analysis(TRAN_SIM, exe="fake-ngspice")
                self.assertEqual(out["summary"]["phase_relation"], expected)

    def test_run_analysis_falls_back_to_ascii_raw(self):
        with mock.patch("spice_engine.subprocess.run",
                        side_effect=_fake_run(raw_bytes=RAW_DC_ASCII)):
            out = run_analysis(DC_SIM, exe="fake-ngspice")
        self.assertEqual(out["status"], "success")
        self.assertAlmostEqual(out["data"]["vb"], 1.9)
        self.assertAlmostEqual(out["data"]["vc"], 9.3)
        self.assertAlmostEqual(out["data"]["ic_ma"], 1.5)

    def test_run_analysis_falls_back_to_binary_raw(self):
        with mock.patch("spice_engine.subprocess.run",
                        side_effect=_fake_run(raw_bytes=RAW_DC_BINARY)):
            out = run_analysis(DC_SIM, exe="fake-ngspice")
        self.assertEqual(out["status"], "success")
        self.assertAlmostEqual(out["data"]["ve"], 1.2)
        self.assertAlmostEqual(out["data"]["vce"], 8.1)
        self.assertAlmostEqual(out["data"]["ic_ma"], 1.5)


    def test_multipoint_ascii_raw_maps_columns_per_point(self):
        with mock.patch("spice_engine.subprocess.run",
                        side_effect=_fake_run(raw_bytes=RAW_TRAN_MULTIPOINT_ASCII)):
            out = run_analysis(TRAN_SIM, exe="fake-ngspice")
        self.assertEqual(out["status"], "success")
        self.assertEqual(len(out["data"]), 3)
        self.assertAlmostEqual(out["data"][0]["time_s"], 0.0)
        self.assertAlmostEqual(out["data"][0]["vin_v"], 1.0)
        self.assertAlmostEqual(out["data"][0]["vout_v"], -2.0)
        self.assertAlmostEqual(out["data"][1]["time_s"], 1e-4)
        self.assertAlmostEqual(out["data"][1]["vin_v"], 0.0)
        self.assertAlmostEqual(out["data"][2]["time_s"], 2e-4)
        self.assertAlmostEqual(out["data"][2]["vin_v"], -1.0)
        self.assertAlmostEqual(out["data"][2]["vout_v"], 2.0)
        self.assertEqual(out["summary"]["phase_relation"], "inverted")

    def test_ac_raw_without_frequency_does_not_invent_frequencies(self):
        with mock.patch("spice_engine.subprocess.run",
                        side_effect=_fake_run(raw_bytes=RAW_AC_NO_FREQ_ASCII)):
            with self.assertRaises(SpiceError) as cm:
                run_analysis(AC_SIM, exe="fake-ngspice")
        self.assertIn("frequency", str(cm.exception))
        self.assertNotIn("index", str(cm.exception).lower())

    def test_complex_ac_raw_derives_gain_and_phase(self):
        with mock.patch("spice_engine.subprocess.run",
                        side_effect=_fake_run(raw_bytes=RAW_AC_COMPLEX_BINARY)):
            out = run_analysis(AC_SIM, exe="fake-ngspice")
        self.assertEqual(out["status"], "success")
        self.assertEqual(len(out["data"]), 2)
        self.assertAlmostEqual(out["data"][0]["freq_hz"], 100.0)
        self.assertAlmostEqual(out["data"][0]["gain_db"], 6.0206, places=3)
        self.assertAlmostEqual(out["data"][0]["phase_deg"], 0.0)
        self.assertAlmostEqual(out["data"][1]["freq_hz"], 1000.0)
        self.assertAlmostEqual(out["data"][1]["gain_db"], 12.0412, places=3)
        self.assertAlmostEqual(out["data"][1]["phase_deg"], -90.0)
        self.assertAlmostEqual(out["summary"]["midband_gain_db"], 12.0412, places=3)
        self.assertAlmostEqual(out["summary"]["f_low_hz"], 100.0)
        self.assertIsNone(out["summary"]["f_high_hz"])

    def test_complex_ac_raw_without_vout_fails(self):
        raw = RAW_AC_COMPLEX_NO_VOUT_BINARY
        with mock.patch("spice_engine.subprocess.run",
                        side_effect=_fake_run(raw_bytes=raw)):
            with self.assertRaises(SpiceError) as cm:
                run_analysis(AC_SIM, exe="fake-ngspice")
        self.assertIn("v(out)", str(cm.exception))

    def test_process_launch_oserror_becomes_spice_error(self):
        failure = FileNotFoundError("launch failed: missing dll")
        with mock.patch("spice_engine.subprocess.run", side_effect=failure):
            with self.assertRaises(SpiceError) as cm:
                run_analysis(DC_SIM, exe="fake-ngspice")
        self.assertIn("fake-ngspice", str(cm.exception))
        self.assertIn("launch failed: missing dll", str(cm.exception))

    def test_timeout_error_includes_stderr_and_log(self):
        def timeout_with_log(cmd, **kwargs):
            log = Path(cmd[cmd.index("-o") + 1])
            log.write_text("log diagnostic before timeout\n", encoding="utf-8")
            raise subprocess.TimeoutExpired(
                cmd, 0.25, output="partial stdout", stderr="partial stderr"
            )

        with mock.patch("spice_engine.subprocess.run", side_effect=timeout_with_log):
            with self.assertRaises(SpiceError) as cm:
                run_analysis(DC_SIM, exe="fake-ngspice", timeout=0.25)
        message = str(cm.exception)
        self.assertIn("partial stdout", message)
        self.assertIn("partial stderr", message)
        self.assertIn("log diagnostic before timeout", message)

    def test_relative_exe_path_is_resolved_before_run(self):
        def absolute_exe_writes_log(cmd, **kwargs):
            if Path(cmd[0]).is_absolute():
                log = Path(cmd[cmd.index("-o") + 1])
                log.write_text(FAKE_LOG_OP, encoding="utf-8")
            return CompletedProcess(cmd, 0, stdout="")

        with tempfile.TemporaryDirectory() as root:
            exe = Path(root) / "ngspice.exe"
            exe.write_text("not really an executable", encoding="utf-8")
            relative_exe = os.path.relpath(str(exe), str(Path.cwd()))
            self.assertFalse(Path(relative_exe).is_absolute())
            with mock.patch("spice_engine.subprocess.run",
                            side_effect=absolute_exe_writes_log):
                out = run_analysis(DC_SIM, exe=relative_exe)
        self.assertEqual(out["status"], "success")
        self.assertAlmostEqual(out["data"]["vce"], 8.1)


class TestRealNgspice(unittest.TestCase):
    """A10-A12: real ngspice output, skipped when no simulator is installed."""

    def test_real_binary_raw_without_pad_byte_parses(self):
        with mock.patch("spice_engine.subprocess.run",
                        side_effect=_fake_run(raw_bytes=RAW_DC_REAL_NO_PAD)):
            out = run_analysis(DC_SIM, exe="fake-ngspice")
        self.assertEqual(out["status"], "success")
        self.assertAlmostEqual(out["data"]["vb"], 2.0036745, places=5)
        self.assertAlmostEqual(out["data"]["ve"], 1.3328797, places=5)
        self.assertAlmostEqual(out["data"]["vc"], 9.0872163, places=5)
        self.assertAlmostEqual(out["data"]["vce"], 7.7543365, places=5)
        self.assertAlmostEqual(out["data"]["ic_ma"], 1.4239559, places=5)

    def test_real_complex_raw_ignores_garbage_frequency_imaginary_part(self):
        with mock.patch("spice_engine.subprocess.run",
                        side_effect=_fake_run(
                            raw_bytes=RAW_AC_REAL_COMPLEX_GARBAGE_FREQ_IMAG)):
            out = run_analysis(AC_SIM, exe="fake-ngspice")
        self.assertEqual(out["status"], "success")
        self.assertEqual(len(out["data"]), 2)
        self.assertAlmostEqual(out["data"][0]["freq_hz"], 1.0)
        self.assertAlmostEqual(out["data"][1]["freq_hz"], 10.0)
        self.assertAlmostEqual(out["data"][1]["gain_db"], 4.8, places=1)

    def test_real_log_banner_numbers_are_not_transient_rows(self):
        with mock.patch("spice_engine.subprocess.run",
                        side_effect=_fake_run(log_text=REAL_TRAN_LOG_BANNER_ONLY)):
            with self.assertRaises(SpiceError) as cm:
                run_analysis(TRAN_SIM, exe="fake-ngspice")
        self.assertIn("no parseable tran output", str(cm.exception))

    @unittest.skipUnless(_ngspice_available(), "ngspice not installed")
    def test_real_ngspice_dc_op_returns_physical_values(self):
        out = run_analysis(DC_SIM)
        self.assertEqual(out["status"], "success")
        data = out["data"]
        self.assertGreater(data["vb"], 0.5)
        self.assertGreater(data["ve"], 0.0)
        self.assertGreater(data["vc"], 0.0)
        self.assertLess(data["vc"], DC_SIM.vcc)
        self.assertGreater(data["vce"], 0.5)
        self.assertAlmostEqual(data["vce"], data["vc"] - data["ve"], places=9)

    @unittest.skipUnless(_ngspice_available(), "ngspice not installed")
    def test_real_ngspice_dc_collector_current_uses_negative_supply_branch(self):
        out = run_analysis(DC_SIM)
        self.assertEqual(out["status"], "success")
        ic_ma = out["data"]["ic_ma"]
        self.assertGreater(ic_ma, 0.1)
        self.assertLess(ic_ma, 5.0)
        self.assertIn("i(vcc)", " ".join(out["warnings"]))

    @unittest.skipUnless(_ngspice_available(), "ngspice not installed")
    def test_real_ngspice_ac_sweep_has_distinct_frequency_points(self):
        out = run_analysis(AC_SIM)
        self.assertEqual(out["status"], "success")
        points = out["data"]
        self.assertGreater(len(points), 20)
        freqs = [point["freq_hz"] for point in points]
        self.assertEqual(len(set(freqs)), len(freqs))
        self.assertTrue(all(left < right for left, right in zip(freqs, freqs[1:])))
        self.assertAlmostEqual(freqs[0], 1.0, places=4)
        self.assertAlmostEqual(freqs[-1], 1e7, delta=1e5)
        self.assertTrue(all(
            math.isfinite(point["gain_db"]) and math.isfinite(point["phase_deg"])
            for point in points
        ))
        # A 10 mV drive produces a ~1.75 V/V midband output in this circuit.
        self.assertGreater(out["summary"]["midband_gain_db"], 1.0)
        self.assertLess(out["summary"]["midband_gain_db"], 20.0)

    @unittest.skipUnless(_ngspice_available(), "ngspice not installed")
    def test_real_ngspice_transient_has_multiple_time_points(self):
        out = run_analysis(TRAN_SIM)
        self.assertEqual(out["status"], "success")
        points = out["data"]
        self.assertGreater(len(points), 100)
        times = [point["time_s"] for point in points]
        self.assertAlmostEqual(times[0], 0.0)
        self.assertTrue(all(left < right for left, right in zip(times, times[1:])))
        self.assertGreater(times[-1], 0.0)
        self.assertTrue(all(
            math.isfinite(point["vin_v"]) and math.isfinite(point["vout_v"])
            for point in points
        ))
        self.assertEqual(out["summary"]["phase_relation"], "inverted")


if __name__ == "__main__":
    unittest.main()
