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
    pause
    exit /b 1
)

:: Show current git status
echo  --- Current Git Status ---
git status --short
echo.

:: Stage all changes
echo  Staging all changes...
git add .
echo.

:: Check if anything is staged after git add
git diff --cached --quiet
if not errorlevel 1 (
    echo  Nothing to commit. Working tree is clean.
    echo  Type p to push anyway, or press Enter to exit.
    set /p push_anyway="  Choice: "
    if /i "!push_anyway!"=="p" goto :do_push
    pause
    exit /b 0
)

:: Commit
set "default_msg=Update RK StudyMind v1.3"
set /p msg="  Commit message (Enter for default): "
if "!msg!"=="" set "msg=!default_msg!"

git commit -m "!msg!"
if errorlevel 1 (
    echo.
    echo  [ERROR] Commit failed.
    pause
    exit /b 1
)

:do_push
echo.
echo  Type f for force push, or press Enter for normal push.
set /p force_flag="  Choice: "
if /i "!force_flag!"=="f" (
    echo  Force pushing to origin/main...
    git push --force origin main
) else (
    echo  Pushing to origin/main...
    git push origin main
)

if errorlevel 1 (
    echo.
    echo  [ERROR] Push failed. Re-run and choose f to force push.
) else (
    echo.
    echo  =====================================================
    echo    Done! RK StudyMind v1.3 pushed to GitHub.
    echo  =====================================================
)

echo.
pause
endlocal
