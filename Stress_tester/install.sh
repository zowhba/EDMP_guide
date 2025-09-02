#!/bin/bash

# Stress Tester App 설치 스크립트
echo "🚀 Stress Tester App 설치를 시작합니다..."

# pip 업그레이드
echo "📦 pip 업그레이드 중..."
python -m pip install --upgrade pip

# 가상환경 확인
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ 가상환경이 활성화되어 있습니다: $VIRTUAL_ENV"
else
    echo "⚠️  가상환경이 활성화되지 않았습니다. 가상환경 사용을 권장합니다."
fi

# 의존성 설치
echo "📥 필요한 패키지들을 설치합니다..."
pip install -r requirements.txt

# 설치 확인
echo "🔍 설치된 패키지 확인:"
pip list | grep -E "(streamlit|httpx|pandas)"

echo ""
echo "✅ 설치가 완료되었습니다!"
echo ""
echo "🚀 앱을 실행하려면 다음 명령어를 사용하세요:"
echo "   streamlit run app.py --server.port 8501"
echo ""
echo "   또는"
echo ""
echo "   python -m streamlit run app.py --server.port 8501"
