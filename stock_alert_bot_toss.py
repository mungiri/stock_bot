"""
토스증권 Open API → Discord 웹훅 알림 봇
- 네이버 크롤링 대신 토스증권 공식 REST API(현재가) 사용
- 5분마다 현재가 체크, 변동률/가격 돌파 알림 (로직은 기존과 동일)

[사전 준비]
1) 토스증권 WTS 로그인 → 설정 > Open API 에서 client_id / client_secret 발급
2) 아래 환경변수 설정 후 실행:
     export TOSS_CLIENT_ID="xxx"
     export TOSS_CLIENT_SECRET="yyy"
     export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
   (보안: 시크릿을 코드에 하드코딩하지 말 것)
"""
import os
import time
import requests
from datetime import datetime, time as dtime
import pytz

# =============================================
# ⚙️ 설정 영역
# =============================================

DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
TOSS_CLIENT_ID       = os.environ["TOSS_CLIENT_ID"]
TOSS_CLIENT_SECRET   = os.environ["TOSS_CLIENT_SECRET"]

TOSS_BASE = "https://openapi.tossinvest.com"

# 모니터링 종목 (symbol: 종목명)  — 토스 symbol은 국내 6자리 코드 사용
STOCKS = {
    "005930": "삼성전자",
    "0046A0": "TIGER 미국초단기(3개월이하) 국채",
}

VOLATILITY_THRESHOLDS = {
    "005930": 0.5,
    "0046A0": 0.2,
}

PRICE_ALERTS = {
    "005930": [
        ("above", 375000),
        ("below", 300000),
    ],
}

INTERVAL = 300  # 5분

MARKET_OPEN  = dtime(9, 0)
MARKET_CLOSE = dtime(15, 30)

# =============================================

KR_TZ = pytz.timezone('Asia/Seoul')


def is_market_open() -> bool:
    now = datetime.now(KR_TZ).time()
    return MARKET_OPEN <= now <= MARKET_CLOSE


# ── 토큰 관리 ────────────────────────────────────────────
_token_cache = {"value": None, "expires_at": 0.0}


def get_access_token() -> str:
    """OAuth2 client_credentials 토큰 발급 + 만료 전까지 캐시 재사용"""
    now = time.time()
    if _token_cache["value"] and now < _token_cache["expires_at"]:
        return _token_cache["value"]

    res = requests.post(
        f"{TOSS_BASE}/oauth2/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_id": TOSS_CLIENT_ID,
            "client_secret": TOSS_CLIENT_SECRET,
        },
        timeout=10,
    )
    res.raise_for_status()
    body = res.json()
    token = body["access_token"]
    expires_in = int(body.get("expires_in", 3600))
    # 만료 60초 전에 미리 갱신
    _token_cache["value"] = token
    _token_cache["expires_at"] = now + max(expires_in - 60, 0)
    return token


def get_current_price(stock_code: str) -> int | None:
    """토스증권 Open API 현재가 조회.

    응답 스키마 (OpenAPI 확정):
      { "result": [ {"symbol":"005930","lastPrice":"72000","currency":"KRW","timestamp":...}, ... ] }
    lastPrice 는 문자열로 내려옴.
    """
    try:
        token = get_access_token()
        res = requests.get(
            f"{TOSS_BASE}/api/v1/prices",
            headers={"Authorization": f"Bearer {token}"},
            params={"symbols": stock_code},
            timeout=10,
        )
        res.raise_for_status()
        body = res.json()

        for item in body.get("result", []):
            if str(item.get("symbol")) != stock_code:
                continue
            last = item.get("lastPrice")
            if last is None:
                print(f"[WARN] {stock_code} lastPrice 없음 (체결 미발생?) item={item}")
                return None
            return int(float(last))

        print(f"[WARN] {stock_code} result에 종목 없음. raw={body}")
    except Exception as e:
        print(f"[ERROR] {stock_code} 시세 조회 실패: {e}")

    return None


def send_discord(message: str):
    payload = {"content": message}
    try:
        res = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        res.raise_for_status()
        print(f"[Discord] 전송 완료: {message}")
    except Exception as e:
        print(f"[ERROR] Discord 전송 실패: {e}")


def check_price_alerts(stock_code: str, name: str, price: int, triggered: set):
    if stock_code not in PRICE_ALERTS:
        return

    for direction, target in PRICE_ALERTS[stock_code]:
        alert_key = f"{stock_code}_{direction}_{target}"

        if direction == "above" and price >= target:
            if alert_key not in triggered:
                send_discord(
                    f"🚨 **{name}** 가격 돌파 알림!\n"
                    f"현재가 **{price:,}원** ≥ 목표가 {target:,}원"
                )
                triggered.add(alert_key)
        elif direction == "below" and price <= target:
            if alert_key not in triggered:
                send_discord(
                    f"🚨 **{name}** 가격 하락 알림!\n"
                    f"현재가 **{price:,}원** ≤ 목표가 {target:,}원"
                )
                triggered.add(alert_key)
        else:
            triggered.discard(alert_key)


def main():
    send_discord("✅ 주식 알림 봇 시작! (토스증권 Open API)")

    print("=" * 40)
    print("📈 주식 알림 봇 시작 (토스증권 Open API)")
    print(f"   종목: {', '.join(STOCKS.values())}")
    print(f"   체크 간격: {INTERVAL}초")
    print("=" * 40)

    prev_prices: dict[str, int] = {}
    triggered_alerts: set = set()

    while True:
        now_str = datetime.now().strftime("%H:%M:%S")

        if not is_market_open():
            print(f"[{now_str}] 장 외 시간 - 대기 중...")
            time.sleep(INTERVAL)
            continue

        for code, name in STOCKS.items():
            price = get_current_price(code)

            if price is None:
                print(f"[{now_str}] {name} 가격 조회 실패")
                continue

            print(f"[{now_str}] {name}: {price:,}원")

            if code in prev_prices:
                prev = prev_prices[code]
                change_pct = (price - prev) / prev * 100
                threshold = VOLATILITY_THRESHOLDS.get(code, 0.5)

                if abs(change_pct) >= threshold:
                    direction = "📈" if change_pct > 0 else "📉"
                    send_discord(
                        f"{direction} **{name}** 변동 감지!\n"
                        f"직전가 {prev:,}원 → 현재가 **{price:,}원**\n"
                        f"변동률: `{change_pct:+.2f}%`"
                    )
                else:
                    print(f"         변동률 {change_pct:+.2f}% → 알림 없음")

            check_price_alerts(code, name, price, triggered_alerts)
            prev_prices[code] = price

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
