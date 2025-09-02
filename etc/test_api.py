#!/usr/bin/env python3
"""BitMobick API 테스트 스크립트"""

from bitcoin_wallet import CryptoWallet
import requests

def test_mobick_api():
    """BitMobick API 테스트"""
    # BitMobick 지갑 생성
    print("=" * 50)
    print("🪙 BitMobick API 테스트")
    print("=" * 50)
    
    wallet = CryptoWallet(coin_type='bitmobick', testnet=False)
    wallet_info = wallet.generate_wallet()
    address = wallet.address
    
    print(f'✅ 생성된 BitMobick 주소: {address}')
    
    # API 테스트
    api_url = 'https://blockchain2.mobick.info/api'
    print(f'🌐 API URL: {api_url}')
    
    # 다양한 API 패턴 테스트
    print("\n🔍 다양한 API 패턴 테스트...")
    
    # 실제 주소로 테스트 (블록체인에 존재하는 주소)
    test_addresses = [
        address,  # 새로 생성한 주소
        'B1tMobickGenesisAddressExample123456',  # 가상의 주소
    ]
    
    # 다양한 API 패턴들 시도
    api_patterns = [
        # Insight API 패턴 (많은 비트코인 탐색기에서 사용)
        'https://blockchain2.mobick.info/insight-api/addr/{address}',
        'https://blockchain2.mobick.info/insight-api/address/{address}',
        
        # Blockbook API 패턴
        'https://blockchain2.mobick.info/api/v2/address/{address}',
        'https://blockchain2.mobick.info/api/address/{address}',
        
        # 기본 패턴들
        f'{api_url}/addr/{{address}}',
        f'{api_url}/address/{{address}}',
        f'{api_url}/addresses/{{address}}',
        f'{api_url}/balance/{{address}}',
        f'{api_url}/{{address}}/balance',
        
        # 상대 경로 시도
        'https://blockchain2.mobick.info/addr/{address}',
        'https://blockchain2.mobick.info/address/{address}',
        
        # 다른 일반적인 패턴
        f'{api_url}/v1/addr/{{address}}',
        f'{api_url}/api/v1/addr/{{address}}',
        
        # 추가 패턴들
        'https://blockchain2.mobick.info/api/addr/{address}',
        'https://blockchain2.mobick.info/ext/getaddress/{address}',
        'https://blockchain2.mobick.info/ext/getbalance/{address}',
    ]
    
    for i, test_address in enumerate(test_addresses):
        print(f"\n--- 주소 {i+1}: {test_address[:20]}... 테스트 ---")
        
        for pattern in api_patterns:
            try:
                url = pattern.format(address=test_address)
                response = requests.get(url, timeout=3)
                
                if response.status_code in [200, 404, 400]:
                    print(f'✅ {response.status_code}: {url}')
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            print(f'   📋 JSON 응답! 타입: {type(data)}, 키/길이: {len(data) if isinstance(data, (list, dict)) else "N/A"}')
                            print(f'   📋 JSON 데이터: {str(data)[:200]}...')
                        except:
                            # HTML 응답에서 API 엔드포인트 찾기
                            html_content = response.text
                            print(f'   📋 HTML 응답 ({len(html_content)} 문자)')
                            
                            # API 엔드포인트를 찾기 위한 패턴들
                            import re
                            api_patterns = [
                                r'/api/[^"\']*',
                                r'/insight-api/[^"\']*',
                                r'api\.[^"\']*',
                                r'blockchain[^"\']*\.json',
                                r'/address/[^"\']+\.json',
                                r'/addr/[^"\']+\.json'
                            ]
                            
                            found_apis = set()
                            for pattern in api_patterns:
                                matches = re.findall(pattern, html_content)
                                found_apis.update(matches)
                            
                            if found_apis:
                                print(f'   🔍 발견된 API 패턴들: {list(found_apis)[:3]}...')
                            
                            # 잔액이나 트랜잭션 관련 데이터 찾기
                            balance_patterns = [
                                r'balance["\']?\s*:\s*["\']?([0-9.]+)',
                                r'amount["\']?\s*:\s*["\']?([0-9.]+)',
                                r'value["\']?\s*:\s*["\']?([0-9.]+)'
                            ]
                            
                            for pattern in balance_patterns:
                                matches = re.findall(pattern, html_content, re.IGNORECASE)
                                if matches:
                                    print(f'   💰 잠재적 잔액 데이터: {matches[:3]}...')
                                    break
                    break  # 성공하면 다음 주소로
            except requests.exceptions.Timeout:
                continue  # 타임아웃은 스킵
            except Exception as e:
                if "Connection" not in str(e):
                    print(f'❌ {pattern}: {str(e)[:50]}...')
        
        if i == 0:  # 첫 번째 주소만 전체 패턴 테스트
            break
    
    # 기본 엔드포인트들 테스트
    print("\n🔍 기본 엔드포인트 테스트...")
    
    base_endpoints = [
        'https://blockchain2.mobick.info/api/status',
        'https://blockchain2.mobick.info/status',
        'https://blockchain2.mobick.info/api/blocks',
        'https://blockchain2.mobick.info/blocks',
        'https://blockchain2.mobick.info/api/tx',
        'https://blockchain2.mobick.info/tx',
    ]
    
    for endpoint in base_endpoints:
        try:
            response = requests.get(endpoint, timeout=3)
            print(f'📡 {response.status_code}: {endpoint}')
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f'   📋 JSON 데이터 확인됨')
                except:
                    print(f'   📋 HTML/텍스트 응답')
        except Exception as e:
            if "timeout" not in str(e).lower():
                print(f'❌ {endpoint}: {str(e)[:50]}...')

if __name__ == "__main__":
    test_mobick_api()
