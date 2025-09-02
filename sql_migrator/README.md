# Mybatis SQL 변환기 (Oracle to PostgreSQL)

Oracle DB 기준의 Mybatis XML 쿼리를 PostgreSQL로 자동 변환하는 도구입니다.

## 🚀 주요 기능

### v3.0 새로운 기능
- **변환 방식 선택**: 자체 로직과 LLM 기반 변환 중 선택 가능
- **모듈화된 구조**: 변환 로직을 별도 파일로 분리하여 재사용성 향상
- **XML 파일 전체 업로드**: Mybatis XML 파일을 업로드하면 모든 쿼리를 자동으로 파싱
- **ID별 접기/펼치기**: 각 쿼리 ID별로 결과를 접었다 펴는 방식으로 깔끔하게 표시
- **일괄 변환**: 업로드된 모든 쿼리를 한 번에 변환
- **LLM 질의 제한**: 비용 절약을 위해 `.env`의 `llm_query_id_limit` 설정으로 AI 검증 제한

### 기존 기능
- Oracle SQL을 PostgreSQL로 자동 변환
- Mybatis 동적 태그 지원 (`<if>`, `<foreach>`, `<trim>` 등)
- Oracle 전용 함수 자동 변환 (SYSDATE → CURRENT_TIMESTAMP 등)
- AI 기반 문법 검증 및 개선 제안
- 경고 및 주의사항 자동 탐지

## 📁 파일 구조

```
sql_migrator/
├── app.py              # 메인 애플리케이션 (UI 및 제어 로직)
├── converter.py        # 변환 로직 모듈 (자체 로직 + LLM 변환)
├── requirements.txt    # Python 의존성 목록
├── env_example.txt     # 환경 변수 설정 예시
└── README.md           # 이 파일
```

## ⚙️ 환경 변수 설정

`env_example.txt`를 `.env`로 복사하고 필요한 값들을 설정하세요:

```bash
# AI 모델 설정
AI_DEPLOY_MODEL=gpt-4
AI_API_KEY=your_api_key_here
AI_ENDPOINT=https://api.openai.com/v1/chat/completions

# LLM 질의 제한 설정 (비용 절약)
llm_query_id_limit=5
```

## 🚀 사용 방법

### 1. 변환 방식 선택
- **자체 로직**: 빠르고 안정적인 변환 (기본값)
- **LLM**: 더 정확하고 지능적인 변환 (API 비용 발생)

### 2. XML 파일 업로드 방식 (권장)
1. 사이드바에서 "XML 파일 업로드" 선택
2. 변환 방식 선택 (자체 로직 또는 LLM)
3. Mybatis XML 파일 업로드
4. 자동으로 모든 쿼리 파싱
5. "모든 쿼리 변환하기" 버튼 클릭
6. 각 쿼리 ID별로 결과 확인 (접기/펼치기 가능)
7. "AI 검증 시작" 버튼으로 문법 검증

### 3. 직접 입력 방식
1. 사이드바에서 "직접 입력" 선택
2. 변환 방식 선택 (자체 로직 또는 LLM)
3. 텍스트 영역에 단일 쿼리 입력
4. "변환하기" 버튼 클릭
5. 변환 결과 및 AI 검증 결과 확인

## 🔍 지원하는 쿼리 타입

- `SELECT` - 조회 쿼리
- `INSERT` - 삽입 쿼리
- `UPDATE` - 수정 쿼리
- `DELETE` - 삭제 쿼리

## ⚠️ 주의사항

- **LLM 질의 제한**: 기본적으로 최대 5개 쿼리만 AI 검증 (비용 절약)
- **복잡한 Oracle 기능**: CONNECT BY, DBMS 패키지 등은 수동 검토 필요
- **동적 태그**: Mybatis 동적 태그는 자동으로 보존되며 변환 후 복원

## 🔧 문제 해결

### LLM API 400 오류 발생 시
1. **환경 변수 확인**: `.env` 파일의 API 키와 엔드포인트가 올바른지 확인
2. **Azure OpenAI 사용 시**: 
   - `AI_ENDPOINT`는 리소스 URL만 입력 (예: `https://your-resource.openai.azure.com/`)
   - `AI_DEPLOY_MODEL`은 실제 배포된 모델 이름과 동일해야 함
   - **gpt-5-mini 모델**: `max_completion_tokens` 사용 (기존 `max_tokens` 아님), `temperature`, `top_p`, `frequency_penalty`, `presence_penalty` 설정 불가 (기본값만 사용)
3. **OpenAI API 사용 시**: 
   - `AI_ENDPOINT`는 `https://api.openai.com/v1/chat/completions`
   - `AI_DEPLOY_MODEL`은 `gpt-4`, `gpt-3.5-turbo` 등
4. **API 키 확인**: Azure Portal 또는 OpenAI 대시보드에서 API 키 유효성 확인

## 🛠️ 설치 및 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 애플리케이션 실행
streamlit run app.py
```

## 📝 변경 이력

### v3.0
- 변환 방식 선택 기능 추가 (자체 로직 vs LLM)
- 변환 로직을 별도 모듈로 분리하여 재사용성 향상
- 모듈화된 구조로 유지보수성 개선

### v2.0
- XML 파일 전체 업로드 기능 추가
- ID별 접기/펼치기 UI 구현
- LLM 질의 제한 기능 추가
- 일괄 변환 기능 구현

### v1.5
- 기본 변환 기능
- AI 검증 기능
- 경고 및 주의사항 탐지
