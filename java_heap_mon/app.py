import streamlit as st
import subprocess
import time
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import threading
import queue
import psutil
import json
import shutil

# 페이지 설정
st.set_page_config(
    page_title="Java Heap Memory Monitor",
    page_icon="☕",
    layout="wide"
)

# 힙덤프 폴더 생성
HEAP_DUMP_DIR = "heap_dump"
if not os.path.exists(HEAP_DUMP_DIR):
    os.makedirs(HEAP_DUMP_DIR)

class JavaHeapMonitor:
    def __init__(self):
        self.monitoring = False
        self.data_queue = queue.Queue()
        self.monitor_thread = None
        self.process_id = None
        self.java_home = self._find_java_home()
        self.jstat_path = self._find_jstat_path()
        self.jmap_path = self._find_jmap_path()
        
    def _find_java_home(self):
        """JAVA_HOME 환경변수 또는 java 명령어로부터 Java 경로 찾기"""
        # JAVA_HOME 환경변수 확인
        java_home = os.environ.get('JAVA_HOME')
        if java_home and os.path.exists(java_home):
            return java_home
        
        # which java로 java 경로 찾기
        try:
            java_path = shutil.which('java')
            if java_path:
                # java 경로에서 JAVA_HOME 추정 (../..)
                java_dir = os.path.dirname(java_path)
                if 'bin' in java_dir:
                    return os.path.dirname(java_dir)
        except:
            pass
        
        # 일반적인 CentOS 7 Java 설치 경로들 확인
        common_paths = [
            '/usr/lib/jvm/java-1.8.0-openjdk',
            '/usr/lib/jvm/java-11-openjdk',
            '/usr/lib/jvm/java-17-openjdk',
            '/usr/java/jdk1.8.0_*',
            '/usr/java/jdk-11*',
            '/usr/java/jdk-17*'
        ]
        
        for path_pattern in common_paths:
            if '*' in path_pattern:
                import glob
                matches = glob.glob(path_pattern)
                if matches:
                    return matches[0]
            elif os.path.exists(path_pattern):
                return path_pattern
        
        return None
    
    def _find_jstat_path(self):
        """jstat 명령어 경로 찾기"""
        if self.java_home:
            jstat_path = os.path.join(self.java_home, 'bin', 'jstat')
            if os.path.exists(jstat_path):
                return jstat_path
        
        # PATH에서 jstat 찾기
        jstat_path = shutil.which('jstat')
        if jstat_path:
            return jstat_path
        
        return 'jstat'  # 기본값
    
    def _find_jmap_path(self):
        """jmap 명령어 경로 찾기"""
        if self.java_home:
            jmap_path = os.path.join(self.java_home, 'bin', 'jmap')
            if os.path.exists(jmap_path):
                return jmap_path
        
        # PATH에서 jmap 찾기
        jmap_path = shutil.which('jmap')
        if jmap_path:
            return jmap_path
        
        return 'jmap'  # 기본값
    
    def is_java_process(self, pid):
        """Java 프로세스인지 확인"""
        try:
            process = psutil.Process(pid)
            cmdline = ' '.join(process.cmdline())
            return 'java' in cmdline.lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def get_heap_usage(self, pid):
        """jstat을 사용하여 heap 사용량 정보 가져오기"""
        try:
            # jstat -gc <pid> 명령어 실행 (CentOS 7 호환)
            result = subprocess.run(
                [self.jstat_path, '-gc', str(pid)],
                capture_output=True,
                text=True,
                timeout=5,  # 타임아웃을 5초로 단축
                env=os.environ.copy()
            )
            
            if result.returncode != 0:
                return None
                
            lines = result.stdout.strip().split('\n')
            if len(lines) < 2:
                return None
                
            # 헤더와 데이터 분리
            headers = lines[0].split()
            values = lines[1].split()
            
            if len(headers) != len(values):
                return None
                
            # 딕셔너리로 변환
            data = dict(zip(headers, values))
            
            # Heap 사용량 계산 (S0C + S1C + EC + OC)
            try:
                s0c = float(data.get('S0C', 0))
                s1c = float(data.get('S1C', 0))
                ec = float(data.get('EC', 0))
                oc = float(data.get('OC', 0))
                
                total_heap = s0c + s1c + ec + oc
                
                # 사용 중인 heap 계산 (S0U + S1U + EU + OU)
                s0u = float(data.get('S0U', 0))
                s1u = float(data.get('S1U', 0))
                eu = float(data.get('EU', 0))
                ou = float(data.get('OU', 0))
                
                used_heap = s0u + s1u + eu + ou
                
                # Old Heap 영역 계산 (OC, OU)
                old_heap_total = oc
                old_heap_used = ou
                old_heap_usage_percent = (old_heap_used / old_heap_total * 100) if old_heap_total > 0 else 0
                
                # Young Heap 영역 계산 (S0C + S1C + EC, S0U + S1U + EU)
                young_heap_total = s0c + s1c + ec
                young_heap_used = s0u + s1u + eu
                young_heap_usage_percent = (young_heap_used / young_heap_total * 100) if young_heap_total > 0 else 0
                
                # GC 정보 (Full GC 횟수)
                fgc = float(data.get('FGC', 0))  # Full GC count
                fgct = float(data.get('FGCT', 0))  # Full GC time
                
                return {
                    'timestamp': datetime.now(),
                    'total_heap_kb': total_heap,
                    'used_heap_kb': used_heap,
                    'free_heap_kb': total_heap - used_heap,
                    'heap_usage_percent': (used_heap / total_heap * 100) if total_heap > 0 else 0,
                    'old_heap_total_kb': old_heap_total,
                    'old_heap_used_kb': old_heap_used,
                    'old_heap_usage_percent': old_heap_usage_percent,
                    'young_heap_total_kb': young_heap_total,
                    'young_heap_used_kb': young_heap_used,
                    'young_heap_usage_percent': young_heap_usage_percent,
                    'full_gc_count': fgc,
                    'full_gc_time': fgct,
                    's0c': s0c, 's1c': s1c, 'ec': ec, 'oc': oc,
                    's0u': s0u, 's1u': s1u, 'eu': eu, 'ou': ou
                }
            except (ValueError, KeyError):
                return None
                
        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            st.error(f"Heap 정보 수집 중 오류: {e}")
            return None
    
    def monitor_loop(self):
        """모니터링 루프"""
        while self.monitoring:
            if self.process_id:
                try:
                    heap_data = self.get_heap_usage(self.process_id)
                    if heap_data:
                        self.data_queue.put(heap_data)
                except Exception as e:
                    # 오류 발생 시에도 계속 모니터링
                    pass
            time.sleep(10)  # 10초마다 수집
    
    def start_monitoring(self, pid):
        """모니터링 시작"""
        if self.monitoring:
            self.stop_monitoring()
            
        self.process_id = pid
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
    
    def get_data(self):
        """큐에서 데이터 가져오기"""
        data = []
        while not self.data_queue.empty():
            try:
                data.append(self.data_queue.get_nowait())
            except queue.Empty:
                break
        return data

def create_heap_dump(pid, jmap_path):
    """힙덤프 생성"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"heap_dump_{pid}_{timestamp}.hprof"
        filepath = os.path.join(HEAP_DUMP_DIR, filename)
        
        # jmap을 사용하여 힙덤프 생성 (CentOS 7 호환)
        result = subprocess.run(
            [jmap_path, '-dump:format=b,file=' + filepath, str(pid)],
            capture_output=True,
            text=True,
            timeout=120,  # CentOS 7에서는 더 긴 타임아웃 필요
            env=os.environ.copy()
        )
        
        if result.returncode == 0:
            return filepath, None
        else:
            return None, result.stderr
    except subprocess.TimeoutExpired:
        return None, "힙덤프 생성 시간 초과"
    except Exception as e:
        return None, str(e)

def main():
    st.title("☕ Java Heap Memory Monitor")
    st.markdown("---")
    
    # 세션 상태 초기화
    if 'monitor' not in st.session_state:
        st.session_state.monitor = JavaHeapMonitor()
    if 'heap_data' not in st.session_state:
        st.session_state.heap_data = []
    if 'monitoring_start_time' not in st.session_state:
        st.session_state.monitoring_start_time = None
    if 'last_full_gc_count' not in st.session_state:
        st.session_state.last_full_gc_count = 0
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = True
    
    monitor = st.session_state.monitor
    
    # 사이드바 - 설정
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # 프로세스 ID 입력
        pid_input = st.text_input(
            "Java 프로세스 ID",
            placeholder="예: 12345",
            help="모니터링할 Java 프로세스의 PID를 입력하세요"
        )
        
        # 모니터링 시간 범위 선택
        time_range = st.selectbox(
            "모니터링 시간 범위",
            ["1시간", "3시간", "6시간", "12시간", "24시간"],
            index=0
        )
        
        # 자동 새로고침 설정
        auto_refresh = st.checkbox(
            "자동 새로고침 (10초)",
            value=st.session_state.auto_refresh,
            help="10초마다 그래프를 자동으로 업데이트합니다 (브라우저 새로고침 필요)"
        )
        st.session_state.auto_refresh = auto_refresh
        
        # 수동 새로고침 버튼
        if st.button("🔄 수동 새로고침"):
            st.rerun()
        
        # 시간 범위를 분으로 변환
        time_ranges = {
            "1시간": 60,
            "3시간": 180,
            "6시간": 360,
            "12시간": 720,
            "24시간": 1440
        }
        max_minutes = time_ranges[time_range]
        
        st.markdown("---")
        
        # 모니터링 컨트롤
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("▶️ 시작", disabled=monitor.monitoring):
                if pid_input:
                    try:
                        pid = int(pid_input)
                        if monitor.is_java_process(pid):
                            monitor.start_monitoring(pid)
                            st.session_state.monitoring_start_time = datetime.now()
                            st.success(f"프로세스 {pid} 모니터링 시작!")
                        else:
                            st.error("Java 프로세스가 아닙니다.")
                    except ValueError:
                        st.error("올바른 프로세스 ID를 입력하세요.")
                else:
                    st.error("프로세스 ID를 입력하세요.")
        
        with col2:
            if st.button("⏹️ 중지", disabled=not monitor.monitoring):
                monitor.stop_monitoring()
                st.success("모니터링 중지!")
        
        st.markdown("---")
        
        # 힙덤프 생성
        st.header("💾 힙덤프")
        if st.button("📥 힙덤프 생성", disabled=not pid_input or not monitor.monitoring):
            if pid_input:
                with st.spinner("힙덤프 생성 중..."):
                    filepath, error = create_heap_dump(int(pid_input), monitor.jmap_path)
                    if filepath:
                        st.success(f"힙덤프 생성 완료: {filepath}")
                    else:
                        st.error(f"힙덤프 생성 실패: {error}")
        
        # Java 도구 정보 표시
        st.markdown("---")
        st.header("🔧 Java 도구 정보")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text(f"JAVA_HOME: {monitor.java_home or 'Not found'}")
        with col2:
            st.text(f"jstat: {monitor.jstat_path}")
        with col3:
            st.text(f"jmap: {monitor.jmap_path}")
    
    # 자동 새로고침 안내
    if st.session_state.auto_refresh and monitor.monitoring:
        st.info("🔄 자동 새로고침 활성화됨 - 브라우저에서 F5를 눌러 새로고침하세요")
    
    # 메인 영역
    if monitor.monitoring:
        # 실시간 데이터 수집
        new_data = monitor.get_data()
        if new_data:
            st.session_state.heap_data.extend(new_data)
            
            # Full GC 발생 감지
            for data in new_data:
                current_fgc = data.get('full_gc_count', 0)
                if current_fgc > st.session_state.last_full_gc_count:
                    st.warning(f"🚨 Full GC 발생! (총 {current_fgc}회, 이전: {st.session_state.last_full_gc_count}회)")
                    st.session_state.last_full_gc_count = current_fgc
        
        # 시간 범위에 따른 데이터 필터링
        if st.session_state.heap_data:
            cutoff_time = datetime.now() - timedelta(minutes=max_minutes)
            st.session_state.heap_data = [
                d for d in st.session_state.heap_data 
                if d['timestamp'] >= cutoff_time
            ]
        
        # 상태 표시
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("상태", "🟢 모니터링 중")
        with col2:
            if st.session_state.heap_data:
                latest = st.session_state.heap_data[-1]
                st.metric("전체 Heap 사용률", f"{latest['heap_usage_percent']:.1f}%")
            else:
                st.metric("전체 Heap 사용률", "N/A")
        with col3:
            if st.session_state.heap_data:
                latest = st.session_state.heap_data[-1]
                st.metric("Old Heap 사용률", f"{latest['old_heap_usage_percent']:.1f}%")
            else:
                st.metric("Old Heap 사용률", "N/A")
        with col4:
            if st.session_state.heap_data:
                latest = st.session_state.heap_data[-1]
                st.metric("Full GC 횟수", f"{latest['full_gc_count']:.0f}회")
            else:
                st.metric("Full GC 횟수", "N/A")
        
        # 차트 표시
        if st.session_state.heap_data:
            try:
                df = pd.DataFrame(st.session_state.heap_data)
                
                # 데이터 검증
                if len(df) == 0:
                    st.warning("데이터가 없습니다.")
                    return
                
                # Heap 사용률 차트 (전체, Old, Young)
                fig_usage = go.Figure()
                
                # 전체 Heap 사용률
                if 'heap_usage_percent' in df.columns:
                    fig_usage.add_trace(go.Scatter(
                        x=df['timestamp'],
                        y=df['heap_usage_percent'],
                        mode='lines+markers',
                        name='전체 Heap 사용률 (%)',
                        line=dict(color='#FF6B6B', width=2),
                        marker=dict(size=4)
                    ))
                
                # Old Heap 사용률
                if 'old_heap_usage_percent' in df.columns:
                    fig_usage.add_trace(go.Scatter(
                        x=df['timestamp'],
                        y=df['old_heap_usage_percent'],
                        mode='lines+markers',
                        name='Old Heap 사용률 (%)',
                        line=dict(color='#FF8C00', width=2),
                        marker=dict(size=4)
                    ))
                
                # Young Heap 사용률
                if 'young_heap_usage_percent' in df.columns:
                    fig_usage.add_trace(go.Scatter(
                        x=df['timestamp'],
                        y=df['young_heap_usage_percent'],
                        mode='lines+markers',
                        name='Young Heap 사용률 (%)',
                        line=dict(color='#32CD32', width=2),
                        marker=dict(size=4)
                    ))
                
                fig_usage.update_layout(
                    title="Heap 메모리 사용률 (전체/Old/Young)",
                    xaxis_title="시간",
                    yaxis_title="사용률 (%)",
                    hovermode='x unified',
                    height=400
                )
                
                st.plotly_chart(fig_usage, use_container_width=True)
                
            except Exception as e:
                st.error(f"차트 생성 중 오류: {e}")
                st.write("데이터 샘플:", st.session_state.heap_data[:3] if st.session_state.heap_data else "데이터 없음")
            
            try:
                # Heap 크기 차트 (Old Heap 중심)
                fig_size = go.Figure()
                
                if 'old_heap_used_kb' in df.columns:
                    fig_size.add_trace(go.Scatter(
                        x=df['timestamp'],
                        y=df['old_heap_used_kb'] / 1024,  # MB로 변환
                        mode='lines+markers',
                        name='Old Heap 사용 중 (MB)',
                        line=dict(color='#FF8C00', width=3),
                        fill='tonexty'
                    ))
                
                if 'old_heap_total_kb' in df.columns:
                    fig_size.add_trace(go.Scatter(
                        x=df['timestamp'],
                        y=df['old_heap_total_kb'] / 1024,  # MB로 변환
                        mode='lines+markers',
                        name='Old Heap 전체 (MB)',
                        line=dict(color='#FFA500', width=2),
                        fill='tonexty'
                    ))
                
                if 'used_heap_kb' in df.columns:
                    fig_size.add_trace(go.Scatter(
                        x=df['timestamp'],
                        y=df['used_heap_kb'] / 1024,  # MB로 변환
                        mode='lines+markers',
                        name='전체 Heap 사용 중 (MB)',
                        line=dict(color='#4ECDC4', width=2)
                    ))
                
                fig_size.update_layout(
                    title="Old Heap 메모리 크기 (Full GC 모니터링)",
                    xaxis_title="시간",
                    yaxis_title="크기 (MB)",
                    hovermode='x unified',
                    height=400
                )
                
                st.plotly_chart(fig_size, use_container_width=True)
                
            except Exception as e:
                st.error(f"Heap 크기 차트 생성 중 오류: {e}")
            
            try:
                # Full GC 횟수 차트
                fig_gc = go.Figure()
                
                if 'full_gc_count' in df.columns:
                    fig_gc.add_trace(go.Scatter(
                        x=df['timestamp'],
                        y=df['full_gc_count'],
                        mode='lines+markers',
                        name='Full GC 횟수',
                        line=dict(color='#DC143C', width=2),
                        marker=dict(size=6)
                    ))
                
                fig_gc.update_layout(
                    title="Full GC 발생 횟수",
                    xaxis_title="시간",
                    yaxis_title="GC 횟수",
                    hovermode='x unified',
                    height=300
                )
                
                st.plotly_chart(fig_gc, use_container_width=True)
                
            except Exception as e:
                st.error(f"Full GC 차트 생성 중 오류: {e}")
            
            try:
                # 상세 정보 테이블
                with st.expander("📊 상세 정보"):
                    display_df = df.copy()
                    display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 안전한 컬럼 처리
                    if 'heap_usage_percent' in display_df.columns:
                        display_df['heap_usage_percent'] = display_df['heap_usage_percent'].round(2)
                    if 'old_heap_usage_percent' in display_df.columns:
                        display_df['old_heap_usage_percent'] = display_df['old_heap_usage_percent'].round(2)
                    if 'young_heap_usage_percent' in display_df.columns:
                        display_df['young_heap_usage_percent'] = display_df['young_heap_usage_percent'].round(2)
                    if 'used_heap_kb' in display_df.columns:
                        display_df['used_heap_mb'] = (display_df['used_heap_kb'] / 1024).round(2)
                    if 'total_heap_kb' in display_df.columns:
                        display_df['total_heap_mb'] = (display_df['total_heap_kb'] / 1024).round(2)
                    if 'old_heap_used_kb' in display_df.columns:
                        display_df['old_heap_used_mb'] = (display_df['old_heap_used_kb'] / 1024).round(2)
                    if 'old_heap_total_kb' in display_df.columns:
                        display_df['old_heap_total_mb'] = (display_df['old_heap_total_kb'] / 1024).round(2)
                    if 'full_gc_count' in display_df.columns:
                        display_df['full_gc_count'] = display_df['full_gc_count'].astype(int)
                    
                    # 사용 가능한 컬럼만 선택
                    available_columns = []
                    column_mapping = {
                        'timestamp': 'timestamp',
                        'heap_usage_percent': 'heap_usage_percent',
                        'old_heap_usage_percent': 'old_heap_usage_percent',
                        'young_heap_usage_percent': 'young_heap_usage_percent',
                        'old_heap_used_mb': 'old_heap_used_mb',
                        'old_heap_total_mb': 'old_heap_total_mb',
                        'full_gc_count': 'full_gc_count'
                    }
                    
                    for col in column_mapping.keys():
                        if col in display_df.columns:
                            available_columns.append(col)
                    
                    if available_columns:
                        st.dataframe(display_df[available_columns], use_container_width=True)
                    else:
                        st.warning("표시할 데이터가 없습니다.")
                        
            except Exception as e:
                st.error(f"상세 정보 테이블 생성 중 오류: {e}")
        else:
            st.info("데이터 수집 중... 잠시만 기다려주세요.")
    
    else:
        st.info("👈 사이드바에서 Java 프로세스 ID를 입력하고 모니터링을 시작하세요.")
        
        # 사용 가능한 Java 프로세스 목록 표시
        st.subheader("🔍 실행 중인 Java 프로세스")
        try:
            java_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'java' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                        java_processes.append({
                            'PID': proc.info['pid'],
                            'Name': proc.info['name'],
                            'Command': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if java_processes:
                st.dataframe(pd.DataFrame(java_processes), use_container_width=True)
            else:
                st.warning("실행 중인 Java 프로세스를 찾을 수 없습니다.")
        except Exception as e:
            st.error(f"프로세스 목록을 가져오는 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()
