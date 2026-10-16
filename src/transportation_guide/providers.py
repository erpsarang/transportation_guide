"""주소 변환과 경로 조회. 외부 서비스 호출은 이 모듈 안에만 둔다.

주소 변환은 OpenStreetMap Nominatim, 경로 조회는 FOSSGIS OSRM을 쓴다. 둘 다 API key가 필요 없다.
API key 같은 secret은 코드에 적지 않는다.
"""

import http.client
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Protocol

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://routing.openstreetmap.de/{service}/route/v1/driving/{coordinates}?overview=false"
USER_AGENT = "transportation_guide/0.1"
TIMEOUT_SECONDS = 10
GEOCODE_INTERVAL_SECONDS = 1.0

WALK = "walk"
BIKE = "bike"
CAR = "car"
MODES = (WALK, BIKE, CAR)


class AddressNotFound(Exception):
    """입력한 주소를 찾지 못했다."""


class NoRouteFound(Exception):
    """갈 수 있는 경로가 없다."""


class ServiceUnavailable(Exception):
    """외부 서비스가 응답하지 않거나 설정되지 않았다."""


@dataclass(frozen=True)
class Place:
    name: str
    lat: float
    lon: float


@dataclass(frozen=True)
class RouteOption:
    mode: str
    duration_seconds: int
    distance_meters: int
    summary: str
    fastest: bool = False


class Provider(Protocol):
    def geocode(self, address: str) -> Place:
        """주소를 좌표로 바꾼다. 없으면 AddressNotFound, 장애면 ServiceUnavailable."""
        ...

    def route(self, origin: Place, destination: Place, mode: str) -> RouteOption:
        """경로를 조회한다. 없으면 NoRouteFound, 장애면 ServiceUnavailable."""
        ...


OSRM_SERVICES = {WALK: "routed-foot", BIKE: "routed-bike", CAR: "routed-car"}


def _describe(duration_seconds: int, distance_meters: int) -> str:
    minutes = max(1, round(duration_seconds / 60))
    if minutes < 60:
        time_text = "%d분" % minutes
    else:
        time_text = "%d시간 %d분" % (minutes // 60, minutes % 60)
    if distance_meters < 1000:
        distance_text = "%dm" % distance_meters
    else:
        distance_text = "%.1fkm" % (distance_meters / 1000)
    return "약 %s, %s" % (time_text, distance_text)


class OsmProvider:
    """Nominatim으로 주소를 좌표로 바꾸고 OSRM으로 경로를 조회한다.

    Nominatim은 초당 1회를 넘겨 호출할 수 없어 주소 변환 사이에 1초 간격을 둔다.
    """

    def __init__(self, opener=None, clock=time.monotonic, sleep=time.sleep):
        self._opener = opener or urllib.request.urlopen
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._last_geocode = None

    def _get_json(self, url: str):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with self._opener(request, timeout=TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            # OSRM은 경로가 없을 때 4xx와 함께 code가 담긴 JSON을 돌려줄 수 있다.
            if 400 <= error.code < 500:
                try:
                    data = json.loads(error.read().decode("utf-8"))
                except (OSError, ValueError):
                    data = None
                if isinstance(data, dict) and "code" in data:
                    return data
            raise ServiceUnavailable("외부 서비스가 오류를 돌려주었습니다.") from error
        except (OSError, http.client.HTTPException, ValueError) as error:
            raise ServiceUnavailable("외부 서비스가 응답하지 않습니다.") from error

    def _wait_turn(self) -> None:
        if self._last_geocode is None:
            return
        wait = GEOCODE_INTERVAL_SECONDS - (self._clock() - self._last_geocode)
        if wait > 0:
            self._sleep(wait)

    def geocode(self, address: str) -> Place:
        query = urllib.parse.urlencode(
            {"q": address, "format": "jsonv2", "limit": 1, "accept-language": "ko"}
        )
        with self._lock:
            self._wait_turn()
            try:
                data = self._get_json(NOMINATIM_URL + "?" + query)
            finally:
                self._last_geocode = self._clock()
        if not isinstance(data, list):
            raise ServiceUnavailable("주소 변환 응답 형식이 올바르지 않습니다.")
        if not data:
            raise AddressNotFound(address)
        try:
            item = data[0]
            return Place(str(item["display_name"]), float(item["lat"]), float(item["lon"]))
        except (KeyError, TypeError, ValueError) as error:
            raise ServiceUnavailable("주소 변환 응답 형식이 올바르지 않습니다.") from error

    def route(self, origin: Place, destination: Place, mode: str) -> RouteOption:
        service = OSRM_SERVICES.get(mode)
        if service is None:
            raise ValueError("지원하지 않는 이동 수단입니다.")
        # OSRM은 경도가 먼저다.
        coordinates = "%s,%s;%s,%s" % (origin.lon, origin.lat, destination.lon, destination.lat)
        data = self._get_json(OSRM_URL.format(service=service, coordinates=coordinates))
        if not isinstance(data, dict):
            raise ServiceUnavailable("경로 응답 형식이 올바르지 않습니다.")
        if data.get("code") != "Ok":
            raise NoRouteFound(mode)
        try:
            routes = data["routes"]
            if not routes:
                raise NoRouteFound(mode)
            first = routes[0]
            duration = int(round(float(first["duration"])))
            distance = int(round(float(first["distance"])))
            summary = ""
            legs = first.get("legs")
            if isinstance(legs, list) and legs and isinstance(legs[0], dict):
                name = legs[0].get("summary")
                if isinstance(name, str):
                    summary = name.strip()
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ServiceUnavailable("경로 응답 형식이 올바르지 않습니다.") from error
        return RouteOption(mode, duration, distance, summary or _describe(duration, distance))
