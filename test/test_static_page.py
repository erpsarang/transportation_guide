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

    def test_map_uses_osm_tiles_without_external_library(self):
        self.assertIn("https://tile.openstreetmap.org/{z}/{x}/{y}.png", self.html)
        self.assertNotIn("leaflet", self.html.lower())
        self.assertNotIn("<script src", self.html)

    def test_map_attribution_is_always_in_markup(self):
        self.assertIn("© OpenStreetMap contributors", self.html)
        self.assertIn('id="map-box" hidden', self.html)

    def test_map_failure_notices_and_isolation(self):
        self.assertIn("지도 이미지를 불러오지 못했습니다", self.html)
        self.assertIn("지도를 표시하지 못했습니다", self.html)
        self.assertIn("img.onerror", self.html)
        self.assertLess(self.html.index("render(result.data.routes, result.data);"), self.html.index("showMap(result.data);"))

    def test_map_reset_on_submit_and_selection(self):
        self.assertIn("clearMap();", self.html)
        self.assertIn("selectMode(route.mode)", self.html)
        self.assertIn("찾은 목적지", self.html)

    def test_recent_destinations_markup(self):
        self.assertIn('id="recent-box" hidden', self.html)
        self.assertIn("최근 목적지", self.html)
        self.assertIn('id="recent-clear"', self.html)
        self.assertIn("지우기", self.html)
        self.assertLess(self.html.index('id="destination"'), self.html.index('id="recent-box"'))

    def test_recent_destinations_storage(self):
        self.assertIn('"transportation_guide_recent_destinations"', self.html)
        self.assertIn("var RECENT_MAX = 10;", self.html)
        self.assertIn("slice(0, RECENT_MAX)", self.html)
        self.assertIn("Array.isArray(parsed)", self.html)
        self.assertIn('typeof value === "string"', self.html)
        self.assertIn("try { localStorage.setItem(RECENT_KEY", self.html)
        self.assertIn("try { localStorage.removeItem(RECENT_KEY)", self.html)
        self.assertIn("try {\n      var parsed = JSON.parse(localStorage.getItem(RECENT_KEY)", self.html)

    def test_recent_destinations_saved_only_on_success(self):
        render_at = self.html.index("render(result.data.routes, result.data);")
        save_at = self.html.index("saveRecent(requestedDestination);")
        self.assertLess(render_at, save_at)
        self.assertLess(save_at, self.html.index("showMap(result.data);"))
        self.assertLess(self.html.index("showError(\"표시할 경로가 없습니다"), save_at)
        self.assertEqual(self.html.count("saveRecent(requestedDestination)"), 1)

    def test_kakao_directions_link(self):
        start = self.html.index("function kakaoDirectionsUrl")
        body = self.html[start:self.html.index("function render(", start)]
        self.assertIn("https://map.kakao.com/link/by/", body)
        self.assertIn('bike: "bicycle"', self.html)
        self.assertIn("encodeURIComponent", self.html)
        self.assertIn("현재 위치", body)
        self.assertIn("return null;", body)
        self.assertNotIn("traffic", self.html)
        self.assertNotIn("kakaomap://", self.html)
        self.assertNotIn("access", body.lower())
        self.assertNotIn("storedCode", body)

    def test_kakao_link_markup_and_event_isolation(self):
        self.assertIn("카카오맵에서 길안내", self.html)
        self.assertIn('link.target = "_blank";', self.html)
        self.assertIn('link.rel = "noopener";', self.html)
        self.assertEqual(self.html.count("event.stopPropagation();"), 2)
        self.assertIn("function render(routes, data)", self.html)

    def test_recent_destination_pick_does_not_submit(self):
        self.assertIn("destinationInput.value = text;", self.html)
        self.assertIn("button.textContent = text;", self.html)
        self.assertNotIn("requestSubmit", self.html)
        self.assertNotIn(".submit()", self.html)


if __name__ == "__main__":
    unittest.main()
