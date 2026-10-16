import unittest

from transportation_guide.providers import (
    AddressNotFound,
    NoRouteFound,
    Place,
    RouteOption,
    ServiceUnavailable,
)
from transportation_guide.recommend import recommend

ORIGIN = Place("현재 위치", 37.0, 127.0)


class FakeProvider:
    def __init__(self, durations=None, places=None, unavailable=False, failing=()):
        self.durations = durations if durations is not None else {"walk": 1800, "bike": 600, "car": 900}
        self.places = places if places is not None else {"시청": Place("시청", 37.5, 127.1)}
        self.unavailable = unavailable
        self.failing = set(failing)

    def geocode(self, address):
        if self.unavailable:
            raise ServiceUnavailable()
        if address not in self.places:
            raise AddressNotFound(address)
        return self.places[address]

    def route(self, origin, destination, mode):
        if self.unavailable:
            raise ServiceUnavailable()
        if mode in self.failing:
            raise ServiceUnavailable()
        if mode not in self.durations:
            raise NoRouteFound(mode)
        return RouteOption(mode, self.durations[mode], 1000, mode + " 경로")


class RecommendTest(unittest.TestCase):
    def test_sorted_by_duration_with_fastest_first(self):
        options = recommend(FakeProvider(), "시청", origin=ORIGIN).routes
        self.assertEqual([o.mode for o in options], ["bike", "car", "walk"])
        self.assertEqual([o.fastest for o in options], [True, False, False])

    def test_partial_routes_return_remaining(self):
        result = recommend(FakeProvider({"walk": 100}), "시청", origin=ORIGIN)
        options = result.routes
        self.assertEqual([o.mode for o in options], ["walk"])
        self.assertTrue(options[0].fastest)
        self.assertEqual([u.mode for u in result.unavailable], ["bike", "car"])
        self.assertTrue(all(u.reason for u in result.unavailable))

    def test_one_service_failure_keeps_other_routes(self):
        result = recommend(FakeProvider(failing={"car"}), "시청", origin=ORIGIN)
        self.assertEqual([o.mode for o in result.routes], ["bike", "walk"])
        self.assertEqual([u.mode for u in result.unavailable], ["car"])
        self.assertIn("다시 시도", result.unavailable[0].reason)

    def test_all_modes_service_failure_is_service_unavailable(self):
        with self.assertRaises(ServiceUnavailable):
            recommend(FakeProvider(failing={"walk", "bike", "car"}), "시청", origin=ORIGIN)

    def test_mixed_failures_without_routes_is_service_unavailable(self):
        with self.assertRaises(ServiceUnavailable):
            recommend(FakeProvider({}, failing={"car"}), "시청", origin=ORIGIN)

    def test_no_route_for_any_mode(self):
        with self.assertRaises(NoRouteFound):
            recommend(FakeProvider({}), "시청", origin=ORIGIN)

    def test_destination_not_found(self):
        with self.assertRaises(AddressNotFound):
            recommend(FakeProvider(), "없는곳", origin=ORIGIN)

    def test_origin_address_is_geocoded(self):
        provider = FakeProvider(places={"시청": Place("시청", 1, 2), "역": Place("역", 3, 4)})
        self.assertTrue(recommend(provider, "시청", origin_address="역").routes)
        with self.assertRaises(AddressNotFound):
            recommend(provider, "시청", origin_address="모름")

    def test_empty_inputs_are_invalid(self):
        with self.assertRaises(ValueError):
            recommend(FakeProvider(), "  ", origin=ORIGIN)
        with self.assertRaises(ValueError):
            recommend(FakeProvider(), "시청")

    def test_service_unavailable_propagates(self):
        with self.assertRaises(ServiceUnavailable):
            recommend(FakeProvider(unavailable=True), "시청", origin=ORIGIN)


if __name__ == "__main__":
    unittest.main()
