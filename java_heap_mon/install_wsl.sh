#!/bin/bash

# Java 힙 덤프 분석기 설치 스크립트 (Windows WSL 환경)
echo "☕ Java 힙 덤프 분석기 설치를 시작합니다 (Windows WSL 환경)..."

# 현재 디렉토리 확인
echo "📁 현재 디렉토리: $(pwd)"

# Java 버전 확인
echo "🐍 Java 버전 확인:"
if command -v java &> /dev/null; then
    java -version
else
    echo "❌ Java가 설치되지 않았습니다."
    echo "다음 명령어로 Java를 설치하세요:"
    echo "sudo apt update && sudo apt install -y openjdk-11-jdk"
    exit 1
fi

# Python 버전 확인
echo "🐍 Python 버전 확인:"
python3 --version

# pip 업그레이드
echo "📦 pip 업그레이드 중..."
python3 -m pip install --upgrade pip

# 가상환경 확인 및 생성
if [ -d ".venv" ]; then
    echo "✅ 기존 .venv 가상환경을 사용합니다."
    source .venv/bin/activate
else
    echo "📦 새로운 .venv 가상환경을 생성합니다..."
    python3 -m venv .venv
    source .venv/bin/activate
fi

# 가상환경 활성화 확인
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ 가상환경이 활성화되어 있습니다: $VIRTUAL_ENV"
else
    echo "❌ 가상환경 활성화에 실패했습니다."
    exit 1
fi

# 의존성 설치 (Windows WSL 환경 최적화)
echo "📥 필요한 패키지들을 설치합니다 (Windows WSL 환경 최적화)..."
pip install -r requirements.txt

# 설치 확인
echo "🔍 설치된 패키지 확인:"
pip list | grep -E "(streamlit|pandas|plotly|psutil)"

echo ""
echo "✅ 설치가 완료되었습니다!"
echo ""
echo "🚀 애플리케이션을 실행하려면 다음 명령어를 사용하세요:"
echo ""
echo "📊 실시간 모니터링:"
echo "   streamlit run app.py --server.port 8501"
echo ""
echo "🔍 힙 덤프 분석기:"
echo "   streamlit run heap_dump_analyzer.py --server.port 8502"
echo ""
echo "🌐 브라우저에서 접속:"
echo "   - 실시간 모니터링: http://localhost:8501"
echo "   - 힙 덤프 분석기: http://localhost:8502"
echo ""
echo "📝 참고사항:"
echo "   - Windows WSL 환경에서 실행됩니다"
echo "   - Java JDK 11+ 버전이 필요합니다"
echo "   - 가상환경 활성화: source .venv/bin/activate"
