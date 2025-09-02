import sqlglot
import re
import os
import requests
import json
import time
from xml.etree import ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

def debug_log(message: str) -> None:
    """디버그 로그 출력 (Streamlit 세션 상태 확인)"""
    # Streamlit이 로드되지 않은 환경에서는 print로 출력
    try:
        import streamlit as st
        if st.session_state.get('debug_enabled', False):
            st.info(message)
    except:
        print(f"[DEBUG] {message}")

def convert_with_self_logic(mybatis_xml):
    """
    자체 로직을 사용하여 Oracle Mybatis XML을 PostgreSQL로 변환합니다.
    """
    try:
        debug_log("[변환] 자체 로직 변환 시작")
        
        # Mybatis XML에서 순수 SQL 추출
        sql_content = extract_pure_sql_from_xml(mybatis_xml)
        
        # Oracle 특정 함수들을 PostgreSQL로 변환
        converted_sql = convert_oracle_to_postgresql(sql_content)
        
        # sqlglot을 사용한 추가 변환
        try:
            parsed = sqlglot.parse_one(converted_sql, read='oracle')
            if parsed:
                final_sql = parsed.sql(dialect='postgres')
                debug_log("[변환] sqlglot 변환 성공")
            else:
                final_sql = converted_sql
                debug_log("[변환] sqlglot 변환 실패, 자체 변환 결과 사용")
        except Exception as e:
            debug_log(f"[변환] sqlglot 오류: {str(e)}, 자체 변환 결과 사용")
            final_sql = converted_sql
        
        # 변환된 SQL을 Mybatis XML에 적용
        converted_xml = apply_converted_sql_to_xml(mybatis_xml, final_sql)
        
        debug_log("[변환] 자체 로직 변환 완료")
        return converted_xml
        
    except Exception as e:
        debug_log(f"[변환] 자체 로직 변환 오류: {str(e)}")
        raise e

def convert_with_llm(mybatis_xml):
    """
    LLM을 사용하여 Oracle Mybatis XML을 PostgreSQL로 변환합니다.
    """
    try:
        debug_log("[변환] LLM 변환 시작")
        
        # 환경 변수 확인
        ai_deploy_model = os.getenv('AI_DEPLOY_MODEL')
        ai_api_key = os.getenv('AI_API_KEY')
        ai_endpoint = os.getenv('AI_ENDPOINT')
        ai_deploy_version = os.getenv('AI_DEPLOY_VERSION', '2023-12-01-preview')
        
        if not all([ai_deploy_model, ai_api_key, ai_endpoint]):
            raise ValueError("LLM API 설정이 완료되지 않았습니다. .env 파일을 확인해주세요.")
        
        # LLM에 전송할 프롬프트 구성
        prompt = f"""
당신은 Oracle과 PostgreSQL, Mybatis 전문가입니다. 다음 Oracle Mybatis XML을 PostgreSQL용으로 변환해주세요.

**원본 Oracle Mybatis XML:**
```xml
{mybatis_xml}
```

**변환 요구사항:**
1. Oracle SQL을 PostgreSQL 문법에 맞게 변환
2. Mybatis XML 구조는 유지
3. Oracle 특정 함수들을 PostgreSQL 대응 함수로 변환
4. 문법 오류가 없는 완전한 PostgreSQL Mybatis XML 제공

**응답 형식:**
변환된 PostgreSQL Mybatis XML만 제공하세요. 설명이나 주석은 포함하지 마세요.
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
                    {'role': 'system', 'content': '당신은 Oracle을 PostgreSQL로 변환하는 전문가입니다.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_completion_tokens': 4000
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
                    {'role': 'system', 'content': '당신은 Oracle을 PostgreSQL로 변환하는 전문가입니다.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 4000,
                'temperature': 0.1,
                'top_p': 0.95,
                'frequency_penalty': 0,
                'presence_penalty': 0
            }
        
        debug_log(f"[변환] LLM API 호출: {azure_endpoint}")
        debug_log(f"[변환] 모델: {ai_deploy_model}")
        debug_log(f"[변환] 프롬프트 길이: {len(prompt)} chars")
        
        start_time = time.perf_counter()
        
        response = requests.post(azure_endpoint, headers=headers, json=data, timeout=60)
        
        elapsed_time = (time.perf_counter() - start_time) * 1000
        debug_log(f"[변환] HTTP 상태: {response.status_code}, 소요시간: {elapsed_time:.1f} ms")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    converted_xml = result['choices'][0]['message']['content'].strip()
                    
                    # XML 태그 제거 (LLM이 설명을 포함할 수 있음)
                    if '<' in converted_xml and '>' in converted_xml:
                        # XML 부분만 추출
                        start_idx = converted_xml.find('<')
                        end_idx = converted_xml.rfind('>') + 1
                        converted_xml = converted_xml[start_idx:end_idx]
                    
                    debug_log(f"[변환] LLM 변환 완료, 결과 길이: {len(converted_xml)} chars")
                    return converted_xml
                else:
                    raise ValueError("LLM 응답에서 변환 결과를 찾을 수 없습니다.")
            except json.JSONDecodeError as e:
                debug_log(f"[변환] JSON 파싱 오류: {str(e)}")
                debug_log(f"[변환] 응답 내용: {response.text[:200]}...")
                raise ValueError("LLM 응답을 파싱할 수 없습니다.")
        else:
            # 400 오류 시 상세 정보 출력
            if response.status_code == 400:
                try:
                    error_detail = response.json()
                    debug_log(f"[변환] 400 오류 상세 정보: {error_detail}")
                except:
                    debug_log(f"[변환] 400 오류 응답: {response.text[:500]}")
            
            debug_log(f"[변환] API 오류: {response.status_code} - {response.text}")
            raise ValueError(f"LLM API 호출 실패: {response.status_code}")
            
    except Exception as e:
        debug_log(f"[변환] LLM 변환 오류: {str(e)}")
        raise e

def extract_pure_sql_from_xml(xml_content):
    """
    Mybatis XML에서 순수 SQL을 추출합니다.
    """
    try:
        # CDATA 섹션 제거
        sql_content = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', xml_content, flags=re.DOTALL)
        
        # Mybatis 파라미터 치환
        sql_content = re.sub(r'#\{([^}]+)\}', r'$1', sql_content)
        sql_content = re.sub(r'\$\{([^}]+)\}', r'$1', sql_content)
        
        # Mybatis 동적 태그 제거
        sql_content = re.sub(r'<if[^>]*>.*?</if>', '', sql_content, flags=re.DOTALL)
        sql_content = re.sub(r'<choose>.*?</choose>', '', sql_content, flags=re.DOTALL)
        sql_content = re.sub(r'<when[^>]*>.*?</when>', '', sql_content, flags=re.DOTALL)
        sql_content = re.sub(r'<otherwise>.*?</otherwise>', '', sql_content, flags=re.DOTALL)
        sql_content = re.sub(r'<foreach[^>]*>.*?</foreach>', '', sql_content, flags=re.DOTALL)
        sql_content = re.sub(r'<where>.*?</where>', '', sql_content, flags=re.DOTALL)
        sql_content = re.sub(r'<set>.*?</set>', '', sql_content, flags=re.DOTALL)
        sql_content = re.sub(r'<trim[^>]*>.*?</trim>', '', sql_content, flags=re.DOTALL)
        
        # XML 태그 제거
        sql_content = re.sub(r'<[^>]+>', '', sql_content)
        
        # 공백 정리
        sql_content = re.sub(r'\s+', ' ', sql_content).strip()
        
        return sql_content
        
    except Exception as e:
        debug_log(f"[추출] SQL 추출 오류: {str(e)}")
        return xml_content

def convert_oracle_to_postgresql(sql_content):
    """
    Oracle SQL을 PostgreSQL로 변환합니다.
    """
    try:
        debug_log("[변환] Oracle→PostgreSQL 함수 변환 시작")
        
        # Oracle 특정 함수들을 PostgreSQL로 변환
        conversions = [
            # 날짜/시간 함수
            (r'\bSYSDATE\b', 'CURRENT_TIMESTAMP'),
            (r'\bSYSTIMESTAMP\b', 'CURRENT_TIMESTAMP'),
            (r'\bTO_DATE\s*\(\s*([^,]+),\s*([^)]+)\s*\)', r'TO_TIMESTAMP(\1, \2)'),
            (r'\bTO_CHAR\s*\(\s*([^,]+),\s*([^)]+)\s*\)', r'TO_CHAR(\1, \2)'),
            
            # NULL 처리 함수
            (r'\bNVL\s*\(\s*([^,]+),\s*([^)]+)\s*\)', r'COALESCE(\1, \2)'),
            (r'\bNVL2\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\s*\)', r'CASE WHEN \1 IS NOT NULL THEN \2 ELSE \3 END'),
            
            # 문자열 함수
            (r'\bINSTR\s*\(\s*([^,]+),\s*([^)]+)\s*\)', r'POSITION(\2 IN \1)'),
            (r'\bSUBSTR\s*\(\s*([^,]+),\s*([^,]+),\s*([^)]+)\s*\)', r'SUBSTRING(\1 FROM \2 FOR \3)'),
            (r'\bLENGTH\s*\(\s*([^)]+)\s*\)', r'LENGTH(\1)'),
            (r'\bUPPER\s*\(\s*([^)]+)\s*\)', r'UPPER(\1)'),
            (r'\bLOWER\s*\(\s*([^)]+)\s*\)', r'LOWER(\1)'),
            
            # 숫자 함수
            (r'\bROUND\s*\(\s*([^,]+),\s*([^)]+)\s*\)', r'ROUND(\1::numeric, \2)'),
            (r'\bTRUNC\s*\(\s*([^,]+),\s*([^)]+)\s*\)', r'TRUNC(\1::numeric, \2)'),
            (r'\bCEIL\s*\(\s*([^)]+)\s*\)', r'CEIL(\1::numeric)'),
            (r'\bFLOOR\s*\(\s*([^)]+)\s*\)', r'FLOOR(\1::numeric)'),
            
            # ROWNUM 처리
            (r'\bROWNUM\s*<=\s*(\d+)', r'ROW_NUMBER() OVER() <= \1'),
            (r'\bROWNUM\s*=\s*1', r'ROW_NUMBER() OVER() = 1'),
            
            # 시퀀스
            (r'\b\.NEXTVAL\b', '.nextval'),
            (r'\b\.CURRVAL\b', '.currval'),
            
            # 테이블 별칭
            (r'\bFROM\s+([^\s]+)\s+([^\s]+)\s+WHERE', r'FROM \1 AS \2 WHERE'),
            
            # Oracle 특정 타입
            (r'\bVARCHAR2\b', 'VARCHAR'),
            (r'\bNUMBER\b', 'NUMERIC'),
            (r'\bCLOB\b', 'TEXT'),
            (r'\bBLOB\b', 'BYTEA'),
            
            # Oracle 특정 연산자
            (r'\b\|\|\b', '||'),
            (r'\bDECODE\s*\(\s*([^)]+)\s*\)', r'CASE \1 END'),
        ]
        
        converted_sql = sql_content
        for pattern, replacement in conversions:
            converted_sql = re.sub(pattern, replacement, converted_sql, flags=re.IGNORECASE)
        
        debug_log("[변환] Oracle→PostgreSQL 함수 변환 완료")
        return converted_sql
        
    except Exception as e:
        debug_log(f"[변환] Oracle→PostgreSQL 변환 오류: {str(e)}")
        return sql_content

def apply_converted_sql_to_xml(original_xml, converted_sql):
    """
    변환된 SQL을 원본 Mybatis XML에 적용합니다.
    """
    try:
        debug_log("[변환] XML에 변환된 SQL 적용 시작")
        
        # 원본 XML을 파싱
        root = ET.fromstring(original_xml)
        
        # SQL이 포함된 태그 찾기 (select, insert, update, delete)
        sql_tags = root.findall('.//select') + root.findall('.//insert') + root.findall('.//update') + root.findall('.//delete')
        
        if sql_tags:
            # 첫 번째 SQL 태그에 변환된 SQL 적용
            sql_tag = sql_tags[0]
            sql_tag.text = f"\n        {converted_sql}\n    "
            
            # 변환 완료 메시지 추가
            note_element = ET.Element('note')
            note_element.text = "Oracle → PostgreSQL 변환 완료 (자체 로직)"
            note_element.set('type', 'conversion_note')
            root.append(note_element)
        
        # XML을 문자열로 변환
        converted_xml = ET.tostring(root, encoding='unicode')
        
        debug_log("[변환] XML에 변환된 SQL 적용 완료")
        return converted_xml
        
    except Exception as e:
        debug_log(f"[변환] XML 적용 오류: {str(e)}")
        return original_xml

def format_xml_consistently(xml_content):
    """
    XML의 들여쓰기와 개행을 일관된 형태로 포맷팅합니다.
    """
    try:
        root = ET.fromstring(xml_content)
        
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
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i
        
        indent(root)
        
        formatted_xml = ET.tostring(root, encoding='unicode')
        
        # 추가 포맷팅 규칙 적용
        formatted_xml = re.sub(r'>\s*\n\s*<', '>\n        <', formatted_xml)
        formatted_xml = re.sub(r'>\s*([^<]+)\s*<', r'>\n            \1\n        <', formatted_xml)
        
        # SQL 태그별 들여쓰기 조정
        formatted_xml = re.sub(r'(<select[^>]*>)\s*\n', r'\1\n        ', formatted_xml)
        formatted_xml = re.sub(r'(<insert[^>]*>)\s*\n', r'\1\n        ', formatted_xml)
        formatted_xml = re.sub(r'(<update[^>]*>)\s*\n', r'\1\n        ', formatted_xml)
        formatted_xml = re.sub(r'(<delete[^>]*>)\s*\n', r'\1\n        ', formatted_xml)
        
        formatted_xml = re.sub(r'\n\s*(</select>)', r'\n    \1', formatted_xml)
        formatted_xml = re.sub(r'\n\s*(</insert>)', r'\n    \1', formatted_xml)
        formatted_xml = re.sub(r'\n\s*(</update>)', r'\n    \1', formatted_xml)
        formatted_xml = re.sub(r'\n\s*(</delete>)', r'\n    \1', formatted_xml)
        
        return formatted_xml
        
    except Exception as e:
        # XML 파싱 실패 시 정규식으로 기본 포맷팅
        formatted_xml = re.sub(r'\n\s*\n', '\n', xml_content)
        formatted_xml = re.sub(r'^\s+', '', formatted_xml, flags=re.MULTILINE)
        formatted_xml = re.sub(r'>\s+<', '>\n<', formatted_xml)
        formatted_xml = re.sub(r'>\s+([^<])', '>\n        \1', formatted_xml)
        formatted_xml = re.sub(r'([^>])\s+<', '\1\n        <', formatted_xml)
        
        return formatted_xml
