import hashlib
import hmac
import jwt
import requests
import uuid
from urllib.parse import urlencode
import time
from typing import Dict, List, Optional, Any


class UpbitAPI:
    def __init__(self, access_key: str, secret_key: str):
        """
        Upbit API 클라이언트 초기화
        
        Args:
            access_key: Upbit API Access Key
            secret_key: Upbit API Secret Key
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.server_url = "https://api.upbit.com"
        
    def _get_headers(self, query_params: Optional[Dict] = None) -> Dict[str, str]:
        """
        API 요청을 위한 인증 헤더 생성
        
        Args:
            query_params: 쿼리 파라미터
            
        Returns:
            인증 헤더
        """
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
        }
        
        if query_params:
            # 배열 파라미터를 올바르게 처리
            query_string = urlencode(query_params, doseq=True)
            m = hashlib.sha512()
            m.update(query_string.encode())
            query_hash = m.hexdigest()
            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = 'SHA512'
        
        jwt_token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        
        return {
            'Authorization': f'Bearer {jwt_token}',
            'Content-Type': 'application/json'
        }
    
    def get_accounts(self) -> List[Dict[str, Any]]:
        """
        전체 계정 조회 (자산 현황)
        
        Returns:
            계정 정보 리스트
        """
        try:
            headers = self._get_headers()
            response = requests.get(
                f"{self.server_url}/v1/accounts", 
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                raise Exception(f"계정 조회 권한이 없습니다. Upbit에서 API 키 권한을 확인해주세요. (오류: {str(e)})")
            elif e.response.status_code == 401:
                raise Exception(f"API 키 인증에 실패했습니다. API 키를 다시 확인해주세요. (오류: {str(e)})")
            else:
                raise Exception(f"계정 조회 실패: {str(e)}")
        except Exception as e:
            raise Exception(f"계정 조회 실패: {str(e)}")
    
    def get_order_chance(self, market: str) -> Dict[str, Any]:
        """
        주문 가능 정보 조회
        
        Args:
            market: 마켓 ID (ex: KRW-BTC)
            
        Returns:
            주문 가능 정보
        """
        try:
            query_params = {'market': market}
            headers = self._get_headers(query_params)
            response = requests.get(
                f"{self.server_url}/v1/orders/chance",
                params=query_params,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"주문 가능 정보 조회 실패: {str(e)}")
    
    def place_order(self, market: str, side: str, volume: Optional[str] = None, 
                   price: Optional[str] = None, ord_type: str = 'limit') -> Dict[str, Any]:
        """
        주문하기
        
        Args:
            market: 마켓 ID (ex: KRW-BTC)
            side: 주문 종류 ('bid': 매수, 'ask': 매도)
            volume: 주문량 (지정가, 시장가 매도 시 필수)
            price: 주문 가격 (지정가 시 필수)
            ord_type: 주문 타입 ('limit': 지정가, 'price': 시장가 매수, 'market': 시장가 매도)
            
        Returns:
            주문 결과
        """
        try:
            query_params = {
                'market': market,
                'side': side,
                'ord_type': ord_type
            }
            
            if volume:
                query_params['volume'] = volume
            if price:
                query_params['price'] = price
                
            headers = self._get_headers(query_params)
            response = requests.post(
                f"{self.server_url}/v1/orders",
                json=query_params,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                raise Exception(f"주문 권한이 없습니다. Upbit에서 API 키 권한을 확인해주세요. (오류: {str(e)})")
            elif e.response.status_code == 401:
                raise Exception(f"API 키 인증에 실패했습니다. API 키를 다시 확인해주세요. (오류: {str(e)})")
            elif e.response.status_code == 400:
                raise Exception(f"잘못된 주문 요청입니다. 주문 정보를 확인해주세요. (오류: {str(e)})")
            else:
                raise Exception(f"주문 실패: {str(e)}")
        except Exception as e:
            raise Exception(f"주문 실패: {str(e)}")
    
    def get_orders(self, market: Optional[str] = None, state: str = 'wait', 
                  states: Optional[List[str]] = None, page: int = 1, 
                  limit: int = 100, order_by: str = 'asc') -> List[Dict[str, Any]]:
        """
        주문 리스트 조회
        
        Args:
            market: 마켓 ID
            state: 주문 상태 ('wait', 'done', 'cancel')
            states: 주문 상태 리스트
            page: 페이지 수
            limit: 요청 개수
            order_by: 정렬 방식 ('asc', 'desc')
            
        Returns:
            주문 리스트
        """
        try:
            query_params = {
                'page': page,
                'limit': limit,
                'order_by': order_by
            }
            
            if market:
                query_params['market'] = market
            if states:
                # states 배열을 올바르게 처리 - Upbit API는 states[] 형태로 받음
                query_params['states[]'] = states
            elif state:
                query_params['state'] = state
                
            headers = self._get_headers(query_params)
            response = requests.get(
                f"{self.server_url}/v1/orders",
                params=query_params,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                raise Exception(f"주문 조회 권한이 없습니다. Upbit에서 API 키 권한을 확인해주세요. (오류: {str(e)})")
            elif e.response.status_code == 401:
                raise Exception(f"API 키 인증에 실패했습니다. API 키를 다시 확인해주세요. (오류: {str(e)})")
            else:
                raise Exception(f"주문 리스트 조회 실패: {str(e)}")
        except Exception as e:
            raise Exception(f"주문 리스트 조회 실패: {str(e)}")
    
    def cancel_order(self, uuid_order: str) -> Dict[str, Any]:
        """
        주문 취소
        
        Args:
            uuid_order: 취소할 주문의 UUID
            
        Returns:
            취소 결과
        """
        try:
            query_params = {'uuid': uuid_order}
            headers = self._get_headers(query_params)
            response = requests.delete(
                f"{self.server_url}/v1/order",
                params=query_params,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"주문 취소 실패: {str(e)}")


def get_market_all() -> List[Dict[str, Any]]:
    """
    마켓 코드 조회 (인증 불필요)
    
    Returns:
        마켓 정보 리스트
    """
    try:
        response = requests.get("https://api.upbit.com/v1/market/all")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"마켓 정보 조회 실패: {str(e)}")


def get_ticker(markets: List[str]) -> List[Dict[str, Any]]:
    """
    현재가 정보 조회 (인증 불필요)
    
    Args:
        markets: 마켓 ID 리스트 (ex: ['KRW-BTC', 'KRW-ETH'])
        
    Returns:
        현재가 정보 리스트
    """
    try:
        markets_param = ','.join(markets)
        response = requests.get(
            f"https://api.upbit.com/v1/ticker?markets={markets_param}"
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"현재가 정보 조회 실패: {str(e)}")
