from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import sqlite3
import json
from datetime import datetime
from typing import Optional, List
import httpx
import base64
from pathlib import Path
import asyncio
from pydantic import BaseModel
from dotenv import load_dotenv
import logging

# Python 3.10+ 호환성 패치
import sys
if sys.version_info >= (3, 10):
    import collections.abc
    collections.MutableSet = collections.abc.MutableSet
    collections.MutableMapping = collections.abc.MutableMapping
    collections.MutableSequence = collections.abc.MutableSequence

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Grafana Dashboard Analyzer", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 환경변수
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4-vision-preview")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./analysis_history.db")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

# 환경변수 확인 로그
logger.info(f"Azure OpenAI Endpoint: {AZURE_OPENAI_ENDPOINT}")
logger.info(f"Azure OpenAI API Key: {'설정됨' if AZURE_OPENAI_API_KEY else '설정되지 않음'}")
logger.info(f"Azure OpenAI Deployment: {AZURE_OPENAI_DEPLOYMENT_NAME}")

# 필수 환경변수 확인
if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY:
    logger.error("Azure OpenAI 환경변수가 설정되지 않았습니다!")
    logger.error("AZURE_OPENAI_ENDPOINT와 AZURE_OPENAI_API_KEY를 .env 파일에 설정해주세요.")

# 업로드 디렉토리 생성
Path(UPLOAD_DIR).mkdir(exist_ok=True)

# Pydantic 모델들
class GrafanaCaptureRequest(BaseModel):
    grafana_url: str
    api_token: str
    dashboard_uid: str
    dashboard_name: Optional[str] = None
    org_id: int = 1
    time_from: str = "now-1h"
    time_to: str = "now"
    width: int = 1920
    height: int = 1080

class AnalysisRequest(BaseModel):
    image_path: str
    prompt_template: str = "이 Grafana 대시보드 이미지를 분석하고 주요 메트릭과 인사이트를 제공해주세요."

class AnalysisResponse(BaseModel):
    id: int
    dashboard_uid: str
    analysis_result: str
    created_at: str
    image_path: str

# 데이터베이스 초기화
def init_database():
    """SQLite 데이터베이스 초기화"""
    conn = sqlite3.connect(DATABASE_URL.replace("sqlite:///", ""))
    cursor = conn.cursor()
    
    # 테이블이 없을 때만 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dashboard_uid TEXT NOT NULL,
            grafana_url TEXT NOT NULL,
            image_path TEXT NOT NULL,
            prompt_template TEXT NOT NULL,
            analysis_result TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    logger.info("데이터베이스 테이블 확인 완료 (없으면 생성).")
    
    conn.commit()
    conn.close()

# 시작시 데이터베이스 초기화
init_database()

async def capture_grafana_dashboard(request: GrafanaCaptureRequest) -> str:
    """Grafana 대시보드 캡처"""
    try:
        # URL 정규화 (끝의 슬래시 제거)
        base_url = request.grafana_url.rstrip('/')
        
        # Grafana 렌더링 API URL 구성 (제공된 예제 형식에 맞춤)
        if request.dashboard_name:
            render_url = f"{base_url}/render/d/{request.dashboard_uid}/{request.dashboard_name}"
        else:
            render_url = f"{base_url}/render/d/{request.dashboard_uid}"
        
        params = {
            "orgId": request.org_id,
            "width": request.width,
            "height": request.height
        }
        
        # 시간 범위가 기본값이 아닌 경우에만 추가
        if request.time_from != "now-1h" or request.time_to != "now":
            params["from"] = request.time_from
            params["to"] = request.time_to
            
        headers = {
            "Authorization": f"Bearer {request.api_token}"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(render_url, params=params, headers=headers)
            response.raise_for_status()
            
            # 이미지 파일 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"grafana_{request.dashboard_uid}_{timestamp}.png"
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            with open(file_path, "wb") as f:
                f.write(response.content)
                
            logger.info(f"Grafana 대시보드 캡처 완료: {file_path}")
            return file_path
            
    except Exception as e:
        logger.error(f"Grafana 캡처 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Grafana 캡처 실패: {str(e)}")

async def analyze_image_with_openai(image_path: str, prompt: str) -> str:
    """Azure OpenAI를 사용한 이미지 분석 (단일 시도 + 필요 시 1회 재시도)"""
    try:
        # 이미지를 base64로 인코딩
        with open(image_path, "rb") as image_file:
            raw_bytes = image_file.read()
            image_data = base64.b64encode(raw_bytes).decode()
        try:
            logger.info(f"보낸 프롬프트 길이: {len(prompt)} / 미리보기: {prompt[:120].replace('\n',' ')}...")
            logger.info(f"보낸 이미지 크기(bytes): {len(raw_bytes)} / base64 길이: {len(image_data)}")
        except Exception:
            pass
        
        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_OPENAI_API_KEY
        }

        # 공통 URL
        base_endpoint = AZURE_OPENAI_ENDPOINT.rstrip('/')
        url = f"{base_endpoint}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT_NAME}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"
        logger.info(f"OpenAI API 호출 URL: {url}")
        logger.info(f"OpenAI API 배포명: {AZURE_OPENAI_DEPLOYMENT_NAME}")

        # system 메시지(안전 단서 - 간결 유지)
        system_msg = {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "당신은 친절하고 전문적인 데이터 분석가입니다. "
                        "응답은 한국어로, 사용자가 이해하기 쉬운 어조로 작성하세요. "
                        "민감정보(개인정보, 비밀키 등)는 분석하지 않습니다. "
                        "가능하면 섹션을 나눠 체계적으로 설명하고, 불필요한 사족은 피하세요."
                    )
                }
            ]
        }

        # 과도한 출력 방지용 제약을 자동 부가
        prompt_base = (prompt or "").strip()
        concise_suffix = (
            "\n\n형식: # 개요 → # 핵심 지표 관찰 → # 주요 인사이트 → # 원인 가설 → # 권장 조치 → # 다음 단계. "
            "톤: 친절하고 체계적, 불릿과 간단한 소제목 활용. "
            "제약: 최대 1200자 내로 요약하되, 핵심은 빠뜨리지 마세요. 표/코드블록은 사용하지 마세요."
        )
        prompt_compact = f"{prompt_base}{concise_suffix}" if prompt_base else "분석해줘 (친절하고 체계적, 최대 1200자)"

        # 단일 기본 페이로드 (image_url + text)
        payload = {
            "messages": [
                system_msg,
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_compact},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}", "detail": "high"}}
                    ]
                }
            ],
            "max_completion_tokens": 6000,
            "response_format": {"type": "text"}
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            logger.info(f"[single] OpenAI 응답 상태: {resp.status_code}")
            if resp.status_code != 200:
                logger.error(f"[single] OpenAI 에러: {resp.text[:800]}")
                # 이미지 미지원 시 텍스트 대체
                if "vision" in (resp.text or "").lower() or "image" in (resp.text or "").lower():
                    logger.warning("모델이 이미지 입력을 처리하지 못함. 텍스트 기반 분석으로 전환합니다.")
                    return await analyze_text_fallback(prompt)
                resp.raise_for_status()
            result = resp.json()

        # 구조 로깅
        try:
            choices = result.get('choices', [])
            logger.info(f"choices 길이: {len(choices)}")
            if choices:
                msg = choices[0].get('message', {})
                logger.info(f"message 키들: {list(msg.keys())}")
                content_raw = msg.get('content')
                logger.info(f"content 원형 타입: {type(content_raw).__name__}")
                if isinstance(content_raw, str):
                    logger.info(f"content 문자열 길이: {len(content_raw)} / 미리보기: {content_raw[:160]}...")
                finish_reason = choices[0].get('finish_reason')
                if finish_reason:
                    logger.info(f"finish_reason: {finish_reason}")
        except Exception:
            pass

        # 콘텐츠 추출
        analysis_result = ""
        try:
            choice0 = (result.get("choices") or [{}])[0]
            message = choice0.get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                analysis_result = content
            elif isinstance(content, list):
                parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") in ("text", "output_text") and isinstance(part.get("text"), str):
                        parts.append(part["text"])
                analysis_result = "\n".join(p for p in parts if p)
            else:
                analysis_result = json.dumps(message, ensure_ascii=False)
        except Exception as parse_err:
            logger.error(f"OpenAI 응답 파싱 오류: {parse_err}")
            analysis_result = ""

        logger.info("OpenAI 이미지 분석 완료")
        logger.info(f"분석 결과 길이: {len(analysis_result) if analysis_result else 0}")
        logger.info(f"분석 결과 미리보기: {analysis_result[:200] if analysis_result else 'None 또는 빈 결과'}...")

        # 빈 응답이고 length로 끊긴 경우 1회만 더 짧게 재시도
        try:
            if (not analysis_result or len(analysis_result.strip()) < 10):
                choice0 = (result.get("choices") or [{}])[0]
                if choice0.get("finish_reason") == "length":
                    logger.info("finish_reason=length → 1회 짧은 재시도")
                    shorter_prompt = (prompt_base + "\n\n형식: 개요, 인사이트, 조치 3개 불릿. 제약: 최대 600자.").strip() or "분석해줘 (최대 600자, 3불릿)"
                    payload_retry = {
                        "messages": [
                            system_msg,
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": shorter_prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}", "detail": "high"}}
                                ]
                            }
                        ],
                        "max_completion_tokens": 3000,
                        "response_format": {"type": "text"}
                    }
                    async with httpx.AsyncClient(timeout=90.0) as client:
                        resp2 = await client.post(url, headers=headers, json=payload_retry)
                        logger.info(f"[retry_short] 상태: {resp2.status_code}")
                        if resp2.status_code == 200:
                            r2 = resp2.json()
                            try:
                                content2 = ((r2.get("choices") or [{}])[0].get("message") or {}).get("content")
                                if isinstance(content2, str) and content2.strip():
                                    return content2
                            except Exception:
                                pass
                        else:
                            logger.error(f"[retry_short] 에러: {resp2.text[:800]}")
        except Exception:
            pass

        # 빈 응답이면 원문 일부 반환하여 원인 가시화, 마지막으로 텍스트 대체
        if not analysis_result or len(analysis_result.strip()) < 10:
            try:
                raw_preview = json.dumps(result, ensure_ascii=False)
                logger.warning(f"빈 응답 발생, 원문 미리보기: {raw_preview[:1200]}")
                return "[원문 응답 미리보기]\n" + raw_preview[:4000]
            except Exception:
                logger.warning("원문 직렬화 실패, 텍스트 기반 분석으로 전환")
                return await analyze_text_fallback(prompt)

        return analysis_result

    except Exception as e:
        logger.error(f"OpenAI 분석 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OpenAI 분석 실패: {str(e)}")

async def analyze_text_fallback(prompt: str) -> str:
    """이미지 분석이 지원되지 않는 경우 텍스트 기반 대안 분석"""
    try:
        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_OPENAI_API_KEY
        }
        
        fallback_prompt = f"""
        {prompt}
        
        참고: 이미지를 직접 분석할 수 없어 Grafana 대시보드의 일반적인 분석 가이드를 제공합니다.
        
        Grafana 대시보드 분석 시 확인해야 할 주요 요소들:
        1. 시스템 리소스 사용률 (CPU, 메모리, 디스크)
        2. 네트워크 트래픽 패턴
        3. 응답 시간 및 지연률
        4. 에러율 및 실패한 요청
        5. 시간대별 트렌드 변화
        """
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": fallback_prompt
                }
            ],
            "max_completion_tokens": 2000
        }
        
        base_endpoint = AZURE_OPENAI_ENDPOINT.rstrip('/')
        url = f"{base_endpoint}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT_NAME}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            analysis_result = result["choices"][0]["message"]["content"]
            
            logger.info("OpenAI 텍스트 기반 분석 완료")
            return analysis_result
            
    except Exception as e:
        logger.error(f"텍스트 분석 오류: {str(e)}")
        return f"분석 중 오류가 발생했습니다: {str(e)}"

def save_analysis_to_db(dashboard_uid: str, grafana_url: str, image_path: str, prompt: str, analysis_result: str) -> int:
    """분석 결과를 데이터베이스에 저장"""
    try:
        conn = sqlite3.connect(DATABASE_URL.replace("sqlite:///", ""))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO analysis_history (dashboard_uid, grafana_url, image_path, prompt_template, analysis_result)
            VALUES (?, ?, ?, ?, ?)
        """, (dashboard_uid, grafana_url, image_path, prompt, analysis_result))
        
        analysis_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"분석 결과 저장 완료: ID {analysis_id}")
        return analysis_id
        
    except Exception as e:
        logger.error(f"데이터베이스 저장 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"데이터베이스 저장 실패: {str(e)}")

@app.get("/")
async def root():
    """API 상태 확인"""
    return {"message": "Grafana Dashboard Analyzer API", "status": "running"}

@app.post("/capture-dashboard")
async def capture_dashboard(request: GrafanaCaptureRequest):
    """Grafana 대시보드 캡처"""
    try:
        image_path = await capture_grafana_dashboard(request)
        return {
            "success": True,
            "image_path": image_path,
            "message": "대시보드 캡처 성공"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-image")
async def analyze_image(request: AnalysisRequest):
    """이미지 분석"""
    try:
        if not os.path.exists(request.image_path):
            raise HTTPException(status_code=404, detail="이미지 파일을 찾을 수 없습니다.")
            
        analysis_result = await analyze_image_with_openai(request.image_path, request.prompt_template)
        return {
            "success": True,
            "analysis_result": analysis_result,
            "message": "이미지 분석 성공"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-uploaded-image")
async def analyze_uploaded_image(
    file: UploadFile = File(...),
    prompt_template: str = Form(None)
):
    """업로드된 이미지 분석"""
    try:
        # 파일 확장자 검증
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            raise HTTPException(status_code=400, detail="지원되지 않는 파일 형식입니다. PNG, JPG, JPEG, GIF, BMP 파일만 업로드 가능합니다.")
        
        # 파일 크기 검증 (10MB 제한)
        if file.size > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="파일 크기가 너무 큽니다. 10MB 이하의 파일만 업로드 가능합니다.")
        
        # 업로드된 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"uploaded_{timestamp}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"업로드된 이미지 저장 완료: {file_path}")
        
        # 프롬프트 미제공 시 기본값 사용
        effective_prompt = (prompt_template or "").strip() or "이 Grafana 대시보드 이미지를 분석하고 주요 메트릭과 인사이트를 제공해주세요."

        # 이미지 분석
        analysis_result = await analyze_image_with_openai(file_path, effective_prompt)
        
        # 결과 저장 (dashboard_uid는 "uploaded"로 설정)
        analysis_id = save_analysis_to_db("uploaded", "uploaded_image", file_path, effective_prompt, analysis_result)
        
        return {
            "success": True,
            "analysis_id": analysis_id,
            "dashboard_uid": "uploaded",
            "image_path": file_path,
            "analysis_result": analysis_result,
            "message": "업로드된 이미지 분석 완료"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"업로드된 이미지 분석 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"이미지 분석 실패: {str(e)}")

@app.post("/analyze-dashboard")
async def analyze_dashboard(
    grafana_url: str,
    api_token: str,
    dashboard_uid: str,
    dashboard_name: Optional[str] = None,
    org_id: int = 1,
    time_from: str = "now-1h",
    time_to: str = "now",
    width: int = 1920,
    height: int = 1080,
    prompt_template: str = "이 Grafana 대시보드 이미지를 분석하고 주요 메트릭과 인사이트를 제공해주세요."
):
    """Grafana 대시보드 캡처 + 분석 통합 API"""
    try:
        # 1. 대시보드 캡처
        capture_request = GrafanaCaptureRequest(
            grafana_url=grafana_url,
            api_token=api_token,
            dashboard_uid=dashboard_uid,
            dashboard_name=dashboard_name,
            org_id=org_id,
            time_from=time_from,
            time_to=time_to,
            width=width,
            height=height
        )
        
        image_path = await capture_grafana_dashboard(capture_request)
        
        # 2. 이미지 분석
        analysis_result = await analyze_image_with_openai(image_path, prompt_template)
        
        # 3. 결과 저장
        analysis_id = save_analysis_to_db(dashboard_uid, grafana_url, image_path, prompt_template, analysis_result)
        
        return {
            "success": True,
            "analysis_id": analysis_id,
            "dashboard_uid": dashboard_uid,
            "image_path": image_path,
            "analysis_result": analysis_result,
            "message": "대시보드 분석 완료"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analysis-history")
async def get_analysis_history(limit: int = 10, offset: int = 0):
    """분석 이력 조회"""
    try:
        conn = sqlite3.connect(DATABASE_URL.replace("sqlite:///", ""))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, dashboard_uid, grafana_url, image_path, prompt_template, analysis_result, created_at
            FROM analysis_history
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                "id": row[0],
                "dashboard_uid": row[1],
                "grafana_url": row[2],
                "image_path": row[3],
                "prompt_template": row[4],
                "analysis_result": row[5],
                "created_at": row[6]
            })
            
        return {
            "success": True,
            "history": history,
            "count": len(history)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analysis/{analysis_id}")
async def get_analysis_by_id(analysis_id: int):
    """특정 분석 결과 조회"""
    try:
        conn = sqlite3.connect(DATABASE_URL.replace("sqlite:///", ""))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, dashboard_uid, grafana_url, image_path, prompt_template, analysis_result, created_at
            FROM analysis_history
            WHERE id = ?
        """, (analysis_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다.")
            
        return {
            "success": True,
            "analysis": {
                "id": row[0],
                "dashboard_uid": row[1],
                "grafana_url": row[2],
                "image_path": row[3],
                "prompt_template": row[4],
                "analysis_result": row[5],
                "created_at": row[6]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
