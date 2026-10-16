"""http.server로 정적 화면과 JSON API를 제공한다."""

import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .providers import (
    AddressNotFound,
    NoRouteFound,
    Place,
    Provider,
    ServiceUnavailable,
    UnconfiguredProvider,
)
from .recommend import recommend

STATIC_DIR = Path(__file__).parent / "static"
MAX_BODY_BYTES = 16 * 1024


def _parse_origin(params: dict) -> Place | None:
    lat, lon = params.get("lat"), params.get("lon")
    if lat in (None, "") and lon in (None, ""):
        return None
    try:
        lat_value, lon_value = float(lat), float(lon)
    except (TypeError, ValueError):
        raise ValueError("현재 위치 좌표가 올바르지 않습니다.")
    if not (-90 <= lat_value <= 90 and -180 <= lon_value <= 180):
        raise ValueError("현재 위치 좌표가 올바르지 않습니다.")
    return Place("현재 위치", lat_value, lon_value)


def handle_recommend(provider: Provider, params: dict) -> tuple[int, dict]:
    """요청 값으로 추천을 만들고 (상태 코드, JSON 본문)을 돌려준다."""
    try:
        destination = params.get("destination")
        if destination is not None and not isinstance(destination, str):
            raise ValueError("목적지 주소를 입력해 주세요.")
        origin_address = params.get("origin_address")
        if origin_address is not None and not isinstance(origin_address, str):
            raise ValueError("출발지 주소가 올바르지 않습니다.")
        options = recommend(
            provider,
            destination or "",
            origin=_parse_origin(params),
            origin_address=origin_address,
        )
        return 200, {"routes": [asdict(option) for option in options]}
    except ValueError as error:
        return 400, {"error": "invalid_input", "message": str(error)}
    except AddressNotFound:
        return 404, {
            "error": "address_not_found",
            "message": "입력한 주소를 찾지 못했습니다. 주소를 다시 확인해 주세요.",
        }
    except NoRouteFound:
        return 422, {
            "error": "no_route",
            "message": "갈 수 있는 경로가 없습니다. 다른 목적지를 입력해 보세요.",
        }
    except ServiceUnavailable:
        return 503, {
            "error": "service_unavailable",
            "message": "경로 서비스가 응답하지 않습니다. 잠시 후 다시 시도해 주세요.",
        }
    except Exception:
        return 500, {
            "error": "internal",
            "message": "알 수 없는 오류가 발생했습니다. 다시 시도해 주세요.",
        }


def make_handler(provider: Provider):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(status, body, "application/json; charset=utf-8")

        def do_GET(self) -> None:
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                try:
                    body = (STATIC_DIR / "index.html").read_bytes()
                except OSError:
                    self._send_json(500, {"error": "internal", "message": "화면 파일을 읽지 못했습니다."})
                    return
                self._send(200, body, "text/html; charset=utf-8")
            elif url.path == "/api/recommend":
                query = {key: values[0] for key, values in parse_qs(url.query).items()}
                self._send_json(*handle_recommend(provider, query))
            else:
                self._send_json(404, {"error": "not_found", "message": "찾을 수 없는 주소입니다."})

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/api/recommend":
                self._send_json(404, {"error": "not_found", "message": "찾을 수 없는 주소입니다."})
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
                if length > MAX_BODY_BYTES:
                    raise ValueError("요청이 너무 큽니다.")
                params = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(params, dict):
                    raise ValueError("요청 형식이 올바르지 않습니다.")
            except (ValueError, UnicodeDecodeError):
                self._send_json(400, {"error": "invalid_input", "message": "요청 형식이 올바르지 않습니다."})
                return
            self._send_json(*handle_recommend(provider, params))

        def log_message(self, format: str, *args) -> None:
            pass

    return Handler


def make_server(provider: Provider | None = None, host: str = "127.0.0.1", port: int = 8000):
    """provider를 주입할 수 있는 서버를 만든다. 생략하면 서비스 미설정 provider를 쓴다."""
    return ThreadingHTTPServer((host, port), make_handler(provider or UnconfiguredProvider()))


def main() -> None:
    server = make_server()
    print("http://127.0.0.1:8000 에서 실행 중입니다. 종료는 Ctrl+C.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
