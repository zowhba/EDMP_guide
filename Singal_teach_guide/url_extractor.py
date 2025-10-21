import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging
from typing import Dict, Any, Optional
import time

logger = logging.getLogger(__name__)


class URLExtractor:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.timeout = 30
    
    def extract_content(self, url: str) -> Dict[str, Any]:
        """URL에서 콘텐츠 추출"""
        try:
            # URL 유효성 검사
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"유효하지 않은 URL: {url}")
            
            # 콘텐츠 가져오기
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            # 인코딩 처리
            if response.encoding is None:
                response.encoding = response.apparent_encoding
            
            # HTML 파싱
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 메타데이터 추출
            title = self._extract_title(soup)
            description = self._extract_description(soup)
            
            # 본문 콘텐츠 추출
            content = self._extract_main_content(soup)
            
            return {
                'source': url,
                'title': title,
                'description': description,
                'content': content,
                'type': 'webpage',
                'status': 'success'
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"URL 요청 실패 {url}: {str(e)}")
            return {
                'source': url,
                'status': 'error',
                'error': f"웹 페이지 접근 실패: {str(e)}"
            }
        except Exception as e:
            logger.error(f"콘텐츠 추출 실패 {url}: {str(e)}")
            return {
                'source': url,
                'status': 'error',
                'error': f"콘텐츠 추출 실패: {str(e)}"
            }
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """제목 추출"""
        # 다양한 방법으로 제목 추출 시도
        title = None
        
        # 1. <title> 태그
        if soup.title:
            title = soup.title.string
        
        # 2. <h1> 태그
        if not title:
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)
        
        # 3. meta property="og:title"
        if not title:
            meta_title = soup.find('meta', property='og:title')
            if meta_title:
                title = meta_title.get('content')
        
        return title.strip() if title else "제목 없음"
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """설명 추출"""
        description = None
        
        # 1. meta name="description"
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content')
        
        # 2. meta property="og:description"
        if not description:
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                description = og_desc.get('content')
        
        return description.strip() if description else ""
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """본문 콘텐츠 추출 (강화된 전처리)"""
        # 스크립트와 스타일 태그 제거
        for script in soup(['script', 'style', 'noscript']):
            script.decompose()
        
        # 노이즈 요소들 제거 (강화)
        noise_selectors = [
            'nav', 'footer', 'header', 'aside',
            '.navigation', '.nav', '.menu', '.sidebar',
            '.advertisement', '.ads', '.ad', '.promo',
            '.related', '.recommendations', '.suggestion',
            '.comments', '.comment-section', '.feedback',
            '.social-media', '.social-share', '.share-buttons',
            '.breadcrumb', '.pagination', '.pager',
            '.footer-links', '.copyright', '.disclaimer',
            '#toc', '.table-of-contents', '.toc',
            '.infobox', '.navbox', '.metadata',
            '.cite', '.reference', '.footnote'
        ]
        
        for selector in noise_selectors:
            for element in soup.select(selector):
                element.decompose()
        
        # 본문 콘텐츠 찾기
        content_candidates = []
        
        # 1. article 태그
        articles = soup.find_all('article')
        for article in articles:
            text = article.get_text(separator='\n', strip=True)
            if len(text) > 100:  # 너무 짧은 콘텐츠 제외
                content_candidates.append(text)
        
        # 2. main 태그
        main = soup.find('main')
        if main:
            text = main.get_text(separator='\n', strip=True)
            if len(text) > 100:
                content_candidates.append(text)
        
        # 3. 특정 클래스/ID를 가진 div
        content_selectors = [
            '.content', '.post', '.entry', '.article-body',
            '.main-content', '.post-content', '.entry-content',
            '.article-text', '.story-body', '.text-content',
            '#content', '#main', '#article', '#post'
        ]
        
        for selector in content_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(separator='\n', strip=True)
                if len(text) > 100:
                    content_candidates.append(text)
        
        # 4. 가장 긴 콘텐츠 선택
        if content_candidates:
            content = max(content_candidates, key=len)
        else:
            # 전체 body에서 텍스트 추출
            body = soup.find('body')
            if body:
                content = body.get_text(separator='\n', strip=True)
            else:
                content = soup.get_text(separator='\n', strip=True)
        
        # 콘텐츠 정제 (강화)
        content = self._clean_extracted_content(content)
        
        return content
    
    def _clean_extracted_content(self, content: str) -> str:
        """추출된 콘텐츠 정제"""
        import re
        
        lines = content.split('\n')
        cleaned_lines = []
        
        # 노이즈 패턴 제거
        noise_patterns = [
            r'^\s*메뉴\s*$',
            r'^\s*내비게이션\s*$',
            r'^\s*바로가기\s*$',
            r'^\s*로그인\s*$',
            r'^\s*회원가입\s*$',
            r'^\s*검색\s*$',
            r'^\s*광고\s*$',
            r'^\s*청주\uc2dc.*과\s*$',
            r'^\s*추천\s*$',
            r'^\s*더보기\s*$',
            r'^\s*공유하기\s*$',
            r'^\s*댓글\s*$',
            r'^\s*페이지.*의\s*$',
            r'^\s*본문.*바로가기\s*$',
            r'^\s*맨.*바로가기\s*$',
            r'^\s*저작권.*\s*$',
            r'^\s*Copyright.*\s*$',
            r'^\s*©.*\s*$',
            r'^\s*이.*문서는.*\s*$',
            r'^\s*참고.*:\s*$',
            r'^\s*관련.*항목\s*$',
            r'^\s*카테고리:\s*$',
            r'^\s*태그:\s*$',
        ]
        
        for line in lines:
            line = line.strip()
            
            # 빈 줄 제거
            if not line:
                continue
                
            # 너무 짧은 줄 제거 (단어 1-2개)
            if len(line.split()) < 3:
                continue
                
            # 노이즈 패턴 제거
            is_noise = False
            for pattern in noise_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    is_noise = True
                    break
            
            if not is_noise:
                cleaned_lines.append(line)
        
        # 중복 제거 및 결합
        seen = set()
        final_lines = []
        for line in cleaned_lines:
            if line not in seen:
                seen.add(line)
                final_lines.append(line)
        
        return '\n'.join(final_lines)
    
    def extract_multiple_urls(self, urls: list, delay: float = 1.0) -> list:
        """여러 URL에서 콘텐츠 추출"""
        results = []
        
        for i, url in enumerate(urls):
            if i > 0:
                time.sleep(delay)  # 요청 간 지연
            
            logger.info(f"추출 중: {url} ({i+1}/{len(urls)})")
            result = self.extract_content(url)
            
            # 콘텐츠 품질 검증
            if result.get('status') == 'success':
                content = result.get('content', '')
                if len(content) < 200:
                    logger.warning(f"URL {url}: 콘텐츠가 너무 짧습니다 ({len(content)}자)")
                    result['status'] = 'warning'
                    result['message'] = f"콘텐츠가 너무 짧습니다: {len(content)}자"
                elif len(content.split()) < 50:
                    logger.warning(f"URL {url}: 단어 수가 너무 적습니다 ({len(content.split())}개)")
                    result['status'] = 'warning'
                    result['message'] = f"단어 수가 너무 적습니다: {len(content.split())}개"
            
            results.append(result)
        
        return results
