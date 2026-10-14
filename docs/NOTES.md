# Notes — Experiments and Measurements

This document records the actual experiments run during development: what was tested, what was measured, and what conclusions were drawn. It is intentionally informal — raw data, in the order it was collected.

---

## Hardware / Software Baseline

- **CPU:** AMD Ryzen (8 cores / 16 threads)
- **RAM:** 32 GB DDR5
- **GPU:** NVIDIA RTX 4060 (not used in these tests — CPU-only inference)
- **Disk:** 1 TB NVMe SSD (system drive C:)
- **OS:** Windows 10.0.19045
- **Build:** MinGW GCC 16.2.0 (UCRT, POSIX threads)
- **llama.cpp commit:** `df18bee`

All measurements taken via `Get-Process llama-server` in PowerShell:
```powershell
Get-Process llama-server | Select-Object `
  @{N='Private (GB)';E={[math]::Round($_.PrivateMemorySize64/1GB,2)}}, `
  @{N='WorkingSet (GB)';E={[math]::Round($_.WorkingSet64/1GB,2)}}
Experiment 1: Baseline RAM with Qwen2.5-Coder-7B
Goal: measure private RAM and working set for a 7B model at 2K context.

Command:

cmd
llama-server.exe -m qwen2.5-coder-7b-ollama.gguf -c 2048 --port 8080
Measured:

Private RAM: 0.38 GB

Working Set: 4.26 GB

Model file size: 4.4 GB

Observation: working set ≈ model size. Private RAM is tiny — model is mmap'd, not loaded into process memory.

Experiment 2: Qwen2.5-Coder-14B at 2K context
Goal: does private RAM grow with model size?

Command:

cmd
llama-server.exe -m qwen2.5-coder-14b-ollama.gguf -c 2048 --port 8080
Measured:

Private RAM: 0.67 GB

Working Set: 8.39 GB

Model file size: 9.0 GB

Observation: model doubled in size (4.4 → 9.0 GB). Working set doubled (4.26 → 8.39 GB). But private RAM grew only by 0.29 GB — from 0.38 to 0.67.

Conclusion 1: Private RAM does not scale with model size. Only KV cache and inference buffers matter.

Experiment 3: Qwen2.5-Coder-14B at 8K context (f16 KV)
Goal: how much does KV cache grow with context?

Command:

cmd
llama-server.exe -m qwen2.5-coder-14b-ollama.gguf -c 8192 --port 8080
Measured:

Private RAM: 1.81 GB

Working Set: 9.52 GB

Delta vs 2K context:

Private RAM: +1.14 GB

Working Set: +1.13 GB

Conclusion 2: At 14B, each 4× increase in context (2048 → 8192) adds ~1.14 GB of KV cache. So ~0.14 MB per token for 14B models with f16 KV.

Extrapolation:

Context	KV cache (f16)
2048	0.29 GB
8192	1.14 GB
16384	2.28 GB
32768	4.56 GB
65536	9.12 GB
131072	18.24 GB
Critical point: at ~64K context, KV cache alone equals the model file size (9 GB). This is where SSD-based KV cache becomes necessary.

Experiment 4: q8_0 KV cache
Goal: does 8-bit KV quantization reduce RAM without hurting quality?

Command:

cmd
llama-server.exe -m qwen2.5-coder-14b-ollama.gguf -c 8192 -ctk q8_0 -ctv q8_0 --port 8080
Measured:

Private RAM: 1.10 GB

Working Set: 8.83 GB

Delta vs f16:

Private RAM: −0.71 GB (−39%)

Working Set: −0.69 GB

Conclusion 3: q8_0 KV reduces private RAM by ~40% with negligible effect on speed.

Speed check:

Config	Decode (tok/s)
f16 KV	2.42
q8_0 KV	2.43
No measurable speed difference. q8_0 is strictly better for this use case.

Experiment 5: Generation quality with q8_0
Goal: does 8-bit KV quantization hurt response quality?

Test prompt (English):

text
Write a Python function to check if a string is a palindrome.
Config: q8_0 KV, 14B model, max_tokens 200.

Result: correct Python function, correct explanation, proper markdown formatting. No degradation.

Test prompt (Russian):

text
Напиши функцию на Python для проверки, является ли строка палиндромом.
Result: model responded in Chinese: "Sorry, I can't understand your question, it appears to be non-Latin text". It did not attempt to answer.

Conclusion 4: qwen2.5-coder is not multilingual. It is code + English only. Russian prompts need a different model (qwen3, gemma).

Note: this is not a q8_0 issue — the same behavior occurs with f16 KV. It is a model capability issue.

Experiment 6: Tool-calling bug with coder models
Goal: test qwen2.5-coder-14b in a chat interface (Open WebUI).

Test: user sends "Привет как дела?" — the model responds with:

json
{"name": "create_note", "arguments": {"content": "Привет как дела?"}}
The model does not answer the question. It attempts to invoke a tool ("create_note") that does not exist.

Cause: qwen2.5-coder is trained with function-calling patterns. In a chat context that includes a tools section (as Open WebUI sends by default), the model interprets user input as tool arguments.

Conclusion 5: For chat use with coder models:

Disable tool-calling in the client (do not send tools).

Do not enable --jinja on the server.

Send plain OpenAI-format messages only.

Our chat.html sends plain {"messages": [...]} without tools — and the model answers normally.

Experiment 7: Speed comparison across models
Config: all at 8K context, q8_0 KV, CPU-only.

Model	Prompt eval (tok/s)	Decode (tok/s)
Qwen2.5-Coder 7B	12.76	4.78
Qwen2.5-Coder 14B	6.73	2.42
Qwen3 8B	(untested)	(untested)
Observations:

Decode speed scales roughly inversely with parameter count.

CPU-only inference is ~4-6× slower than GPU inference.

7B at ~4.8 tok/s is usable for chat.

14B at ~2.4 tok/s is slow but usable for code generation.

GPU projection: enabling CUDA on RTX 4060 should bring decode to ~20-30 tok/s for 7B, ~15-20 tok/s for 14B. This is the next planned optimization.

Experiment 8: DiskLLM — attempt and failure
Goal: test DiskLLM (SSD-based KV cache project) for comparison.

Steps:

pip install diskllm — succeeded.

diskllm pull qwen2.5-coder:7b — succeeded, linked Ollama blob.

diskllm run qwen2.5-coder:7b --session test1 --headless — failed.

Error sequence:

First: libidn.dll not found → copied libidn-12.dll.

Then: libidn.dll not found again → copied libidn2-0.dll.

Then: libidn.dll not found again → copied libunistring-5.dll, libintl-8.dll, libiconv-2.dll.

Then: libidn.dll not found again — even after all dependencies were in place.

Root cause: DiskLLM's llama-server.exe was compiled by a different GCC version than the DLLs we provided. ABI mismatch. objdump -p shows the binary requires functions that do not exist in GCC 16.2.0's libgcc_s_seh-1.dll.

Fix attempted: download MinGW GCC 16.2.0 from WinLibs, copy matching DLLs.

Result: DLLs loaded, but llama-server.exe still failed on libidn.dll — even though objdump shows the binary does not directly import it. The error came from a transitive dependency that was not obvious.

Decision: abandon DiskLLM's pre-built binary. Compile llama-server.exe from source with our own MinGW GCC 16.2.0.

Conclusion 6: Projects that publish Windows binaries without their runtime dependencies create a bad experience. The user must guess which MinGW version to download and which DLLs to place where. This is a structural gap — no tool exists to resolve recursive Windows DLL dependencies automatically.

This became the inspiration for the project's documentation: BUILD.md exists precisely so that no one else has to go through this.

Experiment 9: Successful self-compiled build
Goal: build llama-server.exe from source with the MinGW we control.

Steps:

git clone --depth 1 llama.cpp — 37 MB.

Patch cpp-httplib\httplib.cpp (CreateFile2 → CreateFileW).

Patch cpp-httplib\httplib.h (remove _WIN32_WINNT check).

cmake -B build -G "MinGW Makefiles" -DGGML_CUDA=OFF -DLLAMA_CURL=OFF

cmake --build build -j — 10 minutes.

Result: llama-server.exe — 18 MB, works. --help prints correctly. Loads models. Serves HTTP.

Verification:

cmd
curl http://127.0.0.1:8080/v1/models
Returns valid JSON with the model list.

Conclusion 7: MinGW GCC 16.2.0 can build llama.cpp — with two patches. This is not documented anywhere. The recipe is now in BUILD.md.

Experiment 10: Model switching latency
Goal: measure time to switch models.

Test: from qwen2.5-coder-14b to qwen3-8b, then back.

Warm cache timings:

Kill 14B: 1 sec

Start 8B: 15-20 sec

Kill 8B: 1 sec

Start 14B: 30-40 sec

Cold cache (after reboot):

Start 14B: 60-90 sec

Conclusion 8: Switching is slow enough that the user must be told it is happening. Hence the "Switching to..." system messages in chat.

Loading a 14B model from disk takes 30-60 seconds. The disk read is the dominant cost. SSD helps, but 9 GB is 9 GB.

Experiment 11: KV cache quantization for larger contexts
Not tested yet. Planned.

Hypothesis: at 64K context with q4_0 KV, private RAM should stay below 5 GB for a 14B model — making long-context chat viable on 16 GB machines.

To test:

14B at 32K, 64K, 128K with f16, q8_0, q4_0 KV.

Measure private RAM and response quality.

Experiment 12: GPU offload (pending)
Not tested yet. Planned.

Goal: rebuild with -DGGML_CUDA=ON and measure speedup.

Expected:

Decode speed 7B: 4.78 → 25-30 tok/s

Decode speed 14B: 2.42 → 15-20 tok/s

VRAM usage: ~4-8 GB depending on model size

Complications:

RTX 4060 has 8 GB VRAM. 14B Q4 needs ~9 GB. Partial offload required.

CUDA toolkit adds ~2 GB to the build environment.

DLL dependencies increase (cudart, cublas, etc.).

Key Takeaways
Private RAM is not determined by model size. A 14B model uses 0.67 GB private RAM at 2K context. Only KV cache and active buffers count.

KV cache is the real RAM consumer. At 8K context, 14B model needs 1.14 GB for KV. At 64K, it needs ~9 GB.

q8_0 KV cache is a free upgrade. 40% less RAM, no measurable quality or speed cost. Should always be enabled.

mmap is the unsung hero. It allows models to be 3-5× larger than available RAM, because weights stay on disk and load on demand.

Model switching is expensive. 15-90 seconds per switch. Only one model should be loaded at a time.

Not all models speak all languages. qwen2.5-coder is English + code. For Russian, use qwen3 or gemma.

Tool-calling can break chat. Coder models trained on function-calling will hijack casual prompts if the client sends a tools section. Disable it.

Windows AI tooling is fragile. Missing DLLs, ABI mismatches, no dependency resolution. Building from source with a controlled toolchain is more reliable than trusting pre-built binaries.

The third optimization level (SSD-based KV) is only needed at 64K+ context. Below that, RAM-based KV is fine.

There is no tool that solves all this automatically. The project exists to close that gap for at least one specific use case.