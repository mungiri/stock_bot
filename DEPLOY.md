# GCP e2-micro (Always Free) 배포 가이드

토스 Open API 시세 알림 봇을 GCP 무료 VM에서 24/7 구동.

## 0. 사전 준비
- GCP 계정 (신용카드 등록 — Always Free는 과금 안 됨)
- 토스증권 WTS → 설정 > Open API 에서 `client_id` / `client_secret` 발급
- Discord 웹훅 URL

## 1. VM 생성 (Always Free 조건 — 벗어나면 과금됨)
GCP Console → Compute Engine → VM instances → Create:
- **Region**: `us-west1` / `us-central1` / `us-east1` 중 하나 (이 3개만 무료)
- **Machine type**: `e2-micro` (필수 — 다른 타입은 유료)
- **Boot disk**: Standard persistent disk, 30GB 이하, Debian 12
- **Firewall**: 아웃바운드만 쓰므로 HTTP/HTTPS 체크 불필요
- Create

## 2. 접속 + 코드 올리기
GCP Console의 VM 행에서 **SSH** 버튼 클릭 (브라우저 터미널).

```bash
sudo apt update && sudo apt install -y python3-venv git
git clone <이_repo_URL> stock_bot      # 또는 scp로 파일 전송
cd stock_bot
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

> 시크릿이 git에 없으므로(.gitignore) clone만으론 env 없음 → 다음 단계에서 생성.

## 3. 시크릿 설정
```bash
cp stock-alert.env.example stock-alert.env
nano stock-alert.env      # client_id / secret / webhook 실제 값 입력
```

## 4. 수동 1회 테스트
```bash
set -a; source stock-alert.env; set +a
venv/bin/python stock_alert_bot_toss.py
```
- Discord에 "✅ 봇 시작" 오면 연결 OK
- `[DEBUG] /api/v1/prices raw 응답` 라인 확인 → 현재가 필드명 맞는지 점검
- Ctrl+C로 중단

## 5. systemd 상시 구동
```bash
# stock-alert.service 안의 YOUR_USER 를 실제 계정명(whoami)으로 치환
whoami
sed -i "s/YOUR_USER/$(whoami)/g" stock-alert.service

sudo cp stock-alert.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now stock-alert
sudo systemctl status stock-alert     # active (running) 확인
```

## 6. 운영
```bash
tail -f stock_bot.log                  # 로그 실시간
sudo systemctl restart stock-alert     # 코드/설정 변경 후 재시작
sudo systemctl stop stock-alert        # 중지
```

## 참고
- 봇은 장시간(09:00~15:30 KST) 외엔 5분 대기만 함 → VM CPU 거의 0, 무료 한도 여유.
- VM 재부팅돼도 `enable` 했으니 자동 시작.
- 토큰은 코드가 자동 갱신(만료 60초 전).
