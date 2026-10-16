import unittest

import transportation_guide


class PackageTest(unittest.TestCase):
    def test_package_is_importable(self):
        self.assertTrue(transportation_guide.__version__)


if __name__ == "__main__":
    unittest.main()
