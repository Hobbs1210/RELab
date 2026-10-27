"""Binwalk firmware inspection and extraction MCP server."""
from __future__ import annotations
import json, os, pathlib, re, shutil, subprocess
from fastapi import FastAPI, HTTPException
from fastapi_mcp import FastApiMCP

app = FastAPI(title="Device Binwalk MCP Server", docs_url=None)
FIRMWARE_ROOT = pathlib.Path(os.environ.get("FIRMWARE_PATH", "/firmware")).resolve()
EXTRACT_ROOT = pathlib.Path(os.environ.get("EXTRACT_PATH", "/extracted")).resolve()

def _safe_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,180}", name) or ".." in name:
        raise HTTPException(400, "Invalid filename")
    return name

@app.get("/health", operation_id="binwalk_status")
def binwalk_status() -> dict:
    has_binwalk = shutil.which("binwalk") is not None
    return {"status": "ready" if has_binwalk else "binary_missing", "binwalk_available": has_binwalk}

@app.get("/scan/{filename}", operation_id="binwalk_scan")
def binwalk_scan(filename: str) -> dict:
    fname = _safe_name(filename)
    target = (FIRMWARE_ROOT / fname).resolve()
    if not target.is_relative_to(FIRMWARE_ROOT) or not target.is_file():
        raise HTTPException(404, f"Firmware file not found: {fname}")
    try:
        proc = subprocess.run(["binwalk", str(target)], capture_output=True, text=True, timeout=120)
        return {"filename": fname, "returncode": proc.returncode, "scan_output": proc.stdout[:15000], "stderr": proc.stderr[:2000]}
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Binwalk scan timed out after 120s")
    except Exception as exc:
        raise HTTPException(500, f"Binwalk error: {exc}")

@app.post("/extract/{filename}", operation_id="binwalk_extract")
def binwalk_extract(filename: str) -> dict:
    fname = _safe_name(filename)
    target = (FIRMWARE_ROOT / fname).resolve()
    if not target.is_relative_to(FIRMWARE_ROOT) or not target.is_file():
        raise HTTPException(404, f"Firmware file not found: {fname}")
    dest_dir = EXTRACT_ROOT / fname
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(["binwalk", "-Me", "-C", str(dest_dir), str(target)], capture_output=True, text=True, timeout=300)
        extracted_files = [str(p.relative_to(dest_dir)) for p in dest_dir.rglob("*") if p.is_file()][:100]
        return {"filename": fname, "returncode": proc.returncode, "file_count": len(extracted_files), "sample_files": extracted_files, "stdout_tail": proc.stdout[-2000:]}
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Binwalk extraction timed out after 300s")
    except Exception as exc:
        raise HTTPException(500, f"Extraction failed: {exc}")

@app.get("/extracted/{filename}", operation_id="binwalk_list_extracted")
def binwalk_list_extracted(filename: str) -> dict:
    fname = _safe_name(filename)
    dest_dir = EXTRACT_ROOT / fname
    if not dest_dir.exists():
        return {"filename": fname, "extracted": False, "files": []}
    files = [str(p.relative_to(dest_dir)) for p in dest_dir.rglob("*") if p.is_file()][:200]
    return {"filename": fname, "extracted": True, "total_files": len(files), "files": files}

mcp = FastApiMCP(app, name="Device Binwalk MCP Server", include_operations=["binwalk_status", "binwalk_scan", "binwalk_extract", "binwalk_list_extracted"])
mcp.mount_http(mount_path="/mcp")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

