# RAG ChromaDB 시스템

Flask 기반의 RAG (Retrieval-Augmented Generation) 웹 애플리케이션입니다. ChromaDB를 사용하여 URL과 파일에서 정보를 추출하고 벡터 데이터베이스에 저장합니다.

## 주요 기능

- 🌐 **URL 콘텐츠 추출 및 저장**: 여러 URL에서 동시에 콘텐츠 추출
- 📁 **파일 업로드 지원**: PDF, Word, PowerPoint, Excel, 텍스트 파일 등 다양한 형식 지원
- 🔍 **유사도 검색**: 자연어 쿼리로 저장된 콘텐츠 검색
- ⚙️ **청킹 옵션 설정**: 청크 크기와 오버랩 설정 가능
- 🔄 **중복 방지**: 이미 처리된 URL 자동 감지
- 🗑️ **데이터베이스 관리**: 초기화 및 통계 확인 기능

## 설치 방법

### 1. 환경 설정

Python 3.8 이상이 필요합니다.

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 입력합니다:

```env
# OpenAI API 엔드포인트
ENDPOINT=https://api.openai.com/v1/

# OpenAI API 키
API_KEY=your-api-key-here

# 임베딩 모델
DEPLOY_EMBED=text-embedding-ada-002

# ChromaDB 저장 경로 (상대경로)
CHROMA_DB_PATH=./chroma_db

# 모델 이름
DEPLOY_MODEL_NAME=gpt-3.5-turbo

# 모델 버전
DEPLOY_MODEL_VERSION=latest
```

### 3. 애플리케이션 실행

```bash
python app.py
```

브라우저에서 `http://localhost:5000` 접속

## 사용 방법

### URL 추가하기

1. URL 입력란에 한 줄에 하나씩 URL 입력
2. 필요시 고급 옵션에서 청킹 설정 조정
3. "추출 후 저장" 버튼 클릭

### 파일 업로드하기

1. "파일 선택" 버튼 클릭
2. 지원되는 파일 형식 선택 (PDF, DOCX, PPTX, XLSX, TXT 등)
3. "추출 후 저장" 버튼 클릭

### 유사도 검색

1. 검색어 입력
2. 결과 개수 설정 (기본값: 5)
3. "유사도 검색" 버튼 클릭
4. 유사도 점수와 함께 결과 확인

## 지원 파일 형식

- PDF (.pdf)
- Word 문서 (.docx, .doc)
- PowerPoint (.pptx, .ppt)
- Excel (.xlsx, .xls)
- 텍스트 파일 (.txt, .md, .csv)

## API 엔드포인트

- `POST /api/process_urls` - URL 처리
- `POST /api/upload_files` - 파일 업로드 및 처리
- `POST /api/search` - 유사도 검색
- `POST /api/clear_database` - 데이터베이스 초기화
- `GET /api/stats` - 통계 정보 조회
- `GET /api/supported_formats` - 지원 파일 형식 조회

## 주요 설정

### 청킹 옵션

- **청크 크기**: 각 텍스트 조각의 최대 문자 수 (기본값: 1000)
- **청크 오버랩**: 인접 청크 간 중복 문자 수 (기본값: 200)

### 데이터베이스 경로

`.env` 파일의 `CHROMA_DB_PATH` 변수로 설정 (기본값: `./chroma_db`)

## 문제 해결

### OpenAI API 키 오류

`.env` 파일의 `API_KEY`가 올바르게 설정되었는지 확인하세요.

### 메모리 부족

대용량 파일 처리 시 청크 크기를 줄이거나 파일을 분할하여 처리하세요.

### URL 접근 실패

- 대상 웹사이트가 접근 가능한지 확인
- 방화벽이나 프록시 설정 확인

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
