"""이동 수단별 경로를 조회해 빠른 순으로 추천한다."""

from dataclasses import replace

from .providers import MODES, NoRouteFound, Place, Provider, RouteOption


def recommend(
    provider: Provider,
    destination: str,
    origin: Place | None = None,
    origin_address: str | None = None,
) -> list[RouteOption]:
    """소요 시간 오름차순 경로 목록을 돌려주고 첫 항목에 fastest=True를 표시한다.

    입력이 잘못되면 ValueError, 주소가 없으면 AddressNotFound,
    모든 수단에 경로가 없으면 NoRouteFound, 서비스 장애면 ServiceUnavailable.
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
    for mode in MODES:
        try:
            options.append(provider.route(origin, target, mode))
        except NoRouteFound:
            continue
    if not options:
        raise NoRouteFound("갈 수 있는 경로가 없습니다.")

    options.sort(key=lambda option: option.duration_seconds)
    options[0] = replace(options[0], fastest=True)
    return options
