import streamlit as st
import pandas as pd
from bitcoin_wallet import (
    CryptoWallet, CryptoAPI, NETWORK_CONFIGS,
    validate_crypto_address, validate_bitcoin_address, 
    format_crypto_amount, format_bitcoin_amount, format_timestamp
)
import json
from datetime import datetime
import time


def init_session_state():
    """세션 상태 초기화"""
    if 'coin_type' not in st.session_state:
        st.session_state.coin_type = 'bitcoin'  # 기본값: 비트코인
    if 'wallet' not in st.session_state:
        st.session_state.wallet = CryptoWallet(coin_type=st.session_state.coin_type, testnet=True)
    if 'api' not in st.session_state:
        st.session_state.api = CryptoAPI(coin_type=st.session_state.coin_type, testnet=True)
    if 'wallet_loaded' not in st.session_state:
        st.session_state.wallet_loaded = False
    if 'balance_data' not in st.session_state:
        st.session_state.balance_data = None
    if 'transactions_data' not in st.session_state:
        st.session_state.transactions_data = None


def main():
    st.set_page_config(
        page_title="🪙 Multi-Crypto Wallet",
        page_icon="🪙",
        layout="wide"
    )
    
    init_session_state()
    
    # 현재 선택된 코인의 정보 가져오기
    current_config = NETWORK_CONFIGS[st.session_state.coin_type]
    coin_icon = "₿" if st.session_state.coin_type == 'bitcoin' else "🪙"
    
    st.title(f"{coin_icon} {current_config['name']} Wallet Manager")
    st.markdown("---")
    
    # 사이드바 - 코인 및 네트워크 설정
    with st.sidebar:
        st.header("🪙 코인 선택")
        
        # 코인 타입 선택
        coin_options = {
            f"{NETWORK_CONFIGS[coin]['name']} ({NETWORK_CONFIGS[coin]['symbol']})": coin 
            for coin in NETWORK_CONFIGS.keys()
        }
        
        selected_coin_display = st.selectbox(
            "코인 타입",
            list(coin_options.keys()),
            index=list(coin_options.values()).index(st.session_state.coin_type)
        )
        
        selected_coin = coin_options[selected_coin_display]
        
        # 코인 타입이 변경되었을 때 처리
        if selected_coin != st.session_state.coin_type:
            st.session_state.coin_type = selected_coin
            st.session_state.wallet = CryptoWallet(coin_type=selected_coin, testnet=True)
            st.session_state.api = CryptoAPI(coin_type=selected_coin, testnet=True)
            st.session_state.wallet_loaded = False
            st.session_state.balance_data = None
            st.session_state.transactions_data = None
            st.rerun()
        
        st.markdown("---")
        st.header("🌐 네트워크 설정")
        
        network_type = st.selectbox(
            "네트워크 선택",
            ["테스트넷 (권장)", "메인넷 (주의!)"],
            index=0
        )
        
        is_testnet = network_type.startswith("테스트넷")
        
        # 네트워크가 변경되었을 때 처리
        if st.session_state.api.testnet != is_testnet:
            st.session_state.api = CryptoAPI(coin_type=st.session_state.coin_type, testnet=is_testnet)
            st.session_state.wallet = CryptoWallet(coin_type=st.session_state.coin_type, testnet=is_testnet)
            st.session_state.wallet_loaded = False
            st.session_state.balance_data = None
            st.session_state.transactions_data = None
        
        if not is_testnet:
            st.warning("⚠️ **메인넷 주의사항**\n- 실제 암호화폐가 사용됩니다\n- 송금 기능은 비활성화됩니다\n- 테스트넷 사용을 권장합니다")
        else:
            st.info("ℹ️ **테스트넷 모드**\n- 안전한 테스트 환경\n- 실제 가치가 없는 코인\n- 모든 기능 사용 가능")
        
        # BitMobick 특별 안내
        if st.session_state.coin_type == 'bitmobick':
            st.success("🪙 **BitMobick 실제 네트워크**\n- [blockchain2.mobick.info](https://blockchain2.mobick.info)와 연결\n- 실제 블록체인 데이터 조회\n- 실제 주소 생성 및 잔액 확인 가능")
        
        st.markdown("---")
        
        # 지갑 상태 표시
        st.header("💼 지갑 상태")
        if st.session_state.wallet_loaded:
            st.success(f"✅ {current_config['name']} 지갑이 로드되었습니다")
            if st.session_state.wallet.address:
                st.text(f"주소: {st.session_state.wallet.address[:10]}...")
                st.text(f"코인: {current_config['symbol']}")
        else:
            st.warning("⏳ 지갑을 생성하거나 가져오세요")
    
    # 메인 컨텐츠 - 탭 구성
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔐 지갑 관리", "💰 잔액 조회", "📋 거래 내역", "💸 송금", "📱 QR 코드"])
    
    with tab1:
        show_wallet_management_tab()
    
    with tab2:
        show_balance_tab()
    
    with tab3:
        show_transactions_tab()
    
    with tab4:
        show_send_tab()
    
    with tab5:
        show_qr_tab()


def show_wallet_management_tab():
    """지갑 관리 탭"""
    st.header("🔐 지갑 관리")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🆕 새 지갑 생성")
        st.info("새로운 비트코인 지갑을 생성합니다. 개인키를 안전하게 보관하세요!")
        
        if st.button("🔑 새 지갑 생성", key="generate_wallet"):
            try:
                wallet_info = st.session_state.wallet.generate_wallet()
                st.session_state.wallet_loaded = True
                
                st.success("✅ 새 지갑이 생성되었습니다!")
                
                # 지갑 정보 표시
                st.subheader("📋 지갑 정보")
                
                with st.expander("🔑 개인키 (Private Key)", expanded=False):
                    st.warning("⚠️ 개인키는 절대 타인과 공유하지 마세요!")
                    st.code(wallet_info['private_key'])
                
                with st.expander("🔓 공개키 (Public Key)"):
                    st.code(wallet_info['public_key'])
                
                st.subheader("🏠 비트코인 주소")
                st.code(wallet_info['address'])
                
                with st.expander("💾 WIF (Wallet Import Format)"):
                    st.info("지갑을 다른 곳에서 가져올 때 사용할 수 있는 형식입니다.")
                    st.code(wallet_info['wif'])
                
                # 지갑 정보 다운로드
                wallet_json = json.dumps(wallet_info, indent=2)
                st.download_button(
                    label="💾 지갑 정보 다운로드 (JSON)",
                    data=wallet_json,
                    file_name=f"bitcoin_wallet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
                
            except Exception as e:
                st.error(f"❌ 지갑 생성 실패: {str(e)}")
    
    with col2:
        st.subheader("📥 기존 지갑 가져오기")
        st.info("개인키 또는 WIF를 사용하여 기존 지갑을 가져옵니다.")
        
        import_method = st.radio(
            "가져오기 방법",
            ["개인키 (Hex)", "WIF", "JSON 파일"]
        )
        
        if import_method == "개인키 (Hex)":
            private_key = st.text_input(
                "개인키 입력 (64자 hex)",
                type="password",
                placeholder="예: 1234567890abcdef..."
            )
            
            if st.button("📥 개인키로 가져오기"):
                if private_key:
                    try:
                        wallet_info = st.session_state.wallet.import_wallet(private_key)
                        st.session_state.wallet_loaded = True
                        st.success("✅ 지갑을 성공적으로 가져왔습니다!")
                        st.code(f"주소: {wallet_info['address']}")
                    except Exception as e:
                        st.error(f"❌ 지갑 가져오기 실패: {str(e)}")
                else:
                    st.error("개인키를 입력해주세요.")
        
        elif import_method == "WIF":
            wif = st.text_input(
                "WIF 입력",
                type="password",
                placeholder="예: 5J..."
            )
            
            if st.button("📥 WIF로 가져오기"):
                if wif:
                    try:
                        wallet_info = st.session_state.wallet.import_wallet(wif)
                        st.session_state.wallet_loaded = True
                        st.success("✅ 지갑을 성공적으로 가져왔습니다!")
                        st.code(f"주소: {wallet_info['address']}")
                    except Exception as e:
                        st.error(f"❌ 지갑 가져오기 실패: {str(e)}")
                else:
                    st.error("WIF를 입력해주세요.")
        
        elif import_method == "JSON 파일":
            uploaded_file = st.file_uploader(
                "지갑 JSON 파일 선택",
                type=['json'],
                help="이전에 다운로드한 지갑 JSON 파일을 업로드하세요."
            )
            
            if uploaded_file is not None:
                try:
                    wallet_data = json.load(uploaded_file)
                    
                    if 'private_key' in wallet_data:
                        wallet_info = st.session_state.wallet.import_wallet(wallet_data['private_key'])
                        st.session_state.wallet_loaded = True
                        st.success("✅ JSON 파일에서 지갑을 성공적으로 가져왔습니다!")
                        st.code(f"주소: {wallet_info['address']}")
                    else:
                        st.error("❌ 올바른 지갑 JSON 파일이 아닙니다.")
                        
                except Exception as e:
                    st.error(f"❌ JSON 파일 처리 실패: {str(e)}")


def show_balance_tab():
    """잔액 조회 탭"""
    st.header("💰 잔액 조회")
    
    if not st.session_state.wallet_loaded:
        st.warning("⚠️ 먼저 지갑을 생성하거나 가져와주세요.")
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"📍 지갑 주소")
        st.code(st.session_state.wallet.address)
    
    with col2:
        if st.button("🔄 잔액 새로고침"):
            st.session_state.balance_data = None  # 캐시 초기화
    
    # 잔액 조회
    if st.session_state.balance_data is None:
        try:
            with st.spinner("잔액 조회 중..."):
                balance_data = st.session_state.api.get_balance(st.session_state.wallet.address)
                st.session_state.balance_data = balance_data
        except Exception as e:
            st.error(f"❌ 잔액 조회 실패: {str(e)}")
            return
    
    balance_data = st.session_state.balance_data
    
    # 잔액 정보 표시
    col1, col2, col3, col4 = st.columns(4)
    
    # 현재 코인 설정 가져오기
    current_config = NETWORK_CONFIGS[st.session_state.coin_type]
    coin_symbol = balance_data.get('coin_symbol', current_config['symbol'])
    decimals = current_config['decimals']
    
    with col1:
        st.metric(
            "💰 확인된 잔액",
            format_crypto_amount(balance_data['confirmed_balance'], coin_symbol, decimals)
        )
    
    with col2:
        st.metric(
            "⏳ 미확인 잔액",
            format_crypto_amount(balance_data['unconfirmed_balance'], coin_symbol, decimals)
        )
    
    with col3:
        st.metric(
            "📊 총 잔액",
            format_crypto_amount(balance_data['total_balance'], coin_symbol, decimals)
        )
    
    with col4:
        st.metric(
            "🔄 거래 횟수",
            f"{balance_data['tx_count']} 회"
        )
    
    # 추가 정보
    st.subheader("📈 거래 통계")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "📥 총 수신",
            format_crypto_amount(balance_data['total_received'], coin_symbol, decimals)
        )
    
    with col2:
        st.metric(
            "📤 총 송신",
            format_crypto_amount(balance_data['total_sent'], coin_symbol, decimals)
        )


def show_transactions_tab():
    """거래 내역 탭"""
    st.header("📋 거래 내역")
    
    if not st.session_state.wallet_loaded:
        st.warning("⚠️ 먼저 지갑을 생성하거나 가져와주세요.")
        return
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        tx_limit = st.selectbox("조회할 거래 수", [10, 25, 50, 100], index=0)
    
    with col2:
        if st.button("🔄 거래 내역 새로고침"):
            st.session_state.transactions_data = None
    
    # 거래 내역 조회
    if st.session_state.transactions_data is None:
        try:
            with st.spinner("거래 내역 조회 중..."):
                transactions_data = st.session_state.api.get_transactions(
                    st.session_state.wallet.address, 
                    limit=tx_limit
                )
                st.session_state.transactions_data = transactions_data
        except Exception as e:
            st.error(f"❌ 거래 내역 조회 실패: {str(e)}")
            return
    
    transactions_data = st.session_state.transactions_data
    
    if not transactions_data:
        st.info("📭 거래 내역이 없습니다.")
        return
    
    # 거래 내역 표시
    current_config = NETWORK_CONFIGS[st.session_state.coin_type]
    
    for i, tx in enumerate(transactions_data):
        coin_symbol = tx.get('coin_symbol', current_config['symbol'])
        decimals = current_config['decimals']
        amount_formatted = format_crypto_amount(abs(tx['amount']), coin_symbol, decimals)
        
        with st.expander(f"{'📥' if tx['type'] == 'received' else '📤'} {tx['type'].title()} - {amount_formatted} - {tx['hash'][:16]}..."):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**거래 정보**")
                st.write(f"• 해시: `{tx['hash']}`")
                st.write(f"• 타입: {tx['type'].title()}")
                st.write(f"• 금액: {format_crypto_amount(tx['amount'], coin_symbol, decimals)}")
                st.write(f"• 수수료: {format_crypto_amount(tx['fees'], coin_symbol, decimals)}")
                st.write(f"• 크기: {tx['size']} bytes")
            
            with col2:
                st.write("**확인 정보**")
                st.write(f"• 확인 수: {tx['confirmations']}")
                st.write(f"• 확인 상태: {'✅ 확인됨' if tx['confirmed'] else '⏳ 대기중'}")
                if tx['received']:
                    st.write(f"• 수신 시간: {format_timestamp(tx['received'])}")
            
            # 거래 상세 조회 버튼
            if st.button(f"🔍 상세 보기", key=f"detail_{i}"):
                try:
                    with st.spinner("상세 정보 조회 중..."):
                        detail = st.session_state.api.get_transaction_details(tx['hash'])
                        
                        st.subheader("상세 거래 정보")
                        st.json(detail)
                except Exception as e:
                    st.error(f"상세 정보 조회 실패: {str(e)}")


def show_send_tab():
    """송금 탭"""
    current_config = NETWORK_CONFIGS[st.session_state.coin_type]
    coin_name = current_config['name']
    coin_symbol = current_config['symbol']
    decimals = current_config['decimals']
    
    st.header(f"💸 {coin_name} 송금")
    
    if not st.session_state.wallet_loaded:
        st.warning("⚠️ 먼저 지갑을 생성하거나 가져와주세요.")
        return
    
    # 메인넷에서는 송금 기능 비활성화
    if not st.session_state.api.testnet:
        st.error("🚫 **보안상 메인넷에서는 송금 기능이 비활성화됩니다.**")
        st.info("💡 테스트넷 모드로 전환하여 송금 기능을 테스트해보세요.")
        return
    
    st.warning(f"⚠️ **{coin_name} 테스트넷 송금**\n이 기능은 테스트넷에서만 작동하며, 실제 가치가 없는 테스트 {coin_name}을 사용합니다.")
    
    # 현재 잔액 표시
    if st.session_state.balance_data:
        balance_formatted = format_crypto_amount(
            st.session_state.balance_data['confirmed_balance'], 
            coin_symbol, 
            decimals
        )
        st.info(f"💰 현재 잔액: {balance_formatted}")
    
    # 송금 폼
    with st.form("send_form"):
        st.subheader("📝 송금 정보 입력")
        
        to_address = st.text_input(
            "🎯 수신자 주소",
            placeholder=f"예: {coin_name} 주소",
            help=f"유효한 {coin_name} 주소를 입력하세요."
        )
        
        amount = st.number_input(
            f"💰 송금 금액 ({coin_symbol})",
            min_value=1 / (10 ** decimals),
            max_value=1.0,
            value=0.001,
            step=1 / (10 ** decimals),
            format=f"%.{decimals}f",
            help=f"송금할 {coin_symbol} 금액을 입력하세요."
        )
        
        # 예상 수수료 (테스트넷에서는 낮음)
        estimated_fee = 0.00001
        st.info(f"📊 예상 수수료: {format_crypto_amount(estimated_fee, coin_symbol, decimals)}")
        st.info(f"💵 총 필요 금액: {format_crypto_amount(amount + estimated_fee, coin_symbol, decimals)}")
        
        submitted = st.form_submit_button("💸 송금하기", type="primary")
        
        if submitted:
            # 입력 검증
            if not to_address:
                st.error("수신자 주소를 입력해주세요.")
            elif not validate_crypto_address(to_address, st.session_state.coin_type):
                st.error(f"유효하지 않은 {coin_name} 주소입니다.")
            elif amount <= 0:
                st.error("송금 금액은 0보다 커야 합니다.")
            elif st.session_state.balance_data and amount + estimated_fee > st.session_state.balance_data['confirmed_balance']:
                st.error("잔액이 부족합니다.")
            else:
                # 송금 확인
                st.warning("⚠️ **송금 확인**")
                st.write(f"• 수신자: `{to_address}`")
                st.write(f"• 금액: {format_crypto_amount(amount, coin_symbol, decimals)}")
                st.write(f"• 수수료: {format_crypto_amount(estimated_fee, coin_symbol, decimals)}")
                st.write(f"• 총 차감: {format_crypto_amount(amount + estimated_fee, coin_symbol, decimals)}")
                
                if st.button("✅ 송금 확인"):
                    try:
                        with st.spinner("송금 처리 중..."):
                            result = st.session_state.api.send_transaction(
                                st.session_state.wallet.address,
                                to_address,
                                amount,
                                st.session_state.wallet.private_key
                            )
                            
                            if result['success']:
                                st.success(f"✅ {coin_name} 송금이 완료되었습니다!")
                                st.info(f"📝 거래 ID: `{result['tx_hash']}`")
                                st.info(result['message'])
                                
                                # 잔액 업데이트
                                st.session_state.balance_data = None
                                st.session_state.transactions_data = None
                            else:
                                st.error("❌ 송금에 실패했습니다.")
                                
                    except Exception as e:
                        st.error(f"❌ 송금 실패: {str(e)}")


def show_qr_tab():
    """QR 코드 탭"""
    current_config = NETWORK_CONFIGS[st.session_state.coin_type]
    coin_name = current_config['name']
    coin_symbol = current_config['symbol']
    decimals = current_config['decimals']
    
    st.header("📱 QR 코드")
    
    if not st.session_state.wallet_loaded:
        st.warning("⚠️ 먼저 지갑을 생성하거나 가져와주세요.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📍 주소 QR 코드")
        st.write(f"다른 사람이 당신에게 {coin_name}을 보낼 때 사용할 수 있습니다.")
        
        try:
            qr_img = st.session_state.wallet.generate_qr_code(st.session_state.wallet.address)
            st.image(f"data:image/png;base64,{qr_img}", caption=f"{coin_name} 주소 QR 코드")
            st.code(st.session_state.wallet.address)
        except Exception as e:
            st.error(f"QR 코드 생성 실패: {str(e)}")
    
    with col2:
        st.subheader("💰 결제 요청 QR 코드")
        st.write("특정 금액을 요청하는 QR 코드를 생성할 수 있습니다.")
        
        amount_request = st.number_input(
            f"요청 금액 ({coin_symbol})",
            min_value=1 / (10 ** decimals),
            value=0.001,
            step=1 / (10 ** decimals),
            format=f"%.{decimals}f"
        )
        
        label = st.text_input("라벨 (선택사항)", placeholder="결제 목적")
        message = st.text_input("메시지 (선택사항)", placeholder="추가 메모")
        
        if st.button("🎯 결제 요청 QR 생성"):
            try:
                # BIP21 URI 스키마 사용 (BitMobick도 비트코인 호환 형식 사용)
                uri_scheme = "bitcoin" if st.session_state.coin_type == 'bitcoin' else "bitcoin"  # BitMobick도 bitcoin URI 사용
                uri = f"{uri_scheme}:{st.session_state.wallet.address}"
                params = []
                
                if amount_request > 0:
                    params.append(f"amount={amount_request:.{decimals}f}")
                if label:
                    params.append(f"label={label}")
                if message:
                    params.append(f"message={message}")
                
                if params:
                    uri += "?" + "&".join(params)
                
                qr_img = st.session_state.wallet.generate_qr_code(uri)
                st.image(f"data:image/png;base64,{qr_img}", caption="결제 요청 QR 코드")
                st.code(uri)
                
                amount_formatted = format_crypto_amount(amount_request, coin_symbol, decimals)
                st.success(f"✅ {amount_formatted} 결제 요청 QR 코드가 생성되었습니다!")
                
            except Exception as e:
                st.error(f"결제 요청 QR 생성 실패: {str(e)}")


if __name__ == "__main__":
    main()
