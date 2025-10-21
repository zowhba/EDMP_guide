# Java Heap Memory Monitor

Java 프로세스의 heap 메모리 사용현황을 실시간으로 모니터링하고 힙 덤프 파일을 분석할 수 있는 Streamlit 애플리케이션입니다.

## 기능

### 📊 실시간 모니터링 (app.py)
- **실시간 모니터링**: Java 프로세스 ID를 입력하여 heap 메모리 사용량을 10초 단위로 모니터링
- **시간 범위 조절**: 1, 3, 6, 12, 24시간 중 선택하여 모니터링 데이터 표시
- **시각화**: Plotly를 사용한 실시간 차트 (사용률, 메모리 크기)
- **힙덤프 생성**: 특정 시점에서 힙덤프 파일 생성 (heap_dump 폴더에 저장)
- **프로세스 검증**: Java 프로세스인지 자동 확인
- **Windows WSL 호환**: Windows WSL 환경에 최적화된 Java 도구 경로 자동 감지

### 🔍 힙 덤프 분석기 (heap_dump_analyzer.py)
- **HPROF 파일 분석**: Java 애플리케이션에서 생성된 .hprof 파일 업로드 및 분석 (최대 300MB)
- **Old Generation 누수 분석**: Old Generation 영역의 메모리 누수 의심 객체 자동 식별
- **클래스별 메모리 사용량**: 클래스별 인스턴스 수, 메모리 사용량, 평균 크기 분석
- **시각화**: 메모리 사용량 차트, 인스턴스 수 차트, 파이 차트로 직관적 표시
- **상세 리포트**: 메모리 누수 의심 객체에 대한 상세 분석 리포트 생성
- **임계값 설정**: 사용자 정의 메모리/인스턴스 임계값으로 분석 범위 조절

## Windows WSL 설치 및 실행

### 1. 시스템 요구사항
```bash
# WSL에서 Java JDK 설치 (OpenJDK 11+ 권장)
sudo apt update
sudo apt install -y openjdk-11-jdk

# 또는 OpenJDK 17 설치
sudo apt install -y openjdk-17-jdk

# Java 버전 확인
java -version
javac -version
```

### 2. JAVA_HOME 설정
```bash
# OpenJDK 11의 경우
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH

# .bashrc에 영구 추가
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

### 3. Python 환경 설정 (WSL .venv 기준)
```bash
# 프로젝트 디렉토리로 이동
cd /Ubuntu/home/zowhba/pytest/EDMP_guide/java_heap_mon

# 기존 .venv 가상환경 활성화 (이미 존재하는 경우)
source .venv/bin/activate

# 또는 새로운 가상환경 생성
python3 -m venv .venv
source .venv/bin/activate

# pip 업그레이드
python -m pip install --upgrade pip
```

### 4. 의존성 설치

#### 자동 설치 (권장)
```bash
# WSL 전용 설치 스크립트 실행
chmod +x install_wsl.sh
./install_wsl.sh
```

#### 수동 설치
```bash
# 의존성 설치 (Windows WSL 환경 최적화)
pip install -r requirements.txt
```

### 5. 애플리케이션 실행
```bash
# 실시간 모니터링 실행
streamlit run app.py --server.port 8501

# 힙 덤프 분석기 실행
streamlit run heap_dump_analyzer.py --server.port 8502
```

### 6. 브라우저에서 접속
- **실시간 모니터링**: `http://localhost:8501`
- **힙 덤프 분석기**: `http://localhost:8502`

### 7. Windows 방화벽 설정 (필요시)
Windows 방화벽에서 포트 8501, 8502를 허용하거나 WSL 네트워크 설정을 확인하세요.

## 사용 방법

### 📊 실시간 모니터링 (app.py)
1. **프로세스 ID 입력**: 모니터링할 Java 프로세스의 PID를 입력
2. **시간 범위 선택**: 모니터링할 시간 범위를 선택 (1, 3, 6, 12, 24시간)
3. **모니터링 시작**: "시작" 버튼을 클릭하여 모니터링 시작
4. **힙덤프 생성**: 필요시 "힙덤프 생성" 버튼으로 현재 상태의 힙덤프 파일 생성

### 🔍 힙 덤프 분석기 (heap_dump_analyzer.py)
1. **애플리케이션 실행**: `streamlit run heap_dump_analyzer.py`
2. **HPROF 파일 업로드**: 분석할 .hprof 파일을 업로드
3. **분석 시작**: "분석 시작" 버튼을 클릭하여 분석 실행
4. **결과 확인**: 
   - **분석 결과**: 전체 통계 및 누수 의심 객체 확인
   - **상세 분석**: 클래스별 메모리 사용량 상세 정보
   - **시각화**: 차트를 통한 직관적 메모리 사용량 확인
5. **임계값 조정**: 사이드바에서 메모리/인스턴스 임계값 조정 가능

## 요구사항

- **Windows WSL** 환경 (Ubuntu 기반)
- **Java JDK 11+** (jstat, jmap 명령어 사용)
- **Python 3.8+** (WSL 환경)
- 실행 중인 Java 프로세스

## Windows WSL 특별 고려사항

### Java 도구 자동 감지
애플리케이션은 다음 순서로 Java 도구를 자동으로 찾습니다:
1. `JAVA_HOME` 환경변수
2. `which java` 명령어 결과
3. 일반적인 WSL Java 설치 경로:
   - `/usr/lib/jvm/java-11-openjdk-amd64`
   - `/usr/lib/jvm/java-17-openjdk-amd64`
   - `/usr/lib/jvm/java-8-openjdk-amd64`

### 권한 문제 해결
```bash
# Java 프로세스에 대한 접근 권한 확인
sudo -u java_user jstat -gc <pid>

# 또는 현재 사용자를 java 프로세스 소유자와 동일하게 설정
sudo -u $(ps -o user= -p <pid>) jstat -gc <pid>
```

## 주의사항

- **Java 프로세스 접근 권한**: Java 프로세스에 대한 접근 권한이 필요합니다
- **힙덤프 생성**: 힙덤프 생성 시 프로세스가 일시적으로 정지될 수 있습니다
- **디스크 공간**: 대용량 힙덤프 생성 시 충분한 디스크 공간을 확인하세요
- **파일 크기 제한**: 힙 덤프 분석기는 최대 300MB 파일까지 업로드 가능합니다
- **WSL 환경**: Windows WSL 환경에서 실행되며 Python 3.8+ 필요
- **방화벽**: Windows 방화벽에서 WSL 포트 접근을 허용해야 할 수 있습니다

## 파일 구조

```
java_heap_mon/
├── app.py                    # 실시간 모니터링 애플리케이션
├── heap_dump_analyzer.py     # 힙 덤프 분석기 애플리케이션
├── requirements.txt          # Python 의존성
├── install_wsl.sh           # WSL 환경 자동 설치 스크립트
├── README.md                # 이 파일
├── .streamlit/              # Streamlit 설정 폴더
│   └── config.toml          # Streamlit 설정 (파일 업로드 300MB 제한)
└── heap_dump/               # 힙덤프 파일 저장 폴더 (자동 생성)
```

## 실행 방법

### 실시간 모니터링
```bash
streamlit run app.py --server.port 8501
```

### 힙 덤프 분석기
```bash
streamlit run heap_dump_analyzer.py --server.port 8502
```
