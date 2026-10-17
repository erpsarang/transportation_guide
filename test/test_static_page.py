import unittest
from pathlib import Path

INDEX = Path(__file__).resolve().parent.parent / "src" / "transportation_guide" / "static" / "index.html"


class StaticPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX.read_text(encoding="utf-8")

    def test_busy_notices(self):
        self.assertIn("검색 중입니다", self.html)
        self.assertIn("서버를 깨우는 중입니다", self.html)

    def test_timeout_and_header(self):
        self.assertIn("90000", self.html)
        self.assertIn("X-Access-Code", self.html)

    def test_access_code_toggle_and_notice(self):
        self.assertIn("보기", self.html)
        self.assertIn('type="password"', self.html)
        self.assertIn("접근 코드에는 영문, 숫자, 기호만 쓸 수 있습니다. 키보드를 영문으로 바꿔 주세요", self.html)

    def test_unavailable_title_and_initial_hidden(self):
        self.assertIn("결과를 받지 못한 이동 수단", self.html)
        self.assertIn('id="unavailable-box" hidden', self.html)

    def test_unavailable_box_hidden_when_empty(self):
        self.assertIn("unavailableBox.hidden = items.length === 0;", self.html)

    def test_unavailable_box_hidden_on_submit(self):
        self.assertIn("unavailableBox.hidden = true;", self.html)


if __name__ == "__main__":
    unittest.main()
