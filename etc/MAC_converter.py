import streamlit as st

def remove_leading_zeros(mac_address):
    """
    각 MAC 주소에서 콜론(:)으로 구분된 각 자리의 앞 0을 제거하는 함수
    예: 00:09:74:52:63:3c -> 0:9:74:52:63:3c
    """
    # 각 자리를 콜론으로 분리
    parts = mac_address.split(':')
    # 각 자리에서 앞 0을 제거
    processed_parts = [part.lstrip('0') or '0' for part in parts]
    # 처리된 각 자리를 다시 콜론으로 연결
    return ':'.join(processed_parts)

def process_file(uploaded_file):
    """
    업로드된 파일의 MAC 주소를 처리하는 함수
    """
    # 파일을 읽어서 텍스트로 변환
    content = uploaded_file.getvalue().decode('utf-8')
    # 각 줄을 리스트로 분리
    lines = content.strip().split('\n')
    
    processed_lines = []
    for line in lines:
        # MAC 주소만 처리 (공백이나 빈 줄이 있다면 건너뜀)
        if line.strip():
            processed_lines.append(remove_leading_zeros(line.strip()))
            
    return '\n'.join(processed_lines)

st.title("MAC 주소 앞 0 제거 프로그램")

st.write("텍스트 파일을 업로드하면 MAC 주소의 각 자리에서 앞자리의 '0'이 제거된 새로운 파일을 다운로드할 수 있습니다.")

uploaded_file = st.file_uploader("파일을 선택하세요", type=['txt'])

if uploaded_file is not None:
    # 파일을 처리하고 새로운 내용 생성
    processed_content = process_file(uploaded_file)
    
    # 다운로드 버튼 생성
    st.download_button(
        label="처리된 파일 다운로드",
        data=processed_content,
        file_name="processed_mac_addresses.txt",
        mime="text/plain"
    )
    
    st.write("### 처리 결과 미리보기")
    st.code(processed_content)