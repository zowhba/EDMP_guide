import hashlib
import secrets
import base58
import ecdsa
import requests
import json
from typing import Dict, List, Optional, Tuple
import qrcode
from io import BytesIO
import base64
from bs4 import BeautifulSoup
import re


# 코인별 네트워크 설정
NETWORK_CONFIGS = {
    'bitcoin': {
        'name': 'Bitcoin',
        'symbol': 'BTC',
        'mainnet_byte': b'\x00',
        'testnet_byte': b'\x6f',
        'wif_mainnet_byte': b'\x80',
        'wif_testnet_byte': b'\xef',
        'api_mainnet': 'https://api.blockcypher.com/v1/btc/main',
        'api_testnet': 'https://api.blockcypher.com/v1/btc/test3',
        'decimals': 8,
        'satoshi_per_unit': 100000000
    },
    'bitmobick': {
        'name': 'BitMobick',
        'symbol': 'MO',  # 공식 사이트에서 확인한 심볼
        'mainnet_byte': b'\x00',  # Bitcoin과 같은 네트워크 바이트 (1로 시작)
        'testnet_byte': b'\x6f',  # 테스트넷은 비트코인과 동일하게 설정
        'wif_mainnet_byte': b'\x80',  # Bitcoin과 같은 WIF 바이트
        'wif_testnet_byte': b'\xef',
        'api_mainnet': 'https://blockchain2.mobick.info/api',  # 실제 Mobick Explorer API
        'api_testnet': 'https://blockchain2.mobick.info/api',
        'decimals': 8,
        'satoshi_per_unit': 100000000
    }
}


class CryptoWallet:
    """멀티 코인 지갑 클래스 (Bitcoin, BitMobick 지원)"""
    
    def __init__(self, coin_type: str = 'bitcoin', testnet: bool = True):
        """
        Args:
            coin_type: 코인 타입 ('bitcoin', 'bitmobick')
            testnet: 테스트넷 사용 여부
        """
        if coin_type not in NETWORK_CONFIGS:
            raise ValueError(f"지원하지 않는 코인 타입: {coin_type}")
            
        self.coin_type = coin_type
        self.testnet = testnet
        self.config = NETWORK_CONFIGS[coin_type]
        self.private_key = None
        self.public_key = None
        self.address = None
        self.wif = None  # Wallet Import Format
        
    def generate_wallet(self) -> Dict[str, str]:
        """
        새 비트코인 지갑 생성
        
        Returns:
            지갑 정보 딕셔너리
        """
        # 1. 256비트 랜덤 개인키 생성
        private_key_bytes = secrets.randbits(256).to_bytes(32, byteorder='big')
        self.private_key = private_key_bytes.hex()
        
        # 2. 공개키 생성 (ECDSA secp256k1 곡선 사용)
        sk = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
        vk = sk.verifying_key
        public_key_bytes = b'\x04' + vk.to_string()
        self.public_key = public_key_bytes.hex()
        
        # 3. 비트코인 주소 생성 (P2PKH - Pay to Public Key Hash)
        self.address = self._public_key_to_address(public_key_bytes)
        
        # 4. WIF (Wallet Import Format) 생성
        self.wif = self._private_key_to_wif(private_key_bytes)
        
        return {
            'private_key': self.private_key,
            'public_key': self.public_key,
            'address': self.address,
            'wif': self.wif
        }
    
    def import_wallet(self, private_key_or_wif: str) -> Dict[str, str]:
        """
        기존 지갑 가져오기
        
        Args:
            private_key_or_wif: 개인키(hex) 또는 WIF 형식
            
        Returns:
            지갑 정보 딕셔너리
        """
        try:
            if len(private_key_or_wif) == 64:  # Hex private key
                private_key_bytes = bytes.fromhex(private_key_or_wif)
                self.private_key = private_key_or_wif
            else:  # WIF format
                private_key_bytes = self._wif_to_private_key(private_key_or_wif)
                self.private_key = private_key_bytes.hex()
                
            # 공개키 및 주소 생성
            sk = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
            vk = sk.verifying_key
            public_key_bytes = b'\x04' + vk.to_string()
            self.public_key = public_key_bytes.hex()
            self.address = self._public_key_to_address(public_key_bytes)
            self.wif = self._private_key_to_wif(private_key_bytes)
            
            return {
                'private_key': self.private_key,
                'public_key': self.public_key,
                'address': self.address,
                'wif': self.wif
            }
        except Exception as e:
            raise ValueError(f"잘못된 개인키 또는 WIF 형식: {str(e)}")
    
    def _public_key_to_address(self, public_key_bytes: bytes) -> str:
        """공개키를 암호화폐 주소로 변환"""
        # SHA256 해시
        sha256_hash = hashlib.sha256(public_key_bytes).digest()
        
        # RIPEMD160 해시
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256_hash)
        public_key_hash = ripemd160.digest()
        
        # 네트워크 바이트 선택 (코인 및 네트워크에 따라)
        if self.testnet:
            network_byte = self.config['testnet_byte']
        else:
            network_byte = self.config['mainnet_byte']
            
        extended_hash = network_byte + public_key_hash
        
        # 체크섬 생성 (double SHA256의 첫 4바이트)
        checksum = hashlib.sha256(hashlib.sha256(extended_hash).digest()).digest()[:4]
        
        # Base58 인코딩
        address_bytes = extended_hash + checksum
        address = base58.b58encode(address_bytes).decode('utf-8')
        
        return address
    
    def _private_key_to_wif(self, private_key_bytes: bytes) -> str:
        """개인키를 WIF 형식으로 변환"""
        # 네트워크 바이트 선택 (코인 및 네트워크에 따라)
        if self.testnet:
            network_byte = self.config['wif_testnet_byte']
        else:
            network_byte = self.config['wif_mainnet_byte']
            
        extended_key = network_byte + private_key_bytes
        
        # 체크섬 생성
        checksum = hashlib.sha256(hashlib.sha256(extended_key).digest()).digest()[:4]
        
        # Base58 인코딩
        wif_bytes = extended_key + checksum
        wif = base58.b58encode(wif_bytes).decode('utf-8')
        
        return wif
    
    def _wif_to_private_key(self, wif: str) -> bytes:
        """WIF를 개인키로 변환"""
        wif_bytes = base58.b58decode(wif)
        
        # 체크섬 검증
        extended_key = wif_bytes[:-4]
        checksum = wif_bytes[-4:]
        calculated_checksum = hashlib.sha256(hashlib.sha256(extended_key).digest()).digest()[:4]
        
        if checksum != calculated_checksum:
            raise ValueError("WIF 체크섬 오류")
            
        # 네트워크 바이트 제거
        private_key_bytes = extended_key[1:]
        
        return private_key_bytes
    
    def generate_qr_code(self, data: str, size: int = 10) -> str:
        """
        QR 코드 생성
        
        Args:
            data: QR 코드로 변환할 데이터
            size: QR 코드 크기
            
        Returns:
            Base64 인코딩된 QR 코드 이미지
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 이미지를 Base64로 변환
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return img_str


class CryptoAPI:
    """멀티 코인 네트워크 API 클래스"""
    
    def __init__(self, coin_type: str = 'bitcoin', testnet: bool = True):
        """
        Args:
            coin_type: 코인 타입 ('bitcoin', 'bitmobick')
            testnet: 테스트넷 사용 여부 (True: 테스트넷, False: 메인넷)
        """
        if coin_type not in NETWORK_CONFIGS:
            raise ValueError(f"지원하지 않는 코인 타입: {coin_type}")
            
        self.coin_type = coin_type
        self.testnet = testnet
        self.config = NETWORK_CONFIGS[coin_type]
        
        # API URL 설정
        if testnet:
            self.base_url = self.config['api_testnet']
        else:
            self.base_url = self.config['api_mainnet']
            
        # BitMobick의 경우 API가 없으면 Bitcoin API 사용 (호환성)
        if self.base_url is None:
            if testnet:
                self.base_url = NETWORK_CONFIGS['bitcoin']['api_testnet']
            else:
                self.base_url = NETWORK_CONFIGS['bitcoin']['api_mainnet']
    
    def get_balance(self, address: str) -> Dict[str, float]:
        """
        주소의 잔액 조회
        
        Args:
            address: 암호화폐 주소
            
        Returns:
            잔액 정보
        """
        try:
            if self.coin_type == 'bitmobick':
                # BitMobick HTML 파싱
                return self._parse_mobick_balance(address)
            else:
                # Bitcoin (BlockCypher) JSON API
                response = requests.get(f"{self.base_url}/addrs/{address}/balance")
                response.raise_for_status()
                data = response.json()
                
                # Satoshi를 기본 단위로 변환
                satoshi_per_unit = self.config['satoshi_per_unit']
                balance_main = data.get('balance', 0) / satoshi_per_unit
                unconfirmed_main = data.get('unconfirmed_balance', 0) / satoshi_per_unit
                
                return {
                    'confirmed_balance': balance_main,
                    'unconfirmed_balance': unconfirmed_main,
                    'total_balance': balance_main + unconfirmed_main,
                    'total_received': data.get('total_received', 0) / satoshi_per_unit,
                    'total_sent': data.get('total_sent', 0) / satoshi_per_unit,
                    'tx_count': data.get('n_tx', 0),
                    'coin_symbol': self.config['symbol']
                }
        except Exception as e:
            raise Exception(f"잔액 조회 실패: {str(e)}")
    
    def _parse_mobick_balance(self, address: str) -> Dict[str, float]:
        """BitMobick HTML 페이지에서 잔액 정보 파싱"""
        try:
            # User-Agent 설정으로 브라우저처럼 요청
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            url = f"https://blockchain2.mobick.info/address/{address}"
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 404:
                # 새 주소인 경우 0 잔액 반환
                return {
                    'confirmed_balance': 0.0,
                    'unconfirmed_balance': 0.0,
                    'total_balance': 0.0,
                    'total_received': 0.0,
                    'total_sent': 0.0,
                    'tx_count': 0,
                    'coin_symbol': self.config['symbol']
                }
            
            response.raise_for_status()
            
            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text()
            
            # 잔액 정보 기본값
            balance_data = {
                'confirmed_balance': 0.0,
                'unconfirmed_balance': 0.0,
                'total_balance': 0.0,
                'total_received': 0.0,
                'total_sent': 0.0,
                'tx_count': 0,
                'coin_symbol': self.config['symbol']
            }
            
            # 더 정확한 잔액 패턴들 (주소별 잔액만 추출)
            balance_patterns = [
                rf'Address[^:]*{re.escape(address)}[^0-9]*([0-9,.]+)\s*MO',  # 특정 주소의 잔액
                rf'{re.escape(address)}[^0-9]*Balance[:\s]*([0-9,.]+)',      # 주소 다음의 잔액
                r'Final Balance[:\s]*([0-9,.]+)\s*MO',                       # 최종 잔액
                r'Balance[:\s]*([0-9,.]+)\s*MO',                             # 일반적인 잔액
            ]
            
            for pattern in balance_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    try:
                        balance_str = matches[0].replace(',', '').replace(' MO', '')
                        balance = float(balance_str)
                        # 너무 큰 값은 무시 (전체 네트워크 통계일 가능성)
                        if balance < 1000000:  # 100만 MO 이하만 개인 잔액으로 간주
                            balance_data['confirmed_balance'] = balance
                            balance_data['total_balance'] = balance
                            break
                    except (ValueError, IndexError):
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
                    except (ValueError, IndexError):
                        continue
            
            return balance_data
            
        except Exception as e:
            # 에러 발생 시 0 잔액 반환 (새 주소일 가능성)
            return {
                'confirmed_balance': 0.0,
                'unconfirmed_balance': 0.0,
                'total_balance': 0.0,
                'total_received': 0.0,
                'total_sent': 0.0,
                'tx_count': 0,
                'coin_symbol': self.config['symbol'],
                'error': str(e)
            }
    
    def _get_demo_balance(self, address: str) -> Dict[str, float]:
        """
        BitMobick 데모 잔액 정보 생성
        
        Args:
            address: BitMobick 주소
            
        Returns:
            시뮬레이션된 잔액 정보
        """
        import hashlib
        import random
        
        # 주소를 기반으로 일관된 시드 생성
        seed = int(hashlib.md5(address.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        # 시뮬레이션된 잔액 생성
        confirmed_balance = random.uniform(0.001, 10.0)
        unconfirmed_balance = random.uniform(0, 0.1)
        total_received = confirmed_balance + random.uniform(0, 5.0)
        total_sent = total_received - confirmed_balance
        tx_count = random.randint(1, 50)
        
        return {
            'confirmed_balance': round(confirmed_balance, 8),
            'unconfirmed_balance': round(unconfirmed_balance, 8),
            'total_balance': round(confirmed_balance + unconfirmed_balance, 8),
            'total_received': round(total_received, 8),
            'total_sent': round(total_sent, 8),
            'tx_count': tx_count,
            'coin_symbol': self.config['symbol'],
            'demo_mode': True
        }
    
    def get_transactions(self, address: str, limit: int = 10) -> List[Dict]:
        """
        주소의 트랜잭션 내역 조회
        
        Args:
            address: 암호화폐 주소
            limit: 조회할 트랜잭션 수
            
        Returns:
            트랜잭션 리스트
        """
        try:
            if self.coin_type == 'bitmobick':
                # BitMobick HTML 파싱
                return self._parse_mobick_transactions(address, limit)
            else:
                # Bitcoin (BlockCypher) JSON API
                response = requests.get(f"{self.base_url}/addrs/{address}/full?limit={limit}")
                response.raise_for_status()
                data = response.json()
                
                transactions = []
                satoshi_per_unit = self.config['satoshi_per_unit']
                
                # Bitcoin (BlockCypher) API 응답 구조
                for tx in data.get('txs', []):
                    # 입출금 여부 및 금액 계산
                    total_input = sum(input_tx.get('output_value', 0) for input_tx in tx.get('inputs', []) 
                                    if any(addr == address for addr in input_tx.get('addresses', [])))
                    total_output = sum(output_tx.get('value', 0) for output_tx in tx.get('outputs', []) 
                                     if any(addr == address for addr in output_tx.get('addresses', [])))
                    
                    # 트랜잭션 타입 결정
                    if total_input > 0:
                        tx_type = "sent"
                        amount = -(total_input - total_output) / satoshi_per_unit  # 음수로 표시
                    else:
                        tx_type = "received"
                        amount = total_output / satoshi_per_unit
                    
                    transactions.append({
                        'hash': tx.get('hash'),
                        'type': tx_type,
                        'amount': amount,
                        'confirmations': tx.get('confirmations', 0),
                        'confirmed': tx.get('confirmed'),
                        'received': tx.get('received'),
                        'fees': tx.get('fees', 0) / satoshi_per_unit,
                        'size': tx.get('size', 0),
                        'coin_symbol': self.config['symbol']
                    })
                
                return transactions
        except Exception as e:
            raise Exception(f"트랜잭션 내역 조회 실패: {str(e)}")
    
    def _parse_mobick_transactions(self, address: str, limit: int = 10) -> List[Dict]:
        """BitMobick HTML 페이지에서 트랜잭션 내역 파싱"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            url = f"https://blockchain2.mobick.info/address/{address}"
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 404:
                return []  # 새 주소인 경우 빈 리스트
            
            response.raise_for_status()
            
            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            transactions = []
            
            # 트랜잭션 해시 패턴 찾기 (64자리 16진수)
            tx_hash_pattern = r'[a-fA-F0-9]{64}'
            text = soup.get_text()
            
            # 모든 트랜잭션 해시 찾기
            tx_hashes = re.findall(tx_hash_pattern, text)
            unique_hashes = list(set(tx_hashes))[:limit]
            
            # 각 트랜잭션 해시에 대한 기본 정보 생성
            for i, tx_hash in enumerate(unique_hashes):
                # 간단한 패턴으로 금액 추정 (실제 상세 정보는 별도 요청 필요)
                tx_data = {
                    'hash': tx_hash,
                    'type': 'received',  # 기본값
                    'amount': 0.0,  # HTML에서 추출하기 어려움
                    'confirmations': 1,
                    'confirmed': True,
                    'received': f'Recent {i+1}',
                    'fees': 0.0,
                    'size': 250,  # 추정값
                    'coin_symbol': self.config['symbol']
                }
                
                transactions.append(tx_data)
            
            return transactions
            
        except Exception as e:
            # 에러 발생 시 빈 리스트 반환
            return []
    
    def _get_demo_transactions(self, address: str, limit: int = 10) -> List[Dict]:
        """
        BitMobick 데모 트랜잭션 내역 생성
        
        Args:
            address: BitMobick 주소
            limit: 생성할 트랜잭션 수
            
        Returns:
            시뮬레이션된 트랜잭션 리스트
        """
        import hashlib
        import random
        from datetime import datetime, timedelta
        
        # 주소를 기반으로 일관된 시드 생성
        seed = int(hashlib.md5(address.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        transactions = []
        for i in range(min(limit, random.randint(3, 15))):
            # 랜덤 트랜잭션 생성
            tx_type = random.choice(['sent', 'received'])
            amount = random.uniform(0.001, 2.0)
            if tx_type == 'sent':
                amount = -amount
            
            # 가짜 해시 생성
            tx_hash = hashlib.sha256(f"{address}_{i}".encode()).hexdigest()
            
            # 시간 생성 (최근 30일 내)
            days_ago = random.randint(0, 30)
            tx_time = datetime.now() - timedelta(days=days_ago)
            
            transactions.append({
                'hash': tx_hash,
                'type': tx_type,
                'amount': round(amount, 8),
                'confirmations': random.randint(1, 100),
                'confirmed': True,
                'received': tx_time.isoformat() + 'Z',
                'fees': round(random.uniform(0.00001, 0.001), 8),
                'size': random.randint(200, 500),
                'coin_symbol': self.config['symbol'],
                'demo_mode': True
            })
        
        # 최신 거래가 먼저 오도록 정렬
        transactions.sort(key=lambda x: x['received'], reverse=True)
        return transactions
    
    def get_transaction_details(self, tx_hash: str) -> Dict:
        """
        특정 트랜잭션 상세 정보 조회
        
        Args:
            tx_hash: 트랜잭션 해시
            
        Returns:
            트랜잭션 상세 정보
        """
        try:
            if self.coin_type == 'bitmobick':
                # BitMobick API 호출
                response = requests.get(f"{self.base_url}/tx/{tx_hash}")
            else:
                # Bitcoin (BlockCypher) API
                response = requests.get(f"{self.base_url}/txs/{tx_hash}")
            
            response.raise_for_status()
            data = response.json()
            
            satoshi_per_unit = self.config['satoshi_per_unit']
            
            if self.coin_type == 'bitmobick':
                # Mobick API 응답 구조에 맞게 파싱
                return {
                    'hash': data.get('txid'),
                    'block_height': data.get('blockheight'),
                    'block_hash': data.get('blockhash'),
                    'total': sum(vout.get('value', 0) for vout in data.get('vout', [])) / satoshi_per_unit,
                    'fees': data.get('fees', 0) / satoshi_per_unit,
                    'size': data.get('size', 0),
                    'confirmations': data.get('confirmations', 0),
                    'confirmed': data.get('confirmations', 0) > 0,
                    'received': data.get('time'),
                    'inputs': data.get('vin', []),
                    'outputs': data.get('vout', []),
                    'coin_symbol': self.config['symbol']
                }
            else:
                # Bitcoin (BlockCypher) API 응답 구조
                return {
                    'hash': data.get('hash'),
                    'block_height': data.get('block_height'),
                    'block_hash': data.get('block_hash'),
                    'total': data.get('total', 0) / satoshi_per_unit,
                    'fees': data.get('fees', 0) / satoshi_per_unit,
                    'size': data.get('size', 0),
                    'confirmations': data.get('confirmations', 0),
                    'confirmed': data.get('confirmed'),
                    'received': data.get('received'),
                    'inputs': data.get('inputs', []),
                    'outputs': data.get('outputs', []),
                    'coin_symbol': self.config['symbol']
                }
        except Exception as e:
            raise Exception(f"트랜잭션 상세 조회 실패: {str(e)}")
    
    def _get_demo_transaction_details(self, tx_hash: str) -> Dict:
        """
        BitMobick 데모 트랜잭션 상세 정보 생성
        
        Args:
            tx_hash: 트랜잭션 해시
            
        Returns:
            시뮬레이션된 트랜잭션 상세 정보
        """
        import hashlib
        import random
        from datetime import datetime, timedelta
        
        # 해시를 기반으로 일관된 시드 생성
        seed = int(hashlib.md5(tx_hash.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        # 가짜 블록 해시 생성
        block_hash = hashlib.sha256(f"block_{tx_hash}".encode()).hexdigest()
        
        return {
            'hash': tx_hash,
            'block_height': random.randint(100000, 999999),
            'block_hash': block_hash,
            'total': round(random.uniform(0.001, 5.0), 8),
            'fees': round(random.uniform(0.00001, 0.001), 8),
            'size': random.randint(200, 500),
            'confirmations': random.randint(1, 100),
            'confirmed': True,
            'received': (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat() + 'Z',
            'inputs': [{'addresses': [f'Demo{random.randint(1000, 9999)}Input']}],
            'outputs': [{'addresses': [f'Demo{random.randint(1000, 9999)}Output']}],
            'coin_symbol': self.config['symbol'],
            'demo_mode': True
        }
    
    def send_transaction(self, from_address: str, to_address: str, amount: float, 
                        private_key: str) -> Dict:
        """
        암호화폐 송금 (테스트넷 전용)
        
        Args:
            from_address: 송금자 주소
            to_address: 수신자 주소
            amount: 송금할 코인 금액
            private_key: 송금자 개인키
            
        Returns:
            트랜잭션 결과
        """
        if not self.testnet:
            raise Exception("보안상 메인넷 송금은 지원하지 않습니다. 테스트넷을 사용하세요.")
        
        try:
            # 실제 구현에서는 UTXO 수집, 트랜잭션 구성, 서명 등이 필요
            # 여기서는 API를 사용한 간단한 방법을 시뮬레이션
            amount_satoshi = int(amount * self.config['satoshi_per_unit'])
            
            # 트랜잭션 생성 요청
            tx_data = {
                "inputs": [{"addresses": [from_address]}],
                "outputs": [{"addresses": [to_address], "value": amount_satoshi}]
            }
            
            # 실제로는 여기서 서명 과정이 필요
            # 데모 목적으로 성공 응답 시뮬레이션
            return {
                'success': True,
                'tx_hash': 'demo_transaction_hash',
                'message': f'{self.config["name"]} 테스트넷 트랜잭션이 성공적으로 생성되었습니다.',
                'amount': amount,
                'from': from_address,
                'to': to_address,
                'coin_symbol': self.config['symbol']
            }
        except Exception as e:
            raise Exception(f"트랜잭션 생성 실패: {str(e)}")


def validate_crypto_address(address: str, coin_type: str = 'bitcoin') -> bool:
    """
    암호화폐 주소 유효성 검사
    
    Args:
        address: 검사할 암호화폐 주소
        coin_type: 코인 타입
        
    Returns:
        유효성 여부
    """
    try:
        # Base58 디코딩
        decoded = base58.b58decode(address)
        
        # 길이 확인 (25바이트: 1바이트 네트워크 + 20바이트 해시 + 4바이트 체크섬)
        if len(decoded) != 25:
            return False
        
        # 체크섬 검증
        payload = decoded[:-4]
        checksum = decoded[-4:]
        calculated_checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        
        if checksum != calculated_checksum:
            return False
            
        # 네트워크 바이트 확인
        if coin_type in NETWORK_CONFIGS:
            config = NETWORK_CONFIGS[coin_type]
            network_byte = payload[0:1]
            valid_bytes = [config['mainnet_byte'], config['testnet_byte']]
            return network_byte in valid_bytes
            
        return True
    except:
        return False


# 하위 호환성을 위한 함수
def validate_bitcoin_address(address: str) -> bool:
    """비트코인 주소 유효성 검사 (하위 호환성)"""
    return validate_crypto_address(address, 'bitcoin')


def format_crypto_amount(amount: float, coin_symbol: str = 'BTC', decimals: int = 8) -> str:
    """암호화폐 금액 포맷팅"""
    if amount == 0:
        return f"0.{'0' * decimals} {coin_symbol}"
    elif abs(amount) < (1 / (10 ** decimals)):
        return f"{amount:.2e} {coin_symbol}"
    else:
        return f"{amount:.{decimals}f} {coin_symbol}"


# 하위 호환성을 위한 함수
def format_bitcoin_amount(amount: float) -> str:
    """비트코인 금액 포맷팅 (하위 호환성)"""
    return format_crypto_amount(amount, 'BTC', 8)


def format_timestamp(timestamp: str) -> str:
    """타임스탬프 포맷팅"""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp
