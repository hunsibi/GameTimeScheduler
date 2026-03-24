@echo off
chcp 65001 > nul
echo ==========================================
echo  게임 타이머 - PyInstaller EXE 빌드
echo ==========================================
echo.

:: 현재 디렉터리를 스크립트 위치로 설정
cd /d "%~dp0"

echo [1/3] pyinstaller 설치 확인...
pip install pyinstaller --quiet
if errorlevel 1 (
    echo [오류] pip 실행 실패. Python 환경을 확인하세요.
    pause
    exit /b 1
)

echo [2/3] 의존 패키지 설치 확인...
pip install psutil pystray Pillow plyer --quiet

echo [3/3] EXE 빌드 시작...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "GameTimeScheduler" ^
    --hidden-import "pystray._win32" ^
    --hidden-import "plyer.platforms.win.notification" ^
    --hidden-import "winreg" ^
    --collect-all "pystray" ^
    --collect-all "plyer" ^
    main.py

if errorlevel 1 (
    echo.
    echo [오류] 빌드 실패! 위 오류 메시지를 확인하세요.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  빌드 완료!
echo  dist 폴더 안의 GameTimeScheduler.exe 를 실행하세요.
echo ==========================================
echo.

:: dist 폴더 열기
explorer dist

pause
