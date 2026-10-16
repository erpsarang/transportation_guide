"""이동 수단별 경로를 조회해 빠른 순으로 추천한다."""

from dataclasses import dataclass, replace

from .providers import MODES, NoRouteFound, Place, Provider, RouteOption, ServiceUnavailable


@dataclass(frozen=True)
class Unavailable:
    mode: str
    reason: str


@dataclass(frozen=True)
class RecommendResult:
    routes: list[RouteOption]
    unavailable: list[Unavailable]


def recommend(
    provider: Provider,
    destination: str,
    origin: Place | None = None,
    origin_address: str | None = None,
) -> RecommendResult:
    """소요 시간 오름차순 경로 목록(routes)과 빠진 수단(unavailable)을 돌려준다.

    routes 첫 항목에 fastest=True를 표시한다. 수단 하나가 실패해도 나머지는 그대로 돌려준다.
    입력이 잘못되면 ValueError, 주소가 없으면 AddressNotFound, 모든 수단이 실패했을 때
    서비스 장애가 하나라도 있으면 ServiceUnavailable, 아니면 NoRouteFound.
    """
    destination = (destination or "").strip()
    if not destination:
        raise ValueError("목적지 주소를 입력해 주세요.")

    if origin is None:
        address = (origin_address or "").strip()
        if not address:
            raise ValueError("출발지를 알 수 없습니다. 출발지 주소를 입력해 주세요.")
        origin = provider.geocode(address)
    target = provider.geocode(destination)

    options: list[RouteOption] = []
    unavailable: list[Unavailable] = []
    service_failed = False
    for mode in MODES:
        try:
            options.append(provider.route(origin, target, mode))
        except NoRouteFound:
            unavailable.append(Unavailable(mode, "갈 수 있는 경로가 없습니다."))
        except ServiceUnavailable:
            service_failed = True
            unavailable.append(Unavailable(mode, "경로 서비스가 응답하지 않습니다. 다시 시도해 주세요."))
    if not options:
        if service_failed:
            raise ServiceUnavailable("경로 서비스가 응답하지 않습니다.")
        raise NoRouteFound("갈 수 있는 경로가 없습니다.")

    options.sort(key=lambda option: option.duration_seconds)
    options[0] = replace(options[0], fastest=True)
    return RecommendResult(options, unavailable)
