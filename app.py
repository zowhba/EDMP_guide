import streamlit as st
import pandas as pd
from upbit_api import UpbitAPI, get_market_all, get_ticker
import time
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go


def init_session_state():
    """세션 상태 초기화"""
    if 'api_client' not in st.session_state:
        st.session_state.api_client = None
    if 'markets' not in st.session_state:
        st.session_state.markets = None
    if 'accounts' not in st.session_state:
        st.session_state.accounts = None


def format_currency(amount, currency='KRW'):
    """통화 포맷팅"""
    if currency == 'KRW':
        return f"₩{amount:,.0f}"
    else:
        return f"{amount:.8f} {currency}"


def main():
    st.set_page_config(
        page_title="Upbit 거래소 자동매매 시스템",
        page_icon="🚀",
        layout="wide"
    )
    
    init_session_state()
    
    st.title("🚀 Upbit 거래소 자동매매 시스템")
    st.markdown("---")
    
    # 사이드바 - API 키 입력
    with st.sidebar:
        st.header("🔐 API 설정")
        
        # API 키 입력 (기본값으로 제공된 키 설정)
        access_key = st.text_input(
            "Access Key", 
            value="6sjw61RTiZuiHYNresEReyMzyKBVNl5J6Xc9szJ4",
            type="password"
        )
        secret_key = st.text_input(
            "Secret Key", 
            value="VklrGf36pbNKmGYLuPjQiwwxWX8tiSxBKWNQbxKy",
            type="password"
        )
        
        if st.button("🔑 API 연결"):
            if access_key and secret_key:
                try:
                    st.session_state.api_client = UpbitAPI(access_key, secret_key)
                    # 연결 테스트
                    accounts = st.session_state.api_client.get_accounts()
                    st.session_state.accounts = accounts
                    st.success("✅ API 연결 성공!")
                except Exception as e:
                    error_msg = str(e)
                    if "권한이 없습니다" in error_msg:
                        st.error(f"❌ {error_msg}")
                        st.warning("🔧 **해결 방법**:\n1. Upbit 웹사이트 로그인\n2. 마이페이지 → Open API 관리\n3. API 키 권한에서 '자산조회', '주문조회', '주문하기' 권한 활성화")
                    elif "인증에 실패" in error_msg:
                        st.error(f"❌ {error_msg}")
                        st.warning("🔧 API 키가 올바른지 확인해주세요.")
                    else:
                        st.error(f"❌ API 연결 실패: {error_msg}")
            else:
                st.error("Access Key와 Secret Key를 입력해주세요.")
        
        # 자동 새로고침 설정
        st.header("🔄 자동 새로고침")
        auto_refresh = st.checkbox("자동 새로고침 활성화", value=False)
        if auto_refresh:
            refresh_interval = st.selectbox(
                "새로고침 간격 (초)", 
                [5, 10, 30, 60], 
                index=2
            )
        
        # 디버그 모드
        st.header("🛠️ 디버그")
        debug_mode = st.checkbox("디버그 모드 (개발자용)", value=False)
        st.session_state.debug_mode = debug_mode
    
    # 메인 컨텐츠
    if st.session_state.api_client is None:
        st.warning("🔑 사이드바에서 API 키를 입력하고 연결해주세요.")
        return
    
    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs(["💰 자산현황", "📊 주문하기", "📋 주문내역", "📈 마켓정보"])
    
    with tab1:
        show_accounts_tab()
    
    with tab2:
        show_trading_tab()
    
    with tab3:
        show_orders_tab()
    
    with tab4:
        show_market_tab()
    
    # 자동 새로고침
    if auto_refresh and 'refresh_interval' in locals():
        time.sleep(refresh_interval)
        st.rerun()


def show_accounts_tab():
    """자산현황 탭"""
    st.header("💰 자산 현황")
    
    # 자산 금액 표시 토글
    col_refresh, col_toggle = st.columns([3, 1])
    with col_refresh:
        if st.button("🔄 자산현황 새로고침"):
            try:
                st.session_state.accounts = st.session_state.api_client.get_accounts()
                # 새로고침 시 모든 캐시 초기화
                for key in ['current_prices', 'cached_currencies', 'valid_markets']:
                    if key in st.session_state:
                        del st.session_state[key]
            except Exception as e:
                error_msg = str(e)
                if "권한이 없습니다" in error_msg:
                    st.error(f"❌ {error_msg}")
                    st.warning("🔧 **해결 방법**: Upbit에서 API 키 권한에 '자산조회' 권한을 활성화해주세요.")
                elif "인증에 실패" in error_msg:
                    st.error(f"❌ {error_msg}")
                    st.warning("🔧 API 키가 올바른지 확인해주세요.")
                else:
                    st.error(f"❌ 자산현황 조회 실패: {error_msg}")
                return
    
    with col_toggle:
        hide_amounts = st.checkbox("🔒 금액 숨기기", key="hide_amounts_checkbox")
        # 전역적으로 사용할 수 있도록 세션에 저장
        st.session_state.hide_amounts = hide_amounts
    
    if st.session_state.accounts:
        # 유효한 마켓 목록을 먼저 가져오기 (캐싱)
        if 'valid_markets' not in st.session_state:
            try:
                all_markets = get_market_all()
                st.session_state.valid_markets = {
                    market['market'].replace('KRW-', ''): market['market'] 
                    for market in all_markets if market['market'].startswith('KRW-')
                }
            except Exception as e:
                st.warning(f"⚠️ 마켓 정보 조회 실패: {str(e)}")
                st.session_state.valid_markets = {}
        
        # 보유 코인 목록 추출 (KRW 제외, 유효한 마켓만)
        held_currencies = []
        for acc in st.session_state.accounts:
            currency = acc['currency']
            balance = float(acc['balance'])
            locked = float(acc['locked'])
            
            # KRW 제외, 잔고가 있고, 유효한 마켓인 경우만 포함
            if (balance > 0 or locked > 0) and currency != 'KRW':
                # 유효한 마켓인지 확인 (최소 2자 이상, 알파벳/숫자만)
                if (len(currency) >= 2 and 
                    currency.replace('-', '').replace('_', '').isalnum() and
                    currency in st.session_state.valid_markets):
                    held_currencies.append(currency)
                else:
                    # 유효하지 않은 마켓은 로그만 남기고 스킵
                    if st.session_state.get('debug_mode', False):  # 디버그 모드일 때만 표시
                        st.info(f"ℹ️ 유효하지 않은 마켓 스킵: {currency}")
        
        # 현재가 정보를 세션에 캐시하여 중복 API 호출 방지
        if 'current_prices' not in st.session_state or set(held_currencies) != set(st.session_state.get('cached_currencies', [])):
            st.session_state.current_prices = {}
            if held_currencies:
                try:
                    # 전체 배치로 현재가 조회 시도
                    markets = [f'KRW-{currency}' for currency in held_currencies]
                    if st.session_state.get('debug_mode', False):
                        st.info(f"🔍 현재가 조회 시도: {', '.join(markets)}")
                    
                    ticker_data = get_ticker(markets)
                    st.session_state.current_prices = {
                        ticker['market'].replace('KRW-', ''): ticker['trade_price'] 
                        for ticker in ticker_data
                    }
                    st.session_state.cached_currencies = held_currencies
                    
                    if st.session_state.get('debug_mode', False):
                        st.success(f"✅ 현재가 조회 성공: {len(ticker_data)}개 코인")
                        
                except Exception as e:
                    # 전체 배치 조회 실패 시 개별 조회 시도
                    st.warning(f"⚠️ 배치 현재가 조회 실패: {str(e)}")
                    
                    if st.session_state.get('debug_mode', False):
                        st.info("🔄 개별 현재가 조회 시도 중...")
                    
                    successful_currencies = []
                    for currency in held_currencies:
                        try:
                            single_ticker = get_ticker([f'KRW-{currency}'])
                            if single_ticker:
                                st.session_state.current_prices[currency] = single_ticker[0]['trade_price']
                                successful_currencies.append(currency)
                        except Exception as single_error:
                            if st.session_state.get('debug_mode', False):
                                st.warning(f"❌ {currency} 현재가 조회 실패: {str(single_error)}")
                    
                    st.session_state.cached_currencies = successful_currencies
                    
                    if successful_currencies:
                        st.info(f"ℹ️ {len(successful_currencies)}/{len(held_currencies)}개 코인 현재가 조회 성공. 나머지는 평균매수가로 계산합니다.")
                    else:
                        st.warning("⚠️ 모든 현재가 조회 실패. 평균매수가로 계산합니다.")
            else:
                st.session_state.cached_currencies = []
        
        # 자산 데이터 처리
        accounts_data = []
        total_krw = 0
        
        for account in st.session_state.accounts:
            currency = account['currency']
            balance = float(account['balance'])
            locked = float(account['locked'])
            avg_buy_price = float(account.get('avg_buy_price', 0))
            
            if balance > 0 or locked > 0:
                total_balance = balance + locked
                
                # KRW 환산 가격 계산
                if currency == 'KRW':
                    krw_value = total_balance
                    current_price = 1
                else:
                    current_price = st.session_state.current_prices.get(currency, 0)
                    if current_price > 0:
                        krw_value = total_balance * current_price
                    elif avg_buy_price > 0:
                        # 현재가를 가져올 수 없으면 평균매수가 사용
                        krw_value = total_balance * avg_buy_price
                        current_price = avg_buy_price
                    else:
                        krw_value = 0
                        current_price = 0
                
                total_krw += krw_value
                
                accounts_data.append({
                    '코인': currency,
                    '보유수량': total_balance,
                    '사용가능': balance,
                    '주문중': locked,
                    '평균매수가': avg_buy_price,
                    '현재가': current_price,
                    'KRW 환산': krw_value
                })
        
        if accounts_data:
            df = pd.DataFrame(accounts_data)
            
            # 총 자산 표시 (토글 적용)
            col1, col2, col3 = st.columns(3)
            with col1:
                if hide_amounts:
                    st.metric("💰 총 자산", "🔒 숨김")
                else:
                    st.metric("💰 총 자산", format_currency(total_krw))
            with col2:
                krw_balance = next((item['KRW 환산'] for item in accounts_data if item['코인'] == 'KRW'), 0)
                if hide_amounts:
                    st.metric("💵 KRW 잔고", "🔒 숨김")
                else:
                    st.metric("💵 KRW 잔고", format_currency(krw_balance))
            with col3:
                coin_value = total_krw - krw_balance
                if hide_amounts:
                    st.metric("🪙 코인 자산", "🔒 숨김")
                else:
                    st.metric("🪙 코인 자산", format_currency(coin_value))
            
            # 자산 테이블
            st.subheader("📊 보유 자산 상세")
            
            # 포맷팅된 데이터프레임 생성
            display_df = df.copy()
            display_df['보유수량'] = display_df.apply(lambda x: f"{x['보유수량']:.8f}", axis=1)
            display_df['사용가능'] = display_df.apply(lambda x: f"{x['사용가능']:.8f}", axis=1)
            display_df['주문중'] = display_df.apply(lambda x: f"{x['주문중']:.8f}", axis=1)
            
            # 금액 관련 컬럼 토글 처리
            if hide_amounts:
                display_df['평균매수가'] = "🔒 숨김"
                display_df['현재가'] = "🔒 숨김"
                display_df['KRW 환산'] = "🔒 숨김"
            else:
                display_df['평균매수가'] = display_df.apply(lambda x: format_currency(x['평균매수가']) if x['평균매수가'] > 0 else "-", axis=1)
                display_df['현재가'] = display_df.apply(lambda x: format_currency(x['현재가']) if x['현재가'] > 0 else "-", axis=1)
                display_df['KRW 환산'] = display_df.apply(lambda x: format_currency(x['KRW 환산']), axis=1)
            
            st.dataframe(display_df, use_container_width=True)
            
            # 자산 분포 차트 (토글 적용)
            if len(df) > 1 and not hide_amounts:
                st.subheader("📈 자산 분포")
                fig = px.pie(
                    df[df['KRW 환산'] > 1000], 
                    values='KRW 환산', 
                    names='코인',
                    title="자산 분포 (1,000원 이상)"
                )
                st.plotly_chart(fig, use_container_width=True)
            elif hide_amounts:
                st.subheader("📈 자산 분포")
                st.info("🔒 금액이 숨겨져 있어 차트를 표시할 수 없습니다.")
        else:
            st.info("보유 중인 자산이 없습니다.")


def show_trading_tab():
    """주문하기 탭"""
    st.header("📊 주문하기")
    
    # 마켓 정보 로드
    if st.session_state.markets is None:
        try:
            markets = get_market_all()
            st.session_state.markets = [m for m in markets if m['market'].startswith('KRW-')]
        except Exception as e:
            st.error(f"마켓 정보 로드 실패: {str(e)}")
            return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🟢 매수 주문")
        
        # 마켓 선택
        market_options = {f"{m['korean_name']} ({m['market']})": m['market'] for m in st.session_state.markets}
        selected_market_buy = st.selectbox("매수할 코인 선택", list(market_options.keys()), key="buy_market")
        market_id_buy = market_options[selected_market_buy]
        
        # 현재가 조회
        if st.button("💱 현재가 조회", key="buy_price_check"):
            try:
                ticker_data = get_ticker([market_id_buy])
                if ticker_data:
                    current_price = ticker_data[0]['trade_price']
                    if st.session_state.get('hide_amounts', False):
                        st.success(f"현재가: 🔒 숨김")
                    else:
                        st.success(f"현재가: {format_currency(current_price)}")
                    st.session_state.buy_current_price = current_price
            except Exception as e:
                st.error(f"현재가 조회 실패: {str(e)}")
        
        # 주문 타입
        order_type_buy = st.radio("주문 타입", ["지정가", "시장가"], key="buy_order_type")
        
        if order_type_buy == "지정가":
            buy_price = st.number_input("매수 가격 (KRW)", min_value=1.0, step=1.0, key="buy_price")
            buy_volume = st.number_input("매수 수량", min_value=0.00000001, step=0.00000001, format="%.8f", key="buy_volume")
            
            if buy_price > 0 and buy_volume > 0:
                total_cost = buy_price * buy_volume
                if st.session_state.get('hide_amounts', False):
                    st.info(f"총 주문 금액: 🔒 숨김")
                else:
                    st.info(f"총 주문 금액: {format_currency(total_cost)}")
        else:
            buy_amount = st.number_input("매수 금액 (KRW)", min_value=5000.0, step=1000.0, key="buy_amount")
        
        if st.button("🟢 매수 주문", key="place_buy_order"):
            try:
                if order_type_buy == "지정가":
                    if buy_price > 0 and buy_volume > 0:
                        result = st.session_state.api_client.place_order(
                            market=market_id_buy,
                            side='bid',
                            volume=str(buy_volume),
                            price=str(buy_price),
                            ord_type='limit'
                        )
                        st.success(f"✅ 매수 주문 완료! 주문 UUID: {result['uuid']}")
                    else:
                        st.error("가격과 수량을 모두 입력해주세요.")
                else:
                    if buy_amount >= 5000:
                        result = st.session_state.api_client.place_order(
                            market=market_id_buy,
                            side='bid',
                            price=str(buy_amount),
                            ord_type='price'
                        )
                        st.success(f"✅ 시장가 매수 주문 완료! 주문 UUID: {result['uuid']}")
                    else:
                        st.error("최소 주문 금액은 5,000원입니다.")
            except Exception as e:
                st.error(f"❌ 매수 주문 실패: {str(e)}")
    
    with col2:
        st.subheader("🔴 매도 주문")
        
        # 보유 코인 중에서 선택
        if st.session_state.accounts:
            held_coins = [acc['currency'] for acc in st.session_state.accounts 
                         if float(acc['balance']) > 0 and acc['currency'] != 'KRW']
            
            if held_coins:
                selected_coin_sell = st.selectbox("매도할 코인 선택", held_coins, key="sell_coin")
                market_id_sell = f"KRW-{selected_coin_sell}"
                
                # 보유 수량 표시
                coin_balance = next((float(acc['balance']) for acc in st.session_state.accounts 
                                   if acc['currency'] == selected_coin_sell), 0)
                st.info(f"보유 수량: {coin_balance:.8f} {selected_coin_sell}")
                
                # 현재가 조회
                if st.button("💱 현재가 조회", key="sell_price_check"):
                    try:
                        ticker_data = get_ticker([market_id_sell])
                        if ticker_data:
                            current_price = ticker_data[0]['trade_price']
                            if st.session_state.get('hide_amounts', False):
                                st.success(f"현재가: 🔒 숨김")
                                st.info(f"예상 매도 금액: 🔒 숨김")
                            else:
                                st.success(f"현재가: {format_currency(current_price)}")
                                estimated_value = coin_balance * current_price
                                st.info(f"예상 매도 금액: {format_currency(estimated_value)}")
                    except Exception as e:
                        st.error(f"현재가 조회 실패: {str(e)}")
                
                # 주문 타입
                order_type_sell = st.radio("주문 타입", ["지정가", "시장가"], key="sell_order_type")
                
                if order_type_sell == "지정가":
                    sell_price = st.number_input("매도 가격 (KRW)", min_value=1.0, step=1.0, key="sell_price")
                    sell_volume = st.number_input(
                        "매도 수량", 
                        min_value=0.00000001, 
                        max_value=coin_balance,
                        step=0.00000001, 
                        format="%.8f", 
                        key="sell_volume"
                    )
                    
                    # 전량 매도 버튼
                    if st.button("전량 매도", key="sell_all"):
                        st.session_state.sell_volume = coin_balance
                        st.rerun()
                    
                    if sell_price > 0 and sell_volume > 0:
                        total_amount = sell_price * sell_volume
                        if st.session_state.get('hide_amounts', False):
                            st.info(f"총 매도 금액: 🔒 숨김")
                        else:
                            st.info(f"총 매도 금액: {format_currency(total_amount)}")
                else:
                    sell_volume = st.number_input(
                        "매도 수량", 
                        min_value=0.00000001, 
                        max_value=coin_balance,
                        step=0.00000001, 
                        format="%.8f", 
                        key="sell_volume_market"
                    )
                
                if st.button("🔴 매도 주문", key="place_sell_order"):
                    try:
                        if order_type_sell == "지정가":
                            if sell_price > 0 and sell_volume > 0:
                                result = st.session_state.api_client.place_order(
                                    market=market_id_sell,
                                    side='ask',
                                    volume=str(sell_volume),
                                    price=str(sell_price),
                                    ord_type='limit'
                                )
                                st.success(f"✅ 매도 주문 완료! 주문 UUID: {result['uuid']}")
                            else:
                                st.error("가격과 수량을 모두 입력해주세요.")
                        else:
                            if sell_volume > 0:
                                result = st.session_state.api_client.place_order(
                                    market=market_id_sell,
                                    side='ask',
                                    volume=str(sell_volume),
                                    ord_type='market'
                                )
                                st.success(f"✅ 시장가 매도 주문 완료! 주문 UUID: {result['uuid']}")
                            else:
                                st.error("매도 수량을 입력해주세요.")
                    except Exception as e:
                        st.error(f"❌ 매도 주문 실패: {str(e)}")
            else:
                st.info("매도할 수 있는 코인이 없습니다.")


def show_orders_tab():
    """주문내역 탭"""
    st.header("📋 주문 내역")
    
    col1, col2 = st.columns(2)
    
    with col1:
        state_filter = st.selectbox(
            "주문 상태", 
            ["전체", "대기중", "완료", "취소됨"],
            key="order_state_filter"
        )
    
    with col2:
        if st.button("🔄 주문내역 새로고침"):
            pass  # 새로고침 트리거
    
    try:
        # 상태별 주문 조회
        state_map = {
            "전체": None,
            "대기중": "wait",
            "완료": "done", 
            "취소됨": "cancel"
        }
        
        if state_filter == "전체":
            orders = st.session_state.api_client.get_orders(states=['wait', 'done', 'cancel'])
        else:
            orders = st.session_state.api_client.get_orders(state=state_map[state_filter])
        
        if orders:
            orders_data = []
            for order in orders:
                orders_data.append({
                    '시간': datetime.fromisoformat(order['created_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S'),
                    '마켓': order['market'],
                    '타입': '매수' if order['side'] == 'bid' else '매도',
                    '주문타입': order['ord_type'],
                    '상태': {'wait': '대기중', 'done': '완료', 'cancel': '취소됨'}.get(order['state'], order['state']),
                    '가격': float(order.get('price', 0)),
                    '수량': float(order['volume']),
                    '체결량': float(order['executed_volume']),
                    '체결금액': float(order['paid_fee']) + float(order['executed_volume']) * float(order.get('price', 0)),
                    'UUID': order['uuid']
                })
            
            df_orders = pd.DataFrame(orders_data)
            
            # 포맷팅
            display_df_orders = df_orders.copy()
            display_df_orders['가격'] = display_df_orders['가격'].apply(lambda x: format_currency(x) if x > 0 else "-")
            display_df_orders['수량'] = display_df_orders['수량'].apply(lambda x: f"{x:.8f}")
            display_df_orders['체결량'] = display_df_orders['체결량'].apply(lambda x: f"{x:.8f}")
            display_df_orders['체결금액'] = display_df_orders['체결금액'].apply(lambda x: format_currency(x))
            
            st.dataframe(display_df_orders.drop(columns=['UUID']), use_container_width=True)
            
            # 주문 취소 기능
            st.subheader("🗑️ 주문 취소")
            wait_orders = [order for order in orders if order['state'] == 'wait']
            
            if wait_orders:
                cancel_options = {f"{order['market']} - {order['side']} - {order['created_at'][:19]}": order['uuid'] 
                                for order in wait_orders}
                
                selected_order = st.selectbox("취소할 주문 선택", list(cancel_options.keys()))
                
                if st.button("🗑️ 주문 취소"):
                    try:
                        order_uuid = cancel_options[selected_order]
                        result = st.session_state.api_client.cancel_order(order_uuid)
                        st.success(f"✅ 주문이 취소되었습니다. UUID: {result['uuid']}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 주문 취소 실패: {str(e)}")
            else:
                st.info("취소할 수 있는 대기중인 주문이 없습니다.")
                
        else:
            st.info("주문 내역이 없습니다.")
            
    except Exception as e:
        error_msg = str(e)
        if "권한이 없습니다" in error_msg:
            st.error(f"❌ {error_msg}")
            st.warning("🔧 **해결 방법**: Upbit에서 API 키 권한에 '주문조회' 권한을 활성화해주세요.")
        elif "인증에 실패" in error_msg:
            st.error(f"❌ {error_msg}")
            st.warning("🔧 API 키가 올바른지 확인해주세요.")
        else:
            st.error(f"❌ 주문내역 조회 실패: {error_msg}")


def show_market_tab():
    """마켓정보 탭"""
    st.header("📈 마켓 정보")
    
    try:
        if st.session_state.markets is None:
            markets = get_market_all()
            st.session_state.markets = [m for m in markets if m['market'].startswith('KRW-')]
        
        # 인기 코인 현재가 조회
        popular_markets = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-ADA', 'KRW-DOT']
        ticker_data = get_ticker(popular_markets)
        
        if ticker_data:
            st.subheader("🔥 인기 코인 현재가")
            
            ticker_df_data = []
            for ticker in ticker_data:
                change_rate = ticker['change_rate'] * 100
                ticker_df_data.append({
                    '마켓': ticker['market'],
                    '현재가': ticker['trade_price'],
                    '전일대비': change_rate,
                    '거래량(24H)': ticker['acc_trade_volume_24h'],
                    '거래대금(24H)': ticker['acc_trade_price_24h']
                })
            
            ticker_df = pd.DataFrame(ticker_df_data)
            
            # 포맷팅 (토글 적용)
            display_ticker_df = ticker_df.copy()
            if st.session_state.get('hide_amounts', False):
                display_ticker_df['현재가'] = "🔒 숨김"
                display_ticker_df['거래대금(24H)'] = "🔒 숨김"
            else:
                display_ticker_df['현재가'] = display_ticker_df['현재가'].apply(lambda x: format_currency(x))
                display_ticker_df['거래대금(24H)'] = display_ticker_df['거래대금(24H)'].apply(lambda x: format_currency(x))
            
            display_ticker_df['전일대비'] = display_ticker_df['전일대비'].apply(lambda x: f"{x:+.2f}%")
            display_ticker_df['거래량(24H)'] = display_ticker_df['거래량(24H)'].apply(lambda x: f"{x:,.2f}")
            
            st.dataframe(display_ticker_df, use_container_width=True)
        
        # 전체 마켓 리스트
        st.subheader("📋 전체 마켓 리스트")
        
        markets_df_data = []
        for market in st.session_state.markets[:20]:  # 상위 20개만 표시
            markets_df_data.append({
                '마켓': market['market'],
                '한글명': market['korean_name'],
                '영문명': market['english_name']
            })
        
        markets_df = pd.DataFrame(markets_df_data)
        st.dataframe(markets_df, use_container_width=True)
        
    except Exception as e:
        st.error(f"마켓 정보 조회 실패: {str(e)}")


if __name__ == "__main__":
    main()
