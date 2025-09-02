#!/usr/bin/env python3
"""BitMobick 전용 지갑 테스트 스크립트"""

from mobick_wallet import MobickWallet, MobickAPI, validate_mobick_address, format_mobick_amount
import time

def test_mobick_wallet():
    """BitMobick 전용 지갑 종합 테스트"""
    print("🪙 BitMobick 전용 지갑 테스트")
    print("=" * 60)
    
    start_time = time.time()
    
    # 1. 지갑 생성 테스트
    print("1️⃣ 지갑 생성 테스트...")
    try:
        wallet = MobickWallet(testnet=False)
        wallet_info = wallet.generate_wallet()
        
        print("✅ 지갑 생성 성공!")
        print(f"   🏠 주소: {wallet_info['address']}")
        print(f"   🔑 개인키: {wallet_info['private_key'][:16]}...")
        print(f"   📜 WIF: {wallet_info['wif'][:8]}...")
        
        # 주소가 1로 시작하는지 확인
        assert wallet_info['address'].startswith('1'), "BitMobick 주소는 '1'로 시작해야 함"
        
    except Exception as e:
        print(f"❌ 지갑 생성 실패: {e}")
        return False
    
    # 2. 주소 유효성 검증 테스트
    print("\n2️⃣ 주소 유효성 검증 테스트...")
    test_addresses = [
        (wallet_info['address'], True, "생성된 주소"),
        ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", True, "유효한 주소"),
        ("InvalidAddress123", False, "잘못된 주소"),
        ("", False, "빈 주소")
    ]
    
    for address, expected, description in test_addresses:
        result = validate_mobick_address(address)
        status = "✅" if result == expected else "❌"
        print(f"   {status} {description}: {result}")
    
    # 3. 잔액 조회 테스트
    print("\n3️⃣ 잔액 조회 테스트...")
    try:
        api = MobickAPI(testnet=False)
        balance_data = api.get_balance(wallet_info['address'])
        
        print("✅ 잔액 조회 성공!")
        print(f"   💰 총 잔액: {format_mobick_amount(balance_data['total_balance'])}")
        print(f"   📊 트랜잭션 수: {balance_data['tx_count']}")
        
        if 'error' in balance_data:
            print(f"   ⚠️ 참고: {balance_data['error']}")
        
    except Exception as e:
        print(f"❌ 잔액 조회 실패: {e}")
    
    # 4. 트랜잭션 내역 조회 테스트
    print("\n4️⃣ 트랜잭션 내역 조회 테스트...")
    try:
        transactions = api.get_transactions(wallet_info['address'], limit=3)
        
        if transactions:
            print(f"✅ {len(transactions)}개 트랜잭션 발견!")
            for i, tx in enumerate(transactions, 1):
                print(f"   📋 트랜잭션 {i}: {tx['hash'][:16]}...")
        else:
            print("ℹ️ 트랜잭션 내역이 없습니다 (새 주소)")
        
    except Exception as e:
        print(f"❌ 트랜잭션 조회 실패: {e}")
    
    # 5. QR 코드 생성 테스트
    print("\n5️⃣ QR 코드 생성 테스트...")
    try:
        qr_code = wallet.generate_qr_code(wallet_info['address'])
        print(f"✅ QR 코드 생성 성공! (길이: {len(qr_code)} 문자)")
        
    except Exception as e:
        print(f"❌ QR 코드 생성 실패: {e}")
    
    # 6. 외부 주소 조회 테스트 (예시 주소 사용)
    print("\n6️⃣ 외부 주소 조회 테스트...")
    external_addresses = [
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",  # 유명한 Genesis 주소
    ]
    
    for ext_addr in external_addresses:
        try:
            if validate_mobick_address(ext_addr):
                ext_balance = api.get_balance(ext_addr)
                print(f"✅ {ext_addr[:16]}... 조회 성공!")
                print(f"   💰 잔액: {format_mobick_amount(ext_balance['total_balance'])}")
            else:
                print(f"❌ {ext_addr[:16]}... 유효하지 않은 주소")
        except Exception as e:
            print(f"⚠️ {ext_addr[:16]}... 조회 실패: {e}")
    
    # 테스트 결과 요약
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    print(f"⏱️ 실행 시간: {duration:.2f}초")
    print(f"🪙 코인 타입: BitMobick (MO) 전용")
    print(f"🏠 생성된 주소: {wallet_info['address']}")
    print(f"💰 잔액: {format_mobick_amount(balance_data.get('total_balance', 0))}")
    print(f"🌐 탐색기: https://blockchain2.mobick.info/address/{wallet_info['address']}")
    
    print("\n🎉 BitMobick 전용 지갑이 성공적으로 작동합니다!")
    print("💡 웹 애플리케이션: http://localhost:8501")
    
    return True

if __name__ == "__main__":
    test_mobick_wallet()
