"""주소 변환과 경로 조회 인터페이스. 외부 서비스 호출은 이 모듈 안에만 둔다.

실제 서비스 어댑터는 후속 범위다. 지금 기본 provider는 서비스가 설정되지 않았음을 알린다.
API key 같은 secret은 코드에 적지 않는다.
"""

from dataclasses import dataclass
from typing import Protocol

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


class UnconfiguredProvider:
    """외부 서비스가 설정되지 않은 기본 provider."""

    def geocode(self, address: str) -> Place:
        raise ServiceUnavailable("경로 서비스가 아직 설정되지 않았습니다.")

    def route(self, origin: Place, destination: Place, mode: str) -> RouteOption:
        raise ServiceUnavailable("경로 서비스가 아직 설정되지 않았습니다.")
