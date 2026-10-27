"""Radare2 / Rizin lightweight binary analysis MCP server."""
from __future__ import annotations
import json, math, os, pathlib, re, shutil, subprocess
from fastapi import FastAPI, HTTPException
from fastapi_mcp import FastApiMCP

app = FastAPI(title="Device Radare2 MCP Server", docs_url=None)
FIRMWARE_ROOT = pathlib.Path(os.environ.get("FIRMWARE_PATH", "/firmware")).resolve()

def _safe_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,180}", name) or ".." in name:
        raise HTTPException(400, "Invalid filename")
    return name

def _check_r2() -> str:
    for cmd in ["r2", "radare2", "rizin"]:
        if shutil.which(cmd):
            return cmd
    return ""

@app.get("/health", operation_id="radare_status")
def radare_status() -> dict:
    tool = _check_r2()
    return {"status": "ready" if tool else "tool_missing", "engine": tool or "none"}

@app.get("/info/{filename}", operation_id="radare_info")
def radare_info(filename: str) -> dict:
    fname = _safe_name(filename)
    target = (FIRMWARE_ROOT / fname).resolve()
    if not target.is_relative_to(FIRMWARE_ROOT) or not target.is_file():
        raise HTTPException(404, f"Binary not found: {fname}")
    rabin = "rabin2" if shutil.which("rabin2") else ("rz-bin" if shutil.which("rz-bin") else None)
    if not rabin:
        raise HTTPException(500, "rabin2/rz-bin not found in PATH")
    proc = subprocess.run([rabin, "-Ij", str(target)], capture_output=True, text=True, timeout=30)
    try:
        data = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except Exception:
        data = {"raw": proc.stdout[:2000]}
    return {"filename": fname, "info": data}

@app.get("/strings/{filename}", operation_id="radare_strings")
def radare_strings(filename: str, min_len: int = 6, limit: int = 200) -> dict:
    fname = _safe_name(filename)
    target = (FIRMWARE_ROOT / fname).resolve()
    if not target.is_relative_to(FIRMWARE_ROOT) or not target.is_file():
        raise HTTPException(404, f"Binary not found: {fname}")
    rabin = "rabin2" if shutil.which("rabin2") else ("rz-bin" if shutil.which("rz-bin") else None)
    if not rabin:
        raise HTTPException(500, "rabin2/rz-bin not found in PATH")
    proc = subprocess.run([rabin, "-z", "-n", str(min_len), str(target)], capture_output=True, text=True, timeout=30)
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()][:limit]
    return {"filename": fname, "count": len(lines), "strings": lines}

@app.get("/functions/{filename}", operation_id="radare_functions")
def radare_functions(filename: str, limit: int = 150) -> dict:
    fname = _safe_name(filename)
    target = (FIRMWARE_ROOT / fname).resolve()
    if not target.is_relative_to(FIRMWARE_ROOT) or not target.is_file():
        raise HTTPException(404, f"Binary not found: {fname}")
    r2 = _check_r2()
    if not r2:
        raise HTTPException(500, "r2/radare2 not found")
    proc = subprocess.run([r2, "-q", "-c", "aa; aflj", str(target)], capture_output=True, text=True, timeout=60)
    try:
        funcs = json.loads(proc.stdout) if proc.stdout.strip() else []
        return {"filename": fname, "total": len(funcs), "functions": funcs[:limit]}
    except Exception:
        return {"filename": fname, "raw": proc.stdout[:2000]}

@app.get("/disasm/{filename}", operation_id="radare_disasm")
def radare_disasm(filename: str, symbol_or_offset: str = "main", count: int = 20) -> dict:
    fname = _safe_name(filename)
    target = (FIRMWARE_ROOT / fname).resolve()
    if not target.is_relative_to(FIRMWARE_ROOT) or not target.is_file():
        raise HTTPException(404, f"Binary not found: {fname}")
    r2 = _check_r2()
    if not r2:
        raise HTTPException(500, "r2/radare2 not found")
    safe_loc = re.sub(r"[^A-Za-z0-9_.]", "", symbol_or_offset)[:40]
    safe_count = max(1, min(count, 100))
    proc = subprocess.run([r2, "-q", "-c", f"aa; s {safe_loc}; pdj {safe_count}", str(target)], capture_output=True, text=True, timeout=45)
    try:
        insns = json.loads(proc.stdout) if proc.stdout.strip() else []
        return {"filename": fname, "location": safe_loc, "instructions": insns}
    except Exception:
        return {"filename": fname, "location": safe_loc, "raw": proc.stdout[:3000]}

@app.get("/entropy/{filename}", operation_id="radare_entropy")
def radare_entropy(filename: str) -> dict:
    fname = _safe_name(filename)
    target = (FIRMWARE_ROOT / fname).resolve()
    if not target.is_relative_to(FIRMWARE_ROOT) or not target.is_file():
        raise HTTPException(404, f"Binary not found: {fname}")
    # Compute block entropy quickly in Python
    size = target.stat().st_size
    block_size = max(1024, size // 64) if size > 0 else 1024
    blocks = []
    with target.open("rb") as f:
        while chunk := f.read(block_size):
            counts = {}
            for b in chunk:
                counts[b] = counts.get(b, 0) + 1
            entropy = -sum((c / len(chunk)) * math.log2(c / len(chunk)) for c in counts.values())
            blocks.append(round(entropy, 3))
    avg_entropy = round(sum(blocks) / len(blocks), 3) if blocks else 0.0
    return {"filename": fname, "size": size, "block_count": len(blocks), "average_entropy": avg_entropy, "entropy_curve": blocks[:64]}

mcp = FastApiMCP(app, name="Device Radare2 MCP Server", include_operations=["radare_status", "radare_info", "radare_strings", "radare_functions", "radare_disasm", "radare_entropy"])
mcp.mount_http(mount_path="/mcp")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

