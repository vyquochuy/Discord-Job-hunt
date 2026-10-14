@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

set "TARGET_DIR=%~dp0"
if not "%~1"=="" set "TARGET_DIR=%~1"

if "%TARGET_DIR:~-1%"=="\" set "TARGET_DIR=%TARGET_DIR:~0,-1%"

echo ======================================================
echo    LaTeX Build Artifacts Cleaner
echo    Target: %TARGET_DIR%
echo ======================================================

set /a TOTAL_COUNT=0
set EXT_LIST=aux log out fls fdb_latexmk synctex synctex.gz toc lof lot bbl blg bcf run.xml nav snm vrb idx ilg ind xdv

call :clean_folder "%TARGET_DIR%"

if exist "%TARGET_DIR%\context" (
    if /i not "%TARGET_DIR%"=="%TARGET_DIR%\context" (
        echo.
        echo Checking subfolder: %TARGET_DIR%\context
        call :clean_folder "%TARGET_DIR%\context"
    )
)

echo ------------------------------------------------------
if !TOTAL_COUNT! EQU 0 (
    echo Hoan tat: Khong co file build tam nao can don dep.
) else (
    echo Hoan tat: Da xoa thanh cong !TOTAL_COUNT! file build tam cua LaTeX.
)
echo ======================================================
goto :end

:clean_folder
set "FOLDER=%~1"
for %%e in (%EXT_LIST%) do (
    for %%f in ("!FOLDER!\*.%%e") do (
        if exist "%%~ff" (
            echo   [-] Xoa: %%~nxf
            del /f /q "%%~ff" >nul 2>&1
            set /a TOTAL_COUNT+=1
        )
    )
)
exit /b 0

:end
endlocal
