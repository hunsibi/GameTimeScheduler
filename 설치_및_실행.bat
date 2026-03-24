@echo off
chcp 65001 >nul
echo ============================================
echo  게임 타이머 설치 및 실행 스크립트
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python을 찾을 수 없습니다. 환경변수 PATH 설정을 확인해주세요.
    echo Python 3.10 이상을 설치한 뒤 다시 실행하세요.
    echo  -^> https://www.python.org/downloads/
    pause
    exit /b 1
)

set PYTHON=python
set PYTHONW=pythonw

:: pythonw 확인
where pythonw >nul 2>&1
if errorlevel 1 (
    set PYTHONW=python
)

echo Python 환경변수 인식 성공
echo.
echo 패키지 설치 중...
%PYTHON% -m pip install psutil pystray Pillow plyer --upgrade
echo.
echo 설치 완료! 백그라운드에서 프로그램을 시작합니다...
echo.
start "" %PYTHONW% "%~dp0main.py"
echo 시스템 트레이(우측 하단)에 게임 타이머 아이콘이 생성되었습니다.
echo --------------------------------------------
echo 이제 이 검은색 창(CMD)을 닫으셔도 트레이에서 계속 실행됩니다!
echo --------------------------------------------
timeout /t 5
