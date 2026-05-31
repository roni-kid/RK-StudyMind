@echo off
setlocal EnableDelayedExpansion

:: ============================================================
::   RK StudyMind — GitHub Push Script
::   Version: v1.3
::   Repo: github.com/roni-kid/StudyMine
:: ============================================================

echo.
echo  =====================================================
echo    RK StudyMind v1.3 ^| GitHub Push
echo    Repo: github.com/roni-kid/StudyMine
echo  =====================================================
echo.

:: Move to project directory
cd /d "C:\Users\rocks\Documents\CLaude\StudyMind"
if errorlevel 1 (
    echo [ERROR] Could not find project directory.
    echo         Expected: C:\Users\rocks\Documents\CLaude\StudyMind
    pause
    exit /b 1
)

:: Show current git status so you know what's changing
echo  --- Current Git Status ---
git status --short
echo.

:: Check if there's anything to commit
git diff --quiet HEAD >nul 2>&1
if errorlevel 0 (
    git diff --cached --quiet >nul 2>&1
    if errorlevel 0 (
        git status --porcelain >nul 2>&1
    )
)

:: Stage all changes
echo  Staging all changes...
git add .
echo.

:: Check staged diff — if nothing staged, warn and exit
git diff --cached --quiet
if not errorlevel 1 (
    echo  [INFO] Nothing new to commit. Working tree is clean.
    echo.
    echo  If you expected changes, check that your files saved correctly.
    pause
    exit /b 0
)

:: Commit message — auto-default if left blank
set "default_msg=Update RK StudyMind v1.3"
set /p msg="  Commit message (Enter for default): "
if "!msg!"=="" set "msg=!default_msg!"

git commit -m "!msg!"
if errorlevel 1 (
    echo.
    echo  [ERROR] Commit failed. Check git output above.
    pause
    exit /b 1
)

:: Push — normal or force
echo.
set /p force_flag="  Force push? (f = force, Enter = normal): "
if /i "!force_flag!"=="f" (
    echo  Force pushing to origin/main...
    git push --force origin main
) else (
    echo  Pushing to origin/main...
    git push origin main
)

if errorlevel 1 (
    echo.
    echo  [ERROR] Push failed.
    echo  If remote has diverged, re-run and type 'f' to force push.
) else (
    echo.
    echo  =====================================================
    echo    Done! RK StudyMind v1.3 pushed to GitHub.
    echo  =====================================================
)

echo.
pause
endlocal
