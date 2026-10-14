# Models — Downloading, Linking, and Managing

This document describes how to obtain GGUF models for ZzzFort-LocalChat, how to link them from an existing Ollama installation, and how the model manager discovers and switches between them.

---

## Requirements

- ~15 GB free disk space per 14B model (Q4_K_M quantization)
- ~6 GB per 7B model
- ~5.5 GB per 8B model

Models live in: `C:\ZzzFort\diskllm\models\<model-name>\<model-name>-ollama.gguf`

Each model is a single `.gguf` file in its own subdirectory. The subdirectory name is the model's identifier in the chat selector.

---

## Option A: Link from an Existing Ollama Installation

If you already use [Ollama](https://ollama.com/), models are already downloaded as blobs in `%USERPROFILE%\.ollama\models\blobs\`. DiskLLM can link them without re-downloading.

### 1. Install DiskLLM

```cmd
cd C:\ZzzFort
python -m venv venv
venv\Scripts\activate
pip install diskllm
2. Set DISKLLM_HOME (critical)
By default, DiskLLM writes to %USERPROFILE%\.diskllm\ — outside our project. To keep everything inside C:\ZzzFort, set the environment variable before running any diskllm command:

cmd
set DISKLLM_HOME=C:\ZzzFort\diskllm
Important: set works only in the current CMD session. Every new terminal needs this command again. To make it permanent:

cmd
setx DISKLLM_HOME "C:\ZzzFort\diskllm"
setx writes to the user registry. All new terminals will see it. The current terminal will not — close and reopen.

3. Verify that Ollama has the model
cmd
ollama list
Example output:

text
NAME                       ID              SIZE      MODIFIED
qwen2.5-coder:14b          9ec8897f747e    9.0 GB    2 days ago
qwen3:8b                   a3de86cd1c13    5.2 GB    1 day ago
4. Link the model
cmd
diskllm pull qwen2.5-coder:14b
Expected output:

text
pulling manifest
...
linked ollama blob sha256:... to C:\ZzzFort\diskllm\models\qwen2.5-coder-14b\qwen2.5-coder-14b-ollama.gguf
saved qwen2.5-coder:14b to C:\ZzzFort\diskllm\models\qwen2.5-coder-14b\qwen2.5-coder-14b-ollama.gguf
No re-download. DiskLLM creates a hard link or copies the existing blob. Disk space is not doubled if the filesystem supports hard links.

5. If DiskLLM writes to the wrong path
Symptom: after diskllm pull, the model appears in C:\Users\<you>\.diskllm\models\ instead of C:\ZzzFort\diskllm\models\.

Cause: DISKLLM_HOME was not set in that terminal session.

Fix: move the directory manually:

cmd
move "C:\Users\<you>\.diskllm\models\<model-name>" "C:\ZzzFort\diskllm\models\<model-name>"
Then, for future pulls, always set DISKLLM_HOME (or use setx once and reopen the terminal).

Option B: Manual Download
If Ollama is not installed, download GGUF files directly from HuggingFace.

Recommended sources:

Qwen2.5-Coder GGUF — 7B, 14B, 32B

Qwen3 GGUF — 8B, 14B, 30B

bartowski's GGUFs — most popular models, high-quality quantization

Recommended quantization: Q4_K_M. It offers the best balance of quality, size, and speed. Use Q5_K_M for slightly better quality at ~20% larger file size.

Example: download Qwen2.5-Coder-14B-Instruct-Q4_K_M.gguf

Download from HuggingFace to your Downloads folder.

Create the model directory:

cmd
mkdir C:\ZzzFort\diskllm\models\qwen2.5-coder-14b
Move the file with a standardized name:

cmd
move "%USERPROFILE%\Downloads\Qwen2.5-Coder-14B-Instruct-Q4_K_M.gguf" ^
     "C:\ZzzFort\diskllm\models\qwen2.5-coder-14b\qwen2.5-coder-14b-ollama.gguf"
The name inside the directory must end with .gguf. The -ollama suffix is not required — it is only a convention used by DiskLLM.

How the Model Manager Discovers Models
model-manager.py scans C:\ZzzFort\diskllm\models\ at startup and on every /models request:

Lists all subdirectories of models\.

In each, finds the first *.gguf file.

Returns the list as JSON:

json
{
  "models": [
    {"name": "qwen2.5-coder-14b", "path": "...", "alias": "qwen2.5-coder-14b"},
    {"name": "qwen3-8b", "path": "...", "alias": "qwen3-8b"}
  ]
}
The directory name becomes the model's name and alias. The alias is what appears in the chat selector.

Adding a new model requires no code changes:

Drop a new subdirectory under models\.

Put a .gguf file inside.

Restart model-manager.py (or wait — the manager rescans on each /models request).

The new model appears in the chat selector.

Current Model Set
The project was tested with these three models:

Name	File	Size	Purpose	Language
qwen2.5-coder-7b	qwen2.5-coder-7b-ollama.gguf	4.4 GB	Code, faster	English
qwen2.5-coder-14b	qwen2.5-coder-14b-ollama.gguf	9.0 GB	Code, smarter	English
qwen3-8b	qwen3-8b-ollama.gguf	5.2 GB	General chat	Russian + English
Note on language: qwen2.5-coder is optimized for code and English. It handles Russian poorly — it may respond in Chinese, or attempt to invoke non-existent tool calls. For Russian chat, use qwen3-8b (or any Qwen3 / Gemma model).

Model Switching Behavior
Only one model is loaded at a time. The model manager enforces this:

chat.html sends POST /switch {"model": "..."} to model-manager.py.

Manager kills all llama-server.exe processes (taskkill /F /IM llama-server.exe).

Manager waits for port 8082 to become free.

Manager launches a new llama-server.exe with the selected model.

Manager polls /v1/models on port 8082 until the server responds (up to 90 seconds).

Manager returns {"status": "ok"} to the chat.

Chat updates the status indicator and continues.

Switch time:

7B model: ~15-30 seconds

8B model: ~20-40 seconds

14B model: ~40-70 seconds

The delay is dominated by disk read (cold cache) and model initialization.

Model Storage Layout
text
C:\ZzzFort\diskllm\models\
├── qwen2.5-coder-7b\
│   └── qwen2.5-coder-7b-ollama.gguf      (4.4 GB)
├── qwen2.5-coder-14b\
│   └── qwen2.5-coder-14b-ollama.gguf    (9.0 GB)
└── qwen3-8b\
    └── qwen3-8b-ollama.gguf             (5.2 GB)
Total: ~18.6 GB.

Removing Models
To delete a model:

cmd
rmdir /s /q C:\ZzzFort\diskllm\models\qwen2.5-coder-7b
The manager will not show it in the selector on the next /models request. No other cleanup required.

To re-add, repeat Option A or Option B.

Troubleshooting
Model not showing in the chat selector
Verify the directory exists: dir C:\ZzzFort\diskllm\models\

Verify .gguf file is present: dir C:\ZzzFort\diskllm\models\<name>\

Check that model-manager.py is running: curl http://127.0.0.1:8090/models

Restart model-manager.py if it doesn't reflect changes.

"Model not found" after switch
The path in model-manager.py doesn't match the actual file. Run curl http://127.0.0.1:8090/models and verify the paths.

Switch takes longer than 90 seconds
Increase the timeout in model-manager.py:

python
if wait_for_server(timeout=180):  # was 90
For very large models (32B+), increase to 300 seconds.

Multiple llama-server processes running
If the manager fails to kill a zombie process, kill manually:

cmd
taskkill /F /IM llama-server.exe
Then restart the manager.

Disk Space Planning
Model size	Q4_K_M file size	+KV cache	Total disk
7B	4.4 GB	~1 GB	~5.5 GB
8B	5.2 GB	~1 GB	~6.2 GB
14B	9.0 GB	~1.5 GB	~10.5 GB
32B	19 GB	~2 GB	~21 GB
KV cache is stored in RAM, not on disk, when -ctk q8_0 -ctv q8_0 is used (recommended). Disk space is dominated by model weights.

For a typical setup with three models (7B, 8B, 14B), plan for ~25 GB of disk space.