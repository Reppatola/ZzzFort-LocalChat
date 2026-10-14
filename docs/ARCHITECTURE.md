# Architecture

This document describes the design of ZzzFort-LocalChat — components, data flow, and the reasoning behind key decisions.

---

## Overview

ZzzFort-LocalChat is a three-process system:

1. **`llama-server.exe`** — inference engine (compiled from llama.cpp, port 8082).
2. **`model-manager.py`** — HTTP service that controls the inference engine (port 8090).
3. **`http.server`** — static file server that delivers `chat.html` to the browser (port 8000).

The browser (`chat.html`) talks to both the manager (for model control) and the inference engine (for chat completions).

---

## Data Flow

### Model Switching
chat.html
│
│ POST /switch {"model": "qwen3-8b"}
▼
model-manager.py (port 8090)
│
│ taskkill /F /IM llama-server.exe
▼
(process killed)
│
│ subprocess.Popen(llama-server.exe -m <path> --port 8082 ...)
▼
llama-server.exe (port 8082, loading...)
│
│ poll GET /v1/models until 200 OK
▼
model-manager.py
│
│ {"status": "ok"}
▼
chat.html (updates status indicator)

text

### Chat Completion
chat.html
│
│ POST /v1/chat/completions (stream: true)
▼
llama-server.exe (port 8082)
│
│ Server-Sent Events (SSE) stream
▼
chat.html (renders tokens incrementally)

text

---

## Why Three Processes?

### Why not one?

A single-process design would require the chat UI to be served by the same server that handles inference. That is exactly what Open WebUI does — and it adds 2 GB of Python dependencies, requires a login, caches model lists, and occasionally fails to detect models correctly.

By separating concerns:

- **Inference** stays minimal — pure C++, one binary, no dependencies beyond DLLs.
- **Model control** is a small Python script (~150 lines) that can be rewritten or replaced.
- **Static files** are served by Python's built-in `http.server` — zero setup.

Each component can be debugged in isolation. If the chat shows "Manager unavailable", the issue is in port 8090. If "Model not loaded", it's port 8082. If "Cannot open page", it's port 8000.

### Why not use Ollama?

Ollama is a full-featured LLM server, but:

1. It does not expose `-ctk q8_0 -ctv q8_0` directly — quantization of KV cache requires a custom Modelfile.
2. It has no concept of `--alias` for short model names in a chat selector.
3. On Windows, it does not always report correct VRAM / RAM usage on APU systems.
4. It runs as a background service, which complicates clean startup/shutdown for a self-contained project.

`llama-server.exe` compiled from source gives full control over every flag.

### Why a separate model manager?

The chat client runs in a browser — JavaScript **cannot kill or spawn processes**. Switching models requires OS-level operations (taskkill, subprocess). Therefore a local HTTP service is the bridge: the browser sends a request, the service performs the system operations, and returns a status.

This also allows the manager to be tested independently:
curl http://127.0.0.1:8090/status
curl http://127.0.0.1:8090/models
curl -X POST http://127.0.0.1:8090/switch -d '{"model": "qwen3-8b"}'

text

---

## Components

### `llama-server.exe`

Compiled from `llama.cpp` on MinGW GCC 16.2.0. See [BUILD.md](BUILD.md).

**Startup arguments used by the manager:**
llama-server.exe
-m <path to .gguf>
-c 8192
-ctk q8_0
-ctv q8_0
--alias <short name>
--port 8082
--host 127.0.0.1

text

**Why these flags:**

| Flag | Reason |
|------|--------|
| `-c 8192` | 8K context is enough for chat and most code tasks; 2K is too small, 32K costs RAM. |
| `-ctk q8_0 -ctv q8_0` | KV cache in 8-bit quantization. 40% less RAM than f16. No measurable quality loss. |
| `--alias` | Short name displayed in chat selector instead of the full file path. |
| `--host 127.0.0.1` | Listen only on localhost. No external network access. |
| `--port 8082` | Fixed port for the manager to know where to find it. |

**Not used:**

- `--jinja` — disabled by default. Enabling it activates the model's native Jinja template, which for coder models triggers tool-calling. For chat, plain OpenAI-compatible format works better.
- `-ngl` — no GPU offload in this CPU-only build.

### `model-manager.py`

**~150 lines of Python.** Uses only the standard library plus `requests`.

**Endpoints:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/models` | List available models (scans `models\` directory) |
| GET | `/status` | Current running state: `{"running": bool, "active": str, "port": int}` |
| POST | `/switch` | Switch to a different model. Body: `{"model": "<name>"}` |

**Key functions:**

- `list_models()` — scans `C:\ZzzFort\diskllm\models\` for subdirectories containing `.gguf`.
- `kill_llama_server()` — runs `taskkill /F /IM llama-server.exe`, waits for port 8082 to free.
- `start_llama_server(path, alias)` — spawns the process detached (`DETACHED_PROCESS | CREATE_NO_WINDOW`).
- `wait_for_server(timeout)` — polls `/v1/models` until 200 OK, up to 90 seconds.
- `switch_model(name)` — orchestrates kill → start → wait.

**Startup behavior:**

1. On launch, checks if `llama-server.exe` is already running.
2. If not, starts the default model (`qwen3-8b`).
3. Waits for it to load.
4. Begins listening on port 8090.

**Shutdown:**

`Ctrl+C` — the manager exits, but does **not** kill `llama-server.exe`. The server keeps running in the background. To fully stop, use `taskkill /F /IM llama-server.exe`.

### `chat.html`

**Single file.** No build step, no dependencies, no npm. Opens directly in any browser.

**Features:**

- Model selector (populated from `/models`).
- Streaming responses via Server-Sent Events.
- Chat history persisted in `localStorage`.
- System messages for switch events ("Switching to...", "Model loaded").
- Auto-detection of active model via `/status`.

**Why it must be served over HTTP (not `file://`):**

Browsers enforce the **same-origin policy**. A page loaded from `file://` cannot make cross-origin HTTP requests to `http://127.0.0.1:8090` — even with `Access-Control-Allow-Origin: *`, most browsers block it.

Serving `chat.html` from `http://127.0.0.1:8000` resolves this: both the page and the API are HTTP-origin, and CORS headers on the manager allow the requests through.

**CORS headers on the manager:**
```python
self.send_header("Access-Control-Allow-Origin", "*")
self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
self.send_header("Access-Control-Allow-Headers", "Content-Type")
Port Allocation
Port	Service	Protocol
8000	python -m http.server	HTTP (static files)
8082	llama-server.exe	HTTP (OpenAI-compatible API)
8090	model-manager.py	HTTP (control)
Why these specific numbers:

8000 is the default http.server port, memorable and unlikely to conflict.

8082 is in the standard 8080-range but avoids the common 8080 conflict.

8090 is adjacent to 8082, easy to remember, rarely used by other software.

Conflict handling: start-chat.bat checks each port before launching. If a port is already in use, that process is skipped (assuming the user already started it).

Memory Model
How mmap keeps RAM low
When llama-server loads a model, it does not copy weights into RAM. Instead, it mmaps the .gguf file. The OS treats the file as pageable memory:

Private RAM — only the active inference state (KV cache, buffers, tensors in use). This is what shows in Task Manager as "Private Working Set".

Working Set — includes mmap pages of the model file, but these are evictable. If another process needs RAM, Windows drops these pages without writing them anywhere (they can be re-read from disk).

Practical effect: a 14B model at 8K context shows 1.1 GB private RAM with q8_0 KV cache, while the model file itself is 9 GB. The remaining ~8 GB are evictable mmap pages.

KV cache growth
KV cache size is proportional to:

text
KV bytes ≈ 2 × layers × heads × head_dim × context × dtype_bytes
For Qwen2.5-Coder-14B at 8K context:

f16 KV cache: ~1.14 GB

q8_0 KV cache: ~0.57 GB

Formula for planning:

f16 KV: ~0.14 MB per token for 14B models

q8_0 KV: ~0.07 MB per token

Context size × KV-per-token = KV RAM cost. Plan accordingly.

Why KV cannot live on disk (without patches)
The KV cache is read and written on every generated token. Disk latency (~50 µs for NVMe) is orders of magnitude slower than RAM latency (~50 ns). Standard llama.cpp keeps KV in RAM.

Projects like DiskLLM patch llama.cpp to mmap the KV cache to an SSD file. This works because SSD access is faster than recomputing attention — but the tradeoff is slower decoding.

Not implemented in this project yet. For contexts up to 32K, RAM-based KV is fine on a 32 GB machine. Beyond 64K, SSD-based KV becomes useful.

Switching Time Breakdown
When switching from qwen2.5-coder-14b to qwen3-8b:

Phase	Duration
Kill old process	< 1 sec
Free VRAM (not applicable in CPU build)	—
Free RAM (OS reclaims mmap pages)	1-3 sec
Read new model from disk (warm cache)	3-10 sec
Read new model from disk (cold cache)	20-40 sec
Initialize tensors, allocate KV cache	2-5 sec
Start HTTP listener	< 1 sec
Total (warm)	~10-20 sec
Total (cold)	~30-60 sec
Warm cache = the model file was read recently and is still in the OS file cache.
Cold cache = the file has not been touched since last reboot, or cache was cleared.

Extending the System
Adding a new model
Place .gguf in C:\ZzzFort\diskllm\models\<name>\.

Restart model-manager.py (or it picks up automatically on next /models call).

Model appears in the chat selector.

No code changes.

Changing the port
Edit model-manager.py:

python
LLAMA_PORT = 8082   # change to 8083 if needed
And in chat.html:

javascript
const LLAMA_PORT = 8082;
Both must match.

Adding a GPU build
Rebuild llama-server.exe with -DGGML_CUDA=ON.

Add -ngl 99 (or -ngl all) to the start_llama_server() arguments.

Ensure CUDA DLLs are in diskllm\bin\.

The rest of the architecture is unchanged.

Replacing the manager
Any process that exposes /models, /status, and /switch on port 8090 can replace model-manager.py. The chat treats it as a black box.

Replacing the chat
Any client that speaks OpenAI-compatible /v1/chat/completions can replace chat.html. The server is fully OpenAI-compatible for chat completions.

What This Project Is Not
Not a training framework. Inference only.

Not a multi-user server. Single user, localhost only.

Not production-grade. No auth, no rate limits, no logging.

Not cross-platform. Windows-only. Built for MinGW GCC 16.2.0.

It is a reference implementation of a minimal local LLM chat, built to be understood and modified.