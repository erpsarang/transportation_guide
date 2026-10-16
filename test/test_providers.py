import io
import json
import unittest
import urllib.error
import urllib.parse

from transportation_guide.providers import (
    AddressNotFound,
    NoRouteFound,
    OsmProvider,
    Place,
    ServiceUnavailable,
    TIMEOUT_SECONDS,
    USER_AGENT,
)

ORIGIN = Place("출발", 37.5, 126.9)
DESTINATION = Place("도착", 37.6, 127.0)

CITY_HALL = [
    {
        "lat": "37.5667893",
        "lon": "126.9784204",
        "display_name": "서울특별시청",
    }
]


def osrm(duration, distance, summary=""):
    return {
        "code": "Ok",
        "routes": [
            {"duration": duration, "distance": distance, "legs": [{"summary": summary, "steps": []}]}
        ],
    }


class FakeResponse:
    def __init__(self, payload):
        self.body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeOpener:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return FakeResponse(item)


def make_provider(*responses):
    opener = FakeOpener(*responses)
    sleeps = []
    provider = OsmProvider(opener=opener, clock=lambda: 100.0, sleep=sleeps.append)
    return provider, opener, sleeps


class GeocodeTest(unittest.TestCase):
    def test_lat_lon_strings_become_floats_and_name_is_display_name(self):
        provider, _, _ = make_provider(CITY_HALL)
        place = provider.geocode("서울특별시 중구 세종대로 110")
        self.assertEqual(place, Place("서울특별시청", 37.5667893, 126.9784204))

    def test_request_parameters_user_agent_and_timeout(self):
        provider, opener, _ = make_provider(CITY_HALL)
        provider.geocode("서울특별시 중구 세종대로 110")
        request, timeout = opener.requests[0]
        url = urllib.parse.urlparse(request.full_url)
        self.assertEqual(url.netloc, "nominatim.openstreetmap.org")
        query = urllib.parse.parse_qs(url.query)
        self.assertEqual(query["q"], ["서울특별시 중구 세종대로 110"])
        self.assertEqual(query["format"], ["jsonv2"])
        self.assertEqual(query["limit"], ["1"])
        self.assertEqual(query["accept-language"], ["ko"])
        self.assertEqual(request.get_header("User-agent"), USER_AGENT)
        self.assertEqual(USER_AGENT, "transportation_guide/0.1")
        self.assertEqual(timeout, TIMEOUT_SECONDS)

    def test_empty_array_is_address_not_found(self):
        provider, _, _ = make_provider([])
        with self.assertRaises(AddressNotFound):
            provider.geocode("없는곳")

    def test_network_error_is_service_unavailable(self):
        provider, _, _ = make_provider(urllib.error.URLError("down"))
        with self.assertRaises(ServiceUnavailable):
            provider.geocode("시청")

    def test_timeout_is_service_unavailable(self):
        provider, _, _ = make_provider(TimeoutError())
        with self.assertRaises(ServiceUnavailable):
            provider.geocode("시청")

    def test_invalid_json_is_service_unavailable(self):
        provider, _, _ = make_provider(b"<html>")
        with self.assertRaises(ServiceUnavailable):
            provider.geocode("시청")

    def test_unexpected_shape_is_service_unavailable(self):
        provider, _, _ = make_provider([{"display_name": "이름만"}])
        with self.assertRaises(ServiceUnavailable):
            provider.geocode("시청")

    def test_second_geocode_waits_one_second(self):
        provider, _, sleeps = make_provider(CITY_HALL, CITY_HALL)
        provider.geocode("하나")
        self.assertEqual(sleeps, [])
        provider.geocode("둘")
        self.assertEqual(sleeps, [1.0])


class RouteTest(unittest.TestCase):
    def test_coordinates_are_longitude_first_and_overview_false(self):
        provider, opener, _ = make_provider(osrm(10, 20))
        provider.route(ORIGIN, DESTINATION, "walk")
        request, timeout = opener.requests[0]
        self.assertEqual(
            request.full_url,
            "https://routing.openstreetmap.de/routed-foot/route/v1/driving/"
            "126.9,37.5;127.0,37.6?overview=false",
        )
        self.assertEqual(request.get_header("User-agent"), USER_AGENT)
        self.assertEqual(timeout, TIMEOUT_SECONDS)

    def test_service_name_per_mode(self):
        provider, opener, _ = make_provider(osrm(10, 20), osrm(10, 20))
        provider.route(ORIGIN, DESTINATION, "bike")
        provider.route(ORIGIN, DESTINATION, "car")
        self.assertIn("/routed-bike/", opener.requests[0][0].full_url)
        self.assertIn("/routed-car/", opener.requests[1][0].full_url)

    def test_seconds_and_meters_are_rounded(self):
        provider, _, _ = make_provider(osrm(1389.8, 1735), osrm(587.8, 1697.8), osrm(260, 3076))
        walk = provider.route(ORIGIN, DESTINATION, "walk")
        bike = provider.route(ORIGIN, DESTINATION, "bike")
        car = provider.route(ORIGIN, DESTINATION, "car")
        self.assertEqual((walk.duration_seconds, walk.distance_meters), (1390, 1735))
        self.assertEqual((bike.duration_seconds, bike.distance_meters), (588, 1698))
        self.assertEqual((car.duration_seconds, car.distance_meters), (260, 3076))
        self.assertIsInstance(walk.duration_seconds, int)

    def test_empty_summary_becomes_sentence(self):
        provider, _, _ = make_provider(osrm(587.8, 1697.8))
        option = provider.route(ORIGIN, DESTINATION, "bike")
        self.assertEqual(option.summary, "약 10분, 1.7km")

    def test_road_name_summary_is_used(self):
        provider, _, _ = make_provider(osrm(300, 900, "세종대로"))
        self.assertEqual(provider.route(ORIGIN, DESTINATION, "car").summary, "세종대로")

    def test_code_not_ok_is_no_route(self):
        provider, _, _ = make_provider({"code": "NoRoute", "routes": []})
        with self.assertRaises(NoRouteFound):
            provider.route(ORIGIN, DESTINATION, "walk")

    def test_client_error_with_code_body_is_no_route(self):
        body = io.BytesIO(json.dumps({"code": "NoRoute"}).encode("utf-8"))
        error = urllib.error.HTTPError("http://x", 400, "Bad Request", None, body)
        provider, _, _ = make_provider(error)
        with self.assertRaises(NoRouteFound):
            provider.route(ORIGIN, DESTINATION, "walk")

    def test_server_error_is_service_unavailable(self):
        error = urllib.error.HTTPError("http://x", 500, "Error", None, io.BytesIO(b"oops"))
        provider, _, _ = make_provider(error)
        with self.assertRaises(ServiceUnavailable):
            provider.route(ORIGIN, DESTINATION, "walk")

    def test_network_error_is_service_unavailable(self):
        provider, _, _ = make_provider(urllib.error.URLError("down"))
        with self.assertRaises(ServiceUnavailable):
            provider.route(ORIGIN, DESTINATION, "walk")

    def test_missing_duration_is_service_unavailable(self):
        provider, _, _ = make_provider({"code": "Ok", "routes": [{"distance": 1}]})
        with self.assertRaises(ServiceUnavailable):
            provider.route(ORIGIN, DESTINATION, "walk")


if __name__ == "__main__":
    unittest.main()
