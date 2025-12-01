:: filepath: c:\Users\Lucca Zovedi\Desktop\hardware-diagnosis-cloud-app\run_app.bat
@echo off
setlocal

:: Tenta encontrar o python
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=python
    goto :Found
)

:: Tenta encontrar o py launcher
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=py
    goto :Found
)

echo Erro: Python nao foi encontrado.
echo Por favor, instale o Python em https://www.python.org/downloads/
echo Certifique-se de marcar a opcao "Add Python to PATH" durante a instalacao.
pause
exit /b 1

:Found
echo Python encontrado: %PYTHON_CMD%
echo Executando o aplicativo...
:: Substitua 'main.py' pelo seu arquivo de entrada principal, se for diferente
%PYTHON_CMD% app.py
pause