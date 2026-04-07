import unittest
from pathlib import Path


class WebAssetsTests(unittest.TestCase):
    def test_index_has_required_fields(self):
        html = Path('web/index.html').read_text(encoding='utf-8')
        self.assertIn('slope_angle_deg', html)
        self.assertIn('cohesion_kpa', html)
        self.assertIn('stability.js', html)
        self.assertIn('Fellenius法', html)
        self.assertIn('search_steps', html)

    def test_script_has_two_methods(self):
        js = Path('web/stability.js').read_text(encoding='utf-8')
        self.assertIn('calculateInfiniteSlopeFS', js)
        self.assertIn('calculateFelleniusFS', js)
        self.assertIn('felleniusFSForCenter', js)


if __name__ == '__main__':
    unittest.main()
