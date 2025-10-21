# Redis 슬롯 분석 프로그램

Excel 파일의 `stb_id` 컬럼을 기반으로 Redis 슬롯을 계산하고, Redis 서버 정보를 추가하는 프로그램입니다.

## 기능

- `stb_id` 값을 기반으로 Redis 클러스터 슬롯 번호 계산 (CRC16 해시 사용)
- 계산된 슬롯 번호를 G 컬럼에 저장
- 슬롯 번호에 따른 Redis 서버 정보를 H 컬럼에 저장
- 결과를 새로운 Excel 파일로 저장

## 설치

필요한 패키지를 설치합니다:

```bash
pip install -r requirements.txt
```

## 사용법

```bash
python redis_slot_analyzer.py <excel_file_path>
```

### 예시

```bash
python redis_slot_analyzer.py data.xlsx
python redis_slot_analyzer.py /path/to/your/data.xlsx
```

## 입력 요구사항

- Excel 파일에 `stb_id` 컬럼이 있어야 합니다
- 지원하는 파일 형식: .xlsx

## 출력

- 입력 파일과 같은 디렉토리에 결과 파일이 생성됩니다
- 파일명 형식: `Redis Timeout분석결과(발생일자 YYYY-MM-DD).xlsx`
- G 컬럼: Redis 슬롯 번호 (0-16383)
- H 컬럼: Redis 서버 정보 (redis 1~6 또는 error)

## Redis 서버 매핑

| 슬롯 범위 | Redis 서버 |
|-----------|------------|
| 0 ~ 2730 | redis 1 |
| 2731 ~ 5460 | redis 2 |
| 5461 ~ 8191 | redis 3 |
| 8192 ~ 10922 | redis 4 |
| 10923 ~ 13652 | redis 5 |
| 13653 ~ 16383 | redis 6 |

## 주의사항

- `stb_id` 값이 비어있거나 유효하지 않은 경우 "error"로 표시됩니다
- Redis 클러스터의 표준 CRC16 해시 알고리즘을 사용합니다
