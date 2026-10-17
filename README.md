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

### 환경 변수

| 이름 | 설명 | 기본값 |
| --- | --- | --- |
| `HOST` | 서버가 열리는 주소 | `127.0.0.1` (내 컴퓨터에서만 열림) |
| `PORT` | 서버가 열리는 포트(0~65535 정수). 정수가 아니면 이유를 알리고 시작하지 않는다. | `8000` |
| `ACCESS_CODE` | 접근 코드. 설정하면 코드를 아는 사람만 `/api/recommend`를 쓸 수 있다. | 없음(코드 없이 사용) |

- 접근 코드는 환경 변수로만 받으며 저장소, 응답, 오류 안내, 서버 기록 어디에도 나오지 않는다.
- 코드가 설정되면 `/api/recommend`(GET, POST)는 `X-Access-Code` 헤더가 코드와 같을 때만 동작하고, 아니면 401 `unauthorized`를 돌려준다. 쿼리로는 코드를 받지 않는다. 화면(`/`)은 공개다.
- 화면은 401을 받으면 접근 코드 입력칸을 보여 준다. 입력칸의 "보기"를 고르면 입력한 글자가 보이고 다시 고르면 가려진다(처음엔 가려져 있다). 영문, 숫자, 기호 외의 글자(한글 등)가 있으면 서버에 보내기 전에 키보드를 영문으로 바꾸라고 안내한다.
- 코드가 맞아 결과가 나오면 입력칸은 사라지고, 코드는 그 브라우저(localStorage)가 기억한다. 틀리면 입력칸이 다시 나타나고 다시 입력하라고 안내한다.

- 목적지 주소를 입력하고 검색하면 도보·자전거·자동차 경로가 소요 시간이 짧은 순서로 나오고, 가장 빠른 것에 "가장 빠름"이 표시된다. 각 결과에 수단, 예상 소요 시간, 거리가 보인다. 서비스가 도로 이름을 줄 때만 경로 요약 줄이 따로 나온다.
- 검색 중에는 "검색 중입니다"가 보이고, 15초가 넘으면 "서버를 깨우는 중입니다. 최대 1분쯤 걸릴 수 있습니다"로 바뀌며 결과가 나오면 사라진다.
- 출발지는 브라우저의 현재 위치다. 위치 허용을 거부하거나 오류가 나면 그 이유가 화면에 나오고, 출발지 주소를 직접 입력할 수 있다.
- 주소를 찾지 못하거나 경로가 없거나 외부 서비스가 응답하지 않으면 이유와 다시 시도하라는 안내가 나온다.
- API는 `POST /api/recommend` (JSON: `destination`, `lat`/`lon` 또는 `origin_address`)이며 `GET /api/recommend` 쿼리도 받는다.

### 사용하는 외부 서비스

둘 다 API key나 가입이 필요 없는 공개 서비스이며, 호출은 `providers.py` 안에만 있다.

- 주소 → 좌표: [OpenStreetMap Nominatim](https://nominatim.openstreetmap.org). 요청에 User-Agent `transportation_guide/0.1` 을 붙이고, 초당 1회를 넘겨 호출하지 않는다(주소 변환이 두 번이면 1초 이상 간격을 둔다).
- 경로 조회: FOSSGIS가 운영하는 OSRM(`routing.openstreetmap.de`). 도보 `routed-foot`, 자전거 `routed-bike`, 자동차 `routed-car`.
- 서버는 외부 서비스를 10초까지 기다리고, 화면은 서버를 90초까지 기다린다(무료 호스팅이 잠에서 깨는 시간을 견디기 위해서다). 일부 수단만 실패하면 나머지 결과와 함께 빠진 수단의 이유를 보여 준다.

### Render에 올리기

휴대폰 브라우저에서 링크 하나로 쓰려면 [Render](https://render.com)의 무료 Web Service에 올린다. 계정을 만들고 올리는 일은 사람이 직접 하며, 이 저장소에는 Render 설정 파일이나 컨테이너 정의가 없다. 아래 항목은 Render 화면에서 넣는다(화면의 항목 이름은 배포 시 직접 확인한다).

1. Render에서 새 Web Service를 만들고 이 GitHub 저장소를 연결한다. 요금제는 Free를 고른다.
2. 런타임은 Python으로 두고, 설치할 외부 패키지가 없으므로 빌드 명령은 `echo ok`로 넣는다.
3. 시작 명령(Start Command)은 다음과 같이 넣는다.

   ```text
   PYTHONPATH=src python3 -m transportation_guide.server
   ```

4. 환경 변수를 넣는다.
   - `HOST` = `0.0.0.0` (Render는 모든 주소에서 열려야 한다. `PORT`는 Render가 알려 주므로 넣지 않는다.)
   - `ACCESS_CODE` = 비슷하게 보이는 글자(i, l, o, 0, 1)를 뺀 영문 소문자와 숫자로 된 무작위 16자. 링크를 아는 아무나 이 서버를 거쳐 외부 서비스를 호출하지 못하게 하는 코드다. 내 컴퓨터에서 아래 중 하나로 만들어 붙여 넣고, 저장소에는 적지 않는다.

     Windows PowerShell:

     ```text
     $c='abcdefghjkmnpqrstuvwxyz23456789'; $b=New-Object byte[] 16; (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($b); -join ($b | ForEach-Object { $c[$_ % 31] })
     ```

     Python이 있는 환경:

     ```text
     python3 -c "import secrets; a='abcdefghjkmnpqrstuvwxyz23456789'; print(''.join(secrets.choice(a) for _ in range(16)))"
     ```

     기호와 대문자는 사진이나 손으로 옮겨 적기 어려워 쓰지 않으며, 16자 무작위 값이면 이렇게 해도 추측되지 않는다.
   - `PYTHON_VERSION` = 3.12 계열(예: `3.12.8`). 이 저장소의 자동 검증이 Python 3.12이고 Render의 기본 파이썬 버전은 더 높아서, 맞추지 않으면 검증하지 않은 버전에서 돌게 된다.
5. 배포가 끝나면 Render가 주는 `https://` 주소를 휴대폰에서 열고, 처음 한 번 접근 코드를 입력한다.

알아 둘 점:

- 무료 서비스는 한동안 접속이 없으면 잠든다. 잠든 상태에서 링크를 처음 열면 안내 화면 없이 페이지가 열릴 때까지 기다려야 한다. 이미 열려 있는 화면에서 검색할 때만 "서버를 깨우는 중입니다" 안내가 보인다. 깨우는 시간은 서비스 문서가 30~60초라고 안내하지만 더 짧을 수 있다.
- 휴대폰에서 현재 위치를 쓰려면 보안 연결(https)이 필요하며, 이는 Render가 제공하는 것을 쓴다. 위치를 얻지 못하면 이유가 나오고 출발지 주소를 직접 입력할 수 있다.

### 후속 범위

- 주소 변환·경로 서비스는 연결되어 있다. 캐시, 로그인, 검색 기록은 없다.
- 대중교통, 지도 표시는 다음 요구에서 다룬다.

테스트(`npm test`)는 가짜 provider를 쓰므로 외부 서비스를 호출하지 않는다.
