import unittest

from stability import ParapetInput, calculate_parapet, section_vertices, trial_wedge_active_coefficient


class ParapetStabilityTests(unittest.TestCase):
    def test_sample_case_returns_required_checks(self):
        result = calculate_parapet(ParapetInput())
        names = [check.name for check in result.checks]

        self.assertEqual(names, ["転倒", "滑動", "偏心", "地盤支持力", "極限支持力", "コンクリート応力度"])
        self.assertGreater(result.self_weight_kn, 0)
        self.assertGreater(result.active_earth_pressure_kn, 0)
        self.assertGreater(result.ultimate_bearing_kpa, result.q_max_kpa)

    def test_seismic_case_increases_horizontal_action(self):
        normal = calculate_parapet(ParapetInput(load_case="常時"))
        seismic = calculate_parapet(ParapetInput(load_case="地震時", seismic_coefficient_h=0.2))

        self.assertEqual(normal.horizontal_seismic_kn, 0)
        self.assertGreater(seismic.horizontal_force_kn, normal.horizontal_force_kn)
        self.assertGreater(seismic.overturning_moment_knm, normal.overturning_moment_knm)

    def test_trial_wedge_coefficient_is_reasonable(self):
        ka = trial_wedge_active_coefficient(30)
        self.assertAlmostEqual(ka, 1 / 3, places=2)

    def test_section_geometry_uses_dimensions(self):
        inputs = ParapetInput(parapet_height_m=2, top_width_m=0.6, base_width_m=1.8, front_batter_hv=0.2, back_batter_hv=0.3)
        vertices = section_vertices(inputs)
        self.assertEqual(vertices[0], (0.0, 0.0))
        self.assertEqual(vertices[1], (1.8, 0.0))
        self.assertAlmostEqual(vertices[3][0], 0.4)
        self.assertAlmostEqual(vertices[2][0] - vertices[3][0], 0.6)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            calculate_parapet(ParapetInput(base_width_m=0.4, top_width_m=0.6))
        with self.assertRaises(ValueError):
            calculate_parapet(ParapetInput(friction_angle_deg=80))


if __name__ == '__main__':
    unittest.main()
