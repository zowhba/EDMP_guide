import streamlit as st
import requests
import json
import os
from datetime import datetime, timedelta
import pandas as pd
from PIL import Image
import io
import base64
from prompt_manager import get_all_templates, get_template_names, get_template_prompt, get_template_description

# 페이지 설정
st.set_page_config(
    page_title="Grafana Dashboard Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# FastAPI 백엔드 URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def main():
    st.title("📊 Grafana Dashboard Analyzer")
    st.markdown("---")
    
    # 사이드바에 메뉴
    with st.sidebar:
        st.header("🎛️ 메뉴")
        selected_page = st.radio(
            "페이지 선택",
            ["대시보드 분석", "분석 이력", "설정"]
        )
    
    if selected_page == "대시보드 분석":
        dashboard_analysis_page()
    elif selected_page == "분석 이력":
        analysis_history_page()
    else:
        settings_page()

def dashboard_analysis_page():
    """대시보드 분석 페이지"""
    st.header("🔍 Grafana 대시보드 분석")
    
    # 분석 방식 선택 탭
    analysis_tab1, analysis_tab2 = st.tabs(["📊 Grafana 캡처 분석", "📁 이미지 업로드 분석"])
    
    with analysis_tab1:
        grafana_analysis_tab()
    
    with analysis_tab2:
        image_upload_analysis_tab()

def grafana_analysis_tab():
    """Grafana 캡처 분석 탭"""
    st.subheader("📊 Grafana 대시보드 캡처 분석")
    
    # Grafana 서버 설정 섹션
    with st.expander("🌐 Grafana 서버 설정", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            grafana_url = st.text_input(
                "Grafana 서버 URL *",
                placeholder="예: http://1.255.144.202:8443",
                help="Grafana 서버의 전체 URL을 입력하세요"
            )
            
        with col2:
            api_token = st.text_input(
                "API 토큰 *",
                type="password",
                placeholder="glsa_...",
                help="Grafana API 토큰을 입력하세요"
            )

    # 대시보드 설정 섹션
    with st.expander("📋 대시보드 설정", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            dashboard_uid = st.text_input(
                "대시보드 UID *",
                placeholder="예: aHOzjCSSk",
                help="Grafana 대시보드의 고유 UID를 입력하세요"
            )
            
            dashboard_name = st.text_input(
                "대시보드 이름 (선택사항)",
                placeholder="예: 996c3efa-4efb-5e69-87e7-4a71ade81e1a",
                help="대시보드 이름 또는 추가 식별자"
            )
            
            org_id = st.number_input(
                "조직 ID",
                min_value=1,
                value=1,
                help="Grafana 조직 ID"
            )
        
        with col2:
            # 시간 범위 설정
            time_range_preset = st.selectbox(
                "시간 범위 프리셋",
                ["사용자 정의", "지난 1시간", "지난 6시간", "지난 24시간", "지난 7일", "지난 30일"],
                index=1
            )
            
            if time_range_preset == "사용자 정의":
                time_from = st.text_input("시작 시간", value="now-1h")
                time_to = st.text_input("종료 시간", value="now")
            else:
                time_mapping = {
                    "지난 1시간": ("now-1h", "now"),
                    "지난 6시간": ("now-6h", "now"),
                    "지난 24시간": ("now-24h", "now"),
                    "지난 7일": ("now-7d", "now"),
                    "지난 30일": ("now-30d", "now")
                }
                time_from, time_to = time_mapping.get(time_range_preset, ("now-1h", "now"))
    
    # 캡처 설정
    with st.expander("🖼️ 캡처 설정"):
        col1, col2 = st.columns(2)
        with col1:
            width = st.number_input("가로 해상도", min_value=800, max_value=3840, value=1920, step=100)
        with col2:
            height = st.number_input("세로 해상도", min_value=600, max_value=2160, value=1080, step=100)
    
    # 분석 프롬프트 설정
    with st.expander("🤖 AI 분석 설정", expanded=True):
        # 템플릿 목록 가져오기
        templates = get_all_templates()
        template_names = get_template_names()
        
        # 템플릿 선택
        selected_template = st.selectbox(
            "프롬프트 템플릿",
            template_names + ["사용자 정의"],
            help="분석 목적에 맞는 템플릿을 선택하세요",
            key="grafana_template_select"
        )
        
        # 선택된 템플릿 정보 표시
        if selected_template != "사용자 정의":
            template_info = templates.get(selected_template, {})
            st.info(f"**{template_info.get('name', selected_template)}**")
            st.info(f"설명: {template_info.get('description', '')}")
            
            prompt_template = template_info.get('prompt', '')
        else:
            prompt_template = st.text_area(
                "분석 프롬프트",
                placeholder="AI에게 요청할 분석 내용을 입력하세요...",
                height=150,
                help="사용자 정의 분석 프롬프트를 입력하세요"
            )
    
    # 분석 실행 버튼
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 Grafana 분석 실행", type="primary", use_container_width=True):
            if not grafana_url:
                st.error("Grafana 서버 URL을 입력해주세요!")
                return
            
            if not api_token:
                st.error("API 토큰을 입력해주세요!")
                return
                
            if not dashboard_uid:
                st.error("대시보드 UID를 입력해주세요!")
                return
            
            if not prompt_template:
                st.error("분석 프롬프트를 입력해주세요!")
                return
            
            # 분석 실행
            execute_grafana_analysis(grafana_url, api_token, dashboard_uid, dashboard_name, org_id, time_from, time_to, width, height, prompt_template)

def image_upload_analysis_tab():
    """이미지 업로드 분석 탭"""
    st.subheader("📁 이미지 업로드 분석")
    
    st.info("📋 **사용법**: Grafana 대시보드 스크린샷을 캡처하여 업로드하거나, 기존 이미지 파일을 업로드하여 AI 분석을 수행할 수 있습니다.")
    
    # 파일 업로드
    uploaded_file = st.file_uploader(
        "이미지 파일 업로드",
        type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
        help="PNG, JPG, JPEG, GIF, BMP 형식의 이미지 파일을 업로드하세요 (최대 10MB)"
    )
    
    # 업로드된 이미지 미리보기
    if uploaded_file is not None:
        st.subheader("📸 업로드된 이미지 미리보기")
        
        # 이미지 표시
        image = Image.open(uploaded_file)
        st.image(image, caption=f"업로드된 파일: {uploaded_file.name}", use_column_width=True)
        
        # 파일 정보 표시
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("파일명", uploaded_file.name)
        with col2:
            st.metric("파일 크기", f"{uploaded_file.size / 1024:.1f} KB")
        with col3:
            st.metric("이미지 크기", f"{image.size[0]} x {image.size[1]}")
    
    # 분석 프롬프트 설정
    with st.expander("🤖 AI 분석 설정", expanded=True):
        # 템플릿 목록 가져오기
        templates = get_all_templates()
        template_names = get_template_names()
        
        # 템플릿 선택
        selected_template = st.selectbox(
            "프롬프트 템플릿",
            template_names + ["사용자 정의"],
            help="분석 목적에 맞는 템플릿을 선택하세요",
            key="image_upload_template_select"
        )
        
        # 선택된 템플릿 정보 표시
        if selected_template != "사용자 정의":
            template_info = templates.get(selected_template, {})
            st.info(f"**{template_info.get('name', selected_template)}**")
            st.info(f"설명: {template_info.get('description', '')}")
            
            prompt_template = template_info.get('prompt', '')
        else:
            prompt_template = st.text_area(
                "분석 프롬프트",
                placeholder="AI에게 요청할 분석 내용을 입력하세요...",
                height=150,
                help="사용자 정의 분석 프롬프트를 입력하세요"
            )
    
    # 분석 실행 버튼
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 이미지 분석 실행", type="primary", use_container_width=True, disabled=uploaded_file is None):
            if not uploaded_file:
                st.error("이미지 파일을 업로드해주세요!")
                return
            
            if not prompt_template:
                st.error("분석 프롬프트를 입력해주세요!")
                return
            
            # 분석 실행
            execute_image_upload_analysis(uploaded_file, prompt_template)

def execute_grafana_analysis(grafana_url, api_token, dashboard_uid, dashboard_name, org_id, time_from, time_to, width, height, prompt_template):
    """Grafana 분석 실행 함수"""
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 1. 대시보드 캡처
        status_text.text("📸 Grafana 대시보드 캡처 중...")
        progress_bar.progress(20)
        
        # 통합 API 호출
        status_text.text("🤖 AI 분석 중...")
        progress_bar.progress(60)
        
        analyze_url = f"{API_BASE_URL}/analyze-dashboard"
        
        params = {
            "grafana_url": grafana_url,
            "api_token": api_token,
            "dashboard_uid": dashboard_uid,
            "dashboard_name": dashboard_name or "",
            "org_id": org_id,
            "time_from": time_from,
            "time_to": time_to,
            "width": width,
            "height": height,
            "prompt_template": prompt_template
        }
        
        response = requests.post(analyze_url, params=params)
        
        if response.status_code == 200:
            result = response.json()
            
            # 3. 결과 표시
            status_text.text("✅ 분석 완료!")
            progress_bar.progress(100)
            
            # 결과 표시
            display_analysis_result(result)
            
        else:
            st.error(f"분석 실패: {response.text}")
            
    except Exception as e:
        st.error(f"분석 중 오류가 발생했습니다: {str(e)}")
    finally:
        progress_bar.empty()
        status_text.empty()

def execute_image_upload_analysis(uploaded_file, prompt_template):
    """이미지 업로드 분석 실행 함수"""
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 파일 업로드 및 분석
        status_text.text("📤 이미지 업로드 중...")
        progress_bar.progress(30)
        
        status_text.text("🤖 AI 분석 중...")
        progress_bar.progress(60)
        
        # 파일 업로드 API 호출
        analyze_url = f"{API_BASE_URL}/analyze-uploaded-image"
        
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        data = {"prompt_template": prompt_template}
        
        response = requests.post(analyze_url, files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            
            # 결과 표시
            status_text.text("✅ 분석 완료!")
            progress_bar.progress(100)
            
            # 결과 표시
            display_analysis_result(result)
            
        else:
            st.error(f"분석 실패: {response.text}")
            
    except Exception as e:
        st.error(f"분석 중 오류가 발생했습니다: {str(e)}")
    finally:
        progress_bar.empty()
        status_text.empty()

def display_analysis_result(result):
    """분석 결과를 표시하는 함수"""
    st.success("분석이 성공적으로 완료되었습니다!")
    
    # 분석 정보
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**분석 ID:** {result['analysis_id']}")
        st.info(f"**대시보드 UID:** {result['dashboard_uid']}")
    with col2:
        st.info(f"**이미지 경로:** {result['image_path']}")
        st.info(f"**생성 시간:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 캡처된 이미지 표시
    if os.path.exists(result['image_path']):
        st.subheader("📸 캡처된 대시보드")
        image = Image.open(result['image_path'])
        st.image(image, caption="Grafana Dashboard Capture", use_column_width=True)
    
    # AI 분석 결과
    st.subheader("🤖 AI 분석 결과")
    st.markdown(result['analysis_result'])
    
    # 결과를 세션 상태에 저장
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = []
    
    st.session_state.analysis_results.append({
        'id': result['analysis_id'],
        'dashboard_uid': result['dashboard_uid'],
        'analysis_result': result['analysis_result'],
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'image_path': result['image_path']
    })

def analysis_history_page():
    """분석 이력 페이지"""
    st.header("📊 분석 이력")
    
    try:
        # API에서 이력 가져오기
        response = requests.get(f"{API_BASE_URL}/analysis-history?limit=50")
        
        if response.status_code == 200:
            data = response.json()
            history = data.get('history', [])
            
            if not history:
                st.info("아직 분석 이력이 없습니다.")
                return
            
            # 데이터프레임으로 변환
            df = pd.DataFrame(history)
            df['created_at'] = pd.to_datetime(df['created_at'])
            df = df.sort_values('created_at', ascending=False)
            
            # 필터링 옵션
            col1, col2 = st.columns(2)
            with col1:
                dashboard_uids = df['dashboard_uid'].unique().tolist() if 'dashboard_uid' in df.columns else []
                selected_dashboard = st.selectbox(
                    "대시보드 필터",
                    ["전체"] + dashboard_uids
                )
            
            with col2:
                date_range = st.date_input(
                    "날짜 범위",
                    value=(df['created_at'].min().date(), df['created_at'].max().date()),
                    format="YYYY-MM-DD"
                )
            
            # 필터 적용
            filtered_df = df.copy()
            if selected_dashboard != "전체" and 'dashboard_uid' in df.columns:
                filtered_df = filtered_df[filtered_df['dashboard_uid'] == selected_dashboard]
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                filtered_df = filtered_df[
                    (filtered_df['created_at'].dt.date >= start_date) &
                    (filtered_df['created_at'].dt.date <= end_date)
                ]
            
            # 이력 표시
            st.markdown(f"**총 {len(filtered_df)}개의 분석 결과**")
            
            for _, row in filtered_df.iterrows():
                dashboard_display = row.get('dashboard_uid', row.get('dashboard_id', 'Unknown'))
                with st.expander(f"🔍 {dashboard_display} - {row['created_at'].strftime('%Y-%m-%d %H:%M:%S')}"):
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        st.write(f"**분석 ID:** {row['id']}")
                        st.write(f"**대시보드 UID:** {dashboard_display}")
                        st.write(f"**생성 시간:** {row['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # 이미지 표시
                        if os.path.exists(row['image_path']):
                            image = Image.open(row['image_path'])
                            st.image(image, caption="Dashboard Capture", width=300)
                    
                    with col2:
                        st.write("**AI 분석 결과:**")
                        st.markdown(row['analysis_result'])
                        
                        # 상세 보기 버튼
                        if st.button(f"상세 보기", key=f"detail_{row['id']}"):
                            view_analysis_detail(row['id'])
        else:
            st.error("이력을 불러오는데 실패했습니다.")
            
    except requests.exceptions.RequestException as e:
        st.error(f"API 연결 오류: {str(e)}")
        st.info("FastAPI 서버가 실행 중인지 확인해주세요.")

def view_analysis_detail(analysis_id):
    """분석 상세 보기"""
    try:
        response = requests.get(f"{API_BASE_URL}/analysis/{analysis_id}")
        
        if response.status_code == 200:
            data = response.json()
            analysis = data['analysis']
            
            st.subheader(f"📋 분석 상세 정보 (ID: {analysis_id})")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**대시보드 UID:** {analysis.get('dashboard_uid', analysis.get('dashboard_id', 'Unknown'))}")
                st.write(f"**생성 시간:** {analysis['created_at']}")
                st.write(f"**이미지 경로:** {analysis['image_path']}")
            
            with col2:
                st.write(f"**프롬프트 템플릿:**")
                st.code(analysis['prompt_template'])
            
            if os.path.exists(analysis['image_path']):
                st.subheader("📸 캡처된 이미지")
                image = Image.open(analysis['image_path'])
                st.image(image, caption="Dashboard Capture", use_column_width=True)
            
            st.subheader("🤖 분석 결과")
            st.markdown(analysis['analysis_result'])
            
        else:
            st.error("분석 정보를 불러오는데 실패했습니다.")
            
    except Exception as e:
        st.error(f"오류 발생: {str(e)}")

def settings_page():
    """설정 페이지"""
    st.header("⚙️ 설정")
    
    # 탭으로 구분
    tab1, tab2, tab3 = st.tabs(["🔧 API 설정", "📋 프롬프트 템플릿", "📖 사용법 안내"])
    
    with tab1:
        st.subheader("🔧 API 설정")
        
        api_url = st.text_input(
            "FastAPI 서버 URL",
            value=API_BASE_URL,
            help="FastAPI 백엔드 서버의 URL을 설정하세요"
        )
        
        if st.button("연결 테스트"):
            try:
                response = requests.get(f"{api_url}/")
                if response.status_code == 200:
                    st.success("✅ API 서버 연결 성공!")
                    st.json(response.json())
                else:
                    st.error(f"❌ API 서버 연결 실패: {response.status_code}")
            except Exception as e:
                st.error(f"❌ 연결 오류: {str(e)}")
        
        st.markdown("---")
        st.subheader("환경변수 안내")
        st.markdown("""
        **필요한 환경변수들:**
        
        ```
        # Azure OpenAI 설정
        AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
        AZURE_OPENAI_API_KEY=your-api-key-here
        AZURE_OPENAI_API_VERSION=2024-02-15-preview
        AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-vision-preview
        
        # Grafana 설정
        GRAFANA_URL=http://your-grafana-server:3000
        GRAFANA_API_TOKEN=your-grafana-api-token
        
        # 데이터베이스 설정
        DATABASE_URL=sqlite:///./analysis_history.db
        
        # 기타 설정
        UPLOAD_DIR=./uploads
        ```
        """)
    
    with tab2:
        st.subheader("📋 프롬프트 템플릿 관리")
        
        # 현재 템플릿 목록 표시
        templates = get_all_templates()
        
        st.markdown("### 📚 사용 가능한 템플릿")
        
        for template_name, template_info in templates.items():
            st.write(f"**{template_info['name']}** - {template_info['description']}")
        
        st.markdown("---")
        st.markdown("### 🔧 템플릿 커스터마이징")
        st.info("""
        **템플릿 수정 방법:**
        
        1. `prompts/` 폴더의 텍스트 파일을 직접 수정하세요
        2. 새로운 템플릿을 추가하려면 `prompts/` 폴더에 새 텍스트 파일을 생성하세요
        3. `prompt_manager.py`의 `TEMPLATE_INFO` 딕셔너리에 새 템플릿 정보를 추가하세요
        4. 수정 후 Streamlit 앱을 재시작하면 변경사항이 적용됩니다
        
        **파일 구조:**
        ```
        prompts/
        ├── 기본_분석.txt
        ├── 성능_분석.txt
        ├── 장애_분석.txt
        ├── 트렌드_분석.txt
        ├── 보안_분석.txt
        └── 용량_계획.txt
        ```
        """)
    
    with tab3:
        st.subheader("📖 사용법 안내")
        
        st.markdown("""
        **🚀 시작하기:**
        
        1. **환경변수 설정**: `.env` 파일을 생성하고 필요한 설정값들을 입력하세요
        2. **FastAPI 서버 실행**: `python main.py` 명령으로 백엔드 서버를 실행하세요
        3. **Streamlit 앱 실행**: `streamlit run app.py` 명령으로 UI를 실행하세요
        4. **대시보드 분석**: 대시보드 ID와 설정을 입력한 후 분석을 실행하세요
        
        **📊 분석 기능:**
        
        - Grafana 대시보드 자동 캡처
        - Azure OpenAI를 활용한 AI 분석
        - 다양한 분석 템플릿 제공
        - 분석 이력 관리 및 조회
        
        **🛠️ 주요 기능:**
        
        - 시간 범위 설정 (프리셋 또는 사용자 정의)
        - 특정 패널 캡처 지원
        - 해상도 조정 가능
        - 프롬프트 템플릿 커스터마이징
        
        **📋 프롬프트 템플릿:**
        
        - **기본 분석**: 전반적인 메트릭과 인사이트 분석
        - **성능 분석**: 성능 메트릭과 병목지점 분석
        - **장애 분석**: 이상 징후와 장애 상황 분석
        - **트렌드 분석**: 데이터 트렌드와 미래 예측
        - **보안 분석**: 보안 관련 메트릭 분석
        - **용량 계획**: 리소스 사용량과 확장 계획
        """)

if __name__ == "__main__":
    main()
