import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import logging
from chromadb_manager import ChromaDBManager
from url_extractor import URLExtractor
from file_processor import FileProcessor
import tempfile
import shutil

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경변수 로드
load_dotenv()

# Flask 앱 초기화
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 최대 파일 크기
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

# 매니저 초기화
db_manager = ChromaDBManager()
url_extractor = URLExtractor()
file_processor = FileProcessor()

# 허용된 파일 확장자
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'pptx', 'ppt', 'xlsx', 'xls', 'txt', 'md', 'csv'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')


@app.route('/api/process_urls', methods=['POST'])
def process_urls():
    """URL 처리 API"""
    try:
        data = request.get_json()
        urls = data.get('urls', [])
        chunk_size = data.get('chunk_size', 1000)
        chunk_overlap = data.get('chunk_overlap', 200)
        
        if not urls:
            return jsonify({'status': 'error', 'message': 'URL이 제공되지 않았습니다.'}), 400
        
        # URL 유효성 검사
        valid_urls = []
        for url in urls:
            url = url.strip()
            if url and (url.startswith('http://') or url.startswith('https://')):
                valid_urls.append(url)
        
        if not valid_urls:
            return jsonify({'status': 'error', 'message': '유효한 URL이 없습니다.'}), 400
        
        # URL에서 콘텐츠 추출
        logger.info(f"Processing {len(valid_urls)} URLs")
        extracted_contents = url_extractor.extract_multiple_urls(valid_urls)
        
        # 성공적으로 추출된 콘텐츠만 필터링
        successful_contents = [
            content for content in extracted_contents 
            if content.get('status') == 'success'
        ]
        
        # ChromaDB에 저장
        if successful_contents:
            result = db_manager.add_documents(
                successful_contents, 
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            return jsonify({
                'status': 'success',
                'message': f'{len(successful_contents)}개 URL 처리 완료',
                'details': {
                    'processed': len(successful_contents),
                    'failed': len(extracted_contents) - len(successful_contents),
                    'added_chunks': result['added_chunks'],
                    'skipped_urls': result['skipped_urls']
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '처리할 수 있는 URL이 없습니다.'
            }), 400
            
    except Exception as e:
        logger.error(f"URL 처리 오류: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/upload_files', methods=['POST'])
def upload_files():
    """파일 업로드 및 처리 API"""
    try:
        if 'files' not in request.files:
            return jsonify({'status': 'error', 'message': '파일이 제공되지 않았습니다.'}), 400
        
        files = request.files.getlist('files')
        chunk_size = int(request.form.get('chunk_size', 1000))
        chunk_overlap = int(request.form.get('chunk_overlap', 200))
        
        processed_contents = []
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                try:
                    # 파일 저장
                    file.save(filepath)
                    
                    # 파일 처리
                    content = file_processor.process_file(filepath, filename)
                    if content.get('status') == 'success':
                        processed_contents.append(content)
                    
                finally:
                    # 임시 파일 삭제
                    if os.path.exists(filepath):
                        os.remove(filepath)
        
        # ChromaDB에 저장
        if processed_contents:
            result = db_manager.add_documents(
                processed_contents,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            return jsonify({
                'status': 'success',
                'message': f'{len(processed_contents)}개 파일 처리 완료',
                'details': {
                    'processed': len(processed_contents),
                    'added_chunks': result['added_chunks']
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '처리할 수 있는 파일이 없습니다.'
            }), 400
            
    except Exception as e:
        logger.error(f"파일 처리 오류: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/search', methods=['POST'])
def search():
    """유사도 검색 API"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        n_results = data.get('n_results', 5)
        min_similarity = data.get('min_similarity', 0.3)  # 기본 최소 유사도 30%
        
        if not query:
            return jsonify({'status': 'error', 'message': '검색어가 제공되지 않았습니다.'}), 400
        
        # 검색 수행
        results = db_manager.search(query, n_results, min_similarity)
        
        return jsonify({
            'status': 'success',
            'query': query,
            'total_results': len(results),
            'min_similarity_threshold': min_similarity,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"검색 오류: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/clear_database', methods=['POST'])
def clear_database():
    """데이터베이스 초기화 API"""
    try:
        result = db_manager.clear_database()
        return jsonify(result)
    except Exception as e:
        logger.error(f"DB 초기화 오류: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500




@app.route('/api/stats', methods=['GET'])
def get_stats():
    """데이터베이스 통계 API"""
    try:
        stats = db_manager.get_stats()
        return jsonify({'status': 'success', 'stats': stats})
    except Exception as e:
        logger.error(f"통계 조회 오류: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/supported_formats', methods=['GET'])
def get_supported_formats():
    """지원하는 파일 형식 조회 API"""
    formats = file_processor.get_supported_formats()
    return jsonify({'formats': formats})


@app.route('/api/debug_search', methods=['POST'])
def debug_search():
    """디버깅용 검색 API - 상세한 로깅 제공"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({'status': 'error', 'message': '검색어가 제공되지 않았습니다.'}), 400
        
        # 데이터베이스 상태 확인
        stats = db_manager.get_stats()
        
        # 이상한 결과를 위한 샘플 검색
        results = db_manager.search(query, n_results=3, min_similarity=0.0)  # 모든 결과 표시
        
        # 원본 ChromaDB 결과도 가져오기
        query_embedding = db_manager._get_embedding(query)
        raw_results = db_manager.collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            include=['documents', 'metadatas', 'distances']
        )
        
        return jsonify({
            'status': 'success',
            'query': query,
            'database_stats': stats,
            'query_embedding_dimension': len(query_embedding),
            'query_embedding_sample': query_embedding[:5],  # 처음 5개 값
            'raw_distances': raw_results['distances'][0] if raw_results['distances'][0] else [],
            'processed_results': results,
            'debug_info': {
                'total_documents_in_db': db_manager.collection.count(),
                'collection_metadata': db_manager.collection.metadata if hasattr(db_manager.collection, 'metadata') else 'N/A'
            }
        })
        
    except Exception as e:
        logger.error(f"디버깅 검색 오류: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    # 업로드 폴더 생성
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
