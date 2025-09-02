# 🚀 Stress Tester

CSV 변수 치환 + cURL 템플릿 기반 REST 부하 테스트 도구

## 📋 기능

- **cURL 템플릿 파싱**: cURL 명령어를 자동으로 파싱하여 HTTP 요청 구성
- **CSV 변수 치환**: CSV 파일의 데이터를 요청에 동적으로 치환
- **부하 테스트**: 설정 가능한 RPS, 지속시간, 동시성으로 부하 테스트 실행
- **실시간 통계**: 성공률, 응답시간, HTTP 상태 코드 분포 등 실시간 모니터링

## 🛠️ 설치

### 1. 의존성 설치

#### 자동 설치 (권장)
```bash
chmod +x install.sh
./install.sh
```

#### 단계별 설치 (문제 발생 시)
```bash
chmod +x install_step_by_step.sh
./install_step_by_step.sh
```

#### 수동 설치
```bash
# pip 업그레이드 (리눅스 환경에서 권장)
python -m pip install --upgrade pip

# 개별 패키지 설치
pip install streamlit>=0.75.0
pip install httpx>=0.22.0
pip install pandas>=1.1.0

# 또는 requirements.txt 사용
pip install -r requirements.txt
```

### 2. 앱 실행

```bash
streamlit run app.py --server.port 8501
```

또는

```bash
python -m streamlit run app.py --server.port 8501
```

### 3. 리눅스 환경 특별 주의사항

- **Python 버전**: Python 3.7 이상 권장
- **가상환경**: 가상환경 사용을 강력히 권장
- **방화벽**: 8501 포트가 열려있는지 확인
- **권한**: 실행 권한이 있는지 확인 (`chmod +x install.sh`)

## 📖 사용법

### 1. cURL 템플릿 설정
- 기본값으로 제공되는 cURL 템플릿을 사용하거나 수정
- 리눅스 환경에 최적화된 `\` 라인 연속 문자 사용
- Windows 환경에서는 `^` 대신 `\` 사용 권장

### 2. CSV 파일 업로드 (선택사항)
- CSV 파일에 `stb_id`, `mac_address`, `model_nm` 컬럼 포함
- 각 행의 데이터가 요청 시 동적으로 치환됨

### 3. 테스트 설정
- **RPS**: 초당 요청 수
- **지속시간**: 테스트 실행 시간 (초)
- **타임아웃**: 개별 요청 타임아웃 (초)
- **동시성**: 최대 동시 요청 수

### 4. 테스트 실행
- "설정 저장" 버튼으로 설정 저장
- "Start" 버튼으로 부하 테스트 시작

## 🔧 주요 기능

### cURL 파싱 지원
- HTTP 메서드 자동 감지 (GET/POST)
- 헤더 파싱 (`-H`, `--header`)
- 데이터 파싱 (`--data`, `-d`)
- 라인 연속 문자 처리 (`\`, `^`)

### 변수 치환
- `{{stb_info.stb_id}}` → CSV의 `stb_id` 값
- `{{stb_info.mac_addr}}` → CSV의 `mac_address` 값  
- `{{stb_info.modl_nm}}` → CSV의 `model_nm` 값

### 부하 테스트
- 비동기 HTTP 클라이언트 (`httpx`)
- 설정 가능한 RPS 제어
- 동시성 제한 (세마포어)
- 실시간 결과 수집

## 📊 결과 분석

### 실시간 통계
- 총 요청 수
- 성공률 (%)
- 평균 응답시간 (ms)
- P99 응답시간 (ms)

### 상세 결과
- HTTP 상태 코드 분포
- 응답시간 히스토그램
- 요청/응답 샘플 미리보기

## 🐛 문제 해결

### cURL 파싱 실패
- 라인 연속 문자 확인 (`\` 또는 `^`)
- 따옴표 사용 확인
- HTTP 메서드 명시 (`-X POST`)

### 네트워크 연결 실패
- 대상 서버 URL 확인
- 방화벽 설정 확인
- 타임아웃 값 조정

### 변수 치환 문제
- CSV 컬럼명 확인 (`stb_id`, `mac_address`, `model_nm`)
- 플레이스홀더 문법 확인 (`{{stb_info.stb_id}}`)

## 📝 예시

### 기본 cURL 템플릿
```bash
curl -X POST "http://1.255.145.229:8080/v1/edmp/api/update/stb" \
-H "Content-Type: application/json;charset=utf-8" \
-H "IF: IF-EDMP.UPDATE-003" \
-H "response_format: json" \
-H "ver: v1" \
--data '{
    "if_no": "IF-EDMP.UPDATE.API-003",
    "response_format": "json",
    "ui_name": "NXNEWUI2Q",
    "ver": "v1",
    "stb_info": {
        "stb_id": "{A9CCC0C8-F569-11E9-819D-37B877ECC397}",
        "mac_addr": "80:8c:97:22:1c:80",
        "modl_nm": "BKO-UA500R",
        "stb_sw_ver": "16.522.47-0000",
        "stb_ip": "0.0.0.0",
        "stb_uptime": "20200409123923",
        "rcu_pairing": "0",
        "rcu_manufr_cd": "abcdabcdabcd",
        "rcu_firm_ver": "0x12",
        "hdmi_pow": "1",
        "trigger_cd": "01",
        "timestamp": "1584329976176"
    }
}'
```

### CSV 파일 예시
```csv
stb_id,mac_address,model_nm
{A9CCC0C8-F569-11E9-819D-37B877ECC397},80:8c:97:22:1c:80,BKO-UA500R
{B8DDD1D9-G670-12F0-920E-48C988FDD408},90:9d:a8:33:2d:91,BKO-UA500R
```

## 🔄 업데이트 내역

- **v1.0.0**: 초기 버전
  - cURL 파싱 기능
  - CSV 변수 치환
  - 기본 부하 테스트
  - 실시간 통계

## �� 라이선스

MIT License
