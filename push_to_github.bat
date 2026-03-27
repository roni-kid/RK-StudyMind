@echo off
echo ========================================
echo   RK StudyMind - GitHub Push Script
echo ========================================
echo.
cd /d C:\Users\rocks\Documents\CLaude\StudyMind

echo Adding all changes...
git add .

echo.
set /p msg="Enter commit message: "
git commit -m "%msg%"

echo.
echo Pushing to GitHub...
git push origin main

echo.
echo ========================================
echo   Done! Check above for any errors.
echo ========================================
pause
