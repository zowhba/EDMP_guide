#!/usr/bin/env python3
"""
Multi-Crypto Wallet Web Application 실행 스크립트
Bitcoin & BitMobick 지원
"""

import subprocess
import sys
import os

def check_requirements():
    """필요한 패키지가 설치되어 있는지 확인"""
    required_packages = [
        'streamlit',
        'pandas', 
        'requests',
        'ecdsa',
        'base58',
        'qrcode'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ 다음 패키지들이 설치되지 않았습니다:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 다음 명령어로 설치하세요:")
        print("   pip install -r requirements.txt")
        return False
    
    return True

def run_app():
    """Streamlit 애플리케이션 실행"""
    print("🪙 Multi-Crypto Wallet Web Application 시작 중...")
    print("📊 지원 코인: Bitcoin (BTC), BitMobick (BTMK)")
    print("🌐 웹 브라우저에서 http://localhost:8501 로 접속하세요.")
    print("🛑 종료하려면 Ctrl+C를 누르세요.")
    print("-" * 60)
    
    try:
        subprocess.run([
            sys.executable, 
            "-m", 
            "streamlit", 
            "run", 
            "bitcoin_app.py",
            "--server.headless=true"
        ])
    except KeyboardInterrupt:
        print("\n\n👋 Multi-Crypto Wallet 애플리케이션이 종료되었습니다.")
    except Exception as e:
        print(f"\n❌ 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🪙  Multi-Crypto Wallet Web Application")
    print("    Bitcoin & BitMobick 지원")
    print("=" * 60)
    
    # 현재 디렉토리 확인
    if not os.path.exists("bitcoin_app.py"):
        print("❌ bitcoin_app.py 파일을 찾을 수 없습니다.")
        print("💡 etc 폴더에서 이 스크립트를 실행해주세요.")
        sys.exit(1)
    
    # 필요한 패키지 확인
    if not check_requirements():
        sys.exit(1)
    
    print("✅ 모든 패키지가 설치되어 있습니다.")
    print()
    
    # 애플리케이션 실행
    run_app()
