"""
텍스트 파일 기반 프롬프트 템플릿 관리 모듈
"""

import os
from pathlib import Path

# 프롬프트 파일들이 저장된 디렉토리
PROMPTS_DIR = Path(__file__).parent / "prompts"

# 템플릿 정보 (파일명과 표시명 매핑)
TEMPLATE_INFO = {
    "general_analysis.txt": {
        "name": "종합 분석",
        "description": "대시보드의 전반적인 메트릭, 성능, 상태를 종합적으로 분석합니다."
    },
    "trend_analysis.txt": {
        "name": "트렌드 분석",
        "description": "시간별 변화 패턴과 트렌드를 중점적으로 분석합니다."
    }
}

def get_template_names() -> list:
    """사용 가능한 템플릿 이름 목록을 반환합니다."""
    return [info["name"] for info in TEMPLATE_INFO.values()]

def get_template_prompt(template_name: str) -> str:
    """템플릿 이름으로 프롬프트 문자열을 반환합니다."""
    # 템플릿 이름으로 파일명 찾기
    filename = None
    for file, info in TEMPLATE_INFO.items():
        if info["name"] == template_name:
            filename = file
            break
    
    if not filename:
        return ""
    
    # 파일에서 프롬프트 읽기
    file_path = PROMPTS_DIR / filename
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # 개행을 공백으로 변환하고 연속된 공백을 하나로 정리
            import re
            content = re.sub(r'\s+', ' ', content)
            return content
    except FileNotFoundError:
        print(f"프롬프트 파일을 찾을 수 없습니다: {file_path}")
        return ""
    except Exception as e:
        print(f"프롬프트 파일 읽기 오류: {e}")
        return ""

def get_template_description(template_name: str) -> str:
    """템플릿 이름으로 설명을 반환합니다."""
    for info in TEMPLATE_INFO.values():
        if info["name"] == template_name:
            return info["description"]
    return ""

def get_all_templates() -> dict:
    """모든 템플릿 정보를 반환합니다."""
    templates = {}
    for filename, info in TEMPLATE_INFO.items():
        prompt = get_template_prompt(info["name"])
        templates[info["name"]] = {
            "name": info["name"],
            "description": info["description"],
            "prompt": prompt
        }
    return templates

def list_available_templates() -> list:
    """사용 가능한 템플릿 파일 목록을 반환합니다."""
    if not PROMPTS_DIR.exists():
        return []
    
    available_files = []
    for filename in TEMPLATE_INFO.keys():
        file_path = PROMPTS_DIR / filename
        if file_path.exists():
            available_files.append(filename)
    
    return available_files

def add_new_template(filename: str, name: str, description: str, prompt_content: str) -> bool:
    """새로운 템플릿을 추가합니다."""
    try:
        # prompts 디렉토리가 없으면 생성
        PROMPTS_DIR.mkdir(exist_ok=True)
        
        # 파일 생성
        file_path = PROMPTS_DIR / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(prompt_content)
        
        # TEMPLATE_INFO에 추가
        TEMPLATE_INFO[filename] = {
            "name": name,
            "description": description
        }
        
        return True
    except Exception as e:
        print(f"템플릿 추가 오류: {e}")
        return False
