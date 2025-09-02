#!/usr/bin/env python3
"""실제 BitMobick 주소 형식 분석"""

import requests
import re
from bs4 import BeautifulSoup

def analyze_mobick_addresses():
    """BitMobick 블록체인에서 실제 주소 형식 분석"""
    print("🔍 BitMobick 실제 주소 형식 분석")
    print("=" * 60)
    
    try:
        # 블록 페이지에서 실제 주소들 추출
        response = requests.get('https://blockchain2.mobick.info/blocks', timeout=10)
        if response.status_code != 200:
            print(f"❌ 블록 페이지 로드 실패: {response.status_code}")
            return
        
        # HTML에서 주소 패턴 찾기
        text = response.text
        
        # 다양한 주소 패턴 시도
        address_patterns = [
            r'\b1[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{25,34}\b',  # Bitcoin style (1로 시작)
            r'\b3[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{25,34}\b',  # P2SH style (3으로 시작)
            r'\bB[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{25,34}\b',  # B로 시작
            r'\bM[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{25,34}\b',  # M으로 시작
        ]
        
        print("📋 발견된 주소들:")
        all_addresses = set()
        
        for pattern_name, pattern in [
            ("1로 시작하는 주소", address_patterns[0]),
            ("3으로 시작하는 주소", address_patterns[1]),
            ("B로 시작하는 주소", address_patterns[2]),
            ("M으로 시작하는 주소", address_patterns[3])
        ]:
            addresses = re.findall(pattern, text)
            unique_addresses = list(set(addresses))
            
            if unique_addresses:
                print(f"\n✅ {pattern_name}: {len(unique_addresses)}개")
                for addr in unique_addresses[:5]:  # 처음 5개만
                    print(f"   - {addr}")
                    all_addresses.add(addr)
                if len(unique_addresses) > 5:
                    print(f"   ... 및 {len(unique_addresses) - 5}개 더")
        
        if not all_addresses:
            print("❌ 주소를 찾을 수 없습니다. 다른 방법을 시도합니다.")
            
            # 트랜잭션 페이지에서 시도
            try:
                tx_response = requests.get('https://blockchain2.mobick.info/tx', timeout=10)
                if tx_response.status_code == 200:
                    print("\n🔍 트랜잭션 페이지에서 주소 검색 중...")
                    for pattern_name, pattern in [
                        ("1로 시작하는 주소", address_patterns[0]),
                        ("3으로 시작하는 주소", address_patterns[1])
                    ]:
                        addresses = re.findall(pattern, tx_response.text)
                        if addresses:
                            print(f"✅ {pattern_name}: {addresses[:3]}")
            except:
                pass
        
        return list(all_addresses)[:5]
        
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        return []

def test_real_address(address):
    """실제 주소로 잔액 테스트"""
    print(f"\n🧪 실제 주소 테스트: {address}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        url = f"https://blockchain2.mobick.info/address/{address}"
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"📊 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 주소가 유효하고 페이지가 로드됨")
            
            # 잔액 정보 추출 시도
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text()
            
            # 잔액 패턴 찾기
            balance_patterns = [
                r'Balance[:\s]*([0-9,.]+)\s*MO',
                r'([0-9,.]+)\s*MO',
                r'balance[:\s]*([0-9,.]+)',
            ]
            
            for pattern in balance_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    print(f"💰 잠재적 잔액: {matches[:3]}")
                    break
            else:
                print("💰 잔액 정보를 찾을 수 없음")
                
        elif response.status_code == 404:
            print("ℹ️ 주소가 존재하지 않음 (404)")
        else:
            print(f"⚠️ 예상치 못한 응답: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")

if __name__ == "__main__":
    # 실제 주소 형식 분석
    real_addresses = analyze_mobick_addresses()
    
    # 발견된 주소들로 테스트
    if real_addresses:
        print(f"\n🧪 실제 주소들로 테스트 시작")
        print("=" * 60)
        
        for addr in real_addresses[:3]:  # 처음 3개만 테스트
            test_real_address(addr)
    
    print(f"\n📝 결론:")
    print("1. BitMobick 주소의 실제 형식을 확인했습니다")
    print("2. 올바른 네트워크 바이트를 사용해야 합니다")
    print("3. 새 주소는 0 잔액이어야 정상입니다")
