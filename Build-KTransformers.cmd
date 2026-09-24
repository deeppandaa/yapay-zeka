@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" amd64
if errorlevel 1 exit /b %errorlevel%
set "WindowsSdkDir=C:\Program Files (x86)\Windows Kits\10\"
set "WindowsSDKVersion=10.0.26100.0\"
set "PATH=%WindowsSdkDir%bin\10.0.26100.0\x64;%PATH%"
set "INCLUDE=%WindowsSdkDir%Include\10.0.26100.0\ucrt;%WindowsSdkDir%Include\10.0.26100.0\shared;%WindowsSdkDir%Include\10.0.26100.0\um;%WindowsSdkDir%Include\10.0.26100.0\winrt;%INCLUDE%"
set "LIB=%WindowsSdkDir%Lib\10.0.26100.0\ucrt\x64;%WindowsSdkDir%Lib\10.0.26100.0\um\x64;%LIB%"
set "LIB=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\lib\x64;%LIB%"
set "PKG_CONFIG_PATH=D:\DeepPanda-Proje\Yapay Zeka\AI-Runtimes\hwloc-win64\pkgconfig"
set "PATH=C:\Users\emre\AppData\Local\Microsoft\WinGet\Packages\bloodrock.pkg-config-lite_Microsoft.Winget.Source_8wekyb3d8bbwe\pkg-config-lite-0.28-1\bin;%PATH%"
set "PATH=D:\DeepPanda-Proje\Yapay Zeka\AI-Runtimes\hwloc-win64\hwloc-win64-build-2.14.0\bin;%PATH%"
cd /d "D:\DeepPanda-Proje\Yapay Zeka\AI-Runtimes\ktransformers\kt-kernel"
"C:\Users\emre\Desktop\DeepPanda-Proje\Yapay Zeka\.venv\Scripts\python.exe" -m pip install -e . --no-deps
exit /b %errorlevel%
