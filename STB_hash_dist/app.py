import hashlib
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import time
from typing import List, Tuple

def get_stb_slot(stb_id: str, max_slots: int = 100) -> int:
    """
    STB_ID 문자열을 SHA-256으로 해싱하여 1~max_slots 사이의 슬롯 번호를 반환합니다.

    Args:
        stb_id: 슬롯을 계산할 STB_ID 문자열
        max_slots: 최대 슬롯 개수 (기본값: 100)

    Returns:
        1부터 max_slots 사이의 정수 슬롯 번호
    """
    # 1. STB_ID 문자열을 바이트로 인코딩합니다.
    encoded_id = stb_id.encode('utf-8')

    # 2. SHA-256 해시 객체를 생성하고 해시 값을 16진수 문자열로 얻습니다.
    hashed_hex = hashlib.sha256(encoded_id).hexdigest()

    # 3. 16진수 해시 값을 10진수 정수로 변환합니다.
    hash_int = int(hashed_hex, 16)

    # 4. 모듈로 연산과 +1을 통해 1~max_slots 사이의 슬롯 번호를 계산합니다.
    slot_number = (hash_int % max_slots) + 1

    return slot_number

def process_stb_ids_batch(stb_ids: List[str], batch_size: int = 10000, max_slots: int = 100) -> List[Tuple[str, int]]:
    """
    STB_ID 목록을 배치 단위로 처리하여 슬롯 번호를 계산합니다.
    성능 향상을 위해 배치 처리 방식을 사용합니다.
    
    Args:
        stb_ids: 처리할 STB_ID 목록
        batch_size: 배치 크기
        max_slots: 최대 슬롯 개수
        
    Returns:
        (STB_ID, 슬롯번호) 튜플의 리스트
    """
    results = []
    
    for i in range(0, len(stb_ids), batch_size):
        batch = stb_ids[i:i + batch_size]
        batch_results = [(stb_id, get_stb_slot(stb_id, max_slots)) for stb_id in batch]
        results.extend(batch_results)
        
        # 진행률 표시를 위한 yield (선택사항)
        if i % (batch_size * 10) == 0:
            yield i, len(stb_ids)
    
    return results

def create_slot_distribution_chart(slot_counts: pd.Series) -> go.Figure:
    """슬롯 분포 차트를 생성합니다."""
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=slot_counts.index,
        y=slot_counts.values,
        name='슬롯별 STB 수',
        marker_color='skyblue'
    ))
    
    fig.update_layout(
        title='슬롯별 STB 분포',
        xaxis_title='슬롯 번호',
        yaxis_title='STB 수',
        showlegend=False,
        height=400
    )
    
    return fig

def create_slot_heatmap(slot_counts: pd.Series, max_slots: int = 100) -> go.Figure:
    """슬롯 분포를 히트맵으로 표시합니다."""
    # 슬롯 수에 따라 적절한 그리드 크기 계산
    if max_slots <= 100:
        cols = 10
        rows = min(10, (max_slots + 9) // 10)  # 올림 계산
    elif max_slots <= 1000:
        cols = 20
        rows = min(50, (max_slots + 19) // 20)
    elif max_slots <= 10000:
        cols = 50
        rows = min(200, (max_slots + 49) // 50)
    else:
        cols = 100
        rows = min(10000, (max_slots + 99) // 100)
    
    # 그리드 생성
    grid = np.zeros((rows, cols))
    
    for slot in range(1, max_slots + 1):
        if slot > rows * cols:
            break
        row = (slot - 1) // cols
        col = (slot - 1) % cols
        grid[row, col] = slot_counts.get(slot, 0)
    
    fig = go.Figure(data=go.Heatmap(
        z=grid,
        x=[f'Col {i+1}' for i in range(cols)],
        y=[f'Row {i+1}' for i in range(rows)],
        colorscale='Blues',
        text=grid.astype(int),
        texttemplate="%{text}",
        textfont={"size": min(10, 200 // max(cols, rows))},
        hoverongaps=False
    ))
    
    fig.update_layout(
        title=f'슬롯 분포 히트맵 ({rows}x{cols} 그리드, 총 {max_slots}개 슬롯)',
        height=min(800, max(400, rows * 20))
    )
    
    return fig

def main():
    st.set_page_config(
        page_title="STB 슬롯 분배 분석기",
        page_icon="📡",
        layout="wide"
    )
    
    st.title("📡 STB 슬롯 분배 분석기")
    st.markdown("STB_ID 목록을 업로드하여 슬롯 분배 결과와 통계를 확인할 수 있습니다.")
    
    # 사이드바 설정
    st.sidebar.header("설정")
    
    # 슬롯 개수 설정
    st.sidebar.subheader("슬롯 개수 설정")
    slot_input_method = st.sidebar.radio(
        "입력 방식 선택",
        ["슬라이더", "직접 입력"]
    )
    
    if slot_input_method == "슬라이더":
        max_slots = st.sidebar.slider(
            "최대 슬롯 개수", 
            min_value=10, 
            max_value=10000, 
            value=100, 
            step=10,
            help="슬라이더로 슬롯 개수를 조정합니다 (10-10,000)"
        )
    else:
        max_slots = st.sidebar.number_input(
            "최대 슬롯 개수", 
            min_value=10, 
            max_value=1000000, 
            value=100, 
            step=1,
            help="직접 숫자를 입력하여 슬롯 개수를 설정합니다 (10-1,000,000)"
        )
    
    st.sidebar.info(f"현재 설정: {max_slots:,}개 슬롯")
    
    # 배치 크기 설정
    st.sidebar.subheader("처리 설정")
    batch_size = st.sidebar.slider("배치 크기", 1000, 50000, 10000, step=1000)
    
    # 파일 업로드
    uploaded_file = st.file_uploader(
        "CSV 파일을 업로드하세요 (STB_ID 목록)",
        type=['csv', 'txt'],
        help="STB_ID가 각 줄에 하나씩 있는 CSV 또는 텍스트 파일"
    )
    
    if uploaded_file is not None:
        try:
            # 파일 내용 읽기
            content = uploaded_file.read().decode('utf-8')
            
            # STB_ID 목록 파싱 (빈 줄 제거)
            stb_ids = [line.strip() for line in content.split('\n') if line.strip()]
            
            if not stb_ids:
                st.error("파일에 유효한 STB_ID가 없습니다.")
                return
            
            st.success(f"총 {len(stb_ids):,}개의 STB_ID를 로드했습니다.")
            
            # 처리 시작
            if st.button("슬롯 계산 시작", type="primary"):
                st.info("슬롯 계산을 시작합니다. 대용량 데이터의 경우 시간이 걸릴 수 있습니다.")
                
                # 진행률 표시
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                start_time = time.time()
                
                # 배치 처리로 슬롯 계산
                results = []
                total_processed = 0
                
                for processed, total in process_stb_ids_batch(stb_ids, batch_size, max_slots):
                    total_processed = processed
                    progress = min(processed / len(stb_ids), 1.0)
                    progress_bar.progress(progress)
                    status_text.text(f"처리 중... {processed:,}/{len(stb_ids):,} ({progress:.1%})")
                
                # 마지막 배치 처리
                final_batch = stb_ids[total_processed:]
                final_results = [(stb_id, get_stb_slot(stb_id, max_slots)) for stb_id in final_batch]
                results.extend(final_results)
                
                progress_bar.progress(1.0)
                status_text.text("완료!")
                
                processing_time = time.time() - start_time
                st.success(f"슬롯 계산 완료! 처리 시간: {processing_time:.2f}초")
                
                # 결과를 DataFrame으로 변환
                df = pd.DataFrame(results, columns=['STB_ID', 'Slot'])
                
                # 통계 계산
                slot_counts = df['Slot'].value_counts().sort_index()
                total_stb = len(df)
                unique_slots = len(slot_counts)
                min_slot_count = slot_counts.min() if len(slot_counts) > 0 else 0
                max_slot_count = slot_counts.max() if len(slot_counts) > 0 else 0
                avg_slot_count = total_stb / max_slots
                
                # 통계 표시
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("총 STB 수", f"{total_stb:,}")
                
                with col2:
                    st.metric("사용된 슬롯 수", unique_slots)
                
                with col3:
                    st.metric("최소 슬롯당 STB 수", min_slot_count)
                
                with col4:
                    st.metric("최대 슬롯당 STB 수", max_slot_count)
                
                # 분포 차트
                col1, col2 = st.columns(2)
                
                with col1:
                    st.plotly_chart(create_slot_distribution_chart(slot_counts), use_container_width=True)
                
                with col2:
                    st.plotly_chart(create_slot_heatmap(slot_counts, max_slots), use_container_width=True)
                
                # 상세 통계 테이블
                st.subheader("슬롯별 상세 통계")
                
                # 슬롯별 통계 DataFrame 생성
                slot_stats = pd.DataFrame({
                    '슬롯 번호': range(1, max_slots + 1),
                    'STB 수': [slot_counts.get(i, 0) for i in range(1, max_slots + 1)],
                    '비율 (%)': [slot_counts.get(i, 0) / total_stb * 100 for i in range(1, max_slots + 1)]
                })
                
                # 사용되지 않은 슬롯 표시
                unused_slots = slot_stats[slot_stats['STB 수'] == 0]
                if len(unused_slots) > 0:
                    st.warning(f"사용되지 않은 슬롯: {len(unused_slots)}개")
                    st.dataframe(unused_slots[['슬롯 번호']], use_container_width=True)
                
                # 전체 슬롯 통계 표시
                st.dataframe(slot_stats, use_container_width=True)
                
                # 결과 다운로드
                st.subheader("결과 다운로드")
                
                # CSV 다운로드
                csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="결과 CSV 다운로드",
                    data=csv_data,
                    file_name=f"stb_slot_results_{len(stb_ids)}.csv",
                    mime="text/csv"
                )
                
                # 통계 요약 다운로드
                summary_data = slot_stats.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="통계 요약 CSV 다운로드",
                    data=summary_data,
                    file_name=f"stb_slot_summary_{len(stb_ids)}.csv",
                    mime="text/csv"
                )
                
        except Exception as e:
            st.error(f"파일 처리 중 오류가 발생했습니다: {str(e)}")
    
    else:
        st.info("CSV 파일을 업로드하여 분석을 시작하세요.")
        
        # 사용 예시
        st.subheader("📋 사용 예시")
        st.markdown("""
        CSV 파일 형식:
        ```
        {4655F3A8-D531-11E5-9115-01A83A673161}
        {DC186E50-CECD-11EE-AFAE-7787E87EF42F}
        {A1B2C3D4-E5F6-11EE-1234-567890ABCDEF}
        ```
        
        또는 텍스트 파일로도 업로드 가능합니다.
        """)
        
        # 샘플 데이터로 테스트
        st.subheader("🧪 샘플 데이터로 테스트")
        if st.button("샘플 데이터 생성 및 테스트"):
            # 샘플 STB_ID 생성
            sample_stb_ids = [
                "{4655F3A8-D531-11E5-9115-01A83A673161}",
                "{DC186E50-CECD-11EE-AFAE-7787E87EF42F}",
                "{A1B2C3D4-E5F6-11EE-1234-567890ABCDEF}",
                "{FEDCBA98-7654-11EE-4321-ABCDEF123456}",
                "{12345678-9ABC-11EE-DEF0-987654321ABC}"
            ]
            
            st.write(f"샘플 STB_ID (슬롯 개수: {max_slots}):")
            for stb_id in sample_stb_ids:
                slot = get_stb_slot(stb_id, max_slots)
                st.write(f"- {stb_id} → 슬롯 {slot}")

if __name__ == "__main__":
    main()