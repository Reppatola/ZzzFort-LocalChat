# ZzzFort-LocalChat

> **Local LLM chat for Windows with SSD-based memory, model switching, and zero Python dependencies.**

A minimal, self-contained local chat system built on a **custom-compiled `llama.cpp` server** for Windows (MinGW GCC 16.2.0). No Open WebUI, no Ollama service, no Python for the chat itself — just one `.exe`, one HTML file, and one manager script.

---

## ✨ Features

- **Self-compiled `llama-server.exe`** — built from llama.cpp source on MinGW GCC 16.2.0.
- **Model switching in one click** — pick a model from a dropdown.
- **SSD-based model loading** — mmap keeps weights on disk. A 14B model uses only ~0.7 GB of private RAM at 2K context.
- **q8_0 KV cache** — 40% less RAM than f16, no quality loss.
- **Zero dependencies for the chat** — `chat.html` is a single file.
- **Auto-discovery of models** — scans `models/` directory.
- **Fully offline** — no internet, no telemetry, no accounts.

---

## 🚀 Quick Start

**Requirements:** Windows 10/11, ~15 GB free disk space per model.

1. Clone the repository:
   ```cmd
   git clone https://github.com/Reppatola/ZzzFort-LocalChat.git

2. Set up the workspace:
	mkdir C:\ZzzFort
	mkdir C:\ZzzFort\diskllm\bin
	mkdir C:\ZzzFort\diskllm\models
3. Build llama-server.exe — see docs/BUILD.md.
4. Download models — see docs/MODELS.md.
5. Copy scripts:
	copy scripts\* C:\ZzzFort\
	copy web\chat.html C:\ZzzFort\
6. Run:
	C:\ZzzFort\start-chat.bat
The chat opens at http://127.0.0.1:8000/chat.html

📊 Measured Performance
On 32 GB RAM / RTX 4060 (CPU-only inference):

Model	Context	KV Type	Private RAM	Working Set	Decode (tok/s)
Qwen2.5-Coder 7B	2048	f16	0.38 GB	4.26 GB	4.78
Qwen2.5-Coder 14B	2048	f16	0.67 GB	8.39 GB	2.42
Qwen2.5-Coder 14B	8192	f16	1.81 GB	9.52 GB	2.42
Qwen2.5-Coder 14B	8192	q8_0	1.10 GB	8.83 GB	2.43
Key finding: private RAM does not scale with model size — only with KV cache size.

🏗️ Architecture

┌─────────────────┐         ┌──────────────────┐
│   chat.html     │ ──POST──│  model-manager   │
│   (browser)     │         │  (port 8090)     │
└────────┬────────┘         └────────┬─────────┘
         │                            │
         │                    ┌───────┴────────┐
         │                    │  taskkill +    │
         │                    │  llama-server  │
         │                    │  (port 8082)   │
         │                    └───────┬────────┘
         │                            │
         └───────/v1/chat/completions─┘

See docs/ARCHITECTURE.md for details.

ZzzFort-LocalChat/
├── README.md              ← this file (English)
├── README.ru.md           ← Russian version
├── LICENSE                ← MIT
├── .gitignore
├── docs/
│   ├── BUILD.md
│   ├── MODELS.md
│   ├── ARCHITECTURE.md
│   └── NOTES.md
├── scripts/
│   ├── start-chat.bat
│   ├── model-manager.py
│   └── backup.bat
├── web/
│   └── chat.html
└── patches/
    ├── httplib.cpp.diff
    └── httplib.h.diff

Not in the repository: models (.gguf), llama-server.exe, DLLs, venv, caches.

🛠️ Build from Source
The hardest part was compiling llama.cpp on Windows with MinGW GCC 16.2.0. We patched two files in cpp-httplib. Full recipe: docs/BUILD.md.

🧪 Tested Configurations
Component	Version
Windows	10.0.19045
MinGW-w64	GCC 16.2.0 (UCRT, POSIX threads)
llama.cpp	commit df18bee
Python	3.12 (for model-manager.py only)
Models	Qwen2.5-Coder 7B / 14B, Qwen3 8B
📜 License
MIT — free for everyone. See LICENSE.

🙏 Acknowledgements
llama.cpp

cpp-httplib

MinGW-w64 by WinLibs

The local LLM community