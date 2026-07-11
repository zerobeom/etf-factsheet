#!/usr/bin/env python3
"""
funetf.co.kr(삼성자산운용 펀드 포털)에서 ETF의 현재가·순자산을 긁어오고,
환율(USD/KRW)도 함께 갱신해서 data.json에 반영.

국내 상장 ETF: /product/etf/view/{ISIN}   (예: KR7360750004)
미국 상장 ETF: /usetf/product/view/{ID}   (예: F00000J3JR — funetf 자체 상품 ID, ISIN/티커와 다름)

미국 상장 ETF는 funetf 검색으로 URL을 찾기 어려워(검색엔진 noindex 처리됨),
아래 SOURCES에 직접 확인한 URL만 등록해서 사용한다. 새 종목을 추가하려면
funetf.co.kr에서 직접 검색해 상세페이지 URL을 찾아 SOURCES에 추가할 것.

환율은 Frankfurter API(https://frankfurter.dev, 무료·API 키 불필요, ECB 환율 기준)에서 가져온다.

사용법:
  pip install -r scripts/requirements.txt
  playwright install --with-deps chromium
  python scripts/update_data.py
"""
import json
import re
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data.json"

FX_API_URL = "https://api.frankfurter.dev/v1/latest?from=USD&to=KRW"


def fetch_usd_krw():
    """USD/KRW 환율을 가져온다. 실패하면 None을 반환(기존 값 유지)."""
    try:
        res = requests.get(FX_API_URL, timeout=10)
        res.raise_for_status()
        rate = res.json()["rates"]["KRW"]
        return round(float(rate), 2)
    except Exception as e:  # noqa: BLE001
        print(f"[WARN] 환율 조회 실패, 기존 값 유지: {e}", file=sys.stderr)
        return None


# key: index.html의 FUNDS에서 매칭에 쓰이는 값
#   - 국내 ETF는 isin (예: 'KR7360750004')
#   - 미국 ETF는 ticker (예: 'VOO')
# currency: 'KRW' | 'USD' — 페이지 라벨/통화 표기가 달라서 구분해서 파싱
SOURCES = [
    # ── 국내 상장 (ISIN 기준) ──────────────────────────────
    {"key": "KR7360750004", "url": "https://www.funetf.co.kr/product/etf/view/KR7360750004", "currency": "KRW"},
    {"key": "KR7360200000", "url": "https://www.funetf.co.kr/product/etf/view/KR7360200000", "currency": "KRW"},
    {"key": "KR7379800006", "url": "https://www.funetf.co.kr/product/etf/view/KR7379800006", "currency": "KRW"},
    {"key": "KR7379780000", "url": "https://www.funetf.co.kr/product/etf/view/KR7379780000", "currency": "KRW"},
    {"key": "KR7133690008", "url": "https://www.funetf.co.kr/product/etf/view/KR7133690008", "currency": "KRW"},
    {"key": "KR7379810005", "url": "https://www.funetf.co.kr/product/etf/view/KR7379810005", "currency": "KRW"},
    {"key": "KR7367380003", "url": "https://www.funetf.co.kr/product/etf/view/KR7367380003", "currency": "KRW"},
    {"key": "KR7368590006", "url": "https://www.funetf.co.kr/product/etf/view/KR7368590006", "currency": "KRW"},
    {"key": "KR7476030002", "url": "https://www.funetf.co.kr/product/etf/view/KR7476030002", "currency": "KRW"},
    {"key": "KR70069M0006", "url": "https://www.funetf.co.kr/product/etf/view/KR70069M0006", "currency": "KRW"},
    {"key": "KR7069500007", "url": "https://www.funetf.co.kr/product/etf/view/KR7069500007", "currency": "KRW"},
    # ── 미국 상장 (funetf 자체 ID 기준, /usetf/ 경로) ────────
    {"key": "SPY", "url": "https://www.funetf.co.kr/usetf/product/view/FEUSA00001", "currency": "USD"},
    {"key": "VOO", "url": "https://www.funetf.co.kr/usetf/product/view/F00000J3JR", "currency": "USD"},
    {"key": "IVV", "url": "https://www.funetf.co.kr/usetf/product/view/FEUSA0000E", "currency": "USD"},
    {"key": "QQQ", "url": "https://www.funetf.co.kr/usetf/product/view/FEUSA00003", "currency": "USD"},
    {"key": "TQQQ", "url": "https://www.funetf.co.kr/usetf/product/view/FOUSA08MU7", "currency": "USD"},
    {"key": "QQQM", "url": "https://www.funetf.co.kr/usetf/product/view/F000015DO3", "currency": "USD"},
    {"key": "QLD", "url": "https://www.funetf.co.kr/usetf/product/view/FEUSA04AGC", "currency": "USD"},
    # 모든 종목 등록 완료 (2026-07-11 기준)
]

PRICE_RE_KRW = re.compile(r"현재가[\s\S]{0,80}?([\d,]+)\s*원")
PRICE_RE_USD = re.compile(r"종가[\s\S]{0,80}?\$([\d,.]+)")
AUM_RE_KRW = re.compile(r"순자산\s*\n*\s*([\d,]+)\s*억원")
AUM_RE_USD = re.compile(r"순자산\s*\n*\s*\$([\d,.]+)\s*억")


def format_usd_from_eok(value_eok: float) -> str:
    """funetf가 '$9,861.79억'처럼 억 단위로 주는 달러 순자산을 '$986.2B' 형식으로."""
    usd = value_eok * 1e8
    if usd >= 1e9:
        return f"${usd/1e9:.1f}B"
    if usd >= 1e6:
        return f"${usd/1e6:.1f}M"
    return f"${usd:,.0f}"


def parse_page_text(text: str, currency: str):
    price_re = PRICE_RE_KRW if currency == "KRW" else PRICE_RE_USD
    aum_re = AUM_RE_KRW if currency == "KRW" else AUM_RE_USD
    price_match = price_re.search(text)
    aum_match = aum_re.search(text)
    if not price_match or not aum_match:
        return None

    aum_eok = float(aum_match.group(1).replace(",", ""))

    if currency == "KRW":
        price = int(price_match.group(1).replace(",", ""))
        return {"price": f"{price:,}원", "aum": f"{aum_eok:,.0f}억원"}
    else:
        price = float(price_match.group(1).replace(",", ""))
        return {"price": f"${price:,.2f}", "aum": format_usd_from_eok(aum_eok)}


def fetch_one(page, url: str, currency: str):
    page.goto(url, wait_until="networkidle", timeout=30_000)
    page.wait_for_timeout(1500)  # 비동기로 채워지는 값 대기
    text = page.inner_text("body")
    return parse_page_text(text, currency)


def main():
    if DATA_PATH.exists():
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    else:
        data = {"updated": "", "source": "funetf.co.kr", "usdKrw": None, "funds": {}}

    fx_rate = fetch_usd_krw()
    if fx_rate is not None:
        data["usdKrw"] = fx_rate
        print(f"[OK] USD/KRW: {fx_rate}")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="ko-KR")
        for src in SOURCES:
            try:
                result = fetch_one(page, src["url"], src["currency"])
                if result:
                    data["funds"][src["key"]] = result
                    print(f"[OK] {src['key']}: {result}")
                else:
                    print(f"[WARN] 파싱 실패: {src['key']} ({src['url']}) — 페이지 구조가 바뀌었을 수 있음", file=sys.stderr)
            except Exception as e:  # noqa: BLE001 — 개별 종목 실패가 전체를 막지 않도록
                print(f"[ERROR] {src['key']}: {e}", file=sys.stderr)
            time.sleep(1)  # 과도한 요청 방지
        browser.close()

    data["updated"] = time.strftime("%Y-%m-%d")
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"data.json 갱신 완료 ({data['updated']})")


if __name__ == "__main__":
    main()
