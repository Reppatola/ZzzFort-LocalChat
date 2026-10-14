"""
ZzzFort-LocalChat — Model Manager
Manages llama-server: kills the current process, starts a new one with the selected model.
Listens on port 8090.
"""

import os
import sys
import json
import time
import subprocess
import glob
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import requests

# ===== Configuration =====
BASE = r"C:\ZzzFort"
BIN = os.path.join(BASE, "diskllm", "bin")
MODELS_DIR = os.path.join(BASE, "diskllm", "models")
LLAMA_PORT = 8082
MANAGER_PORT = 8090
DEFAULT_MODEL = "qwen3-8b"
CTX = 8192
KV_TYPE = "q8_0"

# ===== Helpers =====

def list_models():
    """Scan MODELS_DIR, return a list of available models."""
    result = []
    if not os.path.isdir(MODELS_DIR):
        return result
    for d in sorted(os.listdir(MODELS_DIR)):
        subdir = os.path.join(MODELS_DIR, d)
        if not os.path.isdir(subdir):
            continue
        ggufs = glob.glob(os.path.join(subdir, "*.gguf"))
        if ggufs:
            result.append({
                "name": d,
                "path": ggufs[0],
                "alias": d,
            })
    return result


def is_server_running():
    """Check if llama-server responds on LLAMA_PORT."""
    try:
        r = requests.get(f"http://127.0.0.1:{LLAMA_PORT}/v1/models", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def get_active_model():
    """Return the name of the active model, or None."""
    try:
        r = requests.get(f"http://127.0.0.1:{LLAMA_PORT}/v1/models", timeout=2)
        if r.status_code == 200:
            data = r.json()
            if data.get("data"):
                return data["data"][0]["id"]
    except Exception:
        pass
    return None


def kill_llama_server():
    """Kill all llama-server.exe processes. Wait for the port to free."""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "llama-server.exe"],
                       capture_output=True, timeout=10)
    except Exception as e:
        print(f"[manager] taskkill error: {e}", flush=True)
    for _ in range(20):
        time.sleep(0.3)
        if not is_server_running():
            return True
    return False


def start_llama_server(model_path, alias):
    """Launch llama-server with the specified model."""
    exe = os.path.join(BIN, "llama-server.exe")
    cmd = [
        exe,
        "-m", model_path,
        "-c", str(CTX),
        "-ctk", KV_TYPE, "-ctv", KV_TYPE,
        "--alias", alias,
        "--port", str(LLAMA_PORT),
        "--host", "127.0.0.1",
    ]
    print(f"[manager] starting: {' '.join(cmd)}", flush=True)
    # DETACHED_PROCESS | CREATE_NO_WINDOW
    subprocess.Popen(
        cmd,
        cwd=BIN,
        creationflags=0x00000008 | 0x08000000,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def wait_for_server(timeout=90):
    """Wait until llama-server responds."""
    start = time.time()
    while time.time() - start < timeout:
        if is_server_running():
            return True
        time.sleep(1)
    return False


def switch_model(model_name):
    """Kill current server, start new one with the specified model."""
    models = list_models()
    target = next((m for m in models if m["name"] == model_name), None)
    if not target:
        return {"status": "error", "message": f"Model '{model_name}' not found"}

    print(f"[manager] switching to {model_name}...", flush=True)
    kill_llama_server()
    start_llama_server(target["path"], target["alias"])

    if wait_for_server(timeout=90):
        return {"status": "ok", "model": model_name, "port": LLAMA_PORT}
    else:
        return {"status": "error", "message": "Model did not load within 90 seconds"}


# ===== HTTP Handler =====

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[manager] {fmt % args}", flush=True)

    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json({}, 204)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/models":
            self._send_json({"models": list_models()})
        elif path == "/status":
            self._send_json({
                "running": is_server_running(),
                "active": get_active_model(),
                "port": LLAMA_PORT,
            })
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/switch":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                data = json.loads(body)
                model = data.get("model", "")
                result = switch_model(model)
                self._send_json(result)
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, 500)
        else:
            self._send_json({"error": "not found"}, 404)


# ===== Entry Point =====

def main():
    print("[manager] ZzzFort-LocalChat Model Manager", flush=True)
    print(f"[manager] Models dir: {MODELS_DIR}", flush=True)
    print(f"[manager] llama-server port: {LLAMA_PORT}", flush=True)
    print(f"[manager] manager port: {MANAGER_PORT}", flush=True)

    models = list_models()
    print(f"[manager] Found {len(models)} models:", flush=True)
    for m in models:
        print(f"  - {m['name']}", flush=True)

    if is_server_running():
        print(f"[manager] llama-server already running: {get_active_model()}", flush=True)
    else:
        default = next((m for m in models if m["name"] == DEFAULT_MODEL), None)
        if default:
            print(f"[manager] starting default model: {DEFAULT_MODEL}", flush=True)
            start_llama_server(default["path"], default["alias"])
            if wait_for_server(timeout=90):
                print(f"[manager] {DEFAULT_MODEL} loaded", flush=True)
            else:
                print(f"[manager] WARNING: {DEFAULT_MODEL} did not load in 90s", flush=True)
        else:
            print(f"[manager] WARNING: default model '{DEFAULT_MODEL}' not found", flush=True)

    server = HTTPServer(("127.0.0.1", MANAGER_PORT), Handler)
    print(f"[manager] listening on http://127.0.0.1:{MANAGER_PORT}", flush=True)
    print("[manager] press Ctrl+C to stop", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[manager] shutting down...", flush=True)


if __name__ == "__main__":
    main()