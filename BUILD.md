# Building llama-server.exe on Windows with MinGW GCC 16.2.0

This document describes how to compile `llama-server.exe` from `llama.cpp` source on Windows using MinGW-w64 (GCC 16.2.0, UCRT, POSIX threads).

**Why this is needed:** the official `llama.cpp` documentation recommends MSVC or Clang for Windows builds. MinGW is not officially supported, and the build fails on two files in `cpp-httplib`. This document records the exact patches and flags that made the build work.

**Result:** a 18 MB `llama-server.exe` that runs correctly on Windows 10/11 with the MinGW runtime DLLs.

---

## Prerequisites

### 1. MinGW-w64 (GCC 16.2.0)

Download from [winlibs.com](https://winlibs.com/).

Choose: **GCC 16.2.0 (with POSIX threads) + MinGW-w64 14.0.0 (UCRT) — release 2**, **Win64**, **Zip archive** (not 7z, not "without LLVM/Clang/LLDB").

Extract to: `C:\ZzzFort\mingw64\`

Expected structure:
C:\ZzzFort\mingw64
├── bin
│ ├── gcc.exe
│ ├── g++.exe
│ ├── mingw32-make.exe
│ └── ...
├── include
├── lib
└── libexec\

text

### 2. CMake

Install inside the project virtual environment:
```cmd
cd C:\ZzzFort
python -m venv venv
venv\Scripts\activate
pip install cmake
cmake --version
Expected: cmake version 4.x or newer.

3. Git
Required to clone llama.cpp. Windows Git works fine.

4. Python 3.12
Only needed for model-manager.py. Not required for the build itself.

Step 1: Clone llama.cpp
cmd
cd C:\ZzzFort
git clone --depth 1 https://github.com/ggml-org/llama.cpp.git src-llama
cd src-llama
The --depth 1 flag downloads only the latest commit (~37 MB instead of 200+ MB).

Step 2: Add MinGW to PATH
In the current CMD session:

cmd
set PATH=C:\ZzzFort\mingw64\bin;%PATH%
Verify:

cmd
where gcc
where g++
where mingw32-make
All three should point to C:\ZzzFort\mingw64\bin\.

Step 3: Patch cpp-httplib
The bundled cpp-httplib uses Windows 8+ APIs that MinGW does not expose by default, and it blocks builds targeting older Windows versions. Two patches are required.

3.1 Patch httplib.cpp
File: src-llama\vendor\cpp-httplib\httplib.cpp

Around line 1623, find:

cpp
::CreateFile2(wpath.c_str(), GENERIC_READ,
  FILE_SHARE_READ | FILE_SHARE_WRITE, OPEN_EXISTING, NULL);
Replace with:

cpp
::CreateFileW(wpath.c_str(), GENERIC_READ,
  FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING,
  FILE_ATTRIBUTE_READONLY, NULL);
Reason: CreateFile2 is a Windows 8+ API that MinGW does not declare. CreateFileW is the classic Win32 API, available everywhere.

3.2 Patch httplib.h
File: src-llama\vendor\cpp-httplib\httplib.h

Around line 16, find the block:

cpp
#if defined(_WIN32) && _WIN32_WINNT < 0x0A00
#error "cpp-httplib doesn't support Windows 8 or lower. Please use Windows 10 or later."
#endif
Comment it out or delete it entirely:

cpp
// #if defined(_WIN32) && _WIN32_WINNT < 0x0A00
// #error "cpp-httplib doesn't support Windows 8 or lower. Please use Windows 10 or later."
// #endif
Reason: MinGW GCC 16.2.0 defaults _WIN32_WINNT to Windows 7. The check blocks the build even though the code would compile fine.

Step 4: Configure with CMake
From C:\ZzzFort\src-llama:

cmd
cmake -B build -G "MinGW Makefiles" ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DGGML_CUDA=OFF ^
  -DLLAMA_CURL=OFF
Flags explained:

-G "MinGW Makefiles" — use MinGW, not Visual Studio.

-DCMAKE_BUILD_TYPE=Release — optimized build.

-DGGML_CUDA=OFF — no CUDA, pure CPU. Add -DGGML_CUDA=ON later if NVIDIA GPU available.

-DLLAMA_CURL=OFF — skip libcurl dependency (avoids extra DLLs).

Expected output ends with:

text
-- Configuring done
-- Generating done
-- Build files have been written to: C:/ZzzFort/src-llama/build
Step 5: Build
cmd
cmake --build build -j
The -j flag uses all CPU cores. Build time: 5-20 minutes depending on CPU.

Expected final lines:

text
[100%] Built target llama-server
[100%] Built target llama-cli
[100%] Built target llama-app
The binary is at: src-llama\build\bin\llama-server.exe (~18 MB).

Step 6: Copy binary and DLLs
6.1 Copy the executable
cmd
mkdir C:\ZzzFort\diskllm\bin
copy C:\ZzzFort\src-llama\build\bin\llama-server.exe C:\ZzzFort\diskllm\bin\
6.2 Copy direct dependencies
The four DLLs required directly by llama-server.exe:

cmd
copy C:\ZzzFort\mingw64\bin\libgcc_s_seh-1.dll C:\ZzzFort\diskllm\bin\
copy C:\ZzzFort\mingw64\bin\libstdc++-6.dll C:\ZzzFort\diskllm\bin\
copy C:\ZzzFort\mingw64\bin\libwinpthread-1.dll C:\ZzzFort\diskllm\bin\
copy C:\ZzzFort\mingw64\bin\libgomp-1.dll C:\ZzzFort\diskllm\bin\
6.3 Copy recursive dependencies
Important: the four DLLs above have their own dependencies. libgomp-1.dll requires libdl.dll, which requires others. The safest approach is to copy all DLLs from MinGW:

cmd
xcopy C:\ZzzFort\mingw64\bin\*.dll C:\ZzzFort\diskllm\bin\ /Y /I
This copies ~73 DLLs (~200 MB total). It guarantees that every recursive dependency is present.

Why this matters: if any transitive DLL is missing, Windows returns error 0xC0000135 (STATUS_DLL_NOT_FOUND) — and the process exits silently, without any dialog box. Diagnosing this is hard. Copying all DLLs avoids the problem entirely.

Step 7: Verify
cmd
cd C:\ZzzFort\diskllm\bin
llama-server.exe --help
Should print a long list of flags. If you see this output, the build is complete.

To check dependencies of the compiled binary:

cmd
C:\ZzzFort\mingw64\bin\objdump.exe -p llama-server.exe | findstr "DLL Name"
Expected output:

text
DLL Name: libgcc_s_seh-1.dll
DLL Name: libstdc++-6.dll
DLL Name: KERNEL32.dll
DLL Name: libwinpthread-1.dll
DLL Name: SHELL32.dll
DLL Name: WS2_32.dll
DLL Name: libgomp-1.dll
DLL Name: ADVAPI32.dll
DLL Name: api-ms-win-crt-*.dll (multiple)
Troubleshooting
Error: CreateFile2 has not been declared
The patch to httplib.cpp was not applied. Redo Step 3.1.

Error: cpp-httplib doesn't support Windows 8 or lower
The patch to httplib.h was not applied, or the file was not saved. Redo Step 3.2.

Error: #endif without #if
Too many or too few #endif lines after the patch. Compare your httplib.h with the recipe in Step 3.2 carefully.

Runtime error: 0xC0000135 (STATUS_DLL_NOT_FOUND)
One or more DLLs are missing. Run Step 6.3 — copy all DLLs from mingw64\bin\.

Runtime error: 0xC0000139 (STATUS_ENTRYPOINT_NOT_FOUND)
The DLLs were compiled by a different GCC version than the binary. This happens if the binary was downloaded from a release and the DLLs were taken from a separately installed MinGW. Solution: rebuild the binary from source with the same MinGW (Steps 4-5).

Build stops silently
Delete build\ and re-run Step 4:

cmd
rmdir /s /q build
CMake can't find MinGW
Run Step 2 explicitly in the same CMD session before running CMake.

Reproducibility notes
llama.cpp commit: df18bee (visible in the CMake output as ggml commit: df18bee)

GCC version: 16.2.0 (gcc --version)

CMake version: 4.x

Windows: 10.0.19045

To reproduce exactly, check out llama.cpp at commit df18bee. Later commits may change the code around the patches, requiring manual adjustments.

What about GPU?
The build above is CPU-only. To enable NVIDIA GPU (CUDA):

Install the CUDA Toolkit.

Configure with -DGGML_CUDA=ON instead of -DGGML_CUDA=OFF.

Rebuild.

Add CUDA DLLs to diskllm\bin\.

This typically improves decode speed by 10-15× (e.g., 2.4 tok/s → 25-30 tok/s for 14B Q4).

For AMD GPUs, use -DGGML_VULKAN=ON instead.

Summary of files to keep
After a successful build, back up these files — they are not in the git repository:

File	Size	Purpose
llama-server.exe	18 MB	Inference server
libgcc_s_seh-1.dll	~1 MB	GCC runtime
libstdc++-6.dll	~2.5 MB	C++ standard library
libwinpthread-1.dll	~70 KB	POSIX threads
libgomp-1.dll	~340 KB	OpenMP runtime
(all other MinGW DLLs)	~200 MB	Recursive dependencies
To rebuild from scratch, follow Steps 1-7 of this document.