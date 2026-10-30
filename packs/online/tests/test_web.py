"""Offline tests for the safe calculator and unit conversion."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from halweb import tools


class WebTest(unittest.TestCase):
    def test_calculator(self):
        self.assertEqual(tools.calculate("17*23+sqrt(16)")["result"], 395.0)
        self.assertEqual(tools.calculate("15% of 80")["result"], 12.0)
        self.assertEqual(tools.calculate("2^10")["result"], 1024)

    def test_calculator_refuses_code(self):
        for bad in ("__import__('os')", "open('x')", "(lambda: 1)()", "9**99999"):
            with self.assertRaises((ValueError, SyntaxError)):
                tools.calculate(bad)

    def test_calculator_refuses_huge_factorial(self):
        for bad in ("factorial(1001)", "factorial(100000)", "factorial(999)"):
            with self.assertRaises(ValueError, msg=bad):
                tools.calculate(bad)
        self.assertEqual(tools.calculate("factorial(20)")["result"], 2432902008176640000)

    def test_calculator_refuses_results_above_ten_to_the_thousandth(self):
        for bad in ("10**1001", "(10**900)**900", "10**600 * 10**600", "9**1000 * 9**1000"):
            with self.assertRaises(ValueError, msg=bad):
                tools.calculate(bad)
        self.assertEqual(tools.calculate("10**1000")["result"], 10**1000)

    def test_units_and_temperature(self):
        self.assertAlmostEqual(tools.convert(10, "miles", "km")["result"], 16.09344)
        self.assertAlmostEqual(tools.convert(100, "C", "F")["result"], 212.0)
        self.assertAlmostEqual(tools.convert(2, "stone", "kg")["result"], 12.700586)
        with self.assertRaises(ValueError):
            tools.convert(1, "kg", "km")


if __name__ == "__main__":
    unittest.main()
