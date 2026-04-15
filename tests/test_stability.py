import unittest

from stability import (
    CircularSlipInput,
    SlopeInput,
    calculate_fellenius_fs,
    calculate_infinite_slope_fs,
)


class StabilityTests(unittest.TestCase):
    def test_stable_case_infinite(self):
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
        self.assertEqual(result.method, 'infinite_slope')

    def test_unstable_case_infinite(self):
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

    def test_fellenius_water_reduces_fs(self):
        dry = calculate_fellenius_fs(
            CircularSlipInput(
                slope_height_m=12,
                slope_angle_deg=35,
                cohesion_kpa=12,
                friction_angle_deg=30,
                unit_weight_kn_m3=18,
                groundwater_ratio=0.0,
                slices=16,
                search_steps=30,
            )
        )
        wet = calculate_fellenius_fs(
            CircularSlipInput(
                slope_height_m=12,
                slope_angle_deg=35,
                cohesion_kpa=12,
                friction_angle_deg=30,
                unit_weight_kn_m3=18,
                groundwater_ratio=0.8,
                slices=16,
                search_steps=30,
            )
        )
        self.assertEqual(dry.method, 'fellenius')
        self.assertGreater(dry.factor_of_safety, wet.factor_of_safety)

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

        with self.assertRaises(ValueError):
            calculate_fellenius_fs(
                CircularSlipInput(
                    slope_height_m=12,
                    slope_angle_deg=30,
                    cohesion_kpa=10,
                    friction_angle_deg=30,
                    unit_weight_kn_m3=18,
                    groundwater_ratio=0.2,
                    slices=6,
                    search_steps=30,
                )
            )


if __name__ == '__main__':
    unittest.main()
