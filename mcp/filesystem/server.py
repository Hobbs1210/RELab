"""Scoped, safe read-only filesystem MCP server for lab artifacts."""
from __future__ import annotations
import hashlib, os, pathlib
from fastapi import FastAPI, HTTPException
from fastapi_mcp import FastApiMCP

app = FastAPI(title="Device Filesystem MCP Server", docs_url=None)

ALLOWED_ROOTS = {
    "firmware": pathlib.Path(os.environ.get("FIRMWARE_PATH", "/firmware")),
    "captures": pathlib.Path(os.environ.get("PCAP_PATH", "/captures")),
    "analysis": pathlib.Path(os.environ.get("ANALYSIS_PATH", "/analysis")),
    "protocols": pathlib.Path(os.environ.get("PROTOCOLS_PATH", "/protocols")),
    "data": pathlib.Path(os.environ.get("DATA_PATH", "/data")),
}

def _resolve_safe(root_name: str, subpath: str) -> tuple[pathlib.Path, pathlib.Path]:
    if root_name not in ALLOWED_ROOTS:
        raise HTTPException(400, f"Root '{root_name}' not allowed. Allowed: {list(ALLOWED_ROOTS.keys())}")
    root = ALLOWED_ROOTS[root_name].resolve()
    target = (root / subpath.lstrip("/\\")).resolve()
    if not target.is_relative_to(root):
        raise HTTPException(403, "Access outside allowed root path is prohibited")
    return root, target

@app.get("/health", operation_id="fs_status")
def fs_status() -> dict:
    available = {k: v.exists() for k, v in ALLOWED_ROOTS.items()}
    return {"status": "ready", "mounted_roots": available}

@app.get("/list/{root_name}", operation_id="fs_list_files")
def fs_list_files(root_name: str, subpath: str = "") -> dict:
    root, target = _resolve_safe(root_name, subpath)
    if not target.exists():
        raise HTTPException(404, f"Path not found: {subpath}")
    if not target.is_dir():
        return {"root": root_name, "path": subpath, "is_directory": False, "size": target.stat().st_size}
    
    entries = []
    for item in sorted(target.iterdir()):
        entries.append({
            "name": item.name,
            "is_dir": item.is_dir(),
            "size": item.stat().st_size if item.is_file() else 0,
        })
    return {"root": root_name, "path": subpath, "count": len(entries), "entries": entries[:200]}

@app.get("/read/{root_name}", operation_id="fs_read_file")
def fs_read_file(root_name: str, subpath: str, max_bytes: int = 16384) -> dict:
    root, target = _resolve_safe(root_name, subpath)
    if not target.is_file():
        raise HTTPException(404, f"File not found: {subpath}")
    safe_max = max(256, min(max_bytes, 1024 * 1024))
    size = target.stat().st_size
    with target.open("rb") as f:
        data = f.read(safe_max)
    is_text = True
    try:
        text_content = data.decode("utf-8")
    except UnicodeDecodeError:
        is_text = False
        text_content = data.hex()
    return {
        "root": root_name,
        "path": subpath,
        "total_size": size,
        "bytes_returned": len(data),
        "is_text": is_text,
        "content": text_content,
    }

@app.get("/info/{root_name}", operation_id="fs_file_info")
def fs_file_info(root_name: str, subpath: str) -> dict:
    root, target = _resolve_safe(root_name, subpath)
    if not target.exists():
        raise HTTPException(404, f"Target not found: {subpath}")
    stat = target.stat()
    sha256 = ""
    if target.is_file() and stat.st_size < 100 * 1024 * 1024:
        h = hashlib.sha256()
        with target.open("rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        sha256 = h.hexdigest()
    return {
        "root": root_name,
        "path": subpath,
        "is_dir": target.is_dir(),
        "size": stat.st_size,
        "sha256": sha256 or "not_computed",
        "mtime": stat.st_mtime,
    }

@app.get("/find/{root_name}", operation_id="fs_find_files")
def fs_find_files(root_name: str, pattern: str = "*", limit: int = 100) -> dict:
    root, _ = _resolve_safe(root_name, "")
    clean_pattern = pattern.replace("..", "")
    matches = []
    for p in root.rglob(clean_pattern):
        if p.is_file():
            matches.append(str(p.relative_to(root)))
        if len(matches) >= limit:
            break
    return {"root": root_name, "pattern": clean_pattern, "match_count": len(matches), "matches": matches}

mcp = FastApiMCP(app, name="Device Filesystem MCP Server", include_operations=["fs_status", "fs_list_files", "fs_read_file", "fs_file_info", "fs_find_files"])
mcp.mount_http(mount_path="/mcp")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

