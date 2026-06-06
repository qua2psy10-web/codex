import unittest
from pathlib import Path


class WebAssetsTests(unittest.TestCase):
    def test_index_has_parapet_fields_and_pdf_action(self):
        html = Path('web/index.html').read_text(encoding='utf-8')
        self.assertIn('重力式パラペット', html)
        self.assertIn('parapet_height_m', html)
        self.assertIn('front_batter_hv', html)
        self.assertIn('back_batter_hv', html)
        self.assertIn('計算書PDFを作成', html)
        self.assertIn('stability.js', html)

    def test_root_index_redirects_to_web_app(self):
        html = Path('index.html').read_text(encoding='utf-8')
        self.assertIn('url=web/index.html', html)
        self.assertIn('href="web/index.html"', html)
        self.assertIn('href="parapet_design_app.html"', html)

    def test_standalone_app_exists(self):
        html = Path('parapet_design_app.html').read_text(encoding='utf-8')
        self.assertIn('重力式パラペット', html)
        self.assertIn('function calculateParapet', html)
        self.assertNotIn('src="stability.js"', html)

    def test_script_has_parapet_calculation_features(self):
        js = Path('web/stability.js').read_text(encoding='utf-8')
        self.assertIn('calculateParapet', js)
        self.assertIn('trialWedgeActiveCoefficient', js)
        self.assertIn('localStorage', js)
        self.assertIn('window.print', js)
        self.assertIn('detailedReport', js)
        self.assertIn('計算式・照査過程', js)
        self.assertIn('signature-grid', js)
        self.assertIn('揚圧力', js)


if __name__ == '__main__':
    unittest.main()
