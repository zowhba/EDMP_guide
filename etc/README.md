# 🪙 Multi-Crypto Wallet Web Application

Streamlit으로 구현된 멀티 암호화폐 지갑 웹 애플리케이션입니다. Bitcoin과 BitMobick을 지원하며, 교육 및 학습 목적으로 제작되었습니다.

## ✨ 주요 기능

### 🪙 **멀티 코인 지원**
- **Bitcoin (BTC)**: 원조 암호화폐
- **BitMobick (BTMK)**: 비트코인 호환 암호화폐
- **코인 전환**: 실시간 코인 타입 변경
- **독립적 지갑**: 각 코인별 별도 지갑 관리

### 🔐 지갑 관리
- **새 지갑 생성**: 안전한 개인키/공개키 쌍 생성 (코인별)
- **기존 지갑 가져오기**: 개인키, WIF, JSON 파일로 지갑 복원
- **지갑 정보 내보내기**: JSON 형태로 지갑 정보 저장
- **주소 호환성**: 각 코인의 네트워크 바이트 지원

### 💰 잔액 조회
- **실시간 잔액**: 확인된 잔액과 미확인 잔액 표시
- **거래 통계**: 총 수신/송신 금액 및 거래 횟수
- **네트워크 상태**: 테스트넷/메인넷 지원
- **코인별 단위**: 각 코인의 소수점 자릿수 지원

### 📋 거래 내역
- **트랜잭션 목록**: 최근 거래 내역 조회
- **상세 정보**: 각 거래의 상세 정보 확인
- **확인 상태**: 트랜잭션 확인 상태 추적
- **멀티 코인 포맷**: 코인별 적절한 단위 표시

### 💸 송금 기능
- **테스트넷 송금**: 안전한 테스트 환경에서 송금 테스트
- **주소 검증**: 각 코인별 주소 유효성 검사
- **수수료 계산**: 예상 수수료 자동 계산
- **코인별 송금**: 선택된 코인으로 송금

### 📱 QR 코드
- **주소 QR**: 지갑 주소를 QR 코드로 생성
- **결제 요청**: 특정 금액을 포함한 결제 요청 QR 코드
- **BIP21 지원**: 표준 비트코인 URI 스키마 사용
- **멀티 코인 URI**: 각 코인에 맞는 URI 생성

## 🚀 설치 및 실행

### 1. 필요 조건
- Python 3.8 이상
- 인터넷 연결 (블록체인 API 사용)

### 2. 설치
```bash
# 1. etc 디렉토리로 이동
cd etc

# 2. 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 필수 패키지 설치
pip install -r requirements.txt
```

### 3. 실행
```bash
streamlit run bitcoin_app.py
```

웹 브라우저에서 `http://localhost:8501`로 접속하여 사용할 수 있습니다.

### 4. 테스트
```bash
# 전체 기능 테스트 (추천)
python test_final_wallet.py

# 개별 기능 테스트
python html_parser.py      # HTML 파싱 테스트
python test_api.py          # API 연결 테스트
python demo.py              # 라이브러리 데모
```

## 🔧 사용법

### 코인 선택
1. 사이드바에서 **"🪙 코인 선택"** 
2. Bitcoin 또는 BitMobick 선택
3. 네트워크 설정 (테스트넷/메인넷)

### 지갑 생성
1. **"🔐 지갑 관리"** 탭 선택
2. **"🆕 새 지갑 생성"** 섹션에서 "🔑 새 지갑 생성" 버튼 클릭
3. 생성된 지갑 정보를 안전한 곳에 저장
4. **주의**: 각 코인별로 별도의 지갑이 생성됩니다

### 기존 지갑 가져오기
1. **"🔐 지갑 관리"** 탭 선택
2. **"📥 기존 지갑 가져오기"** 섹션에서 가져오기 방법 선택:
   - **개인키 (Hex)**: 64자리 16진수 개인키
   - **WIF**: Wallet Import Format
   - **JSON 파일**: 이전에 저장한 지갑 파일

### 잔액 확인
1. **"💰 잔액 조회"** 탭 선택
2. 자동으로 현재 지갑의 잔액 표시
3. "🔄 잔액 새로고침" 버튼으로 최신 정보 조회

### 거래 내역 확인
1. **"📋 거래 내역"** 탭 선택
2. 조회할 거래 수 선택 (10~100개)
3. 각 거래를 클릭하여 상세 정보 확인

### 송금하기 (테스트넷 전용)
1. 사이드바에서 **"테스트넷"** 선택
2. **"💸 송금"** 탭 선택
3. 수신자 주소와 금액 입력
4. 송금 정보 확인 후 실행

### QR 코드 생성
1. **"📱 QR 코드"** 탭 선택
2. **주소 QR**: 자동으로 지갑 주소 QR 코드 표시
3. **결제 요청 QR**: 금액과 메시지를 포함한 QR 코드 생성

## 🪙 지원 암호화폐

### Bitcoin (BTC)
- **네트워크 바이트**: 메인넷 0x00, 테스트넷 0x6f
- **WIF 바이트**: 메인넷 0x80, 테스트넷 0xef
- **API 지원**: BlockCypher API 완전 지원
- **주소 예시**: `1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa` (메인넷)

### BitMobick (BTMK)
- **네트워크 바이트**: 메인넷 0x19, 테스트넷 0x6f
- **WIF 바이트**: 메인넷 0x99, 테스트넷 0xef
- **API 지원**: 시뮬레이션된 데모 모드
- **주소 특징**: 'B'로 시작하는 주소 (예: BTE5FKKtDnwn96KXMPwxQXkxipVJs52Kju)

## 🌐 네트워크 설정

### 테스트넷 (권장)
- **안전한 테스트 환경**
- **실제 가치가 없는 코인**
- **모든 기능 사용 가능**
- **학습 및 테스트 목적**

### 메인넷 (주의!)
- **실제 암호화폐 네트워크**
- **실제 가치가 있는 코인**
- **송금 기능 비활성화**
- **조회 기능만 사용 가능**

## ⚠️ 보안 주의사항

### 개인키 관리
- **절대 타인과 공유하지 마세요**
- **안전한 곳에 백업 보관**
- **스크린샷 주의**
- **공공 장소에서 사용 금지**

### 네트워크 보안
- **신뢰할 수 있는 네트워크 사용**
- **VPN 사용 권장**
- **공공 WiFi 사용 금지**

### 소프트웨어 보안
- **정기적인 업데이트**
- **바이러스 검사**
- **의심스러운 링크 클릭 금지**

## 🛠️ 기술 스택

- **Frontend**: Streamlit
- **Backend**: Python
- **암호화**: ECDSA (secp256k1)
- **API**: BlockCypher API (Bitcoin), 호환 API (BitMobick)
- **QR Code**: qrcode library
- **Encoding**: base58, hashlib
- **멀티 코인**: 모듈화된 네트워크 설정

## 📁 파일 구조

```
etc/
├── bitcoin_app.py         # 메인 Streamlit 애플리케이션 (멀티 코인 지원)
├── bitcoin_wallet.py      # 멀티 크립토 지갑 라이브러리
├── demo.py               # 멀티 코인 기능 데모
├── run.py                # 편리한 실행 스크립트
├── requirements.txt       # 필수 패키지 목록
└── README.md             # 사용법 가이드
```

## 🆕 BitMobick 지원 특징

### 호환성
- **Bitcoin 호환**: 동일한 암호화 알고리즘 사용
- **주소 체계**: Bitcoin과 유사하지만 다른 네트워크 바이트
- **API 호환**: Bitcoin API를 통한 블록체인 조회

### 차이점
- **메인넷 주소**: `B`로 시작 (네트워크 바이트 0x19)
- **WIF 형식**: 다른 네트워크 바이트 (0x99)
- **독립 지갑**: Bitcoin과 별도로 관리
- **데모 모드**: 실제 블록체인 대신 시뮬레이션 사용

## 🔍 API 정보

### Bitcoin
[BlockCypher API](https://www.blockcypher.com/dev/)를 사용합니다:
- **테스트넷**: `https://api.blockcypher.com/v1/btc/test3`
- **메인넷**: `https://api.blockcypher.com/v1/btc/main`

### BitMobick
시뮬레이션된 데모 모드:
- **실제 API 없음**: 가상의 블록체인 데이터 생성
- **일관된 데이터**: 주소 기반으로 동일한 결과 보장
- **학습 목적**: BitMobick 지갑 사용법 학습용

## 🚨 면책 조항

- **교육 목적**: 이 소프트웨어는 교육 및 학습 목적으로 제작되었습니다
- **멀티 코인 지원**: Bitcoin과 BitMobick 지원은 실험적 기능입니다
- **책임 한계**: 사용으로 인한 손실에 대해 개발자는 책임지지 않습니다
- **보안 경고**: 실제 자산 관리에는 전문적인 보안 검토가 필요합니다
- **테스트 권장**: 메인넷 사용 전 충분한 테스트를 진행하세요
- **BitMobick 주의**: BitMobick 지원은 가상의 구현이며 실제 네트워크와 다를 수 있습니다

## 📚 참고 자료

- [Bitcoin Developer Documentation](https://developer.bitcoin.org/)
- [BIP21 - URI Scheme](https://github.com/bitcoin/bips/blob/master/bip-0021.mediawiki)
- [Base58 Encoding](https://en.bitcoin.it/wiki/Base58Check_encoding)
- [ECDSA Cryptography](https://en.bitcoin.it/wiki/Elliptic_Curve_Digital_Signature_Algorithm)

## 🤝 기여

버그 리포트나 기능 제안은 GitHub Issues를 통해 제출해주세요.

---

**⚠️ 보안 주의**: 실제 비트코인 자산 관리 시에는 하드웨어 지갑 등 전문적인 보안 솔루션을 사용하시기 바랍니다.
