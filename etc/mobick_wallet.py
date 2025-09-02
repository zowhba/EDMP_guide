#!/usr/bin/env python3
"""BitMobick 전용 지갑 라이브러리"""

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

# BitMobick 네트워크 설정
MOBICK_CONFIG = {
    'name': 'BitMobick',
    'symbol': 'MO',
    'mainnet_byte': b'\x00',  # 1로 시작하는 주소
    'testnet_byte': b'\x6f',  # 테스트넷
    'wif_mainnet_byte': b'\x80',
    'wif_testnet_byte': b'\xef',
    'decimals': 8,
    'satoshi_per_unit': 100000000,
    'explorer_url': 'https://blockchain2.mobick.info'
}

class MobickWallet:
    """BitMobick 전용 지갑 클래스"""
    
    def __init__(self, testnet: bool = False):
        """
        Args:
            testnet: 테스트넷 사용 여부
        """
        self.testnet = testnet
        self.config = MOBICK_CONFIG
        self.private_key = None
        self.public_key = None
        self.address = None
        self.wif = None
    
    def generate_wallet(self) -> Dict[str, str]:
        """
        새 BitMobick 지갑 생성
        
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
        
        # 3. BitMobick 주소 생성 (P2PKH - Pay to Public Key Hash)
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
            private_key_or_wif: 개인키(Hex) 또는 WIF
            
        Returns:
            지갑 정보
        """
        try:
            # WIF 형식인지 확인 (Base58로 인코딩되고 길이가 51-52자)
            if len(private_key_or_wif) in [51, 52] and private_key_or_wif[0] in ['5', 'K', 'L', '9', 'c']:
                # WIF에서 개인키 추출
                private_key_bytes = self._wif_to_private_key(private_key_or_wif)
            else:
                # Hex 형식 개인키
                private_key_bytes = bytes.fromhex(private_key_or_wif)
            
            self.private_key = private_key_bytes.hex()
            
            # 공개키 생성
            sk = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)
            vk = sk.verifying_key
            public_key_bytes = b'\x04' + vk.to_string()
            self.public_key = public_key_bytes.hex()
            
            # 주소 생성
            self.address = self._public_key_to_address(public_key_bytes)
            
            # WIF 생성
            self.wif = self._private_key_to_wif(private_key_bytes)
            
            return {
                'private_key': self.private_key,
                'public_key': self.public_key,
                'address': self.address,
                'wif': self.wif
            }
            
        except Exception as e:
            raise Exception(f"지갑 가져오기 실패: {str(e)}")
    
    def _public_key_to_address(self, public_key_bytes: bytes) -> str:
        """공개키를 BitMobick 주소로 변환"""
        # SHA256 해시
        sha256_hash = hashlib.sha256(public_key_bytes).digest()
        
        # RIPEMD160 해시
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256_hash)
        pubkey_hash = ripemd160.digest()
        
        # 네트워크 바이트 추가
        network_byte = self.config['testnet_byte'] if self.testnet else self.config['mainnet_byte']
        versioned_payload = network_byte + pubkey_hash
        
        # 체크섬 계산 (SHA256을 두 번)
        checksum = hashlib.sha256(hashlib.sha256(versioned_payload).digest()).digest()[:4]
        
        # Base58 인코딩
        binary_address = versioned_payload + checksum
        address = base58.b58encode(binary_address).decode('ascii')
        
        return address
    
    def _private_key_to_wif(self, private_key_bytes: bytes) -> str:
        """개인키를 WIF 형식으로 변환"""
        # 네트워크 바이트 추가
        wif_byte = self.config['wif_testnet_byte'] if self.testnet else self.config['wif_mainnet_byte']
        extended_key = wif_byte + private_key_bytes
        
        # 체크섬 계산
        checksum = hashlib.sha256(hashlib.sha256(extended_key).digest()).digest()[:4]
        
        # Base58 인코딩
        wif = base58.b58encode(extended_key + checksum).decode('ascii')
        
        return wif
    
    def _wif_to_private_key(self, wif: str) -> bytes:
        """WIF를 개인키로 변환"""
        try:
            decoded = base58.b58decode(wif)
            
            # 체크섬 검증
            payload = decoded[:-4]
            checksum = decoded[-4:]
            calculated_checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
            
            if checksum != calculated_checksum:
                raise Exception("WIF 체크섬 검증 실패")
            
            # 네트워크 바이트 제거하고 개인키 반환
            private_key = payload[1:]  # 첫 번째 바이트(네트워크 바이트) 제거
            
            return private_key
        except Exception as e:
            raise Exception(f"WIF 디코딩 실패: {str(e)}")
    
    def generate_qr_code(self, data: str, size: int = 10) -> str:
        """
        QR 코드 생성
        
        Args:
            data: QR 코드에 포함할 데이터
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
        
        # 이미지를 Base64로 인코딩
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"

class MobickAPI:
    """BitMobick 블록체인 API 클래스"""
    
    def __init__(self, testnet: bool = False):
        self.testnet = testnet
        self.config = MOBICK_CONFIG
        self.base_url = self.config['explorer_url']
    
    def get_balance(self, address: str) -> Dict[str, float]:
        """
        주소의 잔액 조회
        
        Args:
            address: BitMobick 주소
            
        Returns:
            잔액 정보
        """
        return self._parse_mobick_balance(address)
    
    def _parse_mobick_balance(self, address: str) -> Dict[str, float]:
        """BitMobick HTML 페이지에서 잔액 정보 파싱"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            url = f"{self.base_url}/address/{address}"
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
            
            # 더 정확한 잔액 패턴들
            balance_patterns = [
                rf'Address[^:]*{re.escape(address)}[^0-9]*([0-9,.]+)\s*MO',
                rf'{re.escape(address)}[^0-9]*Balance[:\s]*([0-9,.]+)',
                r'Final Balance[:\s]*([0-9,.]+)\s*MO',
                r'Balance[:\s]*([0-9,.]+)\s*MO',
            ]
            
            for pattern in balance_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    try:
                        balance_str = matches[0].replace(',', '').replace(' MO', '')
                        balance = float(balance_str)
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
            # 에러 발생 시 0 잔액 반환
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
    
    def get_transactions(self, address: str, limit: int = 10) -> List[Dict]:
        """
        주소의 트랜잭션 내역 조회
        
        Args:
            address: BitMobick 주소
            limit: 조회할 트랜잭션 수
            
        Returns:
            트랜잭션 리스트
        """
        return self._parse_mobick_transactions(address, limit)
    
    def _parse_mobick_transactions(self, address: str, limit: int = 10) -> List[Dict]:
        """BitMobick HTML 페이지에서 트랜잭션 내역 파싱"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            url = f"{self.base_url}/address/{address}"
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
                tx_data = {
                    'hash': tx_hash,
                    'type': 'received',  # 기본값
                    'amount': 0.0,
                    'confirmations': 1,
                    'confirmed': True,
                    'received': f'Recent {i+1}',
                    'fees': 0.0,
                    'size': 250,
                    'coin_symbol': self.config['symbol']
                }
                
                transactions.append(tx_data)
            
            return transactions
            
        except Exception as e:
            return []

def validate_mobick_address(address: str) -> bool:
    """
    BitMobick 주소 유효성 검사
    
    Args:
        address: 검사할 주소
        
    Returns:
        유효성 여부
    """
    if not address:
        return False
    
    try:
        # BitMobick 주소는 1로 시작
        if not address.startswith('1'):
            return False
        
        if len(address) < 25 or len(address) > 34:
            return False
        
        # Base58 디코딩 시도
        decoded = base58.b58decode(address)
        if len(decoded) != 25:
            return False
        
        # 체크섬 검증
        payload = decoded[:-4]
        checksum = decoded[-4:]
        calculated_checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        
        return checksum == calculated_checksum
        
    except Exception:
        return False

def format_mobick_amount(amount: float, decimals: int = 8) -> str:
    """BitMobick 금액 포맷팅"""
    if amount == 0:
        return "0.00000000 MO"
    
    # 소수점 자릿수 조정
    formatted = f"{amount:.{decimals}f}"
    
    # 불필요한 0 제거 (하지만 최소 2자리는 유지)
    if '.' in formatted:
        formatted = formatted.rstrip('0').rstrip('.')
        if '.' not in formatted:
            formatted += ".00"
        elif len(formatted.split('.')[1]) < 2:
            formatted += '0' * (2 - len(formatted.split('.')[1]))
    
    return f"{formatted} MO"

def format_timestamp(timestamp: str) -> str:
    """타임스탬프 포맷팅"""
    try:
        from datetime import datetime
        
        # ISO 형식인 경우
        if 'T' in timestamp:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return timestamp
    except:
        return timestamp
