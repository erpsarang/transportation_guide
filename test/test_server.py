import json
import threading
import unittest
import urllib.error
import urllib.request

from transportation_guide.providers import (
    AddressNotFound,
    NoRouteFound,
    Place,
    RouteOption,
    ServiceUnavailable,
)
from transportation_guide.server import make_server


class FakeProvider:
    def geocode(self, address):
        if address == "장애":
            raise ServiceUnavailable()
        if address == "버그":
            raise RuntimeError("boom")
        if address not in ("시청", "역"):
            raise AddressNotFound(address)
        return Place(address, 37.5, 127.1)

    def route(self, origin, destination, mode):
        if destination.name == "역":
            raise NoRouteFound(mode)
        seconds = {"walk": 1800, "bike": 600, "car": 900}[mode]
        return RouteOption(mode, seconds, 2000, mode + " 경로")


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(FakeProvider(), port=0)
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def post(self, payload):
        request = urllib.request.Request(
            self.base + "/api/recommend",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        return self.send(request)

    def send(self, request):
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_index_html(self):
        with urllib.request.urlopen(self.base + "/") as response:
            self.assertEqual(response.status, 200)
            self.assertIn("text/html", response.headers["Content-Type"])
            self.assertIn("목적지 주소", response.read().decode("utf-8"))

    def test_recommend_with_coordinates(self):
        status, body = self.post({"destination": "시청", "lat": 37.0, "lon": 127.0})
        self.assertEqual(status, 200)
        self.assertEqual([r["mode"] for r in body["routes"]], ["bike", "car", "walk"])
        self.assertTrue(body["routes"][0]["fastest"])

    def test_recommend_with_origin_address_via_get(self):
        url = self.base + "/api/recommend?destination=%EC%8B%9C%EC%B2%AD&origin_address=%EC%97%AD"
        # 출발지 '역' 은 지오코딩되지만 목적지 '시청' 경로는 존재한다.
        status, body = self.send(urllib.request.Request(url))
        self.assertEqual(status, 200)
        self.assertEqual(len(body["routes"]), 3)

    def test_invalid_input(self):
        status, body = self.post({"destination": "", "lat": 1, "lon": 1})
        self.assertEqual(status, 400)
        self.assertTrue(body["message"])
        status, _ = self.post({"destination": "시청", "lat": "abc", "lon": 1})
        self.assertEqual(status, 400)
        status, _ = self.post({"destination": "시청"})
        self.assertEqual(status, 400)

    def test_address_not_found(self):
        status, body = self.post({"destination": "없는곳", "lat": 1, "lon": 1})
        self.assertEqual(status, 404)
        self.assertIn("주소", body["message"])

    def test_no_route(self):
        status, body = self.post({"destination": "역", "lat": 1, "lon": 1})
        self.assertEqual(status, 422)
        self.assertIn("경로", body["message"])

    def test_service_unavailable(self):
        status, body = self.post({"destination": "장애", "lat": 1, "lon": 1})
        self.assertEqual(status, 503)
        self.assertIn("다시 시도", body["message"])

    def test_unexpected_error_does_not_kill_server(self):
        status, _ = self.post({"destination": "버그", "lat": 1, "lon": 1})
        self.assertEqual(status, 500)
        status, _ = self.post({"destination": "시청", "lat": 1, "lon": 1})
        self.assertEqual(status, 200)

    def test_bad_json_body(self):
        request = urllib.request.Request(self.base + "/api/recommend", data=b"{not json")
        status, _ = self.send(request)
        self.assertEqual(status, 400)

    def test_unknown_path(self):
        status, _ = self.send(urllib.request.Request(self.base + "/nope"))
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
