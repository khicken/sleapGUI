@echo off
set VERSION=0.1.0

echo Downloading sleapGUI version %VERSION%...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/khicken/sleapGUI/releases/download/v%VERSION%/sleapgui-%VERSION%-py3-none-any.whl' -OutFile 'sleapgui-%VERSION%-py3-none-any.whl'"
echo Installing dependencies...
pip install PyQt5==5.12.3
echo Installing sleapGUI...
pip install --no-deps --force-reinstall sleapgui-%VERSION%-py3-none-any.whl
echo Installation complete!
echo To launch sleapGUI, use the command: sleapgui