#!/usr/bin/env python3
"""BitMobick 전용 지갑 웹 애플리케이션"""

import streamlit as st
import json
from io import StringIO
from mobick_wallet import (
    MobickWallet, MobickAPI, MOBICK_CONFIG,
    validate_mobick_address, format_mobick_amount, format_timestamp
)

# 페이지 설정
st.set_page_config(
    page_title="BitMobick 지갑",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session_state():
    """세션 상태 초기화"""
    if 'wallet' not in st.session_state:
        st.session_state.wallet = None
    if 'wallet_loaded' not in st.session_state:
        st.session_state.wallet_loaded = False
    if 'balance_data' not in st.session_state:
        st.session_state.balance_data = None
    if 'transactions_data' not in st.session_state:
        st.session_state.transactions_data = None
    if 'external_address' not in st.session_state:
        st.session_state.external_address = ""
    if 'external_balance' not in st.session_state:
        st.session_state.external_balance = None
    if 'external_transactions' not in st.session_state:
        st.session_state.external_transactions = None

def sidebar():
    """사이드바 구성"""
    st.sidebar.title("🪙 BitMobick 지갑")
    st.sidebar.markdown("---")
    
    # 네트워크 선택
    st.sidebar.subheader("⚙️ 네트워크 설정")
    is_testnet = st.sidebar.checkbox("테스트넷 사용", value=False)
    
    if is_testnet:
        st.sidebar.info("ℹ️ **테스트넷 모드**\n- 안전한 테스트 환경\n- 실제 가치가 없는 코인")
    else:
        st.sidebar.warning("⚠️ **메인넷 모드**\n- 실제 BitMobick 사용\n- 신중하게 사용하세요")
    
    st.sidebar.success("🪙 **BitMobick 실제 네트워크**\n- [blockchain2.mobick.info](https://blockchain2.mobick.info)와 연결\n- 실제 블록체인 데이터 조회")
    
    return is_testnet

def show_wallet_management(is_testnet):
    """지갑 관리 섹션"""
    st.header("💼 지갑 관리")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🆕 새 지갑 생성", type="primary"):
            try:
                wallet = MobickWallet(testnet=is_testnet)
                wallet_info = wallet.generate_wallet()
                st.session_state.wallet = wallet
                st.session_state.wallet_loaded = True
                st.session_state.balance_data = None
                st.session_state.transactions_data = None
                
                st.success("✅ 새 지갑이 생성되었습니다!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 지갑 생성 실패: {str(e)}")
    
    with col2:
        if st.button("📥 지갑 가져오기"):
            st.session_state.show_import = True
            st.rerun()
    
    # 지갑 가져오기 인터페이스
    if hasattr(st.session_state, 'show_import') and st.session_state.show_import:
        st.markdown("---")
        st.subheader("📥 지갑 가져오기")
        
        import_method = st.selectbox(
            "가져오기 방법",
            ["개인키 (Hex)", "WIF (Wallet Import Format)", "JSON 파일"]
        )
        
        try:
            if import_method == "개인키 (Hex)":
                private_key = st.text_input("개인키 입력", type="password", placeholder="64자리 16진수 개인키")
                if st.button("가져오기") and private_key:
                    wallet = MobickWallet(testnet=is_testnet)
                    wallet.import_wallet(private_key)
                    st.session_state.wallet = wallet
                    st.session_state.wallet_loaded = True
                    st.session_state.show_import = False
                    st.success("✅ 지갑을 성공적으로 가져왔습니다!")
                    st.rerun()
            
            elif import_method == "WIF (Wallet Import Format)":
                wif = st.text_input("WIF 입력", type="password", placeholder="5, K, L, 9, c로 시작하는 WIF")
                if st.button("가져오기") and wif:
                    wallet = MobickWallet(testnet=is_testnet)
                    wallet.import_wallet(wif)
                    st.session_state.wallet = wallet
                    st.session_state.wallet_loaded = True
                    st.session_state.show_import = False
                    st.success("✅ 지갑을 성공적으로 가져왔습니다!")
                    st.rerun()
            
            elif import_method == "JSON 파일":
                uploaded_file = st.file_uploader("JSON 파일 선택", type="json")
                if uploaded_file is not None:
                    try:
                        wallet_data = json.load(uploaded_file)
                        wallet = MobickWallet(testnet=is_testnet)
                        wallet.import_wallet(wallet_data['private_key'])
                        st.session_state.wallet = wallet
                        st.session_state.wallet_loaded = True
                        st.session_state.show_import = False
                        st.success("✅ 지갑을 성공적으로 가져왔습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ JSON 파일 처리 실패: {str(e)}")
        
        except Exception as e:
            st.error(f"❌ 지갑 가져오기 실패: {str(e)}")
        
        if st.button("취소"):
            st.session_state.show_import = False
            st.rerun()

def show_wallet_info():
    """지갑 정보 표시"""
    if not st.session_state.wallet_loaded or not st.session_state.wallet:
        st.info("💡 지갑을 생성하거나 가져와주세요.")
        return
    
    wallet = st.session_state.wallet
    
    st.header("📋 지갑 정보")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.text_input("🏠 주소", value=wallet.address, disabled=True)
        st.text_input("🔓 공개키", value=wallet.public_key, disabled=True)
        
        # 민감한 정보는 토글로 표시
        show_sensitive = st.checkbox("🔒 민감한 정보 표시")
        if show_sensitive:
            st.text_input("🔑 개인키", value=wallet.private_key, disabled=True)
            st.text_input("📜 WIF", value=wallet.wif, disabled=True)
    
    with col2:
        # QR 코드 생성
        if st.button("📱 주소 QR 코드"):
            qr_code = wallet.generate_qr_code(wallet.address)
            st.image(qr_code, caption=f"BitMobick 주소: {wallet.address}", width=200)
        
        # 지갑 내보내기
        if st.button("💾 지갑 내보내기"):
            wallet_data = {
                'address': wallet.address,
                'public_key': wallet.public_key,
                'private_key': wallet.private_key,
                'wif': wallet.wif,
                'network': 'testnet' if wallet.testnet else 'mainnet'
            }
            
            json_data = json.dumps(wallet_data, indent=2)
            st.download_button(
                label="📄 JSON 파일 다운로드",
                data=json_data,
                file_name=f"mobick_wallet_{wallet.address[:8]}.json",
                mime="application/json"
            )

def show_balance_tab(is_testnet):
    """잔액 조회 탭"""
    if not st.session_state.wallet_loaded or not st.session_state.wallet:
        st.info("💡 지갑을 먼저 생성하거나 가져와주세요.")
        return
    
    wallet = st.session_state.wallet
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader(f"💰 지갑 잔액: {wallet.address}")
    
    with col2:
        if st.button("🔄 잔액 새로고침"):
            st.session_state.balance_data = None
    
    # 잔액 조회
    if st.session_state.balance_data is None:
        with st.spinner("잔액 조회 중..."):
            try:
                api = MobickAPI(testnet=is_testnet)
                balance_data = api.get_balance(wallet.address)
                st.session_state.balance_data = balance_data
            except Exception as e:
                st.error(f"❌ 잔액 조회 실패: {str(e)}")
                return
    
    balance_data = st.session_state.balance_data
    
    # 잔액 정보 표시
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💎 확정 잔액",
            format_mobick_amount(balance_data['confirmed_balance'])
        )
    
    with col2:
        st.metric(
            "⏳ 미확정 잔액",
            format_mobick_amount(balance_data['unconfirmed_balance'])
        )
    
    with col3:
        st.metric(
            "💰 총 잔액",
            format_mobick_amount(balance_data['total_balance'])
        )
    
    with col4:
        st.metric(
            "📊 트랜잭션 수",
            f"{balance_data['tx_count']}개"
        )
    
    # 추가 정보
    if balance_data.get('error'):
        st.warning(f"⚠️ 참고: {balance_data['error']}")
    
    # 탐색기 링크
    explorer_url = f"{MOBICK_CONFIG['explorer_url']}/address/{wallet.address}"
    st.markdown(f"🌐 [블록체인 탐색기에서 확인]({explorer_url})")

def show_transactions_tab(is_testnet):
    """거래 내역 탭"""
    if not st.session_state.wallet_loaded or not st.session_state.wallet:
        st.info("💡 지갑을 먼저 생성하거나 가져와주세요.")
        return
    
    wallet = st.session_state.wallet
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader(f"📋 거래 내역: {wallet.address}")
    
    with col2:
        if st.button("🔄 내역 새로고침"):
            st.session_state.transactions_data = None
    
    # 트랜잭션 조회
    if st.session_state.transactions_data is None:
        with st.spinner("거래 내역 조회 중..."):
            try:
                api = MobickAPI(testnet=is_testnet)
                transactions_data = api.get_transactions(wallet.address, limit=10)
                st.session_state.transactions_data = transactions_data
            except Exception as e:
                st.error(f"❌ 거래 내역 조회 실패: {str(e)}")
                return
    
    transactions_data = st.session_state.transactions_data
    
    if not transactions_data:
        st.info("📭 거래 내역이 없습니다.")
        return
    
    # 거래 내역 표시
    for i, tx in enumerate(transactions_data):
        with st.expander(f"거래 #{i+1}: {tx['hash'][:16]}..."):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("**해시:**", tx['hash'])
                st.write("**타입:**", "📤 송금" if tx['type'] == 'sent' else "📥 수신")
            
            with col2:
                st.write("**금액:**", format_mobick_amount(abs(tx['amount'])))
                st.write("**확인:**", f"{tx['confirmations']}회")
            
            with col3:
                st.write("**시간:**", format_timestamp(tx['received']))
                st.write("**수수료:**", format_mobick_amount(tx['fees']))
            
            # 탐색기 링크
            explorer_tx_url = f"{MOBICK_CONFIG['explorer_url']}/tx/{tx['hash']}"
            st.markdown(f"🌐 [탐색기에서 확인]({explorer_tx_url})")

def show_external_address_tab(is_testnet):
    """외부 주소 조회 탭"""
    st.subheader("🔍 외부 주소 조회")
    st.markdown("다른 BitMobick 주소의 잔액과 거래 내역을 확인할 수 있습니다.")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        external_address = st.text_input(
            "🏠 BitMobick 주소 입력",
            value=st.session_state.external_address,
            placeholder="1로 시작하는 BitMobick 주소를 입력하세요"
        )
    
    with col2:
        st.write("")  # 여백
        if st.button("🔍 조회하기", type="primary"):
            if external_address:
                if validate_mobick_address(external_address):
                    st.session_state.external_address = external_address
                    st.session_state.external_balance = None
                    st.session_state.external_transactions = None
                    st.rerun()
                else:
                    st.error("❌ 유효하지 않은 BitMobick 주소입니다.")
            else:
                st.error("❌ 주소를 입력해주세요.")
    
    if st.session_state.external_address:
        address = st.session_state.external_address
        
        # 잔액 조회
        if st.session_state.external_balance is None:
            with st.spinner("외부 주소 잔액 조회 중..."):
                try:
                    api = MobickAPI(testnet=is_testnet)
                    balance_data = api.get_balance(address)
                    st.session_state.external_balance = balance_data
                except Exception as e:
                    st.error(f"❌ 잔액 조회 실패: {str(e)}")
                    return
        
        # 거래 내역 조회
        if st.session_state.external_transactions is None:
            with st.spinner("외부 주소 거래 내역 조회 중..."):
                try:
                    api = MobickAPI(testnet=is_testnet)
                    transactions_data = api.get_transactions(address, limit=10)
                    st.session_state.external_transactions = transactions_data
                except Exception as e:
                    st.error(f"❌ 거래 내역 조회 실패: {str(e)}")
                    return
        
        # 결과 표시
        st.markdown("---")
        st.subheader(f"📊 주소 정보: {address}")
        
        balance_data = st.session_state.external_balance
        
        # 잔액 정보
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "💎 확정 잔액",
                format_mobick_amount(balance_data['confirmed_balance'])
            )
        
        with col2:
            st.metric(
                "⏳ 미확정 잔액",
                format_mobick_amount(balance_data['unconfirmed_balance'])
            )
        
        with col3:
            st.metric(
                "💰 총 잔액",
                format_mobick_amount(balance_data['total_balance'])
            )
        
        with col4:
            st.metric(
                "📊 트랜잭션 수",
                f"{balance_data['tx_count']}개"
            )
        
        # 거래 내역
        transactions_data = st.session_state.external_transactions
        
        if transactions_data:
            st.subheader("📋 최근 거래 내역")
            
            for i, tx in enumerate(transactions_data[:5]):  # 최대 5개만 표시
                with st.expander(f"거래 #{i+1}: {tx['hash'][:16]}..."):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**해시:**", tx['hash'])
                        st.write("**타입:**", "📤 송금" if tx['type'] == 'sent' else "📥 수신")
                    
                    with col2:
                        st.write("**금액:**", format_mobick_amount(abs(tx['amount'])))
                        st.write("**확인:**", f"{tx['confirmations']}회")
                    
                    with col3:
                        st.write("**시간:**", format_timestamp(tx['received']))
                        st.write("**수수료:**", format_mobick_amount(tx['fees']))
                    
                    # 탐색기 링크
                    explorer_tx_url = f"{MOBICK_CONFIG['explorer_url']}/tx/{tx['hash']}"
                    st.markdown(f"🌐 [탐색기에서 확인]({explorer_tx_url})")
        else:
            st.info("📭 거래 내역이 없습니다.")
        
        # 탐색기 링크
        explorer_url = f"{MOBICK_CONFIG['explorer_url']}/address/{address}"
        st.markdown(f"🌐 [블록체인 탐색기에서 자세히 보기]({explorer_url})")

def main():
    """메인 애플리케이션"""
    init_session_state()
    
    # 사이드바
    is_testnet = sidebar()
    
    # 메인 컨텐츠
    st.title("🪙 BitMobick 지갑")
    st.markdown("BitMobick 전용 웹 지갑 - 실제 블록체인과 연결")
    
    # 지갑 관리
    show_wallet_management(is_testnet)
    
    st.markdown("---")
    
    # 지갑 정보
    show_wallet_info()
    
    st.markdown("---")
    
    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs(["💰 내 지갑 잔액", "📋 내 거래 내역", "🔍 외부 주소 조회", "ℹ️ 정보"])
    
    with tab1:
        show_balance_tab(is_testnet)
    
    with tab2:
        show_transactions_tab(is_testnet)
    
    with tab3:
        show_external_address_tab(is_testnet)
    
    with tab4:
        st.subheader("ℹ️ BitMobick 정보")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **🪙 BitMobick (MO)**
            - 비트코인 호환 암호화폐
            - 1로 시작하는 주소 형식
            - 실제 블록체인 네트워크
            
            **🔧 지원 기능**
            - ✅ 지갑 생성/가져오기
            - ✅ 실시간 잔액 조회
            - ✅ 거래 내역 확인
            - ✅ 외부 주소 조회
            - ✅ QR 코드 생성
            """)
        
        with col2:
            st.markdown("""
            **🌐 관련 링크**
            - [BitMobick 공식 사이트](https://btc-mobick-v2.webflow.io/)
            - [블록체인 탐색기](https://blockchain2.mobick.info/)
            
            **⚠️ 주의사항**
            - 개인키를 안전하게 보관하세요
            - 메인넷에서는 실제 자산이 사용됩니다
            - 송금 전 주소를 다시 한 번 확인하세요
            """)
        
        st.info("💡 이 지갑은 BitMobick 전용으로 제작되었습니다. 실제 블록체인과 연결되어 정확한 데이터를 제공합니다.")

if __name__ == "__main__":
    main()
