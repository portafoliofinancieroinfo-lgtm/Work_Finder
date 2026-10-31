@echo off
rem Abre el CRM de Finder Work en http://localhost:8765. Cierra esta ventana para apagarlo.
cd /d "%~dp0"
title Finder Work - CRM
python "Programa CRM\abrir_pagina.py"
if errorlevel 1 pause
