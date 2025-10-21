#!/bin/bash

# Stress Tester App 설치 스크립트 (CentOS 7 전용)
echo "🚀 Stress Tester App 설치를 시작합니다 (CentOS 7 환경)..."

# Python 버전 확인
echo "🐍 Python 버전 확인:"
python3 --version

# pip 업그레이드
echo "📦 pip 업그레이드 중..."
python3 -m pip install --upgrade pip

# 가상환경 확인
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ 가상환경이 활성화되어 있습니다: $VIRTUAL_ENV"
else
    echo "⚠️  가상환경이 활성화되지 않았습니다. 가상환경 사용을 권장합니다."
    echo "   가상환경 생성: python3 -m venv venv"
    echo "   가상환경 활성화: source venv/bin/activate"
fi

# CentOS 7에서 필요한 시스템 패키지 설치 (선택사항)
echo "🔧 시스템 패키지 확인 중..."
if command -v yum &> /dev/null; then
    echo "   CentOS 7에서 다음 패키지들이 필요할 수 있습니다:"
    echo "   sudo yum install -y python3-devel gcc"
fi

# 의존성 설치 (CentOS 7 호환 버전)
echo "📥 필요한 패키지들을 설치합니다 (CentOS 7 호환)..."
python3 -m pip install -r requirements.txt

# 설치 확인
echo "🔍 설치된 패키지 확인:"
python3 -m pip list | grep -E "(streamlit|httpx|pandas)"

echo ""
echo "✅ 설치가 완료되었습니다!"
echo ""
echo "🚀 앱을 실행하려면 다음 명령어를 사용하세요:"
echo "   python3 -m streamlit run app.py --server.port 8501"
echo ""
echo "   또는"
echo ""
echo "   streamlit run app.py --server.port 8501"
echo ""
echo "📝 참고사항:"
echo "   - CentOS 7에서는 python3 명령어를 사용하세요"
echo "   - 방화벽 설정이 필요할 수 있습니다: sudo firewall-cmd --add-port=8501/tcp"
