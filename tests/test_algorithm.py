import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from ezpost_ocr.algorithm import DigitRecognizer, load_image, preprocess_image

ROOT = Path(__file__).resolve().parents[1]


class AlgorithmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = DigitRecognizer(ROOT / 'models/ocr_model.npz')

    def test_renamed_image_preserves_leading_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'unrelated-name.jpg'
            path.write_bytes((ROOT / 'dataset/captcha_0158.jpg').read_bytes())
            self.assertEqual(self.model.recognize(path)['text'], '01493')

    def test_each_background_branch_recognizes_a_held_out_image(self):
        cases = [('0966', '30607', 'green_contrast'),
                 ('0845', '22734', 'red_green_difference'),
                 ('0848', '56412', 'gradient_corrected_difference')]
        for number, expected, mode in cases:
            with self.subTest(number=number):
                path = ROOT / f'dataset/captcha_{number}.jpg'
                self.assertEqual(preprocess_image(load_image(path))['mode'], mode)
                self.assertEqual(self.model.recognize(path)['text'], expected)

    def test_blank_wrong_size_and_corrupt_images_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'invalid.jpg'
            for shape in [(40, 100, 3), (39, 100, 3)]:
                cv2.imencode('.jpg', np.zeros(shape, np.uint8))[1].tofile(str(path))
                with self.assertRaises(ValueError):
                    self.model.recognize(path)
            path.write_bytes(b'not an image')
            with self.assertRaises(ValueError):
                self.model.recognize(path)


if __name__ == '__main__':
    unittest.main()
