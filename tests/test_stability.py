import unittest

from stability import SlopeInput, calculate_infinite_slope_fs


class StabilityTests(unittest.TestCase):
    def test_stable_case(self):
        result = calculate_infinite_slope_fs(
            SlopeInput(
                slope_angle_deg=30,
                cohesion_kpa=10,
                friction_angle_deg=32,
                unit_weight_kn_m3=18,
                failure_depth_m=3,
                groundwater_ratio=0.2,
            )
        )
        self.assertGreater(result.factor_of_safety, 1.2)
        self.assertTrue(result.is_stable)

    def test_unstable_case(self):
        result = calculate_infinite_slope_fs(
            SlopeInput(
                slope_angle_deg=45,
                cohesion_kpa=0,
                friction_angle_deg=20,
                unit_weight_kn_m3=19,
                failure_depth_m=3,
                groundwater_ratio=0.8,
            )
        )
        self.assertLess(result.factor_of_safety, 1.2)
        self.assertFalse(result.is_stable)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            calculate_infinite_slope_fs(
                SlopeInput(
                    slope_angle_deg=30,
                    cohesion_kpa=0,
                    friction_angle_deg=30,
                    unit_weight_kn_m3=18,
                    failure_depth_m=0,
                )
            )


if __name__ == '__main__':
    unittest.main()
