# transportation_guide

목적지 주소를 입력하면, 지금 내가 있는 곳에서 가장 빨리 도착하는 이동 경로와 이동 수단을 추천해 주는 웹 도구다. 만든 사람이 직접 쓴다.

이 저장소는 [AI Development Framework](https://github.com/erpsarang/self-improvement-mvp)로 개발한다. 요구는 `[업무 요구]` Issue로 적는다.

## 도메인

- 사용자: 이 도구를 만든 본인. 처음 가는 곳을 찾아갈 때 쓴다.
- 입력: 목적지 주소 하나. 출발지는 브라우저가 알려 주는 현재 위치다.
- 결과: 이동 수단별 경로. 각 결과에 수단, 예상 소요 시간, 거리, 경로 요약이 있고 가장 빠른 것이 맨 위에 온다.
- 1단계의 이동 수단은 도보·자전거·자동차다. 대중교통은 API key가 필요해 다음 단계에서 다룬다.

## 기술 선택

- **Python 3, 표준 라이브러리만 쓴다.** `pip install`로 받는 외부 패키지를 쓰지 않는다. Framework의 검증·구현 실행 환경에는 Node만 설치되고 Python 패키지를 설치하는 단계가 없기 때문이다.
- 웹 서버는 표준 라이브러리 `http.server`, 화면은 정적 HTML과 JavaScript 한 벌이다.
- 외부 경로·주소 서비스는 한 모듈에 가두고, 테스트는 그 모듈을 가짜로 바꿔 **외부 서비스를 실제로 호출하지 않는다.**
- API key 같은 secret을 저장소에 기록하지 않는다.

## 구성

```text
src/transportation_guide/   런타임 코드
test/                       자동 테스트 (unittest, 파일 이름은 test_*.py)
package.json                Framework가 호출하는 검증 명령의 진입점 (아래)
```

루트 `package.json`의 `devDependencies`는 Framework의 Node 실행 환경을 위한 것이며 이 도구의 코드와 무관하다.

## 검증 명령

Framework는 검증 명령으로 `npm test`와 `npm run build`만 허용한다. 이 저장소에서 두 명령은 Python을 호출한다.

```text
npm test        PYTHONPATH=src python3 -m unittest discover -s test -v
npm run build   python3 -m compileall -q src
```

## 실행

```text
PYTHONPATH=src python3 -m transportation_guide.server
```

브라우저에서 `http://127.0.0.1:8000` 을 연다.

- 목적지 주소를 입력하고 검색하면 도보·자전거·자동차 경로가 소요 시간이 짧은 순서로 나오고, 가장 빠른 것에 "가장 빠름"이 표시된다. 각 결과에 수단, 예상 소요 시간, 거리, 경로 요약이 보인다.
- 출발지는 브라우저의 현재 위치다. 위치 허용을 거부하거나 오류가 나면 그 이유가 화면에 나오고, 출발지 주소를 직접 입력할 수 있다.
- 주소를 찾지 못하거나 경로가 없거나 외부 서비스가 응답하지 않으면 이유와 다시 시도하라는 안내가 나온다.
- API는 `POST /api/recommend` (JSON: `destination`, `lat`/`lon` 또는 `origin_address`)이며 `GET /api/recommend` 쿼리도 받는다.

### 사용하는 외부 서비스

둘 다 API key나 가입이 필요 없는 공개 서비스이며, 호출은 `providers.py` 안에만 있다.

- 주소 → 좌표: [OpenStreetMap Nominatim](https://nominatim.openstreetmap.org). 요청에 User-Agent `transportation_guide/0.1` 을 붙이고, 초당 1회를 넘겨 호출하지 않는다(주소 변환이 두 번이면 1초 이상 간격을 둔다).
- 경로 조회: FOSSGIS가 운영하는 OSRM(`routing.openstreetmap.de`). 도보 `routed-foot`, 자전거 `routed-bike`, 자동차 `routed-car`.
- 서버는 외부 서비스를 10초까지 기다리고, 화면은 서버를 60초까지 기다린다. 일부 수단만 실패하면 나머지 결과와 함께 빠진 수단의 이유를 보여 준다.

### 후속 범위

- 주소 변환·경로 서비스는 연결되어 있다. 캐시, 로그인, 검색 기록은 없다.
- 대중교통, 지도 표시는 다음 요구에서 다룬다.

테스트(`npm test`)는 가짜 provider를 쓰므로 외부 서비스를 호출하지 않는다.
