# ETF Factsheet — 패시브 ETF 비교 사이트

한국 상장 / 미국 상장 패시브 ETF를 지수별로 비교하는 정적 사이트입니다.

> 저장소 이름: **etf-factsheet** — GitHub Pages 배포 시 `https://<계정>.github.io/etf-factsheet/`로 접속됩니다.

## 파일 구성

```
index.html                       ← 사이트 본체 (데이터는 여기 FUNDS 배열에 정적으로 들어있음)
data.json                        ← 가격·순자산·환율 "실시간" 값 (매일 자동 갱신됨)
scripts/update_data.py           ← funetf.co.kr에서 가격·순자산을, Frankfurter API에서 환율을 긁어와 data.json을 갱신하는 스크립트
scripts/requirements.txt         ← 스크립트 의존성 (Playwright)
.github/workflows/update-data.yml← 매일 1회 자동으로 스크립트를 실행하는 GitHub Actions
```

## 데이터 관리 방식

- **정적 정보** (티커, 운용사, 총보수, 상장일, 장단점, 배당 등): `index.html`의 `FUNDS` 배열에 직접 작성. 종목을 새로 추가할 때 여기에 항목을 추가.
- **실시간성 정보** (현재가, 순자산): `data.json`에 ISIN 기준으로 저장되고, `index.html`이 페이지 로드 시 이 파일을 fetch해서 값을 덮어씀. `data.json`이 없거나 fetch에 실패하면 `FUNDS`에 내장된 스냅샷 값을 그대로 보여줌(안전한 폴백). 각 카테고리 내 정렬도 이 순자산 값 기준 내림차순으로 이뤄짐.

## GitHub Pages에 올리는 법

1. GitHub에서 `etf-factsheet`라는 이름으로 새 저장소를 만들고, 이 폴더 전체를 push (예: `git init && git add . && git commit -m "init" && git remote add origin https://github.com/<계정>/etf-factsheet.git && git push -u origin main`)
2. 저장소 Settings → Pages → Source를 `main` 브랜치 루트로 설정
3. `https://<계정>.github.io/etf-factsheet/`으로 접속 확인

## 매일 자동 갱신 켜는 법

1. 저장소 Settings → Actions → General에서 "Workflow permissions"을 **Read and write permissions**로 변경 (Actions가 `data.json`을 커밋하려면 필요)
2. 그대로 두면 매일 07:30(KST)에 자동 실행됩니다. Actions 탭 → "Update ETF data" → **Run workflow**로 수동 실행도 가능
3. 처음 실행 후 Actions 로그를 꼭 확인하세요 — `[WARN] 파싱 실패` 메시지가 뜨면 funetf.co.kr의 페이지 구조가 예상과 달라서 정규식을 손봐야 한다는 뜻입니다 (`scripts/update_data.py`의 `PRICE_RE_KRW`/`PRICE_RE_USD`, `AUM_RE_KRW`/`AUM_RE_USD` 부분). 환율(`usdKrw`)이 갱신되지 않으면 Frankfurter API(https://api.frankfurter.dev) 응답을 확인하세요.

## 알려진 한계

- funetf.co.kr은 `/usetf/product/view/{ID}` 형식으로 미국 상장 ETF도 다루지만, 이 ID는 검색엔진에 노출되지 않아(`noindex`) 자동으로 찾을 수 없습니다. 다행히 **지금 사이트에 등록된 모든 종목(국내 9개 + 미국 SPY·VOO·IVV·QQQ·TQQQ·QQQM·QLD 7개, 총 16개)의 funetf 링크를 확보해서 전부 자동 갱신 대상에 넣었습니다.** 앞으로 종목을 추가할 때도 funetf.co.kr에서 직접 검색해 `/usetf/product/view/{ID}` 링크를 찾아 `scripts/update_data.py`의 `SOURCES`에 추가하면 됩니다.
- `scripts/update_data.py`는 실제 네트워크 환경에서 아직 테스트하지 못한 상태로 작성되었습니다 (작성 환경에 외부 네트워크 접근이 막혀있었음). 첫 실행 시 Actions 로그 확인이 필요합니다.
- KODEX 200의 ISIN(`KR7069500007`)은 일반적으로 통용되는 값이나, 최초 실행 시 실제로 맞는지 함께 확인해주세요.
