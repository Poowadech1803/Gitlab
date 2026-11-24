"""Unit tests for inline SVG plots drawn from real ngspice data points."""

import unittest
import xml.etree.ElementTree as ET

from plots import bode_svg, waveform_svg


BODE_POINTS = [
    {"freq_hz": 1000.0, "gain_db": 20.0, "phase_deg": -170.0},
    {"freq_hz": 10000.0, "gain_db": 14.0, "phase_deg": -175.0},
]

TRAN_POINTS = [
    {"time_s": 0.0, "vin_v": 1.0, "vout_v": -2.0},
    {"time_s": 0.001, "vin_v": 0.0, "vout_v": 0.0},
    {"time_s": 0.002, "vin_v": -1.0, "vout_v": 2.0},
]


def _texts(svg):
    """Exact visible text nodes, so a title cannot satisfy a legend assertion."""
    root = ET.fromstring(svg)
    return ["".join(node.itertext()) for node in root.iter()
            if node.tag.endswith("text")]


def _series(svg):
    """Plotted coordinate lists in document order: gain/vin, then phase/vout."""
    root = ET.fromstring(svg)
    series = []
    for node in root.iter():
        if not node.tag.endswith("polyline"):
            continue
        coordinates = []
        for pair in node.get("points", "").split():
            x, y = pair.split(",")
            coordinates.append((float(x), float(y)))
        series.append(coordinates)
    return series


class TestBodeSvg(unittest.TestCase):
    """The AC plot must expose units, real polylines and independent scales."""

    def test_bode_svg_has_units_and_data_points(self):
        svg = bode_svg([{"freq_hz": 1000, "gain_db": 20, "phase_deg": -170},
                        {"freq_hz": 10000, "gain_db": 14, "phase_deg": -175}])
        self.assertIn("<svg", svg)
        self.assertIn("Frequency (Hz)", svg)
        self.assertIn("Gain (dB)", svg)
        self.assertIn("Phase (°)", svg)
        self.assertIn("<polyline", svg)

    def test_bode_frequency_axis_is_logarithmic(self):
        # A decade in frequency must occupy the same x distance each time;
        # a linear axis would put the second decade ten times further out.
        points = [
            {"freq_hz": freq, "gain_db": 10.0, "phase_deg": -10.0}
            for freq in (10.0, 100.0, 1000.0)
        ]
        xs = [x for x, _ in _series(bode_svg(points))[0]]
        self.assertAlmostEqual(xs[1] - xs[0], xs[2] - xs[1], places=6)

    def test_bode_gain_and_phase_use_independent_scales(self):
        gains = [10.0, 20.0, 30.0]
        base = [
            {"freq_hz": freq, "gain_db": gain, "phase_deg": phase}
            for freq, gain, phase in zip((100.0, 1000.0, 10000.0),
                                         gains, (-10.0, -20.0, -30.0))
        ]
        changed = [{**point, "phase_deg": -45.0 if phase == -30.0 else phase}
                   for point, phase in zip(base, (-10.0, -20.0, -30.0))]
        before, after = _series(bode_svg(base)), _series(bode_svg(changed))
        self.assertEqual(before[0], after[0])  # gain coordinates untouched
        self.assertNotEqual(before[1], after[1])
        self.assertIn("-45", _texts(bode_svg(changed)))

    def test_bode_tick_labels_use_real_min_and_max(self):
        texts = _texts(bode_svg(BODE_POINTS))
        for label in ("1000", "10000", "20", "14", "-170", "-175"):
            with self.subTest(label=label):
                self.assertIn(label, texts)


class TestWaveformSvg(unittest.TestCase):
    """The transient plot must show both series on a shared, ms-based grid."""

    def test_waveform_svg_uses_both_series(self):
        svg = waveform_svg(TRAN_POINTS)
        series = _series(svg)
        self.assertEqual(len(series), 2)
        self.assertNotEqual(series[0], series[1])
        self.assertIn("Time (ms)", svg)
        self.assertIn("Vin, Vout (V)", svg)
        texts = _texts(svg)
        self.assertIn("Vin", texts)
        self.assertIn("Vout", texts)

    def test_waveform_time_ticks_are_in_milliseconds(self):
        points = [
            {"time_s": time_s, "vin_v": 0.0, "vout_v": 0.0}
            for time_s in (0.0, 0.001, 0.002)
        ]
        texts = _texts(waveform_svg(points))
        self.assertIn("Time (ms)", texts)
        for label in ("0", "1", "2"):
            with self.subTest(label=label):
                self.assertIn(label, texts)

    def test_waveform_series_share_one_voltage_axis(self):
        # With a shared 0..4 V scale, 1 V must sit higher than 2 V at the
        # same instant; separately normalised series would both be centred.
        points = [
            {"time_s": 0.0, "vin_v": 0.0, "vout_v": 0.0},
            {"time_s": 0.001, "vin_v": 1.0, "vout_v": 2.0},
            {"time_s": 0.002, "vin_v": 2.0, "vout_v": 4.0},
        ]
        vin, vout = _series(waveform_svg(points))
        self.assertGreater(vin[1][1], vout[1][1])  # larger voltage sits higher
        for label in ("0", "4"):
            with self.subTest(label=label):
                self.assertIn(label, _texts(waveform_svg(points)))


class TestPlotEdges(unittest.TestCase):
    """Empty input, single samples and data mutations must behave safely."""

    def test_empty_points_no_svg(self):
        for function in (bode_svg, waveform_svg):
            for empty in (None, []):
                with self.subTest(function=function.__name__, empty=empty):
                    self.assertEqual(function(empty), "")

    def test_single_point_is_centered_in_plot_area(self):
        # Growing the canvas by 100 px in width and 50 px in height moves a
        # lone sample by half of each increase: it stays at the area centre.
        cases = (
            (bode_svg, [{"freq_hz": 1000.0, "gain_db": 20.0,
                         "phase_deg": -170.0}]),
            (waveform_svg, [{"time_s": 0.001, "vin_v": 1.0,
                             "vout_v": 1.0}]),  # equal voltages: centred y
        )
        for function, one_point in cases:
            with self.subTest(function=function.__name__):
                small = _series(function(one_point, width=720, height=280))[0][0]
                large = _series(function(one_point, width=920, height=380))[0][0]
                self.assertAlmostEqual(large[0] - small[0], 100.0, places=6)
                self.assertAlmostEqual(large[1] - small[1], 50.0, places=6)

    def test_coordinates_track_changed_real_points(self):
        # Three samples make the middle gain change alter the shape instead of
        # merely rescaling the same two-point line.
        bode = [{"freq_hz": freq, "gain_db": gain, "phase_deg": -170.0}
                for freq, gain in ((100.0, 10.0), (1000.0, 20.0), (10000.0, 30.0))]
        changed_bode = [dict(point) for point in bode]
        changed_bode[1]["gain_db"] = 5.0
        before, after = _series(bode_svg(bode)), _series(bode_svg(changed_bode))
        self.assertEqual(before[1], after[1])  # unchanged phase series
        self.assertNotEqual(before[0], after[0])

        changed_tran = [dict(point) for point in TRAN_POINTS]
        changed_tran[2]["vout_v"] = 9.0
        before, after = _series(waveform_svg(TRAN_POINTS)), _series(waveform_svg(changed_tran))
        # Time samples do not move; the changed output must move its polyline.
        self.assertEqual([x for x, _ in before[1]], [x for x, _ in after[1]])
        self.assertNotEqual(before[1], after[1])

    def test_svg_is_well_formed_and_self_contained(self):
        for svg in (bode_svg(BODE_POINTS), waveform_svg(TRAN_POINTS)):
            root = ET.fromstring(svg)
            self.assertTrue(root.tag.endswith("svg"))
            # ElementTree folds the namespace declaration out of .attrib,
            # so verify the emitted markup directly.
            self.assertIn('xmlns="http://www.w3.org/2000/svg"', svg)
            self.assertEqual(root.get("viewBox"), "0 0 720 280")
            self.assertNotIn("nan", svg.lower())
            self.assertNotIn("inf", svg.lower())


if __name__ == "__main__":
    unittest.main()
