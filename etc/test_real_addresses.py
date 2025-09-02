#!/usr/bin/env python3
"""실제 BitMobick 주소로 API 테스트"""

import requests
import re
from bitcoin_wallet import CryptoWallet

def extract_addresses_from_blocks():
    """블록 페이지에서 실제 주소들 추출"""
    try:
        response = requests.get('https://blockchain2.mobick.info/blocks', timeout=10)
        if response.status_code == 200:
            # BitMobick 주소 패턴 찾기 (B로 시작하는 주소들)
            address_pattern = r'B[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{33}'
            addresses = re.findall(address_pattern, response.text)
            
            # 중복 제거하고 유효한 주소들만 반환
            unique_addresses = list(set(addresses))
            return unique_addresses[:5]  # 처음 5개만
    except Exception as e:
        print(f"블록 페이지에서 주소 추출 실패: {e}")
    
    return []

def test_with_real_addresses():
    """실제 주소들로 API 테스트"""
    print("=" * 60)
    print("🔍 실제 BitMobick 주소로 API 테스트")
    print("=" * 60)
    
    # 실제 주소들 추출
    print("🌐 블록체인에서 실제 주소들 추출 중...")
    real_addresses = extract_addresses_from_blocks()
    
    if real_addresses:
        print(f"✅ {len(real_addresses)}개의 실제 주소 발견:")
        for addr in real_addresses:
            print(f"   - {addr}")
    else:
        print("❌ 실제 주소를 찾을 수 없음. 테스트 주소 사용")
        # 테스트용 주소들 (실제 존재할 수도 있는 패턴)
        real_addresses = [
            'B1234567890123456789012345678901234567',  # 테스트 패턴
        ]
    
    # API 패턴들
    api_patterns = [
        'https://blockchain2.mobick.info/address/{address}',
        'https://blockchain2.mobick.info/addr/{address}',
        'https://blockchain2.mobick.info/api/address/{address}',
        'https://blockchain2.mobick.info/api/addr/{address}',
        'https://blockchain2.mobick.info/insight-api/addr/{address}',
        'https://blockchain2.mobick.info/ext/getaddress/{address}',
        'https://blockchain2.mobick.info/ext/getbalance/{address}',
    ]
    
    # 각 실제 주소로 테스트
    for i, address in enumerate(real_addresses):
        print(f"\n--- 실제 주소 {i+1}: {address} ---")
        
        for pattern in api_patterns:
            try:
                url = pattern.format(address=address)
                response = requests.get(url, timeout=5)
                
                print(f"📡 {response.status_code}: {url}")
                
                if response.status_code == 200:
                    # JSON 응답 확인
                    try:
                        data = response.json()
                        print(f"   ✅ JSON 응답!")
                        print(f"   📋 데이터: {data}")
                        return  # JSON API 찾음!
                    except:
                        # HTML에서 데이터 추출 시도
                        html = response.text
                        
                        # 더 정교한 패턴으로 잔액 찾기
                        balance_patterns = [
                            r'Balance[^:]*:\s*([0-9,.]+ MO)',
                            r'balance[^:]*:\s*([0-9,.]+)',
                            r'amount[^:]*:\s*([0-9,.]+)',
                            r'>([0-9,.]+ MO)<',
                            r'MO[^0-9]*([0-9,.]+)',
                            r'([0-9,.]+)\s*MO'
                        ]
                        
                        for pattern in balance_patterns:
                            matches = re.findall(pattern, html, re.IGNORECASE)
                            if matches:
                                print(f"   💰 잔액 발견: {matches}")
                                break
                        
                        # 트랜잭션 수 찾기
                        tx_patterns = [
                            r'transaction[s]?[^:]*:\s*([0-9,]+)',
                            r'tx[s]?[^:]*:\s*([0-9,]+)',
                            r'>([0-9,]+)\s*transaction[s]?<'
                        ]
                        
                        for pattern in tx_patterns:
                            matches = re.findall(pattern, html, re.IGNORECASE)
                            if matches:
                                print(f"   📊 트랜잭션 수: {matches}")
                                break
                
                elif response.status_code == 404:
                    print(f"   ℹ️ 주소 데이터 없음")
                
            except requests.exceptions.Timeout:
                print(f"   ⏰ 타임아웃: {pattern}")
            except Exception as e:
                print(f"   ❌ 에러: {str(e)[:50]}...")
        
        if i >= 2:  # 처음 3개 주소만 테스트
            break

if __name__ == "__main__":
    test_with_real_addresses()
