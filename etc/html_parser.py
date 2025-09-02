#!/usr/bin/env python3
"""BitMobick Explorer HTML 파싱 모듈"""

import requests
import re
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from datetime import datetime

class MobickHTMLParser:
    """BitMobick Explorer HTML 파싱 클래스"""
    
    def __init__(self):
        self.base_url = 'https://blockchain2.mobick.info'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def parse_address_page(self, address: str) -> Dict:
        """
        주소 페이지 HTML을 파싱해서 잔액과 트랜잭션 정보 추출
        
        Args:
            address: BitMobick 주소
            
        Returns:
            잔액 및 트랜잭션 정보
        """
        try:
            url = f'{self.base_url}/address/{address}'
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                raise Exception(f"페이지 로드 실패: HTTP {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 잔액 정보 추출
            balance_info = self._extract_balance_info(soup)
            
            # 트랜잭션 정보 추출
            transactions = self._extract_transactions(soup)
            
            return {
                'address': address,
                'balance': balance_info,
                'transactions': transactions,
                'success': True
            }
            
        except Exception as e:
            return {
                'address': address,
                'error': str(e),
                'success': False
            }
    
    def _extract_balance_info(self, soup: BeautifulSoup) -> Dict:
        """HTML에서 잔액 정보 추출"""
        balance_data = {
            'confirmed_balance': 0.0,
            'unconfirmed_balance': 0.0,
            'total_balance': 0.0,
            'total_received': 0.0,
            'total_sent': 0.0,
            'tx_count': 0
        }
        
        # 다양한 패턴으로 잔액 찾기
        text = soup.get_text()
        
        # 잔액 패턴들
        balance_patterns = [
            r'Balance[:\s]*([0-9,.]+ MO)',
            r'balance[:\s]*([0-9,.]+)\s*MO',
            r'([0-9,.]+)\s*MO[^0-9]*balance',
            r'>([0-9,.]+)\s*MO<',
            r'MO[^0-9]*([0-9,.]+)',
        ]
        
        for pattern in balance_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    # 숫자 추출 및 변환
                    balance_str = matches[0].replace(',', '').replace(' MO', '')
                    balance = float(balance_str)
                    balance_data['confirmed_balance'] = balance
                    balance_data['total_balance'] = balance
                    break
                except ValueError:
                    continue
        
        # 트랜잭션 수 패턴들
        tx_patterns = [
            r'(\d+)\s*transaction[s]?',
            r'transaction[s]?[:\s]*(\d+)',
            r'tx[s]?[:\s]*(\d+)',
            r'(\d+)\s*tx[s]?',
        ]
        
        for pattern in tx_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    balance_data['tx_count'] = int(matches[0])
                    break
                except ValueError:
                    continue
        
        return balance_data
    
    def _extract_transactions(self, soup: BeautifulSoup) -> List[Dict]:
        """HTML에서 트랜잭션 목록 추출"""
        transactions = []
        
        # 트랜잭션 테이블이나 리스트 찾기
        # 일반적인 패턴들:
        # - table with transaction data
        # - div with transaction class
        # - list items with transaction info
        
        # 테이블에서 트랜잭션 찾기
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # 헤더 제외
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:
                    # 트랜잭션 해시, 금액, 시간 등 추출 시도
                    tx_data = self._parse_transaction_row(cells)
                    if tx_data:
                        transactions.append(tx_data)
        
        # div 컨테이너에서 트랜잭션 찾기
        tx_divs = soup.find_all('div', class_=re.compile(r'(transaction|tx)', re.I))
        for div in tx_divs[:10]:  # 최대 10개
            tx_data = self._parse_transaction_div(div)
            if tx_data:
                transactions.append(tx_data)
        
        return transactions[:10]  # 최대 10개 트랜잭션
    
    def _parse_transaction_row(self, cells) -> Optional[Dict]:
        """테이블 행에서 트랜잭션 정보 추출"""
        try:
            cell_texts = [cell.get_text().strip() for cell in cells]
            
            # 해시 패턴 찾기 (64자리 16진수)
            tx_hash = None
            for text in cell_texts:
                if re.match(r'^[a-fA-F0-9]{64}$', text):
                    tx_hash = text
                    break
            
            if not tx_hash:
                return None
            
            # 금액 패턴 찾기
            amount = 0.0
            for text in cell_texts:
                amount_match = re.search(r'([0-9,.]+)\s*MO', text)
                if amount_match:
                    amount = float(amount_match.group(1).replace(',', ''))
                    break
            
            # 시간 패턴 찾기
            time_str = None
            for text in cell_texts:
                if re.search(r'\d{4}-\d{2}-\d{2}|\d+\s*(hour|minute|second|day)s?\s*ago', text, re.I):
                    time_str = text
                    break
            
            return {
                'hash': tx_hash,
                'amount': amount,
                'time': time_str or 'Unknown',
                'type': 'received' if amount > 0 else 'sent',
                'confirmations': 1,  # 기본값
                'confirmed': True
            }
            
        except Exception:
            return None
    
    def _parse_transaction_div(self, div) -> Optional[Dict]:
        """div에서 트랜잭션 정보 추출"""
        try:
            text = div.get_text()
            
            # 해시 찾기
            hash_match = re.search(r'([a-fA-F0-9]{64})', text)
            if not hash_match:
                return None
            
            tx_hash = hash_match.group(1)
            
            # 금액 찾기
            amount_match = re.search(r'([0-9,.]+)\s*MO', text)
            amount = float(amount_match.group(1).replace(',', '')) if amount_match else 0.0
            
            return {
                'hash': tx_hash,
                'amount': amount,
                'time': 'Recent',
                'type': 'received' if amount > 0 else 'sent',
                'confirmations': 1,
                'confirmed': True
            }
            
        except Exception:
            return None
    
    def get_latest_blocks(self) -> List[str]:
        """최신 블록에서 실제 주소들 추출"""
        try:
            response = self.session.get(f'{self.base_url}/blocks', timeout=10)
            if response.status_code == 200:
                # BitMobick 주소 패턴 (B로 시작하는 25-34자리)
                addresses = re.findall(r'B[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{24,33}', response.text)
                return list(set(addresses))[:5]
        except Exception:
            pass
        return []

def test_html_parser():
    """HTML 파서 테스트"""
    parser = MobickHTMLParser()
    
    print("🔍 BitMobick HTML 파서 테스트")
    print("=" * 50)
    
    # 실제 주소들 가져오기
    print("📋 실제 주소들 검색 중...")
    real_addresses = parser.get_latest_blocks()
    
    if real_addresses:
        print(f"✅ {len(real_addresses)}개 실제 주소 발견")
        for addr in real_addresses:
            print(f"   - {addr}")
        
        # 첫 번째 주소로 테스트
        test_address = real_addresses[0]
        print(f"\n🧪 주소 테스트: {test_address}")
        
        result = parser.parse_address_page(test_address)
        if result['success']:
            print("✅ 파싱 성공!")
            print(f"   잔액: {result['balance']}")
            print(f"   트랜잭션 수: {len(result['transactions'])}")
            for tx in result['transactions'][:3]:
                print(f"   - {tx['hash'][:16]}... {tx['amount']} MO")
        else:
            print(f"❌ 파싱 실패: {result['error']}")
    else:
        print("❌ 실제 주소를 찾을 수 없음")

if __name__ == "__main__":
    test_html_parser()
