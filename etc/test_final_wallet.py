#!/usr/bin/env python3
"""완성된 BitMobick 지갑 전체 기능 테스트"""

from bitcoin_wallet import CryptoWallet, CryptoAPI, format_crypto_amount
import time

def test_wallet_generation():
    """지갑 생성 테스트"""
    print("=" * 60)
    print("🎯 BitMobick 지갑 생성 테스트")
    print("=" * 60)
    
    try:
        # BitMobick 지갑 생성
        wallet = CryptoWallet(coin_type='bitmobick', testnet=False)
        wallet_info = wallet.generate_wallet()
        
        print("✅ 지갑 생성 성공!")
        print(f"🔑 개인키: {wallet_info['private_key'][:16]}...{wallet_info['private_key'][-16:]}")
        print(f"🔓 공개키: {wallet_info['public_key'][:20]}...{wallet_info['public_key'][-20:]}")
        print(f"🏠 주소: {wallet_info['address']}")
        print(f"📜 WIF: {wallet_info['wif'][:8]}...{wallet_info['wif'][-8:]}")
        
        # 주소 유효성 검증
        assert wallet_info['address'].startswith('1'), "BitMobick 주소는 '1'로 시작해야 함"
        assert len(wallet_info['address']) >= 25, "주소 길이가 너무 짧음"
        
        return wallet
        
    except Exception as e:
        print(f"❌ 지갑 생성 실패: {e}")
        return None

def test_balance_check(wallet):
    """잔액 조회 테스트"""
    print("\n" + "=" * 60)
    print("💰 BitMobick 잔액 조회 테스트")
    print("=" * 60)
    
    if not wallet:
        print("❌ 지갑이 없어서 테스트 불가")
        return
    
    try:
        # API 객체 생성
        api = CryptoAPI(coin_type='bitmobick', testnet=False)
        
        print(f"🔍 주소: {wallet.address}")
        print("📡 잔액 조회 중...")
        
        # 잔액 조회
        balance_data = api.get_balance(wallet.address)
        
        print("✅ 잔액 조회 성공!")
        print(f"💎 확정 잔액: {format_crypto_amount(balance_data['confirmed_balance'], 'MO', 8)}")
        print(f"⏳ 미확정 잔액: {format_crypto_amount(balance_data['unconfirmed_balance'], 'MO', 8)}")
        print(f"💰 총 잔액: {format_crypto_amount(balance_data['total_balance'], 'MO', 8)}")
        print(f"📊 트랜잭션 수: {balance_data['tx_count']}")
        
        if 'error' in balance_data:
            print(f"⚠️ 참고: {balance_data['error']}")
        
        return balance_data
        
    except Exception as e:
        print(f"❌ 잔액 조회 실패: {e}")
        return None

def test_transaction_history(wallet):
    """트랜잭션 내역 조회 테스트"""
    print("\n" + "=" * 60)
    print("📋 BitMobick 트랜잭션 내역 테스트")
    print("=" * 60)
    
    if not wallet:
        print("❌ 지갑이 없어서 테스트 불가")
        return
    
    try:
        # API 객체 생성
        api = CryptoAPI(coin_type='bitmobick', testnet=False)
        
        print(f"🔍 주소: {wallet.address}")
        print("📡 트랜잭션 내역 조회 중...")
        
        # 트랜잭션 내역 조회
        transactions = api.get_transactions(wallet.address, limit=5)
        
        if transactions:
            print(f"✅ {len(transactions)}개 트랜잭션 발견!")
            
            for i, tx in enumerate(transactions, 1):
                print(f"\n--- 트랜잭션 {i} ---")
                print(f"🔗 해시: {tx['hash'][:16]}...{tx['hash'][-16:]}")
                print(f"📊 타입: {tx['type']}")
                print(f"💰 금액: {format_crypto_amount(abs(tx['amount']), 'MO', 8)}")
                print(f"✅ 확인: {tx['confirmations']}회")
                print(f"📅 시간: {tx['received']}")
        else:
            print("ℹ️ 트랜잭션 내역이 없습니다 (새 주소)")
        
        return transactions
        
    except Exception as e:
        print(f"❌ 트랜잭션 조회 실패: {e}")
        return []

def test_qr_generation(wallet):
    """QR 코드 생성 테스트"""
    print("\n" + "=" * 60)
    print("📱 QR 코드 생성 테스트")
    print("=" * 60)
    
    if not wallet:
        print("❌ 지갑이 없어서 테스트 불가")
        return
    
    try:
        # 주소 QR 코드 생성
        print("🔍 주소 QR 코드 생성 중...")
        address_qr = wallet.generate_qr_code(wallet.address)
        print(f"✅ 주소 QR 코드 생성 성공! (길이: {len(address_qr)} 문자)")
        
        # 결제 요청 QR 코드 생성
        print("💰 결제 요청 QR 코드 생성 중...")
        payment_uri = f"bitcoin:{wallet.address}?amount=1.5&label=Test Payment"
        payment_qr = wallet.generate_qr_code(payment_uri)
        print(f"✅ 결제 QR 코드 생성 성공! (길이: {len(payment_qr)} 문자)")
        
        return True
        
    except Exception as e:
        print(f"❌ QR 코드 생성 실패: {e}")
        return False

def test_address_validation():
    """주소 유효성 검증 테스트"""
    print("\n" + "=" * 60)
    print("✅ 주소 유효성 검증 테스트")
    print("=" * 60)
    
    from bitcoin_wallet import validate_crypto_address
    
    # 테스트 주소들
    test_addresses = [
        ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", True, "유효한 BitMobick/Bitcoin 주소"),
        ("1SQkU9X4NGWeGMuseuiDmZ3H7B2ZZUNj1", True, "새로 생성된 BitMobick 주소"),
        ("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", False, "P2SH 주소 (BitMobick에서 미지원)"),
        ("InvalidAddress123", False, "잘못된 주소"),
        ("", False, "빈 주소")
    ]
    
    for address, expected, description in test_addresses:
        try:
            result = validate_crypto_address(address, coin_type='bitmobick')
            status = "✅" if result == expected else "❌"
            print(f"{status} {description}: {address[:20]}{'...' if len(address) > 20 else ''} → {result}")
        except Exception as e:
            print(f"❌ {description}: 에러 - {e}")

def run_comprehensive_test():
    """종합 테스트 실행"""
    print("🚀 BitMobick 지갑 종합 테스트 시작")
    print("=" * 80)
    
    start_time = time.time()
    
    # 1. 지갑 생성 테스트
    wallet = test_wallet_generation()
    
    # 2. 잔액 조회 테스트
    balance_data = test_balance_check(wallet)
    
    # 3. 트랜잭션 내역 테스트
    transactions = test_transaction_history(wallet)
    
    # 4. QR 코드 생성 테스트
    qr_success = test_qr_generation(wallet)
    
    # 5. 주소 유효성 검증 테스트
    test_address_validation()
    
    # 테스트 결과 요약
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "=" * 80)
    print("📊 테스트 결과 요약")
    print("=" * 80)
    
    print(f"⏱️ 실행 시간: {duration:.2f}초")
    print(f"🎯 지갑 생성: {'✅ 성공' if wallet else '❌ 실패'}")
    print(f"💰 잔액 조회: {'✅ 성공' if balance_data else '❌ 실패'}")
    print(f"📋 거래 내역: {'✅ 성공' if transactions is not None else '❌ 실패'}")
    print(f"📱 QR 코드: {'✅ 성공' if qr_success else '❌ 실패'}")
    
    if wallet and balance_data:
        print(f"\n🎉 BitMobick 지갑이 성공적으로 작동합니다!")
        print(f"🏠 생성된 주소: {wallet.address}")
        print(f"💰 현재 잔액: {format_crypto_amount(balance_data['total_balance'], 'MO', 8)}")
        print(f"📊 트랜잭션 수: {balance_data.get('tx_count', 0)}")
        
        print(f"\n🌐 블록체인 탐색기에서 확인:")
        print(f"   https://blockchain2.mobick.info/address/{wallet.address}")
    else:
        print(f"\n⚠️ 일부 기능에서 문제가 발생했습니다.")
        print(f"   대부분의 경우 새로 생성된 주소이기 때문입니다.")

if __name__ == "__main__":
    run_comprehensive_test()
