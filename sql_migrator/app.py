import streamlit as st
import re
import os
import requests
import json
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from xml.etree import ElementTree as ET
from dotenv import load_dotenv
from converter import convert_with_self_logic, convert_with_llm, format_xml_consistently, extract_pure_sql_from_xml

# 환경 변수 로드
load_dotenv()

# 디버그 로그 헬퍼
def debug_log(message: str) -> None:
    if st.session_state.get('debug_enabled', False):
        st.info(message)

# --- XML 포맷팅 함수 ---
def format_xml_consistently(xml_content):
    """
    XML의 들여쓰기와 개행을 일관된 형태로 포맷팅합니다.
    """
    try:
        # XML 파싱
        root = ET.fromstring(xml_content)
        
        # 일관된 들여쓰기로 XML 재생성
        def indent(elem, level=0):
            i = "\n" + level * "    "
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + "    "
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for child in elem:
                    indent(child, level + 1)
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
        
        indent(root)
        
        # 문자열로 변환
        formatted_xml = ET.tostring(root, encoding='unicode')
        
        # Mybatis 태그들의 일관된 포맷팅
        formatted_xml = re.sub(r'>\s*\n\s*<', '>\n        <', formatted_xml)
        formatted_xml = re.sub(r'>\s*([^<]+)\s*<', r'>\n            \1\n        <', formatted_xml)
        
        # 특정 태그들의 포맷팅 개선
        formatted_xml = re.sub(r'(<select[^>]*>)\s*\n', r'\1\n        ', formatted_xml)
        formatted_xml = re.sub(r'(<insert[^>]*>)\s*\n', r'\1\n        ', formatted_xml)
        formatted_xml = re.sub(r'(<update[^>]*>)\s*\n', r'\1\n        ', formatted_xml)
        formatted_xml = re.sub(r'(<delete[^>]*>)\s*\n', r'\1\n        ', formatted_xml)
        
        # 닫는 태그 포맷팅
        formatted_xml = re.sub(r'\n\s*(</select>)', r'\n    \1', formatted_xml)
        formatted_xml = re.sub(r'\n\s*(</insert>)', r'\n    \1', formatted_xml)
        formatted_xml = re.sub(r'\n\s*(</update>)', r'\n    \1', formatted_xml)
        formatted_xml = re.sub(r'\n\s*(</delete>)', r'\n    \1', formatted_xml)
        
        return formatted_xml
        
    except Exception as e:
        # XML 파싱 실패 시 기본 포맷팅 적용
        # 줄바꿈 정리
        formatted_xml = re.sub(r'\n\s*\n', '\n', xml_content)
        # 들여쓰기 정리
        formatted_xml = re.sub(r'^\s+', '', formatted_xml, flags=re.MULTILINE)
        # 태그 사이 공백 정리
        formatted_xml = re.sub(r'>\s+<', '>\n<', formatted_xml)
        formatted_xml = re.sub(r'>\s+([^<])', '>\n        \1', formatted_xml)
        formatted_xml = re.sub(r'([^>])\s+<', '\1\n        <', formatted_xml)
        
        return formatted_xml

# --- XML 파싱 및 쿼리 추출 함수 ---
def parse_mybatis_xml(xml_content):
    """
    Mybatis XML 파일을 파싱하여 모든 쿼리 id와 내용을 추출합니다.
    """
    try:
        root = ET.fromstring(xml_content)
        queries = {}
        
        # select, insert, update, delete 태그 모두 찾기
        for tag_name in ['select', 'insert', 'update', 'delete']:
            for element in root.findall(f'.//{tag_name}'):
                query_id = element.get('id')
                if query_id:
                    # 전체 태그를 문자열로 변환
                    query_xml = ET.tostring(element, encoding='unicode')
                    queries[query_id] = {
                        'type': tag_name,
                        'xml': query_xml,
                        'converted': None,
                        'warnings': [],
                        'notes': []
                    }
        
        return queries
    except ET.ParseError as e:
        st.error(f"XML 파싱 오류: {e}")
        return {}
    except Exception as e:
        st.error(f"XML 처리 중 오류 발생: {e}")
        return {}

# --- 변환 방식 선택 및 실행 함수 ---
def convert_mybatis_xml(mybatis_xml, conversion_method):
    """
    선택된 변환 방식을 사용하여 Mybatis XML을 변환합니다.
    """
    try:
        if conversion_method == "자체 로직":
            debug_log("[변환] 자체 로직 변환 시작")
            return convert_with_self_logic(mybatis_xml)
        elif conversion_method == "LLM":
            debug_log("[변환] LLM 변환 시작")
            return convert_with_llm(mybatis_xml)
        else:
            raise ValueError(f"지원하지 않는 변환 방식: {conversion_method}")
    except Exception as e:
        debug_log(f"[변환] 변환 오류: {str(e)}")
        raise e

# --- 병렬 변환 함수 ---
def convert_queries_parallel(queries, conversion_method, max_workers=4):
    """
    여러 쿼리를 병렬로 변환합니다.
    """
    results = {}
    
    def convert_single_query(query_data):
        query_id, query_info = query_data
        try:
            converted_xml = convert_mybatis_xml(query_info['xml'], conversion_method)
            return query_id, {
                'type': query_info['type'],
                'xml': query_info['xml'],
                'converted': converted_xml,
                'warnings': [],
                'notes': []
            }
        except Exception as e:
            # Streamlit 컨텍스트 접근 제거
            return query_id, {
                'type': query_info['type'],
                'xml': query_info['xml'],
                'converted': None,
                'warnings': [f"변환 실패: {str(e)}"],
                'notes': []
            }
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 변환 작업 제출
        future_to_query = {
            executor.submit(convert_single_query, (query_id, query_info)): query_id 
            for query_id, query_info in queries.items()
        }
        
        # 진행상황 표시를 위한 변수
        completed = 0
        total = len(queries)
        
        # 완료된 작업 처리
        for future in as_completed(future_to_query):
            query_id = future_to_query[future]
            try:
                result_query_id, result_data = future.result()
                results[result_query_id] = result_data
                completed += 1
                
                # 진행상황 업데이트 (메인 스레드에서만)
                progress = completed / total
                st.progress(progress, text=f"변환 진행 중... ({completed}/{total})")
                
                # 완료된 쿼리 정보 표시 (메인 스레드에서만)
                if result_data['converted']:
                    st.success(f"✅ {result_query_id} 변환 완료")
                else:
                    st.error(f"❌ {result_query_id} 변환 실패")
                    
            except Exception as e:
                # Streamlit 컨텍스트 접근 제거
                results[query_id] = {
                    'type': queries[query_id]['type'],
                    'xml': queries[query_id]['xml'],
                    'converted': None,
                    'warnings': [f"처리 실패: {str(e)}"],
                    'notes': []
                }
                completed += 1
    
    return results

# --- 변환 로직 및 경고 분석 함수 ---
def convert_mybatis_xml(mybatis_xml, conversion_method):
    """
    선택된 변환 방식을 사용하여 Mybatis XML을 변환합니다.
    """
    try:
        if conversion_method == "자체 로직":
            debug_log("[변환] 자체 로직 변환 시작")
            return convert_with_self_logic(mybatis_xml)
        elif conversion_method == "LLM":
            debug_log("[변환] LLM 변환 시작")
            return convert_with_llm(mybatis_xml)
        else:
            raise ValueError(f"지원하지 않는 변환 방식: {conversion_method}")
    except Exception as e:
        debug_log(f"[변환] 변환 오류: {str(e)}")
        raise e

# --- LLM 검증 함수 ---
def validate_with_llm(converted_xml, max_retries=3):
    """
    변환된 PostgreSQL Mybatis XML을 LLM에 질의하여 검증하고 개선사항을 제안합니다.
    재시도 로직과 지연 시간을 포함합니다.
    """
    for attempt in range(max_retries):
        try:
            start_ts = time.perf_counter()
            debug_log(f"[LLM] 호출 시작 (시도 {attempt + 1}/{max_retries})")
            
            # 환경 변수 확인
            ai_deploy_model = os.getenv('AI_DEPLOY_MODEL')
            ai_api_key = os.getenv('AI_API_KEY')
            ai_endpoint = os.getenv('AI_ENDPOINT')
            ai_deploy_version = os.getenv('AI_DEPLOY_VERSION', '2023-12-01-preview')  # 기본값 설정
            
            if not all([ai_deploy_model, ai_api_key, ai_endpoint]):
                missing_vars = []
                if not ai_deploy_model:
                    missing_vars.append("AI_DEPLOY_MODEL")
                if not ai_api_key:
                    missing_vars.append("AI_API_KEY")
                if not ai_endpoint:
                    missing_vars.append("AI_ENDPOINT")
                
                error_msg = f"환경 변수가 설정되지 않았습니다. 누락된 변수: {', '.join(missing_vars)}"
                st.error(error_msg)
                return {ai_deploy_model or "Unknown": {"status": "error", "message": error_msg, "details": None}}
            
            # LLM에 전송할 프롬프트 구성
            prompt = f"""
당신은 PostgreSQL과 Mybatis 전문가입니다. 다음 변환된 PostgreSQL Mybatis XML의 문법 오류를 검증해주세요.

**변환된 PostgreSQL Mybatis XML:**
```xml
{converted_xml}
```

**검증 기준:**
- PostgreSQL 문법 오류가 있으면 수정된 XML 제공
- 문법 오류가 없으면 "정상 동작합니다" 응답
- 성능 최적화나 추가 권장사항은 제외

**응답 형식:**
- 문법 오류 없음: "정상 동작합니다"
- 문법 오류 있음: "문법 오류 발견: [간단한 설명]" + 수정된 XML
"""

            # API 호출을 위한 설정
            headers = {
                'Content-Type': 'application/json'
            }
            
            # Azure OpenAI와 OpenAI API 구분
            if 'azure' in ai_endpoint.lower():
                # Azure OpenAI
                headers['api-key'] = ai_api_key
                
                # API 엔드포인트 구성
                if not ai_endpoint.endswith('/'):
                    ai_endpoint += '/'
                if 'deployments' not in ai_endpoint:
                    azure_endpoint = f"{ai_endpoint}openai/deployments/{ai_deploy_model}/chat/completions?api-version={ai_deploy_version}"
                else:
                    azure_endpoint = ai_endpoint
                    
                # Azure OpenAI 요청 데이터 (기본)
                data = {
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_completion_tokens': 6000
                }
                
                # gpt-5-mini 모델이 아닌 경우에만 추가 매개변수 설정
                if 'gpt-5-mini' not in ai_deploy_model.lower():
                    data.update({
                        'temperature': 0.1,
                        'top_p': 0.95,
                        'frequency_penalty': 0,
                        'presence_penalty': 0
                    })
            else:
                # OpenAI API
                headers['Authorization'] = f'Bearer {ai_api_key}'
                azure_endpoint = ai_endpoint
                
                # OpenAI API 요청 데이터
                data = {
                    'model': ai_deploy_model,
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_tokens': 6000,
                    'temperature': 0.1,
                    'top_p': 0.95,
                    'frequency_penalty': 0,
                    'presence_penalty': 0
                }
            
            # 디버깅을 위한 요청 정보 출력
            debug_log(f"[LLM] Endpoint={azure_endpoint}")
            debug_log(f"[LLM] Model={ai_deploy_model}")
            debug_log(f"[LLM] Prompt length={len(prompt)} chars")
            debug_log(f"[LLM] Payload size ~{len(json.dumps(data))} bytes")
            
            # 콘솔에 전체 프롬프트 출력
            print(f"\n{'='*80}")
            print(f"[LLM REQUEST] Model: {ai_deploy_model}")
            print(f"[LLM REQUEST] Endpoint: {azure_endpoint}")
            print(f"{'='*80}")
            print(f"[LLM REQUEST] PROMPT:")
            print(f"{prompt}")
            print(f"{'='*80}")
            print(f"[LLM REQUEST] PAYLOAD:")
            print(f"{json.dumps(data, indent=2, ensure_ascii=False)}")
            print(f"{'='*80}")
            
            # API 호출
            response = requests.post(azure_endpoint, headers=headers, json=data, timeout=30)
            elapsed = (time.perf_counter() - start_ts) * 1000
            debug_log(f"[LLM] HTTP status={response.status_code}, elapsed={elapsed:.0f} ms")
            
            # 429 오류 (Too Many Requests) 처리
            if response.status_code == 429:
                retry_after = response.headers.get('Retry-After', 60)  # 기본값 60초
                wait_time = int(retry_after)
                
                if attempt < max_retries - 1:  # 마지막 시도가 아닌 경우
                    debug_log(f"[LLM] 429 오류 발생, {wait_time}초 후 재시도... (시도 {attempt + 1}/{max_retries})")
                    st.warning(f"⚠️ API 요청 제한에 도달했습니다. {wait_time}초 후 재시도합니다... (시도 {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    error_msg = f"API 요청 제한에 도달했습니다. {wait_time}초 후 다시 시도해주세요."
                    st.error(error_msg)
                    return {ai_deploy_model: {"status": "error", "message": error_msg, "details": None}}
            
            # 400 오류 시 상세 정보 출력
            if response.status_code == 400:
                try:
                    error_detail = response.json()
                    st.error(f"400 오류 상세 정보: {error_detail}")
                except:
                    st.error(f"400 오류 응답: {response.text[:500]}")
            
            response.raise_for_status()
            
            # 응답 내용 확인 및 디버깅
            try:
                result = response.json()
                llm_response = result['choices'][0]['message']['content']
                debug_log(f"[LLM] 응답 수신, content length={len(llm_response)} chars")
                
                # 콘솔에 전체 응답 출력
                print(f"\n{'='*80}")
                print(f"[LLM RESPONSE] Model: {ai_deploy_model}")
                print(f"[LLM RESPONSE] Status Code: {response.status_code}")
                print(f"[LLM RESPONSE] Response Time: {elapsed:.0f}ms")
                print(f"{'='*80}")
                print(f"[LLM RESPONSE] FULL JSON:")
                print(f"{json.dumps(result, indent=2, ensure_ascii=False)}")
                print(f"{'='*80}")
                print(f"[LLM RESPONSE] EXTRACTED CONTENT:")
                print(f"{llm_response}")
                print(f"{'='*80}")
            except json.JSONDecodeError as json_error:
                # JSON 파싱 실패 시 응답 내용을 로그로 출력
                st.error(f"API 응답이 JSON 형식이 아닙니다. 응답 내용: {response.text[:200]}...")
                return {ai_deploy_model: {"status": "error", "message": f"API 응답 파싱 오류: {str(json_error)}", "details": None}}
            except KeyError as key_error:
                # 응답 구조가 예상과 다를 때
                st.error(f"API 응답 구조가 예상과 다릅니다. 응답: {result}")
                return {ai_deploy_model: {"status": "error", "message": f"API 응답 구조 오류: {str(key_error)}", "details": None}}
            
            # 응답 분석 및 디버그 로그
            debug_log(f"[LLM] 응답 분석 시작: response_length={len(llm_response)}")
            debug_log(f"[LLM] 응답 내용 미리보기: {llm_response[:200]}...")
            
            # 응답이 비어있는지 확인
            if not llm_response or not llm_response.strip():
                debug_log(f"[LLM] 응답이 비어있음")
                return {ai_deploy_model: {"status": "error", "message": "LLM 응답이 비어있습니다.", "details": None}}
            
            if "정상 동작합니다" in llm_response:
                debug_log(f"[LLM] 정상 동작 응답 감지")
                return {ai_deploy_model: {"status": "success", "message": "정상 동작합니다", "details": None}}
            else:
                debug_log(f"[LLM] 문법 오류 또는 개선사항 응답 감지")
                
                # 개선된 XML 추출 시도 (diff 형식 포함)
                xml_match = re.search(r'```xml\s*(.*?)\s*```', llm_response, re.DOTALL)
                if xml_match:
                    improved_xml_content = xml_match.group(1).strip()
                    debug_log(f"[LLM] XML 코드 블록 발견: length={len(improved_xml_content)}")
                    
                    # XML 코드 블록을 제거한 메시지 생성
                    message_without_xml = re.sub(r'```xml\s*.*?\s*```', '', llm_response, flags=re.DOTALL).strip()
                    
                    # 메시지가 너무 짧으면 기본 설명 추가
                    if len(message_without_xml.strip()) < 20:
                        message_without_xml = "LLM이 PostgreSQL 문법 오류를 발견하고 수정된 쿼리를 제공했습니다."
                    
                    return {ai_deploy_model: {"status": "error", "message": message_without_xml, "details": improved_xml_content}}
                else:
                    # diff 형식으로 제공된 경우도 처리
                    diff_match = re.search(r'```diff\s*(.*?)\s*```', llm_response, re.DOTALL)
                    if diff_match:
                        debug_log(f"[LLM] Diff 코드 블록 발견")
                        # diff 코드 블록을 제거한 메시지 생성
                        message_without_diff = re.sub(r'```diff\s*.*?\s*```', '', llm_response, flags=re.DOTALL).strip()
                        return {ai_deploy_model: {"status": "error", "message": message_without_diff, "details": None}}
                    else:
                        debug_log(f"[LLM] 코드 블록 없음, 전체 응답을 메시지로 사용")
                        # LLM 응답을 정리하여 메시지로 사용
                        cleaned_response = llm_response.strip()
                        if len(cleaned_response) > 500:  # 너무 긴 응답은 축약
                            cleaned_response = cleaned_response[:500] + "..."
                        
                        # 응답이 실제로 의미있는 내용을 가지고 있는지 확인
                        if cleaned_response and len(cleaned_response.strip()) > 10:
                            debug_log(f"[LLM] 정리된 응답 사용: length={len(cleaned_response)}")
                            return {ai_deploy_model: {"status": "error", "message": cleaned_response, "details": None}}
                        else:
                            debug_log(f"[LLM] 응답이 너무 짧거나 의미없음, 기본 메시지 사용")
                            return {ai_deploy_model: {"status": "error", "message": "LLM이 문법 오류를 발견했지만 구체적인 설명을 제공하지 않았습니다.", "details": None}}
                        
        except requests.exceptions.RequestException as e:
            error_msg = f"API 호출 오류: {str(e)}"
            
            # 429 오류가 아닌 경우에만 재시도
            if "429" not in str(e) and attempt < max_retries - 1:
                debug_log(f"[LLM] API 호출 오류 발생, 재시도 중... (시도 {attempt + 1}/{max_retries})")
                st.warning(f"⚠️ API 호출 오류가 발생했습니다. 재시도 중... (시도 {attempt + 1}/{max_retries})")
                time.sleep(5)  # 5초 대기 후 재시도
                continue
            else:
                st.error(error_msg)
                return {ai_deploy_model or "Unknown": {"status": "error", "message": error_msg, "details": None}}
                
        except Exception as e:
            error_msg = f"LLM 검증 중 오류 발생: {str(e)}"
            st.error(error_msg)
            return {ai_deploy_model or "Unknown": {"status": "error", "message": error_msg, "details": None}}
    
    # 모든 재시도 실패
    error_msg = f"최대 재시도 횟수({max_retries})를 초과했습니다."
    st.error(error_msg)
    return {ai_deploy_model or "Unknown": {"status": "error", "message": error_msg, "details": None}}

# --- 병렬 AI 검증 함수 ---
def validate_queries_parallel(converted_queries, max_workers=3):
    """
    여러 쿼리를 병렬로 AI 검증합니다.
    재시도 로직과 지연 시간을 포함합니다.
    """
    results = {}
    
    def validate_single_query(query_data):
        query_id, query_info = query_data
        try:
            # 재시도 로직이 포함된 validate_with_llm 호출
            llm_results = validate_with_llm(query_info['converted'], max_retries=3)
            return query_id, llm_results
        except Exception as e:
            # Streamlit 컨텍스트 접근 제거
            return query_id, {
                "Unknown": {
                    "status": "error", 
                    "message": f"검증 실패: {str(e)}", 
                    "details": None
                }
            }
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 검증 작업 제출
        future_to_query = {
            executor.submit(validate_single_query, (query_id, query_info)): query_id 
            for query_id, query_info in converted_queries.items()
        }
        
        # 진행상황 표시를 위한 변수
        completed = 0
        total = len(converted_queries)
        
        # 완료된 작업 처리
        for future in as_completed(future_to_query):
            query_id = future_to_query[future]
            try:
                result_query_id, result_data = future.result()
                results[result_query_id] = result_data
                completed += 1
                
                # 진행상황 업데이트 (메인 스레드에서만)
                progress = completed / total
                st.progress(progress, text=f"AI 검증 진행 중... ({completed}/{total})")
                
                # 완료된 쿼리 정보 표시 (메인 스레드에서만)
                if result_data and any(result.get("status") == "success" for result in result_data.values()):
                    st.success(f"✅ {result_query_id} AI 검증 완료")
                else:
                    st.warning(f"⚠️ {result_query_id} AI 검증 완료 (문제 발견)")
                    
            except Exception as e:
                # Streamlit 컨텍스트 접근 제거
                results[query_id] = {
                    "Unknown": {
                        "status": "error", 
                        "message": f"처리 실패: {str(e)}", 
                        "details": None
                    }
                }
                completed += 1
    
    return results

# --- Streamlit UI 구성 ---
st.set_page_config(layout="wide", page_title="Mybatis SQL 변환기 (Oracle to PostgreSQL)")

st.title("🚀 Mybatis SQL 변환기")
st.caption("Oracle에서 PostgreSQL로! (v2.0)")

# 사이드바에 설정 옵션 추가
with st.sidebar:
    st.subheader("⚙️ 설정")
    
    # LLM 질의 제한 설정
    llm_query_limit = int(os.getenv('llm_query_id_limit', 5))
    st.info(f"LLM 질의 제한: {llm_query_limit}개")
    
    # 변환 방식 선택
    st.subheader("🔄 변환 방식")
    conversion_method = st.selectbox(
        "1차 변환 방식 선택",
        ["자체 로직", "LLM"],
        index=1,  # LLM을 기본값으로 설정
        help="자체 로직: 빠르고 안정적, LLM: 더 정확한 변환"
    )
    if conversion_method != st.session_state.get('conversion_method', 'LLM'):
        st.session_state['conversion_method'] = conversion_method
        # 변환 방식 변경 시 rerun 방지
        st.rerun()
    
    # 디버그 토글
    debug_enabled = st.checkbox("🔧 디버그 로그 표시", value=st.session_state.get('debug_enabled', False))
    if debug_enabled != st.session_state.get('debug_enabled', False):
        st.session_state['debug_enabled'] = debug_enabled
        # 디버그 상태 변경 시 rerun 방지
        st.rerun()
    
    # 병렬처리 설정
    st.subheader("⚡ 성능 설정")
    parallel_enabled = st.checkbox("🚀 병렬처리 활성화", value=st.session_state.get('parallel_enabled', True), help="여러 쿼리를 동시에 처리하여 속도를 향상시킵니다")
    if parallel_enabled != st.session_state.get('parallel_enabled', True):
        st.session_state['parallel_enabled'] = parallel_enabled
        # 병렬처리 상태 변경 시 rerun 방지
        st.rerun()
    
    if parallel_enabled:
        max_workers = st.slider("동시 처리 수", min_value=2, max_value=8, value=st.session_state.get('max_workers', 4), help="동시에 처리할 최대 쿼리 수")
        if max_workers != st.session_state.get('max_workers', 4):
            st.session_state['max_workers'] = max_workers
            # 워커 수 변경 시 rerun 방지
            st.rerun()
    
    # 파일 업로드 옵션
    upload_option = st.radio(
        "입력 방식 선택",
        ["XML 파일 업로드", "직접 입력"],
        help="XML 파일을 업로드하거나 직접 입력할 수 있습니다."
    )
    if upload_option != st.session_state.get('upload_option', 'XML 파일 업로드'):
        st.session_state['upload_option'] = upload_option
        # 업로드 옵션 변경 시 rerun 방지
        st.rerun()

# 메인 컨테이너
main_container = st.container()

with main_container:
    if upload_option == "XML 파일 업로드":
        st.subheader("📁 Mybatis XML 파일 업로드")
        
        uploaded_file = st.file_uploader(
            "XML 파일을 선택하세요",
            type=['xml'],
            help="Mybatis XML 파일을 업로드하면 모든 쿼리를 자동으로 파싱합니다."
        )
        
        if uploaded_file is not None:
            try:
                xml_content = uploaded_file.read().decode('utf-8')
                xml_key = hashlib.md5(xml_content.encode('utf-8')).hexdigest()
                # 업로드 변경 감지 시 상태 초기화
                if st.session_state.get('uploaded_xml_key') != xml_key:
                    debug_log("[STATE] 새 파일 업로드 감지 → 상태 초기화")
                    st.session_state['uploaded_xml_key'] = xml_key
                    st.session_state['queries_converted'] = None
                    st.session_state['ai_validation_running'] = False
                    st.session_state['validation_results'] = {}
                queries = parse_mybatis_xml(xml_content)
                
                if queries:
                    st.success(f"✅ {len(queries)}개의 쿼리를 발견했습니다!")
                    
                    # 쿼리 목록 표시
                    st.subheader("📋 발견된 쿼리 목록")
                    
                    # 변환 버튼
                    if st.button("🚀 모든 쿼리 변환하기", type="primary", use_container_width=True):
                        # 병렬처리 설정 확인
                        parallel_enabled = st.session_state.get('parallel_enabled', True)
                        max_workers = st.session_state.get('max_workers', 4)
                        conversion_method = st.session_state.get('conversion_method', '자체 로직')
                        
                        if parallel_enabled and len(queries) > 1:
                            st.info(f"🚀 병렬처리로 {len(queries)}개 쿼리를 변환합니다 (동시 처리: {max_workers}개)")
                            # 병렬 변환 수행
                            converted_queries = convert_queries_parallel(queries, conversion_method, max_workers)
                            queries.update(converted_queries)
                        else:
                            st.info(f"🔄 순차처리로 {len(queries)}개 쿼리를 변환합니다")
                            with st.spinner("쿼리들을 변환하고 있습니다..."):
                                # 각 쿼리 변환
                                for query_id, query_info in queries.items():
                                    # 각 쿼리별로 변환 수행
                                    converted_xml = convert_mybatis_xml(query_info['xml'], conversion_method)
                                    queries[query_id]['converted'] = converted_xml
                                    queries[query_id]['warnings'] = []  # 경고는 변환 방식에 따라 다를 수 있음
                                    queries[query_id]['notes'] = []     # 노트는 변환 방식에 따라 다를 수 있음
                        
                        # 세션에 변환 결과 저장 (rerun 대비)
                        st.session_state['queries_converted'] = queries
                        st.session_state['uploaded_xml_key'] = xml_key
                        debug_log(f"[STATE] 변환 결과 세션 저장: queries={len(queries)}")
                        
                        # 변환 방식 정보 표시
                        st.success(f"✅ 변환 완료! (변환 방식: {conversion_method}, 병렬처리: {'활성화' if parallel_enabled else '비활성화'})")
                        
                        # 1차 변환 XML 파일 다운로드 기능 추가
                        st.subheader("📥 1차 변환 결과 다운로드")
                        
                        # 모든 변환된 쿼리를 하나의 XML로 결합
                        combined_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<mapper namespace="com.example.mapper">\n'
                        for query_id, query_info in queries.items():
                            if query_info['converted']:
                                combined_xml += f"\n    <!-- {query_id} -->\n"
                                combined_xml += f"    {query_info['converted']}\n"
                        combined_xml += '\n</mapper>'
                        
                        # 다운로드 버튼
                        st.download_button(
                            label="📥 1차 변환 XML 다운로드",
                            data=combined_xml,
                            file_name=f"1차변환_{uploaded_file.name.replace('.xml', '')}_postgresql.xml",
                            mime="application/xml",
                            help="변환된 모든 쿼리가 포함된 XML 파일을 다운로드합니다."
                        )
                    
                    # 각 쿼리별 결과 표시 (접을 수 있는 형태)
                    current_queries = st.session_state.get('queries_converted') or queries
                    if current_queries is not queries:
                        debug_log("[STATE] 세션 저장된 변환 결과 사용 중")
                    for query_id, query_info in current_queries.items():
                        with st.expander(f"🔍 {query_id} ({query_info['type']})", expanded=False):
                            # 탭 생성
                            tab1, tab2, tab3 = st.tabs(["📋 전체 XML", "🔍 순수 SQL 비교", "📝 상세 분석"])
                            
                            with tab1:
                                # 전체 XML 비교
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.subheader("📝 원본 XML")
                                    # 원본 XML 포맷팅
                                    formatted_original = format_xml_consistently(query_info['xml'])
                                    st.code(formatted_original, language="xml")
                                
                                with col2:
                                    st.subheader("🔄 변환된 XML")
                                    if query_info['converted']:
                                        # 변환된 XML 포맷팅
                                        formatted_converted = format_xml_consistently(query_info['converted'])
                                        st.code(formatted_converted, language="xml")
                                         
                                        # AI 개선 여부 표시
                                        if query_info.get('ai_improved', False):
                                            st.success("🤖 AI가 개선한 쿼리입니다", icon="✨")
                                         
                                        # 차이점 하이라이트
                                        st.divider()
                                        st.subheader("🔍 주요 변경사항")
                                         
                                        # 간단한 차이점 분석
                                        if "CURRENT_TIMESTAMP" in formatted_converted and "SYSDATE" in formatted_original:
                                            st.success("✅ SYSDATE → CURRENT_TIMESTAMP 변환됨", icon="💡")
                                        if "COALESCE" in formatted_converted and "NVL" in formatted_original:
                                            st.success("✅ NVL → COALESCE 변환됨", icon="💡")
                                        if "CASE WHEN" in formatted_converted and "DECODE" in formatted_original:
                                            st.success("✅ DECODE → CASE WHEN 변환됨", icon="💡")
                                        if "ROW_NUMBER() OVER()" in formatted_converted and "ROWNUM" in formatted_original:
                                            st.success("✅ ROWNUM → ROW_NUMBER() OVER() 변환됨", icon="💡")
                                        if "POSITION(" in formatted_converted and "INSTR" in formatted_original:
                                            st.success("✅ INSTR → POSITION 변환됨", icon="💡")
                                    else:
                                        st.info("아직 변환되지 않았습니다. '모든 쿼리 변환하기' 버튼을 클릭하세요.")
                            
                            with tab2:
                                # 순수 SQL 비교 (동일한 형식)
                                if query_info['converted']:
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        st.subheader("📝 원본 SQL")
                                        original_sql = extract_pure_sql_from_xml(query_info['xml'])
                                        st.code(original_sql, language="sql")
                                    
                                    with col2:
                                        st.subheader("🔄 변환된 SQL")
                                        converted_sql = extract_pure_sql_from_xml(query_info['converted'])
                                        st.code(converted_sql, language="sql")
                                    
                                    # 차이점 하이라이트
                                    st.divider()
                                    st.subheader("🔍 주요 변경사항")
                                    
                                    # 간단한 차이점 분석
                                    if "SYSDATE" in original_sql and "CURRENT_TIMESTAMP" in converted_sql:
                                        st.success("✅ SYSDATE → CURRENT_TIMESTAMP 변환됨", icon="💡")
                                    if "ROWNUM" in original_sql and "LIMIT" in converted_sql:
                                        st.success("✅ ROWNUM → LIMIT 변환됨", icon="💡")
                                    if "TO_CHAR" in original_sql:
                                        st.info("ℹ️ TO_CHAR 함수는 PostgreSQL에서도 동일하게 사용 가능", icon="ℹ️")
                                else:
                                    st.info("먼저 쿼리를 변환해주세요.")
                            
                            with tab3:
                                # 상세 분석 및 경고/주의사항
                                if query_info['converted']:
                                    st.subheader("🔍 분석 결과")
                                    
                                    if query_info['notes']:
                                        st.subheader("💡 변환 정보")
                                        for note in query_info['notes']:
                                            st.success(note, icon="💡")
                                    
                                    if query_info['warnings']:
                                        st.subheader("⚠️ 주의사항")
                                        for warning in query_info['warnings']:
                                            st.warning(warning)
                                    
                                    # 원본과 변환된 쿼리의 라인 수 비교
                                    original_lines = len(query_info['xml'].split('\n'))
                                    converted_lines = len(query_info['converted'].split('\n'))
                                    
                                    st.subheader("📊 쿼리 정보")
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("원본 라인 수", original_lines)
                                    with col2:
                                        st.metric("변환 라인 수", converted_lines)
                                    with col3:
                                        diff = converted_lines - original_lines
                                        st.metric("라인 수 변화", f"{diff:+d}")
                                else:
                                    st.info("먼저 쿼리를 변환해주세요.")
                    
                    # LLM 검증 섹션 (세션의 변환 결과 기준)
                    if any(q['converted'] for q in current_queries.values()):
                        st.divider()
                        st.subheader("🤖 AI 검증 결과")
                        
                        # 변환된 쿼리만 필터링 (세션 기준)
                        converted_queries = {k: v for k, v in current_queries.items() if v['converted']}
                        
                        # LLM 질의 제한 적용
                        if len(converted_queries) > llm_query_limit:
                            st.warning(f"⚠️ 변환된 쿼리가 {llm_query_limit}개를 초과합니다. 비용 절약을 위해 처음 {llm_query_limit}개만 검증합니다.")
                            converted_queries = dict(list(converted_queries.items())[:llm_query_limit])
                        
                        # AI 검증 버튼과 결과를 별도 컨테이너로 분리
                        validation_container = st.container()
                         
                        # AI 검증 버튼 (검증 중일 때는 비활성화)
                        if st.button("🔍 AI 검증 시작", type="secondary", use_container_width=True, key="ai_validation_start", disabled=st.session_state.get('ai_validation_running', False)):
                             # 검증 상태를 session_state에 저장
                             st.session_state.ai_validation_running = True
                             st.session_state.validation_results = {}
                             debug_log("[AI-검증] 시작 버튼 클릭 → 상태 플래그 설정")
                        
                        # AI 검증 실행 및 결과 표시
                        if st.session_state.get('ai_validation_running', False):
                            with validation_container:
                                st.subheader("🤖 AI 검증 진행 상황")
                                
                                # 병렬처리 설정 확인
                                parallel_enabled = st.session_state.get('parallel_enabled', True)
                                max_workers = min(3, st.session_state.get('max_workers', 4))  # AI 검증은 최대 3개로 제한
                                
                                if parallel_enabled and len(converted_queries) > 1:
                                    st.info(f"🚀 병렬처리로 AI 검증을 수행합니다 (동시 처리: {max_workers}개)")
                                    # 병렬 AI 검증 수행
                                    validation_results = validate_queries_parallel(converted_queries, max_workers)
                                    st.session_state.validation_results.update(validation_results)
                                else:
                                    st.info(f"🔄 순차처리로 AI 검증을 수행합니다")
                                    # 변환된 쿼리들을 위에서부터 차례로 처리
                                    for i, (query_id, query_info) in enumerate(converted_queries.items()):
                                        if i >= llm_query_limit:  # llm_query_id_limit만큼만 처리
                                            break
                                        
                                        debug_log(f"[AI-검증] {i+1}/{min(len(converted_queries), llm_query_limit)} 시작: id={query_id}")
                                        st.info(f"🔍 검증 중... ({i+1}/{min(len(converted_queries), llm_query_limit)}): {query_id}")
                                        
                                        # 이미 검증된 결과가 있으면 재사용
                                        if query_id not in st.session_state.validation_results:
                                            llm_results = validate_with_llm(query_info['converted'])
                                            st.session_state.validation_results[query_id] = llm_results
                                        else:
                                            llm_results = st.session_state.validation_results[query_id]
                                        
                                        debug_log(f"[AI-검증] 완료: id={query_id}")
                            
                            # AI 검증 결과 요약 표시
                            if st.session_state.get('validation_results'):
                                st.divider()
                                st.subheader("📊 AI 검증 결과 요약")
                                
                                # 환경 변수에서 실제 모델명 가져오기
                                ai_deploy_model = os.getenv('AI_DEPLOY_MODEL', 'Unknown')
                                
                                for query_id, query_info in converted_queries.items():
                                    if query_id in st.session_state.validation_results:
                                        validation_result = st.session_state.validation_results[query_id]
                                        
                                        # 모델별 검증 결과 확인
                                        if ai_deploy_model in validation_result:
                                            result = validation_result[ai_deploy_model]
                                            
                                            if result["status"] == "success" or "정상 동작합니다" in result.get("message", ""):
                                                # 성공한 경우
                                                st.success(f"✅ **{query_id}** - {ai_deploy_model} 검증결과: Syntax 오류 없음", icon="🤖")
                                            else:
                                                # 오류가 있는 경우
                                                st.error(f"❌ **{query_id}** - {ai_deploy_model} 검증결과: Syntax 오류 발견", icon="⚠️")
                                                
                                                # 상세 내용을 접을 수 있는 형태로 표시
                                                with st.expander(f"🔍 **{query_id}** 상세 내용 보기", expanded=False):
                                                    st.subheader("📝 AI 검증 메시지")
                                                    
                                                    # 디버그 정보 추가
                                                    debug_log(f"[UI] {query_id} 검증 결과: status={result.get('status')}, message={result.get('message', 'None')[:100]}...")
                                                    
                                                    # 메시지가 있는지 확인하고 표시
                                                    message = result.get("message", "")
                                                    if message and message.strip():
                                                        st.markdown(f"**LLM 응답:**\n\n{message}")
                                                    else:
                                                        st.warning("⚠️ AI 검증 메시지가 비어있습니다. LLM 응답을 확인해주세요.")
                                                        # 디버그 모드에서 더 자세한 정보 표시
                                                        if st.session_state.get('debug_enabled', False):
                                                            st.error(f"**원본 검증 결과:**\n```json\n{result}\n```")
                                                    
                                                    # AI가 수정한 쿼리가 있는 경우에만 표시
                                                    if result.get("details"):
                                                        st.subheader("🔧 AI가 수정한 PostgreSQL 쿼리")
                                                        st.code(result["details"], language="xml")
                                                        
                                                        # 수정된 쿼리 복사 버튼
                                                        if st.button(f"수정된 쿼리 복사 ({query_id})", type="secondary", use_container_width=True, key=f"copy_fixed_{query_id}"):
                                                            st.success(f"✅ {query_id}의 수정된 쿼리가 클립보드에 복사되었습니다.")
                                                    else:
                                                        st.info("AI가 수정한 쿼리가 없습니다.")
                                                    
                                                    # 디버그 정보 표시 (개발자용)
                                                    if st.session_state.get('debug_enabled', False):
                                                        st.subheader("🔧 디버그 정보")
                                                        st.json({
                                                            "status": result.get("status"),
                                                            "message_length": len(message) if message else 0,
                                                            "has_details": bool(result.get("details")),
                                                            "full_result": result
                                                        })
                                        else:
                                            st.warning(f"⚠️ **{query_id}** - {ai_deploy_model} 검증 결과를 찾을 수 없습니다.")
                            
                            st.success("🎉 AI 검증 완료!")
                             
                            # AI 검증 결과를 캐시에 업데이트
                            debug_log("[CACHE] AI 검증 결과를 캐시에 업데이트 시작")
                            for query_id, query_info in converted_queries.items():
                                if query_id in st.session_state.validation_results:
                                    validation_result = st.session_state.validation_results[query_id]
                                    ai_deploy_model = os.getenv('AI_DEPLOY_MODEL', 'Unknown')
                                     
                                    # AI가 수정한 쿼리가 있으면 캐시 업데이트
                                    if (validation_result.get(ai_deploy_model, {}).get("status") == "error" and 
                                        validation_result.get(ai_deploy_model, {}).get("details")):
                                        # 캐시된 쿼리 정보 업데이트
                                        if query_id in st.session_state['queries_converted']:
                                            st.session_state['queries_converted'][query_id]['converted'] = validation_result[ai_deploy_model]['details']
                                            st.session_state['queries_converted'][query_id]['ai_improved'] = True
                                            debug_log(f"[CACHE] {query_id} 쿼리를 AI 개선 결과로 업데이트")
                             
                            # 2차 변환 XML 파일 다운로드 기능 추가
                            st.subheader("📥 2차 변환 결과 다운로드")
                            
                            # AI 검증 결과를 반영한 최종 XML 생성
                            final_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<mapper namespace="com.example.mapper">\n'
                            for query_id, query_info in converted_queries.items():
                                if query_id in st.session_state.validation_results:
                                    validation_result = st.session_state.validation_results[query_id]
                                    # AI가 수정한 쿼리가 있으면 사용, 없으면 1차 변환 결과 사용
                                    # ai_deploy_model을 환경 변수에서 가져오기
                                    ai_deploy_model = os.getenv('AI_DEPLOY_MODEL', 'Unknown')
                                    if (validation_result.get(ai_deploy_model, {}).get("status") == "error" and 
                                        validation_result.get(ai_deploy_model, {}).get("details")):
                                        final_xml += f"\n    <!-- {query_id} (AI 수정) -->\n"
                                        final_xml += f"    {validation_result[ai_deploy_model]['details']}\n"
                                    else:
                                        final_xml += f"\n    <!-- {query_id} -->\n"
                                        final_xml += f"    {query_info['converted']}\n"
                                else:
                                    final_xml += f"\n    <!-- {query_id} -->\n"
                                    final_xml += f"    {query_info['converted']}\n"
                            final_xml += '\n</mapper>'
                            
                            # 다운로드 버튼
                            st.download_button(
                                label="📥 2차 변환 XML 다운로드",
                                data=final_xml,
                                file_name=f"2차변환_{uploaded_file.name.replace('.xml', '')}_postgresql.xml",
                                mime="application/xml",
                                help="AI 검증을 거친 최종 PostgreSQL XML 파일을 다운로드합니다."
                            )
                            
                            # 재검증 버튼
                            if st.button("🔄 새로 검증하기", type="primary", use_container_width=True, key="reset_validation"):
                                st.session_state.ai_validation_running = False
                                st.session_state.validation_results = {}
                else:
                    st.error("XML 파일에서 유효한 Mybatis 쿼리를 찾을 수 없습니다.")
                    
            except Exception as e:
                st.error(f"파일 처리 중 오류가 발생했습니다: {e}")
    
    else:
        # 기존 직접 입력 방식
        st.subheader("📝 직접 입력")
        
        DEFAULT_QUERY = """<!-- 디바이스 정보 수정 -->
<update id="deviceInfoUpdate" parameterType="com.skb.edmp.device.dto.DeviceInfoUpdateReqDto" timeout="1">
    UPDATE DM_DVC_MODL_MST
    <trim prefix="SET" suffixOverrides=",">
        STM_LAST_UPD_DATE = SYSDATE,
        <if test='modl_fg_cd != null and modl_fg_cd != ""'>MODL_FG_CD = #{modl_fg_cd},</if>
        <if test='modl_os_fg_cd != null and modl_os_fg_cd != ""'>MODL_OS_FG_CD = #{modl_os_fg_cd},</if>
        <if test='modl_manufr_fg_cd != null and modl_manufr_fg_cd != ""'>MODL_MANUFR_FG_CD = #{modl_manufr_fg_cd},</if>
        <if test='use_yn != null and use_yn != ""'>USE_YN = #{use_yn},</if>
        <if test='user_id != null and user_id != ""'>STM_LAST_UPD_USER_ID = #{user_id},</if>
    </trim>
    WHERE MODL_CD = #{modl_cd}
</update>
"""

        st.info("좌측에 변환할 Oracle DB 기준의 Mybatis XML 쿼리를 붙여넣고 '변환' 버튼을 누르세요.", icon="ℹ️")

        col1, col2 = st.columns(2)

        with col1:
            # CSS를 사용하여 텍스트 영역을 코드 에디터처럼 스타일링
            st.markdown("""
            <style>
            .stTextArea textarea {
                font-family: 'Courier New', monospace;
                font-size: 14px;
                line-height: 1.4;
                background-color: #2d3748;
                color: #e2e8f0;
                border: 1px solid #4a5568;
                border-radius: 4px;
                padding: 12px;
            }
            .stTextArea textarea:focus {
                background-color: #1a202c;
                color: #f7fafc;
                border-color: #63b3ed;
                box-shadow: 0 0 0 3px rgba(99, 179, 237, 0.1);
            }
            </style>
            """, unsafe_allow_html=True)
            
            input_xml = st.text_area("쿼리 입력", value=DEFAULT_QUERY, height=500, label_visibility="collapsed")

        with col2:
            st.subheader("PostgreSQL 변환 결과")
            if st.button("변환하기", type="primary", use_container_width=True):
                if input_xml:
                    # 병렬처리 설정 확인 (직접 입력은 단일 쿼리이므로 순차처리)
                    conversion_method = st.session_state.get('conversion_method', '자체 로직')
                    
                    with st.spinner("변환 중..."):
                        # 변환 수행
                        converted_xml = convert_mybatis_xml(input_xml, conversion_method)
                    
                    if converted_xml:
                        # 원본과 변환된 XML을 포맷팅하여 비교 표시
                        col2_1, col2_2 = st.columns(2)
                        
                        with col2_1:
                            st.subheader("📝 원본 XML")
                            formatted_original = format_xml_consistently(input_xml)
                            st.code(formatted_original, language="xml")
                        
                        with col2_2:
                            st.subheader("🔄 변환된 XML")
                            formatted_converted = format_xml_consistently(converted_xml)
                            st.code(formatted_converted, language="xml")

                        # 차이점 하이라이트
                        st.divider()
                        st.subheader("🔍 주요 변경사항")
                        
                        # 간단한 차이점 분석
                        if "CURRENT_TIMESTAMP" in formatted_converted and "SYSDATE" in formatted_original:
                            st.success("✅ SYSDATE → CURRENT_TIMESTAMP 변환됨", icon="💡")
                        if "COALESCE" in formatted_converted and "NVL" in formatted_original:
                            st.success("✅ NVL → COALESCE 변환됨", icon="💡")
                        if "CASE WHEN" in formatted_converted and "DECODE" in formatted_original:
                            st.success("✅ DECODE → CASE WHEN 변환됨", icon="💡")
                        if "ROW_NUMBER() OVER()" in formatted_converted and "ROWNUM" in formatted_original:
                            st.success("✅ ROWNUM → ROW_NUMBER() OVER() 변환됨", icon="💡")
                        if "POSITION(" in formatted_converted and "INSTR" in formatted_original:
                            st.success("✅ INSTR → POSITION 변환됨", icon="💡")
                        
                        st.divider()
                        st.subheader("🔍 분석 결과 및 주의사항")

                        # 변환 방식 정보 표시
                        st.info(f"🔄 변환 방식: {conversion_method}")
                        
                        # 병렬처리 정보 표시
                        parallel_enabled = st.session_state.get('parallel_enabled', True)
                        if parallel_enabled:
                            st.success(f"⚡ 병렬처리: 활성화 (동시 처리: {st.session_state.get('max_workers', 4)}개)", icon="🚀")
                        else:
                            st.info("🔄 병렬처리: 비활성화 (순차 처리)", icon="⏱️")
                        
                        # 변환 방식별 특징 설명
                        if conversion_method == "자체 로직":
                            st.success("💡 자체 로직: 빠르고 안정적인 변환", icon="⚡")
                        elif conversion_method == "LLM":
                            st.success("💡 LLM: 더 정확하고 지능적인 변환", icon="🤖")
                        
                        # 1차 변환 XML 파일 다운로드 기능 추가
                        st.subheader("📥 1차 변환 결과 다운로드")
                        st.download_button(
                            label="📥 1차 변환 XML 다운로드",
                            data=converted_xml,
                            file_name="1차변환_postgresql.xml",
                            mime="application/xml",
                            help="변환된 PostgreSQL XML 파일을 다운로드합니다."
                        )
                        
                        # LLM 검증 수행
                        st.divider()
                        st.subheader("🤖 AI 검증 결과")
                        
                        with st.spinner("AI가 변환 결과를 검증하고 있습니다..."):
                            llm_results = validate_with_llm(converted_xml)
                        
                        if llm_results:
                            for model_name, result in llm_results.items():
                                # 모델명과 상태 표시
                                if result["status"] == "success":
                                    st.success(f"✅ **{model_name}**: {result['message']}", icon="🤖")
                                elif result["status"] == "error":
                                    # 간단한 오류 메시지만 먼저 표시
                                    if "정상 동작합니다" in result["message"]:
                                        st.success(f"✅ **{model_name}**: 정상 동작합니다", icon="🤖")
                                    else:
                                        # 문법 오류 발견 시 접을 수 있는 상세 내용 제공
                                        with st.expander(f"⚠️ **{model_name}**: 문법 오류 발견 (클릭하여 상세보기)", expanded=False):
                                            st.markdown(result["message"])
                                            
                                            # 수정된 XML이 있는 경우 표시
                                            if result["details"]:
                                                st.subheader("🔧 수정된 쿼리")
                                                st.code(result["details"], language="xml")
                                                
                                                # 개선된 쿼리 복사 버튼 (JavaScript 클립보드 복사)
                                                copy_button_key = f"copy_{model_name}"
                                                if st.button(f"📋 수정된 쿼리 복사 ({model_name})", type="secondary", use_container_width=True, key=copy_button_key):
                                                    # JavaScript로 클립보드 복사
                                                    st.markdown(f"""
                                                    <script>
                                                    function copyToClipboard{model_name.replace('-', '_').replace('.', '_')}() {{
                                                        const text = `{result["details"].replace('`', '\\`').replace('$', '\\$')}`;
                                                        navigator.clipboard.writeText(text).then(function() {{
                                                            // 성공 메시지 표시 (화면 새로고침 없음)
                                                            const button = document.querySelector('[data-testid="stButton"]');
                                                            if (button) {{
                                                                button.innerHTML = '✅ 복사 완료!';
                                                                button.style.backgroundColor = '#10b981';
                                                                button.style.color = 'white';
                                                                setTimeout(() => {{
                                                                    button.innerHTML = '📋 수정된 쿼리 복사 ({model_name})';
                                                                    button.style.backgroundColor = '';
                                                                    button.style.color = '';
                                                                }}, 2000);
                                                            }}
                                                        }}).catch(function(err) {{
                                                            console.error('클립보드 복사 실패:', err);
                                                        }});
                                                    }}
                                                    copyToClipboard{model_name.replace('-', '_').replace('.', '_')}();
                                                    </script>
                                                    """, unsafe_allow_html=True)
                        
                        # AI 검증 완료 후 2차 변환 XML 다운로드 기능 추가
                        if any(result["status"] == "error" and result.get("details") for result in llm_results.values()):
                            st.subheader("📥 2차 변환 결과 다운로드")
                            
                            # AI 검증 결과를 반영한 최종 XML 생성
                            final_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<mapper namespace="com.example.mapper">\n'
                            
                            # AI가 수정한 쿼리가 있으면 사용, 없으면 1차 변환 결과 사용
                            for model_name, result in llm_results.items():
                                if result["status"] == "error" and result.get("details"):
                                    final_xml += f"\n    <!-- AI 수정된 쿼리 -->\n"
                                    final_xml += f"    {result['details']}\n"
                                else:
                                    final_xml += f"\n    <!-- 1차 변환 결과 -->\n"
                                    final_xml += f"    {converted_xml}\n"
                            
                            final_xml += '\n</mapper>'
                            
                            # 다운로드 버튼
                            st.download_button(
                                label="📥 2차 변환 XML 다운로드",
                                data=final_xml,
                                file_name="2차변환_postgresql.xml",
                                mime="application/xml",
                                help="AI 검증을 거친 최종 PostgreSQL XML 파일을 다운로드합니다."
                            )
                        else:
                            st.success("🎉 AI 검증 완료! 모든 쿼리가 정상적으로 변환되었습니다.")
                    else:
                        st.error("AI 검증을 수행할 수 없습니다.")
                else:
                    st.warning("변환할 쿼리를 입력해주세요.")
