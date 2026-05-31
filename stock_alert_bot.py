"""
네이버 금융 크롤링 → Discord 웹훅 알림 봇
- 5분마다 삼성전자 현재가 체크
- 직전 대비 변동률 큰 경우 알림
- 특정 가격 돌파 시 알림
"""
import os
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, time as dtime

# =============================================
# ⚙️ 설정 영역 (여기만 수정하면 됩니다)
# =============================================

# Discord 웹훅 URL (Discord 채널 설정 → 연동 → 웹훅에서 생성)
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# 모니터링 종목 (종목코드: 종목명)
STOCKS = {
    "000660": "SK하이닉스",
}

# 변동률 알림 기준 (%) - 이 값 이상 변동 시 알림
VOLATILITY_THRESHOLD = 3  # 0.5% 이상 변동 시

# 가격 돌파 알림 설정 (종목코드: [(방향, 가격), ...])
# 방향: "above" = 이상, "below" = 이하
PRICE_ALERTS = {
    "005930": [
        ("above", 2245000),   # n원 이상이면 알림
        ("below", 2000000),   # n원 이하면 알림
    ],
}

# 체크 간격 (초)
INTERVAL = 300  # 5분

# 장 운영 시간 (이 시간 외에는 크롤링 안 함)
MARKET_OPEN  = dtime(9, 0)
MARKET_CLOSE = dtime(15, 30)

# =============================================


def is_market_open() -> bool:
    """현재 장 운영 시간 여부 확인"""
    now = datetime.now().time()
    return MARKET_OPEN <= now <= MARKET_CLOSE


def get_current_price(stock_code: str) -> int | None:
    """네이버 금융에서 현재가 크롤링"""
    url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = requests.get(url, headers=headers, timeout=5)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        price_tag = soup.select_one("p.no_today span.blind")
        if price_tag:
            price = int(price_tag.text.replace(",", ""))
            return price
    except Exception as e:
        print(f"[ERROR] {stock_code} 크롤링 실패: {e}")

    return None


def send_discord(message: str):
    """Discord 웹훅으로 메시지 전송"""
    payload = {"content": message}
    try:
        res = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        res.raise_for_status()
        print(f"[Discord] 전송 완료: {message}")
    except Exception as e:
        print(f"[ERROR] Discord 전송 실패: {e}")


def check_price_alerts(stock_code: str, name: str, price: int, triggered: set):
    """가격 돌파 알림 체크 (중복 알림 방지)"""
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
            # 조건 해제 시 알림 키 제거 (재알림 가능하도록)
            triggered.discard(alert_key)


def main():
    # 봇 시작 알림 (웹훅 연결 확인용)
    send_discord("✅ 주식 알림 봇 시작!")
    
    print("=" * 40)
    print("📈 주식 알림 봇 시작")
    print(f"   종목: {', '.join(STOCKS.values())}")
    print(f"   변동률 기준: ±{VOLATILITY_THRESHOLD}%")
    print(f"   체크 간격: {INTERVAL}초")
    print("=" * 40)

    prev_prices: dict[str, int] = {}      # 직전 가격 저장
    triggered_alerts: set = set()         # 돌파 알림 중복 방지

    while True:
        now_str = datetime.now().strftime("%H:%M:%S")

        #if not is_market_open():
         #   print(f"[{now_str}] 장 외 시간 - 대기 중...")
          #  time.sleep(INTERVAL)
           # continue

        for code, name in STOCKS.items():
            price = get_current_price(code)

            if price is None:
                print(f"[{now_str}] {name} 가격 조회 실패")
                continue

            print(f"[{now_str}] {name}: {price:,}원")

            # ── 변동률 체크 ──────────────────────────
            if code in prev_prices:
                prev = prev_prices[code]
                change_pct = (price - prev) / prev * 100

                if abs(change_pct) >= VOLATILITY_THRESHOLD:
                    direction = "📈" if change_pct > 0 else "📉"
                    send_discord(
                        f"{direction} **{name}** 변동 감지!\n"
                        f"직전가 {prev:,}원 → 현재가 **{price:,}원**\n"
                        f"변동률: `{change_pct:+.2f}%`"
                    )
                else:
                    print(f"         변동률 {change_pct:+.2f}% → 알림 없음")

            # ── 가격 돌파 체크 ───────────────────────
            check_price_alerts(code, name, price, triggered_alerts)

            prev_prices[code] = price

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
