import unittest
from pathlib import Path


class WebAssetsTests(unittest.TestCase):
    def test_index_has_required_fields(self):
        html = Path('web/index.html').read_text(encoding='utf-8')
        self.assertIn('slope_angle_deg', html)
        self.assertIn('cohesion_kpa', html)
        self.assertIn('stability.js', html)


if __name__ == '__main__':
    unittest.main()
