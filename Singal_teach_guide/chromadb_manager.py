import os
import hashlib
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
import requests
import json
from dotenv import load_dotenv
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class ChromaDBManager:
    def __init__(self):
        self.db_path = os.getenv('CHROMA_DB_PATH', './chroma_db')
        self.embedding_model = os.getenv('DEPLOY_EMBED', 'text-embedding-ada-002')
        self.endpoint = os.getenv('ENDPOINT', 'https://api.openai.com/v1/')
        self.api_key = os.getenv('API_KEY')
        
        # OpenAI API 설정 (직접 HTTP 요청 사용)
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # 컬렉션 생성 또는 가져오기
        try:
            self.collection = self.client.get_collection(name="rag_collection")
        except:
            self.collection = self.client.create_collection(
                name="rag_collection",
                metadata={"hnsw:space": "cosine"}
            )
        
        # URL 추적을 위한 메타데이터 컬렉션
        try:
            self.url_collection = self.client.get_collection(name="url_tracking")
        except:
            self.url_collection = self.client.create_collection(name="url_tracking")
    
    def _get_embedding(self, text: str) -> List[float]:
        """텍스트를 임베딩 벡터로 변환 (직접 HTTP 요청)"""
        try:
            # 텍스트 전처리
            text = text.strip()
            if not text:
                raise ValueError("빈 텍스트는 임베딩할 수 없습니다.")
            
            # 너무 긴 텍스트 제한 (Azure OpenAI 토큰 제한)
            if len(text) > 8000:
                text = text[:8000]
                logger.warning(f"텍스트가 너무 길어 8000자로 잘렸습니다.")
            
            # Azure OpenAI 엔드포인트 감지
            if 'azure.com' in self.endpoint.lower():
                # Azure OpenAI API 형식
                url = f"{self.endpoint.rstrip('/')}/openai/deployments/{self.embedding_model}/embeddings"
                # Azure OpenAI API 버전 추가
                if '?' in url:
                    url += f"&api-version=2023-05-15"
                else:
                    url += "?api-version=2023-05-15"
                    
                # Azure OpenAI는 api-key 헤더 사용
                headers = {
                    'api-key': self.api_key,
                    'Content-Type': 'application/json'
                }
            else:
                # 일반 OpenAI API 형식
                url = f"{self.endpoint.rstrip('/')}/embeddings"
                headers = self.headers
            
            payload = {
                'input': text
            }
            
            # Azure OpenAI가 아닌 경우에만 model 필드 추가
            if 'azure.com' not in self.endpoint.lower():
                payload['model'] = self.embedding_model
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            embedding = result['data'][0]['embedding']
            
            # 임베딩 벡터 검증
            if not embedding or len(embedding) == 0:
                raise ValueError("빈 임베딩 벡터가 반환되었습니다.")
            
            # 임베딩 벡터 정규화 (코사인 유사도를 위해)
            import math
            magnitude = math.sqrt(sum(x*x for x in embedding))
            if magnitude == 0:
                raise ValueError("임베딩 벡터의 크기가 0입니다.")
            
            normalized_embedding = [x / magnitude for x in embedding]
            
            logger.debug(f"임베딩 차원: {len(normalized_embedding)}, 크기: {magnitude:.6f}")
            
            return normalized_embedding
            
        except requests.exceptions.RequestException as e:
            logger.error(f"임베딩 API 요청 실패: {str(e)}")
            logger.error(f"요청 URL: {url if 'url' in locals() else 'N/A'}")
            raise
        except KeyError as e:
            logger.error(f"임베딩 응답 파싱 실패: {str(e)}")
            logger.error(f"응답 내용: {result if 'result' in locals() else 'N/A'}")
            raise
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {str(e)}")
            raise
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """텍스트를 청크로 분할 (개선된 버전)"""
        import re
        
        # 전처리: 불필요한 공백 제거
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) < 100:  # 너무 짧은 텍스트는 반환하지 않음
            return []
        
        chunks = []
        
        # 1단계: 문단별로 분할 (\n\n 기준)
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # 현재 청크에 문단을 추가했을 때 크기 체크
            test_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            
            if len(test_chunk) <= chunk_size:
                current_chunk = test_chunk
            else:
                # 현재 청크를 저장하고 새로 시작
                if current_chunk and len(current_chunk.split()) >= 10:  # 최소 10단어 이상
                    chunks.append(current_chunk.strip())
                
                # 단일 문단이 너무 큰 경우 세분화
                if len(paragraph) > chunk_size:
                    sub_chunks = self._split_large_paragraph(paragraph, chunk_size, chunk_overlap)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = paragraph
        
        # 마지막 청크 추가
        if current_chunk and len(current_chunk.split()) >= 10:
            chunks.append(current_chunk.strip())
        
        # 최종 필터링: 중복 제거 및 품질 검사
        filtered_chunks = []
        seen_chunks = set()
        
        for chunk in chunks:
            # 중복 체크 제거 (유사도 기반)
            chunk_hash = hash(chunk[:100])  # 처음 100자로 중복 판단
            if chunk_hash in seen_chunks:
                continue
            seen_chunks.add(chunk_hash)
            
            # 품질 검사
            if self._is_quality_chunk(chunk):
                filtered_chunks.append(chunk)
        
        logger.info(f"청킹 결과: {len(chunks)} -> {len(filtered_chunks)} (필터링 후)")
        return filtered_chunks
    
    def _split_large_paragraph(self, paragraph: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """큰 문단을 세분화"""
        sentences = re.split(r'[.!?]\s+', paragraph)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            test_chunk = current_chunk + ". " + sentence if current_chunk else sentence
            
            if len(test_chunk) <= chunk_size:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk + ".")
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk + ".")
        
        return chunks
    
    def _is_quality_chunk(self, chunk: str) -> bool:
        """청크 품질 검사"""
        import re
        
        # 기본 길이 체크
        if len(chunk) < 50 or len(chunk.split()) < 10:
            return False
        
        # 노이즈 패턴 체크
        noise_patterns = [
            r'^\s*메뉴',
            r'^\s*내비게이션',
            r'^로그인',
            r'^검색',
            r'^광고',
            r'^공유하기',
            r'^댓글',
            r'^저작권',
            r'^Copyright',
            r'^©',
            r'카테고리:',
            r'태그:',
        ]
        
        for pattern in noise_patterns:
            if re.search(pattern, chunk, re.IGNORECASE):
                return False
        
        # 반복 패턴 체크 (동일 단어가 너무 많이 반복)
        words = chunk.lower().split()
        if len(words) > 0:
            most_common_word = max(set(words), key=words.count)
            if words.count(most_common_word) / len(words) > 0.3:  # 30% 이상 반복
                return False
        
        # 의미있는 콘텐츠 비율 체크
        meaningful_chars = re.sub(r'[^\w\s]', '', chunk)
        if len(meaningful_chars) / len(chunk) < 0.7:  # 70% 이상이 의미있는 문자여야 함
            return False
        
        return True
    
    def is_url_processed(self, url: str) -> bool:
        """URL이 이미 처리되었는지 확인"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        results = self.url_collection.get(ids=[url_hash])
        return len(results['ids']) > 0
    
    def mark_url_processed(self, url: str):
        """URL을 처리됨으로 표시"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        self.url_collection.add(
            ids=[url_hash],
            documents=[url],
            metadatas=[{"url": url, "processed": True}]
        )
    
    def add_documents(self, documents: List[Dict[str, Any]], chunk_size: int = 1000, 
                     chunk_overlap: int = 200) -> Dict[str, Any]:
        """문서를 ChromaDB에 추가"""
        added_count = 0
        skipped_urls = []
        
        for doc in documents:
            # URL 중복 체크
            if 'source' in doc and doc['source'].startswith('http'):
                if self.is_url_processed(doc['source']):
                    skipped_urls.append(doc['source'])
                    continue
            
            # 텍스트 청킹
            chunks = self._chunk_text(doc['content'], chunk_size, chunk_overlap)
            
            # 각 청크에 대해 임베딩 생성 및 저장
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc.get('source', 'unknown')}_{i}_{hashlib.md5(chunk.encode()).hexdigest()[:8]}"
                
                try:
                    embedding = self._get_embedding(chunk)
                    
                    self.collection.add(
                        ids=[chunk_id],
                        embeddings=[embedding],
                        documents=[chunk],
                        metadatas=[{
                            "source": doc.get('source', 'unknown'),
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            "title": doc.get('title', ''),
                            "type": doc.get('type', 'text')
                        }]
                    )
                    added_count += 1
                except Exception as e:
                    logger.error(f"청크 추가 실패: {str(e)}")
            
            # URL을 처리됨으로 표시
            if 'source' in doc and doc['source'].startswith('http'):
                self.mark_url_processed(doc['source'])
        
        return {
            "added_chunks": added_count,
            "skipped_urls": skipped_urls
        }
    
    def search(self, query: str, n_results: int = 5, min_similarity: float = 0.3) -> List[Dict[str, Any]]:
        """유사도 검색 수행"""
        try:
            query_embedding = self._get_embedding(query)
            logger.info(f"검색어: '{query}', 임베딩 차원: {len(query_embedding)}")
            
            # 데이터베이스에 있는 총 문서 수 확인
            total_count = self.collection.count()
            actual_n_results = min(n_results, total_count, 20)  # 최대 20개로 제한
            
            if total_count == 0:
                return []
            
            logger.info(f"데이터베이스 총 문서 수: {total_count}, 검색 개수: {actual_n_results}")
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=actual_n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # 디버깅: 원본 거리 값 로깅
            if results['distances'][0]:
                logger.info(f"원본 거리 값들: {results['distances'][0][:3]}...")  # 처음 3개만
            
            # 결과 포맷팅 및 필터링
            formatted_results = []
            for i in range(len(results['ids'][0])):
                distance = results['distances'][0][i]
                
                # ChromaDB의 코사인 거리 범위 확인 및 조정
                logger.debug(f"더비깅 - 인덱스 {i}: 거리={distance}")
                
                # ChromaDB 코사인 거리를 유사도로 변환
                # 코사인 거리: 0(동일) ~ 2(정반대)
                # 유사도 = 1 - (distance / 2)
                similarity_score = max(0, min(1, 1 - (distance / 2)))
                
                logger.debug(f"더비깅 - 거리 {distance:.4f} -> 유사도 {similarity_score:.4f}")
                
                # 최소 유사도 임계값 적용
                if similarity_score >= min_similarity:
                    formatted_results.append({
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'similarity_score': similarity_score,
                        'distance': distance,
                        'relevance_level': self._get_relevance_level(similarity_score)
                    })
            
            logger.info(f"필터링 후 결과 수: {len(formatted_results)}")
            
            # 유사도 높은 순으로 정렬
            formatted_results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return formatted_results
        except Exception as e:
            logger.error(f"검색 실패: {str(e)}")
            raise
    
    def _get_relevance_level(self, similarity_score: float) -> str:
        """유사도 점수에 따른 관련도 레벨 반환"""
        if similarity_score >= 0.9:
            return "매우 높음"
        elif similarity_score >= 0.8:
            return "높음"
        elif similarity_score >= 0.6:
            return "보통"
        elif similarity_score >= 0.4:
            return "낮음"
        else:
            return "매우 낮음"
    
    
    def clear_database(self):
        """데이터베이스 초기화"""
        try:
            # 컬렉션 삭제 및 재생성
            self.client.delete_collection(name="rag_collection")
            self.client.delete_collection(name="url_tracking")
            
            self.collection = self.client.create_collection(
                name="rag_collection",
                metadata={"hnsw:space": "cosine"}
            )
            self.url_collection = self.client.create_collection(name="url_tracking")
            
            return {"status": "success", "message": "데이터베이스가 초기화되었습니다."}
        except Exception as e:
            logger.error(f"데이터베이스 초기화 실패: {str(e)}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """데이터베이스 통계 정보 반환"""
        try:
            rag_count = self.collection.count()
            url_count = self.url_collection.count()
            
            return {
                "total_chunks": rag_count,
                "processed_urls": url_count
            }
        except Exception as e:
            logger.error(f"통계 조회 실패: {str(e)}")
            return {"total_chunks": 0, "processed_urls": 0}
    
    def force_rebuild_database(self):
        """데이터베이스 강제 재구축 (청킹 개선 적용)"""
        try:
            logger.info("데이터베이스 강제 재구축 시작...")
            
            # 기존 컶렉션 삭제
            self.client.delete_collection(name="rag_collection")
            self.client.delete_collection(name="url_tracking")
            
            # 새 컴렉션 생성
            self.collection = self.client.create_collection(
                name="rag_collection",
                metadata={"hnsw:space": "cosine"}
            )
            self.url_collection = self.client.create_collection(name="url_tracking")
            
            logger.info("데이터베이스 재구축 완료")
            return {"status": "success", "message": "데이터베이스가 강제 재구축되었습니다."}
            
        except Exception as e:
            logger.error(f"데이터베이스 재구축 실패: {str(e)}")
            raise
