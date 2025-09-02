#!/bin/bash

# Stress Tester App 단계별 설치 스크립트
echo "🚀 Stress Tester App 단계별 설치를 시작합니다..."

# 1단계: pip 업그레이드
echo "📦 1단계: pip 업그레이드 중..."
python -m pip install --upgrade pip

# 2단계: 가상환경 확인
echo "🔍 2단계: 가상환경 확인..."
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ 가상환경이 활성화되어 있습니다: $VIRTUAL_ENV"
else
    echo "⚠️  가상환경이 활성화되지 않았습니다."
fi

# 3단계: 개별 패키지 설치
echo "📥 3단계: 개별 패키지 설치 중..."

echo "   - streamlit 설치..."
pip install streamlit>=0.75.0

echo "   - httpx 설치..."
pip install httpx>=0.22.0

echo "   - pandas 설치..."
pip install pandas>=1.1.0

# 4단계: 설치 확인
echo "🔍 4단계: 설치된 패키지 확인..."
echo ""
echo "설치된 패키지 목록:"
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
