#!/usr/bin/env python3
"""
Multi-Crypto Wallet 기능 데모 스크립트
"""

from bitcoin_wallet import (
    CryptoWallet, CryptoAPI, NETWORK_CONFIGS,
    validate_crypto_address, validate_bitcoin_address, 
    format_crypto_amount, format_bitcoin_amount
)

def demo_wallet_creation():
    """멀티 코인 지갑 생성 데모"""
    print("=" * 60)
    print("🔑 멀티 코인 지갑 생성 데모")
    print("=" * 60)
    
    wallets = {}
    
    for coin_type in NETWORK_CONFIGS.keys():
        config = NETWORK_CONFIGS[coin_type]
        print(f"\n🪙 {config['name']} ({config['symbol']}) 지갑 생성 중...")
        
        wallet = CryptoWallet(coin_type=coin_type, testnet=True)
        wallet_info = wallet.generate_wallet()
        wallets[coin_type] = wallet
        
        print(f"✅ {config['name']} 지갑이 생성되었습니다!")
        print(f"📍 주소: {wallet_info['address']}")
        print(f"🔑 개인키: {wallet_info['private_key'][:32]}...")
        print(f"💾 WIF: {wallet_info['wif']}")
    
    print()
    return wallets

def demo_address_validation():
    """주소 검증 데모"""
    print("=" * 60)
    print("🔍 멀티 코인 주소 검증 데모")
    print("=" * 60)
    
    test_addresses = [
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",  # 비트코인 주소 (Satoshi's address)
        "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",  # 비트코인 P2SH 주소
        "invalid_address",                      # 무효한 주소
        "1234567890",                          # 무효한 주소
    ]
    
    for coin_type in NETWORK_CONFIGS.keys():
        config = NETWORK_CONFIGS[coin_type]
        print(f"\n🪙 {config['name']} 주소 검증:")
        
        for address in test_addresses:
            is_valid = validate_crypto_address(address, coin_type)
            status = "✅ 유효" if is_valid else "❌ 무효"
            print(f"  {status}: {address}")
    print()

def demo_qr_generation(wallets):
    """QR 코드 생성 데모"""
    print("=" * 60)
    print("📱 QR 코드 생성 데모")
    print("=" * 60)
    
    for coin_type, wallet in wallets.items():
        config = NETWORK_CONFIGS[coin_type]
        print(f"\n🪙 {config['name']} QR 코드:")
        
        try:
            # 주소 QR 코드
            qr_data = wallet.generate_qr_code(wallet.address)
            print(f"  ✅ 주소 QR 코드 생성 성공 ({len(qr_data)} 바이트)")
            
            # 결제 요청 QR 코드
            payment_uri = f"bitcoin:{wallet.address}?amount=0.001&label=Test%20Payment"
            payment_qr = wallet.generate_qr_code(payment_uri)
            print(f"  ✅ 결제 요청 QR 코드 생성 성공 ({len(payment_qr)} 바이트)")
            print(f"  📄 결제 URI: {payment_uri}")
            
        except Exception as e:
            print(f"  ❌ QR 코드 생성 실패: {e}")
    print()

def demo_api_features():
    """API 기능 데모"""
    print("=" * 60)
    print("🌐 멀티 코인 API 연결 데모")
    print("=" * 60)
    
    # 비트코인 테스트넷 API 사용 (BitMobick은 호환 API 사용)
    for coin_type in NETWORK_CONFIGS.keys():
        config = NETWORK_CONFIGS[coin_type]
        print(f"\n🪙 {config['name']} API 테스트:")
        
        api = CryptoAPI(coin_type=coin_type, testnet=True)
    
        # 유명한 테스트넷 주소 (faucet 주소)
        test_address = "2N2JD6wb56AfK4tfmM6PwdVmoYk2dCKf4Br"
        
        try:
            print(f"  🔍 주소 조회: {test_address}")
            balance_info = api.get_balance(test_address)
            
            coin_symbol = balance_info.get('coin_symbol', config['symbol'])
            decimals = config['decimals']
            
            print("  💰 잔액 정보:")
            print(f"    - 확인된 잔액: {format_crypto_amount(balance_info['confirmed_balance'], coin_symbol, decimals)}")
            print(f"    - 미확인 잔액: {format_crypto_amount(balance_info['unconfirmed_balance'], coin_symbol, decimals)}")
            print(f"    - 총 잔액: {format_crypto_amount(balance_info['total_balance'], coin_symbol, decimals)}")
            print(f"    - 거래 횟수: {balance_info['tx_count']}회")
            
            print("\n  📋 최근 거래 내역:")
            transactions = api.get_transactions(test_address, limit=3)
            
            if transactions:
                for i, tx in enumerate(transactions, 1):
                    tx_coin_symbol = tx.get('coin_symbol', coin_symbol)
                    print(f"    {i}. {tx['type'].title()}: {format_crypto_amount(abs(tx['amount']), tx_coin_symbol, decimals)}")
                    print(f"       해시: {tx['hash'][:32]}...")
                    print(f"       확인: {tx['confirmations']}회")
            else:
                print("    거래 내역이 없습니다.")
                
        except Exception as e:
            print(f"  ❌ API 조회 실패: {e}")
            if coin_type == 'bitcoin':
                print("  💡 인터넷 연결을 확인하거나 나중에 다시 시도해보세요.")
            else:
                print(f"  💡 {config['name']}은 데모 모드로 시뮬레이션된 데이터를 제공합니다.")
    print()

def demo_format_functions():
    """포맷팅 함수 데모"""
    print("=" * 60)
    print("📊 멀티 코인 금액 포맷팅 데모")
    print("=" * 60)
    
    test_amounts = [
        0,
        0.00000001,  # 1 satoshi
        0.001,       # 0.001 unit
        1.0,         # 1 unit
        21000000,    # 21 million units
        0.0000000001, # Very small amount
    ]
    
    for coin_type in NETWORK_CONFIGS.keys():
        config = NETWORK_CONFIGS[coin_type]
        print(f"\n🪙 {config['name']} ({config['symbol']}) 포맷팅:")
        
        for amount in test_amounts[:4]:  # 처음 4개만 표시
            formatted = format_crypto_amount(amount, config['symbol'], config['decimals'])
            print(f"  원본: {amount:>10} → 포맷: {formatted}")
    print()

def main():
    """메인 데모 함수"""
    print("🪙" * 70)
    print("  Multi-Crypto Wallet Library 기능 데모")
    print("  Bitcoin & BitMobick 지원")
    print("🪙" * 70)
    print()
    
    try:
        # 1. 지갑 생성
        wallets = demo_wallet_creation()
        
        # 2. 주소 검증
        demo_address_validation()
        
        # 3. QR 코드 생성
        demo_qr_generation(wallets)
        
        # 4. 금액 포맷팅
        demo_format_functions()
        
        # 5. API 기능 (인터넷 연결 필요)
        demo_api_features()
        
        print("=" * 60)
        print("✅ 모든 데모가 완료되었습니다!")
        print("🚀 멀티 코인 웹 애플리케이션을 실행하려면:")
        print("   python run.py")
        print("   또는")
        print("   streamlit run bitcoin_app.py")
        print("\n💡 지원 코인:")
        for coin_type in NETWORK_CONFIGS.keys():
            config = NETWORK_CONFIGS[coin_type]
            print(f"   - {config['name']} ({config['symbol']})")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n👋 데모가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 데모 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
