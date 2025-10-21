# Grafana Dashboard Analyzer

Grafana 대시보드를 자동으로 캡처하고 Azure OpenAI를 활용하여 AI 분석을 수행하는 시스템입니다.

## 🚀 주요 기능

- **자동 대시보드 캡처**: Grafana API를 활용한 대시보드 스크린샷 자동 생성
- **AI 기반 분석**: Azure OpenAI GPT-4 Vision을 활용한 대시보드 이미지 분석
- **분석 이력 관리**: SQLite 기반 분석 결과 저장 및 조회
- **사용자 친화적 UI**: Streamlit 기반 직관적인 웹 인터페이스
- **프롬프트 템플릿**: 다양한 분석 목적에 맞는 프롬프트 템플릿 제공

## 📁 프로젝트 구조

```
EDMP_mon/
├── main.py              # FastAPI 백엔드 서버
├── app.py               # Streamlit UI 애플리케이션
├── prompt_manager.py    # 프롬프트 템플릿 관리 모듈
├── prompts/             # 프롬프트 템플릿 텍스트 파일들
│   ├── 기본_분석.txt
│   ├── 성능_분석.txt
│   ├── 장애_분석.txt
│   ├── 트렌드_분석.txt
│   ├── 보안_분석.txt
│   └── 용량_계획.txt
├── requirements.txt     # Python 패키지 의존성
├── README.md           # 프로젝트 설명서
├── .env                # 환경변수 설정 파일 (생성 필요)
├── uploads/            # 캡처된 이미지 저장 디렉토리 (자동 생성)
└── analysis_history.db # SQLite 데이터베이스 (자동 생성)
```

## ⚙️ 설치 및 설정

### 1. 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. 환경변수 설정

`.env` 파일을 생성하고 다음 내용을 입력하세요:

```env
# Azure OpenAI 설정
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-vision-preview

# 데이터베이스 설정 (SQLite 사용)
DATABASE_URL=sqlite:///./analysis_history.db

# 기타 설정
UPLOAD_DIR=./uploads
```

**참고**: Grafana 설정은 이제 UI에서 직접 입력하므로 환경변수에서 제거되었습니다.

### 3. Grafana API 토큰 생성

1. Grafana 관리자 계정으로 로그인
2. Configuration → API Keys 메뉴로 이동
3. "Add API key" 클릭
4. 이름 입력 및 적절한 권한 설정 (Viewer 권한 이상)
5. 생성된 토큰을 UI에서 직접 입력

### 4. Azure OpenAI 설정

1. Azure Portal에서 OpenAI 리소스 생성
2. GPT-4 Vision 모델 배포
3. 엔드포인트 URL과 API 키를 `.env` 파일에 설정

## 🎯 사용법

### 1. FastAPI 백엔드 서버 실행

```bash
python main.py
```

서버가 성공적으로 실행되면 `http://localhost:8000`에서 API 문서를 확인할 수 있습니다.

### 2. Streamlit UI 실행

새 터미널에서 다음 명령을 실행하세요:

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501`로 접속하여 UI를 사용할 수 있습니다.

### 3. 대시보드 분석

1. **Grafana 서버 설정**:
   - Grafana 서버 URL 입력 (예: `http://1.255.144.202:8443`)
   - API 토큰 입력 (예: `token`)

2. **대시보드 설정**:
   - 대시보드 UID 입력 (예: `aaaa`)
   - 대시보드 이름 입력 (선택사항, 예: `dashboard`)
   - 조직 ID 설정 (기본값: 1)
   - 시간 범위 설정 (프리셋 또는 사용자 정의)
   - 캡처 해상도 설정

3. **AI 분석 설정**:
   - 프롬프트 템플릿 선택 또는 사용자 정의 프롬프트 입력

4. **분석 실행**:
   - "🚀 그라파나 분석 실행" 버튼 클릭
   - 자동으로 캡처 → AI 분석 → 결과 저장 과정 수행

## 📊 프롬프트 템플릿

시스템은 다양한 분석 목적에 맞는 프롬프트 템플릿을 제공합니다:

### 기본 제공 템플릿

- **기본 분석**: 전반적인 메트릭 및 인사이트 분석
- **성능 분석**: 성능 병목지점 및 최적화 포인트 분석
- **장애 분석**: 이상 징후 및 장애 원인 분석
- **트렌드 분석**: 데이터 트렌드 및 예측 분석
- **보안 분석**: 보안 관련 메트릭 및 위협 분석
- **용량 계획**: 리소스 사용량 및 확장 계획 분석

### 템플릿 커스터마이징

- `prompts/` 폴더의 텍스트 파일에서 템플릿 수정 및 추가 가능
- 사용자 정의 프롬프트 직접 입력 지원
- 템플릿 내용은 UI에서 미리보기 없이 직접 파일 편집

### 새로운 템플릿 추가 방법

1. `prompts/` 폴더에 새 텍스트 파일 생성 (예: `새로운_분석.txt`)
2. `prompt_manager.py`의 `TEMPLATE_INFO` 딕셔너리에 새 템플릿 정보 추가
3. Streamlit 앱 재시작
4. UI에서 새 템플릿 선택 가능

예시:
```python
# prompt_manager.py에 추가
"새로운_분석.txt": {
    "name": "새로운 분석",
    "description": "새로운 분석 목적에 맞는 템플릿"
}
```

### 파일 구조

```
prompts/
├── 기본_분석.txt
├── 성능_분석.txt
├── 장애_분석.txt
├── 트렌드_분석.txt
├── 보안_분석.txt
└── 용량_계획.txt
```

## 🔗 API 엔드포인트

### FastAPI 백엔드 API

- `GET /`: API 상태 확인
- `POST /capture-dashboard`: 대시보드 캡처
- `POST /analyze-image`: 이미지 분석
- `POST /analyze-dashboard`: 통합 분석 (캡처 + 분석)
  - Parameters: `grafana_url`, `api_token`, `dashboard_uid`, `dashboard_name`, `org_id`, `time_from`, `time_to`, `width`, `height`, `prompt_template`
- `GET /analysis-history`: 분석 이력 조회
- `GET /analysis/{analysis_id}`: 특정 분석 결과 조회

### 지원되는 Grafana API 형식

제공해주신 예제와 같은 형식을 지원합니다:
```bash


## 🗄️ 데이터베이스 스키마

```sql
CREATE TABLE analysis_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dashboard_uid TEXT NOT NULL,
    grafana_url TEXT NOT NULL,
    image_path TEXT NOT NULL,
    prompt_template TEXT NOT NULL,
    analysis_result TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔧 트러블슈팅

### 일반적인 문제

1. **Grafana 연결 오류**:
   - Grafana URL과 API 토큰이 올바른지 확인
   - 네트워크 연결 및 방화벽 설정 확인

2. **Azure OpenAI 오류**:
   - API 키와 엔드포인트 URL 확인
   - 배포된 모델명이 올바른지 확인
   - 요청 제한(Rate Limit) 확인

3. **이미지 캡처 실패**:
   - Grafana 서버 URL이 올바른지 확인
   - 대시보드 UID가 존재하는지 확인
   - 조직 ID가 올바른지 확인

### 로그 확인

FastAPI 서버 콘솔에서 상세한 오류 로그를 확인할 수 있습니다.

## 📝 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다.

## 🤝 기여

버그 리포트, 기능 요청, 또는 풀 리퀘스트를 환영합니다!
