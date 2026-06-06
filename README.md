# 📈 Stock Alert Bot

네이버 금융 데이터를 크롤링하여 조건에 맞을 때 **Discord**로 주식 변동 알림을 전송하는 파이썬 봇입니다. 

* **5분마다 현재가 체크** (장 운영 시간에만 작동)
* **직전 대비 변동률 큰 경우 알림**
* **특정 가격 돌파(이상/이하) 시 알림**

---

## How to Install

### Prerequisites
* **Python 3.x** — 파이썬 실행 환경
* **Discord Webhook URL** — 디스코드 채널 설정 → 연동 → 웹훅에서 생성

### 1. Project Setup
프로젝트 실행에 필요한 파이썬 패키지를 설치합니다.
pip install requests beautifulsoup4 pytz

### 2. Environment Setup
디스코드 웹훅으로 메시지를 보내기 위해 환경 변수를 설정합니다. 시스템에 맞게 아래 명령어를 입력하세요:

Linux / macOS

Bash
export DISCORD_WEBHOOK_URL="여기에_디스코드_웹훅_URL_입력"
Windows (명령 프롬프트)

DOS
set DISCORD_WEBHOOK_URL="여기에_디스코드_웹훅_URL_입력"
(또는 stock_alert_bot.py 코드 내의 os.environ.get() 부분을 실제 URL 문자열로 직접 수정해도 됩니다.)

3. Configuration
stock_alert_bot.py 파일을 열고 ⚙️ 설정 영역을 본인에게 맞게 수정하세요:

Python
# 모니터링 종목 설정
STOCKS = {
    "000660": "SK하이닉스",
}

# 변동률 알림 기준 (%)
VOLATILITY_THRESHOLDS = {
    "000660": 0.5,
}

# 가격 돌파 알림 설정 (above: 이상, below: 이하)
PRICE_ALERTS = {
    "000660": [
        ("above", 250000),
        ("below", 150000),
    ],
}
4. Run Bot
아래 명령어를 실행하여 모니터링을 시작합니다.

Bash
python stock_alert_bot.py
